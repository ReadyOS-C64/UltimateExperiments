"""Actual C12 coordinator with real resident document/object/history services.
Transport is modeled at its explicit resident action boundary; no native IEC claim.
Owned isolated outputs only; the current resident/overlay images are never rebuilt.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
OUT=ROOT/'build/editor-file';OUT.mkdir(exist_ok=True)
def run(args):return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True).stdout
def names(kind,obj):return set(re.findall(r'Name:\s*"([^"\n]+)"',run(['od65','--dump-'+kind,str(obj)])))
# C12 test links real provider frames and real policy, while raw-sector state only
# supplies the preflight-result API. The host's model returns frozen lengths/EOF.
modules=['src/editor_file/dialog.s','src/editor_file/dialog-state.s','src/editor_file/state.s','src/editor_file/preflight-state.s','src/editor_file/coordinator.s','src/editor_file/open.s','src/editor_file/save.s','src/overlays/fileio-ui.s','src/fileio/state.s','src/fileio/save.s']
objects=[]
for i,p in enumerate(modules):
 obj=OUT/f'test-{i}.o';run(['ca65','-g','-D','SE_FILE_UNION=1','-I','src','-o',str(obj),p]);objects.append(obj)
r=json.loads((ROOT/'build/editor-report.json').read_text());imports=set();exports=set()
for obj in objects:imports|=names('imports',obj);exports|=names('exports',obj)
bind=['; Frozen actual editor resident imports; test-only BSS address $C5E0.']
for n in sorted(imports-exports):
 assert n in r['symbols'],n
 bind += [f'.export {n}',f'{n} = ${r["symbols"][n]:04X}']
(OUT/'bindings.s').write_text('\n'.join(bind)+'\n');run(['ca65','-o',str(OUT/'bindings.o'),str(OUT/'bindings.s')]);objects.append(OUT/'bindings.o')
run(['ld65','-C','src/editor_file/test.cfg','-o',str(OUT/'coordinator.bin'),'-Ln',str(OUT/'coordinator.lbl'),'-m',str(OUT/'coordinator.map'),*map(str,objects)])
s={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/'coordinator.lbl').read_text())};image=(OUT/'coordinator.bin').read_bytes()
assert len(image)<=4096
class Case:
 def __init__(self,old=b'OLD\r',physical=256):
  self.f=EditorFixture();self.f.source(old,banks=max(1,(len(old)+65535)//65536),physical=physical);self.s={**self.f.s,**s};self.f.s=self.s
  self.fs={};self.channel=None;self.diskpos=0;self.steps=0;self.log=[];self.fail=None;self.corrupt=False
  self.f.m.load(0x8D00,bytes(1152));self.f.put('se_f_owner',1,1);self.f.put('se_f_phase',0,1)
 def get(self,n,w=1):return self.f.get(n,w)
 def put(self,n,v,w=1):self.f.put(n,v,w)
 def rd(self,n,w):return self.f.read(self.s[n],w)
 def call(self,n,a=0):
  self.f.m.load(0x6000,image);return self.f.call(n,a)
 def begin(self,op,name=b'DOC'):
  self.f.m.load(self.s['se_f_name'],name.ljust(16,b' '));self.put('se_f_name_len',len(name));self.put('se_f_device',8);self.put('se_f_operation',op)
  x=self.call('se_file_begin');assert not x.p&1,(x.a,op)
 def name(self,other=False):
  n='se_io_other' if other else 'se_io_name';return self.rd(n,self.get(n+'_len'))
 def action(self,op):
  self.log.append(op);err=0;result=0
  if self.fail and (failure:=self.fail(self,op)):err=0x92 if failure is True else failure
  elif op==0xC0:
   for n in ('se_io_mode','se_io_owned_temp','se_io_owned_backup','se_io_eof','se_io_done','se_io_done+1'):
    if '+' in n:self.f.m.write(self.s['se_io_done']+1,0)
    else:self.put(n,0)
  elif op in (0xC1,0xC2,0xD2):
   name=self.name();self.put('se_f_preflight_phase',0)
   if name not in self.fs:err=0x93;self.put('se_io_dos_code',62)
   else:
    self.put('se_f_preflight_length',len(self.fs[name]),3);self.put('se_f_preflight_result',int(not self.fs[name]))
  elif op==0xC3:
   self.channel=self.name();self.diskpos=0;self.put('se_io_mode',1);self.put('se_io_eof',0x40 if not self.fs[self.channel] else 0)
  elif op==0xC4:
   data=self.fs[self.channel];n=self.get('se_io_count') or 256;part=data[self.diskpos:self.diskpos+n]
   if self.corrupt and part:part=bytes([part[0]^1])+part[1:]
   self.f.m.load(0x8000,part);self.diskpos+=len(part);self.put('se_io_done',len(part),2);self.put('se_io_eof',0x40 if self.diskpos==len(data) else 0)
  elif op==0xC5:
   name=self.name()
   if name in self.fs:err=0x93;self.put('se_io_dos_code',63)
   else:self.fs[name]=b'';self.channel=name;self.put('se_io_mode',2);self.put('se_io_owned_temp',1);self.temp=name
  elif op==0xC6:
   n=self.get('se_io_count') or 256;self.fs[self.channel]+=self.f.read(0x8000,n);self.put('se_io_done',n,2);self.put('se_io_wrote',1)
  elif op in (0xC7,0xCC,0xCD):self.channel=None;self.put('se_io_mode',0)
  elif op in (0xC8,0xC9):
   name,dest=self.name(),self.name(True)
   if dest in self.fs:err=0x93;self.put('se_io_dos_code',63)
   else:
    self.fs[dest]=self.fs.pop(name)
    if op==0xC9:self.backup=dest;self.put('se_io_owned_backup',1)
    elif name==getattr(self,'temp',None):self.put('se_io_owned_temp',0)
    elif name==getattr(self,'backup',None):self.put('se_io_owned_backup',0)
  elif op==0xCA:self.fs.pop(self.temp);self.put('se_io_owned_temp',0)
  elif op==0xCB:self.fs.pop(self.backup);self.put('se_io_owned_backup',0)
  elif op==0xCE:
   self.entries=sorted(self.fs);self.entry=0;self.put('se_io_mode',3)
  elif op==0xCF:
   if self.entry<len(self.entries):
    name=self.entries[self.entry];self.entry+=1;self.f.m.load(self.s['se_io_dir_name'],name.ljust(16,b' '));self.put('se_io_dir_len',len(name))
   else:self.put('se_io_dir_len',0)
  elif op==0xD1:self.put('se_f_preflight_phase',0)
  elif op in (0xE1,0xE8):
   regs=self.f.call('se_history_call',1 if op==0xE1 else 8);err=regs.a if regs.p&1 else 0
  else:raise AssertionError(hex(op))
  self.put('se_f_result',err or result);self.put('se_f_carry',bool(err));self.put('se_f_request',0)
 def step(self):
  request=self.get('se_f_request')
  if request:self.action(request)
  regs=self.call('se_file_step');self.steps+=1
  assert self.steps<20000,(self.get('se_f_phase'),self.get('se_sv_phase'),self.log[-8:])
  return regs
 def finish(self):
  while self.get('se_f_phase'):regs=self.step()
  assert self.f.read(0xC600,1024)==self.f.shim
  assert self.get('se_doc_read_locks')==0
  return self.get('se_f_error')
 def close(self):self.f.close()
cases=[]
def case(name,fn):
 c=Case()
 try:fn(c);cases.append(name)
 finally:c.close()
for n in [0,1,128,255,256,257,2048,65536,65537]:
 def opened(c,n=n):
  data=bytes((i*37+11)&255 for i in range(n));c.fs[b'DOC']=data;c.begin(1);assert c.finish()==0;assert c.f.document()==data
  assert c.get('se_f_committed')==2;assert c.get('se_h_dirty')==0
 case(f'open {n}',opened)
for n in [0,1,255,256,257,2048,65537]:
 for exists in [False,True]:
  c=Case(bytes((i*13+3)&255 for i in range(n)))
  try:
   if exists:c.fs[b'DOC']=b'original disk bytes'
   old=c.f.document();c.begin(2);assert c.finish()==0,(n,exists,c.log[-20:]);assert c.fs=={b'DOC':old},(n,exists,c.fs.keys());assert c.f.document()==old;assert c.get('se_h_dirty')==0;cases.append(f'save {n} overwrite{exists}')
  finally:c.close()
# Failed allocation must retain canonical bytes and history; no partial publication.
c=Case(b'KEEP',physical=8)
try:
 c.fs[b'DOC']=b'X'*200000;old=c.f.document();hist=c.rd('se_h_current',4);c.begin(1);assert c.finish()==0x99;assert c.f.document()==old;assert c.rd('se_h_current',4)==hist;cases.append('allocation refusal preserves old document')
finally:c.close()
# Cancellation between chunks and failed H_INIT admission both restore old roots.
for mode in ['cancel','historyfail','readfail']:
 c=Case(b'OLD SOURCE\r')
 try:
  c.fs[b'DOC']=b'new'*500;c.begin(1);old=c.f.document();hist=c.rd('se_h_current',4)
  while True:
   if mode=='cancel' and c.get('se_f_phase')==4 and c.get('se_f_position',3)>0:c.put('se_f_cancel',1);break
   if mode=='historyfail' and c.get('se_f_request')==0xE1:
    c.put('se_f_result',0x51);c.put('se_f_carry',1);c.put('se_f_request',0);break
   if mode=='readfail' and c.get('se_f_request')==0xC4:c.fail=lambda c,op:op==0xC4;break
   c.step()
  c.finish();assert c.f.document()==old;assert c.rd('se_h_current',4)==hist;cases.append(mode+' preserves source/history')
 finally:c.close()
# Definite refusals/corruption never mark the source saved or replace original.
for failure in ['temp-collision','readback-mismatch','promotion-refused','uncertain-write','cancel-created','cancel-writing']:
 c=Case(b'NEW CONTENT'*80)
 try:
  c.fs[b'DOC']=b'ORIGINAL DISK';c.put('se_h_saved',0,4)
  old=c.f.document();saved=c.rd('se_h_saved',4)
  if failure=='temp-collision':c.fs[b'SE~T000000000000']=b'NOT OURS'
  if failure=='readback-mismatch':c.corrupt=True
  if failure=='promotion-refused':c.fail=lambda c,op:0x93 if op==0xC8 and c.name()==getattr(c,'temp',None) else 0
  if failure=='uncertain-write':c.fail=lambda c,op:op==0xC6
  c.begin(2)
  if failure.startswith('cancel-'):
   while True:
    if failure=='cancel-created' and c.get('se_f_request')==0xC5:
     c.action(0xC5);c.put('se_f_cancel',1);break
    if failure=='cancel-writing' and c.get('se_f_request')==0xC6:
     c.action(0xC6);c.put('se_f_cancel',1);break
    c.step()
  err=c.finish();assert err,(failure,c.log)
  assert c.f.document()==old and c.rd('se_h_saved',4)==saved
  assert c.fs[b'DOC']==b'ORIGINAL DISK',(failure,c.fs.keys())
  assert 0xE8 not in c.log
  if failure not in ['uncertain-write']:
   assert c.get('se_io_owned_temp')==0 and c.get('se_io_owned_backup')==0,(failure,c.log)
  else:assert c.get('se_io_owned_temp')==1 and err==0x9B
  assert c.get('se_io_mode')==0
  cases.append(failure+' preserves disk/source/savepoint')
 finally:c.close()
# Actual512KiB profile can stage a small new document via borrowedappend.
for boundary in [0xC1,0xD2]:
 c=Case(b'UNSAVED SOURCE')
 try:
  c.begin(3)
  while c.get('se_f_request')!=boundary:c.step()
  c.action(boundary);assert c.get('se_io_dos_code')==62 and c.get('se_f_carry')==1
  c.put('se_f_cancel',1)
  assert c.finish()==0x9C
  assert 0xC5 not in c.log and 0xE8 not in c.log and not c.fs
  assert c.f.document()==b'UNSAVED SOURCE' and c.get('se_io_owned_temp')==0
  cases.append('STOP after missing acknowledgement '+hex(boundary)+' cannot authorize create')
 finally:c.close()
# Actual512KiB profile can stage a small new document via borrowedappend.
c=Case(b'OLD',physical=8)
try:
 c.fs[b'DOC']=b'512K OPEN WORKS';c.begin(1);assert c.finish()==0;assert c.f.document()==b'512K OPEN WORKS';cases.append('512KiB twoobject staging successful')
finally:c.close()
# Native dialog operation is bounded, preserves document rows and modal F6 state.
c=Case()
try:
 c.f.m.load(0x4000,bytes([0x55])*1000);c.f.m.load(0xD800,bytes([6])*1000)
 c.f.m.load(c.s['se_f_name'],b'Mixed Native');c.put('se_f_name_len',12);c.put('se_f_device',8);c.put('se_f_ui_help',0)
 before=c.f.read(0x4000,960);c.call('se_file_ui_draw');assert c.f.read(0x4000,960)==before
 assert c.f.m.read(0x43D9)==0x38
 for _ in range(10):c.put('se_e_key',ord('A'));c.call('se_file_ui_key')
 assert c.get('se_f_name_len')==16
 c.put('se_e_key',0x86);c.call('se_file_ui_key');assert c.get('se_f_device')==9
 c.put('se_e_key',0x8B);c.call('se_file_ui_key');assert c.get('se_f_ui_help')==1
 c.call('se_file_ui_draw');assert c.f.read(0x4000,960)==before
 c.put('se_e_key',3);assert c.call('se_file_ui_key').a==2
 cases.append('native16B device8/9 modalF6 bottomrow guard')
finally:c.close()
# Dialog executes the same request protocol, with real history/save/open behind it.
def dstart(c,command):
 c.put('se_f_owner',0);c.f.m.write(c.s['se_overlay_frame']+1,command)
 regs=c.call('se_file_dialog');assert not regs.p&1,(command,regs.a)
 return regs
def ddrain(c):
 for _ in range(30000):
  request=c.get('se_f_request')
  if request:c.action(request)
  regs=c.call('se_file_dialog_step')
  assert not regs.p&1,('dialog',hex(regs.a))
  if regs.a==0:return c.call('se_file_dialog_finish')
 raise AssertionError('dialog did not settle')
def dkey(c,key):c.put('se_e_key',key);return c.call('se_file_dialog_key')
c=Case()
try:
 c.fs={f'FILE{i:02}'.encode():b'x' for i in range(21)}
 dstart(c,80);ddrain(c);assert c.get('se_e_ui')==3 and c.get('se_f_owner')==1, {n:c.get(n) for n in ['se_e_ui','se_f_owner','se_fd_command','se_fd_task','se_f_phase','se_f_error','se_fd_list_count']}
 assert c.get('se_fd_list_count')==8 and c.rd('se_fd_list_names',6)==b'FILE00'
 dkey(c,0x87);ddrain(c);assert c.get('se_fd_page',2)==1 and c.rd('se_fd_list_names',6)==b'FILE08'
 dkey(c,0x91);assert c.rd('se_f_name',6)==b'FILE08'
 dkey(c,0x11);assert c.rd('se_f_name',6)==b'FILE09'
 dkey(c,0x86);ddrain(c);assert c.get('se_f_device')==9 and c.get('se_fd_page',2)==0
 dkey(c,0x8B);assert c.get('se_f_ui_help')==1 and c.get('se_f_owner')==1
 assert dkey(c,3).a==2 and c.get('se_f_owner')==0 and c.get('se_e_ui')==0
 cases.append('dialog8row paging/selection/device/F6/cancel unionownership')
finally:c.close()
for choice in [ord('D'),ord('S'),ord('C')]:
 c=Case(b'DIRTY SOURCE')
 try:
  c.fs={b'OLD':b'OLD DISK',b'NEXT':b'OPENED NEXT'};c.f.m.load(c.s['se_f_current_name'],b'OLD'.ljust(16,b' '));c.put('se_f_current_len',3);c.put('se_f_current_device',8);c.put('se_h_dirty',1)
  dstart(c,80);ddrain(c);c.f.m.load(c.s['se_f_name'],b'NEXT'.ljust(16,b' '));c.put('se_f_name_len',4)
  assert dkey(c,13).a==0 and c.get('se_fd_confirm')==1
  regs=dkey(c,choice)
  if choice==ord('C'):assert regs.a==2 and c.f.document()==b'DIRTY SOURCE' and c.get('se_f_owner')==0
  else:
   regs=ddrain(c)
   if choice==ord('S'):
    assert regs.a==1 and c.get('se_fd_resume')==0
    regs=ddrain(c);assert c.fs[b'OLD']==b'DIRTY SOURCE'
   assert regs.a==0 and not regs.p&1 and c.f.document()==b'OPENED NEXT' and c.get('se_f_owner')==0
  cases.append('dirtyOPEN '+chr(choice))
 finally:c.close()
# Unnamed dirty document saves under a new name before resuming the frozen OPEN.
c=Case(b'UNNAMED DIRTY')
try:
 c.fs={b'NEXT':b'NEXT SOURCE'};c.put('se_f_current_len',0);c.put('se_h_dirty',1)
 dstart(c,80);ddrain(c);c.f.m.load(c.s['se_f_name'],b'NEXT'.ljust(16,b' '));c.put('se_f_name_len',4);dkey(c,13)
 assert dkey(c,ord('S')).a==1;ddrain(c);assert c.get('se_fd_resume')==1 and c.get('se_f_operation')==3
 c.f.m.load(c.s['se_f_name'],b'SAVED'.ljust(16,b' '));c.put('se_f_name_len',5);assert dkey(c,13).a==1
 assert ddrain(c).a==1;assert ddrain(c).a==0
 assert c.fs[b'SAVED']==b'UNNAMED DIRTY' and c.f.document()==b'NEXT SOURCE' and c.get('se_f_owner')==0
 cases.append('dirtyunnamed SaveAsbeforeOPEN preservesrequestedname')
finally:c.close()
# Deferred directory cancellation consumes the issued action, then closes once.
c=Case()
try:
 c.fs={b'DOC':b'X'};dstart(c,80);assert c.get('se_f_request')==0xCE
 assert c.call('se_file_dialog_cancel').a==1
 assert ddrain(c).a==2 and c.get('se_f_owner')==0 and c.get('se_io_mode')==0
 cases.append('directorycancel pendingaction closesand releasesunion')
finally:c.close()
# Recovery ownership never disappears through STOP or a subsequent BEGIN.
c=Case(b'UNSAVED')
try:
 c.fs={b'DOC':b'ORIGINAL'};c.begin(2);c.fail=lambda c,op:op==0xC6;assert c.finish()==0x9B
 assert c.get('se_io_owned_temp')==1
 assert c.call('se_file_dialog_finish').a==0x9B
 c.put('se_e_key',3);regs=c.call('se_file_dialog_key');assert regs.p&1 and regs.a==0x9B and c.get('se_f_owner')==1
 regs=c.call('se_file_begin');assert regs.p&1 and regs.a==0x91 and c.get('se_io_owned_temp')==1
 cases.append('recoverySTOPandBEGIN retainexactownership')
finally:c.close()
# Native PETSCII aliases must exactly use the actual shared screen converter.
c=Case()
try:
 c.put('se_f_name_len',2);c.f.m.load(c.s['se_f_name'],bytes([0xA0,0xFF]));c.put('se_f_ui_help',0)
 expected=bytes(c.f.call('se_petscii_screen',v).a for v in [0xA0,0xFF]);c.call('se_file_ui_draw');assert c.f.read(0x43C6,2)==expected
 cases.append('dialogA0/FF sharedPETSCIIconverter')
finally:c.close()
# Separately link the actual C10 raw transport against the same frame ABI.
c10=[]
for i,p in enumerate(['src/editor_file/preflight.s','src/editor_file/transport.s']+[f'src/fileio/{n}.s' for n in ['channel','chunk','status','directory','commands']]):
 obj=OUT/f'transport-{i}.o';run(['ca65','-g','-I','src','-o',str(obj),p]);c10.append(obj)
imports=set();exports=set()
for obj in c10:imports|=names('imports',obj);exports|=names('exports',obj)
bind=[]
for n in sorted(imports-exports):
 assert n in s,n
 bind += [f'.export {n}',f'{n} = ${s[n]:04X}']
(OUT/'transport-bindings.s').write_text('\n'.join(bind)+'\n');run(['ca65','-o',str(OUT/'transport-bindings.o'),str(OUT/'transport-bindings.s')]);c10.append(OUT/'transport-bindings.o')
run(['ld65','-C','src/editor_file/test.cfg','-o',str(OUT/'transport.bin'),'-Ln',str(OUT/'transport.lbl'),'-m',str(OUT/'transport.map'),*map(str,c10)])
ts={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/'transport.lbl').read_text())};transport=(OUT/'transport.bin').read_bytes()
from fileio_fixture import FileIOFixture
from peddle import Machine
class Raw(FileIOFixture):
 def __init__(self):
  self.s={**s,**ts};self.m=Machine();self.m.load(0x6000,transport)
  self.fs={};self.channels={};self.trace=[];self.selected_in=self.selected_out=None
  self.st=0;self.dos=b'00, OK,00,00\r';self.directory=b'';self.inject={};self.blocks={}
  self.shim=bytes((i*43+17)&255 for i in range(1024));self.m.load(0xC600,self.shim);self.call('se_io_init')
 def raw(self,name,error=None):
  m=self.m
  for k,v in [('pc',self.s[name]),('a',0),('x',0),('y',0),('sp',0xFD),('p',0x24)]:getattr(m.lib,'zeropage_peddle_set_'+k)(m.handle,v)
  m.write(0x1FE,0xFE);m.write(0x1FF,0x02)
  for _ in range(200000):
   if m.regs().pc==0x02FF:break
   if m.regs().pc>=0xFF80:self.rom()
   else:m.lib.zeropage_peddle_step_instruction(m.handle)
  else:raise AssertionError(name)
  regs=m.regs();assert bool(regs.p&1)==(error is not None),(name,regs.a,error)
  if error is not None:assert regs.a==error
  else:assert regs.a in (0,2)
  return regs.a
 def rom(self):
  if self.m.regs().pc==0xFFC0 and self.filename==b'#':
   saved=self.filename;self.filename=b'0:__RAW,S,R';self.fs[b'__RAW']=bytes(256);super().rom();self.filename=saved
  else:super().rom()
 def command(self,cmd):
  if cmd.startswith(b'U1:'):
   ch,drive,t,sec=map(int,cmd[3:].split());assert (ch,drive)==(3,0);self.channels[7]=dict(data=self.blocks[(t,sec)],pos=0);self.dos=b'00, OK,00,00\r'
  else:super().command(cmd)
raw=Raw()
try:
 for n in [0,1,254,255,256,65537]:
  header=bytearray(256);header[:2]=bytes([40,3]);directory=bytearray(256);directory[:2]=bytes([0,255]);directory[2:5]=bytes([0x81,1,0]);directory[5:21]=b'DOC'.ljust(16,b'\xA0')
  raw.blocks={(40,0):bytes(header),(40,3):bytes(directory)};left=n;i=0
  while True:
   t,sec=1+i//40,i%40;take=min(254,left);left-=take;block=bytearray(256)
   block[:2]=bytes([1+(i+1)//40,(i+1)%40]) if left else bytes([0,take+1]);raw.blocks[t,sec]=bytes(block);i+=1
   if not left:break
  raw.name(b'DOC');raw.raw('se_f_preflight_begin');steps=0
  while raw.raw('se_f_preflight_step')==2:steps+=1;assert steps<400
  assert int.from_bytes(raw.read('se_f_preflight_length',3),'little')==n
  assert raw.read('se_f_preflight_result')[0]==int(n==0) and not raw.channels
  cases.append(f'emitted raw-chain length {n}')
 # A repeating sector eventually hits the3200-sector budget, never loops forever.
 raw.blocks[(1,0)]=bytes([1,0])+bytes(254);raw.name(b'DOC');raw.raw('se_f_preflight_begin');raw.raw('se_f_preflight_step');raw.raw('se_f_preflight_step')
 raw.set('se_f_preflight_blocks',(3200).to_bytes(2,'little'));raw.raw('se_f_preflight_step',error=0x94);assert not raw.channels;cases.append('cyclic chain budget closes raw channel')
finally:raw.close()
report=dict(schema=1,resident_sha256=r['sha256'],coordinator_sha256=hashlib.sha256(image).hexdigest(),coordinator_bytes=len(image),transport_bytes=len(transport),union_bytes=s['__FILESTATE_SIZE__'],cases=cases)
(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
