from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-run-batch');assert not Path(sys.pycache_prefix).exists()
os.environ['PUBLISHED_DIRECTORY']=str(P/'published');os.environ['MEDIA_DIRECTORY']=str(P/'media')
import json,hashlib,ctypes as C,struct,time,shutil,traceback
import v1_lane as V
from test_journal_start import Journal
import finish_helpers as FH
L=V.L
for name,ret,args in [('dos64_host_input_model_reads',C.c_uint64,[V.ptr,C.c_uint8]),('dos64_step',None,[V.ptr]),('dos64_host_input_model_keys',None,[V.ptr,V.ptr])]:V.bind(name,ret,args)
class Fixture(Journal):
 def __init__(self,hd,columns=80,published='published'):
  os.environ['PUBLISHED_DIRECTORY']=str(P/published);os.environ['MEDIA_DIRECTORY']=str(P/'media')
  super().__init__(columns);self.hd=hd
  self.paths=[self.config[a:a+128].split(b'\0')[0]for a in[136,264,392]]
  assert self.paths==[b'/Home/A.IMG',b'/Home/B.IMG',b'/Home/C.IMG'];self.c=hd;V.PATHS=self.paths
  L.bulk_model_seed(self.m,self.paths[2],hd,len(hd))
 def file(self,path):
  size=L.bulk_model_size(self.m,path);assert size!=0xffffffff;buf=C.create_string_buffer(size);assert L.bulk_model_read(self.m,path,buf,size);return buf.raw

def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def inspect(before,after,out):
 report=V.DISK.inspect(after,(128,2,16));v=V.DISK.Volume(after[8192:]);old=V.DISK.Volume(before[8192:]);base=V.DISK.Volume((P/'media/C.IMG').read_bytes()[8192:])
 for name,body in old.payloads.items():assert v.payloads.get(name)==body,('original or input payload changed',name)
 expected={'V1WORK/ORIG.TXT':b'ALPHA\r\nBETA\r\n','V1WORK/KEEP.TXT':b'ALPHA\r\nBETA\r\n','V1WORK/WCOPY.TXT':b'ALPHA\r\nBETA\r\n','V1WORK/EMPTY.DAT':b'','V1WORK/ENV.TXT':b'BATCHVALUE\r\n','V1WORK/PROMPT.TXT':b'V1$N$G\r\n','V1WORK/FOR.TXT':b'ONE\r\nTWO\r\nTHREE\r\n','V1WORK/ARGS.TXT':b'FIRST\r\nSECOND\r\n','V1WORK/CMD.TXT':b'CHILD_OK\r\n','V1WORK/EXIT.TXT':b'EXIT_OK\r\n','V1WORK/SUB/DEEP.TXT':b'NESTED\r\n','V1DONE.TXT':b'COMPLETE\r\n','V1WORK/BIN.DAT':base.payloads['DOS/COMMAND.COM']}
 for name,body in expected.items():assert v.payloads.get(name)==body,(name,repr(v.payloads.get(name)))
 for bad in['V1FAIL.TXT','V1WORK/BAD.TXT','V1WORK/EXITBAD.TXT','V1WORK/T1.TXT','V1WORK/T2.TXT','V1WORK/TD1.TXT','V1WORK/TD2.TXT']:assert bad not in v.payloads,bad
 assert not any(d['name']=='EMPTY'for d in v.directories)
 log=v.payloads['V1.LOG'].decode('ascii');required=['REN_OK','WILD_OK','WILD2_OK','RO_OK','SUB_OK','CALL_BACK','ERRORLEVEL0_OK','ERRORLEVEL1_OK','RD_OK']
 assert all(log.splitlines().count(x)==1 for x in required),log
 assert 'drive C'in log,log
 assert v.payloads['V1WORK/RET1.COM']==bytes.fromhex('b8014ccd21')
 assert b'R'in v.payloads['V1WORK/ATRO.LOG']and b'KEEP'in v.payloads['V1WORK/ATRO.LOG'];assert b'R'not in v.payloads['V1WORK/ATWR.LOG'].split(b'C:')[0]
 files={n:{'bytes':len(b),'sha256':V.sha(b)}for n,b in v.payloads.items()if n not in old.payloads}
 out.mkdir(exist_ok=True)
 for n,b in v.payloads.items():
  if n not in old.payloads:p=out/'files'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 save(out/'FAT.json',report);return {'passed':True,'original_and_input_payloads_exact':len(old.payloads),'original_DOS_payloads':len(base.payloads),'new_files':files,'log':log,'full_image_sha256':V.sha(after),'free_bytes':report['free_bytes']if'free_bytes'in report else v.report()['free_bytes']}

