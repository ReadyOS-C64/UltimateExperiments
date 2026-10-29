"""Exercise real C64 code through the established .NET VICE plan runner.

The Python layer makes fixtures/plans and independently checks artifacts. It
does not control VICE or emulate editor behavior. Logs are retained on failure.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from vice_config import ROOT, HARNESS, PROJECT, step
from vice_plan import run_plan


def native_screen_text(raw):
    out = []
    for value in raw:
        value &= 0x7F
        if 1 <= value <= 26:
            out.append(chr(value+96))
        elif 65 <= value <= 90:
            out.append(chr(value))
        elif value == 0:
            out.append('@')
        elif value == 28:
            out.append('£')
        elif 32 <= value <= 63:
            out.append(chr(value))
        else:
            out.append('·')
    return '\n'.join(''.join(out[i:i+40]) for i in range(0, len(out), 40))


def run_case(case, args):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence = ROOT/'agentsworking/evidence/M0'/f'{stamp}-{case}'
    evidence.mkdir(parents=True)
    disk = evidence/'working.d81'
    shutil.copyfile(ROOT/'build/supereditor.d81', disk)
    for name in ['build-report.json', 'supereditor.map', 'supereditor.lbl',
                 'disk-manifest.json']:
        shutil.copyfile(ROOT/'build'/name, evidence/name)
    canary = bytes(((i*73+29) & 255) for i in range(1024))
    expected_banks = {'boot': 256, 'no-reu': 0, 'small-reu': 8}[case]
    expected_status = 2 if case == 'no-reu' else 1
    steps = [
        step('launch', 'vice.launch', kill_stale=False),
        step('basic_ready', 'screen.wait_contains', text='READY.', wait_timeout_s=30),
        step('shim_seed', 'memory.write', start=0xC600, bytes_hex=canary.hex(' ')),
    ]
    if case in ('no-reu', 'small-reu'):
        steps.append(step('disable_reu', 'monitor.command', command='raw: resourceset "REU" "0"'))
    if case == 'small-reu':
        steps += [step('size_reu', 'monitor.command', command='raw: resourceset "REUsize" "512"'),
                  step('enable_reu', 'monitor.command', command='raw: resourceset "REU" "1"')]
    if case != 'no-reu':
        steps.append(step('reu_before', 'dump.reu', mode='full', stage_tag='reu_before'))
    # This LOAD+RUN is the genuine disk/ROM path, not a monitor memory injection.
    steps.append(step('disk_boot', 'input.sequence',
                      keys=list(b'LOAD"BOOTPROBE",8,1\rRUN\r'),
                      inter_key_delay_s=0.04, post_delay_s=0.1))
    ready = step('app_ready', 'assert.memory', start=0xC000, end=0xC008,
                 equals_hex=(b'SEDG'+bytes([1, expected_status, 0])+
                             expected_banks.to_bytes(2, 'little')).hex(' '))
    # Retrying a read-only predicate is safe; control inputs are never retried.
    ready['retry'] = dict(max_attempts=12, backoff_ms=40, jitter=False)
    steps += [ready,
              step('native_key', 'input.sequence', keys=[0x41], inter_key_delay_s=0.04),
              step('key_consumed', 'assert.memory', start=0xC009, end=0xC00B,
                   equals_hex='41 01 00'),
              step('shim_intact', 'assert.memory', start=0xC600, end=0xC9FF,
                   equals_hex=canary.hex(' ')),
              step('capture', 'screen.capture', label=f'{case}-screen', capture_state=True),
              step('ranges', 'dump.memory_ranges', ranges=[
                  dict(label='screen', start=0x4000, end=0x43E7),
                  dict(label='shim', start=0xC600, end=0xC9FF),
                  dict(label='diagnostics', start=0xC000, end=0xC01F),
                  dict(label='vic', start=0xD000, end=0xD02E)])]
    if case != 'no-reu':
        steps.append(step('reu_after', 'dump.reu', mode='full', stage_tag='reu_after'))
    steps.append(step('warp_confirmed', 'monitor.command', command='warp'))
    plan = dict(version=1, kind='vice_task_plan', plan_id=f'supereditor-{case}-{stamp}',
                run_mode='gui_vice', global_defaults=dict(
                    monitor_host='127.0.0.1', monitor_port_start=6580, monitor_port_span=30,
                    retry_policy=dict(max_attempts=1, backoff_ms=100, jitter=False),
                    timeouts=dict(launch_s=30, step_s=60, read_s=2),
                    artifact_policy=dict(capture_screen=True, capture_state=True, capture_dump=False),
                    vice=dict(disk8=str(disk), drive8_type=1581, drive9_enabled=False,
                              autostart_enabled=False, true_drive=False, close_vice=True,
                              headless=not args.visible, speed_percent=100)), steps=steps)
    # JSON is a YAML subset accepted by YamlDotNet. It avoids an extra host dependency.
    artifacts, manifest_path = run_plan(plan,evidence)
    screen = (artifacts/'stages/ranges/screen.bin').read_bytes()
    decoded = native_screen_text(screen)
    (evidence/'screen-decoded.txt').write_text(decoded+'\n')
    assert 'SuperEditor' in decoded
    assert ('REU required' if case == 'no-reu' else 'probe ready.') in decoded
    assert (artifacts/'stages/ranges/shim.bin').read_bytes() == canary
    pngs = list((artifacts/'screens').glob(f'{case}-screen.png'))
    assert pngs, 'runner returned no actual screenshot'
    for png in pngs:
        assert png.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and png.stat().st_size > 2000
    reu_equal = None
    if case != 'no-reu':
        # Locate raw images via their index instead of depending on names.
        indexes = list((artifacts/'dumps').glob('*.json'))
        bank_images = {}
        for index in indexes:
            data = json.loads(index.read_text(encoding='utf-8-sig'))
            for chunk in data.get('chunks', []):
                if chunk.get('source') == 'vice_native_reu_image':
                    source = index.parent/Path(chunk['file']).name
                    tag = 'before' if 'before' in index.name else 'after' if 'after' in index.name else None
                    if tag:
                        bank_images[tag] = source
        assert set(bank_images) == {'before', 'after'}, f'cannot find full REU images in {indexes}'
        reu_equal = (hashlib.sha256(bank_images['before'].read_bytes()).hexdigest() ==
                     hashlib.sha256(bank_images['after'].read_bytes()).hexdigest())
        assert reu_equal, 'REU probe did not restore original contents'
    summary = dict(status='passed', case=case, evidence=str(evidence),
                   input='KERNAL PETSCII queue', disk_boot=True, shim_bytes_verified=1024,
                   reu_banks=expected_banks, reu_restored=reu_equal,
                   screenshots=[str(p) for p in pngs], harness_manifest=str(manifest_path))
    (evidence/'result.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=['boot', 'no-reu', 'small-reu', 'all'], default='boot')
    parser.add_argument('--visible', action='store_true')
    args = parser.parse_args()
    build = subprocess.run(['dotnet', 'build', str(PROJECT), '--no-restore', '--nologo'],
                           capture_output=True, text=True, timeout=120)
    if build.returncode:
        raise RuntimeError(build.stdout+build.stderr)
    for case in (['boot', 'no-reu', 'small-reu'] if args.suite == 'all' else [args.suite]):
        run_case(case, args)
