"""Read-only actual CPU attribution for one independently verified styled page."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,subprocess
import test_geos_semantic_editor as semantic
geos=semantic.geos;ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T030804932033Z/fixture'

def runner(out):
 base=out/'runner-base';base.mkdir();old=geos.grid.runner(base)
 cpp=(base/'runner.cpp').read_text()
 counters='''
static bool pf_on=false;static uint16_t pf_active,pf_call,pf_frame,pf_page,pf_tail;
static uint64_t pf_pc[65536]={},pf_cat[32]={},pf_calls[32768]={},pf_bytes=0;
extern "C" void pf_config(uint16_t a,uint16_t c,uint16_t f,uint16_t p,uint16_t t){pf_active=a;pf_call=c;pf_frame=f;pf_page=p;pf_tail=t;}
extern "C" void pf_enable(int on){pf_on=on;}
extern "C" uint64_t pf_value(int kind,int index){return kind==0?pf_pc[index]:kind==1?pf_cat[index]:kind==2?pf_calls[index]:pf_bytes;}
'''
 cpp=cpp.replace('static void step(ZeroPagePeddle*m)',counters+'\nstatic void step(ZeroPagePeddle*m)')
 hook='''
 if(pf_on){pf_pc[r.pc]++;
  if(r.pc==pf_page || r.pc==pf_tail)pf_bytes++;
  if(r.pc==pf_call && r.a<64 && r.x<2){auto op=zeropage_peddle_read(m,pf_frame);pf_calls[(r.a*2+r.x)*256+op]++;}
  if(r.pc>=0xa000 && r.pc<0xc000){auto slot=r.pc>=0xb000?1:0;auto id=zeropage_peddle_read(m,pf_active+slot);if(id>0&&id<=32)pf_cat[id-1]++;}
 }
'''
 cpp=cpp.replace('int offset=-1;', 'int offset=-1;'+hook)
 path=out/'profile.cpp';path.write_text(cpp);ext='.dylib' if __import__('sys').platform=='darwin' else '.so';lib=out/('profile'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if ext=='.dylib' else '-shared','-fPIC','-I'+str(geos.grid.VENDOR),str(path),str(ROOT/('build/libse_peddle'+ext)),'-o',str(lib)],check=True)
 dll=C.CDLL(str(lib))
 for n in ['gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu']:
  getattr(dll,n).argtypes=getattr(old,n).argtypes;getattr(dll,n).restype=getattr(old,n).restype
 dll.pf_config.argtypes=[C.c_uint16]*5;dll.pf_enable.argtypes=[C.c_int];dll.pf_value.argtypes=[C.c_int,C.c_int];dll.pf_value.restype=C.c_uint64
 return dll

def run(out,previous):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=runner(out);f=geos.Fixture(out,frozen,dll,True)
 try:
  data=semantic.FIXTURE;f.source(data);f.command(99);before=f.canonical();used=f.total_instructions
  s=f.s;dll.pf_config(s['se_overlay_active'],s['se_overlay_call'],s['se_overlay_frame'],s['se_overlay_crc_page_byte'],s['se_overlay_crc_tail_byte'])
  loads=f.get('se_overlay_loads',2);hits=f.get('se_overlay_hits',2);dll.pf_enable(1);f.render();dll.pf_enable(0);measured=f.total_instructions-used
  bits,attrs,rows,_=semantic.expected(f,data,{n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)})
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  assert f.canonical()==before and f.merged()==data and f.read(0xC600,1024)==f.shim
  assert not any(f.get(n,1) for n in ['se_f_owner','se_fs_owned','se_doc_read_locks'])
  pc={a:dll.pf_value(0,a) for a in range(65536)}
  calls=[dict(id=id_,slot=slot,operation=op,calls=dll.pf_value(2,(id_*2+slot)*256+op)) for id_ in range(64) for slot in range(2) for op in range(256) if dll.pf_value(2,(id_*2+slot)*256+op)]
  leaf={name:dll.pf_value(1,i) for i,name in enumerate(identity['names']) if dll.pf_value(1,i)}
  crc=sum(pc[a] for a in range(s['se_overlay_crc_page_byte'],s['fast_crc_finished']))
  overlay_resident=sum(pc[a] for a in range(s['se_overlay_call'],s['se_overlay_read']))
  total=sum(pc.values());assert total==measured,(total,measured)
  result=dict(status='passed',identity=identity,source_bytes=len(data),instructions=total,including_test_validation_instructions=f.total_instructions-used,overlay_leaf_instructions=leaf,overlay_calls=calls,overlay_loads=(f.get('se_overlay_loads',2)-loads)&65535,overlay_hits=(f.get('se_overlay_hits',2)-hits)&65535,CRC_bytes=dll.pf_value(3,0),CRC_loop_instructions=crc,overlay_resident_instructions=overlay_resident,other_resident_instructions=total-sum(leaf.values())-overlay_resident,pixels_checked=64000,attributes_checked=1000,scope='Actual instruction-PC counts, not cycle/timing claims; unchanged CPU and actual ROM-read seam only')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');(out/'pc-counts.json').write_text(json.dumps({hex(a):n for a,n in pc.items() if n},indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items() if k!='identity'},indent=2));return result
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/geos-semantic-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture)
