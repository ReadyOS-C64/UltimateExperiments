"""Private full-byte+remainder deletion shift; no production/shared edits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,inspect,json,shutil,subprocess,sys,zipfile
import test_geos_typing_bounds as bounds
import test_geos_style_wide_patch as wide
import test_geos_style_editor as public
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'src/render/geos/typing-shift8-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T133435860867Z/fixture'

def build_component(out,base,variant,is_wide):
 assert is_wide
 out.mkdir(parents=True);symbols=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'loans.s').write_text(f'.exportzp gt_base,gt_bitmap\ngt_base=${symbols["text_ptr"]:02x}\ngt_bitmap=${symbols["screen_ptr"]:02x}\n')
 source=D/('wide-before.s'if variant=='before'else'wide.s');cfg=out/'component.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$A000,size=$1000,type=ro;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 include=out/'include/render/geos/style-typing';include.mkdir(parents=True);shutil.copy2(D/'wide.inc',include/'wide.inc');objects=[]
 for tag,path in [('wide',source),('loans',out/'loans.s')]:
  o=out/(tag+'.o');subprocess.run(['ca65','-g','-I',out/'include','-o',o,path],check=True);objects.append(o)
 subprocess.run(['ld65','-C',cfg,'-o',out/'component.bin','-Ln',out/'component.lbl','-m',out/'component.map',*objects],check=True)
 s={t[2].lstrip('.'):int(t[1],16)for l in(out/'component.lbl').read_text().splitlines()if len(t:=l.split())==3 and t[0]=='al'}
 raw=(out/'component.bin').read_bytes();return raw,s

def component(out,base,variant):
 # Exact released1456-vector suite and17 rejection cases, plus dirty-tail
 # stress. Builder/source are the only transport substitution.
 bounds.build_component=build_component
 original=inspect.getsource(wide.run)
 extra='''
  dirty=True
  for advance in range(8,12):
   for op in (0,1):
    for oldwidth in ([0,1,7,8,9,15,16,31,64,160,307]if op==0 else[8,9,15,16,31,64,160,308,319]):
     if op and oldwidth<advance:continue
     if not op and oldwidth+advance>=320:continue
     xmax=oldwidth-advance if op else oldwidth
     for x in sorted({0,xmax,min(1,xmax),min(7,xmax),min(8,xmax),min(15,xmax)}):
      for top in (16,183):
       glyph=b''.join((rng.randrange(1<<advance)<<(16-advance)).to_bytes(2,'big')for _ in range(9))
       check(op,x,advance,oldwidth,top,glyph,11)
'''
 # original_wide dynamically inspects wide.run; execute the extended copy
 # under a private module to avoid modifying either released verifier.
 original=original.replace("base=b''.join(packed([rng.randrange(2)if p<oldwidth else 0 for p in range(320)])for _ in range(9))", "base=b''.join(packed([rng.randrange(2)if (dirty or p<oldwidth) else 0 for p in range(320)])for _ in range(9))")
 original=original.replace('cases=0;peak=0','cases=0;peak=0;dirty=False')
 original=original.replace('  assert f.canonical()==canonical',extra+'  assert f.canonical()==canonical')
 saved=wide.run;namespace=dict(vars(wide));exec(compile(original,str(out/'dirty-executed.py'),'exec'),namespace)
 # inspect.getsource needs an actual file and a unique module filename.
 modulefile=out/'dirty-original.py';modulefile.write_text(original);spec=importlib.util.spec_from_file_location('shift8_vectors_'+variant,modulefile);module=importlib.util.module_from_spec(spec);module.__dict__.update({k:v for k,v in vars(wide).items()if k not in('__name__','__file__','__spec__','__loader__')});spec.loader.exec_module(module)
 wide.run=module.run
 try:return bounds.original_wide(out,base,variant)
 finally:wide.run=saved

def candidate_fixture(out,base,variant):
 """Rebuild only C32/R30 private copies; no host row-map injection."""
 out.mkdir(parents=True);frozen=out/'fixture';shutil.copytree(base,frozen);source=out/'source'
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(source)
 (source/'tools').mkdir(exist_ok=True)
 for name in ['overlays.py','bindings.py','module_bindings.py']:shutil.copy2(ROOT/'tools'/name,source/'tools'/name)
 shutil.copy2(ROOT/'src/render/geos/style-typing/build.py',source/'src/render/geos/style-typing/build.py')
 shutil.copy2(D/('wide-before.s'if variant=='before'else'wide.s'),source/'src/render/geos/style-typing/wide.s')
 spec=importlib.util.spec_from_file_location('shift8_build_'+variant,source/'src/render/geos/style-typing/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);images,budget=b.build(out/'assets',frozen);identity=json.loads((frozen/'freeze.json').read_text())
 for tag,data in images.items():
  name=next(n for n in identity['names']if(frozen/'build/overlays'/f'{n}.seo').read_bytes()[5:7]==data[5:7]);old=(frozen/'build/overlays'/f'{name}.seo').read_bytes()
  if variant=='before':assert old==data,(tag,'baseline packaged byteidentity')
  (frozen/'build/overlays'/f'{name}.seo').write_bytes(data);identity['assets'][name]=hashlib.sha256(data).hexdigest()
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');(out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return frozen,budget

def run(out,base):
 variants={}
 for variant in ('before','after'):
  d=out/variant;d.mkdir();variants[variant]=component(d,base,variant)
 diff=bounds.compare(variants['before'],variants['after']);(out/'component-comparison.json').write_text(json.dumps(diff,indent=2)+'\n');print('COMPONENT',json.dumps(diff),flush=True)
 frames={};budget={}
 for variant in('before','after'):
  frozen,budget[variant]=candidate_fixture(out/('public-'+variant),base,variant);p=out/('public-gate-'+variant);p.mkdir();public.run(p,frozen);frames[variant]=json.loads((p/'result.json').read_text())
 assert len(frames['before']['frames'])==len(frames['after']['frames'])==18
 changes=[]
 for before,after in zip(frames['before']['frames'],frames['after']['frames']):
  tag=before['tag'];assert tag==after['tag'];assert(out/'public-gate-before'/(tag+'.png')).read_bytes()==(out/'public-gate-after'/(tag+'.png')).read_bytes()
  changes.append(dict(tag=tag,before=before['instructions'],after=after['instructions'],saved=before['instructions']-after['instructions']))
 result=dict(status='passed',base=str(base),component=diff,budget=budget,public18=changes,new_BSS=0,new_ZP=0,scope='Private optional C32/R30 variants. Actual existing1456 randomized primitive vectors plus explicit8..11 dirty-tail/empty/EOF/near319 geometry and17malformed-frame/attribute rejections per variant, full64KiB guards and16MiB source/history/shim.18actual public plain/style/borrower namespace transactions against full producer+independent source/font oracle; before/after18PNGs byte-identical. No native timing claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-shift8-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base.resolve())
