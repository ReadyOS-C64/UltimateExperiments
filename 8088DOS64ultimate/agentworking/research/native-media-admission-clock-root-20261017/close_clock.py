from pathlib import Path
import sys,os,json,hashlib,subprocess,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
def digest(q):
 b=Path(q).read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def verify(rows):
 for n,w in rows.items():assert digest(n)==w,n
def main():
 out=P/'closed-clock';out.mkdir()
 j=json.loads((P/'build/RESULT.json').read_text());records=dict(j['source_inputs']);records.update(j['native_products'])
 records[str(Path(__file__).resolve())]=digest(__file__)
 records[str(Path(sys.executable).resolve())]=digest(Path(sys.executable).resolve())
 for q in (P/'runtime').rglob('*'):
  if q.is_file() and q.suffix.lower() in ['.py','.s','.c','.h','.cpp','.cfg','.inc','.prg','.labels','.bin','.mnu','.dylib','.a']:records[str(q)]=digest(q)
 verify(records);(out/'INPUTS_BEFORE.json').write_text(json.dumps(records,indent=2)+'\n')
 commands=[];groups=0
 for name,script,result,count in [('clock-admission','test_admission_clock.py','ADMISSION_CLOCK_RESULT.json',10),('actual-CIA-smoke','run_smoke.py','SMOKE_RESULT.json',3)]:
  start=time.monotonic();args=[str(Path(sys.executable).resolve()),'-B',script]
  with (out/(name+'.stdout')).open('wb')as o,(out/(name+'.stderr')).open('wb')as e:r=subprocess.run(args,cwd=P/'runtime',stdin=subprocess.DEVNULL,stdout=o,stderr=e)
  commands.append({'argv':args,'cwd':str(P/'runtime'),'exit':r.returncode,'seconds':time.monotonic()-start})
  (out/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n')
  assert r.returncode==0,name
  test=json.loads((P/'runtime'/result).read_text());assert test['passed'] and test['groups']==count
  (out/result).write_text(json.dumps(test,indent=2)+'\n');groups+=count
 verify(records);(out/'INPUTS_AFTER.json').write_text(json.dumps(records,indent=2)+'\n')
 result={'passed':True,'actual_groups':groups,'closed_inputs_products':len(records),'source_products_unchanged':True,'native_products':j['products'],'commands':commands,'model':'source-built peer Peddle model reused after whole-manifest verification; no Root model recompile','scope':'actual WIRE/Save admission10 + CIA SaveAs/Insert/assetrefusal3; synthetic media, no cold/DOS/physical'}
 (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
