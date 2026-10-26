"""Private actual baseline→checked query; parser code never runs on queryhits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as CT,json,re,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_arena as arena
import test_cache_semantic as semantic
from overlays import wrap,HEADER
from peddle import VENDOR
from supermark_model import blocks,inline
BASE=ROOT/'build/plain-geos/20261025T223041055764Z/fixture';F=0x8D00;IO=F+448;C=F+387

def command(*a):return subprocess.run(list(map(str,a)),cwd=ROOT,check=True,capture_output=True,text=True)
def labels(p):return {n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}
def build(out,base,editor=False):
 out.mkdir();r=json.loads((base/'build/editor-report.json').read_text());binding=r['resident_binding']['digest'];s=r['symbols'];objs=[]
 (out/'entry.s').write_text('''.setcpu "6502"
.include "cache/query/api.inc"
.import se_f_owner,se_overlay_frame
.segment "CODE"
.byte '''+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'''
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 beq step
 cmp #2
 beq cancel
 cmp #3
 beq ack
 lda #$C0
 sec
 rts
busy:lda #$B2
 sec
 rts
begin:jmp se_bc_query_begin
step:jmp se_bc_query_step
cancel:jmp se_bc_query_cancel
ack:jmp se_bc_query_ack
''')
 for name,path,defs in [('entry',out/'entry.s',[])]+[(n,ROOT/f'src/cache/query/{n}.s',[])for n in ('query','source','records')]+[(n,ROOT/f'src/cache/arena/{n}.s',['BCA_READONLY_OPEN=1']if n=='open'else[])for n in ('core','open','page')]:
  obj=out/(name+'.o');command('ca65','-g','-I','src',*[v for d in defs for v in ['-D',d]],*(['-D','BCQ_EDITOR_ACTIVE=1']if editor and name in ('entry','query','source','records')else[]),'-o',obj,path);objs.append(obj)
 seam={'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85}
 (out/'state.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${v:04X}'for n,v in seam.items())+'\n');command('ca65','-o',out/'state.o',out/'state.s');objs.append(out/'state.o')
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs);command('ca65','-o',out/'aliases.o',out/'aliases.s');objs.append(out/'aliases.o')
 (out/'query.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }');command('ld65','-C',out/'query.cfg','-o',out/'query.bin','-Ln',out/'query.lbl','-m',out/'query.map',*objs)
 raw=(out/'query.bin').read_bytes();assert len(raw)<=4096
 image=wrap(raw,1,35,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(out/'query.seo').write_bytes(image)
 return image,labels(out/'query.lbl'),seam

def run(out,base,editor=False):
 # Existing released pipeline independently requalifies the writer and emits
 # exact linked R33/C34 modules. No editor/shared make or host semantic seeding.
 prep=out/'baseline';prep.mkdir();arena.run_writer(prep,base);frozen=prep/'fixture';writer=(prep/'writer/writer.seo').read_bytes();worker=(prep/'semantic/worker.bin').read_bytes();c=labels(prep/'semantic/worker.lbl')
 report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];identity=json.loads((frozen/'freeze.json').read_text());names=identity['names'];binding=report['resident_binding']['digest']
 semantic_image=wrap(worker,1,34,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding))
 query,q,seam=build(out/'query',frozen,editor)
 if editor:
  default,_,_=build(out/'default-profile',frozen)
  assert hashlib.sha256(default[HEADER:]).hexdigest()=='9233b2e7b77ec4a04b17f4c6c4e4dcf32c8197c31d6dc0f9bc56b59a8f61d0c0'
 qcr=259 if editor else 180;qref=128 if editor else 310;s.update(seam)
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=frozen;semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=names
 dll=semantic.geos.grid.runner(out);f=semantic.Fixture(out,frozen,dll,True);f.s.update(seam);cases=[]
 # Trace actual nested admissions, never patch CPU/code or mock source reads.
 ext='.dylib' if sys.platform=='darwin' else '.so'
 (out/'trace.cpp').write_text('#include "zeropage_peddle.h"\n#include <cstdint>\nstatic uint64_t calls[2][256],ops[256];\nextern "C" void qclear(){for(auto &r:calls)for(auto &v:r)v=0;for(auto &v:ops)v=0;}\nextern "C" uint64_t qmetric(int slot,int id){return slot==2?ops[id]:calls[slot][id];}\nextern "C" uint64_t qrun(ZeroPagePeddle*m,unsigned address,unsigned frame,uint64_t limit){auto first=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){auto r=zeropage_peddle_regs(m);if(r.pc==0x2ff)return r.instructions-first;if(r.pc==address && r.x<2){calls[r.x][r.a]++;if(!r.x && r.a==14)ops[zeropage_peddle_read(m,frame)]++;}zeropage_peddle_step_instruction(m);}return 0;}')
 command('clang++','-O2','-std=c++20','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),out/'trace.cpp',ROOT/('build/libse_peddle'+ext),'-o',out/('trace'+ext))
 trace=CT.CDLL(str(out/('trace'+ext)));trace.qclear.argtypes=[];trace.qmetric.argtypes=[CT.c_int,CT.c_int];trace.qmetric.restype=CT.c_uint64;trace.qrun.argtypes=[CT.c_void_p,CT.c_uint,CT.c_uint,CT.c_uint64];trace.qrun.restype=CT.c_uint64
 tracing=False;query_calls=0;ram_guards=0

 def import_image(image):
  f.m.load(s['se_overlay_header'],image[:HEADER]);f.m.load(0x5000,image[HEADER:]);r=f.call('se_overlay_import');assert not r.p&1,(image[5:7],r.a)
 def service(ident,slot,op,error=None):
  nonlocal query_calls,ram_guards
  ram=f.read(0,65536) if ident==35 else None
  f.put('se_overlay_frame',op,1)
  if tracing and ident==35:
   for name,value in [('pc',s['se_overlay_call']),('sp',0xfd),('p',0x24),('a',ident),('x',slot),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+name)(f.m.handle,value)
   f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2);n=trace.qrun(f.m.handle,s['se_overlay_call'],s['se_overlay_frame'],8_000_000);assert n;r=f.m.regs()
  else:r,n=f.fast_call(s['se_overlay_call'],a=ident,x=slot)
  f.total_instructions+=n
  if ident==35:
   query_calls+=1;after=f.read(0,65536);wanted=bytearray(ram)
   pairs=[('se_crc_value',2),('se_object_id',12),('new_owner',5),('validate_index',3),('copy_direction',12),('se_reu_c64',16),('ovl_ptr',2),('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_frame',16),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_overlay_header',36),('image_slot',s['se_overlay_capacity']),('se_doc_read_locks',1)]+([('se_bc_flags',1)]if editor else[])
   ranges=[(s[name],s[name]+width)for name,width in pairs]+[(0x100,0x200),(F,F+576),(0x5000,0x6000),(0xa000,0xc000),(0xcbd5,0xcbd6),(0xdf00,0xdf0b)]
   for lo,hi in ranges:wanted[lo:hi]=after[lo:hi]
   assert after==wanted,('querywholeRAM',op,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b));ram_guards+=1
  assert bool(r.p&1)==(error is not None),(ident,op,r.a,r.p,error,f.read(F,32).hex())
  if error is not None:assert r.a==error
  return r
 def w(op):return service(33,0,op)
 def sem(op):return service(34,1,op)
 def wd():
  for _ in range(10000):
   if f.m.read(C+8)in(0,10):return
   w(1)
  raise AssertionError('writer stuck')
 def baseline(data,pending=False):
  f.source(data)
  if pending:f.key(semantic.geos.native_text('Q')[0]);data=f.merged()
  f.m.load(seam['se_bc_arena'],bytes(17));f.put('se_f_owner',4,1);f.m.load(F,bytes(576));f.m.write(F,1);f.m.write(F+5,1)
  for image in (writer,semantic_image,query):import_image(image)
  w(0);wd();token=f.read(seam['se_bc_arena'],5);f.m.load(F+8,token+f.read(seam['se_bc_incarnation'],4)+f.read(seam['se_bc_ticket'],4));sem(0);w(4);wd()
  for _ in range(100000):
   r=sem(1)
   if not r.a:break
   if f.m.read(F+4):w(5);wd();sem(3)
  else:raise AssertionError('producer stuck')
  w(6);wd();assert f.m.read(seam['se_bc_flags'])==1 and not f.get('se_doc_read_locks',1)
  return data
 def query_at(pos):
  nonlocal tracing
  tracing=True;trace.qclear()
  f.m.load(F,bytes(387));f.m.write(F,1);f.m.write(F+5,1);f.m.load(F+8,pos.to_bytes(3,'little'));canonical=f.canonical();before=f.reu();r=service(35,1,0);records=[];events=[];steps=0
  while r.a:
   assert r.a==1,(pos,r.a);r=service(35,1,1);steps+=1;assert steps<100000
   ready=f.m.read(F+4)
   if editor:assert f.m.read(seam['se_bc_flags'])==(9 if f.m.read(F+3)else 1)
   if ready:
    packet=f.read(IO,96 if ready==1 else 10)
    if ready==1:records.append(packet)
    else:events.append(packet)
    # HeldSTEP must not overwrite a packet or cause another source callback.
    state=f.read(F,387);again=service(35,1,1);assert again.a==1 and f.read(IO,len(packet))==packet and f.read(F,387)==state
    r=service(35,1,3)
  assert len(records)==1 and f.m.read(F+6)==0 and not f.get('se_doc_read_locks',1)
  assert f.m.read(seam['se_bc_flags'])==1
  assert f.reu()==before and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  assert trace.qmetric(1,35)>0 and trace.qmetric(0,14)>0
  assert sum(trace.qmetric(1,i)for i in range(256)if i!=35)==0 and sum(trace.qmetric(0,i)for i in range(256)if i!=14)==0
  assert sum(trace.qmetric(2,i)for i in range(256)if i not in(0,1))==0
  tracing=False
  return records[0],events,steps
 def check(tag,data,positions,pending=False):
  data=baseline(data,pending);oracle=blocks(data)
  for pos in positions:
   record,events,steps=query_at(pos)
   event=next((e for e in oracle if e['start']<=pos<=e['end']),None)
   if event is None:
    assert record[3]==255 and pos==len(data) and record[2]==10
    expected=[]
   else:
    a,b,body=event['start'],event['end'],event['body'];assert record[3]==event['kind'] and[int.from_bytes(record[i:i+3],'little')for i in(16,19,22,25)]==[a,b-a,body-a,b+int(b<len(data)and data[b]==13)-a]
    expected=[]
    if event['kind']<4:
     for kind,style,width,opened,closed in inline(data[body:b],start=body,body_column=body-a):expected.append(bytes([kind,style,width])+(opened-a).to_bytes(3,'little')+(closed-a).to_bytes(3,'little')+b'\0')
   assert events==expected,(tag,pos,'events',events[:3],expected[:3])
  entry=dict(tag=tag,source_bytes=len(data),queries=len(positions),query_bytes=len(query)-36);cases.append(entry);print('QUERY PASS',entry,flush=True)
 try:
  data=semantic.geos.native_text('# Heading **bold**\rBody *em* @@code@@.\r:::basic\r10 PRINT "Hi"\r:::\rTail.')
  check('mixed-real-baseline',data,sorted({0,len(data),*(e['start']for e in blocks(data)),*(e['end']for e in blocks(data))}))
  check('empty-real-EOF',b'',[0])
  check('CR-real-sentinel',b'\r\r',[0,1,2])
  check('300-event-stream',semantic.geos.native_text(('**a** '*300)+'\r'),[0,128,1024,1800,1801])
  check('far-body',b'A'*66000+semantic.geos.native_text(' **late**\rTail.'),[0,65535,65536,66000,66008,66015])
  # Reuse one actual completed baseline; every fault starts from the exact
  # saved RAM boundary, never from host-synthesized successful descriptors.
  data=baseline(semantic.geos.native_text('Body **bold** £*literal\rTail.'))
  stable=f.read(0,65536);stable_reu=f.reu();faults=[]
  def reset():f.m.load(0,stable)
  def start():
   f.m.load(F,bytes(387));f.m.write(F,1);f.m.write(F+5,1)
   return service(35,1,0)
  def until_ready():
   r=start()
   for _ in range(10000):
    assert r.a==1
    r=service(35,1,1)
    if f.m.read(F+4):return
   raise AssertionError('fault setup stuck')
  def no_mutation():
   assert f.reu()==stable_reu and f.read(0xc600,1024)==f.shim
  for owner in (0,1,2,3,5,255):
   for op in range(4):
    reset();f.put('se_f_owner',owner,1);before=f.read(F,576)
    service(35,1,op,0xb2);assert f.read(F,576)==before;no_mutation()
  faults.append('sixforeignowners/all4operations opaque')
  for flags in (0,2,3,4,5,8,9):
   reset();f.put('se_bc_flags',flags,1);assert start().a==2;no_mutation()
  reset();f.put('se_bc_count',1,1);assert start().a==2;no_mutation()
  reset();f.m.load(seam['se_bc_arena'],bytes(5));before=f.read(s['object_owner'],184);assert start().a==2;assert f.read(s['object_owner'],184)==before;no_mutation()
  faults.append('unarmed/LOST/MUTATING/ACTIVE/nonemptyqueue/missingtoken miss without allocation')
  for stage in (0,1,3,10,20,40):
   reset();r=start()
   for _ in range(stage):
    if f.m.read(F+4):break
    r=service(35,1,1)
   service(35,1,2);assert not f.get('se_doc_read_locks',1) and f.read(F+1,4)==bytes(4);no_mutation()
  reset();until_ready();assert f.get('se_doc_read_locks',1)==1
  # A foreign client's independently held lease is not query-owned.
  f.put('se_doc_read_locks',2,1);service(35,1,2);assert f.get('se_doc_read_locks',1)==1;no_mutation()
  faults.append('cancel root/page/heldCR releases only owned source lease; published token retained')
  for offset in range(13):
   reset();until_ready();at=seam['se_bc_arena']+offset;old=f.m.read(at);f.m.write(at,old^1)
   service(35,1,1,0xc1);assert f.m.read(F+1)==0;f.m.write(at,old);no_mutation()
  for name in ('se_r_revision','se_doc_generation','se_hot_left','se_doc_busy'):
   reset();until_ready();at=s[name];old=f.m.read(at);f.m.write(at,old^1)
   # ACK drains the packet, then the actual R14 guard checks immutable source.
   f.put('se_overlay_frame',3,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1);assert r.p&1,(name,r.a);f.m.write(at,old);assert not f.m.read(F+1);no_mutation()
  faults.append('all13 authority bytes and actual source revision/generation/gap/busy refuse')
  reset();until_ready();f.put('se_overlay_frame',3,1)
  # Remove R14 from its actual typed catalogue: cleanup must remain resident.
  capacity=s['se_overlay_capacity'];catalog=s['se_overlay_ids'];old=f.read(catalog,capacity*6)
  for i in range(capacity):
   if f.m.read(catalog+i)==14 and f.m.read(s['image_slot']+i)&1==0:f.m.write(catalog+i,255);break
  else:raise AssertionError('R14 catalogue entry missing')
  r,n=f.fast_call(s['se_overlay_call'],a=35,x=1);assert r.p&1 and r.a==0x17,(r.a,r.p)
  assert not f.get('se_doc_read_locks',1) and not f.m.read(F+1);f.m.load(catalog,old);no_mutation()
  faults.append('missingR14 ACK releases owned lease through resident END')
  reset()
  def transfer(offset,raw=None,length=0):
   f.m.load(s['se_object_id'],f.read(seam['se_bc_arena'],5));f.put('se_object_offset',offset);f.put('se_object_length',len(raw)if raw is not None else length,2);f.put('se_object_c64',IO,2)
   if raw is not None:f.m.load(IO,raw)
   r=f.call('se_object_copy',a=int(raw is None));assert not r.p&1
   return f.read(IO,len(raw)if raw is not None else length)
  # Corrupt both root copies. A still-good older EMPTY root cannot authorize a
  # semantic result even if it is independently CRC-valid.
  roots=[transfer(at,length=128)for at in (0,128)]
  for at,root in zip((0,128),roots):
   bad=bytearray(root);bad[119]^=1;transfer(at,bad)
  corrupt=f.reu();reset();r=start()
  for _ in range(10):
   if r.p&1:break
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1)
  assert r.p&1 and r.a==0xc2 and not f.m.read(F+1);assert f.reu()==corrupt
  for at,root in zip((0,128),roots):transfer(at,root)
  assert f.reu()==stable_reu
  faults.append('both root CRC failures cannot authorize semantic hit')
  reset();until_ready();record=f.read(F+qcr,96);ref=f.read(F+qref,4);page=ref[0];slot=ref[1];pageheader=transfer(page*4096,length=64);used=int.from_bytes(pageheader[21:23],'little');payload=b''.join(transfer(page*4096+64+at,length=min(128,used-at))for at in range(0,used,128))
  service(35,1,2)
  for tag,change in [('CR-reserved',lambda b:b.__setitem__(95,1)),('INLINE-count-NIL',lambda b:b.__setitem__(slice(40,44),b'\xff'*4)),('CR-ABI',lambda b:b.__setitem__(1,2))]:
   bad=bytearray(record);change(bad);bad[74:76]=arena.crc(bad[1:74]+bad[76:]).to_bytes(2,'little');bp=bytearray(payload);bp[slot*96:(slot+1)*96]=bad
   header=bytearray(pageheader);header[39:41]=arena.crc(bp).to_bytes(2,'little');header[37:39]=arena.crc(header,(3,37,38)).to_bytes(2,'little')
   for at in range(0,used,128):transfer(page*4096+64+at,bp[at:at+128])
   transfer(page*4096,header);seeded=f.reu();reset();r=start()
   for _ in range(10000):
    assert not f.m.read(F+4),tag
    f.put('se_overlay_frame',1,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1)
    if r.p&1:break
   assert r.p&1 and r.a==0xc2,(tag,r.a);assert not f.get('se_doc_read_locks',1) and f.reu()==seeded
   for at in range(0,used,128):transfer(page*4096+64+at,payload[at:at+128])
   transfer(page*4096,pageheader);assert f.reu()==stable_reu
  faults.append('rechecksummed CR ABI/reserved/nonzeroINLINE+NIL fail before READY')
  reset();until_ready();service(35,1,3)
  for _ in range(1000):
   service(35,1,1)
   if f.m.read(F+4)==2:break
  assert f.m.read(F+4)==2
  service(35,1,2);assert not f.get('se_doc_read_locks',1);no_mutation()
  faults.append('heldINLINE cancel releases own lease and never mutates published arena')
  reset();until_ready();at=s['se_reu_epoch'];old=f.read(at,2);f.m.load(at,((int.from_bytes(old,'little')+1)&65535).to_bytes(2,'little'))
  f.put('se_overlay_frame',1,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1);assert r.p&1 and r.a==0x18,(r.a,r.p) # overlay asset epoch refuses before query executes
  assert f.m.read(F+1) and f.get('se_doc_read_locks',1)==1 # stale epoch must not release anything
  f.m.load(at,old);service(35,1,2);assert not f.get('se_doc_read_locks',1);no_mutation()
  faults.append('changed provider epoch fails closed and does not release stale capability')
  # Check transport CRC before records; then independently rechecksum payload
  # to exercise INLINE schema instead of merely failing its page checksum.
  reset();inline_ref=record[40:44];ipage=inline_ref[0];islot=inline_ref[1]
  ih=transfer(ipage*4096,length=64);iu=int.from_bytes(ih[21:23],'little');ip=b''.join(transfer(ipage*4096+64+at,length=min(128,iu-at))for at in range(0,iu,128))
  for tag,seal in [('payloadCRC',False),('eventReserved',True),('eventWidth',True)]:
   reset();bad=bytearray(ip)
   bad[islot*10+(2 if tag=='eventWidth'else 9)]^=0x40 if tag=='eventWidth'else 1
   head=bytearray(ih)
   if seal:head[39:41]=arena.crc(bad).to_bytes(2,'little');head[37:39]=arena.crc(head,(3,37,38)).to_bytes(2,'little')
   for at in range(0,iu,128):transfer(ipage*4096+64+at,bad[at:at+128])
   transfer(ipage*4096,head);seeded=f.reu();reset();r=start();seen=[]
   for _ in range(10000):
    f.put('se_overlay_frame',1,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1)
    if r.p&1:break
    if f.m.read(F+4):
     seen.append(f.m.read(F+4));f.put('se_overlay_frame',3,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1)
     if r.p&1:break
   assert r.p&1 and r.a==0xc2,(tag,r.a,seen)
   assert 2 not in seen and not f.get('se_doc_read_locks',1) and f.reu()==seeded
   for at in range(0,iu,128):transfer(ipage*4096+64+at,ip[at:at+128])
   transfer(ipage*4096,ih);assert f.reu()==stable_reu
  faults.append('INLINE payloadCRC/rechecksummed reserved/width reject before event publication')
  if editor:
   # Competing BEGIN must preserve a live query byte for byte, including its
   # active claim, held packet and independently owned source lease.
   reset();until_ready();assert f.m.read(seam['se_bc_flags'])==9
   active_frame=f.read(F,576);service(35,1,0,0xc3);assert f.read(F,576)==active_frame
   service(35,1,2);assert f.m.read(seam['se_bc_flags'])==1
   reset();until_ready();f.put('se_bc_flags',11,1);service(35,1,1,0xc1)
   assert f.m.read(seam['se_bc_flags'])==3 # preserve preexisting LOST/ARMED
   faults.append('editorACTIVE competingBEGIN opaque and cleanup preserves ARMED/LOST')
   reset();until_ready();assert f.m.read(F+173+8)==1 and f.get('se_doc_read_locks',1)==1
   catalog=s['se_overlay_ids'];capacity=s['se_overlay_capacity']
   for i in range(capacity):
    if f.m.read(catalog+i)==35 and f.m.read(s['image_slot']+i)&1:f.m.write(catalog+i,255);break
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(s['se_overlay_call'],a=35,x=1);assert r.p&1 and r.a==0x17
   assert f.m.read(seam['se_bc_flags'])==9 and f.get('se_doc_read_locks',1)==1
   # This explicit cold test adapter executes the root fallback contract with
   # the actual resident epoch/token-safe END. No unavailable C image needed.
   cleanup=out/'outer-cleanup.s';cleanup.write_text('.setcpu "6502"\n.segment "CODE"\n.export cleanup\ncleanup:lda $'+format(s['se_f_owner'],'04x')+'\n cmp #4\n bne done\n lda $'+format(seam['se_bc_flags'],'04x')+'\n and #8\n beq done\n ldy #85\ncopy:lda $8DAD,y\n sta $'+format(s['se_fs_state'],'04x')+',y\n dey\n bpl copy\n jsr $'+format(s['se_fs_end'],'04x')+'\n lda $'+format(seam['se_bc_flags'],'04x')+'\n and #$f7\n sta $'+format(seam['se_bc_flags'],'04x')+'\n lda #0\n sta $8d01\n sta $8d03\n sta $8d04\n sta $8db4\n sta $8db5\ndone:clc\n rts\n')
   command('ca65','-o',out/'outer-cleanup.o',cleanup);(out/'outer-cleanup.cfg').write_text('MEMORY { C:file=%O,start=$0800,size=$100; } SEGMENTS { CODE:load=C,type=ro; }');command('ld65','-C',out/'outer-cleanup.cfg','-o',out/'outer-cleanup.bin',out/'outer-cleanup.o')
   f.m.load(0x800,(out/'outer-cleanup.bin').read_bytes());f.put('se_f_owner',1,1);opaque=f.read(F,576);r,n=f.fast_call(0x800);assert not r.p&1 and f.read(F,576)==opaque and f.get('se_doc_read_locks',1)==1 and f.m.read(seam['se_bc_flags'])==9
   f.put('se_f_owner',4,1);r,n=f.fast_call(0x800);assert not r.p&1
   assert f.m.read(seam['se_bc_flags'])==1 and not f.get('se_doc_read_locks',1) and not f.m.read(F+1)
   # A second cleanup is harmless; the foreign-owner call above was opaque.
   r,n=f.fast_call(0x800);assert not r.p&1 and not f.get('se_doc_read_locks',1);no_mutation()
   faults.append('unavailableouterC35 saved86at8DAD actualresidentEND cleanup retains ARMED')
  print('QUERY FAULT PASS',faults,flush=True)
  result=dict(status='PASS',editor_active=editor,bytes=len(query)-36,cases=cases,faults=faults,query_calls=query_calls,whole_RAM_guards=ram_guards,parser_entries=0,source_callbacks='onlyactualR14BEGIN0/GUARD1; noREAD/parserfeed/otherCworker',scope='Private actual C query with R14 fullsnapshot guard, actual producer/writer baseline, no renderer/editor hit integration');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--editor-active',action='store_true');a=p.parse_args();out=ROOT/'build/cache-query'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.editor_active)
