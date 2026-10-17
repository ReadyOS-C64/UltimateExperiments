#!/usr/bin/env python3
"""Source-only coupled INI release. A passed RESULT is the publication authority."""
import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.pycache_prefix=str(ROOT/'build'/('.absent-ini-bundle-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache prefix must be absent')
import argparse,hashlib,importlib.util,json,shutil,struct,subprocess,tempfile,zlib
ASSETS=('START.TPL','START.REL','START.INO','DOS64.PRG','DOS64.REL')

def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def dependencies():
 return {n:ROOT/'build_support'/f for n,f in [('start','start_launcher.py'),('template','start_template_descriptor.py'),('release','setup_release_descriptor.py')]}
def verify(record):
 for n,w in record.items():
  if digest(Path(n))!=w:raise RuntimeError('Source/product changed: '+n)
def copy(source,destination,record):
 wanted=digest(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
 if digest(destination)!=wanted:raise RuntimeError('Copy changed: '+str(source))
 record[str(source)]=wanted;record[str(destination)]=wanted

def validate_bundle(bundle,start_labels,start_map,main_labels,mods=None,*,start20k=False,cold_inventory=False,mnu56k=False):
 if mnu56k and not(start20k and cold_inventory):raise RuntimeError('56KiB MNU requires explicit cold20KiB profile')
 selected=ASSETS+('DOS64.MNU','START.RCV','START.RFW')if cold_inventory else ASSETS
 if {p.name for p in bundle.iterdir()if p.is_file()}!=set(selected):raise RuntimeError('Exact selected coupled release inventory required')
 if mods is None:mods={n:module('ini_check_'+n,q)for n,q in dependencies().items()}
 start=(bundle/'START.TPL').read_bytes();asset=(bundle/'START.INO').read_bytes();main=(bundle/'DOS64.PRG').read_bytes();sr=(bundle/'START.REL').read_bytes();mr=(bundle/'DOS64.REL').read_bytes()
 if mods['template'].make(start,start_labels.read_text(),start_map.read_text(),start20k=start20k)!=sr:raise RuntimeError('START descriptor does not bind template')
 if mods['release'].descriptor(main,main_labels.read_text(),options=True)!=mr:raise RuntimeError('Main options descriptor does not bind main')
 s=mods['template'].labels(start_labels.read_text());at=s['_so_overlay_spec']-0x0801+2;view=mods['template'].validate(sr,start,start20k=start20k);data=view['DATA_offset'];count=view['DATA_bytes']
 if at<data or at-data>count or 16>count-(at-data):raise RuntimeError('Overlay capsule is not initialized bound DATA')
 if start[at:at+6]!=b'D64I\1\20' or start[at+12:at+16]!=b'\0\x60\0\0' or int.from_bytes(start[at+6:at+8],'little')!=len(asset) or int.from_bytes(start[at+8:at+12],'little')!=zlib.crc32(asset):raise RuntimeError('Overlay count/CRC/run binding mismatch')
 if len(start)!=(20480 if start20k else 18432) or not 0<len(asset)<=8192 or s['__PRELAUNCH_RUN__']!=0x6000 or s['__PRELAUNCH_RO_RUN__']+s['__PRELAUNCH_RO_SIZE__']!=0x6000+len(asset):raise RuntimeError('Overlay lifetime/layout bounds')
 if cold_inventory:
  if not start20k:raise RuntimeError('Cold inventory requires20KiB profile')
  for sym,name,magic,run,limit in [('_sm_modal_spec','DOS64.MNU',b'D64M',0x3da000,(57344 if mnu56k else 40960)),('_sj_gate_spec','START.RCV',b'D64G',0x6000,8192),('_sr_worker_spec','START.RFW',b'D64F',0xa000,8192)]:
   off=s[sym]-0x801+2;n=16 if magic!=b'D64G'else 24;c=start[off:off+n];body=(bundle/name).read_bytes()
   if off<data or off-data>count or n>count-(off-data) or c[:6]!=magic+bytes([1,n]) or not 0<len(body)<=limit or int.from_bytes(c[6:8],'little')!=len(body) or int.from_bytes(c[8:12],'little')!=zlib.crc32(body):raise RuntimeError('Cold asset count/CRC/DATA binding '+name)
   if magic==b'D64M':
    header=s['_sm_modal_header']-0x801+2
    if header<data or header-data>count or 64>count-(header-data) or len(body)!=(57344 if mnu56k else 40960) or int.from_bytes(c[12:16],'little')!=run or body[:8]!=b'D64M\1\1\100\0' or body[:64]!=start[header:header+64]:raise RuntimeError('Cold MNU header/run')
   elif int.from_bytes(c[12:14],'little')!=run or not run<=int.from_bytes(c[14:16],'little')<run+len(body):raise RuntimeError('Cold executable run/entry')
 if mr[4]!=2:raise RuntimeError('Coupled bundle requires D64L2')
 return {'template_bytes':len(start),'overlay_bytes':len(asset),'overlay_run':0x6000,'overlay_end_exclusive':0x6000+len(asset),'capsule_file_offset':at,'main_bytes':len(main),'options_required_file_offset':int.from_bytes(mr[56:60],'little'),'D64S_version':1,'D64L_version':2}

def atomic_json(path,value):
 pending=path.with_name(path.name+'.tmp-'+str(os.getpid()));pending.write_text(json.dumps(value,indent=2)+'\n');os.replace(pending,path)

def build(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=out));start=run/'start';main=run/'main';bundle=run/'bundle';evidence=run/'evidence'
 for d in [start,main,bundle,evidence]:d.mkdir()
 record={str(Path(__file__).resolve()):digest(Path(__file__).resolve())};commands=[];phase='load builders'
 try:
  deps=dependencies();record.update({str(q):digest(q)for q in deps.values()});mods={n:module('ini_bundle_'+n,q)for n,q in deps.items()};t=mods['start'].tools()
  for name in ['make']:
   value=shutil.which(os.environ.get('DOS64_'+name.upper(),name))
   if not value:raise RuntimeError('Required tool: '+name)
   t[name]=str(Path(value).resolve())
  t['python']=str(Path(sys.executable).resolve());record.update({str(Path(q)):digest(Path(q))for q in t.values()})
  for name in ['string.h','stddef.h']:
   q=Path(t['cc65']).parent.parent/'share/cc65/include'/name
   if q.is_file():record[str(q)]=digest(q)
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');env.update({'DOS64_'+n.upper():str(t[n])for n in ['cc65','ca65','ld65']});env.update(DOS64_CC65_LIB=str(t['library']),DOS64_PYTHON=t['python'])
  for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
  phase='stage exact public main graph'
  for name in ['src','include','cfg','assets','build_support']:
   for q in sorted((ROOT/name).rglob('*')):
    if q.is_file()and not any(p in ['__pycache__','.zig-cache']for p in q.parts):copy(q,main/q.relative_to(ROOT),record)
  copy(ROOT/'Makefile',main/'Makefile',record)
  phase='stage START graph';mods['start'].sources(start,record,options=True)
  selected=dict(mods['start'].NATIVE,**mods['start'].OPTIONS_NATIVE)
  for name in selected:record[str(start/name)]=digest(start/name)
  atomic_json(evidence/'INPUTS_BEFORE.json',record)
  phase='actual START build'
  with(evidence/'START.stdout').open('wb')as o,(evidence/'START.stderr').open('wb')as e:
   # Reuse the existing builder graph and record every exact compiler command.
   def start_command(argv,cwd):
    argv=[str(x)for x in argv];commands.append(argv)
    subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=o,stderr=e,check=True)
   mods['start'].command=start_command
   mods['start'].build(start,t,options=True)
  phase='actual main build';argv=[t['make'],'build/dos64.prg'];commands.append(argv)
  with(evidence/'MAIN.stdout').open('wb')as o,(evidence/'MAIN.stderr').open('wb')as e:subprocess.run(argv,cwd=main,env=env,stdin=subprocess.DEVNULL,stdout=o,stderr=e,check=True)
  phase='bind matched descriptors'
  for q,d in [(start/'controller.prg',bundle/'START.TPL'),(start/'START.INO',bundle/'START.INO'),(main/'build/dos64.prg',bundle/'DOS64.PRG')]:shutil.copyfile(q,d)
  (bundle/'START.REL').write_bytes(mods['template'].make((bundle/'START.TPL').read_bytes(),(start/'controller.labels').read_text(),(start/'controller.map').read_text()))
  (bundle/'DOS64.REL').write_bytes(mods['release'].descriptor((bundle/'DOS64.PRG').read_bytes(),(main/'build/dos64.labels').read_text(),options=True))
  memory=validate_bundle(bundle,start/'controller.labels',start/'controller.map',main/'build/dos64.labels',mods)
  products={str(q):digest(q)for d in [start,main/'build',bundle]for q in d.iterdir()if q.is_file()and q.suffix in ['.prg','.bin','.TPL','.INO','.PRG','.REL','.labels','.map','.o','.s','.json']and str(q)not in record}
  atomic_json(evidence/'PRODUCTS_BEFORE.json',products);verify(record);verify(products);atomic_json(evidence/'INPUTS_AFTER.json',record);atomic_json(evidence/'PRODUCTS_AFTER.json',products)
  result={'status':'passed','scope':'COUPLED_SOURCE_ONLY_INI_RELEASE_NOT_CONFIGURED_INSTALLATION','run':str(run),'bundle':str(bundle),'assets':{n:digest(bundle/n)for n in ASSETS},'source_inputs':record,'products':products,'memory':memory,'commands':commands,'physical':False,'publish_order':'validate all five assets and source/products, then atomic run/RESULT, then output/RESULT; never a standalone options START','default_release_version':1,'default_START_target_invoked':False}
  phase='publish result';atomic_json(run/'RESULT.json',result);atomic_json(out/'RESULT.json',result);return result
 except BaseException as e:
  atomic_json(run/'FAILURE.json',{'status':'failed','phase':phase,'error':str(e),'published_new_result':False,'prior_output_result_preserved':True});raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'build/start-ini-bundle');a=p.parse_args();r=build(a.out);print(r['bundle'])
if __name__=='__main__':main()
