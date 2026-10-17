from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-run-debug');assert not Path(sys.pycache_prefix).exists();os.environ['PUBLISHED_DIRECTORY']=str(P/'published');os.environ['MEDIA_DIRECTORY']=str(P/'media')
import json,hashlib,ctypes as C,struct,re,subprocess,shlex,shutil,time,traceback
import v1_lane as V
from test_journal_start import Journal
import finish_helpers as FH
L=V.L
for name,ret,args in [('dos64_host_input_model_reads',C.c_uint64,[V.ptr,C.c_uint8]),('dos64_step',None,[V.ptr]),('dos64_host_input_model_keys',None,[V.ptr,V.ptr])]:V.bind(name,ret,args)
class Fixture(Journal):
 def __init__(self,hd,columns=80,published='published'):
  os.environ['PUBLISHED_DIRECTORY']=str(P/published);os.environ['MEDIA_DIRECTORY']=str(P/'media');super().__init__(columns);self.hd=hd;self.paths=[self.config[a:a+128].split(b'\0')[0]for a in [136,264,392]];assert self.paths==[b'/Home/A.IMG',b'/Home/B.IMG',b'/Home/C.IMG'];self.c=hd;V.PATHS=self.paths;L.bulk_model_seed(self.m,self.paths[2],hd,len(hd))
 def file(self,path):
  size=L.bulk_model_size(self.m,path);assert size!=0xffffffff;buf=C.create_string_buffer(size);assert L.bulk_model_read(self.m,path,buf,size);return buf.raw

def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def inspect(before,after,out):
 fat=V.DISK.inspect(after,(128,2,16));v=V.DISK.Volume(after[8192:]);old=V.DISK.Volume(before[8192:]);assert all(v.payloads.get(n)==b for n,b in old.payloads.items())
 assert v.payloads['V1TRAP.COM']==bytes.fromhex('b8341240bb785690b8004ccd21'),v.payloads['V1TRAP.COM'].hex()
 assert v.payloads['DEBUG.DON']==b'V1_DEBUG_COMPLETE\r\n'
 expected=b'N C:\\V1TRAP.COM\r\nE 100 B8 34 12 40 BB 78 56 CC B8 00 4C CD 21\r\nRCX\r\nD\r\nW\r\nT=100\r\nT\r\nG=100 107\r\nE 107 90\r\nW\r\nQ\r\n'
 assert v.payloads['DEBUG.INP']==expected,repr(v.payloads['DEBUG.INP'])
 text=v.payloads['DEBUG.LOG'].decode('ascii');pairs=[]
 for match in re.finditer(r'AX=([0-9A-F]{4})\s+BX=([0-9A-F]{4}).*?IP=([0-9A-F]{4})',text,re.S):pairs.append({'AX':match[1],'BX':match[2],'IP':match[3]})
 assert len(pairs)==3,(pairs,text)
 assert [(p['AX'],p['IP'])for p in pairs[:2]]==[('1234','0103'),('1235','0104')],(pairs,text)
 assert pairs[2]=={'AX':'1235','BX':'5678','IP':'0107'},(pairs,text)
 assert text.count('Writing 000D bytes')==2,text
 assert not any(x in text.lower()for x in ['error','bad command','syntax']),text
 out.mkdir(exist_ok=True);save(out/'FAT.json',fat);(out/'DEBUG.LOG').write_bytes(v.payloads['DEBUG.LOG'])
 for n in ['DEBUG.INP','DEBUG.DON','V1TRAP.COM']:(out/n).write_bytes(v.payloads[n])
 return {'passed':True,'original_plus_input_payloads_exact':len(old.payloads),'new_files':{n:{'sha256':V.sha(v.payloads[n]),'bytes':len(v.payloads[n])}for n in sorted(set(v.payloads)-set(old.payloads))},'DEBUG_registers':pairs,'DEBUG_INT3_IP_qualification':'G user breakpoint address0107; DEBUG normalizes architectural INT3 next-IP0108','full_C_sha256':V.sha(after)}

