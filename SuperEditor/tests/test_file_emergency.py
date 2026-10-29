"""C8 emergency cleanup against a frozen actual editor/object/history fixture.
No VICE, no shared build. Only CLRCHN/CLOSE are mocked for the cleanup itself.
"""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
OUT=ROOT/'build/editor-file/emergency';OUT.mkdir(parents=True,exist_ok=True)
BASE=OUT/'frozen';(BASE/'build/overlays').mkdir(parents=True,exist_ok=True)
report=json.loads((ROOT/'build/editor-report.json').read_text())
from cpu_editor import NAMES
asset_names=list(NAMES)
assert max(seg['end'] for seg in report['segments'] if seg['name']=='BSS') < 0xC5E0, 'test owner slot now occupied'
for name in ['editor.prg','editor-report.json']:
 shutil.copyfile(ROOT/'build'/name,BASE/'build'/name)
for name in asset_names:shutil.copyfile(ROOT/f'build/overlays/{name}.seo',BASE/f'build/overlays/{name}.seo')
import editor_fixture,cpu_editor
editor_fixture.ROOT=BASE;cpu_editor.ROOT=BASE
editor_fixture.NAMES=asset_names;cpu_editor.NAMES=asset_names
from editor_fixture import EditorFixture
def run(args):return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True).stdout
def names(kind,obj):return set(re.findall(r'Name:\s*"([^"\n]+)"',run(['od65','--dump-'+kind,str(obj)])))
def build(modules,stem,external):
 objects=[]
 for i,path in enumerate(modules):
  obj=OUT/f'{stem}-{i}.o';run(['ca65','-g','-D','SE_FILE_UNION=1','-I','src','-o',str(obj),path]);objects.append(obj)
 imports=set();exports=set()
 for obj in objects:imports|=names('imports',obj);exports|=names('exports',obj)
 text=[]
 for name in sorted(imports-exports):
  assert name in external,name
  text += [f'.export {name}',f'{name} = ${external[name]:04X}']
 p=OUT/f'{stem}-bindings.s';p.write_text('\n'.join(text)+'\n');o=p.with_suffix('.o');run(['ca65','-o',str(o),str(p)]);objects.append(o)
 run(['ld65','-C','src/editor_file/test.cfg','-o',str(OUT/f'{stem}.bin'),'-Ln',str(OUT/f'{stem}.lbl'),'-m',str(OUT/f'{stem}.map'),*map(str,objects)])
 symbols={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/f'{stem}.lbl').read_text())}
 return (OUT/f'{stem}.bin').read_bytes(),symbols
