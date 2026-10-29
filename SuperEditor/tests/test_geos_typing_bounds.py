"""Private byte-bounds shift shortcuts: actual wide vectors and independent normal.

No product/other-agent edits. Trusted caret-free base/glyph transport seam only;
64KiB per-call write guards and source/whole16MiB guards remain explicit.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,difflib,hashlib,inspect,json,random,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_style_wide_patch as wide_test
import test_geos_fold_editor as fold
from test_geos_typing_candidate import bits,packed,at
BASE=ROOT/'build/geos-incremental-editor/20261025T112646631270Z/fixture'
SOURCE=ROOT/'src/render/geos/typing-bounds-candidate'

def build_component(out,base,variant,wide):
 out.mkdir(parents=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];tag='wide'if wide else'normal';source=SOURCE/(tag+('-before'if variant=='before'else'')+'.s')
 (out/'loans.s').write_text(f'.exportzp gt_base,gt_bitmap\ngt_base=${s["text_ptr"]:02x}\ngt_bitmap=${s["screen_ptr"]:02x}\n')
 # Freeze both ABI includes for reproducibility. No generated shared outputs.
 for name in ('render/geos/typing/buffered-api.inc','render/geos/style-typing-candidate/wide.inc'):
  p=out/'include'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'src'/name,p)
 objects=[]
 for name,p in [('primitive',source),('loans',out/'loans.s')]:
  obj=out/(name+'.o');subprocess.run(['ca65','-g','-I',str(out/'include'),'-o',str(obj),str(p)],check=True);objects.append(obj)
 cfg=out/'component.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$A000,size=$1000,type=ro;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 subprocess.run(['ld65','-C',str(cfg),'-o',str(out/'component.bin'),'-Ln',str(out/'component.lbl'),'-m',str(out/'component.map'),*map(str,objects)],check=True)
 raw=(out/'component.bin').read_bytes();symbols={p[2].lstrip('.'):int(p[1],16)for line in(out/'component.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'}
 text=subprocess.run(['od65','--dump-segments',str(objects[0])],capture_output=True,text=True,check=True).stdout;segments={n:int(v)for n,v in re.findall(r'Name:\s+"([^\"]+)".*?Size:\s+(\d+)',text,re.S)}
 assert all(segments.get(n,0)==0 for n in('BSS','DATA','ZEROPAGE'))
 (out/'sizes.json').write_text(json.dumps(dict(payload_bytes=len(raw),segments=segments),indent=2)+'\n');return raw,symbols

def wide_faults(f,s):
 F=0x8a80;B=0x8400;T=0x8580;faults=[]
 changes=[(0,2),(1,1),(1,255),(2,15),(2,184),(3,0),(3,12),(8,0),(8,12),(5,2),(7,2),(10,1),(11,1)]
 changes+=list(('attr',i)for i in(0,39,40,79))
 for field,value in changes:
  frame=bytes([0,0,25,5])+bytes([5,0,160,0,5,0x16])+bytes([0xf8,0])*9+b'\xa7'*(105-28)
  f.m.load(F,frame);f.m.load(B,b'\xa5'*360);f.m.load(T,b'\xa7'*40);f.m.load(0x4000+3*40,b'\x16'*80)
  if field=='attr':f.m.write(0x4000+3*40+value,0x76)
  else:f.m.write(F+field,value)
  before=f.read(0,65536);r,n=f.fast_call(s['se_typing_patch']);after=f.read(0,65536)
  assert r.p&1 and r.a==0x90,('wide refusal',field,value,r.a,r.p)
  wanted=bytearray(before);wanted[F+29:F+105]=after[F+29:F+105];wanted[0x100:0x200]=after[0x100:0x200]
  for name in('text_ptr','screen_ptr'):a=f.s[name];wanted[a:a+2]=after[a:a+2]
  assert after==wanted,('wide malformed64KiB write guard',field,value,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))
  faults.append(dict(field=field,value=value,error=r.a))
 return faults

def original_wide(out,base,variant):
 # Reuse the exact existing1456 vectors, RNG seed and independent pixel oracle.
 # Only the source builder and added per-case differential records change.
 source=inspect.getsource(wide_test.run)
 start=source.index(" frozen=out/'fixture';");end=source.index('\n fold.geos.grid.editor_fixture',start)
 source=source[:start]+" frozen=out/'fixture';shutil.copytree(base,frozen);image,s=build_component(out/'component',frozen,variant,True);records=[]"+source[end:]
 needle="peak=max(peak,n);assert not r.p&1"
 replacement="peak=max(peak,n);records.append(dict(op=op,x=x,advance=advance,oldwidth=oldwidth,top=top,caret=caret,instructions=n,sha256=hashlib.sha256(after[B:B+360]+after[TEMP:TEMP+40]+after[0x6000:0x7f40]+after[0x4000:0x43e8]).hexdigest()));assert not r.p&1"
 assert source.count(needle)==1;source=source.replace(needle,replacement)
 source=source.replace('  assert f.canonical()==canonical', '  malformed=wide_faults(f,s)\n  assert f.canonical()==canonical')
 source=source.replace("payload_bytes=len(image),cases=cases,","payload_bytes=len(image),cases=cases,records=records,faults=malformed,")
 source=source.replace("print(result);return result","print('WIDE',variant,'PASS',cases,'payload',len(image),'peak',peak,flush=True);return result")
 namespace=dict(vars(wide_test),build_component=build_component,variant=variant,hashlib=hashlib,wide_faults=wide_faults);exec(compile(source,str(out/'executed-wide-gate.py'),'exec'),namespace);(out/'executed-wide-gate.py').write_text(source);return namespace['run'](out,base)

def vectors():
 rng=random.Random(0x6510B0);v=[]
 # New deterministic normal1024, not mislabeled as a historical existing gate.
 for i in range(1024):
  op=i&1;adv=(i//2)%8+1
  width=rng.randrange(adv if op else 0,320 if op else 320-adv)
  xmax=width-adv if op else width
  x=[0,xmax,min(7,xmax),min(8,xmax),min(15,xmax),min(16,xmax),rng.randrange(xmax+1),rng.randrange(xmax+1)][(i//16)%8]
  glyph=bytes((rng.randrange(256)&(255<<(8-adv)))for _ in range(9));base=bytes(rng.randrange(256)for _ in range(360))
  v.append(dict(op=op,x=x,advance=adv,oldwidth=width,top=16+i%168,glyph=glyph,caret=1+(i%8),base=base))
 return v

def normal(out,base,variant):
 frozen=out/'fixture';shutil.copytree(base,frozen);image,s=build_component(out/'component',frozen,variant,False)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);records=[];faults=0;F=0x8b40;B=0x8400;T=0x8580
 def check(v,mutate=None,error=None):
  nonlocal faults
  op,x,adv,width,top,glyph,caret,base=(v[n]for n in('op','x','advance','oldwidth','top','glyph','caret','base'))
  frame=bytes([op,0,top,adv])+x.to_bytes(2,'little')+width.to_bytes(2,'little')+bytes([caret,0x16])+glyph+b'\xa7'*(96-19)
  f.m.load(F,frame);f.m.load(B,base);f.m.load(T,b'\xa7'*40);f.m.load(0x4000+(top//8)*40,b'\x16'*80)
  for row in range(9):
   for col in range(40):f.m.write(at(top+row,col),(row*31+col*13)&255)
  if mutate:mutate()
  before=f.read(0,65536);r,n=f.fast_call(s['se_typing_patch']);after=f.read(0,65536);want=bytearray(before);want[F+20:F+96]=after[F+20:F+96];want[0x100:0x200]=after[0x100:0x200]
  for name in('text_ptr','screen_ptr'):a=f.s[name];want[a:a+2]=after[a:a+2]
  if error:
   assert r.p&1 and r.a==error;faults+=1
  else:
   assert not r.p&1 and r.a==0 and after[F+19]==1
   want[F+19]=1;want[T:T+40]=after[T:T+40]
   for row in range(9):
    old=bits(base[row*40:(row+1)*40]);ink=bits(glyph[row:row+1])[:adv];new=old[:x]+(ink+old[x:width]if op==0 else old[x+adv:width]);new=(new+[0]*320)[:320];want[B+row*40:B+(row+1)*40]=packed(new);cx=x+adv if op==0 else x
    for p in range(cx,min(320,cx+caret)):new[p]^=1
    for col,value in enumerate(packed(new)):want[at(top+row,col)]=value
   records.append(dict(op=op,x=x,advance=adv,oldwidth=width,top=top,caret=caret,instructions=n,sha256=hashlib.sha256(after[B:B+360]+after[T:T+40]+after[0x6000:0x7f40]+after[0x4000:0x43e8]).hexdigest()))
  assert after==want,('normal full64KiB guard/oracle',variant,v,{hex(i):(a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b})
 try:
  data=fold.geos.native_text('Plain body for bounded shift.\rTail.');f.source(data);f.command(99);f.position(11);f.render();f.key(ord('X'));f.put('se_f_owner',4,1);f.m.load(0xa000,image);canonical=f.canonical();reu=f.reu()
  for v in vectors():check(v)
  v=dict(op=0,x=5,advance=5,oldwidth=160,top=25,glyph=b'\xf8'*9,caret=5,base=bytes([0xa5])*360)
  for field,value in [(0,2),(1,1),(1,255),(2,15),(2,184),(3,0),(3,9),(8,0),(8,9),(5,2),(7,2)]:check(v,lambda field=field,value=value:f.m.write(F+field,value),0x90)
  for op,x,adv,width in [(0,10,8,313),(0,161,5,160),(1,158,5,160),(1,0,8,7)]:check(dict(v,op=op,x=x,advance=adv,oldwidth=width),error=0x90)
  check(dict(v,glyph=b'\1'*9),error=0x90)
  for off in(0,39,40,79):check(v,lambda off=off:f.m.write(0x4000+(v['top']//8)*40+off,0x76),0x90)
  assert f.canonical()==canonical and f.reu()==reu and f.read(0xc600,1024)==f.shim
  result=dict(status='passed',payload_bytes=len(image),cases=len(records),faults=faults,records=records,scope='New deterministic1024 normal direct primitive cases with randomized dirty input tails; full64KiB/pixels/base/attrs/source/REU guard, no root integration claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('NORMAL',variant,'PASS',len(records),'faults',faults,'payload',len(image),flush=True);return result
 finally:f.close()

def compare(before,after):
 assert len(before['records'])==len(after['records']);savings=[]
 for a,b in zip(before['records'],after['records']):
  assert {k:v for k,v in a.items()if k!='instructions'}=={k:v for k,v in b.items()if k!='instructions'},('differential output mismatch',a,b)
  savings.append(a['instructions']-b['instructions'])
 total0=sum(a['instructions']for a in before['records']);total1=sum(a['instructions']for a in after['records'])
 ordered=sorted(zip(savings,before['records'],after['records']),key=lambda v:v[0])
 return dict(cases=len(savings),payload_before=before['payload_bytes'],payload_after=after['payload_bytes'],code_delta=after['payload_bytes']-before['payload_bytes'],instructions_before=total0,instructions_after=total1,saved=sum(savings),percent_saved=round((total0-total1)*100/total0,3),min_saved=min(savings),max_saved=max(savings),regressions=sum(v<0 for v in savings),worst=dict(saved=ordered[0][0],before=ordered[0][1],after=ordered[0][2]),best=dict(saved=ordered[-1][0],before=ordered[-1][1],after=ordered[-1][2]))

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--wide-only',action='store_true');a=p.parse_args();out=ROOT/'build/geos-typing-bounds'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);results={}
 for tag in(['wide']if a.wide_only else['wide','normal']):
  variants={}
  for variant in('before','after'):
   d=out/(tag+'-'+variant);d.mkdir();variants[variant]=original_wide(d,a.fixture.resolve(),variant)if tag=='wide'else normal(d,a.fixture.resolve(),variant)
  results[tag]=compare(variants['before'],variants['after'])
 result=dict(status='passed',fixture=str(a.fixture.resolve()),comparisons=results,wholeRAM_per_call=65536,REU=16777216,newBSS=0,newZP=0,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
