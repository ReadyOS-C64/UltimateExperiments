"""Private R29 reader/body + smaller C21 scheduler; no product build edits.

The root job protocol is unchanged. Only sealed candidate assets are substituted.
The actual reader context/read code is unchanged and shared in R29; GEOS worker
calls are rebound 14->29 to avoid evicting the packet/map micromodule.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys,zipfile,ctypes as C
import test_geos_edit_cache as edit
import test_geos_semantic_editor as semantic
from overlays import wrap,HEADER
ROOT=edit.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T080336705059Z/fixture'
DIR=ROOT/'src/render/geos/coordinator-candidate'


def build(out,frozen):
 out.mkdir();r=json.loads((frozen/'build/editor-report.json').read_text());s=r['symbols'];seal=r['resident_binding']['digest'];api=out/'api';api.mkdir()
 (api/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 original=out/'original';original.mkdir()
 with zipfile.ZipFile(frozen/'product-sources.zip') as z:
  for n in z.namelist():
   if n.startswith(('src/','cfg/')):z.extract(n,original)
 def source(name):return original/name
 records={}
 def image(tag,slot,id_,modules,cfg):
  objs=[]
  for name,path,flags in modules:
   obj=out/(tag+'-'+name+'.o');edit.cmd('ca65','-g',*flags,'-I',api,'-I',original/'src','-o',obj,path);objs.append(obj)
  edit.cmd(sys.executable,'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',out/(tag+'-bindings.s'),*objs)
  edit.cmd('ca65','-o',out/(tag+'-bindings.o'),out/(tag+'-bindings.s'))
  edit.cmd('ld65','-C',cfg,'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objs,out/(tag+'-bindings.o'))
  payload=(out/(tag+'.bin')).read_bytes();image_=wrap(payload,slot,id_,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/(tag+'.seo')).write_bytes(image_)
  records[tag]=dict(image=image_,payload_bytes=len(payload),sha256=hashlib.sha256(image_).hexdigest(),slot=slot,id=id_)
 image('readerbody',0,29,[('entry',DIR/'reader-body.s',[]),('context',source('src/fold/source-context.s'),[]),('read',source('src/fold/source-read.s'),[]),('cache',source('src/render/geos/cache.s'),['-D','SE_GP_CACHE_WARM_ONLY=1'])],DIR/'reader-body.cfg')
 image('geospage',1,21,[('page',DIR/'page-scheduler.s',[]),('cache',source('src/render/geos/cache.s'),[])],source('cfg/geos-editor-page.cfg'))
 # Workers are otherwise byte-for-byte source copies. Their sole reader
 # dispatch immediate changes from14 to29; no source guards or frame changes.
 for tag,id_,main,modules,cfg in [
 ('geosline',20,'source-line.s',[('line','line.s',[]),('measure','measure.s',[]),('assets','assets.s',[])],'geos-editor-layout.cfg'),
 ('geossema',24,'semantic.s',[('parser','../../supermark/block.s',[])],'geos-editor-semantic.cfg'),
 ('geoslex',25,'semantic-lex.s',[('parser','../../supermark/lexer.s',[])],'geos-editor-semantic-lex.cfg'),
 ('geosinln',26,'inline.s',[('parser','../../supermark/inline.s',[])],'geos-editor-inline.cfg')]:
  text=source('src/render/geos/'+main).read_text();assert text.count('lda #14')==1,(tag,'reader dispatch')
  path=out/(tag+'.s');path.write_text(text.replace('lda #14','lda #29'))
  flags=['-D','SE_EDITOR_GEOS_INLINE=1'] if tag=='geosline' else[]
  image(tag,1,id_,[('main',path,flags)]+[(n,source('src/render/geos/'+p),f)for n,p,f in modules],source('cfg/'+cfg))
 return records


def runner(out):
 dll=edit.fold.retention.runner(out);cpp=out/'runner.cpp';s=cpp.read_text();needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 assert s.count(needle)==1
 code="""
