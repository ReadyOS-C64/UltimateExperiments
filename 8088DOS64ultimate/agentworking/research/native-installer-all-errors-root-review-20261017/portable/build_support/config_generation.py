#!/usr/bin/env python3
"""Build the release-bound standalone CONFIG application from public sources."""
from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-config-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache prefix must be absent')
import argparse,hashlib,importlib.util,json,shutil,subprocess,tempfile,zlib,platform
ASSETS=['DOS64.PRG','DOS64.REL','START.INO','START.TPL','START.REL']
CS=['bulk_context','platform','install_config','existing_cfg','directory_browser','lease_context','config_ui','media_reinspect','config_publish','release_patch']
ASM=['bootstrap_diag','core_fixture','bindings','context_bindings','startup_glue','uci','files','platform','startup_close','crc32','media_dma','high_bootstrap','coordinator','file_error']
def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def verify(record):
 for name,w in record.items():
  if digest(Path(name))!=w:raise RuntimeError('Source/product changed: '+name)
def atomic_json(p,value):
 pending=p.with_name(p.name+'.tmp-'+str(os.getpid()));pending.write_text(json.dumps(value,indent=2)+'\n');os.replace(pending,p)
def module(name,path,record):
 record[str(path)]=digest(path);s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def copy(source,destination,record):
 w=digest(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
 if digest(source)!=w or digest(destination)!=w:raise RuntimeError('Copy changed: '+str(source))
 record[str(source)]=w;record[str(destination)]=w

def tool(name,env=None):
 chosen=os.environ.get(env or 'DOS64_'+name.upper(),name);found=shutil.which(chosen)
 if not found:raise RuntimeError('Set '+(env or 'DOS64_'+name.upper())+' to '+name)
 return Path(found).resolve()
def command_environment():
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
 for name in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(name,None)
 return env

def tools(test):
 t={n:tool(n)for n in ['cc65','ca65','ld65']}
 supplied=os.environ.get('DOS64_CC65_LIB');candidates=[Path(supplied).expanduser().resolve()]if supplied else[t['cc65'].parent.parent/'share/cc65/lib/none.lib',Path('/opt/homebrew/share/cc65/lib/none.lib'),Path('/usr/share/cc65/lib/none.lib')]
 t['library']=next((p.resolve()for p in candidates if p.is_file()),None)
 if t['library']is None:raise RuntimeError('Set DOS64_CC65_LIB to none.lib')
 if test:
  if 'DOS64_CLANGXX'in os.environ:t['clang++']=tool('clang++','DOS64_CLANGXX')
  else:t['clang++']=tool('clang++')
  t['zig']=tool('zig')
 return t

def release_metadata_paths(j):
 """Accept checked named products or the recorded older bundle layout."""
 run=Path(j['run']).resolve();products=j.get('products',{});paths=[]
 for name,legacy in [('START.labels','start/controller.labels'),('START.map','start/controller.map'),('DOS64.labels','main/build/dos64.labels')]:
  if name in products:
   row=products[name];p=Path(row['path']).resolve();wanted={k:row[k]for k in ['sha256','bytes']}
  else:
   p=(run/legacy).resolve();wanted=products.get(str(p),j.get('source_inputs',{}).get(str(p)))
  if not p.is_relative_to(run) or wanted is None or digest(p)!=wanted:
   raise RuntimeError('Unbound coupled release metadata: '+name)
  paths.append(p)
 return paths

def release_records(j):
 """Check every declared provider input/product, including unused products."""
 rows={}
 for section in ['source_inputs','native_products']:
  declared=j.get(section,{})
  verify(declared)
  for p,wanted in declared.items():
   if p in rows and rows[p]!=wanted:raise RuntimeError('Conflicting coupled input: '+p)
   rows[p]=wanted
 for name,row in j.get('products',{}).items():
  p=Path(row['path']).resolve()if 'path'in row else Path(name).resolve()
  wanted={k:row[k]for k in ['sha256','bytes']}
  if digest(p)!=wanted:raise RuntimeError('Coupled release product changed: '+name)
  if str(p)in rows and rows[str(p)]!=wanted:raise RuntimeError('Conflicting coupled product: '+name)
  rows[str(p)]=wanted
 return rows

def bind_release(result_path,work,record,*,start20k=False,cold_inventory=False,mnu56k=False):
 copy(result_path,work/'release-RESULT.json',record);j=json.loads((work/'release-RESULT.json').read_text())
 if j.get('status')!='passed':raise RuntimeError('Coupled release RESULT must be passed')
 for p,wanted in release_records(j).items():
  if p in record and record[p]!=wanted:raise RuntimeError('Mixed coupled source generations: '+p)
  record[p]=wanted
 bundle=Path(j['bundle']).resolve();run=Path(j['run']).resolve()
 if not bundle.is_relative_to(run):raise RuntimeError('Bundle outside its immutable run')
 selected=ASSETS+['DOS64.MNU','START.RCV','START.RFW']if cold_inventory else ASSETS
 if {p.name for p in bundle.iterdir()}!=set(selected):raise RuntimeError('Coupled release requires exactly five asset files')
 mods={n:module('config_'+n,ROOT/'build_support'/f,record)for n,f in [('bundle','start_ini_bundle.py'),('template','start_template_descriptor.py'),('release','setup_release_descriptor.py'),('start','start_launcher.py')]}
 paths=release_metadata_paths(j)
 staged_paths=[]
 for p,name in zip(paths,['START.labels','START.map','DOS64.labels']):
  if not p.is_file():raise RuntimeError('Missing coupled release labels/map: '+str(p))
  destination=work/'release-metadata'/name;copy(p,destination,record);staged_paths.append(destination)
 data={}
 for n in selected:
  p=bundle/n
  if digest(p)!=j['assets'][n]:raise RuntimeError('Release asset differs from RESULT: '+n)
  copy(p,work/'release-assets'/n,record);data[n]=(work/'release-assets'/n).read_bytes()
 view=mods['bundle'].validate_bundle(work/'release-assets',*staged_paths,mods=mods,start20k=start20k,cold_inventory=cold_inventory,mnu56k=mnu56k)
 s=data['START.REL'];t=data['START.TPL'];control=int.from_bytes(s[24:28],'little')
 if len(t)!=(20480 if start20k else 18432) or control>len(t)-131:raise RuntimeError('Unsupported CONFIG template size/control')
 header='#ifndef CP_RELEASE_ASSETS_H\n#define CP_RELEASE_ASSETS_H\n#define RP_TEMPLATE_CRC '+str(zlib.crc32(t))+'UL\n#define RP_CONTROL '+str(control)+'u\n#define RP_TEMPLATE_BYTES '+str(len(t))+'u\n#ifndef RP_CONSTANTS_ONLY\n'
 header+='static const br_u32 asset_size['+str(len(selected))+']={'+','.join(str(len(data[n]))+'UL'for n in selected)+'};\n'
 header+='static const br_u32 asset_crc['+str(len(selected))+']={'+','.join(str(zlib.crc32(data[n]))+'UL'for n in selected)+'};\n'
 header+='static const br_u32 asset_reu['+str(len(selected))+']={0x2a0000UL,0x2be000UL,0x2b0000UL,0x2b2000UL,0x2be040UL'+((',0x080000UL,0x08e000UL,0x090000UL'if mnu56k else',0x080000UL,0x08a000UL,0x08c000UL')if cold_inventory else'')+'};\n'
 for label,n in [('expected_d64l','DOS64.REL'),('expected_d64s','START.REL')]:header+='static const br_u8 '+label+'[64]={'+','.join(str(v)for v in data[n])+'};\n'
 header+='static const char *const asset_name['+str(len(selected))+']={'+','.join('"'+n+'"'for n in selected)+'};\n#endif\n#endif\n'
 if cold_inventory:
  cold='#ifndef DOS64_COLD_ASSETS_H\n#define DOS64_COLD_ASSETS_H\n'
  for prefix,name in [('MNU','DOS64.MNU'),('RCV','START.RCV'),('RFW','START.RFW')]:cold+='#define CI_'+prefix+'_BYTES '+str(len(data[name]))+'UL\n#define CI_'+prefix+'_CRC '+str(zlib.crc32(data[name]))+'UL\n'
  cold+='#endif\n';(work/'cold_assets.h').write_text(cold);record[str(work/'cold_assets.h')]=digest(work/'cold_assets.h')
  inc=''
  for prefix,name in [('MNU','DOS64.MNU'),('RCV','START.RCV'),('RFW','START.RFW')]:inc+='CI_'+prefix+'_BYTES='+str(len(data[name]))+'\nCI_'+prefix+'_CRC='+str(zlib.crc32(data[name]))+'\n'
  (work/'cold_assets.inc').write_text(inc);record[str(work/'cold_assets.inc')]=digest(work/'cold_assets.inc')
 path=work/'release_assets.h';path.write_text(header);record[str(path)]=digest(path)
 return {'result':str(result_path),'result_identity':digest(work/'release-RESULT.json'),'archived_result':str(work/'release-RESULT.json'),'assets':{n:digest(work/'release-assets'/n)for n in selected},'binding':view}

def sources(work,record,test):
 path=ROOT/'build_support/config_sources.json';record[str(path)]=digest(path);selected=json.loads(path.read_text())
 for dest,source in selected.items():
  if dest=='release_assets.h':continue
  if Path(dest).name!=dest:raise RuntimeError('Invalid stage destination')
  q=(ROOT/source).resolve()
  if not q.is_relative_to(ROOT):raise RuntimeError('Source outside public project')
  copy(q,work/dest,record)
 if test:
  for p in (ROOT/'tests/config').glob('*'):
   if p.is_file()and p.suffix in{'.py','.zig','.cfg'}:copy(p,work/p.name,record)
  support=ROOT/'tests/config/support'
  for p in support.rglob('*'):
   if p.is_file():copy(p,work/p.relative_to(support),record)
  for p in (ROOT/'third_party/peddle/Peddle').rglob('*'):
   if p.is_file()and p.suffix in{'.h','.cpp','.hpp','.inc'}:copy(p,work/p.relative_to(ROOT),record)

def native(work,t,run_command,*,cold_inventory=False,mnu56k=False,startup_diagnostics=False,all_file_diagnostics=False):
 o=work/'objects';o.mkdir()
 for n in CS:
  opts=['--code-name','RI_CODE','--rodata-name','RI_RO','--bss-name','RIBSS']if n in ['install_config','existing_cfg']else(['--bss-name','RIBSS']if n in ['directory_browser','lease_context']else[])
  if n=='media_reinspect':opts=['--code-name','RM_CODE','--rodata-name','RM_RO','--bss-name','RIBSS']
  if n in ['existing_cfg','config_ui']:opts+=['-D','DOS64_CONFIG_ATTACHED=1']
  if cold_inventory:opts+=['-D','DOS64_SETUP_COLD_INVENTORY=1']
  if mnu56k:opts+=['-D','DOS64_SETUP_MNU_56K=1']
  if all_file_diagnostics:opts+=['-D','DOS64_ALL_FILE_DIAGNOSTICS=1']
  if n=='install_config':opts+=['-D','D64_CONFIG_VALIDATE_ONLY=1']
  run_command([t['cc65'],'-t','none','-O',*opts,n+'.c','-o',o/(n+'_c.s')])
  run_command([t['ca65'],'-g','-D','DOS64_FILES_INFO=1','-I','.',o/(n+'_c.s'),'-o',o/(n+'_c.o')])
 for n in ASM:run_command([t['ca65'],'-g','-D','DOS64_FILES_INFO=1',*(['-D','DOS64_ALL_FILE_DIAGNOSTICS=1']if all_file_diagnostics else[]),*(['-D','DOS64_BOOT_DIAGNOSTICS=1']if startup_diagnostics else[]),'-I','.',n+'.s','-o',o/(n+'.o')])
 run_command([t['ld65'],'-C','all-file-diagnostics.cfg'if all_file_diagnostics else'publisher-diagnostics.cfg'if startup_diagnostics else'publisher.cfg','-o','config.prg','-Ln','config.labels','-m','config.map',*[o/(n+'.o')for n in ASM+[n+'_c'for n in CS]],t['library']])
 labels={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(work/'config.labels').read_text().splitlines()if x.startswith('al ')}
 phase_end=labels['__RM_RO_RUN__']+labels['__RM_RO_SIZE__'];phase_state=labels['__RIBSS_RUN__'];phase_state_end=labels['__RMBSS_RUN__']+labels['__RMBSS_SIZE__'];state_end=labels['__CONFIG_PUBSTATE_RUN__']+labels['__CONFIG_PUBSTATE_SIZE__']
 if phase_end>phase_state or phase_state<0x8700 or phase_state_end>0xb000 or labels['__RMBSS_RUN__']!=phase_state+labels['__RIBSS_SIZE__'] or state_end>0xc000:raise RuntimeError('CONFIG code/state overlap or state bounds')
 b=bytearray((work/'config.prg').read_bytes());base=int.from_bytes(b[:2],'little');load=labels['__CONFIG_HIGH_LOAD__'];address=labels['__CONFIG_HIGH_RUN__'];count=labels['__CONFIG_HIGH_TOTAL__'];field=labels['_cp_high_expected']
 if base!=0x0801 or load!=0x9000 or address!=0xe000 or not 0<count<=0x1ffa or load+count>0xb000 or address+count>0xfffa or not 0x0801<=field<=0x5ffc:raise RuntimeError('HIGH lifetime/layout bounds')
 at=load-base+2;source=bytes(b[at:at+count]);off=field-base+2
 if len(source)!=count or b[off:off+4]!=bytes.fromhex('12345678'):raise RuntimeError('HIGH binding field/source mismatch')
 if startup_diagnostics:
  diag=labels['__BOOT_DIAG_RUN__'];n=labels['__BOOT_DIAG_SIZE__']
  if labels['__BOOT_DIAG_LOAD__']!=diag or diag!=0xb000 or labels['__BSS_RUN__']!=diag or not 0<n<=256 or len(b)!=(labels['__FD_CODE_LOAD__']-base+2+labels['__FD_CODE_SIZE__']+labels['__FD_SAFE_SIZE__']if all_file_diagnostics else diag-base+2+n):raise RuntimeError('Trusted CONFIG cold strip extent/lifetime mismatch')
 if all_file_diagnostics:
  fd_at=labels['__FD_CODE_LOAD__']-base+2;fd_n=labels['__FD_CODE_SIZE__'];fd_off=labels['_fd_expected']-address+load-base+2
  if state_end>0xbfc8 or labels['__FD_SAFE_RUN__']!=0xbfc8 or not 0<labels['__FD_SAFE_SIZE__']<=56 or labels['__FD_SAFE_LOAD__']!=labels['__FD_CODE_LOAD__']+labels['__FD_CODE_SIZE__']:raise RuntimeError('Permanent CONFIG fallback lifetime/bounds')
  entry=labels['config_entry'];entry_at=entry-base+2
  if b[0x080d-base+2:0x080d-base+5]!=b'\x4c'+entry.to_bytes(2,'little') or b[entry_at:entry_at+2]!=b'\x78\xd8':raise RuntimeError('CONFIG SYS must enter trusted guard before diagnostics')
  if not 0<fd_n<=4096 or labels['__FD_CODE_RUN__']!=0x6000 or labels['__FD_STASH_LOAD__']!=0xb100 or b[fd_off:fd_off+4]!=bytes.fromhex('12345678'):raise RuntimeError('Terminal phase bounds/binding')
  b[fd_off:fd_off+4]=(zlib.crc32(b[fd_at:fd_at+fd_n])^0xffffffff).to_bytes(4,'little')
  source=bytes(b[at:at+count]) # HIGH includes the externally bound diagnostic CRC.
 crc=zlib.crc32(source);b[off:off+4]=crc.to_bytes(4,'little');(work/'config.prg').write_bytes(b)
 return {'HIGH_source':load,'HIGH_run':address,'HIGH_bytes':count,'HIGH_crc':crc,'HIGH_source_sha256':hashlib.sha256(source).hexdigest(),'expected_field':field,'entry':0x080d,'vectors_excluded':True,'initial_SOURCE_before_phase_zero':True,'trusted_boot_diagnostics':startup_diagnostics,'diagnostic_cold_strip':{'run':labels['__BOOT_DIAG_RUN__'],'bytes':labels['__BOOT_DIAG_SIZE__'],'retired_by_zerobss':True}if startup_diagnostics else None,'phase_code_end_exclusive':phase_end,'phase_state_start':phase_state,'phase_state_end_exclusive':phase_state_end,'permanent_state_end_exclusive':state_end}

def build(out,result_path,test,media,*,start20k=False,cold_inventory=False,mnu56k=False,startup_diagnostics=False,all_file_diagnostics=False):
 out=out.resolve();out.mkdir(parents=True,exist_ok=True);owner=out/'OWNER.json'
 if owner.exists():
  if json.loads(owner.read_text())!={'kind':'dos64-config-build','version':1}:raise RuntimeError('Output directory has another owner')
 elif any(out.iterdir()):raise RuntimeError('Use an empty or CONFIG-owned output directory')
 else:atomic_json(owner,{'kind':'dos64-config-build','version':1})
 lock=out/'LOCK';fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 run=None;record={str(Path(__file__).resolve()):digest(Path(__file__).resolve())};commands=[];stage='lock'
 try:
  os.write(fd,str(os.getpid()).encode());os.close(fd);fd=None;stage='run'
  run=Path(tempfile.mkdtemp(prefix='run-',dir=out));work=run/'work';work.mkdir();evidence=run/'evidence';evidence.mkdir();stage='tools';t=tools(test)
  for p in list(t.values())+[Path(sys.executable).resolve()]:record[str(p)]=digest(p)
  # Compiler distribution headers/macros are native source inputs too.
  resources=t['cc65'].parent.parent/'share/cc65'
  for folder in ['include','asminc']:
   for p in (resources/folder).rglob('*'):
    if p.is_file():record[str(p)]=digest(p)
  stage='sources';sources(work,record,test);stage='release';binding=bind_release(result_path.resolve(),work,record,start20k=start20k,cold_inventory=cold_inventory,mnu56k=mnu56k)
  if media:
   if not test:raise RuntimeError('Media arguments are test-only')
   for name,p in zip(['A.IMG','B.IMG','C.IMG'],media):copy(p.resolve(),work/'media-inputs'/name,record)
  atomic_json(evidence/'INPUTS_BEFORE.json',record)
  def command(argv):
   args=[str(x)for x in argv];commands.append(args)
   with(evidence/'commands.stdout').open('ab')as o,(evidence/'commands.stderr').open('ab')as e:subprocess.run(args,cwd=work,stdin=subprocess.DEVNULL,stdout=o,stderr=e,check=True,env=command_environment())
  stage='native';memory=native(work,t,command,cold_inventory=cold_inventory,mnu56k=mnu56k,startup_diagnostics=startup_diagnostics,all_file_diagnostics=all_file_diagnostics);products={str(work/n):digest(work/n)for n in ['config.prg','config.labels','config.map']};atomic_json(evidence/'PRODUCTS_BEFORE.json',products)
  groups={}
  if test:
   stage='models';flags=['-dynamiclib']if platform.system()=='Darwin'else['-shared','-fPIC']
   command([t['clang++'],'-std=c++20','-O2',*flags,'-Ithird_party/peddle/Peddle','-Itests/host','-Itests/floppy_export','tests/floppy_export/bridge.cpp',*[Path('third_party/peddle/Peddle')/n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','config-peddle.dylib'])
   products[str(work/'config-peddle.dylib')]=digest(work/'config-peddle.dylib');atomic_json(evidence/'PRODUCTS_BEFORE.json',products)
   stage='actual-sys';command([sys.executable,'-B','test_sys.py'])
   report=json.loads((run/'SYS_TEST_REPORT.json').read_text())
   if report.get('tests_run')!=4 or report.get('successful')is not True:raise RuntimeError('Expected exactly4 passing actual SYS groups')
   stage='actual-zig';command([t['zig'],'build','--build-file','build-config.zig','compile']);command([work/'zig-out/bin/config-tests'])
   if 'All 2 tests passed.'not in(evidence/'commands.stderr').read_text():raise RuntimeError('Expected exactly2 directly executed Zig groups')
   groups={'actual_SYS':4,'direct_Zig':2,'synthetic_media':not bool(media),'genuine_DOS_execution':False}
  stage='closure';verify(record);verify(products);atomic_json(evidence/'INPUTS_AFTER.json',record);atomic_json(evidence/'PRODUCTS_AFTER.json',products)
  stage='publication';published={};product_dir=run/'products';product_dir.mkdir()
  for name,source in [('CONFIG.PRG','config.prg'),('CONFIG.labels','config.labels'),('CONFIG.map','config.map')]:
   destination=product_dir/name;shutil.copyfile(work/source,destination)
   if digest(destination)!=products[str(work/source)]:raise RuntimeError('Publish copy mismatch')
   published[name]={'path':str(destination),**digest(destination)}
  result={'status':'passed','scope':'SOURCE_ONLY_CONFIG_DEVELOPMENT_BUILD_NO_HARDWARE_ACCEPTANCE','run':str(run),'products':published,'native_products':products,'source_inputs':record,'release':binding,'memory':memory,'groups':groups,'commands':commands,'source_only':True,'physical_acceptance':False}
  atomic_json(run/'RESULT.json',result);atomic_json(out/'RESULT.json',result);return result
 except BaseException as ex:
  failure={'status':'failed','run':str(run)if run else None,'stage':stage,'error':str(ex),'exception':type(ex).__name__,'source_inputs':record,'commands':commands}
  # Reporting is bounded and secondary. Never replace the exact first object.
  reports=([run/'FAILURE.json']if run is not None else[])+[out/'LAST_FAILURE.json']
  for path in reports:
   try:atomic_json(path,failure)
   except BaseException as secondary:
    failure.setdefault('diagnostic_errors',[]).append({'exception':type(secondary).__name__,'error':str(secondary)})
  raise
 finally:
  active=sys.exc_info()[0]is not None;cleanup=None
  if fd is not None:
   try:os.close(fd)
   except BaseException as ex:
    if not active:cleanup=ex
  try:lock.unlink(missing_ok=True)
  except BaseException as ex:
   if not active and cleanup is None:cleanup=ex
  if cleanup is not None:raise cleanup

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'build/config');parser.add_argument('--bundle-result',type=Path,default=ROOT/'build/start-ini-bundle/RESULT.json');parser.add_argument('--test',action='store_true');parser.add_argument('--start20k',action='store_true');parser.add_argument('--cold-inventory',action='store_true');parser.add_argument('--mnu56k',action='store_true');parser.add_argument('--startup-diagnostics',action='store_true');parser.add_argument('--all-file-diagnostics',action='store_true');parser.add_argument('--media-a',type=Path);parser.add_argument('--media-b',type=Path);parser.add_argument('--media-c',type=Path);args=parser.parse_args()
 if args.all_file_diagnostics and not args.startup_diagnostics:parser.error('--all-file-diagnostics requires --startup-diagnostics')
 if args.mnu56k and not args.cold_inventory:parser.error('--mnu56k requires --cold-inventory')
 if args.cold_inventory and not args.start20k:parser.error('--cold-inventory requires --start20k')
 media=[args.media_a,args.media_b,args.media_c]
 if any(media)and not all(media):parser.error('Supply all three local test media paths')
 if any(media)and not args.test:parser.error('Media paths require --test')
 result=args.bundle_result.resolve()
 if not result.is_file():
  if args.bundle_result!=ROOT/'build/start-ini-bundle/RESULT.json':raise RuntimeError('Explicit coupled RESULT is missing')
  subprocess.run([sys.executable,'-B',str(ROOT/'build_support/start_ini_bundle.py')],cwd=ROOT,check=True)
 report=build(args.out,result,args.test,media if all(media)else None,start20k=args.start20k,cold_inventory=args.cold_inventory,mnu56k=args.mnu56k,startup_diagnostics=args.startup_diagnostics,all_file_diagnostics=args.all_file_diagnostics);print(json.dumps({'status':report['status'],'run':report['run'],'products':report['products'],'groups':report['groups']},indent=2))
if __name__=='__main__':main()
