"""Lossless hardlinks for closed exact owned lifecycle REU duplicates only."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

def link(e):
 e=Path(e).resolve();reply=json.loads((e/'lifecycle/run-plan.stdout.txt').read_text(encoding='utf-8-sig'));assert reply['Status']=='success'
 runtime=Path(reply['RunDir']).resolve();assert runtime.name.startswith('vice_auto_') and (runtime/'manifest.json').is_file()
 processes=subprocess.run(['ps','-Ao','command'],capture_output=True,text=True,check=True).stdout
 assert str(runtime/'dumps/vice_reu_working.img') not in processes,'owned VICE still live'
 known={};linked=[]
 for folder in (e,runtime):
  for p in sorted(folder.rglob('*')):
   if not p.is_file() or p.stat().st_size!=16777216:continue
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   if digest not in known:known[digest]=p;continue
   peer=known[digest]
   if p.stat().st_ino==peer.stat().st_ino:continue
   tmp=p.with_name(p.name+'.owned-link');os.link(peer,tmp);os.replace(tmp,p)
   assert hashlib.sha256(p.read_bytes()).hexdigest()==digest and p.stat().st_ino==peer.stat().st_ino
   linked.append(dict(path=str(p),peer=str(peer),bytes=16777216,sha256=digest))
 result=dict(closed_owned_only=True,runtime=str(runtime),linked=linked,bytes_avoided=16777216*len(linked))
 (e/'runtime-REU-hardlinks.json').write_text(json.dumps(result,indent=2)+'\n');print(e,len(linked),'closed REU duplicates linked',flush=True);return result
if __name__=='__main__':link(Path(sys.argv[1]))
