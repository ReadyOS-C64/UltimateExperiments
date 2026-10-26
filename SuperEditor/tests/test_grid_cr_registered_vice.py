"""Cold59/60 native Return/BACK A/B, ROM File/Open and actual scheduler.

The stopwatch uses the disclosed PC/SP/public-input seam, not physical keys.
Checks every sealed asset, pending source, native VIC pixel, settings and shim.
"""
from pathlib import Path
import argparse
import hashlib
import inspect
import json
import shutil
import subprocess
import tempfile
import textwrap
import zipfile
import test_grid_raw_typing_vice as raw
import test_retention_grammar_registered_vice as ports
from closed_runtime_copy import run_with_closed_links
from d81_image import D81Image
from test_grid_cr_registered import authenticate

ROOT = raw.ROOT
timing = raw.timing


class Plan(raw.Plan):
    def plan(self):
        p = super().plan()
        p['global_defaults']['monitor_port_start'] = 8500
        return p


def data_for(tag):
    return timing.native.live.grid.native_text(
        ('Alpha words '*12 if tag == 'wrapped' else 'Alpha words.')+
        '\rBeta words.\rTail.\r')


def scenario(e, control):
    # Return here edits body UI0. Retain the real input/scheduler stopwatch;
    # the original generic method assumed Return accepts a command in UI2.
    source = inspect.getsource(timing.Plan.measure)
    assert source.count('ui if key!=13 else 2') == 1
    source = textwrap.dedent(source.replace('ui if key!=13 else 2', 'ui'))
    (e/'body-return-measure.py').write_text(source)
    ns = dict(vars(timing))
    exec(compile(source, str(e/'body-return-measure.py'), 'exec'), ns)
    Plan.measure = ns['measure']
    n = Plan(e, json.loads((e/'editor-report.json').read_text()), 1, 0)
    n.cost_profile = True
    n.boot()
    n.typed('public_plain', 'syntax plain')
    n.memory('actual_plain', 'se_render_caps', 0)
    for width, mode in ((60, 1), (80, 2)):
        for tag in ('short', 'wrapped'):
            data = data_for(tag)
            n.open('open_'+str(width)+tag, ('CR'+tag).upper().encode())
            n.mode_to(mode)
            n.typed('goto_'+str(width)+tag, 'goto 1')
            n.send('column_'+str(width)+tag, b'\x1d'*5)
            n.memory('at_'+str(width)+tag, 'se_hot_caret', 5, 3)
            changed = data[:5]+b'\r'+data[5:]
            for action, key, wanted, at in (('split', 13, changed, 6),
                                            ('merge', 20, data, 5)):
                ident = f'{width}-{tag}-{action}'
                n.measure(ident, wanted, mode, key=key, category='true-CR-'+action)
                n.measurements[-1].update(caps=0, branch=None if control else 2,
                                          expected_caret=at, control=control)
    return n


def evaluate(n, control):
    # The inherited row test owns8100. This wrapper owns8500 and may run
    # beside a separate real-IRQ test on8100; inspect only our own port block.
    old_ports = raw.caret.free_ports
    raw.caret.free_ports = ports.free_ports
    try:
        result = raw.evaluate(n, require_fast=not control)
    finally:
        raw.caret.free_ports = old_ports
    records = json.loads((n.out/'result.json').read_text())
    # The generic evaluator authenticates all catalog images from actual REU.
    # Additionally prove the new R29 actually executed only in the candidate.
    for item in records['measurements']:
        r29 = [g for g in item['cost_profile']['groups']
               if g['slot'] == 0 and g['id'] == 29]
        assert bool(r29) == (not control), (item['id'], 'actual R29 route')
        if r29:
            assert r29[0]['calls'] == 1, (item['id'], 'one complete R29 transaction')
        ident = item['id']
        cap = n.out/'captures'
        before = (cap/(ident+'-before-ram.bin')).read_bytes()
        after = (cap/(ident+'-finished-ram.bin')).read_bytes()
        for name, size in (('se_doc_meta', 15), ('se_doc_length', 3),
                           ('se_doc_roots', 512), ('se_h_current', 4),
                           ('se_h_saved', 4), ('se_h_end', 2),
                           ('se_h_cursor', 2), ('se_clip_token', 5),
                           ('se_clip_length', 3)):
            at = n.s[name]
            assert before[at:at+size] == after[at:at+size], (ident, name)
    result.update(control=control, actual_cold_assets=59 if control else 60,
                  real_R29_calls=0 if control else len(records['measurements']))
    (n.out/'cr-result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def execute(fixture=None, existing=None, control=False, verify=False):
    ports.free_ports()
    if existing:
        e = existing.resolve()
    else:
        assert fixture
        if not control:
            authenticate(fixture)
        else:
            assert len(json.loads((fixture/'freeze.json').read_text())['names']) == 59
        e = timing.freeze(fixture, 'pal')
        target = e.with_name(e.name.replace('display-timing-pal',
                           'grid-cr-control-native' if control else 'grid-cr-registered-native'))
        e.rename(target)
        e = target
        for tag in ('short', 'wrapped'):
            data = data_for(tag)
            source = e/(tag+'.seq')
            source.write_bytes(data)
            p = subprocess.run(['c1541', '-attach', str(e/'working.d81'),
                                '-write', str(source), 'cr'+tag+',s'], capture_output=True)
            (e/(tag+'-package.log')).write_bytes(p.stdout+p.stderr)
            assert not p.returncode
            assert D81Image((e/'working.d81').read_bytes()).read(('CR'+tag).upper().encode(), kind=1).data == data
        shutil.copy2(e/'working.d81', e/'initial-fixtures.d81')
    if verify:
        with tempfile.TemporaryDirectory(prefix='supereditor-cr-evaluator-') as temp:
            ctx = Path(temp)
            shutil.copy2(e/'editor.prg', ctx/'editor.prg')
            n = Plan(ctx, json.loads((e/'editor-report.json').read_text()), 1, 0)
            n.e, n.out, n.cost_profile = e, e/'timing', True
            n.measurements = json.loads((n.out/'measurements.json').read_text())
            return evaluate(n, control)
    n = scenario(e, control)
    plan = n.plan()
    assert len({x['id'] for x in plan['steps']}) == len(plan['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(plan, indent=2)+'\n')
    (n.out/'measurements.json').write_text(json.dumps(n.measurements, indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests', 'tools'):
            for p in sorted((ROOT/folder).glob('*.py')):
                z.write(p, p.relative_to(ROOT))
    project = timing.native.live.grid.synchronous_project(n.out)
    raw.vice_plan.PROJECT = project
    p = subprocess.run(['dotnet', 'build', str(project), '--nologo'],
                       capture_output=True, text=True, timeout=120)
    (n.out/'dotnet-build.log').write_text(p.stdout+p.stderr)
    assert not p.returncode
    print('NATIVE', e, 'steps', len(n.steps), 'frames', len(n.measurements), flush=True)
    run_with_closed_links(raw.capacity.run_owned_plan, plan, n.out, timeout=900)
    ports.free_ports()
    return evaluate(n, control)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path)
    p.add_argument('--existing', type=Path)
    p.add_argument('--verify', action='store_true')
    p.add_argument('--control', action='store_true')
    a = p.parse_args()
    execute(a.fixture.resolve() if a.fixture else None, a.existing, a.control, a.verify)
