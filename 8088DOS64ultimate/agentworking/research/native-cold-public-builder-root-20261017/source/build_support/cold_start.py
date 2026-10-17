#!/usr/bin/env python3
"""Build an opt-in matched cold START bundle from a verified runtime result."""
from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.pycache_prefix=str(ROOT/'build'/('.absent-cold-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists() or sys.flags.optimize:raise RuntimeError('Source-only unoptimized Python required')
import argparse,hashlib,importlib.util,json,shutil,subprocess,tempfile,zlib

def module(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
common=module(ROOT/'build_support/runtime_media.py','cold_common')
digest=common.digest;verify=common.verify;atomic_json=common.atomic_json
ASSETS=('DOS64.PRG','DOS64.REL','DOS64.MNU','START.TPL','START.REL','START.INO','START.RCV','START.RFW')
OWNER={'kind':'dos64-cold-start','schema':1}

def symbols(p):return {l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
def runtime(result,records):
 result=Path(result).resolve();j=json.loads(result.read_text());records[str(result)]=digest(result)
 if j.get('status')!='passed'or j.get('role')!='runtime'or j.get('schema')!=1:raise RuntimeError('Require passed runtime-media RESULT')
 for section in ['source_inputs','native_products']:
  rows=j.get(section)
  if not isinstance(rows,dict)or not rows:raise RuntimeError('Missing runtime closure '+section)
  verify(rows);records.update(rows)
 required=['DOS64.PRG','DOS64.REL','DOS64.MNU','DOS64.labels','DOS64.map','MODAL_HEADER.bin']
 for name,row in j.get('products',{}).items():
  p=Path(row['path']).resolve();wanted={k:row[k]for k in ['sha256','bytes']}
  if digest(p)!=wanted:raise RuntimeError('Runtime product mismatch: '+name)
  records[str(p)]=wanted
 for name in required:
  row=j['products'][name];p=Path(row['path']).resolve();wanted={k:row[k]for k in ['sha256','bytes']}
  if digest(p)!=wanted:raise RuntimeError('Runtime product mismatch: '+name)
  records[str(p)]=wanted
 for name in ['DOS64.PRG','DOS64.REL','DOS64.MNU']:
  if j['assets'][name]!={k:j['products'][name][k]for k in ['sha256','bytes']}:raise RuntimeError('Runtime asset identity mismatch')
 menu=Path(j['products']['DOS64.MNU']['path']).read_bytes();header=Path(j['products']['MODAL_HEADER.bin']['path']).read_bytes();main=Path(j['products']['DOS64.PRG']['path']).read_bytes()
 if len(menu)!=57344 or len(header)!=64 or menu[:64]!=header or header[:8]!=b'D64M\1\1\x40\0'or main.count(header[8:24])!=1:raise RuntimeError('Runtime/header role binding mismatch')
 if j.get('MNU_REU_spans')!=[[0x3da000,24576],[0x3f0000,32768]]:raise RuntimeError('Unsupported runtime REU layout')
 return j

def stage(run,records):
 inv=ROOT/'build_support/cold_start_sources.json';rows=json.loads(inv.read_text())
 if rows.get('schema')!=1:raise RuntimeError('Unsupported source inventory')
 records[str(inv)]=digest(inv);w=run/'native';w.mkdir();archive=run/'inputs';archive.mkdir()
 for dst,src in rows['sources'].items():
  a=(ROOT/common.safe(src)).resolve();b=w/common.safe(dst)
  if not a.is_relative_to(ROOT):raise RuntimeError('Escaping source')
  b.parent.mkdir(parents=True,exist_ok=True);c=archive/common.safe(src);c.parent.mkdir(parents=True,exist_ok=True);wanted=digest(a)
  shutil.copyfile(a,b);shutil.copyfile(a,c)
  if digest(b)!=wanted or digest(c)!=wanted:raise RuntimeError('Source copy mismatch')
  records[str(a)]=wanted;records[str(c)]=wanted;records[str(b)]=wanted
 for n in ['cold_start.py','runtime_media.py','start_launcher.py','setup_release_descriptor.py','start_template_descriptor.py','start_ini_bundle.py']:
  a=ROOT/'build_support'/n;c=archive/'build_support'/n;c.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,c);records[str(a)]=digest(a);records[str(c)]=digest(c)
 return w

def link(w,t,env,run):
 commands=[]
 def command(argv,cwd):
  argv=list(map(str,argv));commands.append({'argv':argv,'cwd':str(cwd)})
  with(run/'build.stdout').open('ab')as o,(run/'build.stderr').open('ab')as e:subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=o,stderr=e,check=True)
 start=module(ROOT/'build_support/start_launcher.py','cold_launcher');start.command=command
 core=w/'core';gate=w/'gate';worker=w/'worker'
 start.build(core,t,options=True,cold=True)
 L=symbols(core/'controller.labels');prg=(core/'controller.prg').read_bytes();ino=(core/'START.INO').read_bytes()
 prefix=L['_d64_release_validate']-0x6000
 if len(prg)!=20480 or not 161<prefix<=4096 or not 0x6000<=L['_d64_config_validate']<0x6000+prefix:raise RuntimeError('Cold prefix/layout mismatch')
 for n in ['__BSS','__DEVICESTATE']:
  if L[n+'_RUN__']+L[n+'_SIZE__']>0x9000:raise RuntimeError('Resident state overlaps gate')
 (gate/'shared-prefix.bin').write_bytes(ino[:prefix]);(gate/'prefix.h').write_text('#define JG_PREFIX_BYTES %du\n#define JG_PREFIX_CRC 0x%08xUL\n'%(prefix,zlib.crc32(ino[:prefix])));(gate/'prefix.inc').write_text('JG_ENTRY = $%04x\n'%(0x6000+prefix))
 def imports(path,values):
  path.write_text('\n'.join(('.exportzp 'if v<256 else '.export ')+n+'\n'+n+' = $%04x'%v for n,v in values.items()if not n.startswith(('__','@'))and n not in ['_jg_init','_jg_initialized'])+'\n')
 imports(gate/'core_imports.s',L)
 def gate_link():
  command([t['cc65'],'-t','none','-Oirs','--add-source','-D','D64_CONFIG_VALIDATE_ONLY=1','-D','D64_START_OPTIONS=1','-I',core,'journal_gate.c','-o','journal_gate.s'],gate)
  for n in ['entry','journal_gate','core_imports']:command([t['ca65'],'-g','-I','.',n+'.s','-o',n+'.o'],gate)
  command([t['ld65'],'-C','gate.cfg','-o','START.RCV','-Ln','gate.labels','-m','gate.map','entry.o','journal_gate.o','core_imports.o',t['library']],gate)
 gate_link();G=symbols(gate/'gate.labels');asset=(gate/'START.RCV').read_bytes()
 if asset[:2]!=b'\0\x60'or not 0<len(asset)-2<=8192 or G['_jg_dispatch']!=L['_d64_release_validate']or G['_jg_home']!=0x9000:raise RuntimeError('Gate layout mismatch')
 payload=asset[2:];at=L['_sj_gate_spec']-0x801+2
 if prg[at:at+6]!=b'D64G\1\30':raise RuntimeError('Gate DATA capsule absent')
 new=bytearray(prg);new[at:at+24]=b'D64G\1\30'+len(payload).to_bytes(2,'little')+zlib.crc32(payload).to_bytes(4,'little')+b'\0\x60'+G['_jg_dispatch'].to_bytes(2,'little')+b'\0\x90'+bytes(6)
 (core/'controller.prg').write_bytes(new);(core/'START.RCV').write_bytes(payload)
 gate_link()
 if (gate/'START.RCV').read_bytes()!=asset or(core/'START.INO').read_bytes()!=ino:raise RuntimeError('Gate relink changed prefix/asset')
 L['_jg_recovery_copy']=G['_jg_recovery_copy'];imports(worker/'imports.s',L)
 command([t['cc65'],'-t','none','-Oirs','--add-source','-D','D64_START_OPTIONS=1','-I',core,'-I',gate,'rollforward.c','-o','rollforward.s'],worker)
 for n in ['entry','rollforward','imports']:command([t['ca65'],'-g',n+'.s','-o',n+'.o'],worker)
 command([t['ld65'],'-C','worker.cfg','-o','ROLL.PRG','-Ln','worker.labels','-m','worker.map','entry.o','rollforward.o','imports.o',t['library']],worker)
 rf=(worker/'ROLL.PRG').read_bytes();F=symbols(worker/'worker.labels')
 if rf[:2]!=b'\0\xa0'or not 0<len(rf)-2<=8192 or F['__RF_BSS_RUN__']!=0x9800 or F['__RF_BSS_SIZE__']>0x800 or G['__RECOVER_BSS_RUN__']+G['__RECOVER_BSS_SIZE__']>0x9800:raise RuntimeError('Recovery worker layout mismatch')
 at=L['_sr_worker_spec']-0x801+2
 if new[at:at+6]!=b'D64F\1\20':raise RuntimeError('Worker DATA capsule absent')
 new[at:at+16]=b'D64F\1\20'+len(rf[2:]).to_bytes(2,'little')+zlib.crc32(rf[2:]).to_bytes(4,'little')+b'\0\xa0\0\xa0'
 (core/'controller.prg').write_bytes(new);(core/'START.RFW').write_bytes(rf[2:])
 descriptor=module(ROOT/'build_support/start_template_descriptor.py','cold_template');(core/'START.REL').write_bytes(descriptor.make(bytes(new),(core/'controller.labels').read_text(),(core/'controller.map').read_text(),start20k=True))
 atomic_json(run/'COMMANDS.json',commands)
 return {'START_bytes':len(new),'INO_bytes':len(ino),'RCV_bytes':len(payload),'RFW_bytes':len(rf)-2,'shared_prefix':prefix,'gate_home':G['_jg_home'],'gate_bss':G['__RECOVER_BSS_SIZE__'],'worker_bss':F['__RF_BSS_SIZE__']}

def build(out,runtime_result):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 if(out/'OWNER.json').exists():
  if json.loads((out/'OWNER.json').read_text())!=OWNER:raise RuntimeError('Different output owner')
 elif any(out.iterdir()):raise RuntimeError('Use empty or owned output')
 else:atomic_json(out/'OWNER.json',OWNER)
 lock=False;run=None;primary=None;phase='lock';fd=None;records={str(Path(__file__).resolve()):digest(__file__)}
 try:
  fd=os.open(out/'LOCK',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);lock=True;os.close(fd);fd=None
  phase='runtime';r=runtime(runtime_result,records);phase='run';run=Path(tempfile.mkdtemp(prefix='run-',dir=out));phase='stage';w=stage(run,records)
  phase='tools';t=common.tools()
  for n in ['make','cc65','ca65','ld65','library']:records[str(t[n])]=digest(t[n])
  records[str(Path(sys.executable).resolve())]=digest(Path(sys.executable).resolve())
  for folder in ['include','asminc']:
   for p in sorted((t['resources']/folder).rglob('*')):
    if p.is_file():records[str(p.resolve())]=digest(p)
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
  for k in common.SCRUB:env.pop(k,None)
  core=w/'core';menu=Path(r['products']['DOS64.MNU']['path']).read_bytes();header=Path(r['products']['MODAL_HEADER.bin']['path']).read_bytes()
  (core/'modal-header.bin').write_bytes(header);(core/'modal_capsule.s').write_text('.export _sm_modal_spec,_sm_modal_header\n.segment "DATA"\n_sm_modal_spec:\n.byte "D64M",1,16\n.word %d\n.dword %d\n.dword $3da000\n_sm_modal_header:\n.incbin "modal-header.bin"\n'%(len(menu),zlib.crc32(menu)))
  records[str(core/'modal-header.bin')]=digest(core/'modal-header.bin');records[str(core/'modal_capsule.s')]=digest(core/'modal_capsule.s')
  atomic_json(run/'INPUTS_BEFORE.json',records);phase='link';layout=link(w,t,env,run)
  # The runtime descriptor must be independently reproduced, not inferred from a tag.
  rel=module(ROOT/'build_support/setup_release_descriptor.py','cold_release').descriptor(Path(r['products']['DOS64.PRG']['path']).read_bytes(),Path(r['products']['DOS64.labels']['path']).read_text(),options=True)
  if rel!=Path(r['products']['DOS64.REL']['path']).read_bytes():raise RuntimeError('Runtime descriptor does not match linked main')
  verify(records);phase='products';dest=run/'products';dest.mkdir();bundle=run/'bundle';bundle.mkdir();products={}
  source={n:Path(r['products'][n]['path'])for n in ['DOS64.PRG','DOS64.REL','DOS64.MNU','DOS64.labels','DOS64.map']}
  source.update({'START.TPL':core/'controller.prg','START.REL':core/'START.REL','START.INO':core/'START.INO','START.RCV':core/'START.RCV','START.RFW':core/'START.RFW','START.labels':core/'controller.labels','START.map':core/'controller.map'})
  for n,p in source.items():
   d=(bundle if n in ASSETS else dest)/n;shutil.copyfile(p,d)
   if digest(d)!=digest(p):raise RuntimeError('Product copy mismatch')
   products[n]={'path':str(d),**digest(d)};d.chmod(0o444)
  validator=module(ROOT/'build_support/start_ini_bundle.py','cold_bundle_validator')
  mods={'template':module(ROOT/'build_support/start_template_descriptor.py','cold_checked_template'),'release':module(ROOT/'build_support/setup_release_descriptor.py','cold_checked_release')}
  memory=validator.validate_bundle(bundle,dest/'START.labels',dest/'START.map',dest/'DOS64.labels',mods=mods,start20k=True,cold_inventory=True,mnu56k=True)
  native={str(p):digest(p)for p in w.rglob('*')if p.is_file()};verify(records);verify(native)
  atomic_json(run/'INPUTS_AFTER.json',records);atomic_json(run/'PRODUCTS.json',native)
  result={'schema':1,'status':'passed','scope':'SOURCE_BUILT_COLD_EIGHT_ASSET_BUNDLE_NO_HARDWARE_ACCEPTANCE','run':str(run),'work':str(w),'bundle':str(bundle),'runtime_result':str(Path(runtime_result).resolve()),'runtime_result_identity':digest(runtime_result),'products':products,'assets':{n:{k:products[n][k]for k in ['sha256','bytes']}for n in ASSETS},'source_inputs':records,'native_products':native,'layout':layout,'memory':memory,'physical':False}
  atomic_json(run/'RESULT.json',result);phase='unlock';(out/'LOCK').unlink();lock=False;phase='publication';atomic_json(out/'RESULT.json',result);return result
 except BaseException as ex:
  primary=ex;failure={'status':'failed','phase':phase,'error':type(ex).__name__+': '+str(ex),'prior_result_preserved':True}
  for p in ([run/'FAILURE.json']if run else [])+[out/'LAST_FAILURE.json']:
   try:atomic_json(p,failure)
   except BaseException:pass
  raise
 finally:
  if fd is not None:
   try:os.close(fd)
   except BaseException:
    if primary is None:raise
  if lock:
   try:(out/'LOCK').unlink()
   except BaseException:
    if primary is None:raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-result',type=Path,required=True);p.add_argument('--out',type=Path,default=ROOT/'build/cold-start');a=p.parse_args();print(build(a.out,a.runtime_result)['run'])
if __name__=='__main__':main()
