#!/usr/bin/env python3
"""Build and optionally test selected A/B SaveAs using synthetic disks only."""
from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.pycache_prefix=str(ROOT/'build'/('.absent-native-media-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache prefix must be absent')
import argparse,hashlib,json,shutil,subprocess,tempfile,platform,re
OWNER={'kind':'dos64-native-media','version':1}
PUBLISH=['dos64.prg','dos64-tests.prg','dos64-tests.prg.unit-extra.bin','dos64-tests.prg.unit-tail.bin','dos64.labels','dos64-tests.labels','dos64.map','dos64-tests.map','dos64.memory.json','dos64-tests.memory.json']
SUITES=[('selected','test_selected_save.py','SELECTED_RESULT.json',5),('sequential','test_sequential_cancel.py','SEQUENTIAL_RESULT.json',4),('online','test_online_save.py','ONLINE_SAVE_REPORT.json',10),('crc','test_crc.py','CRC_RESULT.json',5)]
def digest(p):
 b=Path(p).read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def atomic_json(p,value):
 tmp=p.with_name(p.name+'.tmp-'+str(os.getpid()));primary=None
 try:tmp.write_text(json.dumps(value,indent=2)+'\n');os.replace(tmp,p)
 except BaseException as ex:primary=ex;raise
 finally:
  try:
   if tmp.exists():tmp.unlink()
  except BaseException:
   if primary is None:raise
def verify(record):
 for s,w in record.items():
  if digest(Path(s))!=w:raise RuntimeError('Source/product changed: '+s)
def copy(source,destination,record):
 w=digest(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
 if digest(source)!=w or digest(destination)!=w:raise RuntimeError('Copy changed: '+str(source))
 if str(source)in record and record[str(source)]!=w:raise RuntimeError('Source changed between reads: '+str(source))
 record[str(source)]=w;record[str(destination)]=w
def safe_relative(s):
 p=Path(s)
 if not isinstance(s,str)or not s or p.is_absolute()or '\\'in s or any(x in ('','.','..')for x in s.split('/')):raise RuntimeError('Unsafe source inventory path')
 return p
def tool(name,env=None):
 key=env or 'DOS64_'+name.upper();chosen=os.environ.get(key,name);found=shutil.which(chosen)
 if not found:raise RuntimeError('Set '+key+' to '+name)
 return Path(found).resolve()
def tools(test):
 t={n:tool(n)for n in ['make','ca65','ld65']}
 if test:t.update({'clang++':tool('clang++','DOS64_CLANGXX'),'zig':tool('zig')})
 return t
def command_environment(work,t):
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
 for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','PYTHONHOME','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','CPATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH','OBJC_INCLUDE_PATH','LIBRARY_PATH','COMPILER_PATH','GCC_EXEC_PREFIX','ZIG_LIB_DIR','MAKEFLAGS','MFLAGS','MAKEOVERRIDES']:env.pop(n,None)
 env['ZIG_LOCAL_CACHE_DIR']=str(work/'.zig-cache');env['ZIG_GLOBAL_CACHE_DIR']=str(work/'.zig-global-cache')
 for n in ['make','ca65','ld65','zig']:
  if n in t:env['DOS64_'+n.upper()]=str(t[n])
 return env
def require_make_includes(work):
 # All current includes are literal project paths. A new packaging target must
 # not silently break the separately staged native-only build graph.
 for name in re.findall(r'^include\s+([^\n]+)',(work/'Makefile').read_text(),re.M):
  for relative in name.split():
   path=work/safe_relative(relative)
   if not path.is_file():raise RuntimeError('Native source inventory omits Make include: '+relative)
def stage(run,record,test):
 path=ROOT/'build_support/native_media_sources.json';w=digest(path)
 if str(path)in record and record[str(path)]!=w:raise RuntimeError('Source inventory changed between reads')
 record[str(path)]=w;j=json.loads(path.read_text())
 if set(j)!={'schema','native','test','model_baselines'}or j['schema']!=1:raise RuntimeError('Unsupported media source inventory')
 for source,w in (j['model_baselines'].items()if test else []):
  s=(ROOT/safe_relative(source)).resolve()
  if not s.is_relative_to(ROOT)or digest(s)!=w:raise RuntimeError('Canonical model changed; rebase the two media overrides')
  record[str(s)]=w
 selected=dict(j['native'])
 if test:
  if selected.keys()&j['test'].keys():raise RuntimeError('Duplicate staged destination')
  selected.update(j['test'])
 for dest,source in selected.items():
  s=(ROOT/safe_relative(source)).resolve();d=run/safe_relative(dest)
  if not s.is_relative_to(ROOT)or not s.is_file():raise RuntimeError('Missing/outside public source: '+source)
  copy(s,d,record)
 if test:
  pin=run/'work/third_party/peddle/UPSTREAM.json';j=json.loads(pin.read_text())
  for e in j['files']:
   f=run/'work/third_party/peddle'/safe_relative(e['path'])
   if digest(f)['sha256']!=e['sha256']:raise RuntimeError('Vendored Peddle changed: '+str(f))
 require_make_includes(run/'work')
 return run/'work'
def native(work,t,command,default):
 flags={'DOS64_SAVE_HD_CONTEXT':0 if default else 1,'DOS64_EXPORT_CRC':0 if default else 1}
 command([t['make'],'-B',*[n+'='+str(v)for n,v in flags.items()],'DOS64_CA65='+str(t['ca65']),'DOS64_LD65='+str(t['ld65']),'DOS64_PYTHON='+str(Path(sys.executable).resolve()),'build/dos64.prg','build/dos64-tests.prg','build/dos64-tests.prg.unit-extra.bin','build/dos64-tests.prg.unit-tail.bin','build/dos64-tests.bin','verify-memory'],cwd=work)
 for n in ['dos64','dos64-tests']:
  if json.loads((work/'build'/(n+'.memory.json')).read_text()).get('passed')is not True:raise RuntimeError('Native memory verification failed')
 if not default:
  labels=(work/'build/dos64-tests.labels').read_text()
  if '.sav_drive\n'not in labels or '.dos64_export_crc_raw\n'not in labels:raise RuntimeError('Selected/CRC native profile absent')
 return flags
def build(out,test=True,default=False):
 if test and default:raise RuntimeError('Default profile is native-only')
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);owner=out/'OWNER.json'
 if owner.exists():
  if json.loads(owner.read_text())!=OWNER:raise RuntimeError('Output has another owner')
 elif any(out.iterdir()):raise RuntimeError('Use an empty or native-media-owned output directory')
 else:atomic_json(owner,OWNER)
 lock=out/'LOCK';fd=None
 run=None;owned=False;unlock_attempted=False;primary=None;phase='lock';record={str(Path(__file__).resolve()):digest(Path(__file__).resolve())};commands=[]
 try:
  fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);owned=True
  os.write(fd,str(os.getpid()).encode());os.close(fd);fd=None
  phase='run';run=Path(tempfile.mkdtemp(prefix='run-',dir=out));e=run/'evidence';e.mkdir()
  copy(Path(__file__).resolve(),e/'DRIVER_SOURCE.py',record);copy(ROOT/'build_support/native_media_sources.json',e/'SOURCE_INVENTORY.json',record)
  phase='tools';t=tools(test)
  for q in [*t.values(),Path(sys.executable).resolve()]:record[str(q)]=digest(q)
  # ca65's explicit default macro distribution is a source input.
  resources=t['ca65'].parent.parent/'share/cc65/asminc'
  if not resources.is_dir():
   resources=next((q for q in [Path('/opt/homebrew/share/cc65/asminc'),Path('/usr/share/cc65/asminc')]if q.is_dir()),None)
  if resources is None:raise RuntimeError('Cannot locate ca65 macro sources')
  for q in resources.rglob('*'):
   if q.is_file():record[str(q.resolve())]=digest(q)
  phase='sources';work=stage(run,record,test);env=command_environment(work,t)
  atomic_json(e/'INPUTS_BEFORE.json',record)
  def command(argv,cwd=None):
   args=[str(x)for x in argv];commands.append({'argv':args,'cwd':str(cwd or run)})
   with(e/'commands.stdout').open('ab')as o,(e/'commands.stderr').open('ab')as err:subprocess.run(args,cwd=cwd or run,stdin=subprocess.DEVNULL,stdout=o,stderr=err,check=True,env=env)
  phase='native';flags=native(work,t,command,default)
  products={str(q):digest(q)for q in (work/'build').rglob('*')if q.is_file()};groups={}
  if test:
   phase='models';shared=['-dynamiclib']if platform.system()=='Darwin'else['-shared','-fPIC']
   command([t['clang++'],'-std=c++20','-O2',*shared,'-Iwork/third_party/peddle/Peddle','-Imodel/tests/host','-Imodel/tests/floppy_export','model/tests/floppy_export/bridge.cpp',*[Path('work/third_party/peddle/Peddle')/n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','model/save-peddle.dylib'])
   phase='compile-zig';command([t['zig'],'build','--build-file','build_save_tests.zig','compile'])
   for q in [run/'model/save-peddle.dylib',run/'zig-out/bin/save-tests']:products[str(q)]=digest(q)
  atomic_json(e/'PRODUCTS_BEFORE.json',products)
  if test:
   for name,script,report,count in SUITES:
    phase='test-'+name;command([sys.executable,'-B',script]);j=json.loads((run/report).read_text())
    if j.get('successful')is not True or j.get('tests')!=count:raise RuntimeError('Unexpected '+name+' test result')
    groups[name]=count
   phase='test-zig';command([run/'zig-out/bin/save-tests'])
   if 'All 3 tests passed.'not in(e/'commands.stderr').read_text():raise RuntimeError('Expected3 directly executed Zig groups')
   groups['direct_Zig']=3
  phase='closure';verify(record);verify(products);atomic_json(e/'INPUTS_AFTER.json',record);atomic_json(e/'PRODUCTS_AFTER.json',products)
  phase='products';published={};dest=run/'products';dest.mkdir()
  for name in PUBLISH:
   s=work/'build'/name;d=dest/name;shutil.copyfile(s,d)
   if digest(d)!=products[str(s)]:raise RuntimeError('Published copy mismatch: '+name)
   d.chmod(0o444);published[name]={'path':str(d),**digest(d)}
  verify(record);verify(products)
  result={'status':'passed','scope':'NATIVE_MEDIA_SYNTHETIC_MODEL_NO_HARDWARE_CLEAN_CFG_OR_UI_ACCEPTANCE','run':str(run),'products':published,'source_inputs':record,'native_products':products,'flags':flags,'groups':groups,'commands':commands}
  phase='run-result';atomic_json(run/'RESULT.json',result)
  # Release the host build lock before publishing the only mutable passed pointer.
  # Every pointed-to product and run RESULT is already complete and immutable.
  phase='unlock';unlock_attempted=True;lock.unlink();owned=False
  phase='publication';atomic_json(out/'RESULT.json',result)
  return result
 except BaseException as ex:
  primary=ex;failure={'status':'failed','phase':phase,'run':str(run)if run else None,'error':type(ex).__name__+': '+str(ex),'commands':commands}
  for q in ([run/'FAILURE.json']if run is not None else [])+[out/'LAST_FAILURE.json']:
   try:atomic_json(q,failure)
   except BaseException:pass
  raise
 finally:
  cleanup=None
  if fd is not None:
   try:os.close(fd)
   except BaseException as ex:cleanup=ex
  if owned and not unlock_attempted:
   try:lock.unlink()
   except BaseException as ex:
    if cleanup is None:cleanup=ex
  if primary is None and cleanup is not None:raise cleanup

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'build/native-media');p.add_argument('--native-only',action='store_true');p.add_argument('--default-profile',action='store_true',help='Native-only proof of unchanged default bytes');a=p.parse_args()
 if a.default_profile and not a.native_only:p.error('--default-profile requires --native-only')
 r=build(a.out,test=not a.native_only,default=a.default_profile);print(json.dumps({'status':r['status'],'run':r['run'],'groups':r['groups'],'products':r['products']},indent=2))
if __name__=='__main__':main()
