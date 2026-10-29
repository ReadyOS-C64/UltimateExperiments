"""Actual6510 one-row narrow renderer, independent every-pixel/tile oracle.

Builds only build/narrow-rows; no editor build, VICE, hardware or document input.
The tiny local native runner only batches the existing Peddle single-step API.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,random,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
OUT=ROOT/'build/narrow-rows';OUT.mkdir(exist_ok=True)
SOURCES=['render/narrow/row','render/narrow/arbitrate','render/narrow/font4','render/narrow/font5','render/narrow/probe','tui/petscii']
PRIORITY=[0,6,7,8,0,0,0,5,3,4,1,5,2,0]
SIZE=68
def build():
    objects=[]
    for name in SOURCES:
        out=OUT/(name.replace('/','-')+'.o');objects.append(str(out));subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(out),str(ROOT/'src'/Path(name+'.s'))],cwd=ROOT,check=True)
    subprocess.run(['ld65','-C',str(ROOT/'src/render/narrow/probe.cfg'),'-o',str(OUT/'probe.bin'),'-m',str(OUT/'probe.map'),'-Ln',str(OUT/'probe.lbl'),*objects],check=True)
    return {x[2].lstrip('.'):int(x[1],16) for line in (OUT/'probe.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}
def converter(v):
    if v<32 or 128<=v<160:return 63
    if v<64:return v
    if v<96:return v&63
    if v<128:return (v&31)|64
    if 192<=v<224:return (v&63)|64
    if v==255:return 94
    return (v&63)|96
def oracle(mode,chars,roles,flags,palette,bg,encoding,font):
    width=5 if mode==60 else 4;origin=10 if mode==60 else 0;bitmap=bytearray(320);weights=[[0]*14 for _ in range(40)]
    for col,value in enumerate(chars[:mode]):
        code=(value&127) if encoding else converter(value);reverse=bool(flags[col]&1 or encoding and value&128);invert=bool(flags[col]&6);role=roles[col] if roles[col]<14 else 0
        for gy in range(8):
            for gx in range(width):
                x=origin+col*width+gx;base=bool(font[code*8+gy]&(128>>gx))^reverse;weights[x//8][role]+=base
                if base^invert:bitmap[(x//8)*8+gy]|=128>>(x%8)
    attributes=bytes(((palette[max(range(14),key=lambda r:(counts[r],PRIORITY[r] if counts[r] else 0,-r))]&15)<<4)|(bg&15) for counts in weights)
    return bytes(bitmap),attributes

class Fixture:
    def __init__(self,s):
        self.s=s;self.m=Machine();self.m.load(0,bytes((i*73+19)&255 for i in range(0xD000)));self.m.load(0x1000,(OUT/'probe.bin').read_bytes());self.calls=0;self.peak_cycles=0;self.peak_instructions=0;self.mode_peak={};self.last_instructions=0;self.reads=0
        # Native batching changes neither CPU semantics nor returned state.
        cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t nr_run(ZeroPagePeddle*m,uint64_t limit){auto start=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-start;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void nr_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void nr_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
        ext='.dylib' if sys.platform=='darwin' else '.so';lib=OUT/('runner'+ext);subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(lib)],check=True)
        self.runner=C.CDLL(str(lib));self.runner.nr_run.argtypes=[C.c_void_p,C.c_uint64];self.runner.nr_run.restype=C.c_uint64;self.runner.nr_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.runner.nr_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
        self.reu_before=self.reu()
    def close(self):self.m.close()
    def read(self,a,n):
        b=C.create_string_buffer(n);self.runner.nr_read(self.m.handle,a,n,b);return b.raw
    def reu(self):
        b=C.create_string_buffer(512*1024);self.runner.nr_reu(self.m.handle,len(b),b);return b.raw
    def call(self,name,ctx):
        for name_,v in [('pc',self.s[name]),('sp',0xFD),('a',0),('x',ctx&255),('y',ctx>>8),('p',0x24)]:getattr(self.m.lib,'zeropage_peddle_set_'+name_)(self.m.handle,v)
        self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);before=self.m.regs();n=self.runner.nr_run(self.m.handle,200000);assert n,(name,'nonreturn',hex(self.m.regs().pc));r=self.m.regs();self.peak_cycles=max(self.peak_cycles,r.cycles-before.cycles);self.peak_instructions=max(self.peak_instructions,n);self.calls+=1;self.last_instructions=n;return r
    def render(self,mode,chars,roles,flags,palette,bg=6,encoding=0,row=0,ctx=0xC000,bitmap=0xA000,attributes=0x8000,invalid=False):
        data=bytearray([mode,row,len(chars),encoding,bg]);font_name='se_narrow_font5' if mode==60 else 'se_narrow_font4'
        for ptr in [bitmap,attributes,self.s[font_name],0x8400,0x8500,0x8600,0x8700]:data+=ptr.to_bytes(2,'little')
        assert len(data)==19
        self.m.load(ctx,data+bytes([0xA7])*(SIZE-len(data)));self.m.load(0x8400,chars);self.m.load(0x8500,roles);self.m.load(0x8600,flags);self.m.load(0x8700,palette)
        before=self.read(0,0xD000);r=self.call('se_narrow_row',ctx);after=self.read(0,0xD000);expected=bytearray(before)
        if invalid:assert r.p&1 and r.a==0x90
        else:
            assert not r.p&1 and r.a==0,(mode,row,encoding,r.a,r.p)
            self.mode_peak[mode]=max(self.mode_peak.get(mode,0),self.last_instructions)
            font=(ROOT/'assets/fonts/generated'/('narrow5.bin' if mode==60 else 'narrow4.bin')).read_bytes();bits,attrs=oracle(mode,chars,roles,flags,palette,bg,encoding,font);expected[bitmap+row*320:bitmap+(row+1)*320]=bits;expected[attributes+row*40:attributes+(row+1)*40]=attrs
            assert after[ctx:ctx+19]==data,'immutable input header changed'
            expected[ctx+19:ctx+SIZE]=after[ctx+19:ctx+SIZE]
        # Only the caller's frame, four loanedZP bytes, and CPU stack may change.
        expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200]
        assert after==expected,(mode,row,encoding,'RAM/pixel/tile/guard',next((hex(i),hex(a),hex(b)) for i,(a,b) in enumerate(zip(after,expected)) if a!=b))
        return r

def main():
    s=build();f=Fixture(s);rows=invalid=arb=0;coverage={};rng=random.Random(0x65106080)
    try:
        for mode in [60,80]:
            for encoding in [0,1]:
                for phase in range(256):
                    chars=bytes((phase+i)&255 for i in range(mode));roles=bytes((phase+i)%14 for i in range(mode));flags=bytes((phase+i*7)&7 for i in range(mode));palette=bytes((phase+i*3)&255 for i in range(14))
                    f.render(mode,chars,roles,flags,palette,bg=phase&15,encoding=encoding,row=phase%25,ctx=0xC000 if phase%2 else 0xC0FB);rows+=1
                coverage[f'{mode}/{encoding}']='Every256 input value in every column; all128 glyphs, raw inverse range, native mapping, role colors, all8 inverse/selection/caret flag combinations; all25 destination rows.'
        for mode in [60,80]:
            for count in [0,1,mode-1,mode,mode+1,255]:
                chars=bytes(rng.randrange(256) for _ in range(count));roles=bytes(rng.randrange(256) for _ in chars);flags=bytes(rng.randrange(256) for _ in chars);palette=bytes(rng.randrange(256) for _ in range(14))
                for row in [0,24]:f.render(mode,chars,roles,flags,palette,bg=0x86,row=row);rows+=1
        # Output validation must refuse before any frame/output/source mutation.
        for changes in [dict(mode=0),dict(mode=40),dict(mode=61),dict(mode=255),dict(row=25),dict(row=255),dict(encoding=2),dict(bitmap=0),dict(bitmap=0x1000),dict(bitmap=0x2001),dict(bitmap=0xC000),dict(bitmap=0xE000),dict(attributes=0),dict(attributes=0xC400),dict(attributes=0xC600),dict(attributes=0xFFFF),dict(attributes=0x8001)]:
            kw=dict(mode=80,chars=b'A',roles=bytes([0]),flags=bytes([0]),palette=bytes(range(14)),invalid=True);kw.update(changes);f.render(**kw);invalid+=1
        # Direct arbitration: isolate majority, tie priority, stable equal-rank
        # ties and zero-ink role presence from incidental shapes of a font.
        palette=bytes(range(14));ctx=0xC000
        for first in range(14):
            for second in range(14):
                for wa,wb in [(0,0),(32,32),(33,31)]:
                    hist=[0]*14;hist[first]+=wa;hist[second]+=wb;chosen=max(range(14),key=lambda i:(hist[i],PRIORITY[i] if hist[i] else 0,-i));frame=bytearray(SIZE);frame[4]=6;frame[17:19]=(0x8700).to_bytes(2,'little');frame[21:23]=(0x8000).to_bytes(2,'little');frame[44:58]=bytes(hist);f.m.load(ctx,frame);f.m.load(0x8700,palette);f.m.write(0xF0,ctx&255);f.m.write(0xF1,ctx>>8);before=f.read(0,0xD000);r=f.call('se_narrow_resolve_tile',ctx);after=f.read(0,0xD000);expected=bytearray(before);expected[0x8000]=(chosen<<4)|6;expected[ctx+19:ctx+SIZE]=after[ctx+19:ctx+SIZE];expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200];assert after==expected,(first,second,wa,wb,'arbitration');arb+=1
        assert f.reu()==f.reu_before,'REU changed'
        result=dict(status='passed',row_calls=rows,invalid_frames=invalid,arbitration_cases=arb,total_CPU_calls=f.calls,pixels_checked=rows*2560,attributes_checked=rows*40,full_RAM_guard_bytes_per_call=0xD000,shim_bytes=1024,REU_bytes_unchanged=512*1024,caller_frame_bytes=SIZE,loaned_ZP_bytes=4,new_resident_BSS_bytes=0,new_resident_ZP_bytes=0,font_bytes_each=1024,font4_sha256=hashlib.sha256((ROOT/'assets/fonts/generated/narrow4.bin').read_bytes()).hexdigest(),font5_sha256=hashlib.sha256((ROOT/'assets/fonts/generated/narrow5.bin').read_bytes()).hexdigest(),peak_call_cycles=f.peak_cycles or None,cycle_counter_note='Existing Peddle wrapper does not advance its exported cycle field; no emulated-cycle timing claim.',peak_call_instructions=f.peak_instructions,peak_row_instructions_by_mode=f.mode_peak,coverage=coverage,limits='CPU instruction/pixel/tile proof only; not VIC capture, readability, editor integration or mode-transition proof. Full-row CPU cost reported without claiming a production timing gate.')
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        e=ROOT/'agentsworking/evidence/M6'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-narrow-rows');e.mkdir(parents=True)
        for p in OUT.iterdir():
            if p.is_file() and p.suffix in ['.json','.map','.lbl','.bin','.cpp']:shutil_copy(p,e/p.name)
        with zipfile.ZipFile(e/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in SOURCES:
                p=ROOT/'src'/Path(name+'.s');z.write(p,p.relative_to(ROOT))
            for name in ['src/render/narrow/api.inc','src/render/narrow/probe.cfg','tests/test_narrow_rows.py','tools/peddle.py','assets/fonts/generated/manifest.json']:z.write(ROOT/name,name)
        print('EVIDENCE',e)
    finally:f.close()
def shutil_copy(a,b):
    import shutil
    shutil.copyfile(a,b)
if __name__=='__main__':main()
