"""Preview-owned rawfont reuse; real strict fetch/CG/cache/provider/DMA proof.

No shared build/native run. The installed public-font test remains unchanged;
its default build is byte-identical and continues all CRC-on-hit fault cases.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,json,shutil,subprocess,sys,zipfile
import test_geos_font_store as public
from test_geos_catalog_glyph import oracle
ROOT=public.ROOT;sys.path.insert(0,str(ROOT/'tools'))
from font_fixture import install_font_pack
from overlays import wrap,HEADER


def build(out):
    out.mkdir(parents=True,exist_ok=True)
    def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,capture_output=True)
    run(sys.executable,'tools/geos_font_store_meta.py','--pack','build/geos-font-catalog/font-pack.bin','--output',out/'geos-font-pack.inc')
    (out/'editor-api.inc').write_text('.import se_f_owner\n.importzp text_ptr,screen_ptr\n.macro OVL_BINDING\n.res 16,0\n.endmacro\n')
    (out/'stub.s').write_text('.export se_reu_banks,se_f_owner,se_overlay_binding_digest\n.exportzp text_ptr,screen_ptr\ntext_ptr=$F0\nscreen_ptr=$F2\nse_f_owner=$C5FF\n.segment "BSS"\nse_reu_banks:.res 2\n.segment "RODATA"\nse_overlay_binding_digest:.byte '+','.join(map(str,range(16)))+'\n')
    (out/'fixture.cfg').write_text('MEMORY { Z:file="",start=$F4,size=2; C:file=%O,start=$1000,size=$3000,fill=yes; B:file="",start=$C000,size=$600; T:file="",start=$CA00,size=$180; D:file="",start=$CBC0,size=$40; } SEGMENTS { ZEROPAGE:load=Z,type=zp; CODE:load=C,type=ro; RODATA:load=C,type=ro; CRC_TABLE:load=C,type=ro,align=$100; BSS:load=B,type=bss,define=yes; OVERLAY_CATALOG:load=T,type=bss; FONT_STORE_STATE:load=D,type=bss; }')
    objs=[]
    names=[('runtime','src/render/geos/font-store.s'),('import','src/render/geos/font-import.s'),('state','src/render/geos/font-store-state.s'),('provider','src/reu/provider.s'),('dma','src/reu/dma.s'),('crc','src/overlay/crc_fast.s'),('cache','src/overlay/cache.s'),('header','src/overlay/header.s'),('glyph','src/render/geos/catalog-glyph.s'),('wrapper','src/render/geos/preview-row-entry.s'),('petscii','src/tui/petscii.s'),('stub',out/'stub.s')]
    for name,p in names:
        obj=out/(name+'.o');flags=['-D','SE_GEOS_PREVIEW_FAST=1'] if name=='runtime' else []
        if name in ('cache','header'):flags+=['-D','EDITOR_CATALOG_TAIL=1','-D','EDITOR_FIXED_ENTRY=1','-D','OVL_LIMIT=64']
        run('ca65','-g','-I',out,'-I','src',*flags,'-o',obj,p);objs.append(obj)
    run('ld65','-C',out/'fixture.cfg','-o',out/'fixture.bin','-Ln',out/'fixture.lbl','-m',out/'fixture.map',*objs)
    return {x[2].lstrip('.'):int(x[1],16) for line in (out/'fixture.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}


class Fixture(public.Fixture):
    def __init__(self,out,s):
        super().__init__(out,s)
        source=(out/'runner.cpp').read_text();needle='zeropage_peddle_step_instruction(m);'
        assert source.count(needle)==1
        source='static unsigned short watched_crc=0;static unsigned crc_calls=0;extern "C" void gf_crc_watch(unsigned short p){watched_crc=p;crc_calls=0;}extern "C" unsigned gf_crc_count(){return crc_calls;}\n'+source
        source=source.replace(needle,'if(zeropage_peddle_regs(m).pc==watched_crc)crc_calls++;'+needle)
        (out/'counted.cpp').write_text(source);ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('counted'+ext)
        from peddle import VENDOR
        subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(out/'counted.cpp'),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True,capture_output=True)
        lib=C.CDLL(str(path))
        for n in ('gf_run','gf_ram','gf_reu','gf_io','gf_info'):
            old=getattr(self.r,n);getattr(lib,n).argtypes=old.argtypes;getattr(lib,n).restype=old.restype
        lib.gf_crc_watch.argtypes=[C.c_uint16];lib.gf_crc_count.restype=C.c_uint32;self.r=lib
        self.m.write(s['se_f_owner'],4);self.m.load(0x4800,(ROOT/'assets/fonts/generated/native8.bin').read_bytes())
        install_font_pack(self);assert not self.call('se_overlay_init').p&1
    def query(self,entry):self.m.load(0xCBD0,entry[:4])
    def fetch(self,name='se_gf_fetch_preview'):
        self.r.gf_crc_watch(self.s['se_crc_byte']);before=self.instructions;dma=int.from_bytes(self.read(self.s['se_reu_dma_calls'],2),'little')
        r=self.call(name);return r,self.instructions-before,self.r.gf_crc_count(),(int.from_bytes(self.read(self.s['se_reu_dma_calls'],2),'little')-dma)&65535
    def glyph(self,entry,value,style,inverse):
        origin,flo,fhi,point=entry[:4]
        profile=bytes((0,0,0,9,1,6,0)) if origin==2 else bytes((1,flo,fhi,point,1,6,0))
        self.m.load(0xCC00+18,profile);self.m.write(0xCC00+34,value);self.m.write(0xCC00+32,style);self.m.write(0xCC00+65,inverse);self.m.write(0xCC00+33,0);self.m.write(0xCC00+35,0)
        r,used,crc,dma=self.fetch('entry');return r,self.read(0x8800,240),used,crc,dma
    def asset(self,identity):
        payload=bytes(range(16))+bytes((0xA9,0,0x18,0x60))+bytes([identity])*4076
        image=wrap(payload,0,identity,16,api=(self.s['se_overlay_call'],self.s['se_overlay_frame']),binding_digest=bytes(range(16)))
        self.m.write(0xCBD5,0) #explicit host-owned import staging borrow
        self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,payload)
        assert not self.call('se_overlay_import').p&1
        return image


def run(out,smoke=False):
    s=build(out/'leaf');f=Fixture(out/'leaf',s);pack=(ROOT/'build/geos-font-catalog/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)]
    fonts=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();cases=[];faults=[]
    try:
        f.asset(1);f.asset(2);baseline=f.reu();shim=f.read(0xC600,1024);hot=f.read(0x9200,2048)
        for i,e in enumerate(entries[:1] if smoke else entries):
            offset=int.from_bytes(e[8:11],'little');length=int.from_bytes(e[11:13],'little');raw=pack[offset:offset+length]
            f.query(e);f.m.write(0xCBD5,0);r,first,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma>0 and f.m.read(0xCBD5)==0x81
            r,fast,crc,dma=f.fetch();assert not r.p&1 and crc==dma==0 and f.read(0x5000,length)==raw
            f.query(e);r,strict,crc,dma=f.fetch('se_gf_fetch');assert not r.p&1 and crc==length and dma==0 and f.m.read(0xCBD5)==1
            # Re-arm through strictverifiedrefill; compare actual R23 glyphs
            # against independent rawfont raster, not a cached emitted bitmap.
            samples=[(0xC1,0,0),(0x41,3,0),(0x47,7,1)] if smoke else [(v,st,inv)for v in range(32,128)for st in (0,1,2,7)for inv in (0,1)]
            for value,style,inverse in samples:
                r,frame,used,crc,dma=f.glyph(e,value,style,inverse);assert not r.p&1,(i,value,r.a)
                metrics,ink,coverage=oracle(raw,fonts,value,0,style,inverse,(0,32,0,24))
                assert frame[14:20]==metrics and frame[20:116]==ink and frame[116:212]==coverage,(i,value,style,inverse,'actualR23rawfontglyph')
            assert f.reu()==baseline,'FETCH/glyph changed any16MiBREU'
            cases.append(dict(face=i,bytes=length,first_instructions=first,strict_hit_instructions=strict,fast_hit_instructions=fast,strict_crc_bytes=length,fast_crc_bytes=0,glyphs=len(samples)))
        print('FIRST FAST FONT PASS',cases[0],flush=True)
        e=entries[0];length=int.from_bytes(e[11:13],'little');offset=int.from_bytes(e[8:11],'little');raw=pack[offset:offset+length]
        def armed():f.query(e);f.m.write(0xCBD5,0);assert not f.fetch()[0].p&1
        armed();f.m.write(0x500A,f.m.read(0x500A)^1);r,_,crc,_=f.fetch('se_gf_fetch');assert r.p&1 and r.a==0x94 and crc==length and f.m.read(0xCBD5)==0
        faults.append('public strictFETCH retainsCRC refusal oncachedRAMcorruption')
        # A real unrelated R image stage must disarm BEFORE any overwrite. No
        # counter equality/advance assumptions are needed, including failures.
        armed();assert not f.call('se_overlay_call',1,0).p&1;assert f.m.read(0xCBD5)==0
        r,_,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma and f.read(0x5000,length)==raw
        faults.append('realoverlayload disarms andtrustedFDrefill precedesglyph')
        # Poison stored image2 so CRC admission fails after staging. Loadcount
        # stays unchanged, but stickyVALID mustalreadybezero.
        h=f.m.read(s['se_overlay_asset']);bank=f.m.read(s['se_reu_map']+h);f.m.write(0x8000,0xA7)
        for n,v,w in [('se_reu_logical',h,1),('se_reu_offset',4096+100,2),('se_reu_c64',0x8000,2),('se_reu_length',1,2)]:f.m.load(s[n],v.to_bytes(w,'little'))
        assert not f.call('se_reu_copy',0).p&1
        armed();loads=f.read(s['se_overlay_loads'],2);r=f.call('se_overlay_call',2,0)
        assert r.p&1 and r.a==0x14 and f.read(s['se_overlay_loads'],2)==loads and f.m.read(0xCBD5)==0
        assert not f.fetch()[0].p&1
        faults.append('failedCRCstage disarms despiteunchangedloadcount')
        # Simulate a counterwrapping arbitrarily between verified uses while
        # keeping stickyinvalidated, as every realstage mustdo.
        armed();tag=f.read(s['se_overlay_loads'],2);f.m.write(0xCBD5,0);f.m.load(0x5000,bytes([0xA5])*length);f.m.load(s['se_overlay_loads'],tag)
        r,_,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma and f.read(0x5000,length)==raw
        faults.append('equal16bitcounter cannotoverride stickyknownborrow/wrap invalidation')
        armed();before=f.read(0xCBC0,64);f.m.write(s['se_f_owner'],1);r,_,crc,dma=f.fetch();assert r.p&1 and r.a==0xB2 and crc==dma==0 and f.read(0xCBC0,64)==before;f.m.write(s['se_f_owner'],4)
        faults.append('foreignowner opaque beforedescriptor/fontaccess')
        armed();f.m.write(0xCBD5,0);r,_,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma
        faults.append('freshpage/ownerlifetime explicitdisarm requiresnewverify')
        for at in (0xCBC1,0xCBC2,0xCBC3,0xCBC4):
            armed();old=f.m.read(at);f.m.write(at,old^0x80);r,_,_,_=f.fetch();assert r.p&1 and r.a==0x18 and f.m.read(0xCBD5)==0;f.m.write(at,old)
        faults.append('handles/epochs providerauthentication refusesbefore reuse')
        for at,value,code in ((0xCBC0,0,0x18),(0xCBC5,1,0x91)):
            armed();old=f.m.read(at);f.m.write(at,value);r,_,crc,dma=f.fetch();assert r.p&1 and r.a==code and not crc and not dma and f.m.read(0xCBD5)==0;f.m.write(at,old)
        faults.append('READY/busy refusal disarms ratherthanrevivingverifiedwindow')
        for index in (0,1):
            armed();handle=f.m.read(0xCBC1+index);physical=f.m.read(s['se_reu_map']+handle)
            for table,slot in (('se_reu_logical_owner',handle),('se_reu_physical_owner',physical)):
                at=s[table]+slot;old=f.m.read(at);f.m.write(at,0x77);r,_,crc,dma=f.fetch()
                assert r.p&1 and r.a==0x18 and not crc and not dma and f.m.read(0xCBD5)==0
                f.m.write(at,old);assert not f.fetch()[0].p&1
        faults.append('both logical and physicalFDowners reauthenticated before everyreuse')
        armed();h0,h1=f.read(0xCBC1,2);p0=f.m.read(s['se_reu_map']+h0);p1=f.m.read(s['se_reu_map']+h1)
        f.m.write(s['se_reu_map']+h0,p1);f.m.write(s['se_reu_map']+h1,p0)
        r,_,crc,dma=f.fetch();assert r.p&1 and r.a==0x94 and dma and f.m.read(0xCBD5)==0
        f.m.write(s['se_reu_map']+h0,p0);f.m.write(s['se_reu_map']+h1,p1)
        assert not f.fetch()[0].p&1
        faults.append('different stillFDownedphysicalbindings forceverifiedrefill andwrongcontentrefuses')
        armed();f.query(entries[1]);r,_,crc,dma=f.fetch();assert not r.p&1 and crc==int.from_bytes(entries[1][11:13],'little') and dma
        faults.append('face/keyselection change alwaysrefills/fullCRC')
        armed();f.m.load(s['se_overlay_loads'],((int.from_bytes(f.read(s['se_overlay_loads'],2),'little')+1)&65535).to_bytes(2,'little'))
        r,_,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma
        faults.append('changedloadwitness cannotshortcut strictrefill')
        armed();old=f.m.read(0xCBD8);f.m.write(0xCBD8,old^1);r,_,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma and f.read(0x5000,length)==raw
        faults.append('changeddescriptors/refill length witness cannotshortcutCRC')
        assert f.read(0xC600,1024)==shim and f.read(0x9200,2048)==hot
        result=dict(status='passed',faces=cases,faults=faults,default_public_abi='StrictFETCH stillCRC-on-every-hit, defaultbuildaliasespreviewentrytostrict; unchangedpublicsuite runsseparately.',guard='All16MiB readonly duringfetch/glyph groups; shim/foreignowner unchanged. Overlayfaultsetup ownsitsactualassetwrites.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [ROOT/'src/render/geos/font-store.s',ROOT/'src/render/geos/font-store.inc',ROOT/'src/render/geos/preview-row-entry.s',Path(__file__)]})
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,len(cases),len(faults));return result
    finally:f.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-font-fast'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);run(out,a.smoke)


if __name__=='__main__':main()
