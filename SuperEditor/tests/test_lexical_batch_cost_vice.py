"""Paired PAL whole-operation59 lexical control vs released same-call batching.

Genuine private disk replaces exactly C45/R36/R37, retaining the same resident,
all other56 assets, source and actual root1->5 construction. The released
candidate59 evaluator is reused unchanged for BOTH59 cohorts. PC/SP/public
input stopwatch seam measures completion work with warp, not physical latency.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,subprocess,zipfile
import test_lexical_cost_vice as original
from test_lexical_cost_vice import lexical,timing,vice_plan,ROOT

CONTROL=ROOT/'build/capture-index-fixed/20261026T183928480377Z/fixture'
spec=importlib.util.spec_from_file_location('lexical_batch_native_build',ROOT/'src/cache/lexical-batch-native-probe/build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


def evaluate(n,cohort):
    # Both cohorts must satisfy the original genuine59 root/role-cache oracle.
    # The old54 parser path is deliberately not selected for the control.
    result=original.evaluate(n,'candidate59')
    result['cohort']=cohort
    for row in result['frames']:row['cohort']=cohort
    (n.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def execute(source,cohort):
    original.free_ports();e=timing.freeze(source.resolve(),'pal')
    target=e.with_name(e.name.replace('display-timing-pal','lexical-batch-'+cohort));e.rename(target);e=target
    lexical.package(e);n=original.scenario(e,cohort);p=n.plan()
    assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in('tests','tools'):
            for path in(ROOT/folder).glob('*.py'):z.write(path,path.relative_to(ROOT))
        for path in(ROOT/'src/cache/lexical-batch-native-probe').glob('*.py'):z.write(path,path.relative_to(ROOT))
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('LEXICAL_BATCH_NATIVE',cohort,e,flush=True)
    original.run_owned_plan(p,n.out)
    return e,evaluate(n,cohort)


def compare(pairs):
    rows=[]
    for a,b in zip(pairs[0][1]['frames'],pairs[1][1]['frames']):
        assert(a['language'],a['phase'])==(b['language'],b['phase'])
        assert a['bitmap_attrs_sha256']==b['bitmap_attrs_sha256']and a['png_sha256']==b['png_sha256']
        assert not any(a['C25_trace'][k]or b['C25_trace'][k]for k in('se_sl_init','se_sl_feed','se_sl_finish'))
        rows.append(dict(id=a['id'],control_cycles=a['cycles'],candidate_cycles=b['cycles'],
            percent_saved=100*(a['cycles']-b['cycles'])/a['cycles'],
            control_loads=a['counter_deltas']['se_overlay_loads'],candidate_loads=b['counter_deltas']['se_overlay_loads'],
            control_C25_trace=a['C25_trace'],candidate_C25_trace=b['C25_trace']))
    result=dict(status='PASS',scope=__doc__,cohorts={name:str(pair[0])for name,pair in zip(('control59','fused4'),pairs)},
                comparisons=rows,native_pixels=512000)
    (pairs[1][0]/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--control',type=Path,default=CONTROL)
    p.add_argument('--candidate',type=Path);p.add_argument('--verify',type=Path,nargs=2);a=p.parse_args()
    if a.verify:
        import test_presentation_vice as presentation
        pairs=[(path.resolve(),evaluate(presentation.scenario_loaded(path.resolve()),label))for path,label in zip(a.verify,('control59','fused4'))]
    else:
        if a.candidate:candidate=a.candidate.resolve()
        else:
            out=ROOT/'build/lexical-batch-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            candidate,proof=builder.build(out,a.control.resolve());print('GENUINE_PRIVATE_FIXTURE',candidate,flush=True)
        pairs=[execute(source,label)for source,label in((a.control,'control59'),(candidate,'fused4'))]
    compare(pairs)
