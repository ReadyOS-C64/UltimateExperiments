"""Content-aware cache capsule transaction and exact D81 publication check."""
from pathlib import Path
import argparse,ast,binascii,hashlib,importlib.util,json,os,re,struct,subprocess,sys,tempfile
TAGS=('fold','sema','inln','page','line')
ARTIFACTS=tuple(n+s for n in TAGS for s in ('.seo','.bin','.lbl','.map'))+('budget.json','editor-api.inc','state.s')
SCHEMA=2
LEXICAL=('edit','tail','lex','ical','ctrl')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encoded(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def write_changed(p,data):
 if p.exists()and p.read_bytes()==data:return False
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+'.tmp');tmp.write_bytes(data);os.replace(tmp,p);return True

def closure(project):
 """Conservative production cache inputs plus actual textual include closure.

 Unused direct siblings can trigger a rebuild; private nested probe namespaces
 do not. Generated editor-api/state inputs are covered by the complete resident.
 """
 paths={project/'src/cache/editor/build.py',project/'src/supermark/block.s',project/'src/supermark/inline.s',project/'src/supermark/api.inc'}
 folders=['editor','arena','query','semantic','inline']
 if (project/'src/cache/lexical/build.py').exists():
  folders.append('lexical');paths.add(project/'src/supermark/lexer.s')
 for folder in folders:
  paths.update(p for p in (project/'src/cache'/folder).glob('*')if p.is_file()and p.suffix in('.s','.inc','.py'))
 paths.update(project/'tools'/n for n in('module_bindings.py','bindings.py','overlays.py'))
 pending=list(paths)
 while pending:
  p=pending.pop()
  for kind,name in re.findall(r'^\s*\.(include|incbin)\s+"([^"]+)"',p.read_text(),re.M|re.I):
   if name=='editor-api.inc':continue
   found=next((x.resolve()for x in(p.parent/name,project/'src'/name)if x.is_file()),None)
   if found is None:raise ValueError(f'unresolved {kind} {name} in {p}')
   if found not in paths:paths.add(found);pending.append(found)if kind.lower()=='include'else None
 return sorted(paths)

def identity(project,base):
 sys.path.insert(0,str(project/'tools'))
 from bindings import verify,link_symbols
 seal=verify(base/'build/editor.prg',base/'build/editor.lbl')
 report=json.loads((base/'build/editor-report.json').read_text())
 pairs=set(link_symbols(base/'build/editor.lbl'))
 if any((n,v)not in pairs for n,v in report['symbols'].items()):raise ValueError('report/label symbol mismatch')
 if seal['digest']!=report['resident_binding']['digest']or seal['resident_sha256']!=report['sha256']:raise ValueError('report/PRG/labels mismatch')
 files=closure(project)
 record=dict(schema=SCHEMA,resident={n:sha(base/'build'/n)for n in('editor.prg','editor.lbl','editor-report.json')},binding=seal['digest'],api=[report['symbols'][n]for n in('se_overlay_call','se_overlay_frame')],source={str(p.relative_to(project)):sha(p)for p in files},guard_sha256=sha(Path(__file__)),toolchain={n:subprocess.check_output([n,'-V'],stderr=subprocess.STDOUT,text=True).strip()for n in('ca65','ld65','od65')})
 return record

def families(out,lexical_out):
 result=[dict(name='base',out=out,builder='src/cache/editor/build.py',tags=TAGS,slots=(0,1,1,1,1),ids=(33,34,35,37,39),artifacts=ARTIFACTS,require_resident_sha=True)]
 if lexical_out is not None:
  artifacts=tuple(n+s for n in LEXICAL for s in('.seo','.bin','.lbl','.map'))+('budget.json','editor-api.inc')
  result.append(dict(name='lexical',out=lexical_out,builder='src/cache/lexical/build.py',tags=LEXICAL,slots=(1,0,0,1,1),ids=(45,36,37,47,49),artifacts=artifacts,require_resident_sha=False))
 return result

