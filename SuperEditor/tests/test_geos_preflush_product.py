"""Actual public BACK through coherently linked private resident/C33/C23/C24."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,zipfile
import test_geos_navigation_previous_candidate as prior
geos=prior.geos
ROOT=Path(__file__).resolve().parents[1]

def run(out,project):
    old=geos.ROOT;old_retention=geos.retention.ROOT;old_file=geos.__file__
    (project/'tests').mkdir(exist_ok=True)
    shutil.copy2(old_file,project/'tests/test_geos_editor.py')
    try:
        geos.ROOT=geos.retention.ROOT=project
        geos.__file__=str(project/'tests/test_geos_editor.py')
        frozen,identity=geos.freeze(out)
    finally:
        geos.ROOT=old;geos.retention.ROOT=old_retention;geos.__file__=old_file
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    dll=geos.grid.runner(out)
    f=prior.Fixture(out,frozen,dll,True)
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    with zipfile.ZipFile(frozen/'product-sources.zip') as z:
        local_render = b'gsc_seed_done:' in z.read('src/render/geos/page.s')
    cases=[]
    try:
        for far in [False,True]:
            prefix=geos.native_text('prefix\r')*(9400 if far else 2)
            raw=prefix+geos.native_text('# Heading words.\rFollowing row.\rTail.')
            at=len(prefix)+17
            f.source(raw);f.command(99);f.position(at)
            f.put('se_v_top',at) #viewport setup; realC21 creates actual parser records
            f.render()
            before=f.reu();generation=f.get('se_doc_generation',2)
            f.requests=[];f.tracing=True;used=f.total_instructions
            f.key(0x14) # actual publickey dispatch, no direct C6/reveal/navigation call
            navigation_instructions=f.total_instructions-used
            f.tracing=False
            changed=raw[:at-1]+raw[at:]
            assert f.get('se_doc_generation',2)==generation and f.get('se_hot_pending',1)==1
            assert f.get('se_v_top')==len(prefix) and f.merged()==changed
            assert dict(id=24,op=3) in f.requests and len(f.requests)<40
            assert f.reu()==before,'pendingpublicBACK must not commit or mutate REU'
            assert not any(f.get(n,1) for n in ['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'])
            assert navigation_instructions<500000,'publicnavigation unexpectedly rescanned farprefix'
            canonical=f.canonical();used=f.total_instructions
            f.render();render_instructions=f.total_instructions-used
            if far and local_render:
                assert render_instructions < 2000000, 'new C21 consumer still reparses farprefix'
            bitmap,attrs,_,_=prior.heading.semantic.expected(f,changed,fonts)
            assert f.read(0x6000,8000)==bitmap and f.read(0x4000,1000)==attrs
            assert f.canonical()==canonical and f.read(0xc600,1024)==f.shim
            tag=('far64k' if far else 'near')+'-public-CRjoin'
            geos.png(bitmap,attrs,out/(tag+'.png'))
            case=dict(tag=tag,oldTOP=at,newTOP=f.get('se_v_top'),generation=generation,pending=1,navigation_instructions=navigation_instructions,render_instructions=render_instructions,requests=f.requests,unchanged_REU_during_public_key=16777216)
            cases.append(case);print('PASS',case,flush=True)
        result=dict(status='passed',identity=identity,cases=cases,scope=__doc__,local_render_consumer=local_render,remaining='CPU entry seam is actual publickeydispatch, not nativephysicalkeytiming. MixedABI, broaderediting/recovery and nativeproduct gates remain.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:f.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/geos-preflush-product'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);run(out,a.project.resolve())
