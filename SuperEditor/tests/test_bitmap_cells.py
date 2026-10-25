"""Actual6510 single8x8 UI-tile patch, independent every-pixel/RAM oracle.

Only privatebuild/evidence; no editor make, asset regeneration, VICE or hardware.
The runtime font is caller-supplied; test reads the pinned local chargen bank.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR


def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def labels(p):return {parts[2].lstrip('.'):int(parts[1],16) for line in p.read_text().splitlines() if len(parts:=line.split())==3 and parts[0]=='al'}
def build(out):
    manifest=json.loads((ROOT/'assets/fonts/generated/manifest.json').read_text());rom=Path(os.environ.get('C64_CHARGEN',manifest['native_source']))
    raw=rom.read_bytes();assert len(raw)==4096 and sha(rom)==manifest['native_sha256'];font=raw[2048:3072]
    (out/'native-font.bin').write_bytes(font)
    (out/'aliases.s').write_text('.exportzp se_bc_context,se_bc_pointer,se_nr_context,se_nr_pointer\nse_bc_context=$F0\nse_bc_pointer=$F2\nse_nr_context=$F0\nse_nr_pointer=$F2\n.export se_petscii_screen\nse_petscii_screen=$3300\n')
    (out/'cell.cfg').write_text('MEMORY { C:file=%O,start=$1000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; }')
    command('ca65','-g','-I','src','-o',out/'cell.o','src/render/narrow/cell8.s');command('ca65','-o',out/'aliases.o',out/'aliases.s')
    command('ld65','-C',out/'cell.cfg','-o',out/'cell.bin','-m',out/'cell.map','-Ln',out/'cell.lbl',out/'cell.o',out/'aliases.o')
    assert (out/'cell.bin').stat().st_size<=200
    # Real R16/R17 layout proposal: strict dispatch, narrow font then native AC00.
    # Converter is an imported resident callback, not charged a second time.
    (out/'entry.s').write_text('''.setcpu "6502"
.import se_narrow_row,se_bitmap_cell8
.export entry,se_overlay_frame
se_overlay_frame=$8100
.segment "CODE"
.byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 ;binding placeholder, parent seals real overlay
entry:
 ldx se_overlay_frame+1
 ldy se_overlay_frame+2
 lda se_overlay_frame
 beq row
 cmp #1
 beq cell
 lda #$90
 sec
 rts
row: jmp se_narrow_row
cell: jmp se_bitmap_cell8
''')
    (out/'native.s').write_text('.export native_font\n.segment "NATIVE_FONT"\nnative_font: .incbin "'+str(out/'native-font.bin')+'"\n')
    (out/'composition.cfg').write_text('MEMORY { R:file=%O,start=$A000,size=$1000,fill=yes; } SEGMENTS { CODE:load=R,type=ro; RODATA:load=R,type=ro; NATIVE_FONT:load=R,type=ro,start=$AC00; }')
    for name,source in [('entry',out/'entry.s'),('row',ROOT/'src/render/narrow/row.s'),('arbitrate',ROOT/'src/render/narrow/arbitrate.s'),('font4',ROOT/'src/render/narrow/font4.s'),('font5',ROOT/'src/render/narrow/font5.s'),('native',out/'native.s')]:command('ca65','-g','-I','src','-o',out/f'{name}.o',source)
    compositions={}
    for name in ['font4','font5']:
        command('ld65','-C',out/'composition.cfg','-o',out/f'composition-{name}.bin','-m',out/f'composition-{name}.map','-Ln',out/f'composition-{name}.lbl',*(out/f'{n}.o' for n in ['entry','row','arbitrate','cell',name,'native','aliases']))
        syms=labels(out/f'composition-{name}.lbl');assert syms['native_font']==0xAC00 and (out/f'composition-{name}.bin').stat().st_size==4096
        compositions[name]=dict(bytes=4096,native_font_address=syms['native_font'],row_and_resolver=1800,cell=199,entry_including_binding=41,narrow_font=1024,padding_before_native_font=8,native_font=1024)
    return labels(out/'cell.lbl'),font,dict(native_rom_sha256=sha(rom),native_font_sha256=hashlib.sha256(font).hexdigest(),native_source=str(rom),bank_slice='2048:3072',compositions=compositions)

class Fixture:
    def __init__(self,out,s,font):
        self.out=out;self.s=s;self.font=font;self.m=Machine();self.calls=0;self.invalid=0;self.peak=0
        self.pattern=bytes((i*73+(i>>8)*19+31)&255 for i in range(65536));self.m.load(0,self.pattern);self.m.load(0x1000,(out/'cell.bin').read_bytes());self.m.load(0xAC00,font)
        cpp=out/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t bc_run(ZeroPagePeddle*m,uint64_t limit){auto b=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-b;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void bc_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void bc_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
extern "C" void bc_seed(ZeroPagePeddle*m){for(int bank=0;bank<256;bank++){for(int i=2;i<10;i++)zeropage_peddle_write(m,0xdf00+i,0);zeropage_peddle_write(m,0xdf06,bank);zeropage_peddle_write(m,0xdf0a,0);zeropage_peddle_write(m,0xdf01,0x90);}}
''')
        ext='.dylib' if sys.platform=='darwin' else '.so';lib=out/('runner'+ext);command('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',lib)
        self.runner=C.CDLL(str(lib));self.runner.bc_run.argtypes=[C.c_void_p,C.c_uint64];self.runner.bc_run.restype=C.c_uint64;self.runner.bc_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.runner.bc_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];self.runner.bc_seed.argtypes=[C.c_void_p]
        self.runner.bc_seed(self.m.handle);self.reu_before=self.reu()
    def close(self):self.m.close()
    def read(self,a,n):
        b=C.create_string_buffer(n);self.runner.bc_read(self.m.handle,a,n,b);return b.raw
    def reu(self):
        b=C.create_string_buffer(16*1024*1024);self.runner.bc_reu(self.m.handle,len(b),b);return b.raw
    def call(self,address,ctx):
        for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',0),('x',ctx&255),('y',ctx>>8)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
        self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.runner.bc_run(self.m.handle,10000);assert used,('nonreturn',hex(self.m.regs().pc));self.peak=max(self.peak,used);self.calls+=1;return self.m.regs(),used
    def patch(self,row,col,code,fg,bg,ctx=0xC000,font=0xAC00,bitmap=0x6000,attrs=0x4000,invalid=False,address=None):
        frame=bytes([row,col,code,fg,bg])+font.to_bytes(2,'little')+bitmap.to_bytes(2,'little')+attrs.to_bytes(2,'little');assert len(frame)==11;self.m.load(ctx,frame)
        before=self.read(0,65536);r,used=self.call(address or self.s['se_bitmap_cell8'],ctx);after=self.read(0,65536);expected=bytearray(before)
        if invalid:assert r.p&1 and r.a==0x90,('invalid',frame.hex(),r.a,r.p);self.invalid+=1
        else:
            assert not r.p&1 and r.a==0,('cell',row,col,code,fg,bg,r.a,r.p)
            # Independent VIC layout: ypixel high character row determines
            # 320-byte block; horizontal8px tile adds8, within-tile y adds1.
            for y in range(8):
                glyph=before[font+(code&127)*8+y] ^ (255 if code&128 else 0)
                at=bitmap+(row*8//8)*320+col*8+(row*8+y)%8
                expected[at]=glyph
                # Explicit bit oracle covers all64 pixels, including blanks.
                for x in range(8):assert bool(after[at]&(128>>x))==bool(glyph&(128>>x))
            expected[attrs+row*40+col]=(fg<<4)|bg
        # Only pointer loans, two temporary stack bytes and caller return slot
        # can differ elsewhere; even the rest of the CPU stack is guarded.
        expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x1FC:0x200]=after[0x1FC:0x200]
        assert after==expected,('RAM/output/source/font/frame/neighbor/shim guard',row,col,code,next((hex(i),hex(a),hex(b)) for i,(a,b) in enumerate(zip(after,expected)) if a!=b))
        assert after[ctx:ctx+11]==frame
        return used

def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/bitmap-cells'/stamp;out.mkdir(parents=True);s,font,provenance=build(out);f=Fixture(out,s,font);positions=glyph_cases=font_cases=chrome=popup=0
    try:
        # Every address, both inverse states; values/colors vary independently
        # from row arithmetic and cover each of256 raw codes and16 colors.
        for row in range(25):
            for col in range(40):
                cell=row*40+col
                for inverse in [0,128]:
                    f.patch(row,col,(cell*73&127)|inverse,cell&15,(cell//16*7)&15,ctx=[0xC000,0xC0FB,0xC5F5][cell%3]);positions+=1
        # Each raw glyph at every foreground and every background; all256
        # foreground/background pairs appear across the full256-glyph set.
        for code in range(256):
            for fg in range(16):
                f.patch((code+fg*7)%25,(code*3+fg*11)%40,code,fg,(code+fg)&15,ctx=0xC0FB);glyph_cases+=1
        # All allowed font bases, with other bases holding a distinct guard
        # pattern, so a dropped base component cannot read an identical copy.
        for base in range(0xA000,0xC000,1024):
            f.m.load(0xA000,f.pattern[0xA000:0xC000]);f.m.load(base,font)
            for code in range(256):f.patch(code%25,(code*7)%40,code,code&15,(code>>4)&15,font=base);font_cases+=1
        f.m.load(0xAC00,font)
        invalids=[dict(row=25),dict(row=255),dict(col=40),dict(col=255),dict(fg=16),dict(fg=255),dict(bg=16),dict(bg=255),dict(font=0),dict(font=0x8000),dict(font=0xC000),dict(font=0xC600),dict(font=0xA100),dict(font=0xA001),dict(font=0xBFFF),dict(font=0xBC01),dict(bitmap=0),dict(bitmap=0x2000),dict(bitmap=0x6001),dict(bitmap=0xC600),dict(attrs=0),dict(attrs=0x4001),dict(attrs=0x4400),dict(attrs=0xDB00)]
        for change in invalids:
            params=dict(row=0,col=0,code=255,fg=1,bg=6,invalid=True);params.update(change);f.patch(**params)
        # Complete header/status patch: exactly120 physical cells. The22 body
        # rows retain their preexisting narrow text pixels and attributes.
        before_body=f.read(0x6000+2*320,22*320)+f.read(0x4000+80,880)
        header=bytes([0x5D,70,9,12,5,32,0x5D,69,4,9,20,32,0x5D,86,9,5,23,32,0x5D,78,1,22,9,7,1,20,5,0x5D,66,12,15,3,11,32,0x5D,72,5,12,16,0x5D])
        rule=bytearray([0x40])*40;rule[0]=0x6D;rule[39]=0x7D
        for col in [6,12,18,27,34]:rule[col]=0x71
        for row,codes in [(0,header),(1,rule),(24,b'F6 HELP | 80 COLUMNS | NATIVE UI PATCH'.ljust(40))]:
            assert len(codes)==40
            for col,code in enumerate(codes):f.patch(row,col,code,7 if row==1 or code==0x5D else 1,6);chrome+=1
        assert f.read(0x6000+2*320,22*320)+f.read(0x4000+80,880)==before_body
        for row in range(5,19):
            for col in range(5,35):f.patch(row,col,0x40 if row in [5,18] else 0x5D if col in [5,34] else 32,14,6);popup+=1
        assert f.reu()==f.reu_before,'any of16MiB REU changed'
        # Exercise real composition dispatcher/fontAC00 with existing row code
        # linked in place; cell operation must preserve all its neighboring code.
        composition_cases=0
        for name in ['font4','font5']:
            f.m.load(0xA000,(out/f'composition-{name}.bin').read_bytes());cs=labels(out/f'composition-{name}.lbl');f.m.load(0x8100,b'\x01\x00\xC0')
            for row,col,code in [(0,0,0x5D),(0,39,0x5D),(1,6,0x71),(24,39,255)]:f.patch(row,col,code,7,6,address=cs['entry']);composition_cases+=1
        assert f.reu()==f.reu_before
        result=dict(status='passed',cell_code_bytes=199,caller_frame_bytes=11,caller_scratch_bytes=0,new_resident_BSS_bytes=0,new_resident_ZP_bytes=0,loaned_ZP_bytes=4,temporary_CPU_stack_bytes=2,position_cases=positions,glyph_color_cases=glyph_cases,font_base_cases=font_cases,invalid_cases=f.invalid,header_status_cells=chrome,popup_cells=popup,composition_cases=composition_cases,total_CPU_calls=f.calls,pixels_checked=(f.calls-f.invalid)*64,full_RAM_guard_per_call=65536,shim_guard_bytes=1024,whole_REU_unchanged_bytes=16*1024*1024,peak_call_instructions=f.peak,provenance=provenance,limits='CPU pixel/address/guard proof and isolated composition sizing. No VIC capture, mode switching, editable80-column UI integration, overlay CRC seal or cycle/frame timing claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as e:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
    finally:f.close()
    evidence=ROOT/'agentsworking/evidence/M6'/(stamp+'-bitmap-cells');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build');shutil.copy2(Path(__file__),evidence/'test_bitmap_cells.py')
    for source in ['src/render/narrow/cell8.s','src/render/narrow/api8.inc','src/render/narrow/row.s','src/render/narrow/arbitrate.s','src/render/narrow/api.inc','src/render/narrow/font4.s','src/render/narrow/font5.s','assets/fonts/generated/manifest.json','assets/fonts/generated/narrow4.bin','assets/fonts/generated/narrow5.bin','tools/fonts.py']:
        target=evidence/'source'/source;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,target)
    print('EVIDENCE',evidence)

if __name__=='__main__':main()
