"""Isolated actual6510 specialized80-row proof; no sharedbuild/VICE/editor edits."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,random,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR,library
from test_narrow_rows import oracle
OUT=ROOT/'build/narrow80';OUT.mkdir(exist_ok=True)
PRIORITY=[0,6,7,8,0,0,0,5,3,4,1,5,2,0]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def symbols(p):return {x[2].lstrip('.'):int(x[1],16) for l in p.read_text().splitlines() if len(x:=l.split())==3 and x[0]=='al'}
def assemble(src,out):
    subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(out),str(src)],cwd=ROOT,check=True);return out

def build():
    common=[assemble(ROOT/f'src/{n}.s',OUT/(n.replace('/','-')+'.o')) for n in ['render/narrow/font4','render/narrow/probe','tui/petscii','render/narrow/cell8']]
    code={}
    for name,mods in [('old',['row','arbitrate']),('new',['row80'])]:
        objs=[assemble(ROOT/f'src/render/narrow/{n}.s',OUT/(n+'.o')) for n in mods]
        path=OUT/(name+'.bin');subprocess.run(['ld65','-C',str(ROOT/'src/render/narrow/probe.cfg'),'-o',str(path),'-m',str(path.with_suffix('.map')),'-Ln',str(path.with_suffix('.lbl')),*map(str,objs+common[:-1])],check=True)
        code[name]=(path.read_bytes(),symbols(path.with_suffix('.lbl')))
    # Concreteproduction-space proof: the identical49B entry +cell8 +newrow
    # must finish beforeA800; narrow/native fonts retain fixed addresses.
    cfg=OUT/'fit.cfg';cfg.write_text('MEMORY { IMAGE:file=%O,start=$A000,size=$1000,type=rw,fill=yes; }\nSEGMENTS { CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro; FONT4:load=IMAGE,type=ro,start=$A800; NATIVE_FONT:load=IMAGE,type=ro,start=$AC00; }\n')
    wrapper=OUT/'fit.s';wrapper.write_text('.setcpu "6502"\n.exportzp se_nr_context,se_nr_pointer,se_bc_context,se_bc_pointer\n.export se_petscii_screen\nse_nr_context=$F0\nse_nr_pointer=$F2\nse_bc_context=$F0\nse_bc_pointer=$F2\nse_petscii_screen=$1B99\n.segment "CODE"\n.res49,0\n.segment "FONT4"\n.incbin "assets/fonts/generated/narrow4.bin"\n.segment "NATIVE_FONT"\n.incbin "assets/fonts/generated/native8.bin"\n'.replace('.res49','.res 49'))
    w=assemble(wrapper,OUT/'fit.o');subprocess.run(['ld65','-C',str(cfg),'-o',str(OUT/'fit.bin'),'-m',str(OUT/'fit.map'),'-Ln',str(OUT/'fit.lbl'),str(w),str(OUT/'row80.o'),str(common[-1])],check=True)
    fit=(OUT/'fit.bin').read_bytes();assert len(fit)==4096
    assert fit[0x800:0xC00]==(ROOT/'assets/fonts/generated/narrow4.bin').read_bytes()
    assert fit[0xC00:]==(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
    return code

def runner():
    library();cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t n80_run(ZeroPagePeddle*m,uint64_t limit){auto before=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-before;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void n80_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,uint16_t(a+i));}
extern "C" void n80_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
    ext='.dylib' if sys.platform=='darwin' else '.so';p=OUT/('runner'+ext);subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(p)],check=True)
    d=C.CDLL(str(p));d.n80_run.argtypes=[C.c_void_p,C.c_uint64];d.n80_run.restype=C.c_uint64;d.n80_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];d.n80_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return d

class Fixture:
    def __init__(self,code,dll):
        self.code,self.s=code;self.d=dll;self.m=Machine();self.m.load(0,bytes((i*73+19)&255 for i in range(0xD000)));self.m.load(0xE000,bytes((i*97+31)&255 for i in range(8192)));self.m.load(0x1000,self.code);self.before_reu=self.reu();self.calls=0
    def read(self,a,n):
        b=C.create_string_buffer(n);self.d.n80_read(self.m.handle,a,n,b);return b.raw
    def reu(self):
        b=C.create_string_buffer(2*1024*1024);self.d.n80_reu(self.m.handle,len(b),b);return b.raw
    def run(self,chars,roles,flags,palette,bg=6,encoding=0,row=0,ctx=0xC000,bitmap=0xA000,attributes=0x8000,mode=80,invalid=False,font=None,arrays=0xC200):
        if font is None:font=self.read(self.s['se_narrow_font4'],1024)
        self.m.load(self.s['se_narrow_font4'],font)
        frame=bytes([mode,row,len(chars),encoding,bg])+b''.join(p.to_bytes(2,'little') for p in [bitmap,attributes,self.s['se_narrow_font4'],arrays,arrays+0x100,arrays+0x200,arrays+0x300])
        self.m.load(ctx,frame+bytes([0xA7])*49)
        for a,v in [(arrays,chars),(arrays+0x100,roles),(arrays+0x200,flags),(arrays+0x300,palette)]:self.m.load(a,v)
        for n,v in [('pc',self.s['se_narrow_row']),('sp',0xFD),('p',0x24),('a',0),('x',ctx&255),('y',ctx>>8)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
        self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);before=self.read(0,65536);count=self.d.n80_run(self.m.handle,200000);assert count,('nonreturn',hex(self.m.regs().pc));r=self.m.regs();after=self.read(0,65536);expected=bytearray(before)
        if invalid:assert r.p&1 and r.a==0x90,(mode,row,encoding,'invalid accepted')
        else:
            assert not r.p&1 and r.a==0,(mode,row,encoding,r.a,r.p)
            bits,attrs=oracle(80,chars,roles,flags,palette,bg,encoding,font)
            expected[bitmap+row*320:bitmap+(row+1)*320]=bits;expected[attributes+row*40:attributes+(row+1)*40]=attrs
            assert after[ctx:ctx+19]==frame,'immutable19Binput changed'
            expected[ctx+19:ctx+68]=after[ctx+19:ctx+68]
        expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200]
        assert after==expected,('full64KiB/pixels/attrs/guards',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,expected)) if a!=b))
        self.calls+=1
        return after[bitmap+row*320:bitmap+(row+1)*320],after[attributes+row*40:attributes+(row+1)*40],count
    def close(self):self.m.close()

def main():
    codes=build();d=runner();old,new=Fixture(codes['old'],d),Fixture(codes['new'],d);stats=[];cases=[];rng=random.Random(0x651080);normal_font=(ROOT/'assets/fonts/generated/narrow4.bin').read_bytes()
    def compare(tag,**kw):
        kw.setdefault('font',normal_font)
        a=old.run(**kw);b=new.run(**kw);assert a[:2]==b[:2],(tag,'old/new mismatch');stats.append(dict(tag=tag,count=len(kw['chars']),row=kw.get('row',0),old=a[2],new=b[2]))
    try:
        compare('smoke',chars=b'AB',roles=bytes([1,2]),flags=bytes([0,0]),palette=bytes(range(14)))
        (OUT/'first-result.json').write_text(json.dumps(stats[-1],indent=2)+'\n')
        for encoding in [0,1]:
            for phase in range(256):
                compare(f'allnative{encoding}/{phase}',chars=bytes((phase+i)&255 for i in range(80)),roles=bytes((phase+i)%14 for i in range(80)),flags=bytes((phase+i*7)&7 for i in range(80)),palette=bytes((phase+i*3)&255 for i in range(14)),bg=phase,encoding=encoding,row=phase%25,ctx=0xC000 if phase%2 else 0xC0FB)
        cases.append('every256 native/raw value ineach80columns, allglyphs/inverse/selection/caret/roles/rows')
        for count in list(range(81))+[81,127,255]:
            compare(f'count{count}',chars=bytes(rng.randrange(256) for _ in range(count)),roles=bytes(rng.randrange(256) for _ in range(count)),flags=bytes(rng.randrange(256) for _ in range(count)),palette=bytes(rng.randrange(256) for _ in range(14)),bg=0x86,row=count%25)
        cases.append('allcounts0..80 plusclipped81/127/255; oddleftonly andunknownroles')
        # Controlledfont weights give everytwo-role majority/priority/stabletie,
        # same-rolecombined andzerobase scenarios without assuming glyphshape.
        for first in range(14):
            for second in range(14):
                for wa,wb in [(0,0),(0,1),(1,0),(16,16),(17,15),(15,17),(32,32)]:
                    font=bytearray(1024)
                    for glyph,weight in [(1,wa),(2,wb)]:
                        for bit in range(weight):font[glyph*8+bit//4]|=128>>(bit%4)
                    compare(f'vote{first}/{second}/{wa}/{wb}',chars=bytes([1,2]),roles=bytes([first,second]),flags=bytes([0,0]),palette=bytes(range(14)),encoding=1,font=bytes(font),row=(first+second)%25)
        cases.append('all196 rolepairs withzero/majority/exacttie/same-role weights')
        for _ in range(200):
            count=rng.randrange(256);font=bytes(rng.randrange(256) for _ in range(1024))
            compare('randomfont',chars=bytes(rng.randrange(256) for _ in range(count)),roles=bytes(rng.randrange(256) for _ in range(count)),flags=bytes(rng.randrange(256) for _ in range(count)),palette=bytes(rng.randrange(256) for _ in range(14)),encoding=rng.randrange(2),row=rng.randrange(25),font=font,bg=rng.randrange(256),ctx=0xC0FB)
        cases.append('randomfontlowerbits ignored, unknownflags/roles andpagecrossingframe')
        for bitmap,attributes in [(0x2000,0x4000),(0x4000,0x8000),(0x6000,0x400),(0x8000,0x4000),(0xA000,0x8000),(0x2000,0xC000)]:
            for row in [0,24]:
                compare('legaloutputbase',chars=b'A'*80,roles=bytes([1])*80,flags=bytes([5])*80,palette=bytes(range(14)),bitmap=bitmap,attributes=attributes,row=row,ctx=0x9000 if attributes==0xC000 else 0xC000,arrays=0x9200 if attributes==0xC000 else 0xC200)
        invalids=[dict(mode=x) for x in [0,40,60,61,79,81,255]]+[dict(row=x) for x in [25,255]]+[dict(encoding=x) for x in [2,255]]+[dict(bitmap=x) for x in [0,0x1000,0x2001,0x4001,0xC000,0xE000,0xFFFF]]+[dict(attributes=x) for x in [0,0x100,0xC400,0xC600,0xFFFF,0x8001]]
        for change in invalids:
            new.run(chars=b'A',roles=b'\0',flags=b'\0',palette=bytes(range(14)),invalid=True,**change)
        assert old.reu()==old.before_reu and new.reu()==new.before_reu,'whole2MiBREU changed'
        full=[s for s in stats if s['count']==80];best=min(s['old']/s['new'] for s in full);sizes={n:len(c[0]) for n,c in codes.items()}
        segments=subprocess.check_output(['od65','--dump-segments',str(OUT/'row80.o')],text=True)
        (OUT/'row80-segments.txt').write_text(segments)
        measured={name:int(size) for name,size in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',segments,re.S)}
        assert all(measured.get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE'])
        module_bytes=measured['CODE']+measured['RODATA'];assert module_bytes+49+199<=2048
        assert best>1.9,'specialization must provide a material measured full-row improvement'
        assert all(s['new']<s['old'] for s in full)
        result=dict(status='passed',rows=len(stats),invalid_frames=len(invalids),pixels=len(stats)*2560,attributes=len(stats)*40,cases=cases,old_peak=max(s['old'] for s in stats),new_peak=max(s['new'] for s in stats),full80_min_instruction_speedup=best,full80_mean_old=sum(s['old'] for s in full)/len(full),full80_mean_new=sum(s['new'] for s in full)/len(full),full_RAM_guard_bytes=65536,whole_REU_guard_bytes=2097152,shim_guard_bytes=1024,immutable_input_bytes=19,caller_frame_bytes=68,loaned_ZP_bytes=4,new_resident_BSS=0,new_resident_ZP=0,specialized_CODE_bytes=measured['CODE'],specialized_RODATA_bytes=measured['RODATA'],specialized_total_bytes=module_bytes,pre_font_spare_bytes=2048-module_bytes-49-199,fit_image_bytes=4096,font_addresses=[0xA800,0xAC00],private_binary_bytes=sizes,source_sha256={n:sha(ROOT/n) for n in ['src/render/narrow/row80.s','src/render/narrow/row.s','src/render/narrow/arbitrate.s','src/render/narrow/api.inc','tests/test_narrow80.py','tests/test_narrow_rows.py']},limits=['ActualCPU instructions/pixels/attrs/guards, not nativecycles/VIC/readability/editorintegration.','No sharedmake/productionruntime changed; onlynewmodule/privatecapsules.'])
        (OUT/'rows.json').write_text(json.dumps(stats,indent=2)+'\n');(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:old.close();new.close()
if __name__=='__main__':main()
