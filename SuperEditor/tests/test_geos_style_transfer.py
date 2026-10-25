"""Private C32 gather/scatter unroll measurement; no product/other-agent writes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,inspect,json,random,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_style_transaction as actual
import test_geos_fold_editor as fold
BASE=ROOT/'build/geos-incremental-editor/20261025T115828132288Z/fixture'
D=ROOT/'src/render/geos/style-transfer-candidate'
VARIANTS=('before','unroll4','unroll8','unroll40')

def load_builder():
 spec=importlib.util.spec_from_file_location('transfer_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);return b

def build_stage(out,base,variant):
 images,budget=load_builder().build(out,base,variant)
 images['window']=(base/'build/overlays/window.seo').read_bytes()
 if variant=='before':
  for tag,slot,identity in [('stage',1,32),('worker',0,30),('window',1,6)]:
   original=next(p.read_bytes()for p in(base/'build/overlays').glob('*.seo')if p.read_bytes()[5:7]==bytes([slot,identity]))
   assert images[tag]==original,('baseline differs from actual packaged47',tag)
  budget['packaged_byte_identity']=True
 return images,budget

def build_leaf(out,base,variant):
 out.mkdir(parents=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];text=(D/('transaction-'+variant+'.s')).read_text();start=text.index('scanlines:\n');text=text[start:text.index('.segment "RODATA"',start)]
 prefix='''.setcpu "6502"
.macpack longbranch
.importzp text_ptr,screen_ptr
.export scanlines
F=$8A80
GT_TOP=2
GT_BASE=$8400
COPY=$8BD8
LINE=$8BDB
.segment "CODE"
'''
 (out/'leaf.s').write_text(prefix+text);(out/'loans.s').write_text(f'.exportzp text_ptr,screen_ptr\ntext_ptr=${s["text_ptr"]:02X}\nscreen_ptr=${s["screen_ptr"]:02X}\n');objects=[]
 for name in('leaf','loans'):
  obj=out/(name+'.o');subprocess.run(['ca65','-g','-o',str(obj),str(out/(name+'.s'))],check=True);objects.append(obj)
 (out/'leaf.cfg').write_text('MEMORY {I:file=%O,start=$A000,size=$1000;} SEGMENTS {CODE:load=I,type=ro;}')
 subprocess.run(['ld65','-C',str(out/'leaf.cfg'),'-o',str(out/'leaf.bin'),'-Ln',str(out/'leaf.lbl'),'-m',str(out/'leaf.map'),*map(str,objects)],check=True)
 raw=(out/'leaf.bin').read_bytes();labels={p[2].lstrip('.'):int(p[1],16)for line in(out/'leaf.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'}
 return raw,labels

def component(out,base,variant):
 out.mkdir();frozen=out/'fixture';shutil.copytree(base,frozen);raw,s=build_leaf(out/'leaf',frozen,variant)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);records=[];rng=random.Random(0x6510C032)
 try:
  f.source(fold.geos.native_text('Actual source and history must survive.\rTail.'));f.command(99);f.position(12);f.render();f.key(ord('X'));f.put('se_f_owner',4,1);f.m.load(0xa000,raw);canonical=f.canonical();reu=f.reu()
  for top in range(16,184):
   for direction in(0,1):
    for pattern in range(4):
     bitmap=bytes(640)if pattern==0 else bytes([255])*640 if pattern==1 else bytes((i*31+top)&255 for i in range(640))if pattern==2 else bytes(rng.randrange(256)for _ in range(640))
     linear=bytes([0xa5])*360 if pattern<2 else bytes(rng.randrange(256)for _ in range(360))
     f.m.load(0x8000,bitmap);f.m.load(0x8400,linear);f.m.write(0x8a82,top);f.m.write(0x8bd8,direction);f.m.write(0x8bdb,0xa7)
     before=f.read(0,65536);r,n=f.fast_call(s['scanlines']);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];want[0x8bdb]=9
     for name in('text_ptr','screen_ptr'):a=f.s[name];want[a:a+2]=after[a:a+2]
     for line in range(9):
      y=(top&7)+line
      for col in range(40):
       pixel=0x8000+(y//8)*320+(y&7)+col*8;byte=0x8400+line*40+col
       if direction:want[pixel]=linear[line*40+col]
       else:want[byte]=bitmap[pixel-0x8000]
     assert after==want,('full64KiB gather/scatter',variant,top,direction,pattern,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
     assert int.from_bytes(after[f.s['text_ptr']:f.s['text_ptr']+2],'little')==0x8568
     assert int.from_bytes(after[f.s['screen_ptr']:f.s['screen_ptr']+2],'little')==0x8280+(top&7)
     records.append(dict(top=top,direction=direction,pattern=pattern,instructions=n,sha256=hashlib.sha256(after[0x8000:0x8280]+after[0x8400:0x8568]).hexdigest()))
  assert f.canonical()==canonical and f.reu()==reu and f.read(0xc600,1024)==f.shim
  result=dict(status='passed',variant=variant,bytes=len(raw),cases=len(records),records=records,wholeRAM=65536,wholeREU=16777216,source_history_shim=True,scope='Exact extracted internal helper with actual top16..183, both directions and four dirty-data patterns. Trusted already-admitted frame seam; no standalone owner guard/API claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPONENT',variant,len(raw),len(records),flush=True);return result
 finally:f.close()

def transaction(out,base,variant):
 out.mkdir();source=inspect.getsource(actual.run);start=source.index(" frozen=out/'fixture';");end=source.index('\n fold.geos.grid.editor_fixture',start)
 source=source[:start]+" frozen=out/'fixture';shutil.copytree(base,frozen);images,budget=build_stage(out/'candidate',frozen,variant)"+source[end:]
 source=source.replace("f.m.write(0xcf90,0);start=f.total_instructions;f.render()","f.m.write(0xcf90,0);f.m.write(0xcfe8,0);start=f.total_instructions;f.render()")
 namespace=dict(vars(actual),build_stage=build_stage,variant=variant);exec(compile(source,str(out/'executed-transaction.py'),'exec'),namespace);(out/'executed-transaction.py').write_text(source);r=namespace['run'](out,base,False);print('TRANSACTION',variant,'frames',len(r['frames']),'faults',len(r['faults']),'raw',r['budget']['stage_raw'],flush=True);return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--component-only',action='store_true');a=p.parse_args();out=ROOT/'build/geos-style-transfer'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);components={};budgets={};transactions={}
 for variant in VARIANTS:
  _,budgets[variant]=build_stage(out/('fit-'+variant),a.fixture.resolve(),variant)
  components[variant]=component(out/('component-'+variant),a.fixture.resolve(),variant)
 reference=components['before']['records'];comparisons={}
 for variant in VARIANTS[1:]:
  records=components[variant]['records'];savings=[]
  for a0,b in zip(reference,records):
   assert {k:v for k,v in a0.items()if k!='instructions'}=={k:v for k,v in b.items()if k!='instructions'}
   savings.append(a0['instructions']-b['instructions'])
  total=sum(r['instructions']for r in reference);comparisons[variant]=dict(component_bytes=components[variant]['bytes'],component_delta=components[variant]['bytes']-components['before']['bytes'],stage_raw=budgets[variant]['stage_raw'],stage_raw_delta=budgets[variant]['stage_raw']-budgets['before']['stage_raw'],instructions_saved=sum(savings),percent_saved=round(sum(savings)*100/total,3),min_saved=min(savings),max_saved=max(savings))
 if not a.component_only:
  for variant in VARIANTS:transactions[variant]=transaction(out/('transaction-'+variant),a.fixture.resolve(),variant)
 result=dict(status='passed',fixture=str(a.fixture),component_cases_each=len(reference),comparisons=comparisons,transactions=transactions,budgets=budgets,newBSS=0,newZP=0,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPLETE',out,flush=True);print(json.dumps({k:v for k,v in result.items()if k not in('transactions','budgets')},indent=2),flush=True)
if __name__=='__main__':main()
