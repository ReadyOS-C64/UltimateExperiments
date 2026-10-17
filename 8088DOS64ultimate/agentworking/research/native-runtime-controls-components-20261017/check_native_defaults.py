from pathlib import Path
import sys,os,shutil,subprocess,json,hashlib
P=Path(__file__).resolve().parent;D=P/'native-defaults';assert not D.exists();D.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for n in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH','PYTHONPYCACHEPREFIX']:env.pop(n,None)
products={};commands=[]
for mode,flags in [('undefined',[]),('zero',[n+'=0'for n in ['DOS64_MODAL_MENU','DOS64_SAVE_HD_CONTEXT','DOS64_EXPORT_CRC','DOS64_SAVE_MODAL','DOS64_MEDIA_BINDING']])]:
 w=D/mode;shutil.copytree(P/'work',w,ignore=shutil.ignore_patterns('build','third_party','__pycache__','.zig-cache','zig-out'));a=['make','-B','build/dos64.prg','build/dos64-tests.prg',*flags]
 r=subprocess.run(a,cwd=w,env=env,capture_output=True);(D/(mode+'.stdout')).write_bytes(r.stdout);(D/(mode+'.stderr')).write_bytes(r.stderr);commands.append({'argv':a,'exit':r.returncode});assert r.returncode==0,r.stderr.decode();products[mode]={}
 for name in ['dos64.prg','dos64-tests.prg','dos64.labels','dos64-tests.labels']:
  f=w/'build'/name;products[mode][name]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
assert products['undefined']==products['zero']
assert products['zero']['dos64.prg']['sha256']=='666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064'
assert products['zero']['dos64-tests.prg']['sha256'].startswith('b9e9cc9e')
(D/'RESULT.json').write_text(json.dumps({'passed':True,'products':products,'commands':commands,'scope':'fresh native defaultundefined/explicitzero matchespublicruntime666/unitb9; no physical acceptance'},indent=2)+'\n')
