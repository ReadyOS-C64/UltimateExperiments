"""Instruction-observed owner2 producer RAM lifetime; no product instrumentation."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,ctypes as C,inspect
import test_grid_producer_live_authority as authority
import test_grid_modes as grid
ROOT=authority.ROOT
BASE=ROOT/'build/grid-geowrite-live-dispatch-proof/20261025T205136544396Z/fixture'
def instrument(out):
 dll=authority.fold.retention.runner(out);cpp=out/'runner.cpp';s=cpp.read_text();symbols=json.load(open(BASE/'build/editor-report.json'))['symbols'];owner=symbols['se_f_owner'];active=symbols['se_overlay_active'];copy=symbols['se_reu_copy'];c64=symbols['se_reu_c64'];length=symbols['se_reu_length']
 code='''
static uint32_t ram_bad=0,ram_stores=0,ram_dma=0;static uint8_t ram_pcs[65536];
static uint16_t word(ZeroPagePeddle*m,uint16_t a){return zeropage_peddle_read(m,a)|(zeropage_peddle_read(m,uint16_t(a+1))<<8);}
static bool watched(uint16_t a){return(a>=0x8a00&&a<0x8a80)||a==0x89c3;}
static void ram_before(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);if(zeropage_peddle_read(m,OWNER)!=2)return;
 auto id=zeropage_peddle_read(m,ACTIVE);uint16_t a=0;bool store=true;auto op=zeropage_peddle_read(m,r.pc);auto lo=zeropage_peddle_read(m,r.pc+1);auto abs=word(m,r.pc+1);
 switch(op){case 0x85:case 0x86:case 0x84:case 0x06:case 0x46:case 0x26:case 0x66:case 0xc6:case 0xe6:a=lo;break;
 case 0x8d:case 0x8e:case 0x8c:case 0x0e:case 0x4e:case 0x2e:case 0x6e:case 0xce:case 0xee:a=abs;break;
 case 0x95:case 0x94:case 0x16:case 0x56:case 0x36:case 0x76:case 0xd6:case 0xf6:a=uint8_t(lo+r.x);break;
 case 0x96:a=uint8_t(lo+r.y);break;
 case 0x9d:case 0x1e:case 0x5e:case 0x3e:case 0x7e:case 0xde:case 0xfe:a=abs+r.x;break;
 case 0x99:a=abs+r.y;break;
 case 0x81:{uint8_t z=lo+r.x;a=zeropage_peddle_read(m,z)|(zeropage_peddle_read(m,uint8_t(z+1))<<8);break;}
 case 0x91:a=(zeropage_peddle_read(m,lo)|(zeropage_peddle_read(m,uint8_t(lo+1))<<8))+r.y;break;
 default:store=false;}
 if(store&&watched(a)){ram_stores++;ram_pcs[r.pc]=1;if(id!=14||r.pc<0xa000||r.pc>=0xb000)ram_bad++;}
 if(r.pc==COPY&&r.a==1){auto start=word(m,C64);auto n=word(m,LENGTH);if(start<0x8a80&&uint32_t(start)+(n?n:65536)>0x8a00){ram_dma++;ram_pcs[r.pc]=1;if(id!=14||start!=0x8a00||n!=128)ram_bad++;}}
}
extern "C" uint32_t ram_get(int i){return i==0?ram_bad:i==1?ram_stores:ram_dma;}
extern "C" void ram_pc_get(uint8_t*p){memcpy(p,ram_pcs,65536);}
'''
 for k,v in [('OWNER',owner),('ACTIVE',active),('COPY',copy),('C64',c64),('LENGTH',length)]:code=code.replace(k,str(v))
 s=s.replace('static void step(ZeroPagePeddle*m){',code+'\nstatic void step(ZeroPagePeddle*m){ram_before(m);',1);cpp.write_text(s);lib=out/'ram-lifetime.dylib';subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(grid.VENDOR),cpp,ROOT/'build/libse_peddle.dylib','-o',lib],check=True);pd=C.CDLL(str(lib))
 for name in ('gm_run','gm_idle','gm_read','gm_reu','gm_rom','gm_rom_count','gm_profile','gm_metric','fr_begin','fr_end','fr_bad','fr_writes','fr_mask'):
  fn=getattr(pd,name);old=getattr(dll,name);fn.argtypes=old.argtypes;fn.restype=old.restype
 pd.ram_get.argtypes=[C.c_int];pd.ram_get.restype=C.c_uint32;pd.ram_pc_get.argtypes=[C.c_void_p];return pd
if __name__=='__main__':
 out=ROOT/'build/grid-producer-ram-lifetime'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);pd=instrument(out);src=inspect.getsource(authority.run).replace('dll=fold.retention.runner(out)','dll=pd');ns=dict(authority.__dict__,pd=pd);exec(compile(src,__file__+':same-authority-cases','exec'),ns);r=ns['run'](out,BASE);assert pd.ram_get(0)==0;pcs=C.create_string_buffer(65536);pd.ram_pc_get(pcs);r['lifetime']=dict(status='passed',CPU_stores=pd.ram_get(1),DMAs=pd.ram_get(2),unexpected_writers=pd.ram_get(0),writer_PCs=[hex(i)for i,v in enumerate(pcs.raw)if v],scope='Actual normal documented6510 store/RMW address modes plus allREUcopy writes into SC_H128/LIVE duringowner2. Everyobservedwriter isR14; direct fault-injection hostwrites excluded. Full C14inline+C15lexer+R14/source path exercised by15completeclassifiedframes/13faults. Static scratch allocation accompanies this dynamic proof; not proof allpossibleprograms.');(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r['lifetime'])
