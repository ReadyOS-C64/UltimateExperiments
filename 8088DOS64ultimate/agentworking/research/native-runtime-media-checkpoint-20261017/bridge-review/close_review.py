from pathlib import Path
import hashlib,json,subprocess,shutil,os
P=Path.cwd();assert P.name=='native-insert-controller-repair-review-20261017'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=P/'bridge-source-rebuild';out.mkdir();env=dict(os.environ)
for k in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(k,None)
tools={n:Path(shutil.which(n)).resolve()for n in ['ca65','ld65']};toolspec={n:{'path':str(p),'sha256':h(p)}for n,p in tools.items()}
receipts=[]
for role,w in [('old',P/'historical-counter/runtime'),('repair',P/'runtime')]:
 d=out/role;d.mkdir();inputs={n:h(w/'bridge'/n)for n in ['bridge.s','bridge.cfg','symbols.inc','products.inc']}
 for n in inputs:shutil.copyfile(w/'bridge'/n,d/n)
 commands=[[str(tools['ca65']),'-g','bridge.s','-o',str(d/'bridge.o')],[str(tools['ld65']),'-C','bridge.cfg','-o',str(d/'bridge.prg'),'-m',str(d/'bridge.map'),'-Ln',str(d/'bridge.labels'),str(d/'bridge.o')]]
 for i,c in enumerate(commands):
  r=subprocess.run(c,cwd=w/'bridge',env=env,capture_output=True);(d/f'{i}.stdout').write_bytes(r.stdout);(d/f'{i}.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr
 assert all(h(w/'bridge'/n)==v and h(d/n)==v for n,v in inputs.items());assert (d/'bridge.prg').read_bytes()==(w/'bridge/bridge.prg').read_bytes()
 receipts.append({'role':role,'inputs':inputs,'reproduced':h(d/'bridge.prg'),'commands':commands})
for w in [P,P/'historical-counter']:
 v=json.loads((w/'SOURCE_WINDOW.json').read_text())
 for n,sha in v['files'].items():
  q=w/'runtime'/n
  if n=='model/save-peddle.dylib':assert h(w/'counter-source/old-save-peddle.dylib')==sha
  else:assert h(q)==sha,n
 for x in json.loads((w/'counter-source/BEFORE.json').read_text()):
  assert h(Path(x['path']))==x['sha256'];assert h(w/x['copy'])==x['sha256']
 assert h(w/'runtime/model/save-peddle.dylib')==json.loads((w/'counter-source/MODEL.json').read_text())['source_built_model_sha256']
for n,t in tools.items():assert h(t)==toolspec[n]['sha256']
(P/'SOURCE_CLOSURE.json').write_text(json.dumps({'both_native_windows_exact_except_explicit_source_built_model_replacement':True,'old_and_repair_model_input_count_each':1010,'original_model_bytes_retained':True,'tools':toolspec,'bridge_source_rebuild':receipts},indent=2)+'\n')