coordinator,cs=build(['src/editor_file/state.s','src/editor_file/dialog-state.s','src/editor_file/preflight-state.s','src/editor_file/coordinator.s','src/editor_file/open.s','src/editor_file/save.s','src/editor_file/dialog.s','src/overlays/fileio-ui.s','src/fileio/state.s','src/fileio/save.s'],'coordinator',report['symbols'])
emergency,es=build(['src/overlays/file-emergency.s'],'emergency',{**report['symbols'],**cs})
class Case:
 def __init__(self):
  self.f=EditorFixture();self.f.source(b'OLD CANONICAL\r',banks=1);self.f.s={**self.f.s,**cs,**es};self.s=self.f.s
  self.f.m.load(0x8D00,bytes(1152));self.put('se_f_owner',1);self.data=b'NEW BYTES\r'*100;self.position=0;self.closed=[];self.rom=[]
 def get(self,n,w=1):return self.f.get(n,w)
 def put(self,n,v,w=1):self.f.put(n,v,w)
 def rd(self,n,w):return self.f.read(self.s[n],w)
 def call(self,n,a=0):self.f.m.load(0x6000,coordinator);return self.f.call(n,a)
 def begin(self):
  self.put('se_f_operation',1);self.put('se_f_device',8);self.f.m.load(self.s['se_f_name'],b'DOC');self.put('se_f_name_len',3)
  assert not self.call('se_file_begin').p&1
 def action(self,op):
  if op==0xC0:
   for name in ['se_io_mode','se_io_done','se_io_eof','se_io_owned_temp','se_io_owned_backup']:self.put(name,0)
  elif op in [0xC1,0xC2]:self.put('se_f_preflight_length',len(self.data),3);self.put('se_f_preflight_result',0)
  elif op==0xC3:self.put('se_io_mode',1)
  elif op==0xC4:
   part=self.data[self.position:self.position+256];self.f.m.load(0x8000,part);self.position+=len(part);self.put('se_io_done',len(part),2);self.put('se_io_eof',0x40 if self.position==len(self.data) else 0)
  elif op in [0xC7,0xCC]:self.put('se_io_mode',0)
  elif op==0xE1:
   regs=self.f.call('se_history_call',1);assert not regs.p&1
  else:raise AssertionError(hex(op))
  self.put('se_f_request',0);self.put('se_f_result',0);self.put('se_f_carry',0)
 def step(self):
  request=self.get('se_f_request')
  if request:self.action(request)
  return self.call('se_file_step')
 def until(self,predicate):
  for _ in range(100):
   if predicate():return
   self.step()
  raise AssertionError('phase not reached')
 def cleanup(self,name='se_file_emergency'):
  m=self.f.m;m.load(0x6000,emergency)
  for name,value in [('pc',self.s[name]),('a',0),('x',0),('y',0),('sp',0xFD),('p',0x24)]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
  m.write(0x1FE,0xFE);m.write(0x1FF,0x02)
  for _ in range(100000):
   regs=m.regs()
   if regs.pc==0x02FF:break
   if regs.pc in [0xFFCC,0xFFC3]:
    self.rom.append(regs.pc)
    if regs.pc==0xFFC3:self.closed.append(regs.a)
    ret=(m.read(0x100+((regs.sp+1)&255))|(m.read(0x100+((regs.sp+2)&255))<<8))+1
    for name,value in [('pc',ret),('sp',(regs.sp+2)&255)]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
   else:
    assert regs.pc<0xFF80,hex(regs.pc)
    m.lib.zeropage_peddle_step_instruction(m.handle)
  else:raise AssertionError('cleanup unbounded')
  assert self.f.read(0xC600,1024)==self.f.shim
  return m.regs()
 def close(self):self.f.close()
cases=[]
for phase in ['allocated','reading','before-history','failed-history','acknowledged-history','already-published']:
 c=Case()
 try:
  old=c.f.document();oldtokens=c.rd('se_doc_meta',15);oldhistory=c.rd('se_h_current',4);c.begin()
  if phase=='allocated':c.until(lambda:c.get('se_f_allocated')==2 and c.get('se_f_request')==0xC3)
  elif phase=='reading':c.until(lambda:c.get('se_f_position',3)>0 and c.get('se_f_request')==0xC4)
  else:
   c.until(lambda:c.get('se_f_request')==0xE1)
   if phase=='failed-history':c.put('se_f_request',0);c.put('se_f_carry',1);c.put('se_f_result',0x53)
   if phase in ['acknowledged-history','already-published']:
    c.action(0xE1)
    if phase=='already-published':assert not c.call('se_file_step').p&1
  candidate=c.rd('se_f_candidate',10);regs=c.cleanup();assert regs.p&1 and regs.a==0x9B and c.get('se_f_owner')==1
  assert c.get('se_io_mode')==0 and c.get('se_f_allocated')==0 and c.get('se_f_phase')==0
  if phase in ['acknowledged-history','already-published']:
   assert c.f.document()==c.data and c.get('se_f_committed')==2
   assert c.rd('se_h_original',5)==c.rd('se_doc_original',5)
   for at in [0,5]:
    c.f.m.load(c.s['se_object_id'],oldtokens[at:at+5]);assert c.f.call('se_object_validate').p&1
  else:
   assert c.f.document()==old and c.rd('se_doc_meta',15)==oldtokens and c.rd('se_h_current',4)==oldhistory
   for at in [0,5]:
    c.f.m.load(c.s['se_object_id'],candidate[at:at+5]);assert c.f.call('se_object_validate').p&1
  # Borrowed append remains valid in every outcome.
  c.f.m.load(c.s['se_object_id'],c.rd('se_doc_append',5));assert not c.f.call('se_object_validate').p&1
  cases.append(phase+' safe source/history/token cleanup')
 finally:c.close()
