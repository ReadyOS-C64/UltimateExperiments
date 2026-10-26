"""Build only a private C19 against immutable fixture sources/bindings."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
D=Path(__file__).parent
def command(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 assert p.returncode==0,(args,p.stdout,p.stderr)
def build(out,base):
 out.mkdir(parents=True);tree=out/'tree'
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(tree)
 for name in ('coordinator.s','retain.s'):
  old=(tree/'src/editor_fold'/name).read_text();new=(D/name).read_text()
  assert new==old.replace('jsr se_object_create','jsr ec_create_fold').replace('.segment "CODE"','.import ec_create_fold\n.segment "CODE"',1)
 command([sys.executable,ROOT/'src/fold/editor-leaves/binding.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc'])
 objects=[]
 for name,path in [('entry',tree/'src/overlays/fold-editor.s'),('coordinator',D/'coordinator.s'),('retain',D/'retain.s'),('reader',tree/'src/style/reader-dispatch.s'),('create',D/'create.s')]:
  obj=out/(name+'.o');command(['ca65','-g','-I',out,'-I',tree/'src','-o',obj,'-l',out/(name+'.lst'),path]);objects.append(obj)
 command([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);command(['ca65','-o',out/'aliases.o',out/'aliases.s']);objects.append(out/'aliases.o')
 command(['ld65','-C',tree/'cfg/fold-editor-control.cfg','-o',out/'image.bin','-m',out/'image.map','-Ln',out/'image.lbl',*objects])
 raw=(out/'image.bin').read_bytes();r=json.load(open(base/'build/editor-report.json'));s=r['symbols'];assert len(raw)<=4096
 image=wrap(raw,1,19,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(r['resident_binding']['digest']));(out/'foldctl.seo').write_bytes(image)
 proof=dict(bytes=len(raw),control_bytes=len((base/'build/overlays/foldctl.seo').read_bytes())-36,sha256=hashlib.sha256(image).hexdigest(),baseline=str(base),source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in D.glob('*')if p.is_file()})
 (out/'build.json').write_text(json.dumps(proof,indent=2)+'\n');return image,proof
