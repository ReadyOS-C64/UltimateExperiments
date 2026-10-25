"""Private real R27 root entry; UI/status are explicit two-function stubs.

Actual current resident, C21/FE page, R27 source guard, tile restoration, metadata
and public hot-window moves execute. No shared build/native run. Stub status
records calls only; real chrome glyph/UI oracle belongs to its separate gate.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys
import test_geos_caret_cache as prior
import test_geos_fold_editor as fold
from overlays import wrap
from geos_fold_model import raster
ROOT=fold.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T065852645920Z/fixture'
STATE=0xCF90


def build(out,frozen):
    out.mkdir();r=json.loads((frozen/'build/editor-report.json').read_text());d=r['resident_binding']['digest']
    (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
    (out/'ui-stub.s').write_text('.export se_gcc_status,se_gcc_cell\n.segment "CODE"\nse_gcc_status:inc $CFF0\nlda $CFF2\nbeq ok\nsec\nrts\nse_gcc_cell:inc $CFF1\nok:lda #0\nclc\nrts\n')
    objs=[]
    for name,source in [('caret','src/render/geos/caret-cache.s'),('cache','src/render/geos/cache.s'),('ui',out/'ui-stub.s')]:
        obj=out/(name+'.o');prior.command('ca65','-g','-I',out,'-I','src','-o',obj,source);objs.append(obj)
    prior.command(sys.executable,'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',out/'aliases.s',*objs)
    prior.command('ca65','-g','-o',out/'aliases.o',out/'aliases.s')
    prior.command('ld65','-C','cfg/overlay-r.cfg','-o',out/'root.bin','-Ln',out/'root.lbl','-m',out/'root.map',*objs,out/'aliases.o')
    payload=(out/'root.bin').read_bytes();s=r['symbols'];image=wrap(payload,0,27,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'root.seo').write_bytes(image)
    return payload,image


class Fixture(fold.Fixture):
    def invoke(self,operation):
        self.put('se_overlay_frame',operation,1);before=self.read(0,65536);reu=self.reu();canonical=self.canonical()
        r,n=self.fast_call(self.s['se_overlay_call'],a=27,x=0)
        after=self.read(0,65536);wanted=bytearray(before)
        pairs=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2),('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_object_id',12),('validate_index',1),('validate_extent',1),('validate_type',1),('doc_cache_slot',1),('screen_ptr',2),('se_f_owner',1),('se_v_bottom',3),('se_v_seen',1),('se_v_caret_row',1),('se_l_valid',1),('se_l_need_wrap',1)]
        allowed=[(self.s[k],self.s[k]+w)for k,w in pairs]+[(0x100,0x200),(STATE,STATE+82),(0xCFF0,0xCFF3),(0x8080,0x8088),(0x8100,0x8120),(0x8500,0x8540),(0x9178,0x917E),(0x4000,0x43E8),(0x6000,0x7F40),(0x5000,0x6000),(0xA000,0xB000),(0xCBD5,0xCBD6),(self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_overlay_header'],self.s['se_overlay_header']+36),(0xDF00,0xDF0B)]
        for a,b in allowed:wanted[a:b]=after[a:b]
        assert after==wanted,('wholeRAM',operation,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))
        assert self.canonical()==canonical,'source/history canonical mutation'
        handle=self.get('se_gc_handle',1);bank=self.m.read(self.s['se_reu_map']+handle)
        actual=self.reu();base=bank*65536;want=bytearray(reu)
        # Only authenticated derived FE header and existingrowprefixes change.
        for a,b in [(0,64)]+[(0x200+i*0x800,0x220+i*0x800)for i in range(22)]:want[base+a:base+b]=actual[base+a:base+b]
        if operation==2:want[base+0xB200:base+0xD528]=actual[base+0xB200:base+0xD528]
        assert actual==want,'whole16MiB outsideFEderived header/prefix/base'
        return r,n


def run(out,base,smoke=False):
    frozen,identity=fold.geos.freeze(out,base);payload,image=build(out/'leaf',frozen)
    # Explicit private same-binding component replacement, before realimport.
    (frozen/'build/overlays/geoscaret.seo').write_bytes(image)
    fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen
    fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
    f=Fixture(out,frozen,fold.retention.runner(out),True);cases=[]
    fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)}
    try:
        data=fold.geos.native_text('Wim. Mixed text\rSecond line\rTail.');f.source(data);f.command(99);f.render();f.m.load(0xCFF0,bytes(3))
        assert f.m.read(STATE)==1
        before=f.read(0,65536);r=f.call('se_hot_call',7);assert not r.p&1 and f.get('se_hot_caret')==1
        r,used=f.invoke(3);assert not r.p&1 and r.a==0 and f.get('se_f_owner',1)==0 and f.m.read(0xCFF0)==1,(r.a,r.p)
        matrix,colors,popup=fold.geos.grid.logical_ui(f,data)
        b,a,_,_=raster(data,fonts,[],top=f.get('se_v_top'),caret=1);b,a=fold.geos.with_chrome(b,a,matrix,colors,fonts['native8.bin'],popup)
        # Stub status doesnotrepaintchrome; oldfullstatus usescaret0. Bodyexact.
        assert f.read(0x6000+640,7040)==b[640:7680] and f.read(0x4000+80,880)==a[80:960]
        header=f.raw_cache()[0];assert f.get('se_v_bottom')==int.from_bytes(header[38:41],'little') and f.get('se_v_seen',1)==header[41] and f.get('se_v_caret_row',1)==header[42]
        assert f.get('se_l_valid',1)==1 and f.get('se_l_need_wrap',1)==0
        assert int.from_bytes(f.read(STATE+1,2),'little')==(f.get('se_e_draw_sequence',2)+1)&65535
        assert not f.call('se_er_published').p&1
        cases.append(dict(tag='actualrootowner0-TRYFAST/realhotRIGHT/bodypixels/metadata',instructions=used))
        print('FIRST ROOT R27 PASS',cases[-1],flush=True)
        for owner in (1,2,3,4,0xFF):
            f.put('se_f_owner',owner,1);state=f.read(STATE,82);phase=f.read(0x8D00,1152);ui=f.read(0xCFF0,3)
            r,n=f.invoke(3);assert not r.p&1 and r.a==2 and f.get('se_f_owner',1)==owner and f.read(STATE,82)==state and f.read(0x8D00,1152)==phase and f.read(0xCFF0,3)==ui
            cases.append(dict(tag='foreignrootopaque',owner=owner,instructions=n))
        for owner in (0,1):
            f.put('se_f_owner',owner,1);state=f.read(STATE,82);phase=f.read(0x8D00,1152);count=f.m.read(0xCFF1)
            r,n=f.invoke(1);assert not r.p&1 and r.a==0 and f.m.read(0xCFF1)==count+1 and f.read(STATE,82)==state and f.read(0x8D00,1152)==phase and f.get('se_f_owner',1)==owner
            cases.append(dict(tag='owner0-1cellstubroute',owner=owner,instructions=n))
        f.put('se_f_owner',0,1)
        if not smoke:
            for tag,name,value in [('pan','se_l_pan',1),('popup','se_e_ui',1),('formatted','se_r_presentation',1),('notGEOS','se_mode',2)]:
                old=f.get(name,1);f.put(name,value,1);pixels=f.read(0x6000,8000);r,n=f.invoke(3);assert not r.p&1 and r.a==2 and f.get('se_f_owner',1)==0 and f.m.read(STATE)==0 and f.read(0x6000,8000)==pixels
                f.put(name,old,1);cases.append(dict(tag=tag+'-miss',instructions=n));f.render()
            # Sourcechanged after capture mustmiss, retaining realpending source.
            f.key(ord('Q'));r,n=f.invoke(3);assert not r.p&1 and r.a==2 and f.get('se_f_owner',1)==0 and f.m.read(STATE)==0
            cases.append(dict(tag='pending-sourcekeymiss',instructions=n));f.render()
            # Authenticated cache fault is an error withrelease+disarm, not stalehit.
            old=f.get('se_gc_epoch',2);f.put('se_gc_epoch',old^0x8000,2);r,n=f.invoke(3);assert not r.p&1 and r.a==2 and f.get('se_f_owner',1)==0 and f.m.read(STATE)==0;f.put('se_gc_epoch',old,2)
            cases.append(dict(tag='staleFErefusalmiss',instructions=n))
            f.render();assert not f.call('se_hot_call',7).p&1;f.m.write(0xCFF2,0x94)
            r,n=f.invoke(3);assert r.p&1 and r.a==0x94 and f.get('se_f_owner',1)==0 and f.m.read(STATE)==0 and f.m.read(STATE+56)==0
            f.m.write(0xCFF2,0);cases.append(dict(tag='statuserror-release/disarm-preserveprimary',instructions=n))
            # A real codepage has22physical8px rows. Visit its finalprefix
            # synchronously, then let real public DOWN consume publishedview.
            data=fold.geos.native_text(':::basic\r'+'1\r'*25+':::\rTail')
            f.source(data);f.command(99);f.position(9);f.put('se_v_top',9);f.render();f.m.load(0xCFF0,bytes(3))
            assert f.m.read(STATE+47)==22
            for _ in range(42):assert not f.call('se_hot_call',7).p&1
            assert f.get('se_hot_caret')==51
            r,n=f.invoke(3);assert not r.p&1 and r.a==0 and f.get('se_v_caret_row',1)==21 and f.get('se_f_owner',1)==0
            assert f.m.read(STATE+54)==21
            matrix,colors,popup=fold.geos.grid.logical_ui(f,data);bits,attrs,_,_=raster(data,fonts,[],top=9,caret=51)
            bits,attrs=fold.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
            assert f.read(0x6000+640,7040)==bits[640:7680] and f.read(0x4000+80,880)==attrs[80:960]
            assert not f.call('se_er_published').p&1
            f.command(37);assert f.get('se_hot_caret')==53
            cases.append(dict(tag='all22prefixunits/metadata-following-publicDOWN',instructions=n))
        result=dict(status='passed',private_binding=identity,payload_bytes=len(payload),cases=cases,ui_seam='Only se_gcc_status and se_gcc_cell arestubs recordingcalls; noproof ofactualstatus/cell pixels. Body/source/cache/provider/DMA/metadata areactual.',source_sha256=hashlib.sha256((ROOT/'src/render/geos/caret-cache.s').read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,len(cases));return result
    finally:f.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-caret-root'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)
