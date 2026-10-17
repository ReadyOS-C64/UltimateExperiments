from pathlib import Path
import json,hashlib,shutil,ast
P=Path(__file__).resolve().parent;S=P.parent/'native-media-live-binding-clock-successor-20261017';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();f=S/'FROZEN_PORTABLE_SOURCE.json';assert h(f)=='f3ade6309ec7079f496982e91953b0b4f5aae86ce1244de362521f8908de5dab'
for n,v in json.loads(f.read_text())['files'].items():assert h(S/n)==v['sha256'],n
records={}
for n in ['binding/binding.prg','binding/binding.map','binding/binding.labels','binding/binding-calls.prg','binding/binding-calls.map','binding/binding-calls.labels','binding/glue.s','controller_fixture.py','transaction_fixture.py','test_binding.py']:
 d=P/n if n.startswith('binding/')else P/'fixture_originals'/n;d.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(S/n,d);records[n]={'original':str(S/n),'copy':str(d),'sha256':h(d)}
for n in ['work/build/dos64-tests.prg','work/build/dos64-tests.labels','work/build/dos64.prg','model/save-peddle.dylib','phase/transaction-wire.prg','phase/modal-save.prg','phase/runtime-plan.prg']:assert h(S/n)==h(P/n),n
src=(S/'transaction_fixture.py').read_text();tree=ast.parse(src);functions='\n\n'.join(ast.get_source_segment(src,n)for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['labels','load','fat','reu'])
head='from pathlib import Path\nimport ctypes as C,struct,zlib\nfrom test_online_save import Machine,L,symbols\nfrom fixture_config import cfg,resign\nfrom dos_disk_inspect import Volume\nP=Path(__file__).resolve().parent\n'
headersrc=(S/'test_binding.py').read_text();hdr=next(ast.get_source_segment(headersrc,n)for n in ast.parse(headersrc).body if isinstance(n,ast.FunctionDef)and n.name=='headers')
(P/'fixture_base.py').write_text(head+functions+'\n'+hdr+'\n'+"A=fat(b'ORIGINAL A\\r\\n');OLD_B=fat(b'ORIGINAL B\\r\\n');NEW_B=fat(b'B WORKING MODIFIED\\r\\n')\n"+"symbols.update({n:v for n,v in labels('broker/broker.labels').items()if n.startswith('modal_')})\n")
src=(S/'controller_fixture.py').read_text().replace('from test_binding import headers','from fixture_base import headers').replace('from transaction_fixture import','from fixture_base import');(P/'controller_fixture.py').write_text(src)
(P/'CORRECTED_BINDING_INPUTS.json').write_text(json.dumps({'source_manifest':str(f),'source_manifest_sha256':h(f),'copied':records,'core_model_workers_exact':True,'qualification':'corrected native successor copied, parent final seal pending; fixture functions AST copied and module imports rebased only'},indent=2)+'\n')