def main():
 D=P/'execution';D.mkdir();model=P/'start';src=['tests/floppy_export/bridge.cpp','v1_bridge.cpp']+['third_party/peddle/Peddle/'+n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']]
 compiler=Path(shutil.which('clang++')).resolve();dep=subprocess.run([str(compiler),'-std=c++20','-M','-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle',*src],cwd=model,capture_output=True,check=True);(D/'MODEL_DEPENDENCIES.txt').write_bytes(dep.stdout)
 paths=[Path(__file__).resolve(),P/'prepare.py',P/'FIXTURE_PROVENANCE.json',P/'ORIGINS.json',P/'BUILD_RESULT.json',P/'COLD_RESULT.json',P/'POLICY_BEFORE_CODE.md',P/'V1DEBUG.BAT',P/'v1_lane.py',P/'finish_helpers.py',Path(sys.executable).resolve(),compiler]
 for folder in ['start','project','inputs','runtime','gate','media','published','published40']:paths.extend(p for p in(P/folder).rglob('*')if p.is_file()and'__pycache__'not in p.parts)
 for token in shlex.split(dep.stdout.decode().replace('\\\n',' ')):
  if token.endswith(':'):continue
  p=Path(token);p=p if p.is_absolute()else model/p
  if p.is_file():paths.append(p.resolve())
 records={str(p.resolve()):V.ident(p)for p in paths}
 for n in ['BUILD_RESULT.json','COLD_RESULT.json']:
  j=json.loads((P/n).read_text())
  for section in ['source_inputs','native_products']:
   for p,w in j[section].items():assert V.ident(Path(p))==w,p;records[p]=w
 V.verify(records);save(D/'INPUTS_BEFORE.json',records)
 for i,(p,w)in enumerate(sorted(records.items())):q=D/'copies'/('%05d'%i);q.parent.mkdir(exist_ok=True);shutil.copyfile(p,q);assert V.ident(q)==w
 result={'passed':False,'scope':'genuine DOS DEBUG T/INT3 +native Finish +fresh40 persistence; matched new0bfa TF/FORMAT/cold8','physical':False,'guest_keyboard':'nativeXTword endpoint, physicalhuman bypassed','native_Finish':'heldCIA complete scan, privateSafe/knownCLOSE','new_installer_output_claim':False};f=n=None;primary=None
 try:
  hd=(P/'media/C-input.IMG').read_bytes();d=D/'producer80';d.mkdir();f=Fixture(hd);n=V.launch(f,d)
  n.type('CLS\r','initial-clear');n.wait('initial-cleared',lambda s:s['prompt']and all(not x.strip()or x.strip()=='C>'for x in s['text'].splitlines()))
  n.type('V1DEBUG\r','genuine-DEBUG-batch');s=n.wait('DEBUG-batch-complete',lambda s:s['prompt']and any(x.strip()=='V1_DEBUG_COMPLETE'for x in s['text'].splitlines()))
  saved=FH.finish(n,d);(D/'C-after-Finish.IMG').write_bytes(saved);result['producer']=inspect(hd,saved,d/'independent');result['producer_wire']=n.wire_summary(True);result['producer_guest']=n.guest();assert f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b;f.close();f=n=None
  d=D/'fresh40';d.mkdir();f=Fixture(saved,40,'published40');n=V.launch(f,d)
  n.type('CLS\r','fresh-clear');n.wait('fresh-cleared',lambda s:s['prompt']and all(not x.strip()or x.strip()=='C>'for x in s['text'].splitlines()))
  n.type('TYPE C:\\DEBUG.DON\r','fresh-persistent-marker');n.wait('fresh-marker',lambda s:s['prompt']and any(x.strip()=='V1_DEBUG_COMPLETE'for x in s['text'].splitlines()))
  for value in ['IP=0103','IP=0104','IP=0107']:
   n.type('CLS\r','fresh-clear-'+value);n.wait('fresh-cleared-'+value,lambda s:s['prompt']and all(not x.strip()or x.strip()=='C>'for x in s['text'].splitlines()))
   n.type('FIND "'+value+'" C:\\DEBUG.LOG\r','fresh-log-'+value);n.wait('fresh-log-read-'+value,lambda s:s['prompt']and value in s['text']and'AX=123'in s['text'])
  n.type('CLS\r','fresh-clear-run');n.wait('fresh-cleared-run',lambda s:s['prompt']and all(not x.strip()or x.strip()=='C>'for x in s['text'].splitlines()))
  n.type('C:\\V1TRAP.COM\rECHO V1_FRESH_RUN_OK\r','fresh-COM-run');n.wait('fresh-COM-returned',lambda s:s['prompt']and any(x.strip()=='V1_FRESH_RUN_OK'for x in s['text'].splitlines())and'Bad command'not in s['text'])
  again=FH.finish(n,d);assert again==saved and f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b;result.update(passed=True,fresh40_guest=n.guest(),fresh40_wire=n.wire_summary(False),fresh_full_C_byteexact=True)
 except BaseException as ex:
  primary=ex;result['error']=repr(ex);result['traceback']=traceback.format_exc()
  if n is not None and f is not None:
   try:(D/'C-failure-not-knownclosed.IMG').write_bytes(f.file(V.PATHS[2]));save(D/'FAILURE_OBSERVATIONS.json',n.observations);(D/'failure-RAM.bin').write_bytes(n.ram());result['failed_native_diag']=n.get('dos64_native_diag',34).hex()
   except BaseException as other:result['diagnostic_error']=repr(other)
  raise
 finally:
  actions=[]
  if f is not None:actions.append(f.close)
  actions +=[lambda:V.verify(records),lambda:save(D/'INPUTS_AFTER.json',records)]
  for action in actions:
   try:action()
   except BaseException as ex:
    result.setdefault('secondary_errors',[]).append(repr(ex))
    if primary is None:primary=ex
  result['native_cycles_including_observers_not_perf']=V.TOTAL_NATIVE_CYCLES
  try:save(D/'RESULT.json',result)
  except BaseException as ex:
   if primary is None:primary=ex
  if primary is not None and sys.exc_info()[0]is None:raise primary
if __name__=='__main__':main()