static uint16_t gp_stage=0,gp_candidate=0,gp_ids=0,gp_slots=0;
static uint64_t gp_loads[512];
extern "C" void gp_config(uint16_t stage,uint16_t candidate,uint16_t ids,uint16_t slots){gp_stage=stage;gp_candidate=candidate;gp_ids=ids;gp_slots=slots;memset(gp_loads,0,sizeof(gp_loads));}
extern "C" uint64_t gp_metric(uint16_t n){return gp_loads[n];}
"""
 hook='if(r.pc==gp_stage){uint8_t i=zeropage_peddle_read(m,gp_candidate),id=zeropage_peddle_read(m,gp_ids+i),slot=zeropage_peddle_read(m,gp_slots+i);if(slot<2)gp_loads[256*slot+id]++;}'
 s=s.replace(needle,code+needle+hook);cpp.write_text(s)
 ext='.dylib'if sys.platform=='darwin'else'.so';path=out/('profile-runner'+ext)
 edit.cmd('clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(semantic.geos.grid.VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',path)
 dll=C.CDLL(str(path))
 dll.gm_rom.argtypes=[C.c_void_p,C.c_void_p];dll.gm_rom_count.restype=C.c_uint64
 dll.gm_profile.argtypes=[C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.c_uint16,C.c_uint16];dll.gm_metric.argtypes=[C.c_int];dll.gm_metric.restype=C.c_uint64
 dll.gm_run.argtypes=[C.c_void_p,C.c_uint64];dll.gm_run.restype=C.c_uint64;dll.gm_idle.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64];dll.gm_idle.restype=C.c_uint64;dll.gm_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.gm_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
 dll.fr_begin.argtypes=[C.c_uint16]*7;dll.fr_mask.argtypes=[C.c_void_p];dll.fr_bad.restype=C.c_uint32;dll.fr_writes.restype=C.c_uint32
 dll.gp_config.argtypes=[C.c_uint16]*4;dll.gp_metric.argtypes=[C.c_uint16];dll.gp_metric.restype=C.c_uint64
 return dll


def run(out,previous,fit_only=False):
 frozen,identity=semantic.geos.freeze(out,previous);records=build(out/'candidate',frozen)
 result=dict(status='fit-only',identity=identity,records={k:{n:v for n,v in r.items()if n!='image'}for k,r in records.items()},scope='Private candidate assets only; no shared editor changes.')
 print(json.dumps(result['records'],indent=2),flush=True)
 if fit_only:
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 geos=semantic.geos;geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=runner(out);f=edit.fold.Fixture(out,frozen,dll,True);g=edit.fold.Fixture(out,frozen,dll,True)
 f.assets.update({k:v['image']for k,v in records.items()});fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};frames=[]
 def measure(x):
  dll.gp_config(*[x.s[n]for n in('crc_stage','candidate','se_overlay_ids','image_slot')]);used=x.total_instructions;before=x.get('se_overlay_loads',2);x.render()
  loads={str(i):int(dll.gp_metric(i))for i in range(512)if dll.gp_metric(i)}
  byid={image_[5]*256+image_[6]:len(image_)-HEADER for image_ in x.assets.values()}
  return dict(instructions=x.total_instructions-used,loads=(x.get('se_overlay_loads',2)-before)&65535,stage_counts=loads,crc_payload_bytes=sum(byid[int(i)]*v for i,v in loads.items()))
 def fold_expected(data,folds):
  from geos_fold_model import raster
  bits,attrs,rows,model=raster(data,fonts,folds,top=f.get('se_v_top'),caret=f.get('se_hot_caret'))
  matrix,colors,popup=geos.grid.logical_ui(f,data)
  bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
  return bits,attrs,rows,model
 def check(data,tag,folds=None):
  before=f.canonical();reu=f.reu();a=measure(f);b=measure(g);expected=semantic.expected(f,data,fonts) if folds is None else fold_expected(data,folds)
  assert f.canonical()==before and f.merged()==data==g.merged(),(tag,'source')
  assert (f.read(0x6000,8000),f.read(0x4000,1000))==expected[:2],(tag,'independent pixels')
  assert(f.read(0x6000,8000),f.read(0x4000,1000))==(g.read(0x6000,8000),g.read(0x4000,1000)),(tag,'baseline pixels')
  fc,bank=f.raw_cache();gc,_=g.raw_cache();assert fc[:64]==gc[:64],(tag,'header')
  for i in range(fc[1]):
   at=0x200+i*2048;assert fc[at:at+1814]==gc[at:at+1814],(tag,'row',i)
  after=f.reu();base=bank*65536;assert reu[:base]==after[:base] and reu[base+65536:]==after[base+65536:],(tag,'foreign REU')
  assert f.read(0xC600,1024)==f.shim and not any(f.get(n,1)for n in('se_f_owner','se_fs_owned','se_doc_read_locks'))
  geos.png(*expected[:2],out/(tag+'.png'));frames.append(dict(tag=tag,candidate=a,baseline=b));print('PASS',frames[-1],flush=True)
 try:
  for data,tag in[(semantic.FIXTURE,'mixed-full'),(semantic.INLINE_FIXTURE,'inline-full')]:
   for x in(f,g):x.source(data);x.command(99)
   check(data,tag)
   at=data.index(geos.native_text('plain'))+2 if geos.native_text('plain')in data else 5
   for x in(f,g):x.position(at);x.key(geos.native_text('Q')[0])
   check(data[:at]+geos.native_text('Q')+data[at:],tag+'-pending')
  data=edit.fold.TINY
  for x in(f,g):x.source(data);x.command(99);x.command(115)
  from dataclasses import replace
  folds=[replace(v,flags=1)for v in edit.fold.tree(data)]
  check(data,'folded-source',folds)
  data=geos.native_text('Ordinary text here.\rSecond source line.\rThird line.\r')
  for x in(f,g):
   x.source(data);x.command(99)
   for _ in range(5):assert not x.call('se_hot_call',7).p&1
   x.render();x.key(geos.native_text('Q')[0])
  check(data[:5]+geos.native_text('Q')+data[5:],'incremental-row')
  # Real resident STOP/missing-image cleanup uses the unchanged86B context.
  # These are live source leases, not a hand-seeded owned flag.
  data=semantic.INLINE_FIXTURE
  faults=[]
  for kind in('STOP','missing-R29','source-revision'):
   for x in(f,g):x.source(data);x.command(99)
   r=f.call('se_editor_render');assert not r.p&1 and f.get('se_e_job',1)==11
   for tick in range(10000):
    if f.m.read(0x912D):break
    r=f.call('se_editor_service');assert not r.p&1,(kind,'before-lease',r.a)
   else:raise AssertionError((kind,'no live source context'))
   assert f.get('se_doc_read_locks',1)==1 and f.get('se_f_owner',1)==4
   canonical=f.canonical();before=f.reu();removed=None
   if kind=='STOP':f.queued(3)
   elif kind=='source-revision':
    for x in(f,g):x.put('se_r_revision',x.get('se_r_revision',4)+1,4)
   else:
    removed=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==29 and f.m.read(f.s['image_slot']+i)==0)
    f.m.write(f.s['se_overlay_ids']+removed,0);f.m.write(f.s['se_overlay_active'],0)
   for step in range(10000):
    r=f.call('se_editor_service')
    if not f.get('se_e_job',1):break
   else:raise AssertionError((kind,'cleanup not complete'))
   assert f.canonical()==canonical and f.merged()==data,(kind,'canonical source')
   assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_fs_owned')) and not f.m.read(0x912D),(kind,'orphan lease')
   assert f.read(0xC600,1024)==f.shim and f.reu()==before,(kind,'fault cleanup changed source/REU')
   if removed is not None:f.m.write(f.s['se_overlay_ids']+removed,29)
   f.put('se_e_error',0,1);check(data,'recovery-'+kind)
   faults.append(dict(tag=kind,live_lease=True,cleanup_steps=step+1))
  result.update(status='passed',frames=frames,faults=faults,scope='Actual public root with privately rebound reader/body/scheduler, compared against independent canonical/font oracle and immutable full producer. CPU instructions and exact staged payload bytes, not native cycles.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--fit-only',action='store_true');a=p.parse_args();out=ROOT/'build/geos-coordinator-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.fit_only)
