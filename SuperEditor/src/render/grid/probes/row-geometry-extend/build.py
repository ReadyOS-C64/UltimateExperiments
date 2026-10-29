"""Private single-immediate empty-suffix extension; exact released control first."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[5]
RELEASE=ROOT/'build/grid-row-geometry-full-fit11'
def build(out):
 out.mkdir(parents=True);base=RELEASE/'fixture';tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith(('src/','cfg/')):z.extract(n,tree)
 # Only the actual three generated wrapper inputs differ from the old source ZIP.
 entry=tree/'src/render/geos/fold-entry.s';entry.write_bytes((RELEASE/'bridge/tree/src/render/geos/fold-entry.s').read_bytes())
 shutil.copy2(RELEASE/'editor-api.inc',out/'editor-api.inc')
 raw_control=(base/'build/overlays/geosfold.seo').read_bytes()[36:]
 inputs=[entry,tree/'src/render/geos/fold-query.s',out/'kernel.s',ROOT/'src/render/grid/probes/row-geometry/full/authority.s',ROOT/'src/render/grid/probes/row-geometry/full/transaction.s']
 def link(name,kernel):
  dest=out/name;dest.mkdir();(out/'kernel.s').write_text(kernel);objs=[]
  for i,p in enumerate(inputs):
   o=dest/(str(i)+'.o');subprocess.run(['ca65','-g','-I',str(out),'-I',str(tree/'src'),'-o',str(o),str(p)],check=True);objs.append(o)
   dump=subprocess.check_output(['od65','--dump-segments',str(o)],text=True);segments={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dump,re.S)};assert not any(segments.get(n,0)for n in('BSS','DATA','ZEROPAGE'))
  subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(base/'build/editor-report.json'),'--output',str(dest/'aliases.s'),*map(str,objs)],check=True);subprocess.run(['ca65','-g','-o',str(dest/'aliases.o'),str(dest/'aliases.s')],check=True)
  subprocess.run(['ld65','-C',str(tree/'cfg/overlay-r.cfg'),'-o',str(dest/'leaf.bin'),'-Ln',str(dest/'leaf.lbl'),'-m',str(dest/'leaf.map'),*map(str,objs),str(dest/'aliases.o')],check=True)
  return(dest/'leaf.bin').read_bytes()
 original=(RELEASE/'kernel.s').read_text();control=link('control',original);assert control==raw_control,'released R24 control must reproduce exactly'
 needle=' lda FIRST\n cmp #22\n bcs bad\n';assert original.count(needle)==1
 candidate=link('candidate',original.replace(needle,' lda FIRST\n cmp #23\n bcs bad\n'));delta=[i for i,(a,b)in enumerate(zip(control,candidate))if a!=b];assert len(candidate)==len(control)==3983 and len(delta)==1 and(control[delta[0]],candidate[delta[0]])==(22,23)
 sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];digest=report['resident_binding']['digest'];image=wrap(candidate,0,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'candidate/leaf.seo').write_bytes(image)
 fixture=out/'fixture';shutil.copytree(base,fixture);p=fixture/'build/overlays/geosfold.seo';p.write_bytes(image);identity=json.loads((fixture/'freeze.json').read_text());identity['assets']['geosfold']=hashlib.sha256(image).hexdigest();identity['private_change']='single-immediate checked zero-suffix extension of released geometry R24; C33 unchanged';(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 result=dict(status='BUILT',R24=len(candidate),free=4096-len(candidate),changed_offsets=delta,C33_unchanged=True,R25_unchanged=True,source_control_sha256=hashlib.sha256(control).hexdigest(),candidate_sha256=hashlib.sha256(image).hexdigest(),new_BSS=0,new_ZP=0)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
