"""Actual registered62 root5 cache and controlled standalone lifecycle adapter.
CPU-only: genuine Full construction, packaged C29/R26, trusted fresh bootstrap.
No canonical/shared build, native, Git, hardware, old-stack or ReadyOS claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,inspect,json,os,re,shutil,zipfile
import test_cache_lexical_resume as prior
import test_lifecycle_editor as component
import test_cache_rebase_presentation as presentation
import test_geos_preview_vice as preview_native
import editor_settings
geos=prior.geos;reg=prior.reg;plain=prior.plain;helper=prior.helper;files=prior.files;ROOT=prior.ROOT
BASE=ROOT/'build/cache-rebase-canonical-working/20261026T224329418891Z/fixture'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def project_view(out,base):
    presentation.authenticate(base)
    p=out/'frozen-project';p.mkdir();(p/'src/fold').mkdir(parents=True)
    with zipfile.ZipFile(base/'product-sources.zip')as z:(p/'src/fold/source.inc').write_bytes(z.read('src/fold/source.inc'))
    (p/'build').symlink_to(base/'build',target_is_directory=True)
    for name in ('lifectrl','lifecopy','geoslex'):
        assert(base/f'build/overlays/{name}.bin').read_bytes()==(base/f'build/overlays/{name}.seo').read_bytes()[36:]
    assert(base/'build/lexical/ical.bin').read_bytes()==(base/'build/overlays/ical.seo').read_bytes()[36:]
    return p


class Fixture(files.Fixture):
    def reu(self):
        raw=C.create_string_buffer(16*1024*1024);self.dll.gm_reu(self.m.handle,len(raw),raw);return raw.raw
    def call(self,name,a=0):
        job=self.get('se_e_job',1);request=self.m.read(0x9135);op=self.m.read(0x9136)
        r=super().call(name,a)
        if name=='se_editor_service'and job==11:self.root_trace=getattr(self,'root_trace',[])+[(request,op,r.a,r.p&1,self.m.read(0x9135),self.m.read(0x9136))]
        return r


def source_state(f):
    return {n:f.read(f.s[n],w).hex()for n,w in [('se_ef_state',45),('se_editor_settings',64),('se_mode',1),('se_e_ui',1),('se_r_presentation',1),('se_l_pan',3),('se_v_top',3),('se_l_preferred',3),('se_l_manual',1),('se_clip_token',5),('se_clip_length',3),('se_f_current_name',18)]}


def font_guard(f,base,reu):
    from d81_image import D81Image
    pack=D81Image((base/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
    assert f.get('se_gf_state',1)==0xa5
    handles=f.read(f.s['se_gf_state']+1,2);assert all(handles)and handles[0]!=handles[1]
    for i,h in enumerate(handles):
        p=f.m.read(f.s['se_reu_map']+h);assert p and f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+p)==0xfd
        payload=pack[i*65536:(i+1)*65536];assert reu[p*65536:p*65536+len(payload)]==payload
    return dict(handles=list(handles),pack_sha256=hashlib.sha256(pack).hexdigest(),two_capabilities_exact=True)


def render(f,dll,base,project,data,fonts,tag,out):
    before=f.reu();canonical=f.canonical();catalog=f.catalog();bc_before=helper.bc_state(f);lo,selected,root=reg.arena(f,before)
    producer=reg.labels(project/'build/lexical/ical.lbl');strict=reg.labels(project/'build/overlays/geoslex.lbl')
    f.trace=[];f.root_trace=[];started=f.total_instructions
    dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,producer['se_sl_feed'],0,0,strict['se_sl_feed'])
    f.render();pf,sf=dll.gm_metric(0),dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
    after=f.reu();lo2,newselected,newroot=reg.arena(f,after);assert lo2==lo
    bits,attrs,_=plain.expected(f,data,fonts,3);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
    assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim
    wanted=bytearray(before);_,bank=f.raw_cache()
    for a,b in((0,64),(0x200,0xea88)):wanted[bank*65536+a:bank*65536+b]=after[bank*65536+a:bank*65536+b]
    c41=sum(t[0]==41 for t in f.root_trace)
    published=newselected!=selected
    c41_routes=[t for t in f.root_trace if t[0]==41 and t[4]==21]
    if c41:assert c41_routes and all(t[2]==1 and not t[3]for t in c41_routes),(tag,'realC41 explicit C21 handoff',c41_routes)
    cow=[]
    if published:
        assert c41 and newselected!=selected and newroot[31]==5 and after[lo+selected:lo+selected+128]==root
        pair=newroot[104];assert pair in(12,14)
        n=int.from_bytes(newroot[112:115],'little');used=int.from_bytes(after[lo+(pair+1)*4096+21:lo+(pair+1)*4096+23],'little');journal=root[30]
        cow=[(newselected,newselected+128),(0x100+pair*8,0x100+(pair+2)*8),(0x900+journal*32,0x900+(journal+2)*32),(pair*4096,pair*4096+64+n*96),((pair+1)*4096,(pair+1)*4096+64+used)]
        for a,b in cow:wanted[lo+a:lo+b]=after[lo+a:lo+b]
    else:
        assert after[lo:lo+65536]==before[lo:lo+65536],(tag,'whole53 unchanged on read-only reuse/fallback')
        assert helper.bc_state(f)==bc_before,(tag,'miss/reuse changed observer authority/queue')
    assert after==wanted,(tag,'whole16MiB outside exactFE/COW spans')
    assert not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned'))
    result=dict(tag=tag,instructions=f.total_instructions-started,producer_feeds=pf,strict_feeds=sf,gateway_calls=sum(t[0]==45 for t in f.trace),producer_begins=sum(t[:2]==(47,0)for t in f.trace),linker_begins=sum(t[:2]==(49,0)for t in f.trace),C41_requests=c41,C41_to_C21=c41_routes,COW_published=published,COW_relative_spans=cow,flags=f.get('se_bc_flags',1),BC=helper.bc_state(f),root_FS59_equal=helper.fs_identity(f,project)==newroot[32:91],fonts=font_guard(f,base,after))
    (out/(tag+'.json')).write_text(json.dumps(result,indent=2)+'\n');geos.png(bits,attrs,out/(tag+'.png'));print('REBASE_LIFE_FRAME',result,flush=True);return result


def old_snapshot_refusal(f,dll,base,project,out):
    """Actual post-OPEN provider graph cannot restore an older saved image."""
    out.mkdir();raw=(base/'build/overlays/lifecopy.seo').read_bytes()[36:];labels=reg.labels(project/'build/overlays/lifecopy.lbl')
    f.m.load(0xa000,raw);canonical=f.canonical();before=f.reu();calls=[]
    for index in range(200):
        prior=f.read(0,65536);r,n=f.fast_call(labels['se_lc_restore_begin']if not index else labels['se_lc_copy_step']);calls.append(n);after=f.read(0,65536);wanted=bytearray(prior)
        for a,b in((0x100,0x200),(0x700,0x800),(0x820,0x82e),(0x880,0x8c0),(0xdf00,0xdf0b)):wanted[a:b]=after[a:b]
        assert after==wanted,'old snapshot validation wrote warm/foreign RAM'
        assert f.reu()==before and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
        if r.p&1:break
        assert r.a==1
    assert r.p&1 and r.a==0xde,'real changed provider graph must refuse old image'
    # The trusted direct R26 check displaced a slot, so actual resident policy
    # disarms it before any further ordinary foreground code is considered.
    assert not f.call('se_overlay_unverify').p&1
    result=dict(status='PASS',error=r.a,calls=len(calls),maximum_instructions=max(calls),whole16MiB_exact=True,warm_RAM_unchanged=True,scope='Old snapshot versus actual FileOpen/new-baseline provider allocations; no old context restored')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def run(out,base,smoke=False,only_policy=None,only_language=None):
    out.mkdir(parents=True);project=project_view(out,base);identity=json.loads((base/'freeze.json').read_text());assert len(identity['names'])==62
    geos.grid.cpu_editor.ROOT=geos.grid.editor_fixture.ROOT=prior.reg.automatic.geos.grid.cpu_editor.ROOT=base
    geos.grid.cpu_editor.NAMES=geos.grid.editor_fixture.NAMES=identity['names']
    import font_fixture
    font_fixture.ROOT=base
    dll=geos.grid.runner(out);f=None;cases=[];fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
    try:
        for language in((only_language,)if only_language else('basic',)if smoke else('basic','asm')):
            for policy in((only_policy,)if only_policy else('unchanged',)if smoke else('unchanged','pending','motion','after-code')):
                if f:f.close()
                f=Fixture(out,base,dll,True)
                data=geos.native_text('Intro\r:::'+language+'\r'+('10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; '))+geos.native_text('x')*5000+geos.native_text('\r:::\rMiddle ordinary words.\rTail.')
                # Continue the actual decoded62 cold startup; do not reset or
                # reimport its assets/analysis state through source().
                assert not f.call('se_clip_init').p&1
                name=('CACHE-'+language).upper().encode();f.fs[name]=data;f.start('f7','O');f.enter_name(name,True);f.settle()
                assert f.merged()==data and f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==name and f.get('se_f_current_device',1)==8
                assert not f.channels and f.selected_in is None and f.selected_out is None
                f.typed(geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render()
                producer=reg.labels(project/'build/lexical/ical.lbl');strict=reg.labels(project/'build/overlays/geoslex.lbl');f.trace=[]
                dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,producer['se_sl_feed'],0,0,strict['se_sl_feed'])
                f.typed(geos.native_text('syntax full'));f.render();feeds=dll.gm_metric(0);strictfeeds=dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
                body=data.index(geos.native_text('10 PRINT'if language=='basic'else'label'));end=data.index(13,body)
                assert feeds==end-body and strictfeeds==0 and sum(t[:2]==(47,0)for t in f.trace)==sum(t[:2]==(49,0)for t in f.trace)==1
                lo,selected,root=reg.arena(f,f.reu());assert root[31]==5 and root[98:100]==b'\1\0'and f.get('se_bc_flags',1)&129==129 and not f.get('se_bc_flags',1)&(4|8|32|64)
                assert helper.fs_identity(f,project)==root[32:91]
                tag=language+'-'+policy
                if policy=='pending':
                    f.key(geos.native_text('Q')[0]);data=geos.native_text('Q')+data;assert f.get('se_hot_pending',1)==1 and f.get('se_bc_count',1)>0
                before=source_state(f);bc=helper.bc_state(f);font_guard(f,base,f.reu())
                restored=helper.suspend_resume(f,dll,base,project,out/(tag+'-capture'))
                assert source_state(f)==before and helper.bc_state(f)==bc and not f.m.read(0xcbd5),'all original semantic state preserved; fontwindow revoked'
                if policy=='motion':f.command(2)
                if policy=='after-code':
                    f.typed(geos.native_text('goto 5'))
                    for _ in range(10):f.key(0x1d)
                    at=f.get('se_hot_caret');assert data[at:at+1]!=b'\r' and at>data.index(geos.native_text('Middle'))
                    f.render();f.key(geos.native_text('Q')[0]);data=data[:at]+geos.native_text('Q')+data[at:]
                    f.command(77);assert f.get('se_bc_count',1)==2,'actualSPLICE+REKEY before supportedC41'
                f.key(0x8a);f.key(0x8a)
                frame=render(f,dll,base,project,data,fonts,tag+'-resumed',out)
                assert frame['producer_begins']==frame['linker_begins']==frame['producer_feeds']==0
                if policy=='unchanged':assert frame['strict_feeds']==0 and frame['gateway_calls']>0 and frame['root_FS59_equal']
                elif policy=='pending':assert frame['C41_requests']>0 and not frame['COW_published']and f.get('se_bc_count',1)>0 and frame['strict_feeds']>0
                elif policy=='after-code':assert frame['COW_published']and f.get('se_bc_count',1)==0 and frame['strict_feeds']==0
                else:assert frame['strict_feeds']>0 and not frame['root_FS59_equal']and f.get('se_bc_count',1)==f.get('se_bc_ticket',4)==0
                file_result=None
                if policy=='unchanged'and not smoke:
                    file_result=files.save_reopen(f,data,language,out/(tag+'-files'))
                    f.trace=[];dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,producer['se_sl_feed'],0,0,strict['se_sl_feed']);f.render();freshfeeds=dll.gm_metric(0);freshstrict=dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
                    _,_,freshroot=reg.arena(f,f.reu());assert freshroot[31]==5 and freshroot[98:100]==b'\1\0' and freshfeeds==end-body and not freshstrict
                    assert sum(t[:2]==(47,0)for t in f.trace)==sum(t[:2]==(49,0)for t in f.trace)==1
                    f.key(0x8a);f.key(0x8a);warm=render(f,dll,base,project,data,fonts,tag+'-reopened-warm',out)
                    assert warm['gateway_calls']>0 and not warm['producer_feeds']and not warm['strict_feeds']
                    file_result.update(fresh_producer_feeds=freshfeeds,fresh_root5=True,reopened_warm=warm,old_snapshot=old_snapshot_refusal(f,dll,base,project,out/(tag+'-old-snapshot')))
                cases.append(dict(tag=tag,construction_feeds=feeds,lifecycle=restored,frame=frame,files=file_result))
                (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
        result=dict(status='PASS',identity=identity,cases=cases,scope=__doc__,source_sha256=sha(Path(__file__)))
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
    except BaseException:
        if f:
            (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure.json').write_text(json.dumps(dict(state=f.debug(),trace=getattr(f,'root_trace',[])[-128:]),indent=2)+'\n')
        raise
    finally:
        if f:f.close()


def packaged_pair(out,base):
    """Use actual sealed pair, never replacement images or mutable labels."""
    out.mkdir(parents=True);images={}
    for name in ('lifectrl','lifecopy'):
        raw=(base/f'build/overlays/{name}.bin').read_bytes();image=(base/f'build/overlays/{name}.seo').read_bytes();assert raw==image[36:]
        images[name]=image
        for ext in('bin','lbl','map','seo'):os.link(base/f'build/overlays/{name}.{ext}',out/(name+'.'+ext))
    (out/'resume.bin').write_bytes(images['lifectrl'][36+0x800:36+0x900]);return images


def frozen_catalog(base,native):
    from d81_image import D81Image
    return preview_native.pack_catalog(D81Image((base/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data,native)


def legacy_faults(out,base):
    out.mkdir(parents=True);presentation.authenticate(base)
    geos.grid.cpu_editor.ROOT=geos.grid.editor_fixture.ROOT=base;identity=json.loads((base/'freeze.json').read_text());geos.grid.cpu_editor.NAMES=geos.grid.editor_fixture.NAMES=identity['names']
    import font_fixture
    font_fixture.ROOT=base
    source=inspect.getsource(component.run)
    old="frozen,identity=fold.geos.freeze(out,base);images=build(out/'leaf',frozen)";assert source.count(old)==1
    source=source.replace(old,"frozen=base;identity=json.loads((base/'freeze.json').read_text());images=packaged_pair(out/'leaf',frozen)")
    old="f.m.read(f.s['image_slot']+i)==0";assert source.count(old)==1;source=source.replace(old,"(f.m.read(f.s['image_slot']+i)&1)==0")
    old="if not (frozen/'genuine').exists():shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')";assert source.count(old)==1;source=source.replace(old,"pass # catalog comes only from the frozen D81/fontpack below")
    old="FontCatalog(frozen/'genuine/catalog.json',native=fonts['native8.bin'])";assert source.count(old)==1;source=source.replace(old,"frozen_catalog(frozen,fonts['native8.bin'])")
    namespace=dict(vars(component),packaged_pair=packaged_pair,frozen_catalog=frozen_catalog);exec(compile(source,str(Path(__file__))+'::legacy62-pair','exec'),namespace)
    (out/'source-adaptation.py').write_text(source)
    records=[]
    for tag,mode,preview in(('source40',0,False),('source60',1,False),('source80',2,False),('literal',3,False),('preview',3,True)):
        dest=out/tag;dest.mkdir();r=namespace['run'](dest,base,mode=mode,skip_faults=bool(records),preview=preview);records.append(dict(tag=tag,**r))
    result=dict(status='PASS',cases=records,adaptations='Only packaged-image accessor (no rebuild), declared managed slot-bit mask, frozen-D81 preview catalog; original abort/header/forgery/payload/provider/restore/pending/editUndo/shim oracles unchanged.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def extended_states(out,base):
    """Retain released custom-settings/selection/history/File/failure oracles."""
    import test_lifecycle_extended as extended
    out.mkdir(parents=True);presentation.authenticate(base)
    source=inspect.getsource(extended.run)
    old="frozen,identity=semantic.geos.freeze(out,previous);images=component.build(out/'leaf',frozen)";assert source.count(old)==1
    source=source.replace(old,"frozen=previous;identity=json.loads((previous/'freeze.json').read_text());images=packaged_pair(out/'leaf',frozen)")
    old="f.m.read(f.s['image_slot']+i)==slot";assert source.count(old)==1;source=source.replace(old,"(f.m.read(f.s['image_slot']+i)&1)==slot")
    old="p=f.m.read(f.s['se_reu_map']+h);want[p*65536:(p+1)*65536]=after[p*65536:(p+1)*65536]";assert source.count(old)==1
    source=source.replace(old,"p=f.m.read(f.s['se_reu_map']+h)\n    assert p and f.m.read(f.s['se_reu_physical_owner']+p)==0xfe\n    for a,b in((0,64),(0x200,0xfba9)):want[p*65536+a:p*65536+b]=after[p*65536+a:p*65536+b]")
    namespace=dict(vars(extended),packaged_pair=packaged_pair);exec(compile(source,str(Path(__file__))+'::extended62','exec'),namespace)
    (out/'source-adaptation.py').write_text(source)
    result=namespace['run'](out,base)
    result['frozen_only_source_profile']='Exact packaged62 pair/labels; managed slot-bit adaptation; old wholeFE negative recovery guard tightened to authenticated header64/source0200..FBA8. No53mask.'
    (out/'registered-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');p.add_argument('--policy',choices=('unchanged','pending','motion','after-code'));p.add_argument('--language',choices=('basic','asm'));p.add_argument('--suite',choices=('core','faults','state','all'),default='all');a=p.parse_args();out=ROOT/'build/cache-rebase-lifecycle'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);results={}
    if a.suite in('core','all'):results['core']=run(out/'core',a.fixture.resolve(),a.smoke,a.policy,a.language)
    if a.suite in('faults','all')and not a.smoke:results['faults']=legacy_faults(out/'faults',a.fixture.resolve())
    if a.suite in('state','all')and not a.smoke:results['state']=extended_states(out/'state',a.fixture.resolve())
    (out/'result.json').write_text(json.dumps(dict(status='PASS',groups={k:len(v['cases'])for k,v in results.items()},source_sha256=sha(Path(__file__))),indent=2)+'\n')
