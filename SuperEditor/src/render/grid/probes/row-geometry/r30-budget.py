"""Private R30 selector/component budget, with exact existing C32/R30 controls."""
from pathlib import Path
import sys,json,hashlib,zipfile,shutil,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[5];D=Path(__file__).resolve().parent
BASE=ROOT/'agentsworking/evidence/M8/20261026T083129610982Z-grid-capture-cost/fixture'
def build(out):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(BASE.parent/'release/generated-sources.zip')as z:z.extractall(tree)
 fonts=tree/'assets/fonts/generated';fonts.mkdir(parents=True,exist_ok=True)
 for p in(BASE/'fonts').glob('*.bin'):shutil.copy2(p,fonts/p.name)
 p=tree/'src/render/geos/style-typing/build.py';spec=importlib.util.spec_from_file_location('r30_build',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);images,budget=m.build(out/'control',BASE)
 for n,k in [('gtype','worker'),('type','stage')]:assert images[k]==(BASE/'build/overlays'/(n+'.seo')).read_bytes(),n+' control differs'
 supervisor=tree/'src/render/geos/style-typing/supervisor.s';s=supervisor.read_text();assert s.count('entry: jmp root')==1;s=s.replace('.export entry','.export entry,root\n.import se_rg_dispatch').replace('entry: jmp root','entry: jmp se_rg_dispatch');supervisor.write_text(s)
 transfer=tree/'src/render/geos/typing/transfer.s';transfer.write_text(transfer.read_text()+'\n.export se_rg_owned\nse_rg_owned=owned\n')
 shutil.copy2(D/'vertical.s',tree/'src/render/geos/style-typing/vertical.s')
 s=p.read_text();old="q=link('worker',objs,D/'supervisor.cfg')";assert s.count(old)==1;s=s.replace(old,"objs.append(obj('vertical',D/'vertical.s'))\n q=link('worker',objs,D/'supervisor.cfg')");p.write_text(s)
 spec=importlib.util.spec_from_file_location('r30_geometry_build',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);images,new=m.build(out/'candidate',BASE)
 assert images['stage']==(BASE/'build/overlays/type.seo').read_bytes(),'unchanged C32 must stay byte-identical'
 old=(out/'control/worker.bin').read_bytes();worker=(out/'candidate/worker.bin').read_bytes();assert worker[0x20:0x35]==old[0x20:0x35],'all7 helper vectors must stay exact'
 fixture=out/'fixture';shutil.copytree(BASE,fixture);(fixture/'build/overlays/gtype.seo').write_bytes(images['worker']);identity=json.loads((fixture/'freeze.json').read_text());identity['assets']['gtype']=hashlib.sha256(images['worker']).hexdigest();identity['private_change']='R30 owner4 bounded vertical component; no editor geometry integration.';(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 result=dict(status='PASS',scope='Budget/component selector only; no source-authoritative editor publication claim.',control=budget,candidate=new,fixed7vectors_exact=True,C32_exact=True,remaining=4096-new['R30'],sha256=identity['assets']['gtype']);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
