"""Reduced REU workload with retained FC snapshot and instruction-level allocation peaks.

ROM file operations use the existing explicit CPU filesystem model; no native
IEC/pixel/IRQ claim. Every allocator owner-table store is observed, including
allocations released before an operation completes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,subprocess,sys,zipfile,inspect,textwrap
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
  f.fs[b'REOPEN']=data;f.start(operation='O');f.enter_name(b'REOPEN');f.key(13);assert f.merged()==data;check('staged-OPEN-with-FC')
  # Consume remaining banks through the actual allocator, not table injection.
  hogs=[]
  while True:
   r,n=f.fast_call(f.s['se_reu_alloc'],a=0xa5)
   if r.p&1:break
   hogs.append(r.a)
  assert hogs and dll.ca_info(0)==physical-1
  before=f.canonical();source=f.merged();prior=f.reu();clip=f.read(f.s['se_clip_token'],5)
  f.position(0);f.command(68);f.position(min(20,len(data)))
  # COPY must fail cleanly when it needs a replacement clipboard bank.
  canonical=f.canonical()
  f.command(69,error=1)
  error=f.get('se_e_error',1);assert error and f.merged()==source and f.read(f.s['se_clip_token'],5)==clip,(error,'COPY pressure')
  assert f.reu()==prior and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  f.key(3);f.key(0x8b);f.key(0x8b)
  # Leave one bank free: staged OPEN reserves one object, then must roll back
  # the next failed reservation without disturbing any previously owned bank.
  h=hogs.pop();r,n=f.fast_call(f.s['se_reu_free'],x=h);assert not r.p&1
  f.fs[b'NEW']=data+b'New bytes'
  binding=f.read(f.s['se_f_current_name'],18)
  f.start(operation='O');f.enter_name(b'NEW');stable=f.canonical();source=f.merged();owned=f.read(f.s['se_reu_physical_owner'],256);prior=f.reu()
  f.key(13);assert f.get('se_f_error',1)==0x99 and f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3,('OPEN-pressure',f.get('se_f_error',1),f.get('se_f_owner',1),f.get('se_e_ui',1),f.get('se_fd_confirm',1),f.read(f.s['se_reu_physical_owner'],physical).hex())
  assert f.canonical()==stable and f.merged()==source and f.read(f.s['se_clip_token'],5)==clip and f.read(f.s['se_f_current_name'],18)==binding
  now=f.reu()
  for b,owner in enumerate(owned):
   if 2<=owner<255:assert now[b*65536:(b+1)*65536]==prior[b*65536:(b+1)*65536],('OPEN rollback owned bank',b,owner)
  f.key(3);check('staged-OPEN-reservation-failure-rollback')
  for h in reversed(hogs):
   r,n=f.fast_call(f.s['se_reu_free'],x=h);assert not r.p&1
  assert f.reu()[bank*65536:(bank+1)*65536]==snapshot
  f.key(3);f.position(5);f.key(geos.native_text('R')[0]);assert len(f.merged())==len(data)+1;check('bank-pressure-release-continued-edit')
  result=dict(status='passed',identity=identity,physical_banks=physical,document_quota=65536,FC_retained=True,capture_steps=steps,checks=checks,peak_banks=dll.ca_info(0),peak_objects=dll.ca_info(1),owner_stores=dll.ca_info(2),allocation_failure=error,scope='Actual immutable editor commands/typed provider/C29 with modeled KERNAL files. Allocation peaks sampled after every absolute/indexed owner-table STA, including transient allocations; not native IEC or complete workload maxima.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--banks',type=int,choices=[16,32],default=16);a=p.parse_args();out=ROOT/'build/capacity-lifecycle'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.banks)
