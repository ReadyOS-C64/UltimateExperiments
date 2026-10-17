#!/usr/bin/env python3
"""Construct an exact cold runtime bundle from one immutable source cohort.

This copies qualified products and binds their source metadata; it does not
build native code, configure an installation, or grant hardware authority.
"""
from pathlib import Path
import os,sys
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-cold-bundle-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache path must remain absent')
import argparse,hashlib,importlib.util,json,shutil,tempfile
ASSETS={'DOS64.PRG','DOS64.REL','START.INO','START.TPL','START.REL','DOS64.MNU','START.RCV','START.RFW'}
METADATA={'START.labels','START.map','DOS64.labels'}
def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def atomic(p,j):
 q=p.with_name(p.name+'.tmp-'+str(os.getpid()));q.write_text(json.dumps(j,indent=2)+'\n');os.replace(q,p)
def verify(rows):
 for n,d in rows.items():
  if digest(Path(n))!=d:raise RuntimeError('Source changed: '+n)
def construct(out,cohort,inputs,*,mnu56k=False):
 cohort=cohort.resolve();input_path=inputs.resolve();spec=json.loads(input_path.read_text());sealed=json.loads(cohort.read_text())
 if set(spec)!= {'assets','metadata'}or set(spec['assets'])!=ASSETS or set(spec['metadata'])!=METADATA:raise ValueError('Exact eight assets and three source metadata files required')
 authorized={}
 for n,v in sealed['files'].items():
  p=Path(n);p=(p if p.is_absolute()else cohort.parent/p).resolve();authorized[str(p)]=v['sha256']if isinstance(v,dict)else v
 paths={}
 for kind in ['assets','metadata']:
  for name,n in spec[kind].items():
   p=Path(n).resolve()
   if not p.is_relative_to(cohort.parent)or str(p)not in authorized or digest(p)['sha256']!=authorized[str(p)]:raise ValueError('Input not exact in selected source cohort: '+name)
   paths[name]=p
 out=out.resolve()
 if out.is_relative_to(cohort.parent):raise ValueError('Output cannot modify source cohort')
 out.mkdir(parents=True,exist_ok=True)
 marker=out/'OWNER.json';owner={'kind':'cold-release-bundle','version':1}
 if marker.exists():
  if json.loads(marker.read_text())!=owner:raise ValueError('Output owner mismatch')
 elif any(out.iterdir()):raise ValueError('Output must be empty or builder-owned')
 else:atomic(marker,owner)
 lock=out/'LOCK';fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);run=None
 rows={str(Path(__file__).resolve()):digest(Path(__file__).resolve()),str(cohort):digest(cohort),str(input_path):digest(input_path),str(Path(sys.executable).resolve()):digest(Path(sys.executable).resolve())}
 try:
  run=Path(tempfile.mkdtemp(prefix='run-',dir=out));bundle=run/'bundle';bundle.mkdir();(run/'start').mkdir();(run/'main/build').mkdir(parents=True)
  for name,p in paths.items():
   d=digest(p);q=bundle/name if name in ASSETS else run/({'START.labels':'start/controller.labels','START.map':'start/controller.map','DOS64.labels':'main/build/dos64.labels'}[name]);shutil.copyfile(p,q)
   if digest(q)!=d:raise RuntimeError('Copy mismatch: '+name)
   rows[str(p)]=rows[str(q)]=d
  # Source-only dependency import: cache path was installed before importlib.
  mods={}
  for name,file in [('bundle','start_ini_bundle.py'),('template','start_template_descriptor.py'),('release','setup_release_descriptor.py'),('start','start_launcher.py')]:
   p=ROOT/'build_support'/file;rows[str(p)]=digest(p);s=importlib.util.spec_from_file_location('cold_bound_'+name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);mods[name]=m
  atomic(run/'INPUTS_BEFORE.json',rows)
  view=mods['bundle'].validate_bundle(bundle,run/'start/controller.labels',run/'start/controller.map',run/'main/build/dos64.labels',mods=mods,start20k=True,cold_inventory=True,mnu56k=mnu56k)
  verify(rows);atomic(run/'INPUTS_AFTER.json',rows)
  result={'status':'passed','scope':'EXACT_SOURCE_CLOSED_COLD_EIGHT_ASSET_BUNDLE_NOT_CONFIGURED_INSTALLATION','run':str(run),'bundle':str(bundle),'assets':{n:digest(bundle/n)for n in sorted(ASSETS)},'source_inputs':rows,'memory':view,'source_cohort':{'path':str(cohort),**digest(cohort)},'physical':False,'publication':'all sources/capsules/metadata verified, immutable run/RESULT then output pointer'}
  atomic(run/'RESULT.json',result);atomic(out/'RESULT.json',result);return result
 except BaseException as ex:
  failure={'status':'failed','error':repr(ex),'run':str(run),'published_new_result':False}
  for p in ([run/'FAILURE.json']if run else[])+[out/'LAST_FAILURE.json']:
   try:atomic(p,failure)
   except BaseException:pass
  raise
 finally:
  active=sys.exc_info()[0]is not None
  try:lock.unlink()
  except BaseException:
   if not active:raise
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cohort',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mnu56k',action='store_true');a=p.parse_args();r=construct(a.out,a.cohort,a.inputs,mnu56k=a.mnu56k);print(r['bundle'])
if __name__=='__main__':main()
