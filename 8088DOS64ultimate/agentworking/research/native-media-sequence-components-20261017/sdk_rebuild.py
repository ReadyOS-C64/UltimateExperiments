from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-sdk-rebuild');assert not Path(sys.pycache_prefix).exists()
import hashlib,json,shutil,subprocess
E=P/'sdk-source-rebuild';assert not E.exists();E.mkdir()
def info(q):return {'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
prior=json.loads((P/'closed-execution/INPUTS_AFTER.json').read_text());products=json.loads((P/'closed-execution/PRODUCTS_AFTER.json').read_text());sdk=Path(shutil.which('cc65')).resolve().parents[1]/'share/cc65';extra={str(q.resolve()):info(q)for n in ['include','asminc']for q in(sdk/n).rglob('*')if q.is_file()};extra[str(P/'sdk_rebuild.py')]=info(P/'sdk_rebuild.py');before=prior|extra
for n,h in before.items():assert info(Path(n))==h,n
(E/'INPUTS_BEFORE.json').write_text(json.dumps(before,indent=2)+'\n')
for n in extra:
 q=Path(n);rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');dst=E/'inputs'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dst)
shutil.rmtree(P/'work/build');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(P/'.absent-sdk-source-cache'));r=subprocess.run([sys.executable,'-B','build_ui_bridge.py'],cwd=P,env=env,capture_output=True);(E/'BUILD.stdout').write_bytes(r.stdout);(E/'BUILD.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()
for n,h in before.items():assert info(Path(n))==h,('sourcechanged',n)
for n,h in products.items():assert info(Path(n))==h,('productchanged',n)
(E/'INPUTS_AFTER.json').write_text(json.dumps(before,indent=2)+'\n');(E/'PRODUCTS_AFTER.json').write_text(json.dumps(products,indent=2)+'\n');(E/'RESULT.json').write_text(json.dumps({'passed':True,'source_tool_SDK_union':len(before),'additional_CC65_headers_macros_and_driver':len(extra),'exact_executed_products_reproduced':len(products),'qualification':'Additive SDK-before-read source rebuild; all44 exact products were actually executed unchanged in prior10group cohort. No native test rerun or historical input ledger rewrite.'},indent=2)+'\n');print((E/'RESULT.json').read_text())
