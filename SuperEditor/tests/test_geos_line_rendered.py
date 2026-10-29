"""Actual flag-gated sparse canonical GEOS geometry, independent stream oracle."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,re,subprocess,sys,zipfile,random,hashlib
import test_geos_line as old
ROOT=old.ROOT;F=old.F;DEFAULT=ROOT/'build/geos-pan-dispatch/20261025T040756394080Z/fixture'

def command(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
def build(out,previous):
 out.mkdir(parents=True,exist_ok=True);old.OUT=out
 cfg=out/'line.cfg';cfg.write_text('MEMORY { C:file=%O,start=$1000,size=$3000,type=rw; }\nSEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }\n')
 common=[]
 for name in ['render/geos/line-probe','render/geos/measure','render/geos/assets','tui/petscii']:
  obj=out/(name.replace('/','-')+'.o');command('ca65','-g','-I','src','-o',obj,'src/'+name+'.s');common.append(obj)
 for variant,flags in [('line',['-D','SE_EDITOR_GEOS_RENDERED=1']),('generic',[])]:
  obj=out/(variant+'.o');command('ca65','-g',*flags,'-I','src','-o',obj,'src/render/geos/line.s')
  command('ld65','-C',cfg,'-o',out/(variant+'.bin'),'-Ln',out/(variant+'.lbl'),'-m',out/(variant+'.map'),obj,*common)
 archive=previous/'product-sources.zip';before=out/'generic-source'
 with zipfile.ZipFile(archive) as z:
  for name in ['src/render/geos/line.s','src/render/geos/line.inc','src/render/geos/line-map.s']:
   p=before/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 command('ca65','-g','-I',before/'src','-I','src','-o',out/'previous.o',before/'src/render/geos/line.s')
 command('ld65','-C',cfg,'-o',out/'previous.bin',out/'previous.o',*common)
 assert (out/'generic.bin').read_bytes()==(out/'previous.bin').read_bytes(),'flag-absent generic binary changed'
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'line.lbl').read_text())}
 assert len((out/'line.bin').read_bytes())<=4096
 return labels
class Fixture(old.Fixture):
 def call(self,name,error=None,ctx=F,guard=True):
  before=self.read(0,65536) if guard else None
  n=super().call(name,error,ctx,False)
  if guard:
   after=self.read(0,65536);want=bytearray(before)
   for a,size in [(F,832),(0x4400,486),(0x47F3,9),(0xF0,4),(0x100,256)]:want[a:a+size]=after[a:a+size]
   assert after==want,('fullRAM/font/source/shim/ledger guard',name,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  return n
 def packet(self,data,styles,advances,anchor,hidden):
  mask=bytearray(4)
  for i,h in enumerate(hidden):
   if h:mask[i>>3]|=128>>(i&7)
  self.m.load(0x90A0,mask);self.put(94,0x90A0,2)
  super().packet(data,styles,advances,anchor)

def oracle(data,adv,hidden,start,width,mode,pan,caret,base):
 i=start;x=0;last=None;reason=2;visible=[];pending=0
 while i<len(data):
  if hidden[i] and data[i]!=13:i+=1;continue
  if pending:reason=pending;end=next_=i;break
  if data[i]==13:reason=1;end=i;next_=i+1;break
  a=adv[i]
  if not mode and x+a>width:
   if not visible:
    visible.append((i,x,x+a));i+=1;x+=a;pending=6;continue
   if last:end=next_=last[0];x=last[1];reason=4
   else:end=next_=i;reason=5
   break
  visible.append((i,x,x+a));x+=a;i+=1
  if data[i-1]==32:last=(i,x)
  if not mode and x==width:pending=3
 else:end=next_=i;reason=pending or 2
 visible=[v for v in visible if v[0]<end]
 chosen=visible
 if mode:chosen=[v for v in visible if v[2]>pan and v[1]<pan+width]
 if chosen:
  first=visible.index(chosen[0]);last_index=visible.index(chosen[-1]);left0=base+(visible[first-1][0]+1 if first else start)
  anchors=[base+v[0] for v in chosen]+[base+(visible[last_index+1][0] if last_index+1<len(visible) else end)]
  maps=[max(0,min(width,chosen[0][1]-(pan if mode else 0)))]+[max(0,min(width,v[2]-(pan if mode else 0))) for v in chosen]
 else:
  left0=base+(visible[-1][0]+1 if visible else start);anchors=[base+end];maps=[max(0,min(width,x-(pan if mode else 0)))]
 valid=(start<=caret<end) or(caret==end and reason in (1,2))
 caretx=sum(adv[p] for p in range(start,min(caret,len(data))) if not hidden[p] or data[p]==13) if valid else None
 return dict(reason=reason,end=base+end,next=base+next_,x=x,first=anchors[0],anchors=anchors,left0=left0,maps=maps,caretx=caretx)

def run(out,previous,smoke=False):
 s=build(out/'leaf',previous);f=Fixture(s);rng=random.Random(26020);cases=[];faults=[];hits=0;packets=0
 def check(data,hidden,*,base=0,width=320,mode=0,pan=0,adv=None,caret=None,sizes=(32,),encoding=1,styles=None,all_lines=True):
  nonlocal hits,packets
  styles=bytes(len(data)) if styles is None else styles;adv=f.advance(data,styles) if adv is None else adv;caret=len(data)//2 if caret is None else caret;start=0
  for _ in range(3000):
   want=oracle(data,adv,hidden,start,width,mode,pan,caret,base);f.begin(base+start,width,pan,mode,encoding,base+caret);at=start;k=0
   while f.get('state',1)==1:
    if at==len(data):f.call('finish');break
    n=min(sizes[k%len(sizes)],len(data)-at);k+=1
    f.packet(data[at:at+n],styles[at:at+n],adv[at:at+n],base+at,hidden[at:at+n]);used=f.get('used',1);at+=used;packets+=1
    assert f.get('scan')==base+at and(used or f.get('state',1)==2)
   got={n:f.get(n,1 if n=='reason' else 3) for n in ('reason','end','next','x','first')}
   assert got=={n:want[n] for n in got},('geometry',start,got,want)
   count=f.get('count',2);assert count<=161
   maps=[int.from_bytes(f.read(F+176+i*2,2),'little') for i in range(count+1)]
   anchors=[int.from_bytes(f.read(0x4400+i*3,3),'little') for i in range(count+1)]
   assert maps==want['maps'] and anchors==want['anchors'],('maps',start,maps,anchors,want)
   assert int.from_bytes(f.read(0x47F3,3),'little')==want['left0'],('LEFT0',start,f.read(0x47F3,3).hex(),want)
   assert f.get('rewind',1)==int(f.get('next')<f.get('scan'))
   assert f.get('caretvalid',1)==int(want['caretx'] is not None),('caret valid',caret,want)
   if want['caretx'] is not None:assert f.get('caretx')==want['caretx']
   for x in sorted({0,width,width+1,65535,*maps,*((a+b)//2 for a,b in zip(maps,maps[1:]))}):
    f.put(30,x,2);f.call('hit');index=min(range(len(maps)),key=lambda i:(abs(maps[i]-min(width,x)),-i))
    assert f.get('hitindex',2)==index and f.get('hitsource')==anchors[index],('actual canonical HIT',x,maps,anchors,index,f.get('hitsource'));hits+=1
   cases.append(dict(length=len(data),start=start,base=base,width=width,mode=mode,pan=pan,visible=count,reason=want['reason'],anchors=anchors,caret=caret,packets=k))
   (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
   if not all_lines or want['reason']==2:break
   next_=want['next']-base;assert next_>start;start=next_
  else:raise AssertionError('line convergence')
 try:
  data=b'**A**B\r';check(data,[1,1,0,1,1,0,0],adv=[4]*len(data),caret=4,sizes=(1,2,3,32))
  print('FIRST SPARSE GEOMETRY PASS: hidden zero-width, canonical anchors/HIT, generic binary unchanged',flush=True)
  if not smoke:
   for text in [b'',b'***',b' **A** B **C** ',b'A   B CDEFGHIJ',b'AA**BB** CC**DD** EE',b'**AB**\r**CD**\r',b'@@@@A@@@@',b'AB**']:
    hidden=[c in b'*@' for c in text]
    for mode,pan,width in [(0,0,8),(0,0,12),(0,0,320),(1,0,320),(1,1,320),(1,9,20),(1,100,320)]:
     check(text,hidden,width=width,mode=mode,pan=pan,adv=[4]*len(text),base=65520,sizes=(1,7,32))
   # Full-width and overwide final glyphs absorb a hidden suffix before publish.
   for data,width,advance in [(b'A***B',4,4),(b'A***',4,4),(b'A***B',2,4),(b'***A***',2,4)]:
    check(data,[c==42 for c in data],width=width,adv=[advance]*len(data),sizes=(1,),base=0x10000)
   # A160-cell viewport can intersect161 glyphs when pan cuts both edge cells.
   data=b'W'*180;check(data,[False]*len(data),mode=1,pan=1,adv=[2]*len(data),caret=160)
   # Native font advances/styles are measured by the actual packed-font module.
   data=b'**Wim** mixed @@code@@ suffix\r'
   check(data,[c in b'*@' for c in data],encoding=0,styles=bytes(i%4 for i in range(len(data))),width=80,sizes=(3,32,1))
   for _ in range(30):
    n=rng.randrange(1,200);data=bytes(rng.choice([65,66,32,13,42]) for _ in range(n));hidden=[c==42 and bool(rng.randrange(2)) for c in data]
    mode=rng.randrange(2);check(data,hidden,width=rng.choice([7,19,320]),mode=mode,pan=rng.randrange(40) if mode else 0,adv=[rng.randrange(2,10) for _ in data],base=0xFF00,sizes=(rng.randrange(1,33),))
   # No16-bit source-span or128-byte line limit. Hidden bytes remain canonical.
   for data,hidden in [(b'A'+b'*'*66000+b'B',[False]+[True]*66000+[False]),(b'*'*70001,[True]*70001)]:
    check(data,hidden,mode=1,pan=0,adv=[4]*len(data),base=65520,caret=40000,sizes=(32,))
   # Literal NULL-mask input is still a supported rendered producer.
   f.begin(0,width=320,encoding=1);f.put(94,0,2);f.m.load(0x9040,b'A');f.m.load(0x9080,b'\x04');f.put(26,0,3);f.put(29,1,1);f.call('step');f.call('finish');assert f.get('count',2)==1
   # Capacity failure is bounded and cannot overwrite the162-anchor ledger.
   f.begin(0,width=320,encoding=1);data=b'A'*32
   for block in range(5):f.packet(data,bytes(32),bytes([1])*32,block*32,[False]*32)
   f.packet(b'A',b'\0',b'\1',160,[False]);assert f.get('count',2)==161
   f.m.load(0x9040,b'A');f.m.load(0x9080,b'\1');f.m.load(0x90A0,b'\0'*4);f.put(26,161,3);f.put(29,1,1);f.call('step',error=0x90);faults.append('162nd visible glyph refused before ledger overflow')
   f.begin(0xFFFFFF,encoding=1);f.m.load(0x9040,b'*');f.m.load(0x90A0,b'\x80');f.put(94,0x90A0,2);f.put(26,0xFFFFFF,3);f.put(29,1,1);f.call('step',error=0x7B);faults.append('hidden canonical24-bit overflow refused')
   f.begin(0);f.put(29,33,1);f.call('step',error=0x90);f.put(29,1,1);f.put(26,1,3);f.call('step',error=0x74);f.call('begin',error=0x90,ctx=0xC600);faults.append('packet count/source/context admission guards retained')
  assert f.reu()==f.reu_before
  result=dict(status='passed',cases=cases,hit_tests=hits,packets=packets,faults=faults,payload_bytes=len((out/'leaf/line.bin').read_bytes()),generic_bytes=len((out/'leaf/generic.bin').read_bytes()),generic_sha256=hashlib.sha256((out/'leaf/generic.bin').read_bytes()).hexdigest(),new_BSS=0,new_ZP=0,ledger_bytes=486,witness_bytes=9,peak_instructions=f.peak,scope='Actual rendered-flag line geometry/HIT and packed measure; no C20/frontend/native claim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',lines=len(cases),hits=hits,packets=packets,payload_bytes=result['payload_bytes'],faults=len(faults),out=str(out)),indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-line-rendered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture,a.smoke)
