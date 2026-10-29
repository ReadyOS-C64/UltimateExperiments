"""Actual C24/R14 merged-source block query, independent SuperMark oracle.

Private builds only. No GEOS raster, hidden-prefix, editor-UI or native claim.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, json, re, subprocess, sys
import test_geos_editor as geos
from supermark_model import blocks
from supermark_probe import petscii
from overlays import wrap

ROOT = geos.ROOT
F = 0x8B40
DEFAULT = ROOT/'build/geos-recovery/20261025T022335799891Z/fixture'


def command(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def build(out, base):
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((base/'build/editor-report.json').read_text())
    digest = report['resident_binding']['digest']
    (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2] for i in range(0, 32, 2))+'\n.endmacro\n')
    objects = []
    for name, source in [('semantic', 'src/render/geos/semantic.s'), ('block', 'src/supermark/block.s')]:
        obj = out/(name+'.o')
        command('ca65', '-g', '-I', out, '-I', 'src', '-o', obj, source)
        objects.append(obj)
    command(sys.executable, 'tools/module_bindings.py', '--report', base/'build/editor-report.json', '--output', out/'aliases.s', *objects)
    command('ca65', '-g', '-o', out/'aliases.o', out/'aliases.s')
    command('ld65', '-C', 'cfg/geos-editor-semantic.cfg', '-o', out/'semantic.bin', '-Ln', out/'semantic.lbl', '-m', out/'semantic.map', *objects, out/'aliases.o')
    labels = {n: int(a, 16) for a, n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)', (out/'semantic.lbl').read_text())}
    payload = (out/'semantic.bin').read_bytes()
    assert len(payload) <= 4096 and labels['entry'] == 0xB010
    assert labels['se_sm_state'] == 0x8D00 and labels['se_sm_state_size'] == 79
    s = report['symbols']
    image = wrap(payload, 1, 24, api=(s['se_overlay_call'], s['se_overlay_frame']), binding_digest=bytes.fromhex(digest))
    (out/'semantic.seo').write_bytes(image)
    return image, labels


def expected(data, anchor):
    events = blocks(data)
    event = next((e for e in events if e['start'] <= anchor <= e['end']), None)
    if event is None:
        assert anchor == len(data) and (not data or data[-1] == 13)
        fence = events[-1]['fence'] if events else 0
        event = dict(kind=5 if fence else 1, language=events[-1]['language'] if fence else 0,
                     level=0, body=anchor, start=anchor, end=anchor)
    marker = (event['body']-event['start']) if event['body']-event['start'] < 256 else 0
    kind = event['kind']
    role = 2 if kind == 2 else 1 if kind == 3 else 4 if kind in (4, 5, 6) else 0
    return dict(kind=kind, language=event['language'], level=event['level'], marker=marker,
                start=event['start'], end=event['end'], body=event['body'], role=role,
                reverse=int(kind == 2), height=8 if kind == 5 else 9)


def run(out, previous, smoke=False):
    frozen, identity = geos.freeze(out, previous)
    image, labels = build(out/'leaf', frozen)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    f = geos.Fixture(out, frozen, dll, True)
    f.assets['semantic-private'] = image
    frames, fault_cases = [], []
    parent = bytes((i*31+17) & 255 for i in range(68))
    scratch = bytes((i*47+29) & 255 for i in range(768))

    def invoke(op):
        f.put('se_overlay_frame', op, 1)
        r, _ = f.fast_call(f.s['se_overlay_call'], a=24, x=1)
        assert f.read(0x8100, 768) == scratch, 'parent prefix/source/roles overwritten'
        actual = f.read(0x9134, 68)
        assert actual[:1]+actual[3:] == parent[:1]+parent[3:], 'parent controller overwritten'
        return r

    def query(data, anchor, reuse=False):
        f.put('se_f_owner', 4, 1)
        if reuse:
            f.m.load(F, anchor.to_bytes(3, 'little')+b'\x02\xA0'+bytes([0xA5])*16)
            # C20 owns the whole GL phase between semantic queries. A valid
            # reuse must restore its own certified parser, never trust GL RAM.
            f.m.load(0x8D00, bytes([0xA5])*832)
        else:
            f.m.load(F, anchor.to_bytes(3, 'little')+b'\x02\xA0'+bytes([0xA5])*187)
            f.m.write(F+28, 0) #explicit parent invalidation, no power-on claim
        f.m.load(0x9134, parent)
        f.m.load(0x8100, scratch)
        before = f.canonical()
        r = invoke(0)
        assert not r.p & 1 and r.a in (0, 1), ('begin', anchor, r.a)
        count = 0
        while r.a and not r.p & 1:
            old = int.from_bytes(f.read(0x8D00, 3), 'little')
            r = invoke(1)
            after = int.from_bytes(f.read(0x8D00, 3), 'little')
            assert 0 <= after-old <= 32, (old, after)
            count += 1
            assert count < len(data)//32+10
        assert not r.p & 1, ('query', anchor, r.a)
        offsets = [('kind', 5, 1), ('language', 6, 1), ('level', 7, 1), ('marker', 8, 1),
                   ('start', 9, 3), ('end', 12, 3), ('body', 15, 3), ('role', 18, 1),
                   ('reverse', 19, 1), ('height', 20, 1)]
        actual = {n: int.from_bytes(f.read(F+p, size), 'little') for n, p, size in offsets}
        assert actual == expected(data, anchor), (anchor, actual, expected(data, anchor))
        assert f.read(F, 5) == anchor.to_bytes(3, 'little')+b'\x02\xA0'
        assert f.canonical() == before and f.read(0xC600, 1024) == f.shim
        assert not f.get('se_doc_read_locks', 1) and not f.m.read(0x912D)
        assert f.get('se_f_owner', 1) == 4
        f.put('se_f_owner', 0, 1)
        reads = int.from_bytes(f.read(F+164, 3), 'little')
        frames.append(dict(anchor=anchor, result=actual, steps=count, reads=reads, reuse=reuse))
        (out/'progress.json').write_text(json.dumps(frames, indent=2)+'\n')
        return reads

    def whole_reu():
        data = C.create_string_buffer(16*1024*1024)
        dll.gm_reu(f.m.handle, len(data), data)
        return data.raw

    try:
        data = petscii('# Heading\ntext\n- item\n:::basic\n10 PRINT "HI"\n:::\n:::asm\nloop: lda #$12\n:::\nend\n')
        f.source(data)
        query(data, data.index(petscii('10 PRINT')))
        if not smoke:
            baseline = sum(query(data, anchor) for anchor in range(len(data)+1))
            reused = query(data, 0)
            for anchor in range(len(data)+1):
                reused += query(data, anchor, reuse=True)
            assert reused < baseline//2, (baseline, reused)
            reuse_stats = dict(cold_READs=baseline, monotonic_READs=reused)
            # Backwards and mode/source-key changes must discard the certificate.
            assert query(data, 3, reuse=True) > 0
            assert query(data, 3, reuse=True) == 0
            f.put('se_l_mode', 1, 1)
            assert query(data, 3, reuse=True) > 0
            f.put('se_l_mode', 0, 1)
            assert query(data, 3, reuse=True) > 0
            f.put('se_r_revision', f.get('se_r_revision', 4)+1, 4)
            assert query(data, 3, reuse=True) > 0
            f.position(0)
            f.key(petscii('Q')[0])
            data = petscii('Q')+data
            assert query(data, 3, reuse=True) > 0
            assert f.get('se_hot_pending', 1)
            for data in [b'', b'\r', petscii(':::basic\n'), petscii(':::basic\n10 PRINT "X"'),
                         petscii(':::region title\n:::asm\nlda #0\n:::\n:::end\n'),
                         petscii('1'*300+'. long list body\n'), bytes(range(256))]:
                f.source(data)
                anchors = sorted(set([0, len(data)]+[i for i, c in enumerate(data) if c == 13]))
                for anchor in anchors:
                    query(data, anchor)
            data = b'x'*65530+petscii('\n:::basic\n10 PRINT "HIGH"\n:::\n')
            f.source(data)
            f.position(65542)
            f.key(petscii('Q')[0])
            data = data[:65542]+petscii('Q')+data[65542:]
            assert f.get('se_hot_pending', 1)
            query(data, 65550)
            assert f.get('se_hot_pending', 1)
            anchors = sorted(set([65550, 65551, len(data)-2, len(data)]))
            long_cold = sum(query(data, anchor) for anchor in anchors)
            long_reused = query(data, anchors[0])
            for anchor in anchors[1:]:
                long_reused += query(data, anchor, reuse=True)
            assert long_reused < long_cold//2, (long_cold, long_reused)
            reuse_stats.update(long_source_bytes=len(data), long_cold_READs=long_cold,
                               long_monotonic_READs=long_reused)
            data = petscii(':::basic\n10 PRINT "FAULT"\n:::\n')
            f.source(data)
            before_reu = whole_reu()

            def setup(anchor=12):
                f.put('se_f_owner', 4, 1)
                f.m.load(F, anchor.to_bytes(3, 'little')+bytes([0xA5])*189)
                f.m.write(F+28, 0)
                f.m.load(0x9134, parent)
                f.m.load(0x8100, scratch)

            def remove(id_, slot):
                idx = next(i for i in range(f.s['se_overlay_capacity'])
                           if f.m.read(f.s['se_overlay_ids']+i) == id_
                           and f.m.read(f.s['image_slot']+i) == slot)
                f.m.write(f.s['se_overlay_ids']+idx, 0)
                f.m.write(f.s['se_overlay_active']+slot, 0)
                return idx

            assert not f.call('se_doc_read_acquire').p & 1
            setup()
            assert not invoke(0).p & 1 and f.get('se_doc_read_locks', 1) == 2
            assert not invoke(2).p & 1 and f.get('se_doc_read_locks', 1) == 1
            assert not invoke(2).p & 1 and f.get('se_doc_read_locks', 1) == 1
            assert not f.call('se_doc_read_release').p & 1
            fault_cases.append('idempotent CANCEL releases only counted own lease')
            # After a completed query C20 may own a new shared-reader lease.
            # Calling inactive C24 CANCEL must never end that foreign context.
            f.put('se_f_owner', 0, 1)
            query(data, 12)
            f.put('se_f_owner', 4, 1)
            f.m.load(0x8D00, bytes(32))
            f.m.load(0x8D02, (320).to_bytes(2, 'little'))
            f.put('se_overlay_frame', 0, 1)
            r, _ = f.fast_call(f.s['se_overlay_call'], a=20, x=1)
            assert not r.p & 1 and f.get('se_doc_read_locks', 1) == 1
            saved = f.read(0x9040, 86)
            assert not invoke(2).p & 1
            assert f.get('se_doc_read_locks', 1) == 1 and f.read(0x9040, 86) == saved
            assert f.m.read(0x912D) == 1
            assert not f.call('se_geos_cancel').p & 1
            fault_cases.append('inactive CANCEL preserves subsequent C20 owned source context')
            for id_, slot in [(14, 0), (24, 1)]:
                setup()
                assert not invoke(0).p & 1
                idx = remove(id_, slot)
                r = invoke(1)
                assert r.p & 1 and r.a == 0x17, (id_, r.a)
                if id_ == 24:
                    # This is the actual resident fallback after an unavailable
                    # semantic leaf, using precisely its exported GS snapshot.
                    assert not f.call('se_geos_cancel').p & 1
                assert not f.get('se_doc_read_locks', 1) and not f.m.read(0x912D)
                f.m.write(f.s['se_overlay_ids']+idx, id_)
                fault_cases.append('missing '+str(id_)+' preserves original17 and ends own lease')
            setup()
            assert not invoke(0).p & 1
            f.put('se_r_revision', f.get('se_r_revision', 4)+1, 4)
            r = invoke(1)
            assert r.p & 1 and r.a == 0xB1 and not f.get('se_doc_read_locks', 1)
            fault_cases.append('changed actual source context preserves R14 errorB1')
            setup(len(data)+1)
            r = invoke(0)
            assert r.p & 1 and r.a == 0x7B and not f.get('se_doc_read_locks', 1)
            assert f.read(F+5, 16) == bytes([0xA5])*16
            fault_cases.append('out-of-source query preserves outputs and releases lease')
            for owner in [0, 1, 2, 3, 255]:
                setup()
                f.put('se_f_owner', owner, 1)
                poison = bytes((i*37+owner) & 255 for i in range(1152))
                f.m.load(0x8D00, poison)
                f.m.load(0x9134, parent)
                phase = f.read(0x8D00, 1152)
                frame = f.read(F, 192)
                for op in [0, 1, 2, 3, 255]:
                    r = invoke(op)
                    assert r.p & 1 and r.a == 0xB2
                    assert f.read(F, 192) == frame and f.read(0x8D00, 1152) == phase
            f.put('se_f_owner', 0, 1)
            assert whole_reu() == before_reu
            assert f.read(0xC600, 1024) == f.shim
            fault_cases.append('foreign phase owners and entire16MiB REU preserved')
        result = dict(status='passed', identity=identity, payload_bytes=len(image)-36,
                      phase_block_bytes=79, caller_frame_bytes=192, new_BSS=0, new_ZP=0,
                      queries=frames, faults=fault_cases, max_feeds_per_STEP=32,
                      parent_bytes_preserved=66, source_prefix_roles_bytes_preserved=768,
                      full_fault_REU_guard_bytes=16*1024*1024 if not smoke else 0,
                      monotonic_query_reuse=reuse_stats if not smoke else None,
                      scope='Actual private C24/R14 merged-source block context; no raster/prefix hiding/UI/native claim.')
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(dict(status='passed', queries=len(frames), payload_bytes=len(image)-36, out=str(out)), indent=2))
        return result
    finally:
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, default=DEFAULT)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    out = ROOT/'build/geos-semantic'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    run(out, args.fixture, args.smoke)
