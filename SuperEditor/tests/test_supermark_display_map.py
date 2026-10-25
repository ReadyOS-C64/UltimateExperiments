"""Bounded actual6510 inline display map with complete source reconstruction.

No editor/sharedbuild/native. Full literal/raw packets use actual SuperMark
matched-pair events; host oracle derives hidden offsets and boundary preimages.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,random,re,shutil,subprocess,sys
import test_grid_modes as g
from peddle import Machine
from supermark_model import inline
from supermark_probe import petscii
ROOT=g.ROOT
O=dict(start=0,length=3,eof=4,column=5,busy=8,valid=9,error=10,stage=11,index=12,count=13,events=14,source=25,visible=28,left=29,right=32,input=40,raw=168,hidden=296,glyphs=424,v2s=552,s2v=681)
FRAME=0x8D00;SIZE=810
CANARY=bytes((i*73+29)&255 for i in range(65536))

def build(out):
 (out/'externals.s').write_text('.export se_dm_frame\nse_dm_frame=$8D00\n')
 (out/'map.cfg').write_text('''MEMORY { CODE:start=$1000,size=$1000,file="map.bin",type=ro; INLINE:start=$902A,size=$0100,file="",type=rw; }
SEGMENTS { SM_DISPLAY_MAP:load=CODE,type=ro,define=yes; SM_INLINE:load=CODE,type=ro,define=yes; SM_STATE:load=INLINE,type=bss,define=yes; }
''')
 for n,p in [('map',ROOT/'src/supermark/display-map.s'),('inline',ROOT/'src/supermark/inline.s'),('externals',out/'externals.s')]:subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(out/f'{n}.o'),str(p)],check=True)
 subprocess.run(['ld65','-C','map.cfg','-m','map.map','-Ln','map.lbl','map.o','inline.o','externals.o'],cwd=out,check=True)
 return {n:int(v,16) for v,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(out/'map.lbl').read_text())}
def oracle(data,start,column):
 events=inline(data,start,body_column=column or None);hidden=set()
 for kind,style,width,a,b in events:
  hidden.update(range(a-start,a-start+(width if kind==1 else 1)))
  if kind==1:hidden.update(range(b-start,b-start+width))
 visible=[i for i in range(len(data)) if i not in hidden];prefix=[sum(j<i for j in visible) for i in range(len(data)+1)]
 return events,bytes(data[i] for i in visible),bytes(int(i in hidden) for i in range(len(data))),bytes(visible+[len(data)]),bytes(prefix)
class Fixture:
 def __init__(self,out,s,dll):
  self.s=s;self.dll=dll;self.m=Machine();self.m.load(0,CANARY);self.m.load(0x1000,(out/'map.bin').read_bytes());self.calls=0;self.peak={};self.steps=0;self.input_bytes=0
 def ram(self,a,n):b=C.create_string_buffer(n);self.dll.gm_read(self.m.handle,a,n,b);return b.raw
 def put(self,n,v,w=1):self.m.load(FRAME+O[n],v.to_bytes(w,'little'))
 def get(self,n,w=1):return int.from_bytes(self.ram(FRAME+O[n],w),'little')
 def call(self,n):
  for name,v in [('pc',self.s['se_dm_'+n]),('sp',0xFD),('p',0x24),('a',0),('x',0),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+name)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.dll.gm_run(self.m.handle,100000);assert used,(n,hex(self.m.regs().pc));self.calls+=1;self.peak[n]=max(self.peak.get(n,0),used);return self.m.regs()
 def seed(self,data,start=0,column=0,eof=1):
  self.m.load(FRAME,bytes([0xA7])*SIZE);self.m.load(self.s['se_si_state'],bytes([0xB6])*self.s['se_si_state_size']);self.put('busy',0);self.put('start',start,3);self.put('length',len(data));self.put('eof',eof);self.put('column',column,3);self.m.load(FRAME+40,data)
 def verify(self,data,start=0,column=0,eof=1,checkpoint=None):
  self.seed(data,start,column,eof);before=self.ram(0,65536);reu=C.create_string_buffer(2*1024*1024);self.dll.gm_reu(self.m.handle,len(reu),reu);source=self.ram(FRAME,8)+self.ram(FRAME+40,128)
  r=self.call('begin');assert not r.p&1 and r.a==1
  count=0
  while self.get('busy'):
   r=self.call('step');assert not r.p&1,(data,r.a);count+=1;self.steps+=1
   assert self.ram(FRAME,8)+self.ram(FRAME+40,128)==source,'canonicalpacket/inputsmodified'
   assert self.get('valid')==int(not self.get('busy'))
   assert count<=len(data)*2+2
   if checkpoint==count:
    # Only complete caller context transfers; no ZP/stack/code is copied.
    context=self.ram(FRAME,SIZE)+self.ram(self.s['se_si_state'],self.s['se_si_state_size']);new=Machine();new.load(0,CANARY);new.load(0x1000,self.ram(0x1000,self.s['__SM_DISPLAY_MAP_SIZE__']+self.s['__SM_INLINE_SIZE__']));new.load(FRAME,context[:SIZE]);new.load(self.s['se_si_state'],context[SIZE:]);self.m.close();self.m=new;before=self.ram(0,65536);checkpoint=None
  events,glyphs,hidden,v2s,s2v=oracle(data,start,column)
  assert self.get('count')==len(glyphs) and self.get('events')==len(events)
  assert self.ram(FRAME+168,len(data))==data and self.ram(FRAME+296,len(data))==hidden
  assert self.ram(FRAME+424,len(glyphs))==glyphs and self.ram(FRAME+552,len(v2s))==v2s and self.ram(FRAME+681,len(s2v))==s2v,(data,'projection')
  reconstructed=bytes(self.ram(FRAME+168+i,1)[0] if hidden[i] else glyphs[s2v[i]] for i in range(len(data)))
  assert reconstructed==data,'completehidden+visibleledgerroundtrip'
  for i,v in enumerate(s2v):
   self.put('source',start+i,3);assert not self.call('from_source').p&1 and self.get('visible')==v
  for v in range(len(glyphs)+1):
   positions=[i for i,x in enumerate(s2v) if x==v];self.put('visible',v);assert not self.call('from_visible').p&1
   assert self.get('left',3)==start+min(positions) and self.get('right',3)==start+max(positions)
   if v<len(glyphs):
    assert not self.call('glyph').p&1 and self.get('source',3)==start+v2s[v]
    # Delete/Backspace target this rawbyte only; markerledger remains untouched.
    at=v2s[v];assert data[:at]+data[at+1:]==reconstructed[:at]+reconstructed[at+1:]
  # Every many-to-one hidden boundary remains explicit. Out-of-range
  # queries must preserve the published map and all caller query outputs.
  for at in [start-1,start+len(data)+1]:
   if 0<=at<=0xFFFFFF:
    self.put('source',at,3);anchor=self.ram(FRAME+25,10);r=self.call('from_source');assert r.p&1 and r.a==0xB8 and self.get('valid')==1 and self.ram(FRAME+25,10)==anchor
  self.put('visible',len(glyphs)+1);anchor=self.ram(FRAME+25,10);r=self.call('from_visible');assert r.p&1 and r.a==0xB8 and self.get('valid')==1 and self.ram(FRAME+25,10)==anchor
  # Query failure leaves the published map and query outputs intact.
  self.put('visible',len(glyphs));anchor=self.ram(FRAME+25,10);r=self.call('glyph');assert r.p&1 and r.a==0xB8 and self.get('valid')==1 and self.ram(FRAME+25,10)==anchor
  snapshot=self.ram(FRAME,SIZE);assert not self.call('step').p&1 and self.ram(FRAME,SIZE)==snapshot,'completedSTEPidempotence'
  after=self.ram(0,65536);want=bytearray(before)
  for a,n in [(0x100,256),(FRAME,SIZE),(self.s['se_si_state'],self.s['se_si_state_size'])]:want[a:a+n]=after[a:a+n]
  assert after==want,'full64KiB/ZP/code/shimguard'
  now=C.create_string_buffer(len(reu));self.dll.gm_reu(self.m.handle,len(now),now);assert reu.raw==now.raw,'wholeREUchanged'
  self.input_bytes+=len(data);return dict(source_bytes=len(data),glyphs=len(glyphs),events=len(events),steps=count,start=start,column=column)

def main():
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/supermark-display-map'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);s=build(out);f=Fixture(out,s,g.runner(out));cases=[];rng=random.Random(0x534D4D41)
 try:
  examples=['plain PETSCII','*emphasis* **strong** ***both***','**outer *inner* outer**','@@lda #$20@@ *tail*','*unclosed **unclosed @@unclosed','****literal**** @@@@literal@@@@','£*literal£* £@literal£@ ££ £5','£# escaped header','  £- escaped bullet','123£. escaped number','£#no-header £-no-list','@@£*literal@@','**a *b* c** tail','*a* £* b','', '*a*\n']
  for i,text in enumerate(examples):
   data=petscii(text);cases.append(f.verify(data,0xFFF9 if i%2 else 0,0,eof=int(not data.endswith(b'\r'))))
  print('FIRSTMATCHEDINLINE16PASS',flush=True)
  if not a.smoke:
   for byte in range(256):cases.append(f.verify(bytes([byte]),0x1FFFF))
   for width in [1,2,3]:
    for n in [0,1,2,8,32,128-width*2]:cases.append(f.verify(b'*'*width+b'A'*n+b'*'*width,0xFFFF00))
   for column in [1,2,8,300,65536]:cases.append(f.verify(petscii('£# literal *styled*'),0x2FFFF,column))
   alphabet=petscii('abcPRint£*#:@012345 -.$%\'"+()[]')+bytes([0,10,0x61,0xA0,0xFF])
   for i in range(600):
    data=bytes(rng.choice(alphabet) for _ in range(rng.randrange(129)));cases.append(f.verify(data,0xFFF9 if i%2 else 0x1FFF9,rng.choice([0,0,0,2,8]),checkpoint=rng.randrange(1,len(data)*2+3) if i<24 else None))
  faults=[]
  for label,data,start,column,eof,extra in [
      ('length129',b'A'*128,0,0,1,('length',129,1)),
      ('missingCR',b'A',0,0,0,None),
      ('invalidEOF',b'A',0,0,2,None),
      ('startoverflow',b'A',0xFFFFFF,0,1,None),
      ('coloverflow',b'A',0,0xFFFFFF,1,None),
      ('internalCR',b'A\rB',0,0,1,None)]:
   f.seed(data,start,column,eof)
   if extra:f.put(*extra)
   canonical=f.ram(FRAME,8)+f.ram(FRAME+40,128);rr=f.call('begin')
   while not rr.p&1 and f.get('busy'):rr=f.call('step')
   assert rr.p&1 and rr.a==0xB8 and not f.get('valid') and not f.get('busy'),(label,rr.a,rr.p,f.get('valid'),f.get('busy'))
   assert f.ram(FRAME,8)+f.ram(FRAME+40,128)==canonical
   faults.append(label)
  # BUSY BEGIN refuses without replacing either active context.
  f.seed(petscii('**body**'));assert not f.call('begin').p&1
  state=f.ram(FRAME,SIZE)+f.ram(s['se_si_state'],s['se_si_state_size']);rr=f.call('begin');assert rr.p&1 and rr.a==0xB1 and state==f.ram(FRAME,SIZE)+f.ram(s['se_si_state'],s['se_si_state_size']);faults.append('busyBEGIN')
  f.put('stage',9);rr=f.call('step');assert rr.p&1 and rr.a==0xB1 and not f.get('valid') and not f.get('busy');faults.append('badstage')
  # Every unsupported/malformed input still passes through actual parser;
  # only these explicit private descriptor-state faults bypass it for guards.
  for label,kind,style,width,op,cl in [('kind',0,1,1,0,3),('width',1,1,4,0,3),('style',1,0,1,0,3),('before',1,1,1,-1,3),('future',1,1,1,0,20),('cross',1,2,2,0,1),('escape',2,0,1,0,2)]:
   f.seed(petscii('*abc*'),0x10000);assert not f.call('begin').p&1
   f.put('index',5)
   for n,v,w in [('ready',1,1),('kind',kind,1),('style',style,1),('width',width,1),('open',0x10000+op,3),('close',0x10000+cl,3)]:f.m.load(s['se_si_'+n],v.to_bytes(w,'little'))
   f.s['se_dm_injected']=s['apply'];rr=f.call('injected');assert rr.p&1 and rr.a==0xB2 and not f.get('valid');faults.append('descriptor-'+label)
  cases.append(f.verify(b'',0xFFFFFF));cases.append(f.verify(b'*x*',0xFFFFFC))
  for data in [petscii('@@ *abc* £* all literal'),petscii('**'+('a *'*10)+'X'+('* b'*10)+'**'),b'A'*128]:cases.append(f.verify(data,0x10000))
  sizes={n:s['__'+n+'_SIZE__'] for n in ['SM_DISPLAY_MAP','SM_INLINE','SM_STATE']};assert sizes['SM_DISPLAY_MAP']+sizes['SM_INLINE']<=4096
  result=dict(status='passed',sizes=sizes,frame_bytes=SIZE,total_context=SIZE+sizes['SM_STATE'],resident_bss=0,zeropage=0,cases=len(cases),faults=faults,source_bytes=f.input_bytes,calls=f.calls,steps=f.steps,peak_instructions=f.peak,fixtures=cases,limits=['Completeinline-eligiblepackets<=128 only; no blockprefix hiding/editor/wrap/font/nativeintegration.','RawCRisapreservedlinebreaktoken, neverCHROUT; downstreamlayoutmustinterpretit.'])
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.m.close()
if __name__=='__main__':main()
