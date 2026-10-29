"""Actual C6 single-edit witness on a frozen editor, before incremental consume.

Only the candidate C6 SEO is substituted in the private fixture. Source, gap,
revision and published page are produced by real root services; no shared build.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
import test_geos_editor as geos
from overlays import wrap
ROOT=geos.ROOT
BASE=ROOT/'build/geos-semantic-editor/20261025T071324227584Z/fixture'
GEC=0xCFE8

def run(out,previous):
    frozen,identity=geos.freeze(out,previous)
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    inputs=['src/overlays/hot-window.s','src/overlays/render-damage.s','src/render/geos/edit-certificate.inc','src/render/geos/edit-certificate-body.inc','src/render/geos/caret-cache.s']
    with zipfile.ZipFile(out/'candidate-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in inputs:z.write(ROOT/n,n)
    subprocess.run(['ca65','-g','-D','EDITOR_BINDINGS=1','-I','src','-I','build','-o',out/'window.o','src/overlays/hot-window.s'],cwd=ROOT,check=True)
    subprocess.run(['ld65','-C','cfg/overlay-c.cfg','-o',out/'window.bin',out/'window.o'],cwd=ROOT,check=True)
    report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];payload=(out/'window.bin').read_bytes()
    assert payload[:16]==bytes.fromhex(report['resident_binding']['digest'])
    image=wrap(payload,1,6,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=payload[:16]);(out/'window.seo').write_bytes(image)
    # Private current R27 differs only by clearing the edit witness when a
    # fresh complete base is captured. Reuse sealed unchanged helper objects.
    subprocess.run(['ca65','-g','-I','build/geos-prod','-I','src','-o',out/'caret.o','src/render/geos/caret-cache.s'],cwd=ROOT,check=True)
    deps=['build/geos-prod/'+n+'.o' for n in ['cache-warm','caret-ui','chrome','header','geoscaret-bindings']]
    subprocess.run(['ld65','-C','cfg/overlay-r.cfg','-o',out/'caret.bin',out/'caret.o',*deps],cwd=ROOT,check=True)
    caret=(out/'caret.bin').read_bytes();assert caret[:16]==payload[:16]
    caret_image=wrap(caret,0,27,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=payload[:16])
    dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);f.assets['window']=image;f.assets['geoscaret']=caret_image
    data=geos.native_text('Ordinary text here.\rSecond source line.\r');cases=[]
    def setup(mode=3,pos=5):
        f.source(data);f.command(96+mode)
        for _ in range(pos):f.command(2)
        f.render();assert f.get('se_hot_caret')==pos
    def witness():
        return dict(revision=f.get('se_r_revision',4),length=len(f.merged()),sequence=f.get('se_e_draw_sequence',2),doc_epoch=f.get('se_doc_epoch',2),reu_epoch=f.get('se_reu_epoch',2))
    def exact(op,at,old,new,before,tag):
        expected=bytes([1,op])+at.to_bytes(3,'little')+bytes([old,new])+before['revision'].to_bytes(4,'little')+before['length'].to_bytes(3,'little')+before['sequence'].to_bytes(2,'little')+before['doc_epoch'].to_bytes(2,'little')+before['reu_epoch'].to_bytes(2,'little')
        assert f.read(GEC,20)==expected,(tag,f.read(GEC,20).hex(),expected.hex())
        assert f.get('se_r_revision',4)==(before['revision']+1)&0xffffffff
        assert f.read(0xC600,1024)==f.shim
        cases.append(dict(tag=tag,certificate=expected.hex()))
    try:
        setup();before=witness();q=geos.native_text('Q')[0];f.key(q);exact(0,5,0,q,before,'insert')
        assert f.merged()==data[:5]+bytes([q])+data[5:]
        f.key(q);assert f.read(GEC,1)==b'\0';cases.append(dict(tag='second-edit-before-publication-refuses'))
        f.render();before=witness();f.key(q);exact(0,7,0,q,before,'new-publication-rearms')
        setup();before=witness();f.key(0x14);exact(1,4,data[4],0,before,'backspace-position-after-left')
        assert f.merged()==data[:4]+data[5:]
        setup();before=witness();f.command(4);exact(1,5,data[5],0,before,'forward-delete')
        assert f.merged()==data[:5]+data[6:]
        for mode in (0,1,2):
            setup(mode);f.key(q);assert f.read(GEC,1)==b'\0';cases.append(dict(tag='other-mode-'+str(mode)))
        setup();f.put('se_sel_mark',1,1);f.put('se_sel_anchor',5);f.key(q);assert f.read(GEC,1)==b'\0';cases.append(dict(tag='marked-edit-fallback'))
        setup();f.m.write(0xCF91,f.m.read(0xCF91)^1);f.key(q);assert f.read(GEC,1)==b'\0';cases.append(dict(tag='stale-page-publication-refuses'))
        setup();f.m.write(0xCF90,0);f.key(q);assert f.read(GEC,1)==b'\0';cases.append(dict(tag='invalid-base-refuses'))
        result=dict(status='passed',base_prg_sha256=identity['prg_sha256'],private_C6_substitution=True,payload_bytes=len(payload),cases=cases,source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in inputs},scope='Actual C6 producer + root input on real published source pages. No incremental consumer, pixels or native timing claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:f.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args()
    out=ROOT/'build/geos-edit-certificate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
