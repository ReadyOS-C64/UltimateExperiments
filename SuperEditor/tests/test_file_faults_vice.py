"""Disposable-D81 native M4 faults. Default/--describe/--prepare never launch VICE.

Run only after the parent's explicit exclusive-window grant. Real device9 absence,
real D81 capacity and VICE3.10 attach read-only resource are separate from clearly
labeled debugger injections (catalog deletion / post-service status corruption).
Bounded-service stubs invoke the actual root pump, while cancellation bytes enter
through the harness's native IRQ keyboard path. No document bytes are debug-poked.
"""
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from d81_image import D81Image,D81Error,File
from vice_config import PROJECT,step
from vice_plan import run_plan
from redraw_model import native_text
sys.path.insert(0,str(ROOT/'tests'))
from test_editor_file_vice import NativePlan

BASE=native_text('# Native fault baseline\rMixed case, clipboard and savepoint survive.\r10 PRINT "SAFE"\r')*16
OPENED=native_text('Another document; exact staged source\r')*1900
CASES={
 'cancel-candidate-scan': 'IRQ-native STOP during phase41 with actual raw LF7 open; no temp CREATE and whole disk unchanged',
 'candidate-seq': 'Real closed SEQ owns generated native temp name; no W-open or disk mutation',
 'candidate-prg': 'Real closed PRG owns generated native temp name; no W-open or disk mutation',
 'candidate-splat': 'Real unclosed/splat SEQ owns generated native temp name; no W-open or disk mutation',
 'native-a0-retry': 'Native A0 filename rejected before IO; retry valid SaveAs preserves source and marks verified save',
 'native-at16': 'Exact16-byte literal @ native filename opens without DOS replacement semantics',
 'missing-device': 'Actual disabled device9, native F3/Open and STOP; disk8 unchanged',
 'write-protected': 'Actual VICE3.10 AttachDevice8d0Readonly resource; save refused, source/savepoint unchanged',
 'disk-full': 'Actual closed filler SEQ occupies all but one data sector; write/close fails on native1581',
 'cancel-read': 'IRQ-native STOP after first256-byte OPEN packet, actual bounded root job9 pump',
 'cancel-write': 'IRQ-native STOP after first256-byte SAVE packet, actual bounded root job9 pump',
 'promotion-refused': 'Actual PRG name collision missed by SEQ-only preflight; DOS rename refuses overwrite',
 'backup-collision': 'Actual existing exact backup name; DOS rename refuses it and owned temp is cleaned',
 'close-status-injected': 'DEBUGGER INJECTION: replace completed real CLOSE result with definite DOS72 before coordinator observes it',
 'promotion-ack-injected': 'DEBUGGER INJECTION: actual target→backup and temp→target completed; corrupt promotion acknowledgement to IO92, keep backup via nativeK',
 'missing-c12-open': 'DEBUGGER INJECTION: remove C12 catalog ID after actual H_INIT acknowledgement; AUX completes publication and root resets caret/view',
 'missing-c12-saved-ack9': 'DEBUGGER INJECTION: C12 missing after actual H_SAVED SaveAs device9 acknowledgement; new bound name/device and savepoint must survive',
 'missing-c12-savepoint-pending9': 'DEBUGGER INJECTION: force resident C12 admission before queued H_SAVED action; device9 verified file exists but old bound name/savepoint must remain',
 'missing-c12-save': 'DEBUGGER INJECTION: remove C12 catalog ID during actual owned write; AUX closes/relinquishes epoch-owned lease, nativeK retains exact temp',
 'missing-both-read': 'DEBUGGER INJECTION: remove C12+AUX while actual LF5 open; resident fallback closes only owned channel, retains source/candidates',
 'missing-both-preflight': 'DEBUGGER INJECTION: remove C12+AUX while actual LF7 raw preflight open; resident fallback closes only owned channel',
 'missing-both-stale-lease': 'DEBUGGER INJECTION: stale frameepoch plus C12+AUX missing during SAVE; fallback closes LF5 and retains lease/capabilities without guessed source mutation',
}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fixture_data():return {b'FBASE':BASE,b'FOPEN':OPENED,b'FCOLLIDE':b'\x01\x08ORIGINAL PRG COLLISION',b'FUNCHANGED':native_text('Unrelated exact chain\r')}
def free_blocks(image):
 total=0
 for track in range(1,81):
  bam=image.sector(40,1 if track<=40 else 2);at=16+((track-1)%40)*6;count=bam[at];bits=sum(bin(x).count('1') for x in bam[at+1:at+6]);assert count==bits,(track,count,bits)
  if track!=40:total+=count
 return total

