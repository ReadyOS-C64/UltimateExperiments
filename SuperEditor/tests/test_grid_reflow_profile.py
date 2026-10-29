"""Instruction attribution on immutable releasedSP2; no production code edits."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,json,subprocess
import test_geos_fold_editor as fold,test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'agentsworking/evidence/M8/20261025T201720331556Z-grid-long-prose/fixture';LEAF=BASE.parent/'leaf'
def labels(p):return{z[2].lstrip('.'):int(z[1],16)for line in p.read_text().splitlines()if(z:=line.split())and z[0]=='al'}
def run(out):
 dll=fold.retention.runner(out);cpp=out/'runner.cpp';s=cpp.read_text();extra='''
static uint16_t lp_entry[16],lp_ret[16];static uint8_t lp_sp[16];static uint64_t lp_start[16],lp_total[16],lp_count[16];static bool lp_live[16],lp_on=false;
extern "C" void lp_init(const uint16_t*p){memcpy(lp_entry,p,32);memset(lp_live,0,sizeof(lp_live));memset(lp_count,0,sizeof(lp_count));memset(lp_total,0,sizeof(lp_total));lp_on=true;}
extern "C" uint64_t lp_total_get(int n){return lp_total[n];}
extern "C" uint64_t lp_count_get(int n){return lp_count[n];}
static void lp_before(ZeroPagePeddle*m){if(!lp_on)return;auto r=zeropage_peddle_regs(m);for(int i=0;i<16;i++)if(lp_entry[i]&&r.pc==lp_entry[i]&&!lp_live[i]){lp_live[i]=true;lp_start[i]=r.instructions;lp_sp[i]=r.sp;lp_ret[i]=uint16_t(zeropage_peddle_read(m,0x100+uint8_t(r.sp+1))|(zeropage_peddle_read(m,0x100+uint8_t(r.sp+2))<<8))+1;lp_count[i]++;}}
static void lp_after(ZeroPagePeddle*m){if(!lp_on)return;auto r=zeropage_peddle_regs(m);for(int i=0;i<16;i++)if(lp_live[i]&&r.pc==lp_ret[i]&&r.sp==uint8_t(lp_sp[i]+2)){lp_live[i]=false;lp_total[i]+=r.instructions-lp_start[i];}}
''';s=s.replace('static void step(ZeroPagePeddle*m){',extra+'\nstatic void step(ZeroPagePeddle*m){lp_before(m);',1).replace('zeropage_peddle_step_instruction(m);','zeropage_peddle_step_instruction(m);lp_after(m);',1);cpp.write_text(s);lib=out/'profile.dylib';subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(grid.VENDOR),cpp,ROOT/'build/libse_peddle.dylib','-o',lib],check=True);pd=C.CDLL(str(lib))
 for name in ('gm_run','gm_idle','gm_read','gm_reu','gm_rom','gm_rom_count','gm_profile','gm_metric','fr_begin','fr_end','fr_bad','fr_writes','fr_mask'):
  fn=getattr(pd,name);old=getattr(dll,name);fn.argtypes=old.argtypes;fn.restype=old.restype
 pd.lp_init.argtypes=[C.POINTER(C.c_uint16)];pd.lp_total_get.argtypes=pd.lp_count_get.argtypes=[C.c_int];pd.lp_total_get.restype=pd.lp_count_get.restype=C.c_uint64
 ident=json.load(open(BASE/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=BASE;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=ident['names'];f=fold.Fixture(out,BASE,pd,True);cl=labels(LEAF/'grid.lbl');rl=labels(LEAF/'geostail.lbl');names=['pixel_shift','status','packet_crc','verify_row','SP_crc','fields','short_prepare','long_prepare','packet_commit','view_peek','caret_xor','REU_copy'];pcs=[cl['se_lp_shift_row'],cl['status'],rl['packet_crc'],rl['verify_row'],rl['sc_crc'],rl['fields'],rl['type_prepare'],rl['type_long_prepare'],rl['long_packet'],f.s['se_view_peek'],cl['xor_cell'],f.s['se_reu_copy']];cases=[]
 try:
  for width in(60,80):
   raw=grid.native_text(':::basic\r10 PRINT 1\r:::\rAlpha '+('word '*100)+'ends.\rTail.');at=raw.index(grid.native_text('Alpha'))+132;f.source(raw);f.command(97 if width==60 else 98);f.position(at);f.render();f.finish_style()
   for key in(81,20):
    f.key(key);pd.lp_init((C.c_uint16*16)(*pcs,*([0]*(16-len(pcs)))));start=f.total_instructions;f.render();n=f.total_instructions-start;assert f.m.read(0x89ff)==2;metrics={name:dict(calls=pd.lp_count_get(i),inclusive_instructions=pd.lp_total_get(i))for i,name in enumerate(names)};f.finish_style();assert f.total_instructions-start==n;want,attrs=grid.expected(f,f.merged())[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs;row=dict(width=width,key=key,instructions=n,metrics=metrics);cases.append(row);print(json.dumps(row),flush=True)
  result=dict(status='passed',cases=cases,scope='ActualPeddle instructionentry/return attribution withunchanged6510product; metricsinclusive/overlapping, notnativecycles.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/grid-geowrite-reflow-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
