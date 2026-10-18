#!/usr/bin/env python3
"""Opt-in source-built SETUP runtime preflight tests; no DOS images or hardware."""
from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-setup-preflight-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache prefix must be absent')
import argparse,hashlib,importlib.util,json,shutil,subprocess,tempfile

def digest(p):
 b=Path(p).read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def verify(record):
 for n,v in record.items():
  if digest(n)!=v:raise RuntimeError('Source/product changed: '+n)
def copy(p,q,record):
 v=digest(p);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 if digest(p)!=v or digest(q)!=v:raise RuntimeError('Source copy changed: '+str(p))
 record[str(p)]=v;record[str(q)]=v
def module(name,path,record):
 record[str(path)]=digest(path);s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def tool(name,env):
 q=shutil.which(os.environ.get(env,name))
 if not q:raise RuntimeError('Set '+env+' to '+name)
 return str(Path(q).resolve())
def command(argv,cwd,env,log,commands):
 argv=list(map(str,argv));commands.append({'cwd':str(cwd),'argv':argv})
 with log.with_suffix('.stdout').open('wb')as o,log.with_suffix('.stderr').open('wb')as e:r=subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=o,stderr=e)
 if r.returncode:raise RuntimeError('Command failed; inspect '+str(log.with_suffix('.stderr')))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle-result',type=Path,required=True,help='Qualified coupled release RESULT; make start-ini-bundle first')
 p.add_argument('--out',type=Path,default=ROOT/'build/setup-preflight-tests');a=p.parse_args()
 if not a.bundle_result.is_file():raise RuntimeError('Missing coupled RESULT; run make start-ini-bundle or pass --bundle-result PATH')
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=out));commands=[];phase='tools';record={str(Path(__file__).resolve()):digest(__file__)};products={}
 try:
  s=module('setup_preflight_production',ROOT/'build_support/setup_installer.py',record);t=s.toolchain();t['python']=str(Path(sys.executable).resolve());t['clang++']=tool('clang++','DOS64_CLANGXX')
  record.update({str(Path(q)):digest(q)for q in t.values()})
  env=s.command_environment();env.update({'DOS64_'+n.upper():t[n]for n in ['cc65','ca65','ld65']});env.update(DOS64_CC65_LIB=t['library'],DOS64_PYTHON=t['python'])
  phase='bound production source build';command([t['python'],'-B',ROOT/'build_support/setup_installer.py','--bundle-result',a.bundle_result.resolve(),'--out',run/'production'],ROOT,env,run/'BOUND_BUILD',commands)
  built=json.loads((run/'production/RESULT.json').read_text());assert built['status']=='passed'and built['runtime_preflight'];record.update(built['source_inputs']);work=Path(built['work'])
  phase='default production source build';command([t['python'],'-B',ROOT/'build_support/setup_installer.py','--out',run/'default'],ROOT,env,run/'DEFAULT_BUILD',commands)
  baseline=json.loads((run/'default/RESULT.json').read_text());assert baseline['status']=='passed'and not baseline['runtime_preflight'];record.update(baseline['source_inputs'])
  phase='source-only model/test staging'
  for folder in [ROOT/'tests/setup_installer',ROOT/'tests/setup_preflight']:
   for q in sorted(folder.iterdir()):
    if q.is_file()and q.suffix=='.py':copy(q,work/q.name,record)
  support=ROOT/'tests/setup_installer/support'
  for q in sorted(support.rglob('*')):
   if q.is_file():copy(q,work/q.relative_to(support),record)
  host=ROOT/'tests/setup_preflight_host/test_binding.py';record[str(host)]=digest(host)
  shared=['-dynamiclib']if sys.platform=='darwin'else['-shared','-fPIC']
  phase='actual model compile';command([t['clang++'],'-std=c++20','-O2',*shared,'-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle','tests/floppy_export/bridge.cpp',*[str(Path('third_party/peddle/Peddle')/n)for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','browser-peddle.dylib'],work,env,run/'MODEL_BUILD',commands)
  products={str(q):digest(q)for base in [work/'build',Path(baseline['work'])/'build']for q in base.rglob('*')if q.is_file()};products[str(work/'browser-peddle.dylib')]=digest(work/'browser-peddle.dylib')
  verify(record);verify(products);(run/'INPUTS_BEFORE.json').write_text(json.dumps(record,indent=2)+'\n');(run/'PRODUCTS_BEFORE.json').write_text(json.dumps(products,indent=2)+'\n')
  # Host controls consume this explicitly provisional fixture; it is not a pass
  # receipt and is never published as RESULT before actual native execution.
  fixture={'work':str(work),'bound_result':str(run/'production/RESULT.json'),'default_result':str(run/'default/RESULT.json'),'builder':str(ROOT/'build_support/setup_installer.py')}
  (run/'FIXTURE.json').write_text(json.dumps(fixture,indent=2)+'\n');env['DOS64_SETUP_PREFLIGHT_FIXTURE']=str(run/'FIXTURE.json')
  phase='portable host binding/source controls';command([t['python'],'-B',host],ROOT,env,run/'HOST',commands)
  host_log=(run/'HOST.stderr').read_text();assert host_log.rstrip().endswith('OK')
  phase='actual native SYS/CIA preflight';command([t['python'],'-B','test_preflight_final.py'],work,env,run/'NATIVE',commands)
  native=json.loads((work/'FINAL_PREFLIGHT_RESULTS.json').read_text());assert native['passed']and native['tests']==2
  phase='actual native loader adversaries';command([t['python'],'-B','test_runtime_negative.py'],work,env,run/'NEGATIVE',commands)
  negative=json.loads((work/'RUNTIME_NEGATIVE_RESULTS.json').read_text());assert negative['passed']and negative['tests']==6
  phase='source/product close';verify(record);verify(products)
  (run/'INPUTS_AFTER.json').write_text(json.dumps(record,indent=2)+'\n');(run/'PRODUCTS_AFTER.json').write_text(json.dumps(products,indent=2)+'\n')
  result={'status':'passed','scope':'SOURCE_BUILT_NATIVE_EARLY_SETUP_PREFLIGHT_NOT_FULL_INSTALLER_OR_GUEST_BOOT','run':str(run),'work':str(work),'bound_result':fixture['bound_result'],'default_result':fixture['default_result'],'native_groups':8,'host_groups':int(host_log.split('Ran ')[-1].split(' tests')[0]),'source_inputs':record,'products':products,'native':digest(work/'build/setup.prg'),'memory':built['memory'],'release':built['release'],'commands':commands,'DOS_images_required':False,'prebuilt_model_used':False,'hardware':False}
  s.verify(record);s.verify(products);(run/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');pending=out/('RESULT.pending-'+str(os.getpid())+'.json');pending.write_text(json.dumps(result,indent=2)+'\n');os.replace(pending,out/'RESULT.json');print('PASS native8 + host'+str(result['host_groups'])+': '+str(run))
 except BaseException as first:
  try:(run/'FAILURE.json').write_text(json.dumps({'status':'failed','phase':phase,'first_type':type(first).__name__,'first_message':str(first),'prior_output_RESULT_preserved':True},indent=2)+'\n')
  except BaseException:pass
  raise
if __name__=='__main__':main()