def main():
 D=P/'execution';D.mkdir();paths=[Path(__file__).resolve(),P/'FIXTURE_PROVENANCE.json',P/'ORIGINS.json',P/'START_GUARD_ADAPTATION.json',Path(sys.executable).resolve()]
 for folder in['start','project','inputs','runtime','gate','media','published','published40']:
  paths +=[p for p in(P/folder).rglob('*')if p.is_file()and'__pycache__'not in p.parts]
 paths +=[P/'v1_lane.py',P/'finish_helpers.py',P/'V1TEST.BAT',P/'V1SUB.BAT',P/'V1EXIT.BAT']
 before={str(p.resolve()):V.ident(p)for p in paths};save(D/'INPUTS_BEFORE.json',before)
 for n,v in before.items():
  q=D/'copies'/n.lstrip('/');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(n,q);assert V.ident(q)==v
 result={'passed':False,'scope':'actual c7 DOS shell/batch/CHKDSK +Finish+fresh launch on owned copy of actual SETUP C','physical':False};f=n=None;primary=None
 try:
  hd=(P/'media/C-input.IMG').read_bytes();d=D/'producer80';d.mkdir();f=Fixture(hd);n=V.launch(f,d);n.type('CLS\r','clear-initial');n.wait('cleared',lambda s:s['prompt']and all(not l.strip()or l.strip()=='C>'for l in s['text'].splitlines()))
  n.type('V1TEST\r','run-actual-batch');s=n.wait('batch-complete',lambda s:s['prompt']and any(l.strip()=='V1_BATCH_COMPLETE'for l in s['text'].splitlines()))
  n.type('CLS\r','clear-before-chkdsk');n.wait('cleared-before-chkdsk',lambda s:s['prompt']and all(not l.strip()or l.strip()=='C>'for l in s['text'].splitlines()))
  n.type('CHKDSK C:\r','actual-CHKDSK');s=n.wait('CHKDSK-returned',lambda s:s['prompt']and'total disk space'in s['text'].lower()and'bytes available'in s['text']);save(d/'CHKDSK_SCREEN.json',s)
  assert 'lost'in s['text'].lower()or 'CHKDSK'in s['text'];assert all(x not in s['text'].lower()for x in['allocation error','cross-linked','lost chains','lost clusters','found errors']),s['text']
  n.type('DATE\r','query-date');date=n.wait('date-prompt',lambda s:'Enter new date'in s['text']and'10-17-1988'in s['text'],False);save(d/'DATE_SCREEN.json',date);n.type('\r','keep-date');n.wait('date-return',lambda s:s['prompt'])
  n.type('TIME\r','query-time');clock=n.wait('time-prompt',lambda s:'Enter new time'in s['text']and'12:'in s['text'].rsplit('Current time is',1)[-1],False);save(d/'TIME_SCREEN.json',clock);n.type('\r','keep-time');n.wait('time-return',lambda s:s['prompt'])
  saved=FH.finish(n,d);(D/'C-after-Finish.IMG').write_bytes(saved);result['producer']=inspect(hd,saved,d/'independent');result['producer_wire']=n.wire_summary(True);result['producer_guest']=n.guest();assert f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b
  free=result['producer']['free_bytes'];digits=str(free)
  assert digits in s['text'].replace(',',''),('CHKDSK independent free',free,s['text']);result['CHKDSK_free_matches_full_FAT']=True
  f.close();f=n=None
  d=D/'fresh40';d.mkdir();f=Fixture(saved,40,'published40');n=V.launch(f,d);n.type('CLS\r','fresh-clear');n.wait('fresh-cleared',lambda s:s['prompt']and all(not l.strip()or l.strip()=='C>'for l in s['text'].splitlines()));n.type('TYPE C:\\V1DONE.TXT\r','fresh-marker');n.wait('fresh-marker-read',lambda s:s['prompt']and any(l.strip()=='COMPLETE'for l in s['text'].splitlines()));n.type('TYPE C:\\V1WORK\\ARGS.TXT\r','fresh-args');n.wait('fresh-args-read',lambda s:s['prompt']and all(any(l.strip()==x for l in s['text'].splitlines())for x in['FIRST','SECOND']));n.type('TYPE C:\\V1WORK\\SUB\\DEEP.TXT\r','fresh-nested');n.wait('fresh-nested-read',lambda s:s['prompt']and any(l.strip()=='NESTED'for l in s['text'].splitlines()))
  again=FH.finish(n,d);assert again==saved and f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b;result.update(passed=True,fresh40_guest=n.guest(),fresh40_wire=n.wire_summary(False),fresh_image_byteexact=True)
 except BaseException as ex:
  primary=ex;result['error']=repr(ex);result['traceback']=traceback.format_exc()
  if n is not None and f is not None:
   try:
    (D/'C-failure-not-knownclosed.IMG').write_bytes(f.file(V.PATHS[2]));result['failed_native_diag']=n.get('dos64_native_diag',34).hex();save(D/'FAILURE_OBSERVATIONS.json',n.observations);(D/'failure-RAM.bin').write_bytes(n.ram())
   except BaseException as other:result['diagnostic_error']=repr(other)
  raise
 finally:
  actions=[]
  if f is not None:actions.append(f.close)
  actions +=[lambda:V.verify(before),lambda:save(D/'INPUTS_AFTER.json',before)]
  for action in actions:
   try:action()
   except BaseException as ex:
    result.setdefault('secondary_errors',[]).append(repr(ex))
    if primary is None:primary=ex
  result['native_cycles_including_observer_not_perf']=V.TOTAL_NATIVE_CYCLES
  try:save(D/'RESULT.json',result)
  except BaseException as ex:
   if primary is None:primary=ex
  if primary is not None and sys.exc_info()[0]is None:raise primary
if __name__=='__main__':main()
