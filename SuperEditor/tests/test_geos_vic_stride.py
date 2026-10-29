"""Private VIC stride-eight copy; exact committed62 source input."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,subprocess,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_shift8_candidate as old
D=ROOT/'src/render/geos/vic-stride-probe'
BASE=ROOT/'build/warm-shift-committed/20261027T002602997186Z/fixture'
def build_component(out,base,variant,is_wide):
 assert is_wide;out.mkdir(parents=True);symbols=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'loans.s').write_text(f'.exportzp gt_base,gt_bitmap\ngt_base=${symbols["text_ptr"]:02x}\ngt_bitmap=${symbols["screen_ptr"]:02x}\n')
 source=D/('wide-before.s'if variant=='before'else'wide.s');cfg=out/'component.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$A000,size=$1000,type=ro;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 include=out/'include/render/geos/style-typing';include.mkdir(parents=True);shutil.copy2(D/'wide.inc',include/'wide.inc');objects=[]
 for tag,path in [('wide',source),('loans',out/'loans.s')]:
  o=out/(tag+'.o');subprocess.run(['ca65','-g','-I',out/'include','-o',o,path],check=True);objects.append(o)
 subprocess.run(['ld65','-C',cfg,'-o',out/'component.bin','-Ln',out/'component.lbl','-m',out/'component.map',*objects],check=True)
 s={t[2].lstrip('.'):int(t[1],16)for l in(out/'component.lbl').read_text().splitlines()if len(t:=l.split())==3 and t[0]=='al'};return(out/'component.bin').read_bytes(),s

def run(out,base):
 out.mkdir(parents=True);old.build_component=build_component;variants={}
 for variant in('before','after'):
  d=out/variant;d.mkdir();variants[variant]=old.component(d,base,variant)
 diff=old.bounds.compare(variants['before'],variants['after']);result=dict(status='PASS',fixture=str(base),component=diff,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(D/'wide-before.s',D/'wide.s',D/'wide.inc')});(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
def public(out,base,pairs=4):
 import inspect
 import test_geos_warm_input_profile as profile
 from test_geos_warm_shift_guards import run as guard_run
 spec=importlib.util.spec_from_file_location('vic_stride_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 results={};budgets={};fixtures={}
 for variant in ('before','after'):
  fixtures[variant],budgets[variant]=b.build(out/('build-'+variant),base,variant)
  source=inspect.getsource(profile.run);assert source.count('f.source(initial);')==1;source=source.replace('f.source(initial);','f.source(initial,physical=256);')
  path=out/(variant+'-executed.py');path.write_text(source);ns=dict(vars(profile));exec(compile(source,str(path),'exec'),ns);results[variant]=ns['run'](out/variant,fixtures[variant],pairs=pairs)
 rows=[]
 for a,z in zip(results['before']['records'],results['after']['records']):
  assert (a['dataset'],a['caps'],a['tag'])==(z['dataset'],z['caps'],z['tag']) and a['pixels_sha256']==z['pixels_sha256']
  assert a['loads']==z['loads'];assert a['DMA']==z['DMA'] or a['tag'] in ('pair0-insert','pair0-back')
  rows.append(dict(dataset=a['dataset'],caps=a['caps'],tag=a['tag'],before=a['total_instructions'],after=z['total_instructions'],saved=a['total_instructions']-z['total_instructions'],loads=z['loads']))
 assert len(rows)==(pairs*2+4)*4
 result=dict(status='PASS',fixture=str(base),provider_physical_banks=256,budget=budgets,comparisons=rows,scope='Source-rebuilt baseline pair exact; candidate changes TYPE/GTYPE only. Original D81 retained, CPU catalog substitution seam, no coherent-package or native claim. Independent pixels/source/history/checked DMA and precise full16MiB guard unchanged.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PUBLIC',json.dumps(result),flush=True)
 guard_run(out/'guards',fixtures['after'])
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--out',type=Path);p.add_argument('--public',action='store_true');p.add_argument('--pairs',type=int,default=4);a=p.parse_args();out=a.out or ROOT/'build/vic-stride-probe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True)
 if a.public:
  out.mkdir(parents=True);public(out,a.fixture.resolve(),a.pairs)
 else:run(out,a.fixture.resolve())
