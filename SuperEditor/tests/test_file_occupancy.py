"""Actual emitted read-only D81 occupancy/chain preflight and filename grammar.

All objects/output are isolated under build/filename-occupancy. KERNAL boundary
only is modeled; production C10/C12 and native IEC are separate integration gates.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from fileio_fixture import FileIOFixture,ROM
from peddle import Machine
OUT=ROOT/'build/filename-occupancy';OUT.mkdir(exist_ok=True)
def run(args):return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True).stdout
modules=['src/fileio/'+name+'.s' for name in ['state','channel','chunk','status','commands','directory']]
modules+=['src/editor_file/preflight-state.s','src/editor_file/preflight.s']
objects=[]
for i,name in enumerate(modules):
 p=OUT/f'{i}.o';run(['ca65','-g','-I','src','-o',str(p),name]);objects.append(p)
(OUT/'probe.cfg').write_text('''MEMORY {
 CODE:file=%O,start=$1000,size=$3000,type=rw;
 STATE:file="",start=$C000,size=$0600,type=rw;
}
SEGMENTS {
 CODE:load=CODE,type=ro;
 RODATA:load=CODE,type=ro;
 BSS:load=STATE,type=bss;
 FILESTATE:load=STATE,type=bss;
}
''')
run(['ld65','-C',str(OUT/'probe.cfg'),'-o',str(OUT/'probe.bin'),'-Ln',str(OUT/'probe.lbl'),'-m',str(OUT/'probe.map'),*map(str,objects)])
SYMBOLS={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/'probe.lbl').read_text())}

class Probe(FileIOFixture):
 def __init__(self):
  self.s=SYMBOLS;self.m=Machine();self.m.load(0x1000,(OUT/'probe.bin').read_bytes())
  self.fs={};self.channels={};self.trace=[];self.selected_in=self.selected_out=None
  self.st=0;self.dos=b'00, OK,00,00\r';self.directory=b'';self.inject={}
  self.blocks={};self.reads=[];self.opens=[];self.commands=[];self.command_error=0
  self.shim=bytes((i*43+17)&255 for i in range(1024));self.m.load(0xC600,self.shim)
  self.guard=bytes((i*31+41)&255 for i in range(0x1800));self.m.load(0x8800,self.guard)
  self.max_instructions=0;self.call('se_io_init')
 def call(self,name,a=0,error=None):
  m=self.m
  for k,v in [('pc',self.s[name]),('a',a),('x',0),('y',0),('sp',0xFD),('p',0x24)]:getattr(m.lib,'zeropage_peddle_set_'+k)(m.handle,v)
  m.write(0x1FE,0xFE);m.write(0x1FF,0x02);start=m.regs().instructions
  for _ in range(200000):
   if m.regs().pc==0x02FF:break
   if m.regs().pc in ROM:self.rom()
   else:m.lib.zeropage_peddle_step_instruction(m.handle)
  else:raise AssertionError((name,hex(m.regs().pc)))
  r=m.regs();self.max_instructions=max(self.max_instructions,r.instructions-start)
  assert bool(r.p&1)==(error is not None),(name,r.a,r.p,error)
  if error is not None:assert r.a==error,(name,r.a,error)
  else:assert r.a in (0,2),(name,r.a)
  assert self.read(0xC600,1024)==self.shim
  assert self.read(0x8800,len(self.guard))==self.guard
  return r.a
 def rom(self):
  if self.m.regs().pc==0xFFC0:
   self.opens.append((self.filename,self.sa))
   assert self.filename in (b'#',b'') or self.filename.startswith(b'U1:'),'Unexpected SEQ/W-open'
   if self.filename==b'#' and not self.inject.get(0xFFC0):
    old=self.filename;self.filename=b'0:__RAW,S,R';self.fs[b'__RAW']=bytes(256)
    super().rom();self.filename=old;del self.fs[b'__RAW'];return
  super().rom()
 def command(self,data):
  self.commands.append(data);assert data.startswith(b'U1:'),'No writes/rename/scratch allowed'
  ch,drive,t,s=map(int,data[3:].split());assert (ch,drive)==(3,0)
  self.reads.append((t,s));assert (t,s) in self.blocks,(t,s)
  if self.command_error:
   self.dos=f'{self.command_error:02}, TEST FAILURE,00,00\r'.encode();self.command_error=0
  else:
   self.channels[7]=dict(data=self.blocks[t,s],pos=0);self.dos=b'00, OK,00,00\r'
 def setup(self,entries=(),pages=1):
  assert not self.channels and self.read('se_f_preflight_phase')==b'\0'
  h=bytearray(256);h[:2]=bytes([40,3]);self.blocks={(40,0):bytes(h)}
  for page in range(pages):
   b=bytearray(256);b[:2]=bytes([40,page+4]) if page+1<pages else bytes([0,255])
   self.blocks[40,page+3]=bytes(b)
  for page,index,kind,name,first in entries:
   b=bytearray(self.blocks[40,page+3]);at=index*32;b[at+2]=kind;b[at+3:at+5]=bytes(first)
   b[at+5:at+21]=name.ljust(16,b'\xA0');self.blocks[40,page+3]=bytes(b)
  self.reads=[];self.opens=[];self.commands=[]
 def finish(self,error=None):
  steps=0
  while self.read('se_f_preflight_phase')!=b'\0':
   before=len(self.reads)
   # Errors are expected only on the completing slice; run with a low-level
   # capture through the same executor, then validate the actual status below.
   expected=error if self.next_failure(error) else None
   result=self.call('se_f_preflight_step',error=expected);steps+=1
   assert len(self.reads)-before<=1
   if self.read('se_f_preflight_phase')==b'\0':
    assert (expected is not None)==(error is not None),(error,expected)
    assert self.read('se_f_preflight_kind')==b'\0' and not self.channels
    return result,steps
   assert result==2 and steps<=40
  raise AssertionError('finish called without active scan')
 def next_failure(self,error):
  if error is None:return False
  phase=self.read('se_f_preflight_phase')[0];t=self.read('se_f_preflight_track')[0];s=self.read('se_f_preflight_sector')[0]
  b=self.blocks[t,s]
  if error==0x92:return True
  if error==0x93:return phase==2 and b[0]==0 or bool(self.command_error)
  if error==0x94:return (b[0]!=40 or not 3<=b[1]<40 or self.read('se_f_preflight_remaining')[0]==1) if phase in (1,2) else True
  raise AssertionError(error)

f=Probe();cases=[]
def check(tag):cases.append(tag)
def reu():return hashlib.sha256(bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i) for i in range(8*65536))).hexdigest()
before_reu=reu()
try:
 rejected=set(b'"*,/:=?')|set(range(32))|set(range(127,161))|{32}
 for byte in range(256):
  f.name(bytes([byte]));trace=len(f.trace);f.call('se_io_validate',error=0x90 if byte in rejected else None);assert len(f.trace)==trace
 for size in range(1,17):
  for at in range(size):
   f.name(b'A'*at+b'\xA0'+b'Z'*(size-at-1));trace=len(f.trace)
   for name in ['se_io_validate','se_f_preflight_begin','se_f_exists_begin']:f.call(name,error=0x90)
   assert len(f.trace)==trace
 check('256byte grammar plus136 A0 positions refuse before any ROM')
 candidate=b'SE~T000000000000'
 for kind in range(256):
  f.setup([(0,0,kind,candidate,(0,0))]);old=dict(f.blocks);f.name(candidate);assert f.call('se_f_exists_begin')==2
  value,steps=f.finish(None if kind&7 else 0x93)
  assert steps==2 and f.reads==[(40,0),(40,3)] and f.blocks==old
  assert f.read('se_io_owned_temp')==f.read('se_io_owned_backup')==b'\0'
  if not kind&7:assert f.read('se_io_dos_code')==b'\x3E'
 check('all256 raw types:224 nonDEL occupied and32 DEL patterns absent; no chain read or writes')
 for kind in [0x01,0x81,0xC1,0x82,0x84,0x85,0x87,0x80]:
  f.setup([(0,0,kind,b'NORMAL',(1,0))]);f.blocks[1,0]=b'\0\x02Q'+bytes(253);f.name(b'NORMAL')
  f.call('se_f_preflight_begin');f.finish(None if kind in (0x81,0xC1) else 0x93)
  if kind in (0x81,0xC1):assert f.read('se_f_preflight_length',3)==b'\x01\0\0'
 check('normal chain mode still accepts only closedSEQ including locked and follows payload')
 for name in [b'@',b'A@B',bytes([0xA1,0xC1,0xFF]),candidate]:
  f.setup([(2,7,0x04,name,(0,0))],pages=3);f.name(name);f.call('se_f_exists_begin');f.finish()
  assert f.reads==[(40,0),(40,3),(40,4),(40,5)]
 check('last-slot third-page native/@/A1/FF names exact and bounded')
 f.setup([(0,0,0x81,b'NAME\xA0SUFFIX',(0,0))]);f.name(b'NAME');f.call('se_f_exists_begin');f.finish()
 f.call('se_f_preflight_begin');f.finish(0x93)
 check('occupancy mirrors firstA0 DOS alias while normal chain keeps strict16 comparison')
 for begin in ['se_f_preflight_begin','se_f_exists_begin']:
  f.setup();f.name(candidate);f.call(begin);state=f.read(f.s['se_f_preflight_phase'],17);channels=dict(f.channels);trace=len(f.trace)
  for other in ['se_f_exists_begin','se_f_preflight_begin']:
   f.call(other,error=0x91);assert f.read(f.s['se_f_preflight_phase'],17)==state and f.channels==channels and len(f.trace)==trace
  f.call('se_f_preflight_cancel');assert not f.channels and f.read('se_f_preflight_kind')==b'\0'
 check('competing begin preserves mode/frame/raw-channel and cancel clears only scan')
 f.setup();f.name(candidate);f.channels[5]=dict(data=b'FOREIGN',pos=0);f.set('se_io_mode',1);trace=len(f.trace)
 for begin in ['se_f_preflight_begin','se_f_exists_begin']:f.call(begin,error=0x91)
 assert len(f.trace)==trace and f.channels[5]['data']==b'FOREIGN'
 f.channels.clear();f.set('se_io_mode',0);check('foreign data channel refused without ROM or ownership changes')
 for begin in ['se_f_preflight_begin','se_f_exists_begin']:
  for link in [(0,0),(0,255),(41,3),(40,2),(40,40)]:
   f.setup();h=bytearray(f.blocks[40,0]);h[:2]=bytes(link);f.blocks[40,0]=bytes(h);f.name(candidate);f.call(begin);f.finish(0x94)
 f.setup();d=bytearray(f.blocks[40,3]);d[:2]=bytes([40,3]);f.blocks[40,3]=bytes(d);f.name(candidate);f.call('se_f_exists_begin');_,steps=f.finish(0x94);assert steps==40
 check('bad directory geometry and cycles refuse94 within40 raw sectors')
 for pc in [0xFFC0,0xFFC6,0xFFCF]:
  f.setup();f.name(candidate)
  if pc==0xFFC0:f.inject[pc]=128;f.call('se_f_exists_begin',error=0x92)
  else:f.call('se_f_exists_begin');f.inject[pc]=128;f.finish(0x92)
  assert not f.channels and f.read('se_f_preflight_kind')==b'\0'
 f.setup();f.name(candidate);f.call('se_f_exists_begin');f.command_error=74;f.finish(0x93);assert f.read('se_io_dos_code')==b'\x4A'
 check('OPEN/CHKIN/CHRIN/DOS74 failure closes owned raw channel; only absence yieldsDOS62')
 assert reu()==before_reu
 result=dict(ok=True,cases=cases,raw_type_patterns=256,grammar_bytes=256,A0_positions=136,
             preflight_state_bytes=17,added_FILESTATE_bytes=1,added_ZP_bytes=0,
             max_slice_instructions=f.max_instructions,reu_guard_bytes=8*65536,c64_guard_bytes=len(f.guard),shim_bytes=1024,
             image_sha256=hashlib.sha256((OUT/'probe.bin').read_bytes()).hexdigest(),
             source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in modules},
             scope='Actual emitted operation-sized provider/preflight with modeled KERNAL; no native/editor integration claim')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:f.close()
