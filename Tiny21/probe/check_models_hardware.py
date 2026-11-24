"""Verify a dual-model bundle on the Ultimate from a detached background shell."""
import argparse
import json
import os
from pathlib import Path
import socket
import time

from probe.physical import (CARTRIDGE_CATEGORY, CATEGORY, PORT, Frames, Ultimate, bundle_marker,
                            decode_boot, frame_color, json_file, probe_visible, save_png)
from probe.video_capture import screen_codes

KEY_F1 = 0x85
KEY_F3 = 0x86
SCREEN = 0x0400


def wait_frame(device, frames, marker, deadline, *, busy_first=False):
    stable = 0
    while time.monotonic() < deadline:
        try:
            frame = frames.receive(min(deadline, time.monotonic() + 9))
        except TimeoutError:
            stable = 0
            device.request('/streams/video:stop', method='PUT')
            frames.flush()
            device.request('/streams/video:start', method='PUT', params={'ip': f'{device.local_ip()}:{PORT}'})
            continue
        if not probe_visible(frame, marker):
            stable = 0
            continue
        state = frame_color(frame)
        if state == 2:
            raise RuntimeError('the Ultimate reported a probe error')
        if state in (3, 4):
            busy_first = False
        stable = stable + 1 if state == 5 and not busy_first else 0
        if stable >= 3:
            return frame
    raise TimeoutError('the expected probe screen did not settle')


def screen_line(device, row):
    return device.capture_memory(SCREEN + 40*row, 40).strip(b' ')


def byte(device, symbols, name):
    return device.capture_memory(symbols[name], 1)[0]


def post_key(device, value):
    end = time.monotonic() + 4
    while device.capture_memory(0xC6, 1) != b'\0':
        if time.monotonic() >= end:
            raise TimeoutError('the automation keyboard queue is occupied')
        time.sleep(0.025)
    for address, data in ((0x0277, value), (0x00C6, 1)):
        device.request('/machine:writemem', method='PUT',
                       params={'address': f'{address:04X}', 'data': f'{data:02X}'})


def choose(device, symbols, key, name, expected_bank):
    post_key(device, key)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        # The model changes only after an entire verified image was admitted.
        if screen_line(device, 5) == screen_codes('Model: ' + name):
            if screen_line(device, 10) != screen_codes('Model ready.'):
                time.sleep(0.1)
                continue
            bank = byte(device, symbols, 'model_bank')
            if bank != expected_bank:
                raise RuntimeError(f'{name} displayed with the wrong REU bank {bank}')
            return {'name': name, 'reu_offset': bank << 16,
                    'ultimate_dos': bool(byte(device, symbols, 'model_disk_load')),
                    'context': byte(device, symbols, 'model_context')}
        if screen_line(device, 10).startswith(screen_codes('Load failed.')):
            raise RuntimeError(f'the Ultimate could not load {name}')
        time.sleep(0.25)
    raise TimeoutError(f'model did not switch to {name}')


def question(device, frames, marker, prompt, expected, screenshot):
    for char in prompt:
        post_key(device, ord(char))
        time.sleep(0.03)
    frames.flush()
    post_key(device, 13)
    frame = wait_frame(device, frames, marker, time.monotonic() + 190, busy_first=True)
    if screen_line(device, 10) != screen_codes('Answer complete. Ready.'):
        raise RuntimeError(f'{prompt!r} did not finish normally')
    for index, line in enumerate(expected.splitlines()):
        actual = screen_line(device, 12 + index)
        if actual != screen_codes(line):
            raise RuntimeError(f'{prompt!r} line {index + 1}: expected {line!r}, got {actual.hex()}')
    save_png(frame, screenshot)
    return {'prompt': prompt, 'answer': expected, 'answer_rows': len(expected.splitlines())}


def run(device, bundle, out):
    manifest = json.loads((bundle / 'bundle.json').read_text())
    if not (manifest.get('automation_keyboard') and manifest.get('second_model')):
        raise ValueError('build the dual-model automation console')
    symbols = {name[1:]: int(address, 16) for _, address, name in
               map(str.split, (bundle / 'probe.lbl').read_text().splitlines())}
    out.mkdir(parents=True, exist_ok=False)
    before = device.category(CARTRIDGE_CATEGORY)
    if (before.get('Command Interface') != 'Enabled' or before.get('REU Size') != '16 MB' or
            before.get('RAM Expansion Unit') != 'Enabled' or
            device.category(CATEGORY).get('Turbo Control') != 'C64U Turbo Registers'):
        raise RuntimeError('the Ultimate is missing the required model-switching settings')
    device.install(bundle, manifest)
    device.request('/runners:run_prg', method='PUT',
                   params={'file': manifest['remote_path'] + '/PROBE.PRG'}, timeout=40)
    marker = bundle_marker(manifest)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', PORT))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        device.request('/streams/video:start', method='PUT', params={'ip': f'{device.local_ip()}:{PORT}'})
        try:
            frames = Frames(sock)
            frame = wait_frame(device, frames, marker, time.monotonic() + 80)
            boot = decode_boot(device.capture_memory(manifest['mailbox'], 32), manifest, ready_phase=4)
            save_png(frame, out / 'boot.png')
            result = {'boot': boot, 'models': [], 'questions': []}
            expected = [('show assembler code to set border to red', 'LDA #$02\nSTA $D020'),
                        ('show basic code to clear the screen and print ready',
                         '10 PRINT CHR$(147)\n20 PRINT "READY"')]
            result['models'].append(choose(device, symbols, KEY_F3, 'C64PROGINFO', 0x10))
            json_file(out / 'progress.json', result)
            for i, (prompt, answer) in enumerate(expected, 1):
                result['questions'].append(question(device, frames, marker, prompt, answer,
                                                     out / f'proginfo-{i}.png'))
                json_file(out / 'progress.json', result)
            result['models'].append(choose(device, symbols, KEY_F1, 'Tiny 2.1', 0))
            result['questions'].append(question(device, frames, marker, 'what is 7 times 8',
                                                 '7 times 8 is 56.', out / 'tiny21.png'))
            resident = choose(device, symbols, KEY_F3, 'C64PROGINFO', 0x10)
            if resident['ultimate_dos']:
                raise RuntimeError('the second visit should reuse the verified REU slot')
            result['models'].append(resident)
            assert device.category(CARTRIDGE_CATEGORY) == before
            json_file(out / 'result.json', result)
        finally:
            device.request('/streams/video:stop', method='PUT')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('TINY64_DETACHED') != '1' or os.isatty(0):
        parser.error('run this check from a detached background shell with stdin closed')
    run(Ultimate(args.host), args.bundle, args.out)