def raw_file(image,name):
 # Independent observation of an allocated foreign splat chain. Unlike normal
 # document reads, this oracle deliberately does not require the closed flag.
 entry=next(x for x in image.entries() if x.name==name);pos=entry.first;seen=set();sectors=[];output=bytearray()
 assert pos[0],(name,'missing allocated first sector')
 while pos[0]:
  assert pos not in seen and pos[0]!=40,(name,'cyclic/directory chain');seen.add(pos);block=image.sector(*pos);sectors.append((*pos,block))
  if block[0]:output.extend(block[2:])
  else:assert block[1],(name,'invalid terminal');output.extend(block[2:block[1]+1])
  pos=tuple(block[:2])
 assert len(sectors)==entry.blocks,(name,'block count mismatch')
 return File(entry,bytes(output),tuple(sectors))

def freeze(product_freeze):
 assert product_freeze,'--freeze requires --product-freeze pointing at the root immutable build/source archive'
 product_freeze=product_freeze.resolve();build=product_freeze/'build';source_archive=product_freeze/'sources.zip'
 metadata=json.loads((product_freeze/'freeze.json').read_text());names=metadata['names'];assert 'fileio' in names and 'aux' in names
 e=ROOT/'agentsworking/evidence/M4'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-file-fault-native');e.mkdir(parents=True)
 for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','supereditor.d81','disk-manifest.json']:shutil.copyfile(build/name,e/name)
 r=json.loads((e/'editor-report.json').read_text());assert digest(e/'editor.prg')==r['sha256']==metadata['prg_sha256'];disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
 for name in names:
  data=(build/f'overlays/{name}.seo').read_bytes();assert data[20:36]==data[36:52]==bytes.fromhex(r['resident_binding']['digest']);assert disk.read(name.upper().encode(),kind=1).data==data;assert hashlib.sha256(data).hexdigest()==metadata['assets'][name];(e/(name+'.seo')).write_bytes(data)
 for name in ['tests/test_file_faults_vice.py','tests/test_editor_file_vice.py','tools/d81_image.py','tools/vice_plan.py','tools/vice_config.py']:
  dest=e/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
 shutil.copyfile(source_archive,e/'product-sources.zip')
 provenance=dict(authoritative_product_freeze=str(product_freeze),source_archive=str(source_archive),source_sha256=digest(source_archive),note='Product sources copied unchanged from immutable root build. Harness sources frozen separately; live checkout sources intentionally not archived.')
 (e/'source-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 (e/'freeze.json').write_text(json.dumps(dict(prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],catalog=names,asset_sha256={n:digest(e/(n+'.seo')) for n in names},sources=provenance),indent=2)+'\n')
 print(e);return e

def package(e,case):
 out=e/case;out.mkdir(exist_ok=True);disk=out/'working.d81';assert not disk.exists(),'Use a fresh freeze/case, do not overwrite retained evidence';shutil.copyfile(e/'supereditor.d81',disk)
 cmd=['c1541','-attach',str(disk)]
 for name,data in fixture_data().items():
  p=out/(name.decode()+'.bin');p.write_bytes(data);kind='p' if name==b'FCOLLIDE' else 's';cmd+=['-write',str(p),name.decode().lower()+','+kind]
 if case.startswith('candidate-') or case=='native-at16':
  p=out/'foreign.bin';p.write_bytes(BASE if case=='native-at16' else b'FOREIGN CANDIDATE: EXACT CHAIN MUST SURVIVE');kind='p' if case=='candidate-prg' else 's';cmd+=['-write',str(p),'foreignnative,'+kind]
 if case=='backup-collision':
  p=out/'unowned-backup.bin';p.write_bytes(b'UNRELATED EXACT BACKUP NAME');cmd+=['-write',str(p),'foreignbackup,s']
 result=subprocess.run(cmd+['-list'],capture_output=True,text=True,errors='replace');(out/'package.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stdout+result.stderr
 if case=='backup-collision':
  raw=bytearray(disk.read_bytes());entry=next(x for x in D81Image(raw).entries() if x.name==b'FOREIGNBACKUP');at=((entry.directory_sector[0]-1)*40+entry.directory_sector[1])*256+entry.slot*32+5;raw[at:at+16]=b'SE~B000000000000';disk.write_bytes(raw)
 if case.startswith('candidate-') or case=='native-at16':
  raw=bytearray(disk.read_bytes());entry=next(x for x in D81Image(raw).entries() if x.name==b'FOREIGNNATIVE');at=((entry.directory_sector[0]-1)*40+entry.directory_sector[1])*256+entry.slot*32;raw[at+5:at+21]=b'@LITERAL12345678' if case=='native-at16' else b'SE~T000000000000'
  if case=='candidate-splat':raw[at+2]=1
  disk.write_bytes(raw)
 image=D81Image(disk.read_bytes())
 if case.startswith('candidate-'):assert raw_file(image,b'SE~T000000000000').data==b'FOREIGN CANDIDATE: EXACT CHAIN MUST SURVIVE'
 if case=='native-at16':assert image.read(b'@LITERAL12345678').data==BASE
 if case=='backup-collision':assert image.read(b'SE~B000000000000',kind=1).data==b'UNRELATED EXACT BACKUP NAME'
 for name,data in fixture_data().items():assert image.read(name,kind=2 if name==b'FCOLLIDE' else 1).data==data
 if case=='disk-full':
  free=free_blocks(image);assert free>2
  p=out/'filler.bin';p.write_bytes(bytes([0x55])*((free-1)*254))
  result=subprocess.run(['c1541','-attach',str(disk),'-write',str(p),'ffiller,s','-list'],capture_output=True,text=True,errors='replace');(out/'fill.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stdout+result.stderr
  image=D81Image(disk.read_bytes());assert len(image.read(b'FFILLER',kind=1).sectors)==free-1 and free_blocks(image)==1
 if case in ['missing-c12-saved-ack9','missing-c12-savepoint-pending9']:
  result=subprocess.run(['c1541','-format','faultnine,fn','d81',str(out/'working9.d81')],capture_output=True,text=True);assert result.returncode==0;shutil.copyfile(out/'working9.d81',out/'initial9.d81')
 shutil.copyfile(disk,out/'initial.d81');(out/'package.json').write_text(json.dumps(dict(case=case,initial_sha256=digest(disk),free_data_blocks=free_blocks(image),files={x.name.decode('latin1'):dict(kind=x.kind,blocks=x.blocks) for x in image.entries()}),indent=2)+'\n')
 return out

class FaultPlan(NativePlan):
 def __init__(self,e,case,r):
  # Base plan utility is reused read-only; each fault has an independent emulator.
  super().__init__(e,case,r);self.case=case;self.observations=[];self.controlled=False;self.injections=[];self.source=BASE;self.caret=2
 def memory(self,ident,name,value,width=1):
  super().memory(ident,name,value,width);self.steps[-1]['retry']=dict(max_attempts=200,backoff_ms=50,jitter=False)
 def write(self,ident,name,value,width=1):
  address=self.s[name] if isinstance(name,str) else name;data=value if isinstance(value,bytes) else value.to_bytes(width,'little');self.steps.append(step(ident,'memory.write',start=address,bytes_hex=data.hex(' ')))
 def queue(self,ident,data):
  self.steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.01,post_delay_s=0.15));self.keys+=len(data)
 def stub(self,ident,body,*,a=0,x=0):
  # Executable stubs occupy discarded cold memory0E00 only after startup. Main
  # is parked after a real foreground API; IRQ capture remains enabled.
  source='.setcpu "6502"\n.segment "CODE"\n.export stop\n'+body+'\nstop:\n nop\n jmp stop\n'
  p=self.out/(ident+'.s');p.write_text(source);cfg=self.out/'stub.cfg';cfg.write_text('MEMORY { S:file=%O,start=$0E00,size=$E0,type=ro; }\nSEGMENTS { CODE:load=S,type=ro; }\n')
  subprocess.run(['ca65','-o',str(p.with_suffix('.o')),str(p)],check=True,capture_output=True,text=True)
  subprocess.run(['ld65','-C',str(cfg),'-o',str(p.with_suffix('.bin')),'-Ln',str(p.with_suffix('.lbl')),str(p.with_suffix('.o'))],check=True,capture_output=True,text=True)
  stop=int(re.search(r'al ([0-9A-Fa-f]+) \.stop',p.with_suffix('.lbl').read_text())[1],16);data=p.with_suffix('.bin').read_bytes()
  self.raw(ident,[f'> 0e00 {data.hex(" ")}',f'registers PC=$0e00, SP=$ff, FL=$20, A=${a:02x}, X=${x:02x}',f'until ${stop:04x}']);self.controlled=True
 def api(self,ident,name,a=0,x=0):
  self.stub(ident,f' jsr ${self.s[name]:04X}\n sta $0EE0\n lda #0\n adc #0\n sta $0EE1',a=a,x=x)
 def hold(self,ident):self.stub(ident,' nop')
 def event(self,ident):
  self.stub(ident,f' jsr ${self.s["se_input_get"]:04X}\n jsr ${self.s["se_editor_latch_event"]:04X}\n jsr ${self.s["se_editor_input"]:04X}')
  self.memory(ident+'_native_byte_consumed','se_key_sequence',self.keys,2)
 def wait_request(self,ident,request,*,after_packet=False,phase=None):
  lines=['loop:',f' jsr ${self.s["se_editor_service"]:04X}',f' lda ${self.s["se_e_job"]:04X}',' beq stop',f' lda ${self.s["se_f_request"]:04X}',f' cmp #${request:02X}',' bne loop']
  if phase is not None:lines += [f' lda ${self.s["se_f_phase"]:04X}',f' cmp #${phase:02X}',' bne loop']
  if after_packet:lines += [f' lda ${self.s["se_f_position"]:04X}',f' ora ${self.s["se_f_position"]+1:04X}',f' ora ${self.s["se_f_position"]+2:04X}',' beq loop']
  self.stub(ident,'\n'.join(lines));self.memory(ident+'_request','se_f_request',request)
 def drain(self,ident):self.stub(ident,'loop:\n jsr $%04X\n lda $%04X\n bne loop'%(self.s['se_editor_service'],self.s['se_e_job']));self.memory(ident+'_job0','se_e_job',0)
 def resume(self,ident):self.raw(ident,[f'registers PC=${self.s["se_idle"]:04x}']);self.controlled=False
 def snapshot(self,ident,*,expected=None,unchanged=True,error=None,ui=3,owner=1,locks=0,caps=None,caret=None,current=None,device=8,saved_ack=False):
  if expected is None:expected=self.source
  if caret==2:caret=self.caret
  if self.controlled and ui==3 and not self.case.startswith('missing-both'):
   self.api(ident+'_actual_root_modal_paint','se_editor_render')
   self.memory(ident+'_modal_paint_carry',0x0EE1,0)
  self.memory(ident+'_source_length','se_doc_length',len(expected),3);self.memory(ident+'_shim',0xC600,self.canary);self.memory(ident+'_channels',0x98,0)
  if current is None:current=b'FBASE'
  self.memory(ident+'_current_len','se_f_current_len',len(current));self.memory(ident+'_current_name','se_f_current_name',current);self.memory(ident+'_current_device','se_f_current_device',device)
  self.memory(ident+'_owner','se_f_owner',owner);self.memory(ident+'_ui','se_e_ui',ui);self.memory(ident+'_locks','se_doc_read_locks',locks)
  if error is not None:self.memory(ident+'_root_error','se_e_error',error)
  if caps is not None:
   self.memory(ident+'_tempcap','se_io_owned_temp',caps[0]);self.memory(ident+'_backupcap','se_io_owned_backup',caps[1])
  self.steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{self.out}/native-{ident}.png" 2'))
  self.steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='ram',start=0,end=0xCFFF),dict(label='colors',start=0xD800,end=0xDBE7)]))
  self.steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
  self.observations.append(dict(id=ident,expected=expected.hex(),unchanged=unchanged,error=error,ui=ui,owner=owner,locks=locks,caps=caps,caret=caret,current=current.hex(),device=device,saved_ack=saved_ack))
 def setup(self):
  self.boot();self.open('baseline_open',b'FBASE')
  # Populate an independent private clipboard and retain a marked selection.
  self.send('clipboard_copy',bytes([0x89,0x1D,0x1D,0x88])+b'COPY\r',owner=0)
  save_cases={'cancel-candidate-scan','candidate-seq','candidate-prg','candidate-splat','native-a0-retry','write-protected','disk-full','cancel-write','promotion-refused','backup-collision','close-status-injected','promotion-ack-injected','missing-c12-save','missing-both-stale-lease','missing-c12-saved-ack9','missing-c12-savepoint-pending9'}
  if self.case in save_cases:
   self.send('unmark_before_native_edit',bytes([3]),owner=0)
   self.send('native_unsaved_edit_and_flush',bytes([0xD8,0x1D]),owner=0)
   self.source=BASE[:2]+bytes([0xD8])+BASE[2:];self.caret=4
  self.snapshot('before',ui=0,owner=0,error=0,caret=self.caret)
 def save_name(self,target=b'FNEW'):
  self.modal('save_dialog','A');self.send('save_native_name',bytes([0x14])*16+target,ui=3,owner=1)
 def open_name(self,target=b'FOPEN'):
  self.modal('open_dialog','O');self.send('open_native_name',bytes([0x14])*16+target,ui=3,owner=1)
 def accept_held(self):
  self.hold('park_before_accept');self.queue('queued_native_Return',b'\r');self.event('accept_one_native_event');self.memory('accept_job9','se_e_job',9)
 def lose(self,*names):
  catalog=json.loads((self.e/'freeze.json').read_text())['catalog']
  for name in names:self.write('remove_catalog_'+name,self.s['se_overlay_ids']+catalog.index(name),0)
  self.write('force_C_readmission',self.s['se_overlay_active']+1,0)
  self.injections.append(dict(kind='catalog-ID deletion',assets=names,source_and_REU_bytes_untouched=True))
 def result_failure(self,ident,error,dos=None):
  self.write(ident+'_error','se_f_result',error);self.write(ident+'_carry','se_f_carry',1)
  if dos is not None:self.write(ident+'_dos','se_io_dos_code',dos)
  self.injections.append(dict(kind='replace completed service acknowledgement',error=error,dos=dos))
 def plan(self):
  plan=super().plan();plan['plan_id']='file-fault-'+self.e.name+'-'+self.case;plan['global_defaults']['vice']['disk8']=str(self.out/'working.d81')
  if self.case in ['missing-c12-saved-ack9','missing-c12-savepoint-pending9']:plan['global_defaults']['vice'].update(drive9_enabled=True,drive9_type=1581,disk9=str(self.out/'working9.d81'))
  return plan

