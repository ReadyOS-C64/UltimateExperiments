"""Sealed real R16/R17 modules, fixed fonts and strict leaf-entry proof.

Private build only. build(out,base) is reusable by the actual-mode producer's
isolated capsule. base must contain immutable build/editor.prg/.lbl/report.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap,HEADER
import cpu_editor
from test_bitmap_cells import Fixture,labels
from test_narrow_rows import oracle
BASE=ROOT/'build/style-editor/20261024T230014446442Z/fixture'

def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build(out,base=BASE):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);base=Path(base)
    r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols'];binding=verify(base/'build/editor.prg',base/'build/editor.lbl');assert binding['resident_sha256']==r['sha256'] and binding['digest']==r['resident_binding']['digest']
    lines=[f'{n} = ${s[n]:04X}' for n in ['text_ptr','screen_ptr','se_overlay_frame','se_petscii_screen']]
    lines+=['.macro OVL_BINDING',' .byte '+','.join('$'+binding['digest'][i:i+2] for i in range(0,32,2)),'.endmacro'];(out/'editor-api.inc').write_text('\n'.join(lines)+'\n')
    for name,src in [('row','src/render/narrow/row.s'),('arbitrate','src/render/narrow/arbitrate.s'),('cell','src/render/narrow/cell8.s'),('font4','src/render/narrow/font4.s'),('font5','src/render/narrow/font5.s'),('native','src/render/narrow/native8.s')]:command('ca65','-g','-I',out,'-I','src','-o',out/f'{name}.o',src)
    records={}
    for mode,font,id_ in [(80,'font4',16),(60,'font5',17)]:
        command('ca65','-g','-I',out,'-I','src',*(['-D','GRID60=1'] if mode==60 else []),'-o',out/f'grid{mode}.o','src/overlays/grid.s')
        command('ld65','-C','cfg/grid-r.cfg','-o',out/f'grid{mode}.bin','-m',out/f'grid{mode}.map','-Ln',out/f'grid{mode}.lbl',*(out/f'{n}.o' for n in [f'grid{mode}','row','arbitrate','cell',font,'native']))
        payload=(out/f'grid{mode}.bin').read_bytes();ls=labels(out/f'grid{mode}.lbl');assert len(payload)==4096 and ls['entry']==0xA010 and ls['se_native_font8']==0xAC00 and ls[f'se_narrow_font{5 if mode==60 else 4}']==0xA800
        assert payload[0x800:0xC00]==(ROOT/f'assets/fonts/generated/narrow{5 if mode==60 else 4}.bin').read_bytes();assert payload[0xC00:]==(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
        image=wrap(payload,0,id_,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding['digest']));(out/f'grid{mode}.seo').write_bytes(image)
        records[mode]=dict(identity=id_,payload_bytes=4096,file_bytes=len(image),sha256=hashlib.sha256(image).hexdigest(),payload_sha256=hashlib.sha256(payload).hexdigest(),entry=ls['entry'],narrow_font=0xA800,native_font=0xAC00,symbols=ls,path=str(out/f'grid{mode}.seo'))
    (out/'build.json').write_text(json.dumps(dict(baseline=str(base),resident_sha256=r['sha256'],binding=binding,records=records),indent=2)+'\n')
    return dict(report=r,records=records,base=base)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=BASE);a=parser.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/grid-assets'/stamp;built=build(out,a.base);s=built['report']['symbols'];records=built['records'];base=built['base']
    # Existing cell runner supplies full memory/16MiB REU snapshots and batches
    # the unmodified Peddle CPU. Its standalone199B image is only helper input;
    # all tested leaf code below is the real complete sealed4096B payload.
    (out/'bootstrap-aliases.s').write_text('.exportzp se_bc_context,se_bc_pointer\nse_bc_context=$F0\nse_bc_pointer=$F2\n')
    (out/'bootstrap.cfg').write_text('MEMORY { C:file=%O,start=$1000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; }')
    command('ca65','-o',out/'bootstrap-aliases.o',out/'bootstrap-aliases.s')
    command('ld65','-C',out/'bootstrap.cfg','-o',out/'cell.bin',out/'cell.o',out/'bootstrap-aliases.o')
    font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();f=Fixture(out,records[80]['symbols'],font)
    def invoke(address,a_=0,x=0,y=0):
        for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',a_),('x',x),('y',y)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
        f.m.write(0x1FE,0xFE);f.m.write(0x1FF,2);n=f.runner.bc_run(f.m.handle,2_000_000);assert n,('nonreturn',hex(address),hex(f.m.regs().pc));return f.m.regs(),n
    nop=bad=rowcases=cellcases=admissions=0
    try:
        # Actual resident startup/import/cache admission; no production catalog
        # or disk changes. Current immutable baseline has24 catalog entries.
        freeze=json.loads((base/'freeze.json').read_text());names=freeze['names'];assets={n:(base/f'build/overlays/{n}.seo').read_bytes() for n in names}
        cpu_editor.ROOT=base;cpu_editor.NAMES=names
        f.m.call=lambda address,a=0,x=0,y=0,limit=1_000_000:invoke(address,a,x,y)
        cpu_editor.startup(f.m,s,assets)
        for mode in [80,60]:
            image=(out/f'grid{mode}.seo').read_bytes();f.m.load(s['se_overlay_header'],image[:HEADER]);f.m.load(0x5000,image[HEADER:]);r,_=invoke(s['se_overlay_import']);assert not r.p&1,('import',mode,r.a)
        reu=f.reu()
        for mode in [80,60,80,60]:
            f.m.load(s['se_overlay_frame'],bytes([2,0,0xC6]));before=f.read(0x4000,1000)+f.read(0x6000,8000);shim=f.read(0xC600,1024);vic=f.read(0xD000,0x40)
            r,_=invoke(s['se_overlay_call'],records[mode]['identity'],0);assert not r.p&1 and r.a==0,('real admission',mode,r.a)
            assert f.read(0xA000,4096)==(out/f'grid{mode}.bin').read_bytes()
            assert f.read(0x4000,1000)+f.read(0x6000,8000)==before and f.read(0xC600,1024)==shim and f.read(0xD000,0x40)==vic
            admissions+=1
        assert f.reu()==reu
        for mode in [80,60]:
            image=(out/f'grid{mode}.bin').read_bytes();f.m.load(0xA000,image);entry=records[mode]['entry']
            # NOP never dereferences even invalid/forbidden caller frame.
            for ptr in [0,0xFFFF,0xC600,0x8800]:
                f.m.load(s['se_overlay_frame'],bytes([2,ptr&255,ptr>>8]));before=f.read(0,65536);r,_=invoke(entry);after=f.read(0,65536);expected=bytearray(before);expected[0x1FE:0x200]=after[0x1FE:0x200]
                assert not r.p&1 and r.a==0 and after==expected,('NOP write',mode,ptr);nop+=1
            for operation in range(3,256):
                f.m.load(s['se_overlay_frame'],bytes([operation,0,0xC6]));before=f.read(0,65536);r,_=invoke(entry);after=f.read(0,65536);expected=bytearray(before);expected[0x1FE:0x200]=after[0x1FE:0x200]
                assert r.p&1 and r.a==0x90 and after==expected,('bad opcode',mode,operation,r.a);bad+=1
            # Actual row operation with both raw and shared native conversion.
            for encoding in [0,1]:
                for row in [0,2,23,24]:
                    chars=bytes((i*13+row*7)&255 for i in range(mode));roles=bytes(i%14 for i in range(mode));flags=bytes(i%8 for i in range(mode));palette=bytes([1,3,7,10,12,12,12,7,13,5,15,7,3,1]);frame=bytearray([mode,row,mode,encoding,6])
                    for ptr in [0x6000,0x4000,0xA800,0x8400,0x8500,0x8600,0x8700]:frame+=ptr.to_bytes(2,'little')
                    f.m.load(0x8800,frame+bytes([0xA7])*49);f.m.load(0x8400,chars);f.m.load(0x8500,roles);f.m.load(0x8600,flags);f.m.load(0x8700,palette);f.m.load(s['se_overlay_frame'],b'\0\0\x88');before=f.read(0,65536);r,_=invoke(entry);after=f.read(0,65536)
                    assert not r.p&1 and r.a==0,('row',mode,encoding,row,r.a)
                    bits,attributes=oracle(mode,chars,roles,flags,palette,6,encoding,image[0x800:0xC00]);expected=bytearray(before);expected[0x6000+row*320:0x6000+(row+1)*320]=bits;expected[0x4000+row*40:0x4000+(row+1)*40]=attributes;expected[0x8800+19:0x8800+68]=after[0x8800+19:0x8800+68];expected[2:6]=after[2:6];expected[0x100:0x200]=after[0x100:0x200]
                    assert after==expected,('row guard/pixels',mode,row,encoding,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,expected)) if a!=b));rowcases+=1
            for row,col,code in [(0,0,0x5D),(0,39,0x5D),(1,6,0x71),(24,39,255)]:
                frame=bytes([row,col,code,7,6])+b'\0\xAC\0\x60\0\x40';f.m.load(0x8800,frame);f.m.load(s['se_overlay_frame'],b'\x01\0\x88');before=f.read(0,65536);r,_=invoke(entry);after=f.read(0,65536);expected=bytearray(before);at=0x6000+row*320+col*8;expected[at:at+8]=bytes(b^(255 if code&128 else 0) for b in font[(code&127)*8:(code&127)*8+8]);expected[0x4000+row*40+col]=0x76;expected[2:6]=after[2:6];expected[0x1FC:0x200]=after[0x1FC:0x200];assert not r.p&1 and r.a==0 and after==expected,('cell guard',mode,row,col);cellcases+=1
        assert f.reu()==reu
        result=dict(status='passed',resident_sha256=built['report']['sha256'],binding=built['report']['resident_binding']['digest'],payload_bytes_each=4096,entry_bytes_including_binding=49,narrow_font=0xA800,native_font=0xAC00,padding_bytes=0,actual_resident_catalog_admissions=admissions,NOP_no_write_cases=nop,bad_opcode_no_write_cases=bad,row_cases=rowcases,row_pixels=rowcases*2560,cell_cases=cellcases,full_RAM_guards=65536,whole_REU_unchanged_bytes=16777216,source_records={m:{k:v for k,v in r.items() if k!='symbols'} for m,r in records.items()},limits='Real sealed leaf payload/import/admission and direct entry CPU proof; no disk/assets-list/sharedmake/native run or user editable-mode claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
    finally:f.close()
    evidence=ROOT/'agentsworking/evidence/M6'/(stamp+'-sealed-grid-assets');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build');shutil.copy2(Path(__file__),evidence/'test_grid_assets.py')
    for name in ['src/overlays/grid.s','src/render/narrow/grid.inc','src/render/narrow/native8.s','cfg/grid-r.cfg','src/render/narrow/row.s','src/render/narrow/arbitrate.s','src/render/narrow/cell8.s','src/render/narrow/api.inc','src/render/narrow/api8.inc','src/render/narrow/font4.s','src/render/narrow/font5.s','assets/fonts/generated/native8.bin']:
        target=evidence/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    for name in ['tests/test_bitmap_cells.py','tests/test_narrow_rows.py','tools/peddle.py','tools/cpu_editor.py','tools/overlays.py','tools/bindings.py']:
        target=evidence/'verification'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    print('EVIDENCE',evidence)

if __name__=='__main__':main()
