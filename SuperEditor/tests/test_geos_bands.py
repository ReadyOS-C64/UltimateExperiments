"""Bounded real6510 GEOS strip scheduling and vertical source hit geometry."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,random,re,shutil,subprocess
import test_grid_modes as g
from peddle import Machine
ROOT=g.ROOT
SIZE=286
O=dict(count=0,align=1,empty=2,busy=5,valid=6,error=7,stage=8,index=9,y=10,last=11,cursor=12,outvalid=13,runs=14,run0=15,hity=23,hitvalid=24,hitindex=25,local=26,start=27,end=30,next=33,top=36,row=43,tops=44,lines=66)
CANARY=bytes((i*73+29)&255 for i in range(65536))
def build(out,base):
 (out/'externals.s').write_text(f'.export se_gb_frame\nse_gb_frame=${base:04X}\n')
 (out/'bands.cfg').write_text('MEMORY { CODE:start=$1000,size=$1000,file="bands.bin",type=ro; }\nSEGMENTS { GEOS_BANDS:load=CODE,type=ro,define=yes; }\n')
 for n,p in [('bands',ROOT/'src/render/geos/bands.s'),('externals',out/'externals.s')]:subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(out/f'{n}.o'),str(p)],check=True)
 subprocess.run(['ld65','-C','bands.cfg','-m','bands.map','-Ln','bands.lbl','bands.o','externals.o'],cwd=out,check=True)
 return {n:int(v,16) for v,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(out/'bands.lbl').read_text())}
def records(heights,start=0):
 out=[]
 for i,h in enumerate(heights):
  end=start+i%5;next_=end+1+(17 if i%3==2 else 0);out.append((start,end,next_,h));start=next_
 return out
def model(lines,align):
 tops=[];y=16
 for s,e,n,h in lines:
  if align and h==8:y=(y+7)&~7
  tops.append(y);y+=h
 packets=[]
 for row in range(2,24):
  runs=[]
  for i,((s,e,n,h),top) in enumerate(zip(lines,tops)):
   a=max(row*8,top,16);b=min((row+1)*8,top+h,192)
   if a<b:runs.append((i,top-row*8,a-row*8,b-row*8))
  assert len(runs)<=2;packets.append((row,runs))
 return tops,packets
def hit_model(lines,tops,y,empty):
 visible=[i for i,t in enumerate(tops) if t<192];target=min(191,max(16,y))
 if not visible:return (0,255,0,16,empty,empty,empty)
 chosen=next((i for i in visible if target<tops[i]+lines[i][3]),visible[-1]);local=min(lines[chosen][3]-1,max(0,target-tops[chosen]));s,e,n,h=lines[chosen]
 return (1,chosen,local,tops[chosen],s,e,n)
class Fixture:
 def __init__(self,out,s,dll,base):
  self.base=base;self.s=s;self.dll=dll;self.m=Machine();self.m.load(0,CANARY);self.m.load(0x1000,(out/'bands.bin').read_bytes());self.calls=0;self.peak={};self.frames=0;self.strips=0
 def ram(self,a,n):b=C.create_string_buffer(n);self.dll.gm_read(self.m.handle,a,n,b);return b.raw
 def get(self,n,w=1):return int.from_bytes(self.ram(self.base+O[n],w),'little')
 def put(self,n,v,w=1):self.m.load(self.base+O[n],v.to_bytes(w,'little'))
 def call(self,n,error=0):
  before=self.ram(0,65536)
  for key,v in [('pc',self.s['se_geos_bands_'+n]),('sp',0xFD),('p',0x24),('a',0),('x',0),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+key)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.dll.gm_run(self.m.handle,100000);assert used,(n,hex(self.m.regs().pc));r=self.m.regs();self.calls+=1;self.peak[n]=max(self.peak.get(n,0),used)
  after=self.ram(0,65536);want=bytearray(before)
  for a,b in [(0x100,0x200),(self.base+5,self.base+23),(self.base+24,self.base+66)]:want[a:b]=after[a:b]
  assert after==want,(n,'fullRAM/source/list/shim/ZP/fontguard',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  assert bool(r.p&1)==bool(error) and (not error or r.a==error),(n,error,r.a,r.p)
  return r
 def seed(self,lines,align=1,empty=0):
  self.m.load(self.base,bytes([0xA7])*SIZE);self.put('count',len(lines));self.put('align',align);self.put('empty',empty,3);self.put('busy',0)
  data=b''.join(b''.join(v.to_bytes(3,'little') for v in row[:3])+bytes([row[3]]) for row in lines);self.m.load(self.base+66,data)
 def verify(self,lines,align=1,empty=0,hit_all=True,checkpoint=None):
  self.seed(lines,align,empty);tops,wanted=model(lines,align);reu=C.create_string_buffer(512*1024);self.dll.gm_reu(self.m.handle,len(reu),reu)
  r=self.call('begin');assert r.a==1;steps=0;packets=[];coverage=set()
  while self.get('busy'):
   stage,index=self.get('stage'),self.get('index');r=self.call('step');steps+=1
   assert steps<=len(lines)+22
   if stage==1:assert self.get('index')==index+1 and not self.get('outvalid'),'onevalidationrecordperSTEP'
   if checkpoint==steps:
    context=self.ram(self.base,SIZE);code=self.ram(0x1000,self.s['__GEOS_BANDS_SIZE__']);new=Machine();new.load(0,CANARY);new.load(0x1000,code);new.load(self.base,context);self.m.close();self.m=new
   if stage==1 and self.get('valid'):
    cursor=self.get('cursor');self.put('hity',31);self.call('hit_y');assert self.get('cursor')==cursor,'HITbetweenstripsmustnotchangecursor'
   if self.get('outvalid'):
    self.strips+=1;row=self.get('row');runs=[]
    for k in range(self.get('runs')):
     raw=self.ram(self.base+15+k*4,4);i,origin,top,bottom=raw;origin=origin-256 if origin&128 else origin
     assert -8<=origin<=7 and 0<=top<bottom<=8 and i<len(lines)
     runs.append((i,origin,top,bottom))
     for dy in range(top,bottom):
      source_y=dy-origin;assert 0<=source_y<lines[i][3]
      item=(i,source_y);assert item not in coverage;coverage.add(item)
    packets.append((row,runs))
  assert steps==len(lines)+22 and packets==wanted and r.a==0 and self.get('valid')==1,(lines,align,steps,packets,wanted)
  assert self.ram(self.base+44,len(lines))==bytes(t if t<192 else 255 for t in tops)
  expected={(i,dy) for i,(row,t) in enumerate(zip(lines,tops)) for dy in range(row[3]) if 16<=t+dy<192};assert coverage==expected,'ninthrow/bottomclipcoverage'
  snapshot=self.ram(self.base,SIZE);assert self.call('step').a==0 and self.ram(self.base,SIZE)==snapshot,'completedidempotent'
  for y in (range(200) if hit_all else [0,15,16,24,25,31,32,183,191,192,199]):
   self.put('hity',y);assert self.call('hit_y').a==0
   actual=tuple(self.get(n,w) for n,w in [('hitvalid',1),('hitindex',1),('local',1),('top',1),('start',3),('end',3),('next',3)])
   assert actual==hit_model(lines,tops,y,empty),(lines,align,y,actual,hit_model(lines,tops,y,empty))
  now=C.create_string_buffer(len(reu));self.dll.gm_reu(self.m.handle,len(now),now);assert reu.raw==now.raw,'wholeREUchanged'
  self.frames+=1;return dict(lines=len(lines),align_native=align,steps=steps,visible=sum(t<192 for t in tops),ninth_rows=sum(1 for i,dy in coverage if lines[i][3]==9 and dy==8))
 def close(self):self.m.close()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');a=ap.parse_args();out=ROOT/'build/geos-bands'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);s=build(out,0x8D00);dll=g.runner(out);f=Fixture(out,s,dll,0x8D00);cases=[];rng=random.Random(0xB54009)
 try:
  for h in [[],[8],[9],[9,9],[9,8,9,8],[8]*22,[9]*22,[9,8]*11]:
   cases.append(f.verify(records(h,0xFFF0),1,0xFFFFFF))
  print('FIRST8GEOMETRIES-PASS',flush=True)
  if not a.smoke:
   for i in range(400):
    hs=[rng.choice([8,9]) for _ in range(rng.randrange(23))];cases.append(f.verify(records(hs,rng.choice([0,0xFFFF,0x1FFFF,0xFFF000])),i&1,rng.randrange(0x1000000),checkpoint=rng.randrange(1,len(hs)+23) if i<24 else None))
   # Empty EOF is a real last logical row, not an invented source advance.
   eof=records([9,8],0xFFFFF0);at=eof[-1][2];eof.append((at,at,at,9));cases.append(f.verify(eof))
  faults=[]
  invalid=[('count23',records([9]*22),('count',23),0x90),('count255',[],('count',255),0x90),('align2',[],('align',2),0x90),('align255',[],('align',255),0x90)]
  for h in [0,7,10,255]:invalid.append(('height'+str(h),[(0,1,2,h)],None,0x90))
  invalid += [('startafterend',[(0x10000,0xFFFF,0x10001,9)],None,0x90),('endafternext',[(0,0x10000,0xFFFF,9)],None,0x90),('chain',[(0,1,2,9),(3,4,5,8)],None,0x90),('nonprogress',[(0,0,0,9),(0,1,2,9)],None,0x90)]
  for label,rows,change,error in invalid:
   f.seed(rows)
   if change:f.put(change[0],change[1])
   rr=f.call('begin',error if change else 0)
   if not change:
    for _ in range(len(rows)+1):
     # Invalid source/height may fail at its first or later record.
     stage=f.get('index');bad_here=(label=='chain' and stage==1) or (label!='chain')
     rr=f.call('step',error if bad_here else 0)
     if rr.p&1:break
   assert rr.p&1 and not f.get('valid') and not f.get('busy') and not f.get('outvalid');faults.append(label)
  f.seed(records([9,8]));f.call('begin');snapshot=f.ram(f.base,SIZE);f.call('begin',0x91);assert f.ram(f.base,SIZE)==snapshot;faults.append('busyBEGIN')
  snapshot=f.ram(f.base+24,13);f.put('hity',16);f.call('hit_y',0x91);assert f.ram(f.base+24,13)==snapshot;faults.append('HITunvalidated')
  f.put('stage',9);f.call('step',0x91);assert not f.get('valid') and not f.get('busy');faults.append('badstage')
  cases.append(f.verify([(0xFFFFFF,0xFFFFFF,0xFFFFFF,9)]))
  for value in [200,255]:
   f.put('hity',value);snapshot=f.ram(f.base+24,13);f.call('hit_y',0x90);assert f.ram(f.base+24,13)==snapshot and f.get('valid')==1;faults.append('HIT'+str(value))
  # Link relocation proves the module does not hide an absolute frame pointer.
  other=out/'relocated';other.mkdir();rs=build(other,0x8F40);rf=Fixture(other,rs,dll,0x8F40)
  try:
   for i in range(24):cases.append(rf.verify(records([rng.choice([8,9]) for _ in range(rng.randrange(23))],0x10000),i&1))
  finally:rf.close()
  result=dict(status='passed',code_bytes=s['__GEOS_BANDS_SIZE__'],caller_frame_bytes=286,workspace_bytes=66,list_bytes=220,new_BSS=0,new_ZP=0,frames=len(cases),faults=faults,strips=f.strips+rf.strips,calls=f.calls+rf.calls,peak_instructions={k:max(f.peak.get(k,0),rf.peak.get(k,0)) for k in set(f.peak)|set(rf.peak)},cases=cases,scope='Pureactual6510authoritative-line geometry; no fonts/pixels/source reader/editor/native/timingintegration')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
