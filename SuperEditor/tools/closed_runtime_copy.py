"""Share immutable successful owned-run output without duplicating REU dumps.

The existing runner still controls process lifetime, protocol and assertions.
Only its final host copy changes, after successful --close-vice completion.
"""
from pathlib import Path
import hashlib,json,os,shutil

def run_with_closed_links(runner,plan,out,timeout=900):
 out=Path(out);original=shutil.copytree;records=[]
 def copytree(source,target,*args,**kwargs):
  if Path(target).resolve()==(out/'run').resolve():
   outcome=json.loads((out/'run-plan.stdout.txt').read_text())
   source=Path(source)
   assert outcome['Status']=='success'and source.resolve()==Path(outcome['RunDir']).resolve()
   manifest=json.loads(Path(outcome['Manifest']).read_text(encoding='utf-8-sig'))
   assert manifest['status']=='success'
   # The subprocess invocation has returned with --close-vice. These are its
   # completed captures, never the REU backing file of a live emulator.
   def link(a,b):
    a,b=Path(a),Path(b);digest=hashlib.sha256(a.read_bytes()).hexdigest();os.link(a,b)
    assert a.stat().st_ino==b.stat().st_ino and hashlib.sha256(b.read_bytes()).hexdigest()==digest
    records.append(dict(source=str(a),target=str(b.relative_to(out)),bytes=a.stat().st_size,sha256=digest));return str(b)
   kwargs['copy_function']=link
  return original(source,target,*args,**kwargs)
 shutil.copytree=copytree
 try:return runner(plan,out,timeout=timeout)
 finally:
  shutil.copytree=original
  if records:(out/'closed-runtime-link-receipts.json').write_text(json.dumps(dict(scope=__doc__,files=records),indent=2)+'\n')
