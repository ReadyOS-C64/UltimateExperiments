"""Bounded current59 mutation/history soak, actual product CPU/ROM seams only.

Reuses the released independent byte/history/clipboard model. Real allocator
fragmentation and periodic independent fullpixels + observed typedDMA guards.
16bank profile keeps foldmap unallocated;32bank also exercises storedfolds and
>64KiB. No native/latency/ReadyOS/physical worst-case claim.
"""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import argparse,binascii,hashlib,inspect,json,textwrap
import test_editor_soak as old
import test_capacity_lifecycle as capacity
import test_grid_capture_index as identity
import test_geos_semantic_editor as semantic
import test_lifecycle_cache_current as cache
from test_geos_preview_vice import pack_catalog
from geos_preview_model import render as preview_render
from d81_image import D81Image
ROOT=old.ROOT
BASE=ROOT/'build/normal-row80-committed/20261026T193357856684Z/fixture'


def run(out,base,physical,rounds=64,seed=0x53454f53):
 out.mkdir(parents=True)
 manifest=json.loads((base/'freeze.json').read_text());report=json.loads((base/'build/editor-report.json').read_text());disk=(base/'build/supereditor.d81').read_bytes();d81=D81Image(disk)
 assert len(manifest['names'])==59 and hashlib.sha256(disk).hexdigest()=='446a5fa688886d7065b1da21491cf75c76f497bc111c37b83c3673c1a930171e'
 prg=(base/'build/editor.prg').read_bytes();assert hashlib.sha256(prg).hexdigest()==manifest['prg_sha256']==report['sha256'] and d81.read(b'SUPEREDITOR',kind=2).data==prg
 digest=bytes.fromhex(report['resident_binding']['digest'])
 for name in manifest['names']:
  image=(base/f'build/overlays/{name}.seo').read_bytes();assert hashlib.sha256(image).hexdigest()==manifest['assets'][name] and d81.read(name.upper().encode(),kind=1).data==image
  assert image[20:36]==image[36:52]==digest and len(image)-36==int.from_bytes(image[8:10],'little') and binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
 seal=dict(PRG=manifest['prg_sha256'],D81=hashlib.sha256(disk).hexdigest(),binding=digest.hex(),assets=59,C33=manifest['assets']['grid'])
 class Fixture(old.fold.Fixture):
  def source(self,data):old.fold.geos.Fixture.source(self,data,banks=1 if len(data)<=65536 else 2,physical=physical)
 proxy=SimpleNamespace(**vars(old.fold));proxy.Fixture=Fixture
 source=textwrap.dedent(inspect.getsource(old.run))
 source=source.replace('source=fold.geos.native_text(', 'source=fold.geos.native_text(',1)
 needle="':::basic\\r10 PRINT \"Hello\":REM note\\r:::\\r:::asm\\rstart: lda #$2A\\r rts\\r:::\\rTail **end**.\\r')"
 assert source.count(needle)==1
 source=source.replace(needle,needle+"+fold.geos.native_text('Long '+('x'*700)+'\\r')")
 source=source.replace('data=source\n','data=source\n    held=[];fragmentation=[];pixel_checks=[];baseline_proofs=[];piece_peak=0\n',1)
 a=source.index('    def seed_foreign():');b=source.index('    def clip_bytes():',a)
 source=source[:a]+'''    def seed_foreign():
        held.clear()
        # Genuine baseline before the audited edits; no unchecked type53 writes
        # are permitted later by the unchanged DMA observer.
        f.command(99);f.render()
        if f.get('se_bc_flags',1)&1:
            proof,_=cache.cache_frame(f.s,f.read(0,65536),f.reu(),frozen/'build/overlays');baseline_proofs.append(proof)
        f.command(96)
        # Three checked allocations, free alternate handles: actual holes,
        # one retained foreign bank. No object/provider table is host-patched.
        allocations=[]
        for _ in range(3):
            r,n=f.fast_call(f.s['se_reu_alloc'],a=0xa5)
            assert not r.p&1,('fragmentallocation',r.a)
            allocations.append(r.a)
        for index,handle in enumerate(allocations):
            if index!=1:
                r,n=f.fast_call(f.s['se_reu_free'],x=handle);assert not r.p&1
            else:held.append((handle,f.m.read(f.s['se_reu_map']+handle)))
        pattern=bytes((i*73+29)&255 for i in range(256));f.m.load(0x8800,pattern)
        for handle,bank in held:
            for offset in (0,0xff00):
                for n,v,w in [('se_reu_logical',handle,1),('se_reu_offset',offset,2),('se_reu_c64',0x8800,2),('se_reu_length',256,2)]:f.put(n,v,w)
                assert not f.call('se_reu_copy',0).p&1
        fragmentation.append(dict(allocations=allocations,retained=held.copy(),physical_owners=f.read(f.s['se_reu_physical_owner'],PHYSICAL).hex()))

    def pixels(tag):
        f.render();mode=f.get('se_mode',1)
        fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)}
        if f.get('se_e_ui',1)==4:
            pack=D81Image((frozen/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
            catalog_=pack_catalog(pack,fonts['native8.bin']);page=preview_render(data,f.read(0xcb80,64),catalog=catalog_,top=f.get('se_v_top'))
            matrix,colors,_=fold.geos.grid.logical_ui(f,data);bits,attrs=fold.geos.with_chrome(page.bitmap,page.attrs,matrix,colors,fonts['native8.bin'])
        elif mode==3:bits,attrs,_,_=semantic.expected(f,data,fonts)
        else:(bits,attrs),_,_,_=fold.geos.grid.expected(f,data)
        assert f.read(0x4000 if mode==0 else 0x6000,len(bits))==bits,(tag,'independentpixels')
        actual=bytes(v&15 for v in f.read(0xd800,1000))if mode==0 else f.read(0x4000,1000)
        assert actual==attrs,(tag,'independentattrs')
        pixel_checks.append(dict(tag=tag,mode=mode,preview=f.get('se_e_ui',1)==4,bytes=len(bits)+1000,sha256=hashlib.sha256(bits+attrs).hexdigest()))

'''+source[b:]
 oldforeign="        assert f.m.read(f.s['se_reu_logical_owner']+250)==0xA5\n        assert f.m.read(f.s['se_reu_map']+250)==249 and newowners[249]==0xA5"
 assert oldforeign in source
 source=source.replace(oldforeign,"        for logical,bank in held:\n            assert f.m.read(f.s['se_reu_logical_owner']+logical)==0xa5 and f.m.read(f.s['se_reu_map']+logical)==bank and newowners[bank]==0xa5")
 # Host clipboard readback uses disposable row scratch, not doc-root cache8000.
 source=source.replace("f.put('se_object_c64',0x8000,2)","f.put('se_object_c64',0x8800,2)").replace('f.read(0x8000,n)','f.read(0x8800,n)')
 source=source.replace("        assert f.merged()==data,(tag,'canonical source',len(data),len(f.merged()))","        nonlocal piece_peak\n        assert f.merged()==data,(tag,'canonical source',len(data),len(f.merged()))\n        piece_peak=max(piece_peak,sum(f.read(f.s['se_doc_roots']+i*8,8)[1]for i in range(f.get('se_doc_root_count',1))))\n        if tag.startswith('transaction-') and int(tag.split('-')[-1])%8 in (0,1,2,3) or tag.startswith(('above64KiB','preview-','unfold-all-')):pixels(tag)")
 a=source.index('                # Random edits can leave');b=source.index('                # Actual read-only preview',a)
 block=source[a:b];source=source[:a]+'                if PHYSICAL>=32:\n'+textwrap.indent(block,'    ')+source[b:]
 a=source.index('        # A real canonical offset above65535');b=source.index('        result=dict(',a)
 source=source[:a]+'        if PHYSICAL>=32:\n'+textwrap.indent(source[a:b],'    ')+source[b:]
 source=source.replace("        checks.append(dict(tag=tag,", "        assert f.get('se_h_cursor',2)<=f.get('se_h_end',2) and 1<=f.get('se_h_current',4)<=f.get('se_h_counter',4)\n        assert f.get('se_h_dirty',1)==int(f.get('se_h_current',4)!=f.get('se_h_saved',4))\n        checks.append(dict(tag=tag,")
 source=source.replace("        f.source(data);seed_foreign();catalog=f.catalog()", "        dll.ca_config(f.s['se_reu_physical_owner'],f.s['object_owner']);dll.ca_baseline(f.m.handle)\n        f.source(data);seed_foreign();catalog=f.catalog()",1)
 source=source.replace("        check('small-final')", """        check('small-final')
        before,oldowners=f.reu(),owners();f.audit_begin();f.command(50);goto(0);old=data
        raw=fold.geos.native_text('Q'*32)
        for byte in raw:f.key(byte)
        data=raw+old;f.command(2);assert f.merged()==data
        f.command(16);assert f.merged()==old,('repeated32 undo',)
        f.command(17);assert f.merged()==data,('repeated32 redo',)
        check('repeated32');pixels('repeated32');foreign(before,oldowners,'repeated32')
        events.append(dict(turn='repeated32',operation='insert-group+UndoRedo',mode=f.get('se_mode',1),start=0,delta=32))""")
 source=source.replace('checkpoint_max_objects=high_objects,peak_instructions=f.peak,','checkpoint_max_objects=high_objects,peak_instructions=f.peak,physical_banks=PHYSICAL,piece_peak=piece_peak,pixel_checks=pixel_checks,fragmentation=fragmentation,baseline_proofs=baseline_proofs,observed_STA_bank_peak=dll.ca_info(0),observed_STA_object_peak=dll.ca_info(1),observed_owner_stores=dll.ca_info(2),')
 source=source.replace("scope='Actual public all-mode seeded", "scope='Registered59 CPU scoped profile;16bank no storedfold/far phase;32bank fullfold/far; independentpixels and actualfragmentalloc. Actual public all-mode seeded")
 ns=dict(vars(old),runner=capacity.runner,fold=proxy,PHYSICAL=physical,semantic=semantic,cache=cache,D81Image=D81Image,pack_catalog=pack_catalog,preview_render=preview_render)
 exec(compile(source,str(out/'executed-soak.py'),'exec'),ns)
 try:
  result=ns['run'](out,base,rounds,seed);result['registered_seal']=seal;result['mutation_history_operations']=sum(3 for e in result['events']if e['delta'])+(12 if physical==32 else 0);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:(out/'executed-soak.py').write_text(source)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',type=int,choices=[16,32],default=32);p.add_argument('--rounds',type=int,default=64);p.add_argument('--seed',type=lambda n:int(n,0),default=0x53454f53);a=p.parse_args();out=ROOT/'build/stress-registered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks,a.rounds,a.seed)
