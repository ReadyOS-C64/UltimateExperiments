from pathlib import Path
import json,hashlib
P=Path.cwd();assert P.name=='native-runtime-media-public-20261017'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
final=json.loads((P/'build-final/RESULT.json').read_text());W=Path(final['work']);records={}
for report in [P/'build-final/RESULT.json',P/'relocated tree/project with spaces/build/runtime-media/RESULT.json']:
 j=json.loads(report.read_text())
 for key in ['source_inputs','native_products']:
  for p,v in j[key].items():assert h(Path(p))==v['sha256']and Path(p).stat().st_size==v['bytes'],p
 for name,x in j['products'].items():assert h(Path(x['path']))==x['sha256'];assert x['sha256']==final['products'][name]['sha256']
 records[str(report.relative_to(P))]={'source_inputs':len(j['source_inputs']),'native_products':len(j['native_products']),'products':{n:{k:v[k]for k in ['sha256','bytes']}for n,v in j['products'].items()}}
old=P.parent/'native-insert-controller-repair-review-20261017/runtime';tag=(W/'HEADER.bin').read_bytes()[8:24];oldtag=(old/'HEADER.bin').read_bytes()[8:24];comparisons={}
for n in ['work/build/dos64.prg','MODAL.MNU','broker/broker.prg','bridge/bridge.prg','controller/controller.prg','ui/panel.prg','phase/transaction-wire.prg','phase/modal-save.prg','phase/runtime-plan.prg','binding/binding.prg','worker/incoming.prg','insert-binding/binding.prg','insert-binding/insert-support.prg','finish/finish.prg']:
 a=(W/n).read_bytes();o=(old/n).read_bytes();assert len(a)==len(o);assert a.replace(tag,bytes(16))==o.replace(oldtag,bytes(16)),n
 comparisons[n]={'bytes':len(a),'changed_bytes':sum(x!=y for x,y in zip(a,o)),'same_executable_bytes_with_tag_normalized':True,'sha256':h(W/n)}
smoke=P/'model-smoke-final/runtime'
for q in W.rglob('*.prg'):
 rel=q.relative_to(W);assert q.read_bytes()==(smoke/rel).read_bytes(),rel
for x in json.loads((P/'model-smoke/counter-source/BEFORE.json').read_text()):assert h(Path(x['path']))==x['sha256'];assert h(P/'model-smoke'/x['copy'])==x['sha256']
model=json.loads((P/'model-smoke/counter-source/MODEL.json').read_text());assert h(Path(model['compiler']['path']))==model['compiler']['sha256'];assert h(smoke/'model/save-peddle.dylib')==model['source_built_model_sha256']
for n in ['dos64','dos64-tests']:
 q=P/'default-work/build'/(n+'.prg');wanted='666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064'if n=='dos64'else'b9e9cc9e7d87176848ccf8bae49dfe4f4ff0125b3aad5a1cb874341436b78df6';assert h(q)==wanted
assert json.loads((smoke/'SMOKE_RESULT.json').read_text())['passed'];assert json.loads((P/'HOST_RESULT.json').read_text())['passed']
for q in(P/'project').rglob('*'):
 if q.is_file():assert q.read_bytes()==(P/'frozen-project'/q.relative_to(P/'project')).read_bytes()
(P/'CLOSURE.json').write_text(json.dumps({'passed':True,'final_and_relocated_builds':records,'parent_comparison':comparisons,'model_inputs':model['inputs'],'model_sha256':model['source_built_model_sha256'],'focused_CIA_groups':3,'host_groups':8,'default_runtime':'666089b5','default_UNIT':'b9e9cc9e','final_tag':tag.hex(),'scope':'optional source-built runtime+56K media graph; no cold/DOS/physical acceptance','first_failures':['build-first missing Make memory target','build-second attempted old unused alias-file read','FIRST_HOST_RESULT unused staged foundation fixture rejected by no-test-dependency control','FIRST_CLOSURE_FAILURE exact output comparison exposed fresh tag after unused source inventory removal; final tag actual CIA rerun performed']},indent=2)+'\n')
print('closed',len(final['source_inputs']),len(final['native_products']))
