from pathlib import Path
import sys,os,json,shutil,traceback,time,struct
P=Path(__file__).resolve().parent;assert Path.cwd()==P;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-util-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists();os.environ['PUBLISHED_DIRECTORY']=str(P/'published');os.environ['MEDIA_DIRECTORY']=str(P/'media')
import ast,ctypes as C
import run_debug as R
V=R.V;FH=R.FH
original_key=V.key
extra={'"':0x2822,'=':0x0d3d,'_':0x0c5f,',':0x332c,'\x03':0x2e03,'\x1a':0x2c1a}
V.key=lambda ch:extra[ch]if ch in extra else original_key(ch)
COMMANDS=['CLS\r','V1UTIL\r','EDLIN C:\\V1ED.TXT\r','I\rALPHA\rBETA\r','\x03','2\rBETA EDIT\r','E\r','L\r','Q\r','Y\r','TYPE C:\\V1ED.TXT\r','LABEL C:\r','V1UTIL\r','VOL C: >C:\\VOL.LOG\r']
preflight={repr(c):hex(V.key(c))for c in sorted(set(''.join(COMMANDS)))}
assert all((V.key(c)&255)==ord(c) for c in set(''.join(COMMANDS)))
assert V.sha((P/'start/journal-peddle.dylib').read_bytes())=='450ca17b54b216330ec62f9d8604ade4930b31d35f3743fb639f2e0b8d1ff6d4'
(P/'KEYBOARD_PREFLIGHT.json').write_text(json.dumps(preflight,indent=2)+'\n')
abi={}
for filename in ['run_utilities.py','run_debug.py','finish_helpers.py','v1_lane.py']:
 for node in ast.walk(ast.parse((P/filename).read_text())):
  if isinstance(node,ast.Attribute)and isinstance(node.value,ast.Name)and node.value.id=='L':
   fn=getattr(V.L,node.attr);assert fn.argtypes is not None,node.attr;abi[node.attr]={'args':[getattr(a,'__name__',str(a))for a in fn.argtypes],'result':getattr(fn.restype,'__name__',None)}
(P/'CTYPES_ABI.json').write_text(json.dumps(abi,indent=2)+'\n')
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def edprompt(s):
 row,col=s['cursor'];return not s['prompt']and s['text'].splitlines()[row][:col].strip()=='*'
def inspect(before,after,d):
 old=V.DISK.Volume(before[8192:]);new=V.DISK.Volume(after[8192:]);assert all(new.payloads.get(n)==b for n,b in old.payloads.items())
 expected={'V1UTIL/SRC/ONE.TXT':b'REPLACED\r\n','V1UTIL/SRC/TWO.TXT':b'ALPHA\r\n','V1UTIL/DST/ONE.TXT':b'REPLACED\r\n','V1UTIL/DST/TWO.TXT':b'ALPHA\r\n','SORT.OUT':b'ALPHA\r\nBETA\r\nGAMMA\r\n'}
 for n,b in expected.items():assert new.payloads.get(n)==b,(n,new.payloads.get(n))
 for n in ['FC.LOG','FC2.LOG']:assert b'no differences' in new.payloads[n].lower(),(n,new.payloads[n])
 assert b'ALPHA' in new.payloads['FIND.OUT'] and b'BETA'not in new.payloads['FIND.OUT'];assert b'V1UTIL'in new.payloads['VOL.LOG']
 assert 'SRC'in new.payloads['TREE.LOG'].decode('ascii') and 'DST'in new.payloads['TREE.LOG'].decode('ascii')
 assert b'compare ok'in new.payloads['COMP.LOG'].lower(),new.payloads['COMP.LOG']
 text=new.payloads['V1ED.TXT'];assert text.rstrip(b'\x1a')==b'ALPHA\r\nBETA EDIT\r\n',repr(text)
 d.mkdir();save(d/'FAT.json',V.DISK.inspect(after,(128,2,16)))
 for n,b in new.payloads.items():
  if n not in old.payloads:
   q=d/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 return {'passed':True,'preserved_payloads':len(old.payloads),'new_files':{n:{'sha256':V.sha(b),'bytes':len(b)}for n,b in new.payloads.items()if n not in old.payloads},'EDLIN_exact_text_hex':text.hex(),'volume_labels':new.labels}
