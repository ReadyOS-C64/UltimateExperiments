"""Isolated bounded fold-hint transform with actual typed objects/REU DMA.

Only build/fold-transform and evidence; no editor/sharedbuild/VICE. Hints are
never a parsed/published fold map. Fresh parser identity+ancestry is mandatory.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,ctypes as C,hashlib,json,random,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from test_fold_leaves import runner,labels
from test_folds import Fold,valid_model
SOURCES=['reu/provider','reu/dma','object/state','object/validate','object/allocate','object/resize','object/copy','fold/transform','fold/probe']

def build(out):
 (out/'probe.cfg').write_text('''MEMORY { CORE:file=%O,start=$1000,size=$3000,fill=yes; TRANSFORM:file=%O,start=$4000,size=$1000,fill=yes; OBJ:file="",start=$9E00,size=$0200; STATE:file="",start=$A000,size=$0800; } SEGMENTS { CODE:load=CORE,type=ro; FOLD_TRANSFORM:load=TRANSFORM,type=ro,define=yes; OBJECTS:load=OBJ,type=bss; BSS:load=STATE,type=bss; }''')
 objs=[]
 for name in SOURCES:
  obj=out/(name.replace('/','-')+'.o');subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(obj),str(ROOT/'src'/f'{name}.s')],check=True);objs.append(obj)
 subprocess.run(['ld65','-C',str(out/'probe.cfg'),'-o',str(out/'probe.bin'),'-Ln',str(out/'probe.lbl'),'-m',str(out/'probe.map'),*map(str,objs)],check=True)
 text=subprocess.check_output(['od65','--dump-segments',str(out/'fold-transform.o')],text=True);(out/'segments.txt').write_text(text);sizes={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',text,re.S)};assert all(sizes[n]==0 for n in ['CODE','RODATA','BSS','DATA','ZEROPAGE']);return labels(out/'probe.lbl'),sizes

# Host interval/tree reasoning: not the assembler's16-slot preorder stack.
def oracle(folds,length,p,d,i):
 assert 0<=p<=length and 0<=d<=length-p and length-d+i<=0xffffff
 out=[];mapped={};dropped=0
 for index,f in enumerate(folds):
  parent_ok=f.parent==65535 or f.parent in mapped
  intersects=(d>0 and p<f.hidden and p+d>f.start) or (d==0 and i>0 and f.start<p<f.hidden)
  cross_end=p<f.end<p+d
  s=f.start+(i-d if p<=f.start else 0)
  h=f.hidden+(i-d if p<f.hidden else 0)
  e=f.end+(i-d if p<f.end else 0)
  if not parent_ok or intersects or cross_end or not 0<=s<h<e<=length-d+i:
   dropped+=1;continue
  mapped[index]=len(out);out.append(replace(f,start=s,hidden=h,end=e,parent=65535 if f.parent==65535 else mapped[f.parent],flags=f.flags&1,saved=0,motion=0))
 return out,dropped

class Fixture:
 def __init__(self,out,s):
  self.out=out;self.s=s;self.dll=runner(out);self.m=Machine();self.m.load(0x1000,(out/'probe.bin').read_bytes());self.calls=0;self.peak=0;self.dma_peak=0
  self.put('se_reu_banks',64,2);assert not self.call('se_reu_provider_init').p&1;assert not self.call('se_object_init').p&1
  for logical,physical in [(200,2),(201,4)]:assert not self.call('se_reu_bind',99,logical,physical).p&1
  self.input=self.create(0x46,16);self.output=self.create(0x46,16);self.foreign=self.create(0x47,2)
  self.write_object(self.foreign,bytes((i*73+29)&255 for i in range(100003)))
  self.shim=bytes((i*37+17)&255 for i in range(1024));self.m.load(0xC600,self.shim)
 def close(self):self.m.close()
 def ram(self,a,n):
  a=self.s[a] if isinstance(a,str) else a;b=C.create_string_buffer(n);self.dll.fl_ram(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(4*1024*1024);self.dll.fl_reu(self.m.handle,len(b),b);return b.raw
 def put(self,n,v,w=1):self.m.load(self.s[n],v if isinstance(v,bytes) else v.to_bytes(w,'little'))
 def get(self,n,w=1):return int.from_bytes(self.ram(n,w),'little')
 def call(self,n,a=0,x=0,y=0,hook=None,extra_allowed=()):
  before=self.ram(0,65536) if n.startswith('se_ft_') else None
  for field,v in [('pc',self.s[n]),('a',a),('x',x),('y',y),('p',0x24),('sp',0xfd)]:getattr(self.m.lib,'zeropage_peddle_set_'+field)(self.m.handle,v)
  self.m.write(0x1fe,0xfe);self.m.write(0x1ff,2);dma=self.get('se_reu_dma_calls',2)
  if hook is None:used=self.dll.fl_run(self.m.handle,100000)
  else:
   start=self.m.regs().instructions;hit=False
   for _ in range(100000):
    regs=self.m.regs()
    if regs.pc==0x2ff:break
    if not hit and regs.pc==self.s['se_object_copy'] and regs.a==0:hook();hit=True
    self.m.lib.zeropage_peddle_step_instruction(self.m.handle)
   assert hit;used=self.m.regs().instructions-start
  assert used and self.m.regs().pc==0x2ff,(n,'nonreturn',hex(self.m.regs().pc));r=self.m.regs()
  if before is not None:
   self.calls+=1;self.peak=max(self.peak,used);delta=(self.get('se_reu_dma_calls',2)-dma)&65535;self.dma_peak=max(self.dma_peak,delta);assert delta<=2
   after=self.ram(0,65536);want=bytearray(before)
   allowed=[(0x100,0x200),(self.s['se_ft_input'],self.s['se_ft_frame_end']),(self.s['se_object_id'],self.s['copy_left']+2),(self.s['se_reu_c64'],self.s['dma_physical']+1),(0xdf00,0xdf0b)]
   for lo,hi in [*allowed,*extra_allowed]:want[lo:hi]=after[lo:hi]
   assert after==want,(n,'RAM/source/shim/phaseprefix/ZPguard',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  return r
 def create(self,type_,banks):
  assert not self.call('se_object_create',type_,banks).p&1;token=self.ram('se_object_id',5);self.put('se_object_offset',banks*65536,3);assert not self.call('se_object_resize').p&1;return token
 def write_object(self,token,data):
  for i in range(0,len(data),1024):
   chunk=data[i:i+1024];self.m.load(0x8000,chunk);self.put('se_object_id',token);self.put('se_object_offset',i,3);self.put('se_object_length',len(chunk),2);self.put('se_object_c64',0x8000,2);assert not self.call('se_object_copy',0).p&1
 def object_bytes(self,token,n,image=None):
  image=self.reu() if image is None else image;out=bytearray()
  for j in range((n+65535)//65536):
   logical=self.m.read(self.s['object_extents']+token[0]*16+j);bank=self.m.read(self.s['se_reu_map']+logical);out.extend(image[bank*65536:bank*65536+min(n-j*65536,65536)])
  return bytes(out)
 def seed(self,folds,length,p,d,i):
  assert valid_model(folds,length);self.write_object(self.input,b''.join(f.bytes() for f in folds));self.m.load(self.s['se_ft_input'],bytes(self.s['se_ft_frame_end']-self.s['se_ft_input']))
  for n,v,w in [('se_ft_input',self.input,5),('se_ft_output',self.output,5),('se_ft_count',len(folds),2),('se_ft_length',length,3),('se_ft_position',p,3),('se_ft_delete',d,3),('se_ft_insert',i,3)]:self.put(n,v,w)
 def transform(self,folds,length,p,d,i):
  self.seed(folds,length,p,d,i);before=self.reu();expected,dropped=oracle(folds,length,p,d,i);reg=self.call('se_ft_begin');assert not reg.p&1,(p,d,i,reg.a)
  steps=0
  while self.get('se_ft_busy'):
   reg=self.call('se_ft_step');steps+=1;assert not reg.p&1,(p,d,i,reg.a,self.get('se_ft_index',2));assert steps<=len(folds)+1
   assert self.get('se_ft_valid')==int(not self.get('se_ft_busy'))
  assert reg.a==0 and self.get('se_ft_valid') and self.get('se_ft_written',2)==len(expected) and self.get('se_ft_dropped',2)==dropped and self.get('se_ft_new_length',3)==length-d+i
  after=self.reu();raw=b''.join(x.bytes() for x in expected);assert self.object_bytes(self.output,len(raw),after)==raw,(p,d,i,'recorddiff',expected,self.object_bytes(self.output,len(raw),after).hex(),raw.hex())
  want=bytearray(before)
  for j in range(0,len(raw),65536):
   logical=self.m.read(self.s['object_extents']+self.output[0]*16+(j//65536));bank=self.m.read(self.s['se_reu_map']+logical);chunk=raw[j:j+65536];want[bank*65536:bank*65536+len(chunk)]=chunk
  assert after==want,('outsideexactoutputREUguard',p,d,i)
  assert self.ram(0xC600,1024)==self.shim;return steps
 def transform_log(self,folds,length,events,pointer=0x80f9):
  self.seed(folds,length,0,0,0);packed=b''.join(v.to_bytes(3,'little') for event in events for v in event);self.m.load(pointer,packed);self.put('se_ft_log_pointer',pointer,2);self.put('se_ft_log_count',len(events));before=self.reu()
  expected=folds
  for p,d,i in events:expected,_=oracle(expected,length,p,d,i);length=length-d+i
  dma=self.get('se_reu_dma_calls',2);reg=self.call('se_ft_begin_log');assert not reg.p&1 and reg.a==1
  for _ in events:
   assert self.get('se_ft_phase')==1;reg=self.call('se_ft_step');assert not reg.p&1 and self.get('se_reu_dma_calls',2)==dma and not self.get('se_ft_valid')
  assert self.get('se_ft_phase')==2
  steps=len(events)
  while self.get('se_ft_busy'):
   reg=self.call('se_ft_step');steps+=1;assert not reg.p&1,(events,reg.a,self.get('se_ft_index',2),self.get('se_ft_log_event'));assert steps<=len(events)+(len(folds)+1)*(len(events)+2)
   assert self.get('se_ft_valid')==int(not self.get('se_ft_busy'))
  raw=b''.join(x.bytes() for x in expected);after=self.reu();assert reg.a==0 and self.get('se_ft_valid') and self.get('se_ft_written',2)==len(expected) and self.get('se_ft_dropped',2)==len(folds)-len(expected) and self.get('se_ft_new_length',3)==length
  assert self.object_bytes(self.output,len(raw),after)==raw,('log-recorddiff',events,expected,self.object_bytes(self.output,len(raw),after).hex(),raw.hex())
  want=bytearray(before)
  for j in range(0,len(raw),65536):
   logical=self.m.read(self.s['object_extents']+self.output[0]*16+(j//65536));bank=self.m.read(self.s['se_reu_map']+logical);chunk=raw[j:j+65536];want[bank*65536:bank*65536+len(chunk)]=chunk
  assert after==want and self.ram(pointer,len(packed))==packed and self.ram(0xC600,1024)==self.shim
  return steps

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/fold-transform'/stamp;out.mkdir(parents=True);s,sizes=build(out);f=Fixture(out,s);cases=[];checks=0
 try:
  one=[Fold(10,20,80,flags=3,saved=30,motion=99,lines=4)]
  for p,d,i in [(5,0,3),(30,0,3),(90,0,3)]:f.transform(one,100,p,d,i);checks+=1
  cases.append('actualtypedobjects/readwriteDMA/insertbefore-body-after/COLLAPSEDkept-SAVEDcleared')
  f.transform_log(one,100,[(5,0,3),(30,1,0),(90,0,2)]);checks+=1
  cases.append('actualBEGIN_LOG/3sequentialedits/validatebeforeDMA/hostpagecrossing/oneinput-oneoutput')
  if not args.smoke:
   tree=[Fold(5,10,400,flags=3,saved=40,lines=30,motion=91),Fold(15,20,90,0,1,flags=3,saved=40,lines=8,motion=92),Fold(30,35,70,1,2,3,3,40,4,0,93),Fold(100,110,200,0,1,2,1,lines=8,level=0),Fold(220,230,390,0,1,flags=1,lines=15),Fold(400,405,500,kind=3,flags=1,level=0),Fold(420,425,470,5,1,flags=1)]
   assert valid_model(tree,500)
   points={0,500,*[p for fold in tree for a in (fold.start,fold.hidden,fold.end) for p in (a-1,a,a+1) if 0<=p<=500]}
   for p in sorted(points):
    for d in sorted({0,1,min(7,500-p),min(47,500-p),500-p}):
     if d>500-p:continue
     for i in (0,1,13):f.transform(tree,500,p,d,i);checks+=1
   f.transform([],0,0,0,3);checks+=1
   cases.append('nestedheadings-code-regions/before-at-aftereachboundary/deletes-crossingopeners-ends/dropdescendants/denseparentremap/empty')
   high=[Fold(65530,65536,100000,flags=1),Fold(100000,100003,0xff0000,kind=3,flags=1,level=0)]
   for edit in [(0,0,1),(65530,0,2),(65536,0,3),(99999,2,0),(100003,8,8),(0xff0000,0,1),(0xfeffff,1,0)]:f.transform(high,0xff0000,*edit);checks+=1
   deepest=[Fold(i*3,i*3+1,200-i*3,65535 if i==0 else i-1,i,flags=1) for i in range(16)]
   for edit in [(20,0,3),(46,0,1),(1,0,2),(100,30,1)]:f.transform(deepest,200,*edit);checks+=1
   f.transform([Fold(i*3,i*3+1,i*3+3,flags=i&1) for i in range(2052)],6156,6145,1,0);checks+=1
   cases.append('24bit-carry/EOF/maxlength/16deep/input-and-dense-outputcross64KiBbank')
   # Admission failures never issue DMA or touch any REU byte.
   invalid=[('se_ft_position',101,3),('se_ft_delete',101,3),('se_ft_insert',0xffffff,3),('se_ft_count',32769,2),('se_ft_input',f.foreign,5),('se_ft_output',f.foreign,5),('se_ft_output',f.input,5)]
   for name,value,w in invalid:
    f.seed(one,100,5,0,3);f.put(name,value,w);before=f.reu();dma=f.get('se_reu_dma_calls',2);reg=f.call('se_ft_begin');assert reg.p&1 and reg.a==0xb0 and not f.get('se_ft_valid') and not f.get('se_ft_busy');assert f.reu()==before and f.get('se_reu_dma_calls',2)==dma;checks+=1
   for which in ['logical-overlap','physical-overlap']:
    f.seed(one,100,5,0,3);outslot=f.s['object_extents']+f.output[0]*16;inlogical=f.m.read(f.s['object_extents']+f.input[0]*16);outlogical=f.m.read(outslot)
    at=outslot if which=='logical-overlap' else f.s['se_reu_map']+outlogical;old=f.m.read(at);f.m.write(at,inlogical if which=='logical-overlap' else f.m.read(f.s['se_reu_map']+inlogical));before=f.reu();dma=f.get('se_reu_dma_calls',2);reg=f.call('se_ft_begin');assert reg.p&1 and reg.a==0xb0 and f.reu()==before and f.get('se_reu_dma_calls',2)==dma;f.m.write(at,old);checks+=1
   cases.append('invalidedit-overflow/count32769/type47/sametoken/same-typephysicalalias/refusebeforeDMA')
   # Exact24-bit limit and maximum record count admission (not a full32K scan).
   f.transform([Fold(0xffff00,0xffff10,0xffffff,flags=1)],0xffffff,0xfffffe,1,1);checks+=1
   f.seed([],0,0,0,0);f.put('se_ft_count',32768,2);reg=f.call('se_ft_begin');assert not reg.p&1;assert not f.call('se_ft_cancel').p&1;checks+=1
   for stop in (0,1,3,7):
    f.seed(tree,500,12,0,3);before=f.reu();assert not f.call('se_ft_begin').p&1
    for _ in range(stop):assert not f.call('se_ft_step').p&1
    partial=f.reu();reg=f.call('se_ft_cancel');assert not reg.p&1 and reg.a==0 and f.get('se_ft_error')==0xb3 and not f.get('se_ft_valid') and not f.get('se_ft_busy') and f.reu()==partial
    assert not f.call('se_ft_cancel').p&1;assert f.object_bytes(f.input,len(tree)*32)==b''.join(x.bytes() for x in tree);checks+=1
   cases.append('max32768-admission/cancel-partial-nevervalid/idempotence/input-retained')
   # Frozen request/epoch and actual object provider changes fail before DMA.
   for field,width in [('se_ft_input',5),('se_ft_output',5),('se_ft_count',2),('se_ft_length',3),('se_ft_position',3),('se_ft_delete',3),('se_ft_insert',3),('se_reu_epoch',2)]:
    f.seed(one,100,5,0,3);assert not f.call('se_ft_begin').p&1;at=f.s[field]+width-1;old=f.m.read(at);f.m.write(at,old^1);before=f.reu();dma=f.get('se_reu_dma_calls',2);reg=f.call('se_ft_step');assert reg.p&1 and reg.a==0xb1 and not f.get('se_ft_valid') and f.reu()==before and f.get('se_reu_dma_calls',2)==dma;f.m.write(at,old);checks+=1
   for which,error in [('generation',0x31),('logical',0xb1),('physical',0xb1)]:
    f.seed(one,100,5,0,3);assert not f.call('se_ft_begin').p&1;outslot=f.s['object_extents']+f.output[0]*16;inlogical=f.m.read(f.s['object_extents']+f.input[0]*16);outlogical=f.m.read(outslot)
    at=f.s['object_gen_lo']+f.input[0] if which=='generation' else outslot if which=='logical' else f.s['se_reu_map']+outlogical
    old=f.m.read(at);f.m.write(at,old^1 if which=='generation' else inlogical if which=='logical' else f.m.read(f.s['se_reu_map']+inlogical));before=f.reu();dma=f.get('se_reu_dma_calls',2);reg=f.call('se_ft_step');assert reg.p&1 and reg.a==error and f.reu()==before and f.get('se_reu_dma_calls',2)==dma,(which,reg.a);f.m.write(at,old);checks+=1
   f.seed(one,100,5,0,3);assert not f.call('se_ft_begin').p&1;logical=f.m.read(f.s['object_extents']+f.output[0]*16);bank=f.m.read(f.s['se_reu_map']+logical);at=f.s['se_reu_physical_owner']+bank;old=f.m.read(at);before=f.reu();reg=f.call('se_ft_step',hook=lambda:f.m.write(at,99),extra_allowed=[(at,at+1)]);assert reg.p&1 and reg.a==0x34 and f.reu()==before and not f.get('se_ft_valid');f.m.write(at,old);checks+=1
   cases.append('allfrozeninputs/providerEpoch/staletoken/sametypeextent-mappingchanges/betweenREADandWRITEownershipfault/neverforeignwrite')
   # Corrupt record schema/preorder is refused; any earlier candidate remains
   # invalid and must be discarded, never promoted as a trustworthy fold map.
   for offset,value in [(0,20),(3,10),(6,19),(9,0),(11,1),(11,16),(12,0),(12,4),(13,4),(14,1),(20,0),(25,1),(31,1)]:
    f.seed(one,100,5,0,3);raw=bytearray(one[0].bytes());raw[offset]=value;f.write_object(f.input,raw);before=f.reu();assert not f.call('se_ft_begin').p&1;reg=f.call('se_ft_step');assert reg.p&1 and reg.a==0xb0 and not f.get('se_ft_valid') and f.reu()==before,(offset,value,reg.a);checks+=1
   f.seed(tree,500,5,0,0);raw=bytearray(b''.join(x.bytes() for x in tree));raw[32+9]=5;f.write_object(f.input,raw);assert not f.call('se_ft_begin').p&1;assert not f.call('se_ft_step').p&1;reg=f.call('se_ft_step');assert reg.p&1 and reg.a==0xb0 and not f.get('se_ft_valid');checks+=1
   cases.append('schemaflags/anchors/kind/level/reserved/savedcaret/depth/preorderparent-malformed-neverpublish')
   logs=[[(1,0,3),(120,0,1),(450,1,0)],[(16,0,2),(102,0,3),(401,2,0)],[(100,120,0),(5,0,3)],[(450,1,1),(20,20,0),(399,1,1)],[(0,500,0)],[(500,0,10),(503,2,0)],[(0,0,0)]*112]
   for j,events in enumerate(logs):f.transform_log(tree,500,events,0x8410 if len(events)==112 else 0x80f9+j*0x100);checks+=1
   rng=random.Random(0xF01D20)
   for _ in range(24):
    length=500;events=[]
    for _ in range(rng.randrange(1,9)):
     p=rng.randrange(length+1);d=rng.randrange(min(length-p,50)+1);i=rng.randrange(15);events.append((p,d,i));length+=i-d
    f.transform_log(tree,500,events);checks+=1
   # Exact host end8800, descriptor bounds and invalid later event all refuse
   # before a single read/write DMA; log byte immutability is caller contract.
   f.transform_log(one,100,[(30,0,1)],0x87f7);checks+=1
   for pointer,count in [(0x7fff,1),(0x8800,1),(0x87f8,1),(0x8000,0),(0x8000,113),(0x8411,112)]:
    f.seed(one,100,0,0,0);f.put('se_ft_log_pointer',pointer,2);f.put('se_ft_log_count',count);before=f.reu();dma=f.get('se_reu_dma_calls',2);reg=f.call('se_ft_begin_log');assert reg.p&1 and reg.a==0xb0 and f.reu()==before and f.get('se_reu_dma_calls',2)==dma;checks+=1
   for events in [[(5,0,1),(101,1,0)],[(5,0,1),(0,0,0xffffff)]]:
    f.seed(one,100,0,0,0);f.m.load(0x8000,b''.join(v.to_bytes(3,'little') for event in events for v in event));f.put('se_ft_log_pointer',0x8000,2);f.put('se_ft_log_count',2);before=f.reu();dma=f.get('se_reu_dma_calls',2);assert not f.call('se_ft_begin_log').p&1;assert not f.call('se_ft_step').p&1;reg=f.call('se_ft_step');assert reg.p&1 and reg.a==0xb0 and not f.get('se_ft_valid') and f.reu()==before and f.get('se_reu_dma_calls',2)==dma;checks+=1
   for field,width in [('se_ft_log_pointer',2),('se_ft_log_count',1),('se_ft_log_mode',1)]:
    f.seed(one,100,0,0,0);f.m.load(0x8000,bytes(9));f.put('se_ft_log_pointer',0x8000,2);f.put('se_ft_log_count',1);assert not f.call('se_ft_begin_log').p&1;at=f.s[field]+width-1;old=f.m.read(at);f.m.write(at,old^1);before=f.reu();dma=f.get('se_reu_dma_calls',2);reg=f.call('se_ft_step');assert reg.p&1 and reg.a==0xb1 and f.reu()==before and f.get('se_reu_dma_calls',2)==dma;checks+=1
   for stop in [0,1,3,4,5,6,10]:
    events=[(5,0,1),(30,0,1),(90,0,1)];f.seed(tree,500,0,0,0);f.m.load(0x8000,b''.join(v.to_bytes(3,'little') for e in events for v in e));f.put('se_ft_log_pointer',0x8000,2);f.put('se_ft_log_count',len(events));assert not f.call('se_ft_begin_log').p&1
    for _ in range(stop):assert not f.call('se_ft_step').p&1
    before=f.reu();assert not f.call('se_ft_cancel').p&1 and not f.get('se_ft_valid') and not f.get('se_ft_busy') and f.reu()==before;checks+=1
   cases.append('BEGIN_LOG1..112/ordered-disjoint-randomedits/nesteddrop-parentremap/lateinvalid-beforeDMA/boundptr-count-mode/cancel-eachphase')
  result=dict(status='passed',checks=checks,cases=cases,code_bytes=sizes['FOLD_TRANSFORM'],frame_bytes=s['se_ft_frame_end']-s['se_ft_input'],BSS=0,ZP=0,calls=f.calls,peak_instructions=f.peak,max_DMA_per_call=f.dma_peak,whole_REU_guard_bytes=4194304,limits='Dense transformed old-record hints only; never publish directly. Fresh parse identity and ancestry match required; SF_LINES intentionally ignored for edited retention. Caller owns source edit provenance and source lease.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.ram(0,65536));raise
 finally:f.close()
 evidence=ROOT/'agentsworking/evidence/M5'/(stamp+'-fold-transform');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 with zipfile.ZipFile(evidence/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in [*[f'src/{n}.s' for n in SOURCES],'src/fold/transform.inc','src/object/api.inc','src/fold/api.inc','tests/test_fold_transform.py']:z.write(ROOT/name,name)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()
