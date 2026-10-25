"""Actual root page cost attribution, privateCPU instructions only, no product edits."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,json,re,subprocess,sys
import test_geos_paint_packet_candidate as packet
import test_geos_semantic_editor as semantic
import test_geos_fold_editor as fold
import test_fold_retention as retention
import test_grid_editor_vice
ROOT=packet.ROOT
BASE=ROOT/'build/geos-raster-loop-native-input/20261025T182425073274Z/fixture'
def runner(out):
 retention.runner(out);p=out/'runner.cpp';source=p.read_text();needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);';assert source.count(needle)==1
 extra=r'''
#include <cstdlib>
static uint16_t cp_pc[64],cp_active;static uint8_t cp_slot[64],cp_tag[64];static unsigned cp_n=0,cp_depth=0;static bool cp_on=false;
struct CPFrame{unsigned id;uint8_t sp;uint16_t ret;};static CPFrame cp_frames[128];
static uint64_t cp_calls[64],cp_inc[64],cp_exc[64];
extern "C" void cp_begin(uint16_t active,unsigned n,const uint16_t*pc,const uint8_t*slot,const uint8_t*tag){cp_active=active;cp_n=n;memcpy(cp_pc,pc,n*2);memcpy(cp_slot,slot,n);memcpy(cp_tag,tag,n);memset(cp_calls,0,sizeof(cp_calls));memset(cp_inc,0,sizeof(cp_inc));memset(cp_exc,0,sizeof(cp_exc));cp_depth=0;cp_on=true;}
extern "C" void cp_end(){cp_on=false;}
extern "C" void cp_metrics(unsigned i,uint64_t*p){p[0]=cp_calls[i];p[1]=cp_inc[i];p[2]=cp_exc[i];}
static void cp(ZeroPagePeddle*m,const decltype(zeropage_peddle_regs((ZeroPagePeddle*)nullptr))&r){if(!cp_on)return;
 while(cp_depth && r.pc==cp_frames[cp_depth-1].ret && r.sp==uint8_t(cp_frames[cp_depth-1].sp+2))cp_depth--;
 for(unsigned i=0;i<cp_n;i++){if(r.pc!=cp_pc[i])continue;if(cp_slot[i] && zeropage_peddle_read(m,cp_active+cp_slot[i]-1)!=cp_tag[i])continue;
  if(cp_depth>=128)abort();uint16_t ret=uint16_t(zeropage_peddle_read(m,0x100+uint8_t(r.sp+1)) | (zeropage_peddle_read(m,0x100+uint8_t(r.sp+2))<<8))+1;
  cp_frames[cp_depth++]={i,r.sp,ret};cp_calls[i]++;break;}
 for(unsigned j=0;j<cp_depth;j++)cp_inc[cp_frames[j].id]++;
 if(cp_depth)cp_exc[cp_frames[cp_depth-1].id]++;
}
static void cp_after(ZeroPagePeddle*m){if(!cp_on)return;auto r=zeropage_peddle_regs(m);while(cp_depth && r.pc==cp_frames[cp_depth-1].ret && r.sp==uint8_t(cp_frames[cp_depth-1].sp+2))cp_depth--;}
'''
 source=source.replace(needle,extra+needle+'cp(m,r);');assert source.count('zeropage_peddle_step_instruction(m);')==1;source=source.replace('zeropage_peddle_step_instruction(m);','zeropage_peddle_step_instruction(m);cp_after(m);');p.write_text(source);ext='.dylib'if sys.platform=='darwin'else'.so';path=out/('page-cost'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(retention.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True)
 dll=C.CDLL(str(path));dll.gm_rom.argtypes=[C.c_void_p,C.c_void_p];dll.gm_rom_count.restype=C.c_uint64;dll.gm_profile.argtypes=[C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.c_uint16,C.c_uint16];dll.gm_metric.argtypes=[C.c_int];dll.gm_metric.restype=C.c_uint64
 dll.gm_run.argtypes=[C.c_void_p,C.c_uint64];dll.gm_run.restype=C.c_uint64;dll.gm_idle.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64];dll.gm_idle.restype=C.c_uint64;dll.gm_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.gm_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];dll.fr_begin.argtypes=[C.c_uint16]*7;dll.fr_mask.argtypes=[C.c_void_p];dll.fr_bad.restype=dll.fr_writes.restype=C.c_uint32
 dll.cp_begin.argtypes=[C.c_uint16,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p];dll.cp_metrics.argtypes=[C.c_uint,C.c_void_p];return dll

def run(out,base):
 fixture,identity=semantic.geos.freeze(out,base);packet.build(out/'C22',fixture,'control');labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',(out/'C22/paint.lbl').read_text())}
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=fixture;semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=identity['names'];dll=runner(out);f=fold.Fixture(out,fixture,dll,True)
 try:
  data=test_grid_editor_vice.fixture();f.source(data);f.command(99);f.position(0);f.put('se_v_top',0);f.render()
  for n in ['se_r_valid','se_gc_valid','se_gc_width']:f.put(n,0,1)
  f.m.write(0xCF90,0);f.m.write(0xCFE8,0)
  # Guarded C22 symbols must come from its cache object, not same-name local
  # labels in another image. Exported names are unique; cheap owner labels
  # are intentionally omitted from quantitative root accounting.
  targets=[]
  for n in ['se_gp_paint_begin','se_gp_paint_step','se_gp_cache_guard','refresh','owned','header_request','se_gp_cache_read','request','certify','scan_line','draw_prose','draw_cell','native_step']:
   targets.append((n,labels[n],2,identity['names'].index('geospaint')+1))
  for n in ['se_view_init','se_doc_validate','se_object_validate','object_service_valid','se_doc_invalidate','se_reu_copy','se_editor_render','se_editor_service']:
   targets.append((n,f.s[n],0,0))
  for n,slot in [('viewsource',1),('geosrow',1),('geosline',2),('geospage',2),('geossema',2),('geoslex',2),('geosinln',2),('gfont',2)]:targets.append(('overlay-'+n,0xA010 if slot==1 else 0xB010,slot,identity['names'].index(n)+1))
  canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();f.audit_begin();before=f.total_instructions
  dll.cp_begin(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*[t[1]for t in targets]),(C.c_uint8*len(targets))(*[t[2]for t in targets]),(C.c_uint8*len(targets))(*[t[3]for t in targets]));f.render();dll.cp_end();f.dll.fr_end();writes=f.audit_end(reu,'profile-exact-derived-writes');used=f.total_instructions-before
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xC600,1024)==f.shim
  fonts={n:(fixture/'fonts'/n).read_bytes()for n in semantic.geos.GEOS_FONTS+('native8.bin',)};want=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==want[0] and f.read(0x4000,1000)==want[1];semantic.geos.png(want[0],want[1],out/'actual-cpu.png')
  records=[]
  for i,(n,pc,slot,tag)in enumerate(targets):
   m=(C.c_uint64*3)();dll.cp_metrics(i,m);records.append(dict(name=n,pc=hex(pc),slot=slot,tag=tag,calls=m[0],inclusive_instructions=m[1],exclusive_instructions=m[2]));print(records[-1],flush=True)
  result=dict(status='passed',identity=identity,source_length=len(data),top=f.get('se_v_top'),instructions=used,derived_stashes=writes,functions=records,scope='Actual public TOP0 forcedfull root, exact independent320x200pixels/attrs/source/catalog/shim and observedtypedREUwrite spans across16MiB. CPUinstruction function attribution, not nativecycles. Inclusive frames countnestedtrackedtargets; exclusive excludestrackedchildfunctions only. No production edits.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-page-cost-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,BASE)
