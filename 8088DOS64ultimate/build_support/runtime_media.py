#!/usr/bin/env python3
"""Source-build the optional real-runtime media menu and its 56 KiB container."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.pycache_prefix=str(ROOT/'build'/('.absent-runtime-media-'+str(__import__('os').getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only import cache must be absent')
if sys.flags.optimize:raise RuntimeError('Optimized Python cannot enforce native source assertions')
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile,zlib
OWNER={'kind':'dos64-runtime-media','schema':1}
FLAGS={'DOS64_MODAL_MENU':1,'DOS64_SAVE_HD_CONTEXT':1,'DOS64_EXPORT_CRC':1,'DOS64_SAVE_MODAL':1,'DOS64_MEDIA_BINDING':1}
SCRUB=('PYTHONOPTIMIZE','PYTHONPATH','PYTHONPYCACHEPREFIX','PYTHONHOME','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','CPATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH','OBJC_INCLUDE_PATH','LIBRARY_PATH','COMPILER_PATH','GCC_EXEC_PREFIX','MAKEFLAGS','MFLAGS','MAKEOVERRIDES')
def digest(p):
 b=Path(p).read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def atomic_json(p,v):
 tmp=p.with_name(p.name+'.tmp-'+str(os.getpid()));primary=None
 try:tmp.write_text(json.dumps(v,indent=2)+'\n');os.replace(tmp,p)
 except BaseException as ex:primary=ex;raise
 finally:
  try:tmp.unlink(missing_ok=True)
  except BaseException:
   if primary is None:raise

def verify(records):
 for p,w in records.items():
  if digest(p)!=w:raise RuntimeError('Source/product changed: '+p)
def safe(s):
 if not isinstance(s,str)or not s or '\\'in s or Path(s).is_absolute()or any(n in ('','.','..')for n in s.split('/')):raise RuntimeError('Unsafe inventory path')
 return Path(s)
def module(path):
 spec=importlib.util.spec_from_file_location('runtime_release_descriptor',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def tools():
 t={}
 for n in ['make','cc65','ca65','ld65']:
  choice=os.environ.get('DOS64_'+n.upper(),n);q=shutil.which(choice)
  if not q:raise RuntimeError('Set DOS64_'+n.upper()+' to '+n)
  t[n]=Path(q).resolve()
 roots=[t['cc65'].parent.parent/'share/cc65',Path('/opt/homebrew/share/cc65'),Path('/usr/share/cc65')]
 lib=os.environ.get('DOS64_CC65_LIB')
 t['library']=Path(lib).expanduser().resolve()if lib else next((d/'lib/none.lib'for d in roots if(d/'lib/none.lib').is_file()),None)
 if not t['library']or not t['library'].is_file():raise RuntimeError('Set DOS64_CC65_LIB to none.lib')
 t['resources']=t['library'].parent.parent
 if not all((t['resources']/d).is_dir()for d in ['asminc','include']):raise RuntimeError('cc65 source resources absent beside library')
 return t

def stage(run,records):
 inventory=ROOT/'build_support/runtime_media_sources.json';j=json.loads(inventory.read_text())
 if set(j)!={'schema','core','media'}or j['schema']!=1:raise RuntimeError('Unsupported source inventory')
 w=run/'native_media';w.mkdir();archive=run/'inputs';archive.mkdir()
 selected={str(Path('work')/safe(n)):n for n in j['core']}
 for n,source in j['media'].items():
  if str(safe(n))in selected:raise RuntimeError('Duplicate inventory output')
  selected[str(safe(n))]=source
 selected['work/build_support/runtime_media.py']='build_support/runtime_media.py'
 selected['work/build_support/runtime_media_sources.json']='build_support/runtime_media_sources.json'
 for dest,source in selected.items():
  s=(ROOT/safe(source)).resolve()
  if not s.is_relative_to(ROOT)or not s.is_file():raise RuntimeError('Missing or escaping input: '+source)
  d=w/safe(dest);a=archive/safe(source);d.parent.mkdir(parents=True,exist_ok=True);a.parent.mkdir(parents=True,exist_ok=True);wanted=digest(s)
  shutil.copyfile(s,d);shutil.copyfile(s,a)
  if digest(d)!=wanted or digest(a)!=wanted or digest(s)!=wanted:raise RuntimeError('Source copy mismatch')
  records[str(s)]=wanted;records[str(a)]=wanted
 # Inventory completeness is required even for Make includes unused by this target.
 for line in re.findall(r'^include\s+([^\n]+)',(w/'work/Makefile').read_text(),re.M):
  for n in line.split():
   if not(w/'work'/safe(n)).is_file():raise RuntimeError('Missing Make include: '+n)
 return w

def build(out,floppy_format=False,cpu_trap=False):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);owner=out/'OWNER.json'
 if owner.exists():
  if json.loads(owner.read_text())!=OWNER:raise RuntimeError('Different output owner')
 elif any(out.iterdir()):raise RuntimeError('Use an empty or owned output directory')
 else:atomic_json(owner,OWNER)
 fd=None;owned=False;unlock_attempted=False;primary=None;run=None;phase='lock';records={str(Path(__file__).resolve()):digest(__file__)};commands=[]
 try:
  fd=os.open(out/'LOCK',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);owned=True;os.write(fd,str(os.getpid()).encode());os.close(fd);fd=None
  phase='run';run=Path(tempfile.mkdtemp(prefix='run-',dir=out));phase='tools';t=tools()
  for q in [t[n]for n in ['make','cc65','ca65','ld65','library']]+[Path(sys.executable).resolve()]:records[str(q)]=digest(q)
  for folder in ['asminc','include']:
   for q in sorted((t['resources']/folder).rglob('*')):
    if q.is_file():records[str(q.resolve())]=digest(q)
  phase='stage';work=stage(run,records);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
  for k in SCRUB:env.pop(k,None)
  # Every compiler subprocess, including subordinate scripts, uses these exact tools.
  farm=run/'tool-bin';farm.mkdir()
  for n in ['make','cc65','ca65','ld65']:(farm/n).symlink_to(t[n]);env['DOS64_'+n.upper()]=str(t[n])
  env['PATH']=str(farm)+os.pathsep+os.defpath;env['DOS64_CC65_LIB']=str(t['library']);env['DOS64_PYTHON']=str(Path(sys.executable).resolve())
  atomic_json(run/'INPUTS_BEFORE.json',records)
  phase='native build';command=[str(Path(sys.executable).resolve()),'-B','build_ui_bridge.py','--role','runtime']+(['--floppy-format']if floppy_format else [])+(['--cpu-trap']if cpu_trap else []);commands.append({'argv':command,'cwd':str(work)})
  with(run/'build.stdout').open('wb')as o,(run/'build.stderr').open('wb')as e:subprocess.run(command,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=o,stderr=e,check=True)
  phase='validate';j=json.loads((work/'UI_BUILD_RESULT.json').read_text());main=work/'work/build/dos64.prg';labels=work/'work/build/dos64.labels';menu=work/'MODAL.MNU';header=(work/'HEADER.bin').read_bytes()
  if j['role']!='runtime'or len(header)!=64 or header[:8]!=b'D64M\1\1\x40\0'or menu.stat().st_size!=57344 or menu.read_bytes()[:64]!=header or main.read_bytes().count(header[8:24])!=1:raise RuntimeError('Actual runtime/menu cohort mismatch')
  if '.fixture_return\n'in labels.read_text()or 'UNITEXTRA'in labels.read_text():raise RuntimeError('Unit role is not a release')
  memory=json.loads((work/'work/build/dos64.memory.json').read_text())
  if memory.get('passed')is not True:raise RuntimeError('Native memory checks failed')
  if bool(memory.get('load',{}).get('cpu_trap'))!=cpu_trap:raise RuntimeError('CPU trap profile mismatch')
  validation=module(work/'verify_runtime.py').verify('runtime')
  if validation['SAVER_bytes']!=len((work/'work/build/dos64-resident.prg.saver.bin').read_bytes()):raise RuntimeError('SAVER metadata mismatch')
  atomic_json(run/'ROLE_VALIDATION.json',validation)
  rel=work/'DOS64.REL';rel.write_bytes(module(work/'work/build_support/setup_release_descriptor.py').descriptor(main.read_bytes(),labels.read_text(),options=True))
  # Keep all generated objects, maps, aliases and packing metadata in this immutable run.
  native_products={str(q):digest(q)for q in work.rglob('*')if q.is_file()and not q.is_relative_to(work/'work/third_party')}
  verify(records);atomic_json(run/'PRODUCTS_BEFORE.json',native_products)
  phase='products';dest=run/'products';dest.mkdir();published={}
  for name,q in {'DOS64.PRG':main,'DOS64.MNU':menu,'DOS64.REL':rel,'DOS64.labels':labels,'DOS64.map':work/'work/build/dos64.map','DOS64.memory.json':work/'work/build/dos64.memory.json','MODAL_HEADER.bin':work/'HEADER.bin','MEDIA_BUILD.json':work/'UI_BUILD_RESULT.json','MEDIA_PHASES.json':work/'CONTROLLER_BUILD.json'}.items():
   d=dest/name;shutil.copyfile(q,d)
   if digest(d)!=digest(q):raise RuntimeError('Published copy mismatch')
   d.chmod(0o444);published[name]={'path':str(d),**digest(d)}
  verify(records);verify(native_products);atomic_json(run/'INPUTS_AFTER.json',records);atomic_json(run/'PRODUCTS_AFTER.json',native_products)
  result={'schema':1,'status':'passed','scope':'SOURCE_BUILT_OPTIONAL_RUNTIME_MEDIA_NO_COLD_DOS_HARDWARE_ACCEPTANCE','run':str(run),'work':str(work),'role':'runtime','flags':dict(FLAGS,DOS64_FLOPPY_FORMAT=int(floppy_format),**({'DOS64_TRAP1':1}if cpu_trap else {})),'MNU_bytes':57344,'MNU_REU_spans':[[0x3da000,24576],[0x3f0000,32768]],'header':header.hex(),'products':published,'assets':{n:{k:v[k]for k in ['sha256','bytes']}for n,v in published.items()if n in ['DOS64.PRG','DOS64.REL','DOS64.MNU']},'source_inputs':records,'native_products':native_products,'commands':commands,'physical':False}
  phase='run result';atomic_json(run/'RESULT.json',result)
  phase='unlock';unlock_attempted=True;(out/'LOCK').unlink();owned=False
  phase='publication';atomic_json(out/'RESULT.json',result);return result
 except BaseException as ex:
  primary=ex;failure={'status':'failed','phase':phase,'run':str(run)if run else None,'error':type(ex).__name__+': '+str(ex),'prior_result_preserved':True}
  for q in ([run/'FAILURE.json']if run else [])+[out/'LAST_FAILURE.json']:
   try:atomic_json(q,failure)
   except BaseException:pass
  raise
 finally:
  cleanup=None
  if fd is not None:
   try:os.close(fd)
   except BaseException as ex:cleanup=ex
  if owned and not unlock_attempted:
   try:(out/'LOCK').unlink()
   except BaseException as ex:
    if cleanup is None:cleanup=ex
  if primary is None and cleanup is not None:raise cleanup

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'build/runtime-media');p.add_argument('--floppy-format',action='store_true',help='Enable XT360K FORMAT in the runtime-only profile');p.add_argument('--cpu-trap',action='store_true',help='Enable original8088 type1 trap correctness in this optional runtime');a=p.parse_args();r=build(a.out,floppy_format=a.floppy_format,cpu_trap=a.cpu_trap);print(json.dumps({'status':r['status'],'run':r['run'],'products':r['products']},indent=2))
if __name__=='__main__':main()