def scenario(e,case,r):
 n=FaultPlan(e,case,r);n.setup()
 if case=='cancel-candidate-scan':
  n.save_name();n.accept_held();n.wait_request('candidate_scan_LF7_open',0xC2,phase=41)
  n.memory('actual_raw_channel7_open',0x98,1);n.memory('raw_scan_active','se_f_preflight_phase',1);n.memory('no_temp_CREATE','se_io_owned_temp',0);n.memory('epoch_owned_read_lease','se_f_lease',1)
  n.queue('actual_IRQ_STOP_during_candidate_scan',bytes([3]));n.drain('root_cancel_raw_preflight');n.memory('STOP_consumed','se_key_sequence',n.keys,2)
  n.resume('resume_after_scan_cancel');n.idle('scan_cancel_redrawn',ui=0,error=0,owner=0);n.snapshot('cancelled',ui=0,owner=0,error=0,caret=2)
 elif case.startswith('candidate-'):
  n.save_name();n.send('accept_occupied_temp_save',b'\r',ui=3,owner=1);n.memory('occupied_DOS63','se_f_dos_error',63);n.memory('occupied_fio93','se_f_error',0x93)
  n.snapshot('refused',error=0,caret=2,caps=(0,0));n.send('close_refused',bytes([3]),owner=0);n.snapshot('closed',ui=0,owner=0,error=0,caret=2)
 elif case=='native-a0-retry':
  n.save_name(b'F\xA0BAD');n.send('reject_A0_accept',b'\r',ui=3,owner=1);n.memory('invalid_native_name90','se_f_error',0x90);n.snapshot('refused',error=0,caret=2,caps=(0,0))
  n.name('safe_retry_name',b'FSAFE');n.snapshot('saved',ui=0,owner=0,error=0,caret=2,current=b'FSAFE',saved_ack=True)
 elif case=='native-at16':
  n.open('literal_at16_open',b'@LITERAL12345678');n.snapshot('opened',expected=BASE,unchanged=False,ui=0,owner=0,error=0,caret=0,current=b'@LITERAL12345678')
 elif case=='missing-device':
  n.modal('open_drive_dialog','O');n.send('actual_missing_device9',bytes([0x86]),ui=3,owner=1);n.memory('device9','se_f_device',9)
  n.name('missing_drive_accept',b'FOPEN',ui=3,owner=1);n.memory('missing_drive_io92','se_f_error',0x92)
  n.snapshot('failed',error=0,caret=2,caps=(0,0));n.send('cancel_missing_drive',bytes([3]),owner=0);n.snapshot('closed',ui=0,owner=0,error=0,caret=2)
 elif case in ['write-protected','disk-full','promotion-refused','backup-collision']:
  if case=='write-protected':n.raw('actual_attach_write_protection',['resourceset "AttachDevice8d0Readonly" "1"','resourceget "AttachDevice8d0Readonly"'])
  target=b'FCOLLIDE' if case=='promotion-refused' else b'FBASE' if case=='backup-collision' else b'FNEW'
  n.save_name(target);n.send('accept_save',b'\r',ui=3,owner=1)
  if case=='write-protected':
   n.memory('actual_protect_DOS26','se_f_dos_error',26);n.memory('protect_fio93','se_f_error',0x93)
  elif case=='disk-full':
   n.memory('full_readst_timeout2','se_f_raw_error',2);n.memory('full_recovery9B','se_f_error',0x9B);n.memory('full_owned_temp','se_io_owned_temp',1)
  else:n.memory('real_DOS_name_collision63','se_f_dos_error',63);n.memory('collision_fio93','se_f_error',0x93)
  n.snapshot('failed',error=0,caret=2)
  n.send('keep_or_close',b'K\x03' if case=='disk-full' else bytes([3]),owner=0,error=0)
  n.snapshot('closed',ui=0,owner=0,error=0,caret=2)
 elif case in ['cancel-read','cancel-write']:
  if case=='cancel-read':n.open_name();request=0xC4
  else:n.save_name();request=0xC6
  n.accept_held();n.wait_request('after_first_packet',request,after_packet=True)
  n.queue('actual_IRQ_STOP_during_job',bytes([3]));n.drain('actual_root_poll_and_owned_cancel');n.memory('STOP_consumed','se_key_sequence',n.keys,2)
  n.resume('resume_after_cancel');n.idle('cancelled_redrawn',ui=0,error=0,owner=0)
  n.snapshot('cancelled',ui=0,owner=0,error=0,caret=2)
 elif case=='close-status-injected':
  n.save_name();n.accept_held();n.wait_request('native_close_pending',0xC7,phase=31)
  n.api('real_ROM_close','se_editor_service');n.memory('real_close_consumed','se_f_request',0);n.memory('real_close_channels',0x98,0)
  n.result_failure('inject_definite_DOS72',0x93,72);n.drain('coordinator_refuses_close');n.memory('close_result93','se_f_error',0x93)
  n.snapshot('failed',error=0,caret=2,caps=(0,0));n.resume('resume_after_close_fault');n.send('close_modal',bytes([3]),owner=0)
 elif case=='promotion-ack-injected':
  n.save_name(b'FBASE');n.accept_held();n.wait_request('promotion_pending',0xC8,phase=31)
  n.api('real_ROM_promote','se_editor_service');n.memory('promote_request_consumed','se_f_request',0);n.memory('real_promote_temp_consumed','se_io_owned_temp',0);n.memory('backup_owned','se_io_owned_backup',1)
  n.result_failure('inject_lost_promotion_ack',0x92);n.drain('uncertain_recovery');n.memory('recovery9B','se_f_error',0x9B)
  n.snapshot('failed',error=0,caret=2,caps=(0,1));n.resume('resume_recovery');n.send('explicit_native_keep_files',b'K',owner=0);n.snapshot('kept',ui=0,owner=0,error=0,caret=2)
 elif case=='missing-c12-open':
  n.open_name();n.accept_held();n.wait_request('H_INIT_pending',0xE1)
  n.api('real_H_INIT_ack','se_editor_service');n.memory('H_INIT_consumed','se_f_request',0);n.memory('H_INIT_success','se_f_carry',0)
  n.lose('fileio');n.drain('root_admission_failure_publication');n.memory('recovery','se_f_error',0x9B)
  n.snapshot('failed',expected=OPENED,unchanged=False,error=0x17,caret=0,caps=(0,0),current=b'FOPEN');n.resume('resume_recovery');n.send('safe_native_STOP',bytes([3]),owner=0);n.snapshot('closed',expected=OPENED,unchanged=False,ui=0,owner=0,error=0,caret=0,current=b'FOPEN')
 elif case in ['missing-c12-saved-ack9','missing-c12-savepoint-pending9']:
  n.save_name(b'FSAVED9');n.send('actual_SaveAs_device9',bytes([0x86]),ui=3,owner=1);n.memory('save_device9','se_f_device',9)
  n.accept_held();n.wait_request('H_SAVED_pending',0xE8)
  if case=='missing-c12-saved-ack9':
   n.api('actual_H_SAVED_ack','se_editor_service');n.memory('H_SAVED_ack_carry','se_f_carry',0);n.memory('H_SAVED_consumed','se_f_request',0)
  n.lose('fileio')
  if case=='missing-c12-savepoint-pending9':
   # This is an explicit wrapper-admission boundary fixture, not the ordinary
   # pump's action order (which would consume pendingE8 before enteringC12).
   n.api('injected_early_C12_wrapper_admission','se_editor_file_call',a=2);n.injections.append(dict(kind='forced resident C12 admission while H_SAVED request is still pending'))
  n.drain('root_savepoint_admission_failure');n.memory('savepoint_recovery','se_f_error',0x9B)
  ack=case=='missing-c12-saved-ack9';bound=b'FSAVED9' if ack else b'FBASE';drive=9 if ack else 8
  n.snapshot('failed',error=0x17,caret=2,caps=(0,0),current=bound,device=drive,saved_ack=ack)
  n.resume('resume_savepoint_recovery');n.send('safe_STOP_savepoint',bytes([3]),owner=0)
  n.snapshot('closed',ui=0,owner=0,error=0,caret=2,current=bound,device=drive,saved_ack=ack)
 elif case in ['missing-c12-save','missing-both-read','missing-both-preflight','missing-both-stale-lease']:
  if case in ['missing-c12-save','missing-both-stale-lease']:n.save_name();request=0xC6
  else:n.open_name();request=0xC2 if case=='missing-both-preflight' else 0xC4
  n.accept_held();n.wait_request('owned_IO_boundary',request,after_packet=request!=0xC2)
  # Consume one actual IO slice, then C12 is the next image needed. No state
  # branch is fabricated; only admission/epoch faults below are injected.
  n.api('real_IO_consumed','se_editor_service');n.memory('request_consumed','se_f_request',0)
  if case=='missing-both-stale-lease':n.write('inject_stale_frame_epoch','se_f_epoch',0,2);n.injections.append(dict(kind='stale file frame epoch',value=0))
  n.lose('fileio',*(['aux'] if case.startswith('missing-both') else []));n.drain('root_missing_overlay_failure')
  locks=1 if case=='missing-both-stale-lease' else 0;caps=(1,0) if case in ['missing-c12-save','missing-both-stale-lease'] else (0,0)
  n.snapshot('failed',error=0x17,caret=2,locks=locks,caps=caps)
  if case=='missing-c12-save':
   n.resume('resume_recovery');n.send('native_keep_temp',b'K',owner=0);n.snapshot('kept',ui=0,owner=0,error=0,caret=2)
  # Both-missing cases intentionally end with owner/phase/lease retained. No
  # claim that the app can finish cleanup with neither required image admitted.
 else:raise AssertionError(case)
 return n