def main():
 D=P/'execution';D.mkdir();records={str(q.resolve()):V.ident(q)for q in P.rglob('*')if q.is_file()and not q.is_relative_to(D)and q.name not in ['RUN.stdout','RUN.stderr']and'__pycache__'not in q.parts};records[str(Path(sys.executable).resolve())]=V.ident(Path(sys.executable).resolve())
 for n in ['BUILD_RESULT.json','COLD_RESULT.json']:
  j=json.loads((P/n).read_text())
  for section in ['source_inputs','native_products']:
   for name,v in j[section].items():assert V.ident(Path(name))==v,name;records[name]=v
 for name,v in json.loads((P/'BORROWED_MODEL_INPUTS.json').read_text()).items():
  assert V.ident(Path(name))==v,name;records[name]=v
 V.verify(records);save(D/'INPUTS_BEFORE.json',records)
 for i,(name,v)in enumerate(sorted(records.items())):
  q=D/'copies'/('%05d'%i);q.parent.mkdir(exist_ok=True);shutil.copyfile(name,q);assert V.ident(q)==v
 result={'passed':False,'scope':'genuineDOS suppliedfile/text utilities andEDLIN model','physical':False,'borrowed_model_sourcebuild':'acceptedDEBUG450ca17b unchanged copied','initial_media':'actual utilities+LABEL knownclosed checkpoint after retained hostnamespacefailure; originalDEBUGnativeSETUP ancestry; no utilities replay','keyboard':'XTword, physicalhuman bypassed'};f=n=None;primary=None
 try:
  hd=(P/'media/C-utilities-knownclosed.IMG').read_bytes();out=D/'producer80';out.mkdir();f=R.Fixture(hd,80);n=V.launch(f,out)
  n.type('EDLIN C:\\V1ED.TXT\r','edlin-new');n.wait('edlin-new-prompt',lambda s:edprompt(s)and'New file'in s['text'])
  n.type('I\rALPHA\rBETA\r','edlin-insert');s=n.wait('edlin-entered-lines',lambda s:not s['prompt']and'ALPHA'in s['text']and'BETA'in s['text']);n.key(s,0x2e03);n.wait('edlin-insert-ended',edprompt)
  n.type('2\rBETA EDIT\r','edlin-edit-line2');n.wait('edlin-edited',lambda s:edprompt(s)and'BETA EDIT'in s['text'])
  n.type('E\r','edlin-save');n.wait('DOS-after-edlin-save',lambda s:s['prompt'])
  n.type('CLS\r','clear-reopen');n.wait('reopen-cleared',lambda s:s['prompt']and all(not x.strip()or x.strip()=='C>'for x in s['text'].splitlines()))
  n.type('EDLIN C:\\V1ED.TXT\rL\r','edlin-reopen-list');n.wait('edlin-reopened-content',lambda s:edprompt(s)and'ALPHA'in s['text']and'BETA EDIT'in s['text'])
  n.type('Q\r','edlin-quit');n.wait('edlin-quit-confirmation',lambda s:not s['prompt']and'Abort'in s['text']);n.type('Y\r','edlin-confirm-quit');n.wait('DOS-after-edlin-reopen',lambda s:s['prompt'])
  saved=FH.finish(n,out);(D/'C-after-Finish.IMG').write_bytes(saved);result['producer']=inspect(hd,saved,D/'independent');result.update(wire=n.wire_summary(True),guest=n.guest());assert f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b
  f.close();f=n=None;out=D/'fresh40';out.mkdir();f=R.Fixture(saved,40,published='published40');n=V.launch(f,out)
  n.type('CLS\r','fresh-clear');n.wait('fresh-cleared',lambda s:s['prompt']and all(not x.strip()or x.strip()=='C>'for x in s['text'].splitlines()))
  n.type('TYPE C:\\V1ED.TXT\r','fresh-edlin-source');n.wait('fresh-exact-edlin-file',lambda s:s['prompt']and [x.strip()for x in s['text'].splitlines()if x.strip()]==['C>TYPE C:\\V1ED.TXT','ALPHA','BETA EDIT','C>'])
  n.type('VOL C: >C:\\VOL.LOG\r','fresh-volume-report');n.wait('fresh-volume-complete',lambda s:s['prompt'])
  fresh=FH.finish(n,out);(D/'C-after-fresh40-Finish.IMG').write_bytes(fresh);result['fresh40']=inspect(saved,fresh,D/'fresh-independent');result['fresh40_wire']=n.wire_summary(True);result['passed']=True
 except BaseException as ex:
  primary=ex;result['error']=repr(ex);result['traceback']=traceback.format_exc()
  if n is not None:
   try:save(D/'FAILURE_OBSERVATIONS.json',n.observations);(D/'failure-RAM.bin').write_bytes(n.ram());(D/'C-failed-not-knownclosed.IMG').write_bytes(f.file(V.PATHS[2]))
   except BaseException as secondary:result['diagnostic_error']=repr(secondary)
   try:
    s=n.observe('failure-safe-finish-check',True)
    assert s['prompt'] and s['head']==s['tail'] and n.get('hdb_active')==b'\0' and n.stage()in[4,5]
    data=FH.finish(n,D/'producer80');(D/'C-diagnostic-Finish-primaryfailure-retained.IMG').write_bytes(data);result['diagnostic_Finish']='knownclosed, primaryfailure retained'
   except BaseException as secondary:result['diagnostic_Finish_error']=repr(secondary)
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
  result['native_cycles_with_observers_not_perf']=V.TOTAL_NATIVE_CYCLES;save(D/'RESULT.json',result)
  if primary is not None and sys.exc_info()[0]is None:raise primary
if __name__=='__main__':main()
