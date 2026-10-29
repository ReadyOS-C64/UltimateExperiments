"""Reduced REU workload with retained FC snapshot and instruction-level allocation peaks.

ROM file operations use the existing explicit CPU filesystem model; no native
IEC/pixel/IRQ claim. Every allocator owner-table store is observed, including
allocations released before an operation completes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,json,subprocess,sys,zipfile,inspect,textwrap
import test_editor_soak as soak
import test_lifecycle_extended as extended
geos=extended.semantic.geos;ROOT=geos.ROOT

def runner(out):
 reference=soak.runner(out);p=out/'runner.cpp';s=p.read_text()
 needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 extra='''
static uint16_t ca_phys=0,ca_objects=0;
static uint64_t ca_peak_banks=0,ca_peak_objects=0,ca_stores=0;
extern "C" void ca_config(uint16_t a,uint16_t b){ca_phys=a;ca_objects=b;ca_peak_banks=ca_peak_objects=ca_stores=0;}
static void ca_sample(ZeroPagePeddle*m){uint64_t b=0,o=0;
 for(int i=0;i<256;i++){auto v=zeropage_peddle_read(m,ca_phys+i);if(v>=2 && v!=255)b++;}
 for(int i=0;i<8;i++)if(zeropage_peddle_read(m,ca_objects+i))o++;
 if(b>ca_peak_banks)ca_peak_banks=b;if(o>ca_peak_objects)ca_peak_objects=o;}
extern "C" void ca_baseline(ZeroPagePeddle*m){ca_sample(m);}
extern "C" uint64_t ca_info(int i){uint64_t v[]={ca_peak_banks,ca_peak_objects,ca_stores};return v[i];}
'''
 assert s.count(needle)==1;s=s.replace(needle,extra+needle+'''
 auto ca_op=zeropage_peddle_read(m,r.pc);uint16_t ca_at=zeropage_peddle_read(m,r.pc+1)|(zeropage_peddle_read(m,r.pc+2)<<8);
 if(ca_op==0x9d)ca_at+=r.x;else if(ca_op==0x99)ca_at+=r.y;
 bool ca_write=ca_phys && (ca_op==0x8d||ca_op==0x9d||ca_op==0x99) &&
 ((ca_at>=ca_phys && ca_at<ca_phys+256)||(ca_at>=ca_objects && ca_at<ca_objects+8));
''',1)
 needle='zeropage_peddle_step_instruction(m);';assert s.count(needle)==1
 s=s.replace(needle,needle+'if(ca_write){ca_stores++;ca_sample(m);}',1)
 # FC is a typed lifecycle capability; source/history/FE permissions stay exact.
 s=s.replace('lo!=0x46 && lo!=0xfe','lo!=0x46 && lo!=0xfe && lo!=0xfc')
 s=s.replace('extern "C" uint64_t gm_run','extern "C" void ca_step(ZeroPagePeddle*m){step(m);}'+'extern "C" uint64_t gm_run',1)
 p.write_text(s);suffix='.dylib'if sys.platform=='darwin'else'.so';lib=out/('capacity-runner'+suffix)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+suffix)),'-o',str(lib)],check=True)
 dll=C.CDLL(str(lib))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','fr_begin','fr_mask','fr_bad','fr_writes','fr_end'):
  getattr(dll,name).argtypes=getattr(reference,name).argtypes;getattr(dll,name).restype=getattr(reference,name).restype
 dll.ca_step.argtypes=[C.c_void_p];dll.ca_config.argtypes=[C.c_uint16]*2;dll.ca_baseline.argtypes=[C.c_void_p];dll.ca_info.argtypes=[C.c_int];dll.ca_info.restype=C.c_uint64
 return dll

# Route modeled file-pump instructions through the same observed CPU step;
# ordinary calls keep the existing compiled engine and genuine ROM-load seam.
_call=textwrap.dedent(inspect.getsource(extended.filemodel.IntegratedFiles.call))
_call=_call.replace('return super().call(name,a)','return geos.Fixture.call(self,name,a)')
_call=_call.replace('m.lib.zeropage_peddle_step_instruction(m.handle)','self.dll.ca_step(m.handle)')
_namespace=dict(ROM=extended.filemodel.ROM,geos=geos)
exec(_call,_namespace)
class Fixture(extended.Fixture):
 call=_namespace['call']

def run(out,base,physical):
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=runner(out);f=Fixture(out,frozen,dll,True);checks=[]
 data=geos.native_text('# Capacity\rOrdinary text for copying.\r:::basic\r10 PRINT "Hi"\r:::\r:::region Work\rHidden text.\r:::end\rTail.\r')
 try:
  geos.grid.Fixture.source(f,data,banks=1,physical=physical);assert not f.call('se_clip_init').p&1
  dll.ca_config(f.s['se_reu_physical_owner'],f.s['object_owner']);dll.ca_baseline(f.m.handle)
  def check(tag):
   assert f.read(0xc600,1024)==f.shim
   assert not any(f.get(n,1)for n in ('se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned')),(tag,f.debug())
   checks.append(dict(tag=tag,banks_peak=dll.ca_info(0),objects_peak=dll.ca_info(1),owner_stores=dll.ca_info(2),length=len(f.merged())));print('PASS',checks[-1],flush=True)
  def history_state():
   return f.read(f.s['se_h_state_start'],f.s['se_h_state_end']-f.s['se_h_state_start'])
  def history_journal():
   return f.object_bytes(f.read(f.s['se_h_token'],5),f.get('se_h_end',2))
  def clip_identity():
   return f.read(f.s['se_clip_token'],5)+f.read(f.s['se_clip_length'],3)
  def clip_payload():
   token=f.read(f.s['se_clip_token'],5);length=f.get('se_clip_length')
   return f.object_bytes(token,length) if token[0] and length else b''
  def name_binding():return f.read(f.s['se_f_current_name'],18)
  def memory_contract():
   return dict(source=f.merged(),canonical=f.canonical(),history=history_state(),name=name_binding(),clip=clip_identity(),canary=f.read(0xc600,1024))
  def full_contract():
   value=memory_contract();value.update(history_journal=history_journal(),clip_payload=clip_payload());return value
  def digests(value):return {k:hashlib.sha256(v).hexdigest() for k,v in value.items()}
  f.position(0);f.command(68)
  for _ in range(5):f.command(2)
  f.command(69);f.key(3);assert f.get('se_clip_length')==5
  f.command(115);f.command(99);f.render();check('clipboard-fold-FE-font')
  digest=bytes.fromhex(json.loads((frozen/'build/editor-report.json').read_text())['resident_binding']['digest'])
  f.m.load(0x800,digest+bytes(0x40));image=(frozen/'build/overlays/lifectrl.seo').read_bytes();f.m.load(0xa00,image[36+0x800:36+0x900]);f.put('se_e_redraw',0,1)
  r,n=f.lc(0);assert not r.p&1 and r.a==1,('FCBEGIN',r.a,r.p)
  steps=0
  while r.a:
   r,n=f.lc(1);steps+=1;assert not r.p&1 and steps<400,(r.a,r.p)
  assert steps==381;handle=f.m.read(0x810);bank=f.m.read(f.s['se_reu_map']+handle);assert f.m.read(f.s['se_reu_physical_owner']+bank)==0xfc
  snapshot=f.reu()[bank*65536:(bank+1)*65536]
  r,n=f.lc(2);assert not r.p&1 and f.m.read(f.s['se_reu_physical_owner']+bank)==0xfc;check('FC-retained-after-prepare')
  # Real save and staged open coexist with the retained snapshot capability.
  f.command(96);f.position(5);f.key(geos.native_text('Q')[0]);data=data[:5]+geos.native_text('Q')+data[5:]
  f.start(operation='A');f.enter_name(b'CAPOUT');f.key(13);assert f.fs[b'CAPOUT']==data
  check('SAVE-with-FC-clipboard-fold-history')
  f.fs[b'REOPEN']=data
  optional_before=[i for i in range(8) if f.m.read(f.s['object_owner']+i)==0x53]
  open_before=full_contract();open_memory=memory_contract();open_reu=f.reu()
  owners_before=f.read(f.s['se_reu_physical_owner'],physical)
  objects_before=f.read(f.s['object_owner'],8)
  dll.ca_config(f.s['se_reu_physical_owner'],f.s['object_owner']);dll.ca_baseline(f.m.handle)
  f.start(operation='O');f.enter_name(b'REOPEN');f.key(13)
  first_open_peak=dict(banks=dll.ca_info(0),objects=dll.ca_info(1),stores=dll.ca_info(2))
  optional_after=[i for i in range(8) if f.m.read(f.s['object_owner']+i)==0x53]
  fc_release=None;retry_peak=None;refusal=None
  if physical==32:
   assert not f.get('se_f_owner',1) and not f.get('se_f_error',1)
   assert f.merged()==data and f.m.read(f.s['se_reu_physical_owner']+bank)==0xfc
   assert f.reu()[bank*65536:(bank+1)*65536]==snapshot
   check('staged-OPEN-with-FC')
  else:
   assert f.get('se_f_error',1)==0x99 and f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3 and not f.get('se_fd_confirm',1)
   assert memory_contract()==open_memory and f.reu()==open_reu
   owners_after=f.read(f.s['se_reu_physical_owner'],physical)
   objects_after=f.read(f.s['object_owner'],8)
   owner_delta=[dict(bank=b,before=owners_before[b],after=owners_after[b]) for b in range(physical) if owners_before[b]!=owners_after[b]]
   object_delta=[dict(slot=i,before=objects_before[i],after=objects_after[i]) for i in range(8) if objects_before[i]!=objects_after[i]]
   if optional_before:
    assert len(optional_before)==1 and len(owner_delta)==1 and owner_delta[0]['before']==0x53 and owner_delta[0]['after']==0
    assert len(object_delta)==1 and object_delta[0]['slot']==optional_before[0] and object_delta[0]['before']==0x53 and object_delta[0]['after']==0
   else:
    assert not owner_delta and not object_delta
   refusal=dict(error=f.get('se_f_error',1),owner=f.get('se_f_owner',1),ui=f.get('se_e_ui',1),confirm=f.get('se_fd_confirm',1),owner_delta=owner_delta,object_delta=object_delta,owners_before=owners_before.hex(),owners_after=owners_after.hex(),objects_before=objects_before.hex(),objects_after=objects_after.hex(),reu_sha256=hashlib.sha256(open_reu).hexdigest())
   f.key(3);check('staged-OPEN-FC-pressure-refusal-cancelled')
   assert full_contract()==open_before and f.reu()==open_reu

   # Authenticate the retained lifecycle capability before checked release.
   assert f.m.read(f.s['se_reu_map']+handle)==bank
   assert f.m.read(f.s['se_reu_logical_owner']+handle)==0xfc
   assert f.m.read(f.s['se_reu_physical_owner']+bank)==0xfc
   header=snapshot[0xbc20:0xbc60];payload=snapshot[:0xbc18]
   assert header[:8]==b'LCA1'+bytes((1,0xa5,3,0xfc)) and header[8:24]==digest
   assert binascii.crc_hqx(payload,0xffff)==int.from_bytes(header[51:53],'little')
   assert binascii.crc_hqx(header[:62],0xffff)==int.from_bytes(header[62:64],'little')
   release_contract=full_contract();release_reu=f.reu()
   r,n=f.fast_call(f.s['se_reu_free'],x=handle);assert not r.p&1
   assert not f.m.read(f.s['se_reu_logical_owner']+handle) and not f.m.read(f.s['se_reu_physical_owner']+bank)
   assert full_contract()==release_contract and f.reu()==release_reu
   fc_release=dict(logical=handle,physical=bank,payload_crc=int.from_bytes(header[51:53],'little'),header_crc=int.from_bytes(header[62:64],'little'),binding=header[8:24].hex())

   dll.ca_config(f.s['se_reu_physical_owner'],f.s['object_owner']);dll.ca_baseline(f.m.handle)
   f.start(operation='O');f.enter_name(b'REOPEN');f.key(13)
   retry_peak=dict(banks=dll.ca_info(0),objects=dll.ca_info(1),stores=dll.ca_info(2))
   assert not f.get('se_f_owner',1) and not f.get('se_f_error',1) and f.merged()==data
   check('staged-OPEN-after-checked-FC-release')
  assert f.get('se_f_current_len',1)==6 and f.read(f.s['se_f_current_name'],6)==b'REOPEN'
  assert clip_identity()==open_before['clip'] and clip_payload()==open_before['clip_payload'] and f.read(0xc600,1024)==open_before['canary']
  opened=full_contract()
  # Consume remaining banks through the real provider. This preserves the
  # original COPY replacement refusal and observes every owner-table STA.
  hogs=[]
  while True:
   r,n=f.fast_call(f.s['se_reu_alloc'],a=0xa5)
   if r.p&1:break
   hogs.append(r.a)
  assert hogs and dll.ca_info(0)==physical-1
  exhausted_peak=dict(banks=dll.ca_info(0),objects=dll.ca_info(1),stores=dll.ca_info(2))
  source=f.merged();prior=f.reu();clip=f.read(f.s['se_clip_token'],5)
  f.position(0);f.command(68);f.position(min(20,len(data)))
  canonical=f.canonical()
  f.command(69,error=1)
  copy_error=f.get('se_e_error',1);assert copy_error and f.merged()==source and f.read(f.s['se_clip_token'],5)==clip
  assert f.reu()==prior and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  f.key(3);f.key(0x8b);f.key(0x8b)

  # Release only A5 handles. File/Open never has authority over these foreign
  # allocations.
  for h in reversed(hogs):
   r,n=f.fast_call(f.s['se_reu_free'],x=h);assert not r.p&1
  assert f.merged()==data and f.get('se_f_current_len',1)==6 and f.read(f.s['se_f_current_name'],6)==b'REOPEN'
  assert clip_identity()==opened['clip'] and clip_payload()==opened['clip_payload'] and f.read(0xc600,1024)==opened['canary']
  f.position(5);f.key(geos.native_text('R')[0]);assert f.merged()==data[:5]+geos.native_text('R')+data[5:]
  edit_pending=f.get('se_hot_pending',1);edited_current=f.get('se_h_current',4)
  f.command(16);assert f.merged()==data and f.get('se_h_current',4)==f.get('se_h_saved',4) and not f.get('se_h_dirty',1)
  assert f.get('se_h_cursor',2)<f.get('se_h_end',2)
  assert f.get('se_h_current',4)==f.get('se_h_saved',4)==1 and f.get('se_h_counter',4)==2 and not f.get('se_h_dirty',1)
  assert len(history_journal())==f.get('se_h_end',2) and f.get('se_h_cursor',2)<f.get('se_h_end',2)
  assert clip_identity()==opened['clip'] and clip_payload()==opened['clip_payload'] and f.read(0xc600,1024)==opened['canary'] and name_binding()==opened['name']
  check('pressure-release-open-edit-undo')
  proof=dict(optional53_before=optional_before,optional53_after_first_open=optional_after,refusal=refusal,exhausted_peak=exhausted_peak,first_open_peak=first_open_peak,retry_peak=retry_peak,fc_release=fc_release,before_open=digests(open_before),opened=digests(opened),edit=dict(pending=edit_pending,current=edited_current,source_bytes=len(data)+1),after_undo=dict(source_sha256=hashlib.sha256(f.merged()).hexdigest(),history_state_sha256=hashlib.sha256(history_state()).hexdigest(),history_journal_sha256=hashlib.sha256(history_journal()).hexdigest(),history_current=f.get('se_h_current',4),history_saved=f.get('se_h_saved',4),history_counter=f.get('se_h_counter',4),history_end=f.get('se_h_end',2),history_cursor=f.get('se_h_cursor',2),history_dirty=f.get('se_h_dirty',1),name=name_binding().hex(),clip=clip_identity().hex(),clip_payload_sha256=hashlib.sha256(clip_payload()).hexdigest(),canary_sha256=hashlib.sha256(f.read(0xc600,1024)).hexdigest()))
  result=dict(status='passed',identity=identity,physical_banks=physical,document_quota=65536,FC_retained=(physical==32),FC_explicitly_released=(physical==16),capture_steps=steps,checks=checks,peak_banks=max(exhausted_peak['banks'],first_open_peak['banks'],retry_peak['banks'] if retry_peak else 0),peak_objects=max(exhausted_peak['objects'],first_open_peak['objects'],retry_peak['objects'] if retry_peak else 0),owner_stores=exhausted_peak['stores']+first_open_peak['stores']+(retry_peak['stores'] if retry_peak else 0),allocation_failure=0x99 if physical==16 else 0,lifecycle_proof=proof,scope='Exact packaged current51 CPU commands/typed provider/C29 with modeled KERNAL files; no native IEC/IRQ claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--banks',type=int,choices=[16,32],default=16);a=p.parse_args();out=ROOT/'build/capacity-lifecycle'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.banks)
