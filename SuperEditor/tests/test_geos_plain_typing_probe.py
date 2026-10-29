"""Private Plain GEOS typing profile, exact packaged source/ROM/provider seams.
No shared build/source changes. Default profile only, no private substitutions.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,hashlib,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_geos_editor as geos
import test_geos_preview_editor as preview
import font_fixture
BASE=ROOT/'build/view-menu-current/20261026T210541922992Z/link/fixture'
DATA=geos.native_text('Ordinary short text here.\rSecond ordinary row.\rThird source row.\rLast.')
def profile_runner(out):
 original=geos.grid.runner(out);p=out/'runner.cpp';source=p.read_text()
 marker='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);int offset=-1;'
 assert source.count(marker)==1
 extra='''static uint16_t policy_active=0,policy_ids=0;static uint64_t policy_calls[64]={},stage41=0,stage42=0;
extern "C" void pt_start(uint16_t a,uint16_t ids){policy_active=a;policy_ids=ids;for(auto &v:policy_calls)v=0;stage41=stage42=0;}
extern "C" uint64_t pt_calls(uint8_t id){return id<64?policy_calls[id]:id==254?stage42:stage41;}
'''
 source=source.replace(marker,extra+marker+'''
 if(policy_active && r.pc==0xB010){auto index=zeropage_peddle_read(m,policy_active+1);if(index){auto id=zeropage_peddle_read(m,policy_ids+index-1);if(id<64)policy_calls[id]++;}}
 if(policy_active && r.pc==0x5000 && zeropage_peddle_read(m,0xCBD5)==0x41)stage41++;
 if(policy_active && r.pc==0x5000 && zeropage_peddle_read(m,0xCBD5)==0x42)stage42++;
''')
 p.write_text(source);suffix='.dylib'if sys.platform=='darwin'else'.so';path=out/('plain-runner'+suffix)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+suffix)),'-o',str(path)],check=True)
 dll=C.CDLL(str(path))
 for n in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu'):
  getattr(dll,n).argtypes=getattr(original,n).argtypes;getattr(dll,n).restype=getattr(original,n).restype
 dll.pt_start.argtypes=[C.c_uint16,C.c_uint16];dll.pt_calls.argtypes=[C.c_uint8];dll.pt_calls.restype=C.c_uint64
 return dll
def run(out,base):
 out.mkdir(parents=True);ident=json.loads((base/'freeze.json').read_text());geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=font_fixture.ROOT=base;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=ident['names']
 dll=profile_runner(out);f=preview.Fixture(out,base,dll,True);g=preview.Fixture(out,base,dll,True);fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};records=[]
 assert f.s['se_gf_state']==0xcbc0 # exact fixed window-witness counter address
 try:
  for preset,caps in [('full',3),('plain',0)]:
   for x in (f,g):
    x.source(DATA);x.typed(geos.native_text('syntax '+preset));x.command(99)
    for _ in range(5):x.key(0x1d)
    x.render()
   for action,key in [('insert',geos.native_text('Q')[0]),('back',0x14)]:
    before_key=f.total_instructions
    for x in (f,g):x.key(key)
    input_used=f.total_instructions-before_key;gtc=f.read(0x9149,47);raw,bank=f.raw_cache();caretrow=raw[42];row=raw[0x200+caretrow*2048:0x200+(caretrow+1)*2048];count=int.from_bytes(row[12:14],'little')
    gce=f.read(0xcfe8,20);canonical=f.canonical();reu=f.reu();catalog=f.catalog();start=f.total_instructions;loads=f.get('se_overlay_loads',2)
    indices=[i+1 for i in range(64)if f.m.read(f.s['se_overlay_ids']+i)in(30,31)and f.m.read(f.s['image_slot']+i)&0x7f==0];assert len(indices)==2
    dll.gm_profile(f.s['se_overlay_active'],*indices,f.s['se_er_published'],0,f.s['se_er_published'],0);dll.pt_start(f.s['se_overlay_active'],f.s['se_overlay_ids'])
    f.render();used=f.total_instructions-start;direct=bool(dll.gm_metric(0));calls={i:int(dll.pt_calls(i))for i in range(64)if dll.pt_calls(i)};stage41=int(dll.pt_calls(255));dll.pt_start(0,0);dll.gm_profile(0,0,0,0,0,0,0)
    g.m.write(0xcfe8,0);g.m.write(0xcf90,0);startg=g.total_instructions;g.render();forced=g.total_instructions-startg
    data=f.merged();assert data==g.merged()and f.canonical()==canonical and f.catalog()==catalog
    bits,attrs,_=geos.body_model(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'))
    m,c,p=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,attrs,m,c,fonts['native8.bin'],p)
    assert f.read(0x6000,8000)==bits==g.read(0x6000,8000)and f.read(0x4000,1000)==attrs==g.read(0x4000,1000)
    assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in ('se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'))
    if caps==0:assert not set(calls)&{14,15,17,18,19,24,25,26,31}and stage41==0
    bank0=bank*65536;after=f.reu();cursor=0
    for lo,hi in [(0,64),(0x200,0xe568)]:
     assert reu[cursor:bank0+lo]==after[cursor:bank0+lo];cursor=bank0+hi
    assert reu[cursor:]==after[cursor:]
    records.append(dict(preset=preset,action=action,key_input_instructions=input_used,render_instructions=used,end_to_end_instructions=input_used+used,forced_render_instructions=forced,loads=(f.get('se_overlay_loads',2)-loads)&65535,GEC_VALID=gce[0],GTC_VALID=gtc[0],row_kind=row[16],row_inline=row[23],row_count=count,styles_nonzero=sum(bool(v)for v in row[194:194+count]),roles_nonzero=sum(bool(v)for v in row[356:356+count]),GTF_META=raw[0xea68:0xea88].hex(),direct=direct,C_entry_counts=calls,C31_stage_entries=stage41,source_sha256=hashlib.sha256(data).hexdigest()))
    print(records[-1],flush=True)
 finally:f.close();g.close()
 result=dict(status='PASS',fixture=str(base),assets={n:ident['assets'][n]for n in('gtype','type')},records=records,scope='Explicit frozen fixture; actual public key/root, forcedfull+independent rawfont pixels and full16MiB exact outside declared FE. Instruction counts, not cycles/native latency. This profile alone is not the broader candidate qualification.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-plain-typing'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())
