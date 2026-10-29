"""Actual cold62 repeated edit/flush/repaint versus committed60, native PAL.

Real ROM File/Open and IRQ setup. The disclosed stopwatch probe calls public
input, public WRAP_OFF, then the real scheduler. No source/cache state is seeded.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import inspect
import json
import re
import shutil
import socket
import subprocess
import tempfile
import textwrap
import zipfile
import test_geos_plain_typing_registered_vice as local
import test_cache_splice as splice
from supermark_model import blocks
from closed_runtime_copy import run_with_closed_links
from d81_image import D81Image
from cache_job_build import editor_pair_index

ROOT = local.ROOT
timing = local.timing
DATA = timing.native.live.grid.native_text(
    'Intro\r:::basic\r10 PRINT "Hi":REM '+'x'*8000+
    '\r:::\rMiddle ordinary line.\rTail.')
AT = DATA.index(timing.native.live.grid.native_text('ordinary'))+3
NAME = b'REBASE8K'


def free_ports():
    for port in (8500, *range(8600, 8640)):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))


def labels(p):
    return {n: int(a, 16) for a, n in
            re.findall(r'al ([0-9a-fA-F]+) \.(\w+)', p.read_text())}


class Plan(local.Plan):
    pass


def freeze(base, variant):
    identity = json.loads((base/'freeze.json').read_text())
    assert len(identity['names']) == (62 if variant == 'candidate' else 60)
    assert ('parse' in identity['names']) == (variant == 'candidate')
    e = timing.freeze(base, 'pal')
    target = ROOT/'agentsworking/evidence/M8'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+
        '-rebase-'+variant+'-native')
    e.rename(target)
    e = target
    (e/'rebase8k.seq').write_bytes(DATA)
    p = subprocess.run(['c1541', '-attach', str(e/'working.d81'), '-write',
                        str(e/'rebase8k.seq'), 'rebase8k,s'], capture_output=True)
    (e/'rebase-package.log').write_bytes(p.stdout+p.stderr)
    assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(NAME, kind=1).data == DATA
    shutil.copy2(e/'working.d81', e/'rebase-initial.d81')
    # Only these byte-matched symbol groups drive conditional parser traces.
    # Other stages are independently reassembled by the full stack gate.
    for name in ('geossema', 'geoslex', 'parse'):
        if name not in identity['names']:
            continue
        shutil.copy2(base/f'build/overlays/{name}.lbl', e/(name+'.lbl'))
        assert (base/f'build/overlays/{name}.bin').read_bytes() == (e/(name+'.seo')).read_bytes()[36:]
    (e/'variant.json').write_text(json.dumps(dict(label=variant, source=str(base)), indent=2)+'\n')
    return e


def scenario(e, variant, repeats):
    source = inspect.getsource(timing.Plan.measure)
    needle = "code=bytes((0x20,target&255,target>>8,0x4C,self.s['se_idle']&255,self.s['se_idle']>>8))"
    assert source.count(needle) == 1
    source = source.replace(needle,
        "command=self.s['se_editor_command'];code=bytes((0x20,target&255,target>>8,0xA9,77,0x20,command&255,command>>8,0x4C,self.s['se_idle']&255,self.s['se_idle']>>8))")
    needle = "        commands += [\n            f'break exec ${self.idle_pc:04x}"
    assert source.count(needle) == 1
    source = source.replace(needle, "        commands += self.parser_traces\n"+needle)
    source = textwrap.dedent(source)
    (e/'edit-flush-measure.py').write_text(source)
    ns = dict(vars(timing))
    exec(compile(source, str(e/'edit-flush-measure.py'), 'exec'), ns)
    Plan.measure = ns['measure']
    n = Plan(e, json.loads((e/'editor-report.json').read_text()), 1, 0)
    n.cost_profile = True
    names = json.loads((e/'freeze.json').read_text())['catalog']
    def runtime_index(name):
        image=(e/(name+'.seo')).read_bytes()
        return editor_pair_index(image[5],image[6]) if 'catalog_index' in n.s else names.index(name)
    n.parser_points = []
    for name, ident in (('geossema', 24), ('geoslex', 25), ('parse', 41)):
        if name not in names:
            continue
        syms = labels(e/(name+'.lbl'))
        for fn in ('se_sm_init', 'se_sm_feed', 'se_sl_init', 'se_sl_feed'):
            if fn in syms:
                n.parser_points.append(dict(name=name+':'+fn, pc=syms[fn],
                                            slot=runtime_index(name)+1, id=ident))
    n.parser_traces = [f'trace exec ${p["pc"]:04x} if @cpu:${n.s["se_overlay_active"]+1:04x} == ${p["slot"]:02x}'
                       for p in n.parser_points]
    n.boot()
    n.open('open_rebase8k', NAME)
    n.typed('initial_markdown', 'syntax markdown')
    n.typed('initial_geos', 'mode hires')
    n.typed('initial_nowrap', 'wrap off')
    n.typed('retained_full', 'syntax full')
    n.memory('full_caps', 'se_render_caps', 3)
    n.typed('target_line', 'goto 5')
    n.send('target_column', b'\x1d'*10)
    n.memory('initial_caret', 'se_hot_caret', AT, 3)
    n.memory('initial_empty_events', 'se_bc_count', 0)
    data = DATA
    for k in range(repeats):
        data = data[:AT+k]+timing.native.live.grid.native_text('Q')+data[AT+k:]
        tag = 'repeat-'+str(k+1)
        n.measure(tag, data, 3, key=timing.native.live.grid.native_text('Q')[0],
                  category='public-edit-flush-repaint')
        n.measurements[-1].update(repeat=k+1, variant=variant)
        n.memory(tag+'_pending', 'se_hot_pending', 0)
        n.memory(tag+'_caret', 'se_hot_caret', AT+k+1, 3)
        n.memory(tag+'_history', 'se_h_current', k+2, 4)
        if variant == 'candidate':
            n.memory(tag+'_retired_events', 'se_bc_count', 0)
    (n.out/'parser-points.json').write_text(json.dumps(n.parser_points, indent=2)+'\n')
    return n


def evaluate(n, variant):
    original, catalog = timing.semantic.expected, timing.FontCatalog
    timing.semantic.expected = local.presentation.expected_geos
    timing.FontCatalog = lambda path, native: local.preview.pack_catalog((n.e/'font-pack.bin').read_bytes(), native)
    try:
        result = timing.evaluate(n)
    finally:
        timing.semantic.expected, timing.FontCatalog = original, catalog
    images = timing.native.live.grid.reu_images(n.out/'run')
    frames = []
    parser_points = json.loads((n.out/'parser-points.json').read_text())
    for item in result['measurements']:
        tag = item['id']
        ram = (n.out/'captures'/(tag+'-ram.bin')).read_bytes()
        f = local.Captured(n.s, ram, (n.out/'captures'/(tag+'-colors.bin')).read_bytes(), n.e)
        data = bytes.fromhex(item['source'])
        assert f.get('se_mode', 1) == 3 and f.get('se_render_caps', 1) == 3
        assert f.get('se_hot_pending', 1) == 0 and f.get('se_hot_caret') == AT+item['repeat']
        assert f.get('se_h_current', 4) == item['repeat']+1 and f.get('se_h_saved', 4) == 1
        assert f.get('se_clip_length') == 0 and f.get('se_sel_mark', 1) == 0
        assert f.read(n.s['se_editor_settings'], 64) == (n.e/'editor-defaults.bin').read_bytes()
        text = (n.out/('stopwatch-'+tag+'.log')).read_text(encoding='utf-8-sig')
        counts = {p['name']: len(re.findall(r'(?mi)^\.C:'+format(p['pc'], '04x')+r'\s', text))
                  for p in parser_points}
        if variant == 'candidate':
            assert counts.get('parse:se_sm_feed', 0) > 0
            assert counts.get('geossema:se_sm_feed', 0) == counts.get('geoslex:se_sl_feed', 0) == 0
            assert f.get('se_bc_count', 1) == 0
            token = f.read(n.s['se_bc_arena'], 5)
            handle = ram[n.s['object_extents']+token[0]*16]
            bank = ram[n.s['se_reu_map']+handle]
            assert handle and bank and ram[n.s['se_reu_logical_owner']+handle] == ram[n.s['se_reu_physical_owner']+bank] == 0x53
            raw = images[tag][bank*65536:(bank+1)*65536]
            selected = splice.roots(raw)[2]
            assert selected[31] == 5 and selected[104] == (14 if item['repeat'] & 1 else 12)
            assert selected[30] == item['repeat']*2
            expected = blocks(data)
            assert int.from_bytes(selected[112:115], 'little') == len(expected)
            for j, b in enumerate(expected):
                cr = raw[selected[104]*4096+64+j*96:selected[104]*4096+160+j*96]
                a = int.from_bytes(cr[16:19], 'little')
                assert (cr[3], a, a+int.from_bytes(cr[19:22], 'little'),
                        a+int.from_bytes(cr[22:25], 'little'), cr[69], cr[70]) == tuple(
                            b[k] for k in ('kind', 'start', 'end', 'body', 'language', 'level'))
                assert int.from_bytes(cr[12:16], 'little') == f.get('se_bc_ticket', 4)
        else:
            assert counts.get('geossema:se_sm_feed', 0) > 0
        frames.append(dict(id=tag, cycles=item['emulated_cycles'],
                           first_publish=item['first_publish_cycles'],
                           loads=item['counter_deltas']['se_overlay_loads'],
                           parser_entries=counts,
                           png_sha256=hashlib.sha256((n.out/('native-'+tag+'.png')).read_bytes()).hexdigest()))
    assert (n.e/'working.d81').read_bytes() == (n.e/'rebase-initial.d81').read_bytes()
    summary = dict(status='PASS', variant=variant, identity=result['identity'],
                   frames=frames, pixels=len(frames)*64000, scope=__doc__,
                   source_graphs_and_sealed_assets='checked by complete native timing evaluator',
                   limits='Mutable source/history/cache edits; no whole-REU read-only claim. CPU gate separately checks exact COW/DMA spans.',
                   visual_review='pending')
    (n.out/'rebase-result.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def execute(base, variant, repeats=4):
    free_ports()
    e = freeze(base, variant)
    n = scenario(e, variant, repeats)
    p = n.plan()
    assert len({s['id'] for s in p['steps']}) == len(p['steps'])
    (n.out/'measurements.json').write_text(json.dumps(n.measurements, indent=2)+'\n')
    (n.out/'plan.yaml').write_text(json.dumps(p, indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests', 'tools'):
            for q in sorted((ROOT/folder).glob('*.py')):
                z.write(q, q.relative_to(ROOT))
    project = timing.native.live.grid.synchronous_project(n.out)
    local.vice_plan.PROJECT = project
    build = subprocess.run(['dotnet', 'build', str(project), '--nologo'], capture_output=True, text=True, timeout=120)
    (n.out/'dotnet-build.log').write_text(build.stdout+build.stderr)
    assert not build.returncode
    print('REBASE_NATIVE', e, 'variant', variant, 'steps', len(n.steps), 'frames', repeats, flush=True)
    run_with_closed_links(local.capacity.run_owned_plan, p, n.out, timeout=900)
    free_ports()
    return e, evaluate(n, variant)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--variant', choices=['control', 'candidate'], required=True)
    p.add_argument('--repeats', type=int, default=4)
    a = p.parse_args()
    execute(a.fixture.resolve(), a.variant, a.repeats)
