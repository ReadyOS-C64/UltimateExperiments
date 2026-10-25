"""Actual6510 packed BSW9 measure/raster oracle, isolated from the editor/VIC."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,struct,subprocess,sys,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
OUT=ROOT/'build/geos-glyphs';OUT.mkdir(exist_ok=True)
SOURCES=['render/geos/measure','render/geos/glyph','render/geos/assets','render/geos/probe','tui/petscii']
SIZE=77
def digest(data):return hashlib.sha256(data).hexdigest()
def build():
    objs=[]
    for name in SOURCES:
        o=OUT/(name.replace('/','-')+'.o');objs.append(str(o));subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(o),str(ROOT/'src'/Path(name+'.s'))],cwd=ROOT,check=True)
    subprocess.run(['ld65','-C',str(ROOT/'src/render/geos/probe.cfg'),'-o',str(OUT/'probe.bin'),'-m',str(OUT/'probe.map'),'-Ln',str(OUT/'probe.lbl'),*objs],check=True)
    return {x[2].lstrip('.'):int(x[1],16) for line in (OUT/'probe.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}
def native(v):
    if v<32 or 128<=v<160:return 63
    if v<64:return v
    if v<96:return v&63
    if v<128:return (v&31)|64
    if 192<=v<224:return (v&63)|64
    if v==255:return 94
    return (v&63)|96
MAP={0:64,**{i:i+96 for i in range(1,27)},27:91,29:93,**{i:i for i in range(32,64)},**{i:i for i in range(65,91)}}

class Fixture:
    def __init__(self,s):
        self.s=s;self.m=Machine();self.m.load(0,bytes((i*37+11)&255 for i in range(0xD000)));self.m.load(0x1000,(OUT/'probe.bin').read_bytes());self.calls=0;self.peak={}
        manifest=json.loads((ROOT/'assets/fonts/generated/manifest.json').read_text());self.packed=(ROOT/'assets/fonts/generated/bsw9-original.bin').read_bytes();self.widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();self.expanded=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();rom=Path(manifest['native_source']).read_bytes();assert digest(rom)==manifest['native_sha256'];self.fallback=rom[2048:3072]
        for n,b in [('bsw9-original.bin',self.packed),('bsw9-widths.bin',self.widths),('bsw9.bin',self.expanded)]:assert digest(b)==manifest['files'][n]
        assert struct.unpack('<BHBHH',self.packed[:8])==(6,60,9,8,204) and len(self.packed)==744
        offsets=struct.unpack('<98H',self.packed[8:204]);assert all(a<=b<=480 for a,b in zip(offsets,offsets[1:]))
        # Decode packed bits independently and prove equivalence to the existing
        # M1 expanded asset, including its explicit graphics fallback mapping.
        self.words={}
        for code in range(128):
            rows=[]
            if code in MAP:
                start,end=offsets[MAP[code]-32:MAP[code]-30];assert self.widths[code]==end-start
                for y in range(9):rows.append(sum(bool(self.packed[204+y*60+(start+x)//8]&(128>>((start+x)%8)))<<(15-x) for x in range(end-start)))
            else:
                assert self.widths[code]==8;rows=[(self.fallback[code*8+y]<<8) if y<8 else 0 for y in range(9)]
            assert b''.join(x.to_bytes(2,'big') for x in rows)==self.expanded[code*18:(code+1)*18],('packed/existing-expanded',code);self.words[code]=rows
        self.m.load(0x8800,self.fallback);self.m.load(0x9000,self.packed);self.m.load(0x9400,self.widths)
        cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t gg_run(ZeroPagePeddle*m,uint64_t limit){auto start=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-start;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void gg_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void gg_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
        ext='.dylib' if sys.platform=='darwin' else '.so';lib=OUT/('runner'+ext);subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(lib)],check=True)
        self.r=C.CDLL(str(lib));self.r.gg_run.argtypes=[C.c_void_p,C.c_uint64];self.r.gg_run.restype=C.c_uint64;self.r.gg_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.r.gg_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];self.reu_before=self.reu()
    def close(self):self.m.close()
    def read(self,a,n):
        b=C.create_string_buffer(n);self.r.gg_read(self.m.handle,a,n,b);return b.raw
    def reu(self):
        b=C.create_string_buffer(512*1024);self.r.gg_reu(self.m.handle,len(b),b);return b.raw
    def call(self,name,ctx):
        for k,v in [('pc',self.s[name]),('sp',0xFD),('a',0),('x',ctx&255),('y',ctx>>8),('p',0x24)]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
        self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);n=self.r.gg_run(self.m.handle,20000);assert n,(name,'did not return',hex(self.m.regs().pc));self.peak[name]=max(self.peak.get(name,0),n);self.calls+=1;return self.m.regs()
    def oracle(self,value,encoding,style,flags,clip):
        code=value&127 if encoding else native(value);reverse=bool(flags&1 or encoding and value&128);width=self.widths[code];advance=width+(style&1)+((style&2));cell=((1<<advance)-1)<<(16-advance);left,right,top,bottom=clip;mask=sum(1<<(15-x) for x in range(advance) if left<=x<right);ink=[];coverage=[]
        for y,word in enumerate(self.words[code]):
            if style&1:word|=word>>1
            if style&2:word>>=2 if y<3 else 1 if y<6 else 0
            if reverse:word^=cell
            ink.append((word&mask) if top<=y<bottom else 0);coverage.append(mask if top<=y<bottom else 0)
        return dict(code=code,kind=int(code not in MAP),width=width,advance=advance,ink=b''.join(x.to_bytes(2,'big') for x in ink),coverage=b''.join(x.to_bytes(2,'big') for x in coverage))
    def check(self,value,encoding=0,style=0,flags=0,clip=(0,16,0,9),measure=False,ctx=0xC000,error=None,font=None,widths=None):
        frame=bytearray([value,encoding,style,flags]);frame+=(self.s['se_geos_packed'] if font is None else font).to_bytes(2,'little');frame+=(self.s['se_geos_widths'] if widths is None else widths).to_bytes(2,'little');frame+=(0x8800).to_bytes(2,'little');frame+=bytes(clip);assert len(frame)==14
        self.m.load(ctx,frame+bytes([0xA7])*(SIZE-14));before=self.read(0,0xD000);r=self.call('se_geos_measure' if measure else 'se_geos_glyph',ctx);after=self.read(0,0xD000);expected=bytearray(before)
        assert after[ctx:ctx+14]==frame
        if error is not None:assert r.p&1 and r.a==error and after[ctx+14]==0,(value,'expected refusal',r.a,r.p,after[ctx+14])
        else:
            assert not r.p&1 and r.a==0,(value,encoding,style,clip,'CPU error',r.a,r.p)
            o=self.oracle(value,encoding,style,flags,clip);assert after[ctx+14:ctx+21]==bytes([1 if measure else 2,o['code'],o['kind'],o['width'],o['advance'],6,9]),(value,encoding,style,flags,'metrics')
            if measure:assert after[ctx+21:ctx+57]==bytes([0xA7])*36,'measure painted raster outputs'
            else:
                assert after[ctx+21:ctx+39]==o['ink'],(value,encoding,style,flags,clip,'ink',after[ctx+21:ctx+39].hex(),o['ink'].hex())
                assert after[ctx+39:ctx+57]==o['coverage'],(value,encoding,style,flags,clip,'coverage')
        expected[ctx+14:ctx+SIZE]=after[ctx+14:ctx+SIZE];expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200]
        assert after==expected,('fonts/source/shim/RAM guard',value,next((hex(i),hex(a),hex(b)) for i,(a,b) in enumerate(zip(after,expected)) if a!=b));return r

def main():
    s=build();f=Fixture(s);measures=rasters=clips=invalid=corrupt=0
    try:
        for encoding in [0,1]:
            for value in range(256):
                for style in range(4):
                    for flags in [0,1]:
                        ctx=0xC000 if (value+style)%2 else 0xC0FB
                        f.check(value,encoding,style,flags,measure=True,ctx=ctx);measures+=1
                        f.check(value,encoding,style,flags,ctx=ctx);rasters+=1
        # Every horizontal/vertical boundary, including empty/inverted windows,
        # on native graphic fallbacks and descenders under all four styles.
        for style in range(4):
            for left in range(17):
                for right in range(17):f.check([0x47,0x5C,0x5E,0xD1][(left+right)%4],style=style,flags=(left+right)&1,clip=(left,right,0,9));clips+=1
            for top in range(10):
                for bottom in range(10):f.check([0x47,0x4A,0x50,0x51,0x59][(top+bottom)%5],style=style,flags=(top+bottom)&1,clip=(0,16,top,bottom));clips+=1
        for kw in [dict(encoding=2),dict(encoding=255),dict(style=4),dict(style=255),dict(clip=(17,16,0,9)),dict(clip=(0,17,0,9)),dict(clip=(0,16,10,9)),dict(clip=(0,16,0,10))]:f.check(0x41,error=0x90,**kw);invalid+=1
        for at in range(8):
            data=bytearray(f.packed);data[at]^=1;f.m.load(0x9000,data);f.check(0x41,font=0x9000,error=0x94);corrupt+=1
        f.m.load(0x9000,f.packed)
        for width in [0,9,255]:
            data=bytearray(f.widths);data[1]=width;f.m.load(0x9400,data);f.check(0x41,widths=0x9400,error=0x94);corrupt+=1
        data=bytearray(f.widths);data[28]=7;f.m.load(0x9400,data);f.check(0x5C,widths=0x9400,error=0x94);corrupt+=1
        # Packed offsets corrupt but header valid: raster must reject mismatch,
        # reversed or out-of-row intervals, rather than read another glyph.
        index=MAP[1]-32
        for start,end in [(0,480),(480,481),(20,19),(0xFFFF,0),(0,512)]:
            data=bytearray(f.packed);data[8+index*2:12+index*2]=struct.pack('<HH',start,end);f.m.load(0x9000,data);f.check(0x41,font=0x9000,error=0x94);corrupt+=1
        assert f.reu()==f.reu_before
        result=dict(status='passed',measure_calls=measures,raster_calls=rasters,clip_cases=clips,invalid_frames=invalid,corrupt_asset_cases=corrupt,total_CPU_calls=f.calls,normal_glyphs_equivalent_to_existing_expanded=128,all_styles=['normal','bold','italic','combined'],baseline=6,line_height=9,fallback='All unmapped native graphics use caller128x8 font; ninth row blank before inverse. Native mapping imports shared converter.',output_pixel_bits_checked=(rasters+clips)*9*16*2,caller_frame_bytes=SIZE,loaned_ZP_bytes=4,new_resident_BSS=0,new_resident_ZP=0,packed_font_bytes=744,widths_bytes=128,expanded_font_bytes_linked=0,packed_sha256=digest(f.packed),widths_sha256=digest(f.widths),native_fallback_sha256=digest(f.fallback),RAM_guard_bytes_per_call=0xD000,shim_bytes=1024,REU_bytes_unchanged=512*1024,peak_instructions=f.peak,cycles=None,limits='CPU glyph/metrics/mask proof. Caller compositor owns placement, tile arbitration, selection union and bitmap memory; no VIC/editor/readability/mode-switch or cycle-timing claim.')
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));e=ROOT/'agentsworking/evidence/M7'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-geos-glyphs');e.mkdir(parents=True)
        for p in OUT.iterdir():
            if p.is_file() and p.suffix in ['.json','.map','.lbl','.bin','.cpp']:shutil.copyfile(p,e/p.name)
        with zipfile.ZipFile(e/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in SOURCES:
                p=ROOT/'src'/Path(name+'.s');z.write(p,p.relative_to(ROOT))
            for name in ['src/render/geos/api.inc','src/render/geos/probe.cfg','tests/test_geos_glyphs.py','tools/peddle.py','assets/fonts/generated/manifest.json']:z.write(ROOT/name,name)
        print('EVIDENCE',e)
    finally:f.close()
if __name__=='__main__':main()
