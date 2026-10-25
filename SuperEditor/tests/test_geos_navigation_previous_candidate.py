"""Private C23/C24/C21 local E_POSITION through the actual root job12 pump.

Direct resident navigation entry is an explicit seam before pending flush; V2 predecessor lookup handles actual CR joins;
this does not claim that the public before-TOP CR join has been fixed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, importlib.util, json, zipfile
import test_geos_heading_body_candidate as heading
import test_geos_navigation_editor as navigation

ROOT = Path(__file__).resolve().parents[1]
geos = heading.geos


class Fixture(heading.Fixture):
    def __init__(self, *args, **kwargs):
        self.tracing = False
        self.requests = []
        super().__init__(*args, **kwargs)

    def call(self, name, a=0):
        if self.tracing and name == 'se_editor_service' and self.get('se_e_job', 1) == 12:
            self.requests.append(dict(id=self.m.read(0x9135), op=self.m.read(0x9136)))
        return super().call(name, a)


def run(out, base, operand=False):
    spec = importlib.util.spec_from_file_location('seed_navigation', ROOT / 'src/render/geos/navigation-previous-candidate/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.build(out / 'link', base)
    frozen, identity = geos.freeze(out, base)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    f = Fixture(out, frozen, dll, True)
    for name, path in [('geosnav', 'candidate/geosnav.seo'),
                       ('geossema', 'semantic/seed/geossema.seo'),
                       ('geospage', 'semantic/producer/geospage.seo')]:
        f.assets[name] = (out / 'link' / path).read_bytes()
    fonts = {name: (frozen/'fonts'/name).read_bytes() for name in geos.GEOS_FONTS + ('native8.bin',)}
    cases = []
    try:
        for far in [False, True]:
            for pending in [False, True]:
                prefix = geos.native_text('prefix\r') * (9400 if far else 2)
                raw = prefix + geos.native_text(':::asm\rlda #1\rsta $d020\r:::\rTail.')
                anchor = len(prefix) + 7
                at = anchor + (6 if operand else 3)
                f.source(raw)
                f.position(at)
                f.command(99)
                f.put('se_v_top', anchor)
                f.render()
                handle = f.get('se_gc_handle', 1)
                bank = f.m.read(f.s['se_reu_map'] + handle)
                record = f.reu()[bank*65536+0x600:bank*65536+0x640]
                assert record[:4] == b'S\2@\1'
                assert int.from_bytes(record[4:7], 'little') == anchor, (anchor, f.get('se_v_top'), record.hex())
                assert record[35:37] == bytes((3, 2)), 'actual assembler incoming carry'
                if pending:
                    byte = geos.native_text('2' if operand else 'Q')[0]
                    f.key(byte)
                    raw = raw[:at] + bytes((byte,)) + raw[at:]
                else:
                    # Discard only the derived row-table validity through its
                    # actual FE capability; retain the independent parser CP.
                    f.m.write(0x8080, 0)
                    for name, value, width in [('se_reu_logical', handle, 1), ('se_reu_offset', 0, 2),
                                               ('se_reu_length', 1, 2), ('se_reu_c64', 0x8080, 2)]:
                        f.put(name, value, width)
                    assert not f.call('se_reu_copy', 0).p & 1
                generation = f.get('se_doc_generation', 2)
                preserved = navigation.preserved(f)
                before = f.reu()
                f.put('se_e_target', f.get('se_hot_caret'))
                f.put('se_e_command', 47, 1)
                f.requests = []
                f.tracing = True
                used = f.total_instructions
                assert not f.call('se_geos_navigate').p & 1
                f.settle()
                instructions = f.total_instructions - used
                f.tracing = False
                assert dict(id=24, op=3) in f.requests, 'real TRY_SEED dispatch'
                assert len(f.requests) < 40, ('local query unexpectedly scanned from BOF', len(f.requests))
                assert f.get('se_v_top') == anchor and f.merged() == raw
                assert f.get('se_doc_generation', 2) == generation and f.get('se_hot_pending', 1) == int(pending)
                assert navigation.preserved(f) == preserved and f.reu() == before
                assert not any(f.get(n, 1) for n in ['se_f_owner', 'se_doc_read_locks', 'se_fs_owned', 'se_e_error'])
                assert f.read(0xc600, 1024) == f.shim
                f.render()
                bitmap, attrs, _, _ = heading.semantic.expected(f, raw, fonts)
                tag = ('far64k' if far else 'near') + ('-pending' if pending else '-exact')
                if f.read(0x6000, 8000) != bitmap or f.read(0x4000, 1000) != attrs:
                    geos.png(f.read(0x6000, 8000), f.read(0x4000, 1000), out/(tag+'-actual.png'))
                    geos.png(bitmap, attrs, out/(tag+'-expected.png'))
                    print('MISMATCH',tag,[(i,a,b)for i,(a,b)in enumerate(zip(f.read(0x6000,8000),bitmap))if a!=b][:16],[(i,a,b)for i,(a,b)in enumerate(zip(f.read(0x4000,1000),attrs))if a!=b][:16],flush=True)
                assert f.read(0x6000, 8000) == bitmap and f.read(0x4000, 1000) == attrs
                geos.png(bitmap, attrs, out / (tag + '.png'))
                cases.append(dict(tag=tag, anchor=anchor, instructions=instructions, requests=f.requests,
                                  pending_preserved=bool(pending), unchanged_REU_bytes=16777216))
                print('PASS', tag, instructions, len(f.requests), flush=True)
        for far in [False, True]:
            prefix = geos.native_text('prefix\r') * (9400 if far else 2)
            raw = prefix + geos.native_text('# Heading words.\rFollowing row.\rTail.')
            at = len(prefix) + 17
            f.source(raw)
            f.command(99)
            f.position(at)
            # Explicit viewport setup only; actual C21 must generate both CPs.
            f.put('se_v_top', at)
            f.render()
            oldtop = f.get('se_v_top')
            assert oldtop == at
            generation = f.get('se_doc_generation', 2)
            assert not f.call('se_hot_call', 4).p & 1
            changed = raw[:at-1] + raw[at:]
            assert f.merged() == changed and f.get('se_hot_pending', 1)
            preserved = navigation.preserved(f)
            before = f.reu()
            f.put('se_e_target', f.get('se_hot_caret'))
            f.put('se_e_command', 47, 1)
            f.requests = []
            f.tracing = True
            used = f.total_instructions
            assert not f.call('se_geos_navigate').p & 1
            f.settle()
            instructions = f.total_instructions - used
            f.tracing = False
            assert dict(id=24, op=3) in f.requests and len(f.requests) < 40
            assert f.get('se_doc_generation', 2) == generation and f.get('se_hot_pending', 1)
            assert f.get('se_v_top') == len(prefix)
            assert navigation.preserved(f) == preserved and f.reu() == before
            assert not any(f.get(n, 1) for n in ['se_f_owner', 'se_doc_read_locks', 'se_fs_owned', 'se_e_error'])
            f.render()
            bitmap, attrs, _, _ = heading.semantic.expected(f, changed, fonts)
            assert f.read(0x6000, 8000) == bitmap and f.read(0x4000, 1000) == attrs
            assert f.read(0xc600, 1024) == f.shim
            tag = ('far64k' if far else 'near') + '-pending-beforeTOP-CRjoin'
            geos.png(bitmap, attrs, out / (tag + '.png'))
            cases.append(dict(tag=tag, oldtop=oldtop, newtop=f.get('se_v_top'), instructions=instructions, requests=f.requests, pending_preserved=True, unchanged_REU_bytes=16777216))
            print('PASS', tag, instructions, len(f.requests), flush=True)
        result = dict(status='passed', cases=cases, operand_edits=operand, scope=__doc__,
            separate_open_issue='Actual C23 preflush entry seam only; public resident reveal routing is unchanged. Current packaged ASM wholeword fix is independently qualified.')
        (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
        return result
    except BaseException:
        (out / 'failure-ram.bin').write_bytes(f.read(0, 65536))
        raise
    finally:
        f.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--operand', action='store_true', help='Separate numeric-operand case; retain default mnemonic-suffix counterexample.')
    args = p.parse_args()
    out = ROOT / 'build/geos-navigation-previous' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    run(out, args.fixture.resolve(), args.operand)
