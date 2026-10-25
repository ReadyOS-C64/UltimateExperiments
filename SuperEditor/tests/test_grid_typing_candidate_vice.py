"""Private C33/R25 source typing A/B; owned8100/text8200, unchanged native oracles."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,importlib.util,shutil,subprocess
import test_source_grid_typing_profile_vice as profile
ROOT=profile.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
def main():
 out=ROOT/'build/grid-typing-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen=out/'fixture';shutil.copytree(BASE,frozen)
 spec=importlib.util.spec_from_file_location('gridtypingbuild',ROOT/'src/render/grid/typing-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen)
 identity=json.loads((frozen/'freeze.json').read_text())
 for name,seo in seos.items():
  p=frozen/'build/overlays'/(name+'.seo');p.write_bytes(seo);identity['assets'][name]=hashlib.sha256(seo).hexdigest()
  r=subprocess.run(['c1541','-attach',str(frozen/'build/supereditor.d81'),'-delete',name,'-write',str(p),name+',s'],capture_output=True,text=True);(out/(name+'-disk.log')).write_text(r.stdout+r.stderr);assert not r.returncode
 identity['disk_sha256']=hashlib.sha256((frozen/'build/supereditor.d81').read_bytes()).hexdigest();identity['private_substitutions']=budget;(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 sys.argv=[sys.argv[0],'--fixture',str(frozen)];profile.main()
if __name__=='__main__':main()