for scenario in ['normal','stale-frame','provider-reset','invalid-lease-count']:
 c=Case()
 try:
  c.put('se_f_operation',2);c.put('se_f_epoch',c.get('se_doc_epoch',2),2)
  assert not c.f.call('se_doc_read_acquire').p&1;c.put('se_f_lease',1)
  c.put('se_io_mode',2);c.put('se_f_preflight_phase',3);c.put('se_io_owned_temp',1);c.put('se_io_owned_backup',1)
  c.f.m.load(c.s['se_io_temp_name'],b'EXACT OWNED TEMP');c.f.m.load(c.s['se_io_backup_name'],b'EXACT BACKUP')
  capabilities=c.rd('se_io_temp_name',16)+c.rd('se_io_backup_name',16)
  oldsource=c.f.document()
  if scenario=='stale-frame':c.put('se_f_epoch',c.get('se_f_epoch',2)+1,2)
  if scenario=='provider-reset':c.put('se_reu_epoch',c.get('se_reu_epoch',2)+1,2)
  if scenario=='invalid-lease-count':c.put('se_doc_read_locks',0)
  locks=c.get('se_doc_read_locks');regs=c.cleanup();assert regs.a==0x9B and regs.p&1 and c.closed==[5,7]
  assert c.get('se_io_owned_temp')==1 and c.get('se_io_owned_backup')==1
  assert c.rd('se_io_temp_name',16)+c.rd('se_io_backup_name',16)==capabilities
  assert c.get('se_doc_read_locks')==(0 if scenario=='normal' else locks)
  assert c.get('se_f_lease')==(0 if scenario=='normal' else 1)
  assert c.get('se_f_owner')==1 and c.get('se_io_mode')==0 and c.get('se_f_preflight_phase')==0
  if scenario!='provider-reset':assert c.f.document()==oldsource
  cases.append(scenario+' epoch-ownedlease/channel/capability preservation')
 finally:c.close()
# A complete provider/object/document reset may reuse token IDs and lock bytes.
# Stale old-frame capabilities must never free/restore/decrement this new source.
c=Case()
try:
 c.begin();c.until(lambda:c.get('se_f_request')==0xE1);oldframe=c.f.read(0x8D00,1152)
 for name,a in [('se_reu_provider_init',0),('se_object_init',0),('se_doc_init',1)]:assert not c.f.call(name,a).p&1
 fresh=b'FRESH EPOCH DOCUMENT';token=c.rd('se_doc_original',5);c.f.m.load(c.s['se_object_id'],token);c.f.m.load(0x8000,fresh)
 c.put('se_object_offset',0,3);c.put('se_object_length',len(fresh),2);c.put('se_object_c64',0x8000,2);assert not c.f.call('se_object_copy').p&1
 c.put('se_doc_source_length',len(fresh),3);assert not c.f.call('se_doc_adopt_original').p&1
 assert not c.f.call('se_doc_read_acquire').p&1
 canonical=c.rd('se_doc_roots',278+256);newtokens=c.rd('se_doc_meta',15);c.f.m.load(0x8D00,oldframe)
 c.put('se_f_operation',2);c.put('se_f_lease',1);c.put('se_io_mode',1);regs=c.cleanup()
 assert regs.a==0x9B and c.get('se_doc_read_locks')==1 and c.rd('se_doc_roots',278+256)==canonical
 assert c.rd('se_doc_meta',15)==newtokens and c.f.document()==fresh and c.get('se_f_allocated')==2 and c.get('se_f_lease')==1
 cases.append('actualnewprovider/documentepoch untouched bystale oldframe')
