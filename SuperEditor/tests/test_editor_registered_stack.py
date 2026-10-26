"""Actual59 stack graph with finite lexical tables and checked C33/R25 capture.

Every new service instruction is decoded. The only extra address mapping is
R25's actual authenticated image within C33; other unowned R entries still fail.
The released lexical verifier byte-checks both bounded local jump tables.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,inspect,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]


def run(out,base,project,idle_log=None):
    source=ROOT/'src/cache/lexical-registration-probe/stack-run.py'
    spec=importlib.util.spec_from_file_location('current59_stack',source)
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    context=out.with_name(out.name+'-context');context.mkdir(parents=True)
    original=runner.m.original.foreground_proof
    text=inspect.getsource(original)
    old="[(0xb000,image[36:])],Ccall)"
    new="[(0xb000,image[36:])]+([(0xa000,images['geostail'][36:])]if name=='grid'else[]),Ccall)"
    assert text.count(old)==1
    text=text.replace(old,new)
    path=context/'capture-foreground.py';path.write_text(text)
    ns=dict(runner.m.original.__dict__)
    exec(compile(text,str(path),'exec'),ns)
    runner.m.original.foreground_proof=ns['foreground_proof']
    # Supply a matching native natural-idle witness only after the registered
    # verifier has established its original table and actual-stage proofs.
    staged_run=runner.m.run
    if idle_log:
        def witnessed(target,fixture,rom,unused=None):
            return staged_run(target,fixture,rom,idle_log)
        runner.m.run=witnessed
    result=runner.run(out,base,project)
    payload=(base/'build/overlays/geostail.seo').read_bytes()[36:]
    fg=result['foreground']
    helper=next(x for x in fg['results']if x['name']=='R:geostail')
    assert not helper['faults'] and not helper['opaque_non_IEC_calls']
    result['capture_mapping']=dict(consumer='C:grid',entry=0xA010,
        authenticated_payload_sha256=hashlib.sha256(payload).hexdigest(),
        loader_edges_in_R25=0,other_consumers_unchanged=True)
    result['scope']=__doc__
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--idle-log',type=Path)
    a=p.parse_args();out=ROOT/'build/editor-registered-stack'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.project.resolve(),a.idle_log.resolve()if a.idle_log else None)
