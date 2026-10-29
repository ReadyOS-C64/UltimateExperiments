"""Actual sealed62 presentation counters, including C41 and R34.

All old presentation/observer assertions remain in the released original. This
wrapper adds frozen byte-matched new/lexical targets and an R-slot observation
kind. No capsule swap, source/parser seed, shared build or native/hardware work.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,inspect,json,shutil,zipfile
import test_presentation_bypass as original
from d81_image import D81Image

ROOT=original.ROOT
BASE=ROOT/'build/cache-rebase-cold62-prep/fixture'
PROJECT=ROOT/'build/cache-rebase-cold62-prep/project'
FUNCTIONS=('entry','se_sm_init','se_sm_feed','se_sm_finish','se_si_init','se_si_feed','se_si_finish','se_sl_init','se_sl_feed','se_sl_finish')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def authenticate(base):
    ident=json.loads((base/'freeze.json').read_text());report=json.loads((base/'build/editor-report.json').read_text())
    assert len(ident['names'])==len(set(ident['names']))==62
    assert sha(base/'build/editor.prg')==ident['prg_sha256']==report['sha256']
    assert sha(base/'build/supereditor.d81')==ident['disk_sha256']
    disk=D81Image((base/'build/supereditor.d81').read_bytes());binding=bytes.fromhex(report['resident_binding']['digest']);pairs=[]
    assert disk.read(b'SUPEREDITOR',kind=2).data==(base/'build/editor.prg').read_bytes()
    for name in ident['names']:
        p=base/f'build/overlays/{name}.seo';image=p.read_bytes();assert sha(p)==ident['assets'][name]
        assert image[20:36]==image[36:52]==binding and len(image)-36==int.from_bytes(image[8:10],'little')
        assert binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
        assert disk.read(name.upper().encode(),kind=1).data==image;pairs.append(tuple(image[5:7]))
    assert len(set(pairs))==62 and pairs[-2:]==[(1,41),(0,34)]
    return dict(resident=ident['prg_sha256'],binding=binding.hex(),D81=ident['disk_sha256'],assets=62)


def capture(out,fixture,project):
    directory=out/'entry-labels';directory.mkdir(exist_ok=True)
    # Every normal pair is read from the frozen fixture. The two stage groups
    # were omitted by its original freezer, so borrow only byte-equal held
    # private-project outputs, never mutable shared aliases.
    groups=[(name,name,fixture/'build/overlays'/name,False)for name in original.WORKERS]
    groups += [(name,asset,fixture/'build/cache-editor'/asset,False)for name,asset in
               [('cachebuild','sema'),('cachequery','inln'),('cacheforward','page'),('cachesource','line')]]
    groups += [(name,asset,fixture/'build/lexical'/asset,False)for name,asset in
               [('lexgateway','edit'),('lexresolve','tail'),('lextransport','lex'),('lexproducer','ical'),('lexlink','ctrl')]]
    groups += [('rebase','parse',fixture/'build/cache-rebase/parse',False),('rebaseio','xform',fixture/'build/cache-rebase/xform',False)]
    groups += [('stage31','clex',project/'build/geos-prod/code-typing/stage',True),('stage32','type',project/'build/geos-prod/style-typing/stage',True)]
    names=json.loads((fixture/'freeze.json').read_text())['names'];targets=[];records={}
    for name,asset,path,staged in groups:
        image=(fixture/f'build/overlays/{asset}.seo').read_bytes();raw=path.with_suffix('.bin').read_bytes()
        assert raw==image[36:],(name,'incoherent raw/labels versus actual SEO',path)
        labels=original.symbols(path.with_suffix('.lbl'));slot=image[5]
        for ext in('.bin','.lbl','.map'):shutil.copy2(path.with_suffix(ext),directory/(name+ext))
        records[name]=dict(asset=asset,slot=slot,source=str(path),binary_sha256=hashlib.sha256(raw).hexdigest(),files={ext:sha(directory/(name+ext))for ext in('.bin','.lbl','.map')})
        for fn in FUNCTIONS:
            if fn not in labels:continue
            pc=0x5000 if staged and fn=='entry'else labels[fn]
            if staged:assert 0x5000<=pc<0x5000+len(raw)-32
            else:assert (0xb010 if slot else 0xa010)<=pc<(0xb000 if slot else 0xa000)+len(raw)
            targets.append(dict(name=name+':'+fn,pc=pc,kind=3 if staged else 2 if slot else 1,tag=0 if staged else names.index(asset)+1,signature=(raw[32:48]if staged else bytes(16)).hex()))
    assert len(targets)<=64,len(targets)
    assert any(t['name']=='rebase:se_sm_feed'for t in targets)
    assert any(t['name']=='rebaseio:entry'and t['kind']==1 for t in targets)
    assert any(t['name']=='lexproducer:se_sl_feed'for t in targets)
    (out/'entry-labels.json').write_text(json.dumps(records,indent=2)+'\n')
    return targets


def runner(out):
    # Extend only the read-only instruction observer: old C/stage cases are
    # unchanged; a real R34/36/37 PC is authenticated against active R-slot.
    text=inspect.getsource(original_runner)
    needle='if(pb_kind[i]==2 && zeropage_peddle_read(m,pb_active+1)!=pb_tag[i])continue;'
    assert text.count(needle)==1
    text=text.replace(needle,'if(pb_kind[i]==1 && zeropage_peddle_read(m,pb_active)!=pb_tag[i])continue;\n '+needle)
    namespace=dict(original.__dict__);exec(compile(text,str(Path(__file__))+'::Rslot-observer','exec'),namespace)
    return namespace['runner'](out)


original_runner=original.runner


def run(out,base,project):
    out.mkdir(parents=True);seal=authenticate(base)
    oldcapture,oldrunner=original.capture_labels,original.runner
    original.capture_labels=lambda target,fixture:capture(target,fixture,project)
    original.runner=runner
    try:result=original.run(out,base)
    finally:original.capture_labels,original.runner=oldcapture,oldrunner
    result.update(registered62_seal=seal,new_worker_scope='Actual C41 SM init/feed/finish and R34 entry, plus C39/C45/R36/R37/C47/C49 and existing workers/staged controls. Frozen byte-matched targets; no shared-label borrowing.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('REGISTERED62_PRESENTATION_PASS',len(result['records']),out,flush=True)
    return result


def lexical(out,base,project):
    """Genuine root5 construction, actual C41 edit, then preset bypass.

    Host setup uses the released source/provider seam and W_LOAD position helper;
    producer/linker/rebase BEGINs, refs, parser state and flags are never seeded.
    Render consumes the actual registered parent request/OP protocol.
    """
    import test_plain_geos as plain
    import test_cache_lexical_registered as registered
    import font_fixture
    out.mkdir(parents=True);seal=authenticate(base);targets=capture(out,base,project)
    original.geos.grid.editor_fixture.ROOT=original.geos.grid.cpu_editor.ROOT=font_fixture.ROOT=base
    identity=json.loads((base/'freeze.json').read_text())
    original.geos.grid.editor_fixture.NAMES=original.geos.grid.cpu_editor.NAMES=identity['names']
    dll=runner(out);f=original.fold.Fixture(out,base,dll,True)
    dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*(t['pc']for t in targets)),(C.c_uint8*len(targets))(*(t['kind']for t in targets)),(C.c_uint8*len(targets))(*(t['tag']for t in targets)),(C.c_uint8*(len(targets)*16)).from_buffer_copy(b''.join(bytes.fromhex(t['signature'])for t in targets)))
    fonts={n:(base/'fonts'/n).read_bytes()for n in original.geos.GEOS_FONTS+('native8.bin',)}
    frames=[];data=b'';calls=[];requests={};originalcall=f.call
    def call(name,a=0):
        if name=='se_editor_service'and f.get('se_e_job',1)==11:
            request=f.m.read(0x9135);op=f.m.read(0x9136)
            requests[request]=requests.get(request,0)+1;calls.append((request,op));calls[:]=calls[-256:]
        return originalcall(name,a)
    f.call=call
    def check(tag,caps,operation,*,readonly=False,source_edit=False):
        canonical=f.canonical();catalog=f.catalog();before=f.reu();started=f.total_instructions;calls.clear();requests.clear()
        dll.pb_begin()
        try:operation()
        finally:dll.pb_end()
        counts={t['name']:int(dll.pb_get(i))for i,t in enumerate(targets)}
        original.enforce(caps,counts)
        assert f.get('se_render_caps',1)==caps and f.merged()==data
        assert f.catalog()==catalog and f.read(0xc600,1024)==f.shim
        if not source_edit:assert f.canonical()==canonical,(tag,'analysis/render changed canonical state')
        assert not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_e_draw_busy'))
        assert f.m.read(0x912d)==0
        bits,attrs,_=plain.expected(f,data,fonts,caps)
        assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
        if readonly:
            assert f.canonical()==canonical
            after=f.reu();expected=bytearray(before);_,bank=f.raw_cache()
            for lo,hi in((0,64),(0x200,0xea88)):expected[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
            assert after==expected,(tag,'whole16MiB outside exactFE source/GTF')
        row=dict(tag=tag,caps=caps,counts=counts,instructions=f.total_instructions-started,root_request_counts=dict(requests),root_requests_last256=list(calls),source_sha256=hashlib.sha256(data).hexdigest(),pixels_sha256=hashlib.sha256(bits+attrs).hexdigest())
        frames.append(row);(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
        print('LEXICAL62_CASE',tag,{k:v for k,v in counts.items()if v},flush=True)
        return counts
    def force():f.key(0x8a);f.key(0x8a);original.drain(f)
    try:
        for language,prefix in(('basic','10 PRINT "Hi":REM '),('asm','label lda #42 ; ')):
            data=original.geos.native_text('Intro\r:::'+language+'\r'+prefix+'x'*5000+'\r:::\rMiddle ordinary words.\rTail.')
            f.source(data);f.put('se_status',1,1);f.typed(original.geos.native_text('syntax markdown'));f.command(99);f.command(77)
            c=check(language+'-markdown-baseline',1,lambda:original.drain(f))
            assert not sum(v for k,v in c.items()if ':se_sl_'in k)
            f.typed(original.geos.native_text('syntax full'))
            c=check(language+'-full-build',3,lambda:original.drain(f))
            lo,selected,root=registered.arena(f,f.reu())
            assert root[31]==5 and int.from_bytes(root[98:100],'little')==1
            body=data.index(original.geos.native_text(prefix));end=data.index(13,body)
            assert c['lexproducer:se_sl_feed']==end-body and c['lexproducer:se_sl_init']==c['lexproducer:se_sl_finish']==1
            assert c['lexlink:entry']>0 and c['geoslex:se_sl_feed']==0
            c=check(language+'-full-retained-window',3,force,readonly=True)
            assert c['lexgateway:entry']>0 and c['lexproducer:se_sl_feed']==c['geoslex:se_sl_feed']==0
            at=data.index(original.geos.native_text('ordinary'))+3
            f.position(at);original.drain(f)
            lo,selected,oldroot=registered.arena(f,f.reu());assert oldroot[31]==5
            q=original.geos.native_text('Q');f.key(q[0]);data=data[:at]+q+data[at:];f.command(77)
            assert f.get('se_bc_count',1)==2
            before=f.reu();stable=f.canonical();journal=oldroot[30]
            c=check(language+'-full-C41-rebase',3,lambda:original.drain(f))
            assert c['rebase:entry']>0 and c['rebase:se_sm_feed']>0 and c['rebaseio:entry']>0
            assert c['lexproducer:se_sl_feed']==c['geoslex:se_sl_feed']==0 and f.get('se_bc_count',1)==0
            assert requests.get(41,0)>0,('actual root C41 request',requests)
            assert f.canonical()==stable,'C41 render changed canonical source/history'
            after=f.reu();lo2,alternate,newroot=registered.arena(f,after);assert lo2==lo and newroot[31]==5 and alternate!=selected
            assert after[lo+selected:lo+selected+128]==oldroot
            pair=newroot[104];assert pair in(12,14)
            n=int.from_bytes(newroot[112:115],'little');lexused=int.from_bytes(after[lo+(pair+1)*4096+21:lo+(pair+1)*4096+23],'little')
            expected=bytearray(before);_,fe=f.raw_cache()
            for a,b in((0,64),(0x200,0xea88)):expected[fe*65536+a:fe*65536+b]=after[fe*65536+a:fe*65536+b]
            for a,b in((alternate,alternate+128),(0x100+pair*8,0x100+(pair+2)*8),(0x900+journal*32,0x900+(journal+2)*32),(pair*4096,pair*4096+64+n*96),((pair+1)*4096,(pair+1)*4096+64+lexused)):
                expected[lo+a:lo+b]=after[lo+a:lo+b]
            assert after==expected,(language,'whole16MiB outside exactCOW/sourceFE')
            f.typed(original.geos.native_text('syntax markdown'))
            c=check(language+'-markdown-after-root5-C41',1,force,readonly=True)
            assert not sum(v for k,v in c.items()if ':se_sl_'in k)
            f.typed(original.geos.native_text('syntax plain'))
            c=check(language+'-plain-after-root5-C41',0,force,readonly=True);assert not any(c.values())
            # Actual pending Plain edit must not accidentally enter C41 or a
            # retained-lexer helper just because a root5 object still exists.
            pos=f.get('se_hot_caret');data=data[:pos]+q+data[pos:]
            c=check(language+'-plain-pending-after-root5',0,lambda:(f.key(q[0]),original.drain(f)),source_edit=True)
            assert not any(c.values())
        result=dict(status='PASS',identity=seal,records=frames,targets=targets,scope=lexical.__doc__)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
    except BaseException as error:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(error),trace=calls,frames=frames,state=f.debug()),indent=2)+'\n')
        (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
    finally:dll.pb_end();f.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--project',type=Path,default=PROJECT);p.add_argument('--lexical-only',action='store_true');p.add_argument('--source-only',action='store_true');a=p.parse_args()
    assert not(a.lexical_only and a.source_only)
    out=ROOT/'build/cache-rebase-presentation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
    results={}
    if not a.lexical_only:results['source']=run(out/'source',a.fixture.resolve(),a.project.resolve())
    if not a.source_only:results['lexical']=lexical(out/'lexical',a.fixture.resolve(),a.project.resolve())
    (out/'result.json').write_text(json.dumps(dict(status='PASS',groups={k:dict(records=len(v['records']))for k,v in results.items()}),indent=2)+'\n')