finally:c.close()
# A successful H_INIT acknowledgement cannot authorize rollback if its current
# history context is subsequently inconsistent: retain new source and all queues.
c=Case()
try:
 c.begin();c.until(lambda:c.get('se_f_request')==0xE1);c.action(0xE1)
 c.put('se_h_generation',c.get('se_h_generation',2)+1,2);newcanonical=c.rd('se_doc_meta',15)
 regs=c.cleanup();assert regs.a==0x9B and c.f.document()==c.data and c.rd('se_doc_meta',15)==newcanonical
 assert c.get('se_f_committed')==1 and c.get('se_f_allocated')==2 and c.get('se_f_phase')==6
 cases.append('inconsistentacknowledgedhistory retainsnewcanonical/queue')
finally:c.close()
# No file owner: no KERNAL/channel/source/frame write.
c=Case()
try:
 c.put('se_f_owner',0);before=c.f.read(0x8D00,1152);regs=c.cleanup();assert not regs.p&1 and regs.a==0 and not c.rom and c.f.read(0x8D00,1152)==before;cases.append('owner0 no-op')
finally:c.close()
# AUX recovery keys do not depend on an available C12 image.
for key,owned,expected in [(3,0,2),(3,1,0x9B),(ord('K'),1,2),(ord('k'),1,2),(ord('Z'),1,0)]:
 c=Case()
 try:
  c.put('se_f_epoch',c.get('se_doc_epoch',2),2);c.put('se_e_ui',3);c.put('se_f_error',0x9B)
  c.put('se_io_owned_temp',owned);c.put('se_io_owned_backup',owned);c.f.m.load(c.s['se_io_temp_name'],b'KEEP EXACT TEMP!!');c.f.m.load(c.s['se_io_backup_name'],b'KEEP EXACT BACKUP')
  private=c.rd('se_io_temp_name',16)+c.rd('se_io_backup_name',16);source=c.f.document()
  c.put('se_e_key',key);regs=c.cleanup('se_file_recovery_key');assert regs.a==expected and bool(regs.p&1)==(expected==0x9B)
  assert not c.rom and c.f.document()==source and c.rd('se_io_temp_name',16)+c.rd('se_io_backup_name',16)==private
  if expected==2:assert c.get('se_f_owner')==0 and c.get('se_e_ui')==0 and c.get('se_io_owned_temp')==0 and c.get('se_io_owned_backup')==0
  else:assert c.get('se_f_owner')==1 and c.get('se_io_owned_temp')==owned and c.get('se_io_owned_backup')==owned
  cases.append(f'recoverykey{key} caps{owned} result{expected} noDOS')
 finally:c.close()
for field in ['se_f_phase','se_f_request','se_f_preflight_phase','se_io_mode','se_f_allocated','se_f_lease','se_f_epoch']:
 c=Case()
 try:
  c.put('se_f_epoch',c.get('se_doc_epoch',2),2);c.put('se_e_ui',3);c.put('se_io_owned_temp',1);c.put(field,2 if field=='se_f_epoch' else 1);c.put('se_e_key',ord('K'))
  regs=c.cleanup('se_file_recovery_key');assert regs.a==0x9B and regs.p&1 and c.get('se_f_owner')==1 and c.get('se_io_owned_temp')==1 and not c.rom
  # Help is still available under the same source-safety refusal.
  c.put('se_e_key',0x8B);c.put('se_f_ui_help',0);regs=c.cleanup('se_file_recovery_key');assert regs.a==0 and not regs.p&1 and c.get('se_f_ui_help')==1 and c.get('se_f_owner')==1
  cases.append(field+' blocks recoveryclose but permitsF6')
 finally:c.close()
result=dict(schema=1,resident_sha256=report['sha256'],emergency_bytes=len(emergency),emergency_sha256=hashlib.sha256(emergency).hexdigest(),coordinator_bytes=len(coordinator),union_bytes=cs['__FILESTATE_SIZE__'],cases=cases)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
