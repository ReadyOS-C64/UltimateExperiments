"""Actual 6510 arena transport against frozen19fe resident/object/provider.

No product image substitutions or native claim. New17B persistent state is
bound to the proven unused OBJECTS tail; all actual allocator/DMA code is the
sealed product. Output only in a unique private build directory.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,subprocess,sys,ctypes as CT
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR,library
F=0x8D00;C=F+387;IO=F+448
DEFAULT=ROOT/'agentsworking/evidence/M8/20261025T223045649882Z-presentation-wrap-native'

def command(*args):return subprocess.run(list(map(str,args)),cwd=ROOT,check=True,capture_output=True,text=True)
def crc(raw,skip=()):return binascii.crc_hqx(bytes(v for i,v in enumerate(raw) if i not in skip),0xffff)
def build(out,source):
 (out/'fixture').mkdir();source=Path(source)
 for n in ('editor.prg','editor.lbl','editor-report.json','editor-bindings.json'):shutil.copy2(source/n,out/'fixture'/n)
 r=json.loads((out/'fixture/editor-report.json').read_text());assert r['sha256']=='bf153ce471111faee3fb343497b6bdef5e1c3594a527a0c55edd90c8b86b2508'
 files=[ROOT/'src/cache/arena'/n for n in ('control.s','core.s','open.s','page.s')];objs=[]
 for p in files:
  obj=out/(p.stem+'.o');command('ca65','-g','-I','src','-o',obj,p);objs.append(obj)
 seam={'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85}
 (out/'seam.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${a:04X}' for n,a in seam.items())+'\n')
 command('ca65','-o',out/'seam.o',out/'seam.s');objs.append(out/'seam.o')
 command(sys.executable,'tools/module_bindings.py','--report',out/'fixture/editor-report.json','--output',out/'aliases.s',*objs)
 command('ca65','-o',out/'aliases.o',out/'aliases.s');objs.append(out/'aliases.o')
 (out/'arena.cfg').write_text('MEMORY { R:file=%O,start=$A000,size=$2000; } SEGMENTS { CODE:load=R,type=ro; RODATA:load=R,type=ro; }')
 command('ld65','-C',out/'arena.cfg','-o',out/'arena.bin','-Ln',out/'arena.lbl','-m',out/'arena.map',*objs)
 symbols=dict(r['symbols']);symbols.update(seam)
 for line in (out/'arena.lbl').read_text().splitlines():
  parts=line.split()
  if len(parts)==3:symbols[parts[2].lstrip('.')]=int(parts[1],16)
 return r,symbols

class Test:
 def __init__(self,out,source):
  self.out=out;self.r,self.s=build(out,source);self.m=Machine();self.calls=0;self.instructions=0;self.peak=0
  raw=(out/'fixture/editor.prg').read_bytes();self.m.load(int.from_bytes(raw[:2],'little'),raw[2:]);self.m.load(0xA000,(out/'arena.bin').read_bytes())
  self.call('se_clear_state');self.put('se_reu_banks',256,2);self.call('se_reu_provider_init');self.call('se_object_init')
  self.m.load(0xc600,bytes((i*71+13)&255 for i in range(1024)));self.shim=self.read(0xc600,1024)
  self.m.load(F,bytes((i*37+5)&255 for i in range(576)));self.m.load(C,bytes(61));self.m.load(0x9fb5,bytes(17));self.put('se_f_owner',4,1)
  self.opaque=self.read(F,387)
  self.ram_intervals=0;self.reu_intervals=0
  # Two tiny inspection functions only; the emulator and CPU execution remain
  # the existing actual Peddle runtime. Avoid16million Python/C crossings.
  ext='.dylib' if sys.platform=='darwin' else '.so'
  (out/'inspect.cpp').write_text('#include "zeropage_peddle.h"\nextern "C" void inspect(ZeroPagePeddle*m,unsigned a,unsigned n,unsigned char*p,int reu){for(unsigned i=0;i<n;i++)p[i]=reu?zeropage_peddle_read_reu(m,a+i):zeropage_peddle_read(m,a+i);}')
  command('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),out/'inspect.cpp',ROOT/('build/libse_peddle'+ext),'-o',out/('inspect'+ext))
  self.inspector=CT.CDLL(str(out/('inspect'+ext)));self.inspector.inspect.argtypes=[CT.c_void_p,CT.c_uint,CT.c_uint,CT.c_void_p,CT.c_int]
 def snapshot(self,reu=False):
  n=16*1024*1024 if reu else 65536;b=CT.create_string_buffer(n);self.inspector.inspect(self.m.handle,0,n,b,int(reu));return b.raw
 def reu_guard(self,before,bank=None):
  after=self.snapshot(True);wanted=bytearray(before)
  if bank is not None:
   for b in ([bank] if isinstance(bank,int) else bank):wanted[b*65536:(b+1)*65536]=after[b*65536:(b+1)*65536]
  assert after==wanted,'foreign REU mutation';self.reu_intervals+=1
 def allowed(self):
  pairs=[('se_crc_value',2),('se_object_id',12),('new_owner',5),('validate_index',3),('copy_direction',12),('object_owner',184),('se_reu_c64',16),('se_reu_map',768),('provider_owner',1)]
  return [(self.s[n],self.s[n]+w) for n,w in pairs]+[(0x100,0x200),(C,F+576),(0x9fb5,0x9fc6),(0xcc4d,0xcc4e),(0xdf00,0xdf0b)]
 def read(self,a,n):return bytes(self.m.read(a+i) for i in range(n))
 def put(self,n,v,w=3):self.m.load(self.s.get(n,n) if isinstance(n,str) else n,int(v).to_bytes(w,'little'))
 def call(self,n,a=0,x=0,error=None,check=True):
  r,used=self.m.call(self.s[n],a=a,x=x);self.calls+=1;self.instructions+=used;self.peak=max(self.peak,used)
  if check:assert bool(r.p&1)==(error is not None),(n,hex(r.a),hex(r.p),error)
  if error is not None:assert r.a==error,(n,hex(r.a),hex(error))
  return r
 def invoke(self,n,error=None):
  before=self.snapshot();dc=int.from_bytes(before[self.s['se_reu_dma_calls']:self.s['se_reu_dma_calls']+2],'little');db=int.from_bytes(before[self.s['se_reu_dma_bytes']:self.s['se_reu_dma_bytes']+3],'little');r=self.call(n,error=error);after=self.snapshot();wanted=bytearray(before)
  assert (int.from_bytes(after[self.s['se_reu_dma_calls']:self.s['se_reu_dma_calls']+2],'little')-dc)&65535<=1,(n,'unboundedDMA')
  assert (int.from_bytes(after[self.s['se_reu_dma_bytes']:self.s['se_reu_dma_bytes']+3],'little')-db)&0xffffff<=128,(n,'unboundedbytes')
  for lo,hi in self.allowed():wanted[lo:hi]=after[lo:hi]
  assert after==wanted,('wholeRAM',n,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  self.ram_intervals+=1
  assert self.read(F,387)==self.opaque and self.read(0xc600,1024)==self.shim
  return r
 def drain(self):
  steps=0
  while self.m.read(C+8):self.invoke('se_bc_arena_step');steps+=1;assert steps<100
  return steps
 def token(self):return self.read(self.s['se_bc_arena'],5)
 def object_transfer(self,offset,raw=None,length=0):
  self.m.load(self.s['se_object_id'],self.token());self.put('se_object_offset',offset);self.put('se_object_length',len(raw) if raw is not None else length,2);self.put('se_object_c64',IO,2)
  if raw is not None:self.m.load(IO,raw)
  self.call('se_object_copy',a=int(raw is None));return self.read(IO,len(raw) if raw is not None else length)
 def physical(self):
  ident=self.token()[0];logical=self.m.read(self.s['object_extents']+ident*16);return self.m.read(self.s['se_reu_map']+logical)
 def bank(self):return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,self.physical()*65536+i) for i in range(65536))
 def page(self,index,payload,kind=1,gen=1):
  entry=bytearray(gen.to_bytes(2,'little')+bytes([kind,1])+bytes(4));entry[4:6]=crc(entry,(4,5)).to_bytes(2,'little');self.object_transfer(0x100+8*index,entry)
  h=bytearray(64);h[:8]=b'BP'+bytes([1,1,index,kind])+gen.to_bytes(2,'little');h[8:12]=self.read(self.s['se_bc_incarnation'],4);h[12:17]=self.token();h[21:23]=len(payload).to_bytes(2,'little');h[25:33]=b'\xff'*8;h[39:41]=crc(payload).to_bytes(2,'little');h[37:39]=crc(h,(3,37,38)).to_bytes(2,'little')
  self.object_transfer(index*4096,h)
  for at in range(0,len(payload),128):self.object_transfer(index*4096+64+at,payload[at:at+128])
  return h,entry
 def proof(self,index=1,kind=1,gen=1):
  self.put(C+4,index,1);self.put(C+5,kind,1);self.put(C+6,gen,2);return self.invoke('se_bc_page_begin')

def run(out,source):
 t=Test(out,source);cases=[]
 try:
  # Force logical arena1 to physical2; transport must never assume equality.
  r,_=t.m.call(t.s['se_reu_bind'],a=7,x=190,y=1);assert not r.p&1
  t.put('se_bc_flags',2,1);initial=t.snapshot(True);assert t.invoke('se_bc_arena_open').a==1
  for _ in range(32):assert t.invoke('se_bc_arena_step').a==1
  assert t.m.read(C+8)==5 and t.token()==bytes(5)
  assert t.invoke('se_bc_arena_step').a==1 and t.m.read(C+8)==6 and t.token()==bytes(5)
  candidate=t.read(C+10,5);logical=t.m.read(t.s['object_extents']+candidate[0]*16);physical=t.m.read(t.s['se_reu_map']+logical)
  assert t.m.lib.zeropage_peddle_read_reu(t.m.handle,physical*65536+5)==0
  assert t.invoke('se_bc_arena_step').a==0;steps=34
  token=t.token();assert t.physical()==2;assert token[1:3]==b'\1\0' and t.read(t.s['se_bc_incarnation'],4)==b'\1\0\0\0' and t.m.read(t.s['se_bc_flags'])==2
  t.reu_guard(initial,t.physical());bank=t.bank();root=bank[:128];assert root[:8]==b'BCA1\1\1\x80\0' and root[8:13]==token and root[31:94]==bytes(63) and bank[128:4096]==bytes(3968)
  assert int.from_bytes(root[119:121],'little')==crc(root,(5,119,120));cases.append('empty-open-validlast/no-semantic-authority')
  print('FIRST arena OPEN PASS: actual typed allocation +34 bounded steps, empty root CRC/64KiB committed, opaque producer/shim intact',flush=True)
  ro=t.snapshot(True);assert t.invoke('se_bc_arena_open').a==1;assert t.drain()==3;t.reu_guard(ro);assert t.read(IO,128)==root;cases.append('existing-root-A-format-checked')
  # RootB is newer and selected; corruptB falls backA; both corrupt refuse.
  b=bytearray(root);b[18:22]=(2).to_bytes(4,'little');b[119:121]=crc(b,(5,119,120)).to_bytes(2,'little');t.object_transfer(128,b)
  t.invoke('se_bc_arena_open');t.drain();assert t.read(IO,128)==b
  b[127]=1;t.object_transfer(128,b);t.invoke('se_bc_arena_open');t.drain();assert t.read(IO,128)==root
  cases.append('root-B-newer-and-CRC/reserved-fallback')
  bad=bytearray(root);bad[119]^=1;t.object_transfer(0,bad);ro=t.snapshot(True);t.invoke('se_bc_arena_open');t.invoke('se_bc_arena_step');t.invoke('se_bc_arena_step',0xc2);assert t.token()==token;t.reu_guard(ro);t.invoke('se_bc_arena_cancel');t.object_transfer(0,root)
  # Equal sequence copies are deliberately ambiguous/fail-closed.
  t.object_transfer(128,root);t.invoke('se_bc_arena_open');t.invoke('se_bc_arena_step');t.invoke('se_bc_arena_step',0xc2);t.invoke('se_bc_arena_cancel');t.object_transfer(128,bytes(128))
  cases.append('both-invalid-or-equal-sequence-roots-refuse-without-release')
  payload=bytes((i*71+23)&255 for i in range(4032));h,e=t.page(15,payload,7,123)
  assert t.proof(15,7,123).a==1;assert t.drain()==34;assert t.m.read(C+39)==0xa5
  for offset,length in [(0,1),(1,128),(127,128),(3904,128),(4031,1)]:
   t.put(C,15*4096+64+offset);t.put(C+3,length,1);t.invoke('se_bc_arena_read');assert t.read(IO,length)==payload[offset:offset+length]
  for offset,length in [(63,1),(4095,2),(64,0),(64,129),(0x10000,1)]:
   t.put(C,15*4096+offset if offset<0x10000 else offset);t.put(C+3,length,1);dma=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_arena_read',0xc0);assert t.read(t.s['se_reu_dma_calls'],5)==dma
  cases.append('4032B-last-page-directory/header/fullpayloadCRC/exact-read-bounds')
  # Fail closed when the observer publishes a new ticket between slices.
  t.proof(15,7,123);t.put('se_bc_ticket',1,4);dma=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_arena_step',0xc1);assert t.read(t.s['se_reu_dma_calls'],5)==dma;t.put('se_bc_ticket',0,4);t.invoke('se_bc_arena_cancel')
  # Corrupt last payload byte cannot certify a valid prefix.
  t.object_transfer(15*4096+4095,b'\x01');t.proof(15,7,123)
  while t.m.read(C+8):
   r=t.call('se_bc_arena_step',check=False)
   if r.p&1:assert r.a==0xc2;break
  assert t.m.read(C+39)==0;t.invoke('se_bc_arena_cancel');cases.append('ticket-yield-stale-and-final-byte-CRC-refusal')
  # Wrong owners are opaque, including every public operation.
  for owner in (0,1,2,3,5,255):
   t.put('se_f_owner',owner,1);before=t.read(F,576)
   for n in ('se_bc_arena_open','se_bc_arena_step','se_bc_arena_cancel','se_bc_arena_trim','se_bc_page_begin','se_bc_arena_read'):t.call(n,error=0xb2);assert t.read(F,576)==before
  t.put('se_f_owner',4,1);cases.append('wrong-owner-all-entries-opaque')
  # Request dimensions are bound throughout directory/header/payload/proof.
  t.page(15,payload,7,123)
  for byte in range(4):
   t.proof(15,7,123);original=t.m.read(C+4+byte);t.m.write(C+4+byte,original^1);dma=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_arena_step',0xc1);assert t.read(t.s['se_reu_dma_calls'],5)==dma;t.m.write(C+4+byte,original);t.invoke('se_bc_arena_cancel')
  t.proof(15,7,123);t.drain();t.m.write(C+4,14);dma=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_arena_read',0xc1);assert t.read(t.s['se_reu_dma_calls'],5)==dma;t.m.write(C+4,15)
  cases.append('all4-page-request-bytes-bound-across-yield-and-certified-read')
  # Each malformed metadata field is tested independently against validCRC,
  # so checks cannot be accidentally explained by the checksum alone.
  mutants=[(0,0),(1,0),(2,2),(3,0),(4,14),(5,1),(6,124),(8,2),(12,7),(21,193),(22,16),(42,1),(63,1)]
  for at,value in mutants:
   bad=bytearray(h);bad[at]=value;bad[37:39]=crc(bad,(3,37,38)).to_bytes(2,'little');t.object_transfer(15*4096,bad);t.proof(15,7,123);t.invoke('se_bc_arena_step');t.invoke('se_bc_arena_step',0xc2);assert t.m.read(C+39)==0;t.invoke('se_bc_arena_cancel')
  t.object_transfer(15*4096,h)
  for at,value in [(0,1),(1,2),(2,1),(3,0),(6,1),(7,1),(4,e[4]^1)]:
   bad=bytearray(e);bad[at]=value
   if at!=4:bad[4:6]=crc(bad,(4,5)).to_bytes(2,'little')
   t.object_transfer(0x100+15*8,bad);t.proof(15,7,123);t.invoke('se_bc_arena_step',0xc2);t.invoke('se_bc_arena_cancel')
  t.object_transfer(0x100+15*8,e);cases.append('13-rechecksummed-header-and7-directory-corruptions-refuse')
  for pg,kind,gen in [(0,1,1),(16,1,1),(255,1,1),(1,0,1),(1,8,1),(1,1,65535)]:
   t.put(C+4,pg,1);t.put(C+5,kind,1);t.put(C+6,gen,2);dma=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_page_begin',0xc0);assert t.read(t.s['se_reu_dma_calls'],5)==dma
  cases.append('page0/capacity/255/kind/FFFF-refuse-before-DMA')
  # Empty page CRC FFFF, all payload lengths1..128 and cancellation retain
  # the published arena while revoking the caller's temporary page proof.
  for size in (0,1,2,127,128,129,255,256,257,4031,4032):
   raw=bytes((i*17+size)&255 for i in range(size));t.page(1,raw);ro=t.snapshot(True);t.proof();t.drain();t.reu_guard(ro);assert t.m.read(C+39)==0xa5
   if size:t.put(C,4096+64);t.put(C+3,min(128,size),1);t.invoke('se_bc_arena_read');assert t.read(IO,min(128,size))==raw[:128]
   t.invoke('se_bc_arena_cancel');assert t.token()==token and t.m.read(C+39)==0
  cases.append('11-empty/chunk/boundary-lengths-fullCRC-readonly-16MiB-and-cancel')
  # Full type/logical/physical ownership validation beforeDMA/free.
  logical=t.m.read(t.s['object_extents']+token[0]*16);physical=t.physical()
  for name,index in [('se_reu_logical_owner',logical),('se_reu_physical_owner',physical)]:
   address=t.s[name]+index;old=t.m.read(address);t.m.write(address,0x77);before=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_arena_open',0x34);assert t.read(t.s['se_reu_dma_calls'],5)==before;t.m.write(address,old)
  t.invoke('se_bc_arena_trim');assert t.token()==bytes(5) and t.m.read(t.s['se_reu_logical_owner']+logical)==0 and t.m.read(t.s['se_bc_flags'])==2
  t.invoke('se_bc_arena_open');t.invoke('se_bc_arena_step');candidate=t.read(C+10,5);assert candidate!=token;t.invoke('se_bc_arena_cancel');assert t.token()==bytes(5) and t.m.read(t.s['object_owner']+candidate[0])==0;cases.append('logical/physical-owner-refusal/trim/candidate-cancel')
  # New incarnation wrap is refused before allocation and metadata writes.
  t.put('se_bc_incarnation',0xffffffff,4);owners=t.read(t.s['se_reu_map'],768);t.invoke('se_bc_arena_open',0xc1);assert t.read(t.s['se_reu_map'],768)==owners and t.token()==bytes(5);t.put('se_bc_incarnation',1,4)
  # Cancellation at each unpublished phase frees exactly that candidate,
  # including a written but stillINVALID root. A malformed root never writes.
  for stop in (0,1,32,33):
   ro=t.snapshot(True);t.invoke('se_bc_arena_open')
   for _ in range(stop):t.invoke('se_bc_arena_step')
   candidate=t.read(C+10,5);owned=t.physical() if any(t.token()) else t.m.read(t.s['se_reu_map']+t.m.read(t.s['object_extents']+candidate[0]*16));t.invoke('se_bc_arena_cancel');assert t.token()==bytes(5) and t.m.read(t.s['object_owner']+candidate[0])==0;t.reu_guard(ro,owned)
  t.invoke('se_bc_arena_open')
  for _ in range(32):t.invoke('se_bc_arena_step')
  before=t.snapshot(True);t.m.write(IO+127,1);dma=t.read(t.s['se_reu_dma_calls'],5);t.invoke('se_bc_arena_step',0xc2);assert t.read(t.s['se_reu_dma_calls'],5)==dma;t.reu_guard(before);t.invoke('se_bc_arena_cancel')
  cases.append('VALID-last-source-token-publication/cancel0-1-32-33/malformed-root-no-write')
  # Observer MUTATING blocks creation before allocation; LOST alone never
  # invents an ARMED baseline and survives successful initialization.
  t.put('se_bc_flags',4,1);owners=t.read(t.s['se_reu_map'],768);t.invoke('se_bc_arena_open',0xc1);assert t.read(t.s['se_reu_map'],768)==owners;t.put('se_bc_flags',2,1)
  for _ in range(8):t.call('se_object_create',a=4,x=1)
  ro=t.snapshot(True);owners=t.read(t.s['se_reu_map'],768);t.invoke('se_bc_arena_open',0x35);t.reu_guard(ro);assert t.read(t.s['se_reu_map'],768)==owners and t.token()==bytes(5) and t.m.read(C+8)==0
  cases.append('mutation-latch-and-eight-object-pressure-refuse-without-bank/data-leak')
  # New test lifecycle, not a warm source reset: actual provider reset+init
  # deliberately invalidates all preceding handles. Force16 extents onto
  # noncontiguous even physical banks and certify page boundaries across64KiB.
  t.call('se_reu_provider_init');t.call('se_object_init');t.m.load(0x9fb5,bytes(17));t.m.load(C,bytes(61))
  for i in range(16):
   r,_=t.m.call(t.s['se_reu_bind'],a=7,x=190+i,y=2*i+1);assert not r.p&1
  t.call('se_object_create',a=0x53,x=16);multi=t.read(t.s['se_object_id'],5);t.put('se_object_offset',16*65536);t.call('se_object_resize');t.m.load(t.s['se_bc_arena'],multi);t.put('se_bc_incarnation',9,4)
  rr=bytearray(root);rr[8:13]=multi;rr[14:18]=(9).to_bytes(4,'little');rr[119:121]=crc(rr,(5,119,120)).to_bytes(2,'little')
  for offset in range(0,4096,128):t.object_transfer(offset,rr if offset==0 else bytes(128))
  t.invoke('se_bc_arena_open');t.drain()
  physicals=[t.m.read(t.s['se_reu_map']+t.m.read(t.s['object_extents']+multi[0]*16+i)) for i in range(16)];assert physicals==list(range(2,33,2)),physicals
  for pg in (16,31,32,47,48,255):
   raw=bytes((i*31+pg)&255 for i in range(4032));t.page(pg,raw,2,0xfffe);ro=t.snapshot(True);t.proof(pg,2,0xfffe);assert t.drain()==34;t.put(C,pg*4096+64);t.put(C+3,128,1);t.invoke('se_bc_arena_read');assert t.read(IO,128)==raw[:128];t.reu_guard(ro);t.invoke('se_bc_arena_cancel')
  cases.append('16-mapped-even-extents/pages16-31-32-47-48-255/1MiB-exact-end')
  # Currenttoken generation/provider/owner corruption refuses before anyDMA;
  # stale TRIM never frees foreign or recycled allocations.
  stable=t.read(t.s['se_bc_arena'],5)
  for offset in range(5):
   t.m.write(t.s['se_bc_arena']+offset,stable[offset]^0x80);owners=t.read(t.s['se_reu_map'],768);ro=t.snapshot(True);t.invoke('se_bc_arena_open',0x31);t.invoke('se_bc_arena_trim',0x31);t.reu_guard(ro);assert t.read(t.s['se_reu_map'],768)==owners;t.m.load(t.s['se_bc_arena'],stable)
  t.put('se_reu_epoch',t.m.read(t.s['se_reu_epoch'])+1,2);owners=t.read(t.s['se_reu_map'],768);t.invoke('se_bc_arena_open',0x30);t.invoke('se_bc_arena_trim',0x30);assert t.read(t.s['se_reu_map'],768)==owners
  cases.append('five-token-byte/stale-provider/TRIM-before-free-guards')
  # Physical exhaustion has no tentatives to leak; OPEN returns actual1.
  t.put('se_reu_banks',2,2);t.call('se_reu_provider_init');t.call('se_object_init');t.m.load(0x9fb5,bytes(17));t.m.load(C,bytes(61));t.call('se_object_create',a=4,x=1);owners=t.read(t.s['se_reu_map'],768);ro=t.snapshot(True);t.invoke('se_bc_arena_open',1);t.reu_guard(ro);assert t.token()==bytes(5) and t.m.read(C+8)==0 and t.read(t.s['se_reu_map'],768)==owners
  cases.append('actual-two-bank-provider-capacity-refusal-preserves-existing-object')
  result=dict(status='PASS',whole_RAM_intervals=t.ram_intervals,whole_16MiB_intervals=t.reu_intervals,cases=cases,code_bytes=len((out/'arena.bin').read_bytes()),state_bytes=0,zp_bytes=0,phase_bytes=61,io_bytes=128,root_open_steps=steps,calls=t.calls,instructions=t.instructions,peak_instructions=t.peak,resident_sha=t.r['sha256'],scope='private actual6510 transport; no integrated semantic cache or native claim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 finally:t.m.close()


# Writer profile proof runs actual semantic parser output through R33. The
# source producer is not replaced by host packets; host models only verify.
def run_writer(out,base):
 import test_cache_semantic as semantic
 from overlays import wrap,HEADER
 from supermark_model import blocks,inline
 frozen,identity=semantic.geos.freeze(out,base)
 linked,semantic_budget=semantic.build(out/'semantic',frozen)
 report=json.loads((frozen/'build/editor-report.json').read_text());binding=report['resident_binding']['digest'];s=report['symbols']
 leaf=out/'writer';leaf.mkdir();objs=[]
 (leaf/'entry.s').write_text('''.setcpu "6502"
.include "cache/arena/writer.inc"
.import se_overlay_frame,se_f_owner
.segment "CODE"
.byte '''+','.join('$'+binding[i:i+2] for i in range(0,32,2))+'''
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq open
 cmp #1
 beq step
 cmp #2
 beq cancel
 cmp #3
 beq trim
 cmp #4
 beq begin
 cmp #5
 beq append
 cmp #6
 beq final
 cmp #7
 beq abort
 lda #$C0
 sec
 rts
busy:lda #$B2
 sec
 rts
open:jmp se_bc_arena_open
step:jmp se_bc_arena_step
cancel:jmp se_bc_arena_cancel
trim:jmp se_bc_arena_trim
begin:jmp se_bc_write_begin
append:jmp se_bc_write_append
final:jmp se_bc_write_final
abort:jmp se_bc_write_cancel
''')
 for name,path in [('entry',leaf/'entry.s')]+[(n,ROOT/f'src/cache/arena/{n}.s') for n in ('control','core','open','writer')]:
  obj=leaf/(name+'.o');command('ca65','-g','-I','src','-D','BCA_WRITER_PROFILE=1','-o',obj,path);objs.append(obj)
 seam={n:linked[n] for n in ('se_bc_arena','se_bc_ticket','se_bc_incarnation','se_bc_flags','se_bc_head','se_bc_tail','se_bc_count','se_bc_ring')}
 (leaf/'seam.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${a:04X}' for n,a in seam.items())+'\n');command('ca65','-o',leaf/'seam.o',leaf/'seam.s');objs.append(leaf/'seam.o')
 command(sys.executable,'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',leaf/'aliases.s',*objs);command('ca65','-o',leaf/'aliases.o',leaf/'aliases.s');objs.append(leaf/'aliases.o')
 (leaf/'leaf.cfg').write_text('MEMORY { R:file=%O,start=$A000,size=$1000; } SEGMENTS { CODE:load=R,type=ro; RODATA:load=R,type=ro; }')
 command('ld65','-C',leaf/'leaf.cfg','-o',leaf/'writer.bin','-Ln',leaf/'writer.lbl','-m',leaf/'writer.map',*objs)
 raw=(leaf/'writer.bin').read_bytes();assert len(raw)<=4096
 image=wrap(raw,0,33,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(leaf/'writer.seo').write_bytes(image)
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=frozen;semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=identity['names']
 dll=semantic.geos.grid.runner(out);f=semantic.Fixture(out,frozen,dll,True);cases=[];raw_worker=(out/'semantic/worker.bin').read_bytes();canonical=None
 writer_calls=0;writer_peak=0;producer_protected=0
 def wc(op,error=None):
  nonlocal writer_calls,writer_peak,producer_protected
  before=f.read(F,387);ram=f.read(0,65536);f.put('se_overlay_frame',op,1);r,n=f.fast_call(s['se_overlay_call'],a=33,x=0);f.total_instructions+=n;writer_calls+=1;writer_peak=max(writer_peak,n)
  assert bool(r.p&1)==(error is not None),('writer',op,hex(r.a),hex(f.m.read(C+8)),f.read(C,61).hex(),error)
  if error is not None:assert r.a==error,('writer-error',op,hex(r.a),hex(error))
  assert f.read(F,387)==before,('writer-touched-producer387',op)
  after=f.read(0,65536);wanted=bytearray(ram)
  pairs=[('se_crc_value',2),('se_object_id',12),('new_owner',5),('validate_index',3),('copy_direction',12),('object_owner',184),('se_reu_c64',16),('se_reu_map',768),('provider_owner',1),('ovl_ptr',2),('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_frame',16),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_overlay_header',36),('image_slot',s['se_overlay_capacity'])]
  ranges=[(s[n],s[n]+w) for n,w in pairs]+[(0x100,0x200),(C,F+576),(0x9fb5,0x9fc6),(0xcc4d,0xcc4e),(0xcbd5,0xcbd6),(0xdf00,0xdf0b),(0x5000,0x6000),(0xa000,0xb000)]
  for lo,hi in ranges:wanted[lo:hi]=after[lo:hi]
  assert after==wanted,('writer-wholeRAM',op,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))
  assert f.read(0xc600,1024)==f.shim;producer_protected+=1
  return r
 def drain():
  for steps in range(10000):
   if f.m.read(C+8)==10 or f.m.read(C+8)==0:return steps
   wc(1)
  raise AssertionError('writer never settled')
 def start(data,lost=False,pending=False,begin_writer=True,queued=False):
  f.source(data)
  if pending:f.key(semantic.geos.native_text("Q")[0])
  f.s.update(seam);f.m.load(seam['se_bc_arena'],bytes(17))
  if queued:
   # Schema-valid historical queue fixture, not forged semantic cache output.
   # Real full-source parsing below independently establishes the new baseline.
   events=[]
   for ticket in (1,2,3):
    event=bytearray(32);event[1]=2;event[4:8]=ticket.to_bytes(4,'little');event[8:12]=(ticket-1).to_bytes(4,'little');event[12:16]=ticket.to_bytes(4,'little');event[25:27]=(ticket).to_bytes(2,'little');event[27:29]=(ticket+1).to_bytes(2,'little');event[29:31]=crc(event,(0,29,30)).to_bytes(2,'little');event[0]=0xa5;events.append(event)
   f.m.load(seam['se_bc_ring'],b''.join(events));f.put('se_bc_ticket',3,4);f.put('se_bc_head',0,1);f.put('se_bc_tail',0,1);f.put('se_bc_count',3,1)
  f.put('se_f_owner',4,1);f.m.load(F,bytes(576));f.m.write(F,1);f.m.write(F+5,1)
  f.m.load(s['se_overlay_header'],image[:HEADER]);f.m.load(0x5000,image[HEADER:]);assert not f.call('se_overlay_import').p&1
  wc(0);drain();token=f.read(seam['se_bc_arena'],5);inc=f.read(seam['se_bc_incarnation'],4);ticket=f.read(seam['se_bc_ticket'],4);f.m.load(F+8,token+inc+ticket)
  if lost:f.put('se_bc_flags',2,1);f.m.write(F+6,128)
  f.install(raw_worker,linked);r,_=f.cc('se_bsc_begin');assert not r.p&1 and r.a==1
  if begin_writer:wc(4);drain()
  return token
 def arena_bank(token):
  handle=f.m.read(s['object_extents']+token[0]*16);physical=f.m.read(s['se_reu_map']+handle);allreu=f.reu();return allreu[physical*65536:(physical+1)*65536],physical,allreu
 def check(tag,data,lost=False,pending=False,queued=False):
  token=start(data,lost,pending,queued=queued);before,physical,allbefore=arena_bank(token);canonical=f.canonical();catalog=f.catalog();source=f.merged();data=source;records=[];events=[];steps=0
  queue=f.read(seam['se_bc_head'],3);queued_records=f.read(seam['se_bc_ring'],96);observed=f.read(seam['se_bc_ticket'],4)
  if queued:assert queue==b'\0\0\3'
  while True:
   r,_=f.cc('se_bsc_step');assert not r.p&1,(tag,'producer',r.a);steps+=1;assert steps<100000
   if r.a==0:break
   ready=f.m.read(F+4)
   if ready:
    if ready==1:records.append(f.read(IO,96))
    else:events.append((int.from_bytes(f.read(F+291+16,3),'little'),f.read(IO,10)))
    wc(5);drain();assert f.read(seam['se_bc_head'],3)==queue and f.read(seam['se_bc_ring'],96)==queued_records;r,_=f.cc('se_bsc_ack');assert not r.p&1,(tag,'ACK',r.a)
  if tag=='real-mixed':
   for at,value,error in [(F+60,0,0xc0),(F+21,f.m.read(F+21)^1,0xc1),(F+50,f.m.read(F+50)^1,0xc1),(F+173+8,1,0xc0)]:
    old=f.m.read(at);f.m.write(at,value);snapshot=f.reu();wc(6,error=error);assert f.reu()==snapshot and not f.m.read(seam['se_bc_flags'])&1;f.m.write(at,old)
  assert f.read(seam['se_bc_head'],3)==queue
  wc(6)
  if queued:
   while f.m.read(C+8)!=18:
    wc(1);assert f.read(seam['se_bc_head'],3)==queue
   bank,_,_=arena_bank(token);assert bank[128+5]==0 and f.m.read(seam['se_bc_flags'])&3==2
   wc(1);assert f.read(seam['se_bc_head'],3)==bytes(3)
  else:drain()
  assert f.read(seam['se_bc_head'],3)==bytes(3) and f.read(seam['se_bc_ticket'],4)==observed and f.read(seam['se_bc_ring'],96)==queued_records
  bank,_,after=arena_bank(token);root=bank[128:256]
  assert root[:8]==b'BCA1\1\1\x80\0' and int.from_bytes(root[18:22],'little')==2 and root[31]==1 and root[32:91]==f.read(F+173+27,59) and int.from_bytes(root[91:94],'little')==len(data),(tag,'root',root.hex())
  assert int.from_bytes(root[119:121],'little')==crc(root,(5,119,120))
  assert f.m.read(seam['se_bc_flags'])&3==1 and f.m.read(C+8)==0
  wc(0);drain();assert f.read(IO,128)==root,(tag,'postpublication-newest-OPEN')
  pages={}
  for pg in range(1,15):
   e=bank[0x100+pg*8:0x108+pg*8]
   if not e[3]:continue
   assert e[3]==1 and int.from_bytes(e[4:6],'little')==crc(e,(4,5))
   header=bank[pg*4096:pg*4096+64];used=int.from_bytes(header[21:23],'little');payload=bank[pg*4096+64:pg*4096+64+used]
   assert header[:8]==b'BP\1\1'+bytes([pg,e[2]])+b'\1\0' and header[8:12]==root[14:18] and header[12:17]==token
   assert int.from_bytes(header[37:39],'little')==crc(header,(3,37,38)) and int.from_bytes(header[39:41],'little')==crc(payload)
   pages[pg]=(header,payload)
  got=[]
  for pg,(h,payload) in sorted(pages.items()):
   if h[5]==1:
    count=int.from_bytes(h[23:25],'little');assert len(payload)==count*96
    for slot in range(count):got.append((bytes([pg,slot,1,0]),payload[slot*96:slot*96+96]))
  assert len(got)==len(records)==int.from_bytes(root[112:115],'little'),(tag,'recordcount',len(got),len(records),root.hex())
  assert root[104:108]==got[0][0] and root[108:112]==got[-1][0]
  found_events=[]
  for (ref,record),expected in zip(got,records):
   assert record[:40]==expected[:40] and record[44:74]==expected[44:74] and record[84:]==expected[84:] and record[76:84]==b'\xff'*8
   assert int.from_bytes(record[74:76],'little')==crc(record[1:74]+record[76:])
   amount=int.from_bytes(record[44:47],'little');ref=record[40:44]
   if not amount:assert ref==b'\xff'*4
   for _ in range(amount):
    pg,slot=ref[:2];h,p=pages[pg];assert h[5]==2 and ref[2:]==b'\1\0';count=int.from_bytes(h[23:25],'little')
    if slot==count:ref=h[29:33];pg,slot=ref[:2];h,p=pages[pg]
    found_events.append((int.from_bytes(record[16:19],'little'),p[slot*10:slot*10+10]));ref=bytes([pg,slot+1,1,0])
  assert found_events==events,(tag,'events',found_events[:3],events[:3])
  semantic_oracle=blocks(data);real_records=[record for _,record in got if not record[2]&8];assert len(real_records)==len(semantic_oracle)
  expected_events=[]
  for record,event in zip(real_records,semantic_oracle):
   a,b,body=event['start'],event['end'],event['body'];next_=b+int(b<len(data) and data[b]==13)
   assert record[3]==event['kind'] and [int.from_bytes(record[i:i+3],'little') for i in (16,19,22,25)]==[a,b-a,body-a,next_-a]
   if event['kind']<4:
    for kind,style,width,opened,closed in inline(data[body:b],start=body,body_column=body-a):expected_events.append((a,bytes([kind,style,width])+(opened-a).to_bytes(3,'little')+(closed-a).to_bytes(3,'little')+b'\0'))
  assert found_events==expected_events,(tag,'independent-fullsource-semantic/inline-oracle')
  assert source==f.merged()==data and f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim and not f.get('se_doc_read_locks',1)
  lo=physical*65536;assert after[:lo]==allbefore[:lo] and after[lo+65536:]==allbefore[lo+65536:]
  entry=dict(tag=tag,source_bytes=len(data),records=len(got),inline_events=len(events),pages=len(pages),producer_steps=steps,writer_bytes=len(raw));cases.append(entry);print('PASS writer',entry,flush=True)
 try:
  check('real-mixed',semantic.geos.native_text('# Heading **bold** *emph*\r:::basic\r10 PRINT "Hi"\r:::\rTail @@code@@.'))
  check('real-empty',b'')
  check('real-multi-page',semantic.geos.native_text(('Body **pair** *em* @@code@@\r')*60))
  check('real-one-line-300-events',semantic.geos.native_text(('**a** '*300)+'\r'))
  check('real-far-body-over64KiB',b'A'*66000+semantic.geos.native_text(' **late**\rTail.'))
  check('real-pending-merged',semantic.geos.native_text('Body **pair**\rTail.'),pending=True)
  check('real-LOST-explicit-rebuild',semantic.geos.native_text('Recovered **meaning**\rTail.'),lost=True,queued=True)
  # Existing semantic authority cannot be silently replaced by an initial
  # baseline builder; future COW/growth logic is a separate operation.
  ro=f.reu();wc(4,error=0xc0);assert f.reu()==ro
  faults=[]
  def pending_output(data,queued=False):
   token=start(data,lost=queued,queued=queued)
   for _ in range(10000):
    r,_=f.cc('se_bsc_step');assert not r.p&1
    if f.m.read(F+4):return token
   raise AssertionError('no producer output')
  # LOST is only a rebuild request after initial EMPTY root authorization;
  # no early clearing and no semantic authority from an allzero FS snapshot.
  token=start(b'One\rTail.',begin_writer=False,queued=True);f.put('se_bc_flags',2,1);before=f.reu();wc(4,error=0xc1);assert f.reu()==before and f.m.read(seam['se_bc_flags'])==2 and f.read(seam['se_bc_head'],3)==b'\0\0\3'
  f.m.write(F+6,128);wc(4);drain();assert f.m.read(seam['se_bc_flags'])&3==2
  original_identity=f.read(F+173+27,59);f.m.load(F+173+27,bytes(59));before=f.reu();wc(5,error=0xc1);assert f.reu()==before;f.m.load(F+173+27,original_identity);r,_=f.cc('se_bsc_cancel');assert not r.p&1;wc(7);assert f.read(seam['se_bc_head'],3)==b'\0\0\3';faults.append('LOST-needs-explicit-REBUILD-and-zeroFS-cannot-authorize')
  # All service entry opcodes preserve an opaque foreign phase owner.
  token=start(b'Owner guard.')
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);opaque=f.read(F,576);before=f.reu()
   for op in range(8):wc(op,error=0xb2);assert f.read(F,576)==opaque
   assert f.reu()==before
  f.put('se_f_owner',4,1);r,_=f.cc('se_bsc_cancel');assert not r.p&1;wc(7);faults.append('sixforeignowners/all8opcodes-opaque')
  # Formal FINAL cannot mistake CANCEL's cleared state for completed parsing.
  token=pending_output(b'First\rSecond\rThird\r',queued=True);wc(5);drain();r,_=f.cc('se_bsc_cancel');assert not r.p&1;before=f.reu();wc(6,error=0xc0);assert f.reu()==before and not f.m.read(seam['se_bc_flags'])&1 and f.read(seam['se_bc_head'],3)==b'\0\0\3';wc(7);assert f.read(seam['se_bc_head'],3)==b'\0\0\3';faults.append('partial-producer-CANCEL-cannot-FINAL-arm')
  # Every real source field and every13B captured authority byte is guarded.
  token=pending_output(semantic.geos.native_text('One **pair**\rTail.'))
  for at in [*range(F+8,F+21),*range(F+66,F+79),s['se_r_revision'],s['se_doc_generation'],s['se_hot_left'],*(s[n] for n in ('se_doc_busy','se_h_phase','se_b_phase','se_clip_busy','se_snapshot_busy'))]:
   old=f.m.read(at);f.m.write(at,old^1);before=f.reu();wc(5,error=0xc1);assert f.reu()==before;f.m.write(at,old)
  # A copied snapshot alone cannot authorize a stale source object's mapping.
  original=f.read(s['se_doc_original'],5);logical=f.m.read(s['object_extents']+original[0]*16);physical=f.m.read(s['se_reu_map']+logical);old=f.m.read(s['se_reu_physical_owner']+physical);f.m.write(s['se_reu_physical_owner']+physical,0x77);before=f.reu();wc(5,error=0x34);assert f.reu()==before;f.m.write(s['se_reu_physical_owner']+physical,old)
  r,_=f.cc('se_bsc_cancel');assert not r.p&1;wc(7);faults.append('13+13authority/live-source/all-five-busy-exclusions/actualphysical-source-ownership-refuse-readonly')
  # CRC-invalid actual producer CR does not persist. Only producer-ownedCR is
  # altered here as an explicit malformed-output fault, then restored.
  token=pending_output(b'One\rTail.')
  assert f.m.read(F+4)==1;old=f.m.read(F+291+74);f.m.write(F+291+74,old^1);before=f.reu();wc(5,error=0xc2);assert f.reu()==before;f.m.write(F+291+74,old);r,_=f.cc('se_bsc_cancel');assert not r.p&1;wc(7);faults.append('producer-CR-invalidCRC-no-payload-write')
  # Exhaustion streams rather than publishing a truncated root.
  for tag,data in [('CR-pressure',b'A\r'*600),('INLINE-pressure',semantic.geos.native_text('**a** '*3600))]:
   token=start(data);_,physical,before=arena_bank(token);canonical=f.canonical();stream=False
   for _ in range(200000):
    r,_=f.cc('se_bsc_step');assert not r.p&1
    if f.m.read(F+4):
     r=wc(5)
     if r.a==3:stream=True;break
     drain();r,_=f.cc('se_bsc_ack');assert not r.p&1
    if r.a==0:break
   assert stream,(tag,'didnotstream');bank,_,after=arena_bank(token);assert bank[5]==1 and bank[31]==0 and bank[128+5]==0 and not f.m.read(seam['se_bc_flags'])&1 and f.m.read(C+8)==0
   r,_=f.cc('se_bsc_cancel');assert not r.p&1;assert not f.get('se_doc_read_locks',1) and f.canonical()==canonical and f.merged()==data
   lo=physical*65536;assert before[:lo]==after[:lo] and before[lo+65536:]==after[lo+65536:];faults.append(tag+'-STREAM-no-truncated-root')
  # Both absent service and caller cancellation leave source/leases safe.
  token=pending_output(b'One\rTail.');catalog=f.catalog();index=len(identity['names']);entry=s['se_overlay_ids']+index;assert f.m.read(entry)==33
  saved=f.read(entry,1);f.m.write(entry,0);before=f.reu();wc(5,error=0x17);assert f.reu()==before;f.m.load(entry,saved);r,_=f.cc('se_bsc_cancel');assert not r.p&1;wc(7);assert not f.get('se_doc_read_locks',1);faults.append('missingR33-beforeappend/producercancel-leasecleanup')

  result=dict(status='PASS',profile='R33 writer core/open/control without standalone readerpage',writer_bytes=len(raw),semantic_budget=semantic_budget,cases=cases,faults=faults,writer_calls=writer_calls,writer_peak_instructions=writer_peak,producer387_intervals=producer_protected,queue_retirement='three CRC/schema-valid stale REKEY records retained throughbuild/refusal/cancel; indicescleared onlyafterVALID-last; observedticket/ringbytespreserved',resident_sha=report['sha256']);(out/'writer-result.json').write_text(json.dumps(result,indent=2)+'\n');print('WRITER RESULT',json.dumps(result),flush=True);return result
 except BaseException:
  (out/'writer-failed-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--writer',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/cache-arena'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 if a.writer:run_writer(out,a.fixture or ROOT/'build/plain-geos/20261025T223041055764Z/fixture')
 else:run(out,a.fixture or DEFAULT)