def validate(profile,record):
 out=profile['out'];d=bytes.fromhex(record['binding']);budget=json.loads((out/'budget.json').read_text())
 if budget['binding']!=record['binding']:raise ValueError('budget seal mismatch')
 if profile['require_resident_sha']and budget['resident_sha256']!=record['resident']['editor.prg']:raise ValueError('budget resident SHA mismatch')
 for tag,slot,ident in zip(profile['tags'],profile['slots'],profile['ids']):
  image=(out/(tag+'.seo')).read_bytes();raw=(out/(tag+'.bin')).read_bytes()
  if len(image)<53 or image[:5]!=b'SEO2\x02'or image[5:8]!=bytes([slot,ident,0])or image[16:20]!=struct.pack('<HH',*record['api'])or image[20:36]!=d or raw[:16]!=d or image[36:]!=raw:raise ValueError('bad sealed cache image '+tag)
  if not 16<len(raw)<=4096 or int.from_bytes(image[10:12],'little')!=16 or int.from_bytes(image[8:10],'little')!=len(raw)or binascii.crc_hqx(raw,65535)!=int.from_bytes(image[12:14],'little'):raise ValueError('payload CRC/length '+tag)
  if binascii.crc_hqx(image[:14]+image[16:36],65535)!=int.from_bytes(image[14:16],'little'):raise ValueError('header CRC '+tag)
  item=budget['images'][tag]
  if item['bytes']!=len(raw):raise ValueError('budget size mismatch '+tag)
  if 'slot'in item and item['slot']!=slot or 'id'in item and item['id']!=ident:raise ValueError('budget identity mismatch '+tag)
  if 'sha256'in item and item['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('budget raw SHA mismatch '+tag)
 return {profile['name']+'/'+n:sha(out/n)for n in profile['artifacts']}

def ensure(project,base,out,publish=None,lexical_out=None):
 project=project.resolve();base=base.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=True)
 lexical_out=lexical_out.resolve()if lexical_out is not None else None
 names=set(editor_names(project));new=set(LEXICAL)
 if names&new and (not new<=names or lexical_out is None):raise ValueError('registered lexical family requires all five names and --lexical-out')
 if lexical_out is not None and not (project/'src/cache/lexical/build.py').is_file():raise ValueError('missing lexical builder')
 profiles=families(out,lexical_out);lock=out/'.ensure.lock'
 try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 except FileExistsError:raise RuntimeError('cache job check already running; stale locks require explicit review')
 os.close(fd)
 try:
  before=identity(project,base);before['profiles']=[{k:p[k]for k in('name','builder','tags','slots','ids','artifacts','require_resident_sha')}for p in profiles]
  # JSON primitive representation must be identical after a stored round trip.
  before=json.loads(encoded(before));signature=hashlib.sha256(encoded(before)).hexdigest();manifest=out/'content.json';reason='missing manifest'
  def current_identity():
   value=identity(project,base);value['profiles']=before['profiles'];return value
  if manifest.exists():
   try:
    old=json.loads(manifest.read_text());artifacts={k:v for p in profiles for k,v in validate(p,before).items()}
    if old['signature']==signature and old['artifacts']==artifacts:reason=None
    else:reason='content or artifact changed'
   except (ValueError,KeyError,OSError,json.JSONDecodeError):reason='missing or invalid artifact'
  rebuilt=reason is not None
  if rebuilt:
   with tempfile.TemporaryDirectory(prefix='cache-jobs-',dir=out.parent)as temporary:
    fresh=[]
    for p in profiles:
     target=dict(p,out=Path(temporary)/p['name']);fresh.append(target)
     subprocess.run([sys.executable,project/p['builder'],target['out'],base],cwd=project,check=True,stdout=subprocess.DEVNULL)
    if current_identity()!=before:raise RuntimeError('cache inputs changed while building')
    artifacts={k:v for p in fresh for k,v in validate(p,before).items()}
    manifest.unlink(missing_ok=True)
    for source,target in zip(fresh,profiles):
     for name in target['artifacts']:write_changed(target['out']/name,(source['out']/name).read_bytes())
    write_changed(manifest,json.dumps(dict(signature=signature,inputs=before,artifacts=artifacts),indent=2,sort_keys=True).encode()+b'\n')
  if current_identity()!=before:raise RuntimeError('cache inputs changed during validation/publication')
  stamps={p['name']:write_changed(p['out']/'jobs.stamp',(signature+'\n').encode())for p in profiles}
  copied=[]
  if publish is not None:
   for p in profiles:
    for tag in p['tags']:
     name=tag+'.seo'
     if write_changed(publish/name,(p['out']/name).read_bytes()):copied.append(name)
  return dict(rebuilt=rebuilt,reason=reason,binding=before['binding'],signature=signature,published=copied,stamps_changed=stamps,input_files=len(before['source']),families=[p['name']for p in profiles],capsules=sum(len(p['tags'])for p in profiles))
 finally:lock.unlink()

def editor_names(project):
 names=[]
 for node in ast.parse((project/'tools/cpu_editor.py').read_text()).body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='NAMES'for t in node.targets):names=list(ast.literal_eval(node.value))
  if isinstance(node,ast.AugAssign)and isinstance(node.target,ast.Name)and node.target.id=='NAMES':
   if not isinstance(node.op,ast.Add):raise ValueError('unsupported catalog declaration')
   names+=ast.literal_eval(node.value)
 if not names or len(names)!=len(set(names)):raise ValueError('missing/duplicate editor catalog')
 return names

