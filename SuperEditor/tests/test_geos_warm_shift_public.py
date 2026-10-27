"""Read-only original/candidate root56 key profiles with exact independent pixels."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,inspect,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_warm_input_profile as profile
D=ROOT/'src/render/geos/warm-shift-probe';BASE=profile.BASE

def run(out,base):
 out.mkdir(parents=True);p=D/'build.py';spec=importlib.util.spec_from_file_location('warm_shift_build',p);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 results={};budgets={}
 for variant in('before','after'):
  fixture,budgets[variant]=b.build(out/('build-'+variant),base,variant);text=inspect.getsource(profile.run);assert text.count('f.source(initial);')==1;text=text.replace('f.source(initial);','f.source(initial,physical=256);');ns=dict(vars(profile));exec(compile(text,str(out/(variant+'-executed.py')),'exec'),ns);(out/(variant+'-executed.py')).write_text(text);results[variant]=ns['run'](out/variant,fixture)
 rows=[]
 for a,z in zip(results['before']['records'],results['after']['records']):
  assert (a['dataset'],a['caps'],a['tag'])==(z['dataset'],z['caps'],z['tag'])and a['pixels_sha256']==z['pixels_sha256'];assert a['loads']==z['loads'];assert a['DMA']==z['DMA']or a['tag']=='pair0-insert'or a['tag']=='pair0-back'
  rows.append(dict(dataset=a['dataset'],caps=a['caps'],tag=a['tag'],before=a['total_instructions'],after=z['total_instructions'],saved=a['total_instructions']-z['total_instructions'],loads=z['loads']))
 assert len(rows)==56
 r=dict(status='PASS',fixture=str(base),budget=budgets,comparisons=rows,scope='Private source-rebuilt before pair must byte-match frozen product. Exactly C32/R30 substituted after; original D81 retained and not claimed coherent. Actual public56 original/candidate keys, independent pixels/source/history-render/actualUndoRedo/whole16MiB precise FE guards from profile. No native latency claim.')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--out',type=Path);a=p.parse_args();o=a.out or ROOT/'build/geos-warm-shift-public'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',o,flush=True);run(o,a.fixture.resolve())
