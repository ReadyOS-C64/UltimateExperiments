"""Observed foreground stack high-water on an immutable editor CPU fixture.

Clones the private generated soak runner; never patches the CPU library/product.
Every instruction executed through gm_run/gm_idle is sampled before and after.
The existing soak supplies actual public commands plus canonical/REU guards.
No IRQ/NMI/KERNAL execution or hardware worst-case bound is inferred.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, json, subprocess, sys, zipfile
import test_editor_soak as soak
ROOT=soak.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T071324227584Z/fixture'


def runner(out):
    reference=soak_runner(out)
    path=out/'runner.cpp';source=path.read_text()
    needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
    assert source.count(needle)==1
    extra=r'''
static uint16_t sb_active=0,sb_mode=0,sb_job=0;
static uint64_t sb_steps=0,sb_min=255,sb_pc=0,sb_next=0,sb_r=0,sb_c=0,sb_m=0,sb_j=0,sb_opcode=0,sb_wrap=0;
static uint8_t sb_stack[256];
extern "C" void sb_config(uint16_t a,uint16_t m,uint16_t j){sb_active=a;sb_mode=m;sb_job=j;}
extern "C" void sb_begin(){sb_steps=0;sb_min=255;sb_pc=sb_next=sb_r=sb_c=sb_m=sb_j=sb_opcode=sb_wrap=0;}
static void sb_sample(ZeroPagePeddle*m,uint16_t pc,uint8_t opcode){auto r=zeropage_peddle_regs(m);
 if(r.sp<sb_min){sb_min=r.sp;sb_pc=pc;sb_next=r.pc;sb_opcode=opcode;
  sb_r=zeropage_peddle_read(m,sb_active);sb_c=zeropage_peddle_read(m,sb_active+1);
  sb_m=zeropage_peddle_read(m,sb_mode);sb_j=zeropage_peddle_read(m,sb_job);
  for(int i=0;i<256;i++)sb_stack[i]=zeropage_peddle_read(m,0x100+i);}}
extern "C" uint64_t sb_info(int i){uint64_t v[]={sb_steps,sb_min,sb_pc,sb_next,sb_r,sb_c,sb_m,sb_j,sb_opcode,sb_wrap};return v[i];}
extern "C" void sb_bytes(uint8_t*out){memcpy(out,sb_stack,256);}
'''
    source=source.replace(needle,extra+needle+'sb_sample(m,r.pc,zeropage_peddle_read(m,r.pc));')
    step='zeropage_peddle_step_instruction(m);'
    assert source.count(step)==1
    source=source.replace(step,'''auto sb_op=zeropage_peddle_read(m,r.pc);
 if((sb_op==0x20 && r.sp<2)||((sb_op==0x48||sb_op==0x08)&&r.sp==0))sb_wrap++;
 zeropage_peddle_step_instruction(m);sb_steps++;sb_sample(m,r.pc,sb_op);''')
    path.write_text(source)
    suffix='.dylib' if sys.platform=='darwin' else '.so';dllpath=out/('stack-runner'+suffix)
    subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',
        '-I'+str(soak.fold.geos.grid.VENDOR),str(path),str(ROOT/('build/libse_peddle'+suffix)),'-o',str(dllpath)],check=True)
    dll=C.CDLL(str(dllpath))
    for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu',
                 'fr_begin','fr_mask','fr_bad','fr_writes','fr_end'):
        getattr(dll,name).argtypes=getattr(reference,name).argtypes
        getattr(dll,name).restype=getattr(reference,name).restype
    dll.sb_config.argtypes=[C.c_uint16]*3;dll.sb_info.argtypes=[C.c_int];dll.sb_info.restype=C.c_uint64
    dll.sb_bytes.argtypes=[C.c_void_p]
    calibrate(dll,out)
    return dll


def calibrate(dll,out):
    """Known two-level JSR/PHA/PHP shape checks post-instruction minima."""
    m=soak.fold.geos.grid.Machine()
    try:
        m.load(0x0f80,bytes([0x20,0x90,0x0f,0x60]))
        m.load(0x0f90,bytes([0x48,0x08,0x28,0x68,0x60]))
        for name,value in [('pc',0x0f80),('sp',0xfd),('p',0x24)]:
            getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
        m.write(0x1fe,0xfe);m.write(0x1ff,2)
        dll.sb_config(0,0,0);dll.sb_begin();used=dll.gm_run(m.handle,32)
        v=[dll.sb_info(i)for i in range(10)]
        assert used==v[0]==7 and v[1]==0xf9 and v[2]==0x0f91 and v[8]==8 and not v[9],v
        (out/'calibration.json').write_text(json.dumps(dict(status='passed',instructions=used,
            minimum_sp=v[1],observed_bytes=255-v[1],expected_bytes=6,
            explanation='Two synthetic caller bytes + JSR2 + PHA1 + PHP1; min recorded immediately after PHP.'),indent=2)+'\n')
    finally:m.close()


soak_runner=soak.runner
Base=soak.fold.Fixture
class Fixture(Base):
    """Keep every existing assertion; add observation at the call boundary."""
    def __init__(self,*args,**kw):
        self.measured=False;self.context='setup';self.observed={};self.observed_steps=0;self.observed_calls=0;self.stack_peak=None
        super().__init__(*args,**kw)
        self.dll.sb_config(*[self.s[n] for n in ('se_overlay_active','se_mode','se_e_job')])
    def source(self,data):
        self.measured=False
        super().source(data)
        self.measured=True
    def fast_call(self,address,a=0,x=0,y=0,limit=8_000_000):
        measuring=self.measured
        if measuring:self.dll.sb_begin()
        result=super().fast_call(address,a,x,y,limit)
        if measuring:
            v=[self.dll.sb_info(i)for i in range(10)]
            assert v[0]==result[1],('instruction-sampling gap',v[0],result[1])
            assert not v[9],('hardware stack wrap during push',v)
            sample=dict(case=self.context,call_address=address,argument=a,instructions=v[0],minimum_sp=v[1],
                stack_bytes_from_ff=255-v[1],instruction_pc=v[2],resulting_pc=v[3],active_r=v[4],active_c=v[5],mode=v[6],job=v[7],opcode=v[8])
            self.observed_steps+=v[0];self.observed_calls+=1
            key=(self.context,address,a);old=self.observed.get(key)
            if old is None or sample['minimum_sp']<old['minimum_sp']:self.observed[key]=sample
            if self.stack_peak is None or sample['minimum_sp']<self.stack_peak['minimum_sp']:
                buf=C.create_string_buffer(256);self.dll.sb_bytes(buf)
                self.stack_peak=dict(sample,stack_page_hex=buf.raw.hex())
        return result
    def command(self,c,*args,**kw):
        old=self.context;self.context='public-command-'+str(c)
        try:return super().command(c,*args,**kw)
        finally:self.context=old
    def key(self,c,*args,**kw):
        old=self.context;self.context='public-key-'+hex(c)
        try:return super().key(c,*args,**kw)
        finally:self.context=old
    def close(self):
        if self.stack_peak is not None:
            identity=json.loads((self.out/'fixture/freeze.json').read_text())
            names=identity['names'];peak=self.stack_peak
            for sample in [peak]+list(self.observed.values()):
                for field in ('active_r','active_c'):
                    index=sample[field];name=names[index-1]if index else None
                    sample[field+'_catalog_index']=index
                    sample[field+'_name']=name
                    sample[field+'_module_id']=(self.out/'fixture/build/overlays'/(name+'.seo')).read_bytes()[6]if name else 0
            result=dict(status='observed',identity=identity,measured_calls=self.observed_calls,
                measured_instructions=self.observed_steps,peak=peak,cases=list(self.observed.values()),
                measurement='All instructions in every measured gm_run call, sampled before and after each executed instruction. Each public-call harness starts SP=$FD with two synthetic return bytes; usage is reported from$FF including those two bytes. Canonical fixture initialization and IEC/font host seams are excluded.',
                limits='CPU interrupts masked (P=$24), noIRQ/NMI/KERNAL ROM execution; no proof of native worst-case stack depth. Per-case calls reset SP; this is foreground service nesting, not a resumable interrupted CPU continuation.')
            (self.out/'stack-result.json').write_text(json.dumps(result,indent=2)+'\n')
            print('STACK',json.dumps({k:result[k]for k in ('measured_calls','measured_instructions','peak')}),flush=True)
        super().close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT)
    p.add_argument('--rounds',type=int,default=128);p.add_argument('--seed',type=lambda s:int(s,0),default=0x53454F53)
    a=p.parse_args()
    if not a.run:print('Prepared per-instruction foregroundSP measurement; --run uses immutable07132439asset fixture.');return
    out=ROOT/'build/editor-stack'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    soak.runner=runner;soak.fold.Fixture=Fixture
    print('RUN',out,flush=True)
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
    soak.run(out,a.fixture.resolve(),a.rounds,a.seed)
    result=json.loads((out/'stack-result.json').read_text());assert result['measured_instructions']>0
    assert json.loads((out/'result.json').read_text())['status']=='passed'
    result['status']='passed';(out/'stack-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',out,flush=True)

if __name__=='__main__':main()