# Decode actual REU piece-table bytes without invoking a potentially damaged app.
def decode_source(ram,reu,s):
 def v(name,width=1):return int.from_bytes(ram[s[name]:s[name]+width],'little')
 def obj(identity,offset,length):
  output=bytearray()
  while length:
   count=min(length,65536-(offset&65535));bank=ram[s['object_extents']+identity*16+(offset>>16)];output+=reu[bank*65536+(offset&65535):bank*65536+(offset&65535)+count];offset+=count;length-=count
  return bytes(output)
 result=bytearray();root=s['se_doc_roots']
 for i in range(v('se_doc_root_count')):
  item=ram[root+i*8:root+(i+1)*8];leaf=obj(v('se_doc_meta'),item[0]*1024,item[1]*16)
  for j in range(item[1]):
   p=leaf[j*16:(j+1)*16];identity=p[0];assert int.from_bytes(p[1:3],'little')==ram[s['object_gen_lo']+identity]+256*ram[s['object_gen_hi']+identity]
   result+=obj(identity,int.from_bytes(p[3:6],'little'),int.from_bytes(p[6:9],'little'))
 assert len(result)==v('se_doc_length',3)
 return bytes(result),obj

def evaluate(n,artifacts,manifest):
 images={}
 for p in (artifacts/'dumps').glob('*.json'):
  for chunk in json.loads(p.read_text(encoding='utf-8-sig')).get('chunks',[]):
   if chunk.get('source')=='vice_native_reu_image':images[p.name.removeprefix('reu_').removesuffix('_reu_index.json')]=(p.parent/Path(chunk['file']).name).read_bytes()
 baseline=None;observed=[]
 for item in n.observations:
  ident=item['id'];ram=(artifacts/'stages'/(ident+'_ram')/'ram.bin').read_bytes();reu=images[ident];assert len(ram)==0xD000 and len(reu)==1024*1024
  def val(name,width=1):return int.from_bytes(ram[n.s[name]:n.s[name]+width],'little')
  source,obj=decode_source(ram,reu,n.s);assert source==bytes.fromhex(item['expected']),(ident,'source mismatch')
  assert ram[0xC600:0xCA00]==n.canary and ram[0x98]==0
  # Cursor/selection and clipboard objects are independent from file staging.
  clip=ram[n.s['se_clip_token']:n.s['se_clip_token']+5];clipdata=obj(clip[0],0,val('se_clip_length',3)) if val('se_clip_active') else b''
  history={name:ram[n.s[name]:n.s[name]+width].hex() for name,width in [('se_h_token',5),('se_h_generation',2),('se_h_original',5),('se_h_append',5),('se_h_end',2),('se_h_cursor',2),('se_h_current',4),('se_h_saved',4),('se_h_counter',4),('se_h_dirty',1)]}
  canonical=ram[n.s['se_doc_roots']:n.s['se_doc_roots']+256]+ram[n.s['se_doc_ready']:n.s['se_doc_ready']+22]
  selection=(val('se_hot_caret',3),val('se_sel_mark'),val('se_sel_anchor',3));clipboard=(clip.hex(),clipdata.hex(),val('se_clip_length',3),val('se_clip_generation',2))
  if baseline is None:baseline=dict(history=history,canonical=canonical,selection=selection,clipboard=clipboard)
  else:
   assert clipboard==baseline['clipboard'],(ident,'clipboard changed')
   if item['unchanged']:
    expected_history=dict(baseline['history'])
    if item['saved_ack']:expected_history.update(se_h_saved=baseline['history']['se_h_current'],se_h_dirty='00')
    assert history==expected_history and canonical==baseline['canonical'] and selection==baseline['selection'],(ident,'source/history/savepoint/selection changed')
   else:assert val('se_hot_caret',3)==0 and val('se_sel_mark')==0 and val('se_h_current',4)==val('se_h_saved',4)
  if item['caret'] is not None:assert val('se_hot_caret',3)==item['caret']
  observed.append(dict(id=ident,source_bytes=len(source),source_sha256=hashlib.sha256(source).hexdigest(),root_error=val('se_e_error'),file_error=val('se_f_error') if val('se_f_owner') else None,dos=val('se_f_dos_error') if val('se_f_owner') else None,owner=val('se_f_owner'),lease=val('se_f_lease') if val('se_f_owner') else None,history=history,clipboard_bytes=len(clipdata)))
 before=D81Image((n.out/'initial.d81').read_bytes());after=D81Image((n.out/'working.d81').read_bytes());changed_target=n.case=='promotion-ack-injected'
 for entry in before.entries():
  if changed_target and entry.name==b'FBASE':assert after.read(b'FBASE',kind=1).data==n.source;continue
  first,last=raw_file(before,entry.name),raw_file(after,entry.name);assert first.entry.raw[2:]==last.entry.raw[2:] and first.data==last.data and first.sectors==last.sectors,(n.case,'unrelated original chain changed',entry.name)
 names={entry.name for entry in after.entries()};extra=names-{entry.name for entry in before.entries()}
 allowed={b'SE~T000000000000',b'SE~B000000000000'}|({b'FSAFE'} if n.case=='native-a0-retry' else set());assert extra<=allowed,(n.case,extra)
 extras=[]
 for name in sorted(extra):
  entry=next(x for x in after.entries() if x.name==name);record=dict(name=name.decode('ascii'),closed=entry.closed,blocks=entry.blocks)
  try:
   candidate=after.read(name);record.update(bytes=len(candidate.data),sha256=hashlib.sha256(candidate.data).hexdigest(),first32_hex=candidate.data[:32].hex(),sector_chain=[(t,sec) for t,sec,_ in candidate.sectors])
  except D81Error as error:record['unreadable_candidate']=str(error)
  extras.append(record)
 if n.case=='native-a0-retry':assert after.read(b'FSAFE',kind=1).data==n.source and extra=={b'FSAFE'}
 if n.case=='disk-full':assert free_blocks(before)==1 and free_blocks(after)==0 and extra=={b'SE~T000000000000'}
 if n.case=='promotion-ack-injected':assert after.read(b'SE~B000000000000',kind=1).data==BASE
 if n.case in ['missing-c12-saved-ack9','missing-c12-savepoint-pending9']:
  nine=D81Image((n.out/'working9.d81').read_bytes());assert nine.read(b'FSAVED9',kind=1).data==n.source and {x.name for x in nine.entries()}=={b'FSAVED9'}
 if n.case.startswith('candidate-') or n.case in ['missing-device','write-protected','native-at16','cancel-candidate-scan']:assert (n.out/'working.d81').read_bytes()==(n.out/'initial.d81').read_bytes()
 if n.case in ['cancel-read','cancel-write','cancel-candidate-scan','promotion-refused','backup-collision','close-status-injected']:assert not extra,(n.case,'uncollected owned temp',extra)
 result=dict(status='passed',executed_test_sha256=digest(Path(__file__)),case=n.case,coverage=CASES[n.case],evidence=str(n.out),manifest=str(manifest),resident_sha256=n.r['sha256'],injections=n.injections,observations=observed,extra_exact_native_names=[name.decode('ascii') for name in sorted(extra)],extra_artifacts=extras,raw_disk_sha256=digest(n.out/'working.d81'),shim_bytes=1024,channels_closed=True,limitations='Native ROM IEC/root pump with IRQ keyboard bytes; no physical keyboard or power-loss claim. Monitor stubs control bounded phase scheduling; catalog/status/epoch changes are explicitly debugger-injected, never physical disk failures. Screenshots need visual review.')
 (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--describe',action='store_true');p.add_argument('--freeze',action='store_true');p.add_argument('--product-freeze',type=Path);p.add_argument('--prepare',type=Path);p.add_argument('--run',type=Path);p.add_argument('--case',choices=list(CASES),action='append');a=p.parse_args()
 if a.describe or not(a.freeze or a.prepare or a.run):print(json.dumps(dict(cases=CASES,requirements='Explicit exclusive VICE grant for --run; final stable build for freeze/prepare',official_resource_reference='https://vice-emu.sourceforge.io/vice_6.html#SEC117',monitor_reference='https://vice-emu.sourceforge.io/vice_12.html'),indent=2));return
 if a.freeze:freeze(a.product_freeze);return
 e=(a.prepare or a.run).resolve()
 if a.run:assert (e/'sources/tests/test_file_faults_vice.py').read_bytes()==Path(__file__).read_bytes(), 'Freeze the executed test revision into a fresh evidence directory'
 r=json.loads((e/'editor-report.json').read_text());assert digest(e/'editor.prg')==r['sha256']
 for case in a.case or list(CASES):
  if not(e/case/'initial.d81').exists():package(e,case)
  n=scenario(e,case,r);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'observations.json').write_text(json.dumps(n.observations,indent=2)+'\n')
  print(f'Prepared {case}: {len(n.steps)} steps at {n.out}',flush=True)
  if a.run:
   b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);(n.out/'harness-build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
   artifacts,manifest=run_plan(plan,n.out);evaluate(n,artifacts,manifest)
if __name__=='__main__':main()
