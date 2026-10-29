"""Actual full-page R21 PC histogram, plus the established public rendering guards."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,subprocess,sys
import test_geos_page_cost_profile as page
ROOT=page.ROOT
original=page.runner
LAST=None

def runner(out):
    global LAST
    prototype=original(out)
    cpp=out/'runner.cpp';source=cpp.read_text()
    extra=r'''
static uint64_t hp_count[4096];static bool hp_on=false;static uint16_t hp_active=0;static uint8_t hp_tag=0;
extern "C" void hp_begin(uint16_t active,uint8_t tag){hp_active=active;hp_tag=tag;memset(hp_count,0,sizeof(hp_count));hp_on=true;}
extern "C" void hp_end(){hp_on=false;}
extern "C" void hp_get(uint64_t*p){memcpy(p,hp_count,sizeof(hp_count));}
static void hp(ZeroPagePeddle*m,const decltype(zeropage_peddle_regs((ZeroPagePeddle*)nullptr))&r){if(hp_on&&r.pc>=0xa000&&r.pc<0xb000&&zeropage_peddle_read(m,hp_active)==hp_tag)hp_count[r.pc-0xa000]++;}
'''
    needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
    assert source.count(needle)==1
    source=source.replace(needle,extra+needle+'hp(m,r);')
    cpp.write_text(source)
    ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('raster-address'+ext)
    subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(page.retention.grid.VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True)
    dll=C.CDLL(str(path))
    for name,value in list(vars(prototype).items()):
        if isinstance(value,C._CFuncPtr):
            function=getattr(dll,name);function.argtypes=value.argtypes;function.restype=value.restype
    dll.hp_begin.argtypes=[C.c_uint16,C.c_uint8];dll.hp_get.argtypes=[C.c_void_p]
    begin=dll.cp_begin;end=dll.cp_end
    def start(active,n,pcs,slots,tags):
        # The existing profile targets name actual R21 as overlay-geosrow.
        i=next(i for i in range(n) if slots[i]==1 and pcs[i]==0xa010 and tags[i]==R21_TAG)
        dll.hp_begin(active,tags[i]);return begin(active,n,pcs,slots,tags)
    def stop():dll.hp_end();return end()
    dll.cp_begin=start;dll.cp_end=stop;LAST=dll
    return dll

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
    identity=json.loads((a.fixture/'freeze.json').read_text());R21_TAG=identity['names'].index('geosrow')+1
    out=ROOT/'build/geos-raster-address-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);page.runner=runner
    result=page.run(out,a.fixture.resolve());counts=(C.c_uint64*4096)();LAST.hp_get(counts)
    histogram={hex(0xa000+i):int(count)for i,count in enumerate(counts)if count}
    result['R21_PC_instruction_hits']=histogram
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R21_TOTAL',sum(counts),'TOP',sorted(histogram.items(),key=lambda x:-x[1])[:20],flush=True)
