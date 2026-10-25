"""Native VICE stopwatch timings through the existing .NET automation harness.

No product source is patched. A cold-only $0E00 probe calls real services with
IRQs enabled; host key arrival and queue-dispatch delay are outside this scope.
--prepare writes plans only; --run requires the delegated exclusive VICE slot.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import binascii
import hashlib
import json
import re
import shutil
import statistics
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from cpu_editor import NAMES
from vice_config import PROJECT, step
from vice_plan import run_plan
from redraw_model import source40, verify_screen
from png_pixels import read_png
from overlays import HEADER

SCRATCH = 0x0E00
SOURCES = {
    'monitor': 'https://vice-emu.sourceforge.io/vice_12.html',
    'resources': 'https://vice-emu.sourceforge.io/vice_7.html',
    'vic_model_constants': 'https://raw.githubusercontent.com/VICE-Team/svn-mirror/main/vice/src/vicii.h',
}


def word(value):
    return value.to_bytes(2, 'little')


def stub(symbols, kind):
    """Return self-contained probe bytes and the exact pre-NOP stop address."""
    leave = bytes([0xEA, 0x4C]) + word(symbols['se_idle'])
    if kind == 'calibration':
        code = bytes([0xEA] * 8)
    elif kind == 'render':
        code = bytes([0x20]) + word(symbols['se_editor_render'])
    elif kind == 'input':
        code = (bytes([0x20]) + word(symbols['se_editor_input']) +
                bytes([0x20]) + word(symbols['se_editor_render']))
    elif kind == 'drain':
        code = (bytes([0x20]) + word(symbols['se_editor_input']) +
                bytes([0x20]) + word(symbols['se_editor_service']) +
                bytes([0xAD]) + word(symbols['se_e_job']) + bytes([0xD0, 0xF8]) +
                bytes([0x20]) + word(symbols['se_editor_render']))
    else:
        raise ValueError(kind)
    return code + leave, SCRATCH + len(code)


def extract_cycles(text):
    matches = re.findall(r'Stopwatch:\s*([0-9]+)', text, flags=re.I)
    assert len(matches) == 1, ('missing/ambiguous stopwatch', text)
    value = int(matches[0])
    assert 0 < value < 50_000_000, ('implausible stopwatch interval', value)
    return value


def build_plan(evidence, report, standard, vic_model, samples, probe):
    symbols = report['symbols']
    steps, cases = [], []
    canary = bytes((i * 73 + 29) & 255 for i in range(1024))
    disk = evidence / 'working.d81'
    shutil.copyfile(ROOT / 'build/supereditor.d81', disk)
    keys = 0

    def raw(ident, command):
        if '\n' in command:
            script = evidence / f'monitor-{ident}.mon'
            script.write_text(command + '\n')
            command = f'playback "{script}"'
        steps.append(step(ident, 'monitor.command', command='raw: ' + command))

    def memory(ident, name, value, width=1):
        at = symbols[name] if isinstance(name, str) else name
        data = value if isinstance(value, bytes) else value.to_bytes(width, 'little')
        item = step(ident, 'assert.memory', start=at, end=at+len(data)-1,
                    equals_hex=data.hex(' '))
        item['retry'] = dict(max_attempts=30, backoff_ms=30, jitter=False)
        steps.append(item)

    def idle(ident):
        for name in ['se_e_job', 'se_e_error', 'se_e_ui', 'se_e_draw_busy',
                     'se_e_redraw', 'se_doc_read_locks', 'se_b_phase', 'se_clip_busy']:
            memory(ident + '_' + name, name, 0)

    def send(ident, data):
        nonlocal keys
        steps.append(step(ident, 'input.sequence', keys=list(data),
                          inter_key_delay_s=0.04, post_delay_s=0.08))
        keys += len(data)
        memory(ident + '_consumed', 'se_key_sequence', keys, 2)
        idle(ident)

    def measure(ident, category, kind, *, key=None, forced_full=False,
                expected_path=None, expected_rows=None):
        code, stop = stub(symbols, kind)
        timing_log = evidence / f'monitor-timing-{ident}.log'
        preparation = [f'logname "{timing_log}"', 'log on',
                       f'> {SCRATCH:04x} ' + code.hex(' ')]
        if key is not None:
            preparation += [f'> {symbols["se_e_key"]:04x} {key:02x}',
                            f'> {symbols["se_e_mods"]:04x} 00']
        if forced_full:
            preparation.append(f'> {symbols["se_r_valid"]:04x} 00')
        flags = 0x24 if kind == 'calibration' else 0x20
        preparation += [f'registers PC=${SCRATCH:04x}, SP=$ff, FL=${flags:02x}',
                        'registers', 'stopwatch reset', f'until ${stop:04x}',
                        'stopwatch', 'registers', 'log off']
        # One official playback file, with no binary capture command between
        # reset and stop. The native monitor log survives the harness's short
        # text-drain observation window for long cold-admission operations.
        raw(ident, '\n'.join(preparation))
        ranges = [dict(label='state', start=0xC000, end=0xC5FF),
                  dict(label='metadata', start=0x9A00, end=0x9FFF),
                  dict(label='view', start=symbols['se_editor_state_start'],
                       end=symbols['se_editor_state_end']-1),
                  dict(label='matrix', start=0x4000, end=0x43E7),
                  dict(label='colors', start=0xD800, end=0xDBE7)]
        steps.append(step(ident + '_state', 'dump.memory_ranges', ranges=ranges))
        if kind != 'calibration':
            idle(ident + '_idle')
        cases.append(dict(id=ident, category=category, kind=kind,
                          stop_pc=stop, flags=flags, key=key,
                          expected_path=expected_path, expected_rows=expected_rows,
                          jsr_rts_probe_overhead_cycles=12 if kind == 'render' else
                          24 if kind == 'input' else None))

    steps += [step('launch', 'vice.launch', kill_stale=False),
              step('basic', 'screen.wait_contains', text='READY.', wait_timeout_s=30)]
    raw('video_set', f'resourceset "MachineVideoStandard" "{standard}"\n'
                    f'resourceset "VICIIModel" "{vic_model}"\n'
                    f'resourceset "MachinePowerFrequency" "{50 if standard == 1 else 60}"')
    raw('video_confirm', 'resourceget "MachineVideoStandard"\nresourceget "VICIIModel"\n'
                         'resourceget "MachinePowerFrequency"\nwarp\n'
                         'resourceget "Drive8TrueEmulation"')
    raw('reu_small', 'resourceset "REU" "0"\nresourceset "REUsize" "512"\nresourceset "REU" "1"')
    steps += [step('shim_seed', 'memory.write', start=0xC600, bytes_hex=canary.hex(' ')),
              step('boot', 'input.sequence', keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),
                   inter_key_delay_s=0.04, post_delay_s=0.15)]
    memory('ready', 'se_status', 1)
    memory('first_draw', 'se_e_draw_sequence', 1, 2)
    idle('initial')
    steps.append(step('initial_reu', 'dump.reu', mode='full', stage_tag='initial_reu'))
    for i in range(3):
        measure(f'calibration_{i}', 'eight_nop_irq_masked', 'calibration')
    for i in range(samples):
        measure(f'cursor_{i}', 'cached_cursor', 'input', key=0x1D if i % 2 == 0 else 0x9D,
                expected_path=1, expected_rows=0)
    if not probe:
        for i in range(samples):
            measure(f'typing_{i}', 'cached_typing_dirty_row', 'input', key=0xD8,
                    expected_path=2, expected_rows=1)
        for i in range(samples):
            measure(f'full_{i}', 'forced_full_render', 'render', forced_full=True,
                    expected_path=0, expected_rows=22)
        # Flush an actual pending edit, including the resident service slices,
        # history C4/R2/C6 admission, and cold R1 restoration in the measurement.
        measure('flush_left', 'pending_flush_and_left', 'drain', key=0x9D,
                expected_path=1, expected_rows=0)
        for i in range(samples):
            send(f'menu_cold_{i}', bytes([0x85, 3]))
            measure(f'cold_c6_{i}', 'cold_c6_cursor', 'input',
                    key=0x1D if i % 2 == 0 else 0x9D,
                    expected_path=1, expected_rows=0)
    memory('shim_intact', 0xC600, canary)
    memory('channels_closed', 0x98, 0)
    raw('final_native', f'screenshot "{evidence}/native-final.png" 2')
    steps.append(step('final_ram', 'dump.memory_ranges', ranges=[
        dict(label='state', start=0xC000, end=0xC5FF),
        dict(label='view', start=symbols['se_editor_state_start'], end=symbols['se_editor_state_end']-1),
        dict(label='hot', start=0x9200, end=0x99FF),
        dict(label='metadata', start=0x9A00, end=0x9FFF),
        dict(label='matrix', start=0x4000, end=0x43E7),
        dict(label='colors', start=0xD800, end=0xDBE7),
        dict(label='font', start=0x4800, end=0x4FFF)]))
    steps.append(step('final_reu', 'dump.reu', mode='full', stage_tag='final_reu'))
    plan = dict(version=1, kind='vice_task_plan',
        plan_id=f'supereditor-timing-{standard}-{evidence.name}', run_mode='gui_vice',
        global_defaults=dict(monitor_host='127.0.0.1', monitor_port_start=6580,
            monitor_port_span=30, retry_policy=dict(max_attempts=1, backoff_ms=100, jitter=False),
            timeouts=dict(launch_s=30, step_s=60, read_s=2),
            artifact_policy=dict(capture_screen=False, capture_state=False, capture_dump=False),
            vice=dict(disk8=str(disk), drive8_type=1581, drive9_enabled=False,
                autostart_enabled=False, true_drive=False, close_vice=True,
                headless=True, speed_percent=100)), steps=steps)
    return plan, cases


def evaluate(evidence, artifacts, report, cases, standard, vic_model):
    symbols = report['symbols']
    rows = []
    resources = (artifacts / 'stages/video_confirm/monitor_command.txt').read_text(encoding='utf-8-sig')
    for name, value in [('MachineVideoStandard', standard), ('VICIIModel', vic_model)]:
        assert re.search(rf'{name}[^\r\n]*\b{value}\b', resources), (name, resources)
    assert re.search(r'warp[^\r\n]*\bon\b', resources, flags=re.I), resources
    assert 'Unknown resource' not in resources, resources

    def get(folder, name, width=1):
        at = symbols[name]
        if 0xC000 <= at < 0xC600:
            data = (folder / 'state.bin').read_bytes()
            offset = at - 0xC000
        elif 0x9A00 <= at < 0xA000:
            data = (folder / 'metadata.bin').read_bytes()
            offset = at - 0x9A00
        elif symbols['se_editor_state_start'] <= at < symbols['se_editor_state_end']:
            data = (folder / 'view.bin').read_bytes()
            offset = at - symbols['se_editor_state_start']
        else:
            raise AssertionError(('uncaptured symbol range', name, hex(at)))
        assert len(data[offset:offset+width]) == width, ('short state capture', name)
        return int.from_bytes(data[offset:offset+width], 'little')

    for case in cases:
        text = (evidence / f'monitor-timing-{case["id"]}.log').read_text(encoding='utf-8-sig')
        cycles = extract_cycles(text)
        stop_hex = f'{case["stop_pc"]:04x}'
        assert re.search(r'(?:\.C:|\.;)\s*' + stop_hex, text, flags=re.I), ('exact stop PC', case, text)
        phases = re.findall(r'(?m)^\.;[0-9a-f]{4}\s+(?:[0-9a-f]{2}\s+){6}'
                            r'[01]{8}\s+(\d+)\s+(\d+)\s+(\d+)', text, flags=re.I)
        assert len(phases) == 2, ('start/end raster register records', case, text)
        assert int(phases[-1][2]) == cycles
        folder = artifacts / f'stages/{case["id"]}_state'
        item = dict(case, emulated_cycles=cycles,
                    start_raster_line=int(phases[0][0]), start_raster_cycle=int(phases[0][1]),
                    end_raster_line=int(phases[1][0]), end_raster_cycle=int(phases[1][1]),
                    path=get(folder, 'se_r_path'), rows=get(folder, 'se_r_rows'),
                    cells=get(folder, 'se_r_cells', 2),
                    caret=get(folder, 'se_hot_caret', 3),
                    overlay_loads=get(folder, 'se_overlay_loads', 2),
                    dma_calls=get(folder, 'se_reu_dma_calls', 2),
                    dma_bytes=get(folder, 'se_reu_dma_bytes', 3))
        if case['kind'] == 'calibration':
            assert 16 <= cycles <= 64, ('calibration NOP cycles/VIC stretch', cycles, text)
        else:
            assert item['path'] == case['expected_path'] and item['rows'] == case['expected_rows'], item
            assert get(folder, 'se_e_job') == get(folder, 'se_e_error') == 0, item
            if item['path'] == 1:
                assert item['cells'] <= 2, item
        rows.append(item)
    categories = {}
    for name in sorted({item['category'] for item in rows}):
        values = [item['emulated_cycles'] for item in rows if item['category'] == name]
        categories[name] = dict(samples=len(values), minimum=min(values), maximum=max(values),
                                median=statistics.median(values), emulated_cycles=values)
    final = artifacts/'stages/final_ram'
    prg = (evidence/'editor.prg').read_bytes()
    sample = prg[2+symbols['sample']-0x801:2+symbols['sample_end']-0x801]
    cursor_cases = [case for case in cases if case['category'] == 'cached_cursor']
    typing_cases = [case for case in cases if case['category'] == 'cached_typing_dirty_row']
    cursor = len(cursor_cases) % 2
    source = sample[:cursor] + bytes([0xD8])*len(typing_cases) + sample[cursor:]
    if typing_cases:
        cursor += len(typing_cases)-1
        cursor += sum(1 if case['key'] == 0x1D else -1 for case in cases
                      if case['category'] == 'cold_c6_cursor')
    assert get(final, 'se_hot_caret', 3) == cursor
    assert get(final, 'se_hot_pending') == 0
    assert get(final, 'se_hot_base', 3) == 0
    assert get(final, 'se_doc_length', 3) == len(source)
    hot = (final/'hot.bin').read_bytes()
    span = hot[:get(final, 'se_hot_left', 2)] + hot[get(final, 'se_hot_right', 2):]
    assert span == source, ('native hot source differs', len(span), len(source))
    expected = source40(source, get(final, 'se_v_top', 3), cursor,
                        pending=False, dirty=bool(get(final, 'se_h_dirty')))
    matrix, colors = (final/'matrix.bin').read_bytes(), (final/'colors.bin').read_bytes()
    verify_screen(matrix, colors, expected, tag='native timing final screen')
    images = {}
    for index in (artifacts/'dumps').glob('*.json'):
        for chunk in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks', []):
            if chunk.get('source') == 'vice_native_reu_image':
                key = 'initial' if 'initial_reu' in index.name else 'final' if 'final_reu' in index.name else None
                assert key is not None, index
                images[key] = (index.parent/Path(chunk['file']).name).read_bytes()
    assert set(images)=={'initial','final'}
    before, image = images['initial'], images['final']
    assert len(before)==len(image)==512*1024
    for i, name in enumerate(NAMES):
        payload = (evidence/(name+'.seo')).read_bytes()[HEADER:]
        assert image[65536+i*4096:65536+i*4096+len(payload)] == payload, ('actual asset', name)
    roots = (final/'metadata.bin').read_bytes()
    roots_at = symbols['se_doc_roots']-0x9A00
    rebuilt = bytearray()
    for i in range(get(final, 'se_doc_root_count')):
        record = roots[roots_at+i*8:roots_at+(i+1)*8]
        leaf = 2*65536 + record[0]*1024
        for piece in range(record[1]):
            descriptor = image[leaf+piece*16:leaf+(piece+1)*16]
            identity = descriptor[0]
            assert identity in (1, 2) and descriptor[1:3] == b'\x01\x00'
            offset, length = int.from_bytes(descriptor[3:6], 'little'), int.from_bytes(descriptor[6:9], 'little')
            physical = 3 if identity == 1 else 4
            rebuilt += image[physical*65536+offset:physical*65536+offset+length]
    assert rebuilt == source, 'published REU source reconstruction'
    journal_bytes = 0
    untouched_reu_bytes = len(image)
    if typing_cases:
        inserted = len(typing_cases);position = len(cursor_cases)%2
        body = bytes([2,1,0])+bytes(3)+inserted.to_bytes(3,'little')+(75).to_bytes(2,'little')
        header = bytearray(64);header[:6]=b'SEH1\x01\x01';header[6:8]=(75).to_bytes(2,'little')
        header[8:12]=(1).to_bytes(4,'little');header[12:16]=(2).to_bytes(4,'little')
        header[16:21]=bytes([1,1,0,1,0]);header[21:26]=bytes([2,1,0,1,0])
        header[26:29]=position.to_bytes(3,'little');header[32:35]=inserted.to_bytes(3,'little')
        header[37:39]=(1).to_bytes(2,'little');header[39:42]=position.to_bytes(3,'little')
        header[42:45]=(position+inserted).to_bytes(3,'little');header[45]=1
        header[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little')
        header[58:60]=binascii.crc_hqx(header[:58]+header[60:],0xFFFF).to_bytes(2,'little')
        journal=bytes(header)+body;journal_bytes=len(journal)
        assert image[5*65536:5*65536+75]==journal,'exact active typing journal/CRCs/carets'
        assert image[5*65536+0xB000:5*65536+0xB000+75]==journal,'exact staged typing journal'
        assert get(final,'se_h_end',2)==75 and get(final,'se_h_cursor',2)==75
        assert get(final,'se_h_current',4)==2 and get(final,'se_h_saved',4)==1
        assert image[4*65536:4*65536+inserted]==bytes([0xD8])*inserted
        owned=[(2*65536,2048),(4*65536,inserted),(5*65536,75),(5*65536+0xB000,75)]
        at=0
        for start,length in owned:
            assert image[at:start]==before[at:start],('unowned REU bytes changed',hex(at),hex(start))
            at=start+length
        assert image[at:]==before[at:],'unowned REU tail changed'
        untouched_reu_bytes=len(image)-sum(length for start,length in owned)
        (evidence/'expected-journal.bin').write_bytes(journal)
    else:assert image==before,'cursor-only probe changed REU'
    w, h, pixels = read_png(evidence/'native-final.png')
    font = (final/'font.bin').read_bytes()
    background = pixels[0]
    def bit_at(row, col, y, x):
        return bool(font[matrix[row*40+col]*8+y] & (128 >> x))
    candidates = []
    for y0 in range(h-200+1):
        for x0 in range(w-320+1):
            if all((pixels[(y0+y)*w+x0+col*8+x] != background) == bit_at(0, col, y, x)
                   for col in range(1, 11) for y in range(8) for x in range(8)):
                candidates.append((x0, y0))
    viewports = []
    for x0, y0 in candidates:
        if all((pixels[(y0+row*8+y)*w+x0+col*8+x] != background) == bit_at(row, col, y, x)
               for row in range(25) for col in range(40) for y in range(8) for x in range(8)):
            viewports.append((x0, y0))
    assert len(viewports) == 1, ('native VIC viewport/full glyph match', w, h, viewports)
    result = dict(status='passed', prg_sha256=report['sha256'],
        timing_harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        resident_binding=report['resident_binding']['digest'],
        overlay_sha256={name: hashlib.sha256((evidence/(name+'.seo')).read_bytes()).hexdigest()
                        for name in NAMES},
        machine_video_standard=standard, vicii_model=vic_model,
        configured_video='PAL6569' if standard == 1 else 'NTSC6567',
        reu_kib=512, warp=True, true_drive=False, drive_traps=True,
        irq_enabled_except_calibration=True, reserved_shim_bytes_checked=1024,
        cold_probe_address=SCRATCH, measurements=rows, categories=categories,
        exact_active_and_staged_journal_bytes=journal_bytes, untouched_reu_bytes_checked=untouched_reu_bytes, reu_metadata_leaf_slots_bounded=2,
        native_source_bytes_reconstructed=len(source), source_sha256=hashlib.sha256(source).hexdigest(),
        full_native_screen_oracle_cells=1000, native_vic_glyph_pixels_checked=64000,
        native_image_dimensions=[w, h], native_viewport=viewports[0],
        monitor_resource_confirmation=resources, primary_references=SOURCES,
        limitations='Instruction-entry service timings, not physical key-to-pixel latency. Observed starts are near raster line0; these samples do not cover every IRQ/badline phase or establish worst-case latency. Stopwatch includes stub JSR/RTS overhead and emulated VIC/IRQ/REU effects. Warp affects host throughput. Frames/milliseconds are not inferred from unverified timing geometry.')
    (evidence/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--samples', type=int, default=5)
    parser.add_argument('--standard', choices=['pal', 'ntsc', 'both'], default='both')
    args = parser.parse_args()
    assert 1 <= args.samples <= 12
    report = json.loads((ROOT/'build/editor-report.json').read_text())
    if args.run:
        build = subprocess.run(['dotnet', 'build', str(PROJECT), '--no-restore', '--nologo'],
                               capture_output=True, text=True, timeout=120)
        assert build.returncode == 0, build.stdout+build.stderr
    profiles = [(1, 0), (2, 3)]
    for standard, model in profiles:
        if args.standard != 'both' and args.standard != ('pal' if standard == 1 else 'ntsc'):
            continue
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        evidence = ROOT/'agentsworking/evidence/M3'/f'{stamp}-timing-{standard}'
        evidence.mkdir(parents=True)
        for name in ['editor.prg', 'editor-report.json', 'editor-bindings.json',
                     'editor.map', 'editor.lbl', 'disk-manifest.json']:
            shutil.copyfile(ROOT/'build'/name, evidence/name)
        for name in NAMES:
            shutil.copyfile(ROOT/f'build/overlays/{name}.seo', evidence/(name+'.seo'))
        assert hashlib.sha256((evidence/'editor.prg').read_bytes()).hexdigest()==report['sha256']
        for name in NAMES:
            data=(evidence/(name+'.seo')).read_bytes()
            assert data[20:36]==data[36:52]==bytes.fromhex(report['resident_binding']['digest']),name
        for name in ['tests/test_redraw_timing_vice.py','tools/redraw_model.py','tools/vice_plan.py','tools/vice_config.py','tools/png_pixels.py']:
            dest=evidence/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        with zipfile.ZipFile(evidence/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for directory in ['src','cfg']:
                for path in (ROOT/directory).rglob('*'):
                    if path.is_file():archive.write(path,path.relative_to(ROOT))
            archive.write(ROOT/'Makefile','Makefile')
        plan, cases = build_plan(evidence, report, standard, model, args.samples, args.probe)
        (evidence/'plan.yaml').write_text(json.dumps(plan, indent=2)+'\n')
        (evidence/'measurement-cases.json').write_text(json.dumps(cases, indent=2)+'\n')
        print(f'Prepared {evidence}', flush=True)
        if args.run:
            artifacts, manifest = run_plan(plan, evidence)
            try:
                evaluate(evidence, artifacts, report, cases, standard, model)
            except Exception as error:
                (evidence/'result.json').write_text(json.dumps(dict(status='failed',
                    error=repr(error), prg_sha256=report['sha256'],
                    harness_manifest=str(manifest)), indent=2)+'\n')
                raise


if __name__ == '__main__':
    main()
