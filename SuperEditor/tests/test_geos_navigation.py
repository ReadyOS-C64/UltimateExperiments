"""Private actual C23/C20 navigation, canonical independent proportional oracle.

No shared make/native. Root job12 is modeled solely by sequential real overlay
calls; neither maps, parser results nor target source offsets are injected.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, json, re, subprocess, sys
import test_geos_editor as geos
import test_geos_semantic as semantic
from test_geos_glyphs import native
from supermark_model import blocks
from overlays import wrap

ROOT = geos.ROOT
DEFAULT = ROOT/'build/geos-recovery/20261025T022335799891Z/fixture'


def command(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def build(out, base):
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((base/'build/editor-report.json').read_text())
    digest = report['resident_binding']['digest']
    (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2] for i in range(0, 32, 2))+'\n.endmacro\n')
    objects = []
    for name in ['navigation', 'cache']:
        obj = out/(name+'.o')
        command('ca65', '-g', '-I', out, '-I', 'src', '-o', obj, ROOT/f'src/render/geos/{name}.s')
        objects.append(obj)
    command(sys.executable, 'tools/module_bindings.py', '--report', base/'build/editor-report.json', '--output', out/'aliases.s', *objects)
    command('ca65', '-g', '-o', out/'aliases.o', out/'aliases.s')
    command('ld65', '-C', 'cfg/geos-editor-navigation.cfg', '-o', out/'geosnav.bin', '-Ln', out/'geosnav.lbl', '-m', out/'geosnav.map', *objects, out/'aliases.o')
    labels = {n: int(a, 16) for a, n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)', (out/'geosnav.lbl').read_text())}
    payload = (out/'geosnav.bin').read_bytes()
    assert labels['entry'] == 0xB010 and len(payload) <= 4096
    s = report['symbols']
    image = wrap(payload, 1, 23, api=(s['se_overlay_call'], s['se_overlay_frame']), binding_digest=bytes.fromhex(digest))
    (out/'geosnav.seo').write_bytes(image)
    return image, labels


def rows(data, widths):
    events = blocks(data)
    code = bytearray(len(data))
    for e in events:
        if e['kind'] == 5:
            code[e['start']:e['end']] = b'\1'*(e['end']-e['start'])
    advance = [8 if code[i] else widths[native(c)] for i, c in enumerate(data)]
    result = []
    at = 0
    origin = 0
    while True:
        event = next((e for e in events if e['start'] <= at <= e['end']), None)
        mono = event is not None and event['kind'] == 5
        if event is None and at == len(data) and events and events[-1]['fence']:
            mono = True
        if mono:
            origin = (origin+7)&~7
        row = geos.line_break(data, advance, at, 320, 0, 0, -1, 0)
        row['height'] = 8 if mono else 9
        row['origin'] = origin
        result.append((at, row))
        if row['reason'] == 2:
            return result
        assert row['next'] > at
        at = row['next']
        origin += row['height']


def oracle(data, widths, caret, top, cmd, preferred=None):
    lines = rows(data, widths)
    current = next(i for i, (start, r) in enumerate(lines)
                   if start <= caret < r['end'] or caret == r['end'] and r['reason'] in (1, 2))
    start, row = lines[current]
    x = sum((8 if row['height'] == 8 else widths[native(c)]) for c in data[start:caret]) if preferred is None else preferred
    step = 19 if cmd in (38, 39) else 1
    target_index = current if cmd == 47 else max(0, min(len(lines)-1, current+(-step if cmd in (36, 38) else step)))
    if cmd == 38:
        threshold = max(0, row['origin']-171)
        target_index = max(i for i, (_, r) in enumerate(lines) if r['origin'] <= threshold)
    elif cmd == 39:
        threshold = row['origin']+171
        target_index = next((i for i, (_, r) in enumerate(lines) if r['origin'] >= threshold), len(lines)-1)
    start, row = lines[target_index]
    if cmd == 47:
        target = caret
    else:
        candidates = list(range(len(row['maps'])))
        if row['reason'] not in (1, 2):
            candidates = candidates[:-1]
        idx = min(candidates, key=lambda i: (abs(row['maps'][i]-x), -i))
        target = row['first']+idx
    top_index = next((i for i, (s, _) in enumerate(lines) if s == top), None)
    visible = (top_index is not None and top_index <= target_index < top_index+20)
    if cmd in (38, 39) and top_index is not None:
        visible = 0 <= lines[target_index][1]['origin']-lines[top_index][1]['origin'] < 176
    new_top = top if visible else start
    return target, new_top, x


def run(out, previous, focus=False):
    frozen, identity = geos.freeze(out, previous)
    image, labels = build(out/'leaf', frozen)
    semantic_image, _ = semantic.build(out/'semantic', frozen)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    f = geos.Fixture(out, frozen, dll, True)
    f.assets['geosnav-private'] = image
    f.assets['semantic-private'] = semantic_image
    widths = (frozen/'fonts/bsw9-widths.bin').read_bytes()
    cases, feeds = [], []

    def whole_reu():
        data = C.create_string_buffer(16*1024*1024)
        dll.gm_reu(f.m.handle, len(data), data)
        return data.raw

    def invoke(identity_, op):
        f.put('se_overlay_frame', op, 1)
        r, _ = f.fast_call(f.s['se_overlay_call'], a=identity_, x=1)
        return r

    def nav(data, caret, cmd, top=0, preferred=None, cached=True, load=True):
        if load:
            f.position(caret)
        else:
            assert f.get('se_hot_caret') == caret
        f.put('se_v_top', top)
        f.put('se_n_preferred_valid', 0 if preferred is None else 2, 1)
        if preferred is not None:
            f.put('se_l_preferred', preferred)
        f.put('se_e_command', cmd, 1)
        if cmd == 47:
            f.put('se_e_target', caret)
        f.render()
        if not cached:
            f.put('se_gc_width', 0, 1)
        canonical, before = f.canonical(), f.reu()
        want = oracle(data, widths, caret, top, cmd, preferred)
        r = invoke(23, 0)
        count = reads = semantic_calls = 0
        last_id = 23
        while not r.p & 1 and (r.a or last_id in (20, 24)):
            requested, op = f.m.read(0x9135), f.m.read(0x9136)
            last_id = requested
            assert requested in (20, 23, 24)
            if requested in (20, 24):
                scan = int.from_bytes(f.read(0x8D00+38, 3), 'little')
                r = invoke(requested, op)
                if requested == 24:
                    semantic_calls += 1
                if requested == 20 and op == 1:
                    after = int.from_bytes(f.read(0x8D00+38, 3), 'little')
                    assert 0 <= after-scan <= 32, (op, after, scan)
                    reads += 1
                assert not r.p & 1, ('child', requested, op, r.a)
                f.m.write(0x9135, 23)
                f.m.write(0x9136, 1)
            else:
                r = invoke(23, op)
            count += 1
            assert count < len(data)*4+10000, ('nonconvergence', caret, cmd)
        assert not r.p & 1, ('C23', hex(r.a), caret, cmd, f.read(0x9134, 68).hex())
        got = f.get('se_e_target'), f.get('se_v_top')
        assert got == want[:2], (caret, cmd, top, preferred, cached, got, want)
        assert f.canonical() == canonical and f.reu() == before
        assert not any(f.get(n, 1) for n in ('se_f_owner', 'se_doc_read_locks', 'se_fs_owned'))
        assert f.read(0xC600, 1024) == f.shim
        if cmd != 47:
            assert f.get('se_l_preferred') == want[2] and f.get('se_n_preferred_valid', 1) == 2
        cases.append(dict(caret=caret, command=cmd, top=top, preferred=preferred,
                          cached=cached, target=got[0], target_top=got[1], steps=count, reads=reads))
        cases[-1]['semantic_calls'] = semantic_calls
        feeds.append(reads)
        (out/'progress.json').write_text(json.dumps(cases, indent=2)+'\n')

    try:
        data = geos.native_text('Wim wide word\r\ri short\r')+geos.native_text('Mixed word '*30)+b'\r'+geos.native_text('tail\r')*28
        f.source(data)
        f.command(99)
        initial = [] if focus else [(5, 37, None, True), (15, 36, 37, True), (1, 39, 37, True), (len(data), 38, 319, False), (0, 36, None, False), (len(data), 37, 320, False), (35, 47, None, False)]
        for caret, cmd, preferred, cached in initial:
            nav(data, caret, cmd, preferred=preferred, cached=cached)
        for top in ([] if focus else [0, rows(data, widths)[10][0]]):
            for caret in [1, 20, len(data)-5]:
                for cmd in [36, 37, 38, 39]:
                    nav(data, caret, cmd, top=top, preferred=319)
        for data in ([] if focus else [b'', b'\r', geos.native_text('W'*200), b' '*160]):
            f.source(data)
            f.command(99)
            for caret in [0, len(data)]:
                for cmd in [36, 37, 38, 39]:
                    nav(data, caret, cmd, preferred=320)
        mixed = geos.native_text('before\rcurrent\rplain\r:::basic\r'+
                ''.join('10 PRINT "Mixed CASE" '+('X'*65)+'\r' for _ in range(25))+
                ':::\rone\rtwo\rthree\r')
        f.source(mixed)
        f.command(99)
        code = mixed.index(geos.native_text('10 PRINT'))
        for caret, cmd in [(code+5, 37), (code+45, 36), (code+5, 39),
                           (len(mixed), 38), (code+200, 47)]:
            nav(mixed, caret, cmd, preferred=37, cached=False)
        counterexample = geos.native_text('before\rcurrent\rplain\r:::basic\r'+
                ''.join('x\r' for _ in range(14))+':::\rone\rtwo\rthree\r')
        f.source(counterexample)
        f.command(99)
        nav(counterexample, 7, 39, top=7, preferred=0, cached=False)
        # An authenticated far-page arrow must use cached HEIGHT/KIND. It must
        # not parse all preceding source merely to rediscover prose metrics.
        far = geos.native_text('W'*65540+'\rNarrow tail\rNext row\r')
        f.source(far)
        f.command(99)
        starts = rows(far, widths)
        far_top, far_caret = starts[-8][0], starts[-7][0]+5
        for cmd in [36, 37]:
            nav(far, far_caret, cmd, top=far_top, preferred=37)
            assert cases[-1]['semantic_calls'] == 0, 'far cached arrow scanned C24 prefix'
        # Actual reader/source offsets cross64KiB; the pending insertion stays
        # in the gap and must not be flushed by this layout-only controller.
        if not focus:
            data = geos.native_text('W'*65540+'\rNarrow tail\rNext row\r')
            f.source(data)
            f.command(99)
            nav(data, 65537, 36, preferred=319, cached=False)
            f.position(65535)
            f.key(geos.native_text('Q')[0])
            data = data[:65535]+geos.native_text('Q')+data[65535:]
            assert f.get('se_hot_pending', 1)
            nav(data, 65536, 37, preferred=37, cached=False, load=False)
            assert f.get('se_hot_pending', 1)

        # Use a fresh source for scoped cleanup/admission tests. These calls
        # execute the real resident END even after removing the worker image.
        data = geos.native_text('Fault source\rSecond row\r')
        f.source(data)
        f.command(99)
        faults = []
        foreign_reu = whole_reu()

        def acquire():
            f.put('se_e_command', 37, 1)
            f.put('se_gc_width', 0, 1)
            r = invoke(23, 0)
            assert not r.p & 1 and r.a == 1
            for _ in range(10000):
                child, op = f.m.read(0x9135), f.m.read(0x9136)
                if child == 20:
                    assert op == 0
                    break
                r = invoke(child, op)
                assert not r.p & 1
                if child == 24:
                    f.m.write(0x9135, 23)
                    f.m.write(0x9136, 1)
            else:
                raise AssertionError('no C20 admission')
            r = invoke(20, 0)
            assert not r.p & 1 and r.a == 1 and f.m.read(0x912D)

        def remove(id_, slot):
            idx = next(i for i in range(f.s['se_overlay_capacity'])
                       if f.m.read(f.s['se_overlay_ids']+i) == id_
                       and f.m.read(f.s['image_slot']+i) == slot)
            f.m.write(f.s['se_overlay_ids']+idx, 0)
            f.m.write(f.s['se_overlay_active']+slot, 0)
            return idx

        assert not f.call('se_doc_read_acquire').p & 1
        acquire()
        assert f.get('se_doc_read_locks', 1) == 2
        assert not invoke(23, 2).p & 1
        assert f.get('se_doc_read_locks', 1) == 1 and not f.get('se_f_owner', 1)
        assert not f.call('se_doc_read_release').p & 1
        faults.append('cancel releases only counted own lease')
        for id_, slot, op in [(20, 1, 1), (14, 0, 1), (23, 1, 1)]:
            acquire()
            before = f.canonical()
            idx = remove(id_, slot)
            r = invoke(23 if id_ == 23 else 20, op)
            assert r.p & 1 and r.a == 0x17, (id_, r.a)
            assert not f.call('se_geos_cancel').p & 1
            assert not f.get('se_doc_read_locks', 1) and not f.get('se_f_owner', 1)
            assert f.canonical() == before
            f.m.write(f.s['se_overlay_ids']+idx, id_)
            faults.append('missing '+str(id_)+' load-free cleanup')
        f.put('se_e_command', 37, 1)
        f.put('se_gc_width', 0, 1)
        assert not invoke(23, 0).p & 1 and f.m.read(0x9135) == 24
        assert not invoke(24, 0).p & 1 and f.get('se_doc_read_locks', 1) == 1
        idx = remove(24, 1)
        r = invoke(24, 1)
        assert r.p & 1 and r.a == 0x17
        assert not f.call('se_geos_cancel').p & 1
        assert not f.get('se_doc_read_locks', 1) and not f.get('se_f_owner', 1)
        f.m.write(f.s['se_overlay_ids']+idx, 24)
        faults.append('missing semantic C24 uses resident snapshot cleanup')
        acquire()
        revision = f.get('se_r_revision', 4)
        f.put('se_r_revision', revision+1, 4)
        r = invoke(23, 1)
        assert r.p & 1 and r.a == 0x74
        assert not f.call('se_geos_cancel').p & 1
        assert not f.get('se_doc_read_locks', 1)
        faults.append('full source revision change refuses stale target')
        for owner in [1, 2, 3, 255]:
            poison = bytes((i*53+owner) & 255 for i in range(1152))
            f.put('se_f_owner', owner, 1)
            f.m.load(0x8D00, poison)
            for op in [0, 1, 2, 255]:
                r = invoke(23, op)
                assert r.p & 1 and r.a == 0xB2 and f.read(0x8D00, 1152) == poison
        f.put('se_f_owner', 0, 1)
        faults.append('foreign owners preserve entire1152B phase')
        assert whole_reu() == foreign_reu, 'entire16MiB REU changed during fault/cancel/ownership guards'
        result = dict(status='passed', identity=identity, payload_bytes=len(image)-36,
                      new_BSS=0, new_ZP=0, phase_bytes=68, cases=cases,
                      faults=faults,
                      C20_read_slices=sum(feeds), max_source_feeds_per_slice=32,
                      fault_REU_guard_bytes=16*1024*1024,
                      scope='Actual private C23/C20 catalog navigation/controller; parent job12 integration and native proof separate.')
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(dict(status='passed', payload_bytes=len(image)-36, cases=len(cases), reads=sum(feeds), fixture=str(frozen)), indent=2))
        return result
    finally:
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, default=DEFAULT)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--focus', action='store_true', help='mixed geometry/fault gate without historical long matrix')
    args = parser.parse_args()
    out = ROOT/'build/geos-navigation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    if args.build_only:
        image, _ = build(out, args.fixture)
        print('C23 payload', len(image)-36)
    else:
        run(out, args.fixture, args.focus)
