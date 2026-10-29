"""Unchanged native29 C33 oracle, released private C33/R25; owned8100/8200."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,shutil,socket,subprocess,threading
import test_grid_caret_candidate_vice as proof
ROOT=proof.ROOT
BASE=ROOT/'build/grid-typing-native/20261025T180126291505Z/fixture'
class Plan(proof.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1;return p
def ports_free():
 for port in [8100,*range(8200,8240)]:
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as ex:raise AssertionError(('owned port occupied',port))from ex

def freeze(base):
 e=proof.engine.folds.freeze(base);target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-geos-fold-native','-grid-typing-gallery-native');shutil.move(e,target)
 identity=json.loads((target/'freeze.json').read_text());assert len(identity['catalog'])==48 and identity['catalog'][-1]=='grid'
 expected={'grid':(2414,'e9b657cf42f38ef57f4a9bad47179c084830cc97ad608839926385077bd968cf'),'geostail':(3543,'0ad94e310eb3f5034eb4126eb14c138d095ca49ac516789874198bd7c4262afc')}
 for name,(size,digest)in expected.items():
  image=(target/(name+'.seo')).read_bytes();assert len(image)-36==size and hashlib.sha256(image).hexdigest()==digest
 (target/'private-overrides.json').write_text(json.dumps(dict(expected=expected,base=str(base),provenance='Inherited product-sources.zip describes immutable baseline resident/46 images. Exact override sources retained at M8/20261025T180126572082Z-grid-typing-checkpoint/private-implementation-verifier.zip.'),indent=2)+'\n');return target

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();e=freeze(a.fixture.resolve());stop=threading.Event()
 def watch():
  while not stop.wait(.05):
   q=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for line in q.stdout.splitlines():
    if '/x64sc 'in line and str(e/'working.d81')in line:
     z=line.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(PID=int(z[0]),command=z[2]),indent=2)+'\n');return
 thread=threading.Thread(target=watch,daemon=True);thread.start();proof.Plan=Plan;proof.ports_free=ports_free
 try:print(proof.execute(e),flush=True)
 finally:
  stop.set();thread.join(timeout=2)
  if(e/'owned-process.json').exists():
   z=json.load(open(e/'owned-process.json'));q=subprocess.run(['ps','-p',str(z['PID']),'-o','pid=,comm='],capture_output=True,text=True);assert not q.stdout.strip();z['closed']=True;(e/'closure.json').write_text(json.dumps(z,indent=2)+'\n')
if __name__=='__main__':main()