def all_editor_capsules(project,record):
 digest=bytes.fromhex(record['binding']);result={}
 for name in editor_names(project):
  p=project/'build/overlays'/(name+'.seo');data=p.read_bytes()
  if len(data)<53 or data[:5]!=b'SEO2\x02'or data[20:36]!=digest or data[36:52]!=digest:raise ValueError('foreign/invalid editor capsule '+name)
  if data[16:20]!=struct.pack('<HH',*record['api']):raise ValueError('foreign editor API '+name)
  if int.from_bytes(data[8:10],'little')!=len(data)-36 or binascii.crc_hqx(data[36:],65535)!=int.from_bytes(data[12:14],'little')or binascii.crc_hqx(data[:14]+data[16:36],65535)!=int.from_bytes(data[14:16],'little'):raise ValueError('editor capsule CRC '+name)
  result[name]=sha(p)
 return result

def package_inputs(project):
 manifest=json.loads((project/'build/disk-manifest.json').read_text());command=manifest['command'];members=[]
 for i,item in enumerate(command):
  if item!='-write':continue
  p=Path(command[i+1]).resolve()
  if not p.is_relative_to(project/'build'):raise ValueError('foreign packaging input path')
  members.append([str(p.relative_to(project)),command[i+2]])
 if not members or len(members)!=len(set(n for _,n in members)):raise ValueError('missing/duplicate packaging member')
 deps=['tools/package.py','tools/overlays.py','tools/bindings.py','tools/d81_image.py','tools/cpu_editor.py','build/editor-report.json','build/editor.lbl','build/overlay-probe-report.json']
 files={name:sha(project/name)for name in sorted(set(deps+[p for p,_ in members]))}
 return dict(members=members,files=files,guard_sha256=sha(Path(__file__)))

def ensure_disk(project,c1541='c1541'):
 """Always checked by a forced D81 recipe; clock equality grants no authority."""
 project=project.resolve();disk=project/'build/supereditor.d81';manifest=project/'build/disk-manifest.json';proof=project/'build/disk-content.json';lock=project/'build/.disk-content.lock'
 try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 except FileExistsError:raise RuntimeError('packaging check already running')
 os.close(fd)
 try:
  record=identity(project,project);capsules=all_editor_capsules(project,record)
  before=None
  try:before=package_inputs(project)
  except (OSError,ValueError,KeyError,json.JSONDecodeError):pass
  if before is not None and proof.exists()and disk.exists():
   try:
    old=json.loads(proof.read_text())
    if old['inputs']==before and old['disk_sha256']==sha(disk)and old['manifest_sha256']==sha(manifest):
     return dict(packaged=False,members=len(before['members']),editor_capsules=len(capsules),disk_sha256=old['disk_sha256'])
   except (OSError,ValueError,KeyError,json.JSONDecodeError):pass
  previous={p:p.read_bytes()if p.exists()else None for p in(disk,manifest)}
  try:
   subprocess.run([sys.executable,project/'tools/package.py','--c1541',c1541],cwd=project,check=True,stdout=subprocess.DEVNULL)
   if identity(project,project)!=record:raise RuntimeError('resident/source changed during packaging')
   if all_editor_capsules(project,record)!=capsules:raise RuntimeError('editor capsule changed during packaging')
   current=package_inputs(project)
   # package.py intentionally regenerates its six malformed probe fixtures.
   generated={'build/overlays/'+n+'.seo'for n in('short','extra','badcrc','badhdr','binderr','payerr')}
   if before is not None:
    for name,value in before['files'].items():
     if name not in generated and current['files'].get(name)!=value:raise RuntimeError('input changed during packaging: '+name)
   spec=importlib.util.spec_from_file_location('_cache_disk_oracle',project/'tools/d81_image.py');mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
   image=mod.D81Image(disk.read_bytes())
   for name,native in current['members']:
    dos=native.split(',')[0].upper().encode('ascii');kind=1 if native.lower().endswith(',s')else 2
    if image.read(dos,kind=kind).data!=(project/name).read_bytes():raise ValueError('packaged bytes differ: '+name)
   if json.loads(manifest.read_text())['sha256']!=sha(disk):raise ValueError('disk manifest SHA mismatch')
   state=dict(inputs=current,disk_sha256=sha(disk),manifest_sha256=sha(manifest),editor_capsules=capsules)
   write_changed(proof,json.dumps(state,indent=2,sort_keys=True).encode()+b'\n')
   return dict(packaged=True,members=len(current['members']),editor_capsules=len(capsules),disk_sha256=state['disk_sha256'])
  except BaseException:
   for p,data in previous.items():
    if data is None:p.unlink(missing_ok=True)
    else:write_changed(p,data)
   raise
 finally:lock.unlink()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--publish',type=Path);p.add_argument('--lexical-out',type=Path);p.add_argument('--package',action='store_true');p.add_argument('--c1541',default='c1541');a=p.parse_args();result=ensure(a.project,a.base,a.out,a.publish,a.lexical_out);result['disk']=ensure_disk(a.project,a.c1541)if a.package else None;print(json.dumps(result,sort_keys=True))
