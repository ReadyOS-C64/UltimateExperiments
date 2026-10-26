"""Private C19 automatic incomplete-grammar fallback; public editing regression.
No shared builds/product writes. Checked ROM/provider CPU seams, not native.
"""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,shutil,subprocess,zipfile,argparse,gzip
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_editor_soak as old
import test_geos_semantic_editor as semantic
from overlays import wrap
from d81_image import D81Image
BASE=ROOT/'build/normal-row80-committed/20261026T193357856684Z/fixture'
D=ROOT/'src/cache/retention-grammar-probe'
SOURCE=old.fold.geos.native_text(':::region Work\rEditable line here.\r:::end\rTail.\r')
def shell(args):subprocess.run([str(x)for x in args],check=True,stdout=subprocess.DEVNULL)
def build(out,base):
 out.mkdir(parents=True);tree=out/'frozen-source'
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith(('src/','cfg/')):(tree/n).parent.mkdir(parents=True,exist_ok=True);(tree/n).write_bytes(z.read(n))
 report=json.loads((base/'build/editor-report.json').read_text());digest=bytes.fromhex(report['resident_binding']['digest'])
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$%02x'%b for b in digest)+'\n.endmacro\n')
 parts=['src/overlays/fold-editor.s','src/editor_fold/coordinator.s','src/editor_fold/retain.s','src/style/reader-dispatch.s','src/editor_fold/create.s'];images={};sizes={}
 for variant in ['control','candidate']:
  dest=out/variant;dest.mkdir();objects=[]
  for i,name in enumerate(parts):
   p=D/'coordinator.s'if variant=='candidate'and i==1 else tree/name;o=dest/(str(i)+'.o');shell(['ca65','-g','-I',out,'-I',tree/'src','-o',o,p]);objects.append(o)
  shell([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',dest/'bindings.s',*objects]);shell(['ca65','-o',dest/'bindings.o',dest/'bindings.s']);objects.append(dest/'bindings.o')
  shell(['ld65','-C',tree/'cfg/fold-editor-control.cfg','-o',dest/'foldctl.bin','-m',dest/'foldctl.map','-Ln',dest/'foldctl.lbl',*objects]);payload=(dest/'foldctl.bin').read_bytes();assert len(payload)<=4096
  images[variant]=wrap(payload,1,19,api=(report['symbols']['se_overlay_call'],report['symbols']['se_overlay_frame']),binding_digest=digest);sizes[variant]=len(payload)
 assert images['control']==(base/'build/overlays/foldctl.seo').read_bytes(),'frozen control must reassemble exactly'
 private=out/'fixture';shutil.copytree(base,private,copy_function=shutil.copy2)
 (private/'build/overlays/foldctl.seo').write_bytes(images['candidate']);ident=json.loads((private/'freeze.json').read_text());ident['assets']['foldctl']=hashlib.sha256(images['candidate']).hexdigest()
 disk=private/'build/supereditor.d81';shell(['c1541','-attach',disk,'-delete','foldctl','-write',private/'build/overlays/foldctl.seo','foldctl,s']);before=D81Image((base/'build/supereditor.d81').read_bytes());after=D81Image(disk.read_bytes());assert after.read(b'FOLDCTL',kind=1).data==images['candidate']
 for e in before.entries():
  if e.name!=b'FOLDCTL':assert before.read(e.name).data==after.read(e.name).data and before.read(e.name).sectors==after.read(e.name).sectors
 ident['disk_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest()
 # Frozen source identity declares the one private source change.
 with zipfile.ZipFile(base/'product-sources.zip')as z,zipfile.ZipFile(private/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as w:
  for n in z.namelist():w.writestr(n,(D/'coordinator.s').read_bytes()if n=='src/editor_fold/coordinator.s'else z.read(n))
 ident['sources']['src/editor_fold/coordinator.s']=hashlib.sha256((D/'coordinator.s').read_bytes()).hexdigest();(private/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n');return private,dict(bytes=sizes,candidate_sha256=ident['assets']['foldctl'])

def run(out,base):
 out.mkdir(parents=True);private,budget=build(out/'link',base);dll=old.runner(out);cases=[]
 for variant,fixture,modes in [('control',base,[0]),('candidate',private,range(4))]:
  ident=json.loads((fixture/'freeze.json').read_text());old.fold.geos.grid.editor_fixture.ROOT=old.fold.geos.grid.cpu_editor.ROOT=fixture;old.fold.geos.grid.editor_fixture.NAMES=old.fold.geos.grid.cpu_editor.NAMES=ident['names']
  f=old.fold.Fixture(out,fixture,dll,True);catalog=None
  def prepare(mode,source=SOURCE):
   old.fold.geos.Fixture.source(f,source,banks=1,physical=32)
   # Genuine optional semantic baseline is established before the edit audit;
   # the unchanged observer then forbids any type53 payload write in this run.
   f.command(99);f.render();f.command(96+mode);f.render();f.command(115);f.render();f.command(116);f.render();assert f.get('se_ef_valid',1)==1
  def edit():
   f.typed(old.fold.geos.native_text('goto 3'));f.command(2);f.command(2);at=f.get('se_hot_caret');assert at==SOURCE.index(b':::END')+2
   f.key(old.fold.geos.native_text('Q')[0]);data=SOURCE[:at]+old.fold.geos.native_text('Q')+SOURCE[at:];f.command(1);f.command(16);assert f.merged()==SOURCE;f.command(17);assert f.merged()==data;return data
  def pixels(data):
   if f.get('se_mode',1)==3:
    fonts={n:(fixture/'fonts'/n).read_bytes()for n in old.fold.geos.GEOS_FONTS+('native8.bin',)};bits,attrs,_,_=semantic.expected(f,data,fonts)
   else:(bits,attrs),_,_,_=old.fold.geos.grid.expected(f,data)
   mode=f.get('se_mode',1);assert f.read(0x4000 if mode==0 else 0x6000,len(bits))==bits,'independent pixels';actual=bytes(v&15 for v in f.read(0xd800,1000))if mode==0 else f.read(0x4000,1000);assert actual==attrs,'independent attrs'
  try:
   for mode in modes:
    prepare(mode);catalog=f.catalog();before=f.reu();f.audit_begin();data=edit();assert len(data)==49
    history=f.read(f.s['se_h_current'],4)+f.read(f.s['se_h_saved'],4)+f.read(f.s['se_h_cursor'],2)+f.read(f.s['se_h_end'],2);error=None
    try:f.render()
    except AssertionError as e:error=repr(e)
    assert f.merged()==data and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
    assert history==f.read(f.s['se_h_current'],4)+f.read(f.s['se_h_saved'],4)+f.read(f.s['se_h_cursor'],2)+f.read(f.s['se_h_end'],2)
    assert not any(f.get(n,1)for n in ['se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned','se_ef_valid','se_ef_active'])
    assert f.get('se_ej_status',1)==128
    if variant=='control':assert error and f.get('se_e_error',1)==0xb5
    else:
     assert error is None and f.get('se_e_error',1)==0;pixels(data)
     f.key(old.fold.geos.native_text('Z')[0]);at=f.get('se_hot_caret')-1;nextdata=data[:at]+old.fold.geos.native_text('Z')+data[at:];f.command(2);f.command(16);assert f.merged()==data;f.command(17);assert f.merged()==nextdata;f.render();pixels(nextdata)
     f.command(96+(mode+1)%4);f.render();assert f.merged()==nextdata;pixels(nextdata)
    f.audit_end(before,variant+str(mode));cases.append(dict(variant=variant,mode=mode,source49_sha256=hashlib.sha256(data).hexdigest(),error=error,continued_typing=variant=='candidate'))
   if variant=='candidate':
    # Explicit user action still reports the documented B5 without source edits.
    malformed=SOURCE.replace(b':::END',b'::Q:END');old.fold.geos.Fixture.source(f,malformed,banks=1,physical=32);before=f.reu();f.audit_begin();f.command(115,error=0xb5);assert f.merged()==malformed and f.get('se_f_owner',1)==f.get('se_doc_read_locks',1)==0;f.audit_end(before,'explicit-fold-refusal');cases.append(dict(control='explicit FoldAll malformed grammar',error=181))
    # Actual missing-reader admission is not an incomplete-grammar fallback.
    prepare(0);data=edit();raw=f.assets['viewsource'];slot,id_=raw[5],raw[6];i=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)&1==slot);f.m.write(f.s['se_overlay_ids']+i,0);f.m.write(f.s['se_overlay_active']+slot,0)
    try:f.render();assert False,'missing reader must remain error'
    except AssertionError:assert f.get('se_e_error',1)==0x17
    assert f.merged()==data and f.get('se_f_owner',1)==f.get('se_doc_read_locks',1)==0;cases.append(dict(control='actual missing R14 admission',error=23))
  finally:dll.fr_end();f.m.close()
 result=dict(status='passed',budget=budget,cases=cases,fixture=str(private),scope='Private sealedC19 only; actual public editing/all4pixel modes and checked typedDMA16MiB guards. Explicit FoldAll B5 and actual missingR14 still fail. No native/product promotion claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/retention-grammar'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture)
