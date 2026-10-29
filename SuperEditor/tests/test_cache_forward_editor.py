"""Actual foreground C37 handoff, with one deliberately corrupted slot input.

The public renderer produces the baseline, proof and semantic outputs. Only the
untrusted slot byte is faulted; no worker, lease, checkpoint or output is seeded.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json
import test_cache_observer as observer
import test_plain_geos as plain

ROOT = observer.ROOT


def run(out, base):
    gate = observer.Gate(out, base)
    f = gate.f
    cases = []
    try:
        assert 'page' in gate.identity['names']
        fonts = {n: (gate.frozen/'fonts'/n).read_bytes()
                 for n in observer.geos.GEOS_FONTS+('native8.bin',)}
        data = plain.SOURCE
        f.source(data)
        f.typed(observer.geos.native_text('syntax markdown'))
        f.command(99)
        f.render()
        for fault in (False, True):
            before, canonical = gate.reu(), gate.stable()
            start = f.total_instructions
            f.put('se_gc_width', 0, 1)
            f.m.write(0xCF90, 0)
            f.m.write(0xCFE8, 0)
            f.put('se_r_valid', 0, 1)
            f.put('se_l_valid', 0, 1)
            f.put('se_l_need_wrap', 1, 1)
            r = f.call('se_editor_render')
            assert not r.p & 1
            trace, injected, awaiting_begin = [], False, False
            for _ in range(10000):
                if not f.get('se_e_job', 1):
                    break
                request, op = f.read(0x9135, 2)
                if request in (35, 37):
                    trace.append([request, op])
                if fault and not injected and (request, op) == (37, 0):
                    f.m.write(0x8B40+114, 255)
                    injected = True
                    awaiting_begin = True
                r = f.call('se_editor_service')
                assert not r.p & 1 and not f.get('se_e_error', 1)
                if awaiting_begin:
                    assert f.read(0x9135, 2) == bytes((35, 0)), \
                        ('handoff must retain BEGIN0', f.read(0x9135, 2).hex())
                    assert not f.get('se_doc_read_locks', 1)
                    awaiting_begin = False
            else:
                raise AssertionError('foreground renderer did not converge')
            assert any(x[0] == 37 for x in trace)
            assert injected == fault
            assert trace.count([35, 0]) == 1 + int(fault), trace
            bits, attrs, _ = plain.expected(f, data, fonts, 1)
            assert f.read(0x6000, 8000) == bits
            assert f.read(0x4000, 1000) == attrs
            assert f.merged() == data and gate.stable() == canonical
            assert f.read(0xC600, 1024) == f.shim
            assert not any(f.get(n, 1) for n in
                           ('se_e_error', 'se_f_owner', 'se_doc_read_locks'))
            _, bank = f.raw_cache()
            after, wanted = gate.reu(), bytearray(before)
            spans = [(0, 64), (0x600, 0x680), (0xB200, 0xD8B2),
                     (0xE568, 0xEA88)]
            spans += [(0x200+i*0x800, 0x200+i*0x800+842)
                      for i in range(22)]
            for lo, hi in spans:
                lo += bank*65536
                hi += bank*65536
                wanted[lo:hi] = after[lo:hi]
            assert after == wanted, 'whole16MiB outside existing FE spans'
            tag = 'corrupt-slot-handoff' if fault else 'forward-render'
            observer.geos.png(bits, attrs, out/(tag+'.png'))
            case = dict(tag=tag, trace=trace,
                        instructions=f.total_instructions-start)
            cases.append(case)
            print('PASS', case, flush=True)
        result = dict(status='PASS', resident=f.report['sha256'],
                      cases=cases,
                      verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      scope='Actual public foreground rendering and resident C37→C35 BEGIN handoff; one untrusted slot input is faulted, outputs are independently modeled.')
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    finally:
        f.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', type=Path, required=True)
    args = p.parse_args()
    out = ROOT/'build/cache-forward-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    run(out, args.fixture.resolve())
