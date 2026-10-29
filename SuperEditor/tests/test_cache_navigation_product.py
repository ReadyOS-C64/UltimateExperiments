"""Packaged54 navigator: no private build, code patch or image substitution.

CPU IEC/font fixture transports are explicit seams. Public commands and real
resident jobs select the packaged C23/C26/C35/C39 workers. This is not native
IRQ/cold-D81 qualification; the independent native gate is parent-owned.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, inspect, json, sys, types, zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline_navigation as shared
observer,plain=shared.observer,shared.plain
DEFAULT=ROOT/'build/cache-editor-product/20261026T045019460982Z/fixture'
RELEASE=ROOT/'build/cache-inline-navigation/20261026T044712100925Z/release.json'
REFERENCE=ROOT/'agentsworking/evidence/M8/20261026T044932522126Z-cache-inline-navigation'


def matrix_capture(out,g,fonts,tag):
    # Reuse the released independent state/pixel/REU matrix without changing
    # any emulated instruction/field. The sole verifier addition saves PNGs.
    text=inspect.getsource(shared.matrix)
    needle='frames.append(item);print('
    assert text.count(needle)==3
    text=text.replace(needle,"observer.geos.png(bits,attrs,out/(item['tag']+'.png'));"+needle)
    (out/'matrix-verifier.py').write_text(text)
    env=dict(shared.__dict__);exec(compile(text,str(out/'matrix-verifier.py'),'exec'),env)
    return env['matrix'](out,g,fonts,tag)


def run(out,fixture):
    released=json.loads(RELEASE.read_text())
    source=ROOT/'tests/test_cache_inline_navigation.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==released['sources'][str(source.relative_to(ROOT))]
    # Accidental use of the private builder is a verifier failure.
    def forbidden(*a,**k):raise AssertionError('packaged test must not build private images')
    shared.build=forbidden
    g=observer.Gate(out,fixture);f=g.f
    assert len(g.identity['names'])==54
    assets={k:hashlib.sha256(v).hexdigest()for k,v in f.assets.items()}
    assert all(f.assets[k]==(g.frozen/'build/overlays'/(k+'.seo')).read_bytes()for k in f.assets)
    resident=hashlib.sha256(f.read(0x1000,0x2f00)).hexdigest()
    settle=inspect.getsource(observer.geos.grid.editor_fixture.EditorFixture.settle).replace('25000','200000')
    env={};exec('\n'.join(x[1:]for x in settle.splitlines()),env);f.settle=types.MethodType(env['settle'],f)
    fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
    targets=[('C23','geosnav'),('C20','geosline'),('C24','geossema'),('C26','geosinln'),('C35','inln'),('C37','page'),('C39','line')]
    g.dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*([0xb010]*len(targets))),(C.c_uint8*len(targets))(*([2]*len(targets))),(C.c_uint8*len(targets))(*(g.identity['names'].index(v[1])+1 for v in targets)),(C.c_uint8*(16*len(targets)))())
    cases=[];broad=[]
    try:
        data=observer.geos.native_text('**')+b'x'*4092+observer.geos.native_text('**\rNext.')
        for preset in('plain','markdown'):
            for target in(3072,len(data)):
                f.source(data);f.typed(observer.geos.native_text('syntax '+preset));f.command(99);f.render()
                before=g.reu();stable=g.stable();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dma=f.get('se_reu_dma_calls',2);trace=[];original=f.call
                def tracked(name,a=0):
                    if name=='se_editor_service'and f.get('se_e_job',1)==12:trace.append(tuple(f.read(0x9135,2)))
                    return original(name,a)
                f.call=tracked;g.dll.pb_begin()
                try:
                    if target==len(data):f.command(35)
                    else:
                        f.position(target);r=f.call('se_editor_reveal');assert not r.p&1;f.settle()
                finally:g.dll.pb_end();f.call=original
                elapsed=f.total_instructions-start;navloads=(f.get('se_overlay_loads',2)-loads)&65535;navdma=(f.get('se_reu_dma_calls',2)-dma)&65535
                counts={n:int(g.dll.pb_get(i))for i,(n,_)in enumerate(targets)}
                assert f.get('se_hot_caret')==target and g.stable()==stable and g.reu()==before and f.merged()==data
                assert not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))and f.read(0xc600,1024)==f.shim
                if preset=='plain':assert all(counts[k]==0 for k in('C24','C26','C35','C37','C39'))
                else:
                    assert(26,6)in trace and(35,0)in trace and(26,7)in trace and(23,1)in trace
                    if target==3072:assert(39,0)in trace
                    else:assert counts['C39']==0 and counts['C24']==0,'targeted bottom must skip prior logical body'
                audit=g.audit_begin();f.render();g.audit_end(audit,'long-'+preset+str(target))
                bits,attrs,_=plain.expected(f,data,fonts,0 if preset=='plain'else 1)
                assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
                tag=preset+'-'+str(target);observer.geos.png(bits,attrs,out/(tag+'.png'))
                item=dict(tag=tag,preset=preset,target=target,top=f.get('se_v_top'),instructions=elapsed,loads=navloads,dma=navdma,entries=counts,trace=trace,bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());cases.append(item)
                print('PUBLIC PASS',{k:v for k,v in item.items()if k!='trace'},flush=True)
        expected=json.loads((REFERENCE/'20261026T044548688541Z/result.json').read_text())
        prior={x['tag']:x for x in expected['broad']if x['variant']=='candidate'}
        for repeat in range(2):
            d=out/('matrix'+str(repeat));d.mkdir();rows=matrix_capture(d,g,fonts,'canonical-'+str(repeat));assert len(rows)==26
            for x in rows:
                p=prior[x['tag']];assert x['state']==p['state']and x['bitmap']==p['bitmap']and x['attrs']==p['attrs'],('private-reviewed-ancestry',x['tag'])
            broad+=rows
        assert len(broad)==52
        assert assets=={k:hashlib.sha256(v).hexdigest()for k,v in f.assets.items()}
        assert resident==hashlib.sha256(f.read(0x1000,0x2f00)).hexdigest(),'resident payload changed'
        # Archive the exact verifier/module inputs used; no images are rebuilt.
        with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
            for folder in('tests','tools'):
                for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
        result=dict(status='PASS',identity=g.identity,packaged_assets=assets,resident_runtime_sha256=resident,cases=cases,broad=broad,frames=len(cases)+len(broad),exact_mode='canonical-packaged-no-substitutions',scope=__doc__,reference=str(REFERENCE.relative_to(ROOT)))
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('RESULT PASS',result['frames'],flush=True);return result
    except BaseException:
        (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
    finally:f.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args()
    out=ROOT/'build/cache-navigation-product'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
