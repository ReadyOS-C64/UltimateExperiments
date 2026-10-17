from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-current-turbo')
import json,hashlib,ctypes as C,time,shutil,subprocess,shlex,ast
import v1_lane as V
L=V.L
for name,ret,args in [('dos64_host_input_model_reads',C.c_uint64,[V.ptr,C.c_uint8]),('dos64_step',None,[V.ptr]),('dos64_host_input_model_keys',None,[V.ptr,V.ptr])]:V.bind(name,ret,args)
def labels(p):return {s.split()[2].lstrip('.'):int(s.split()[1],16)for s in p.read_text().splitlines()if s.startswith('al ')}
B=labels(P/'runtime/broker/broker.labels');UI=labels(P/'runtime/ui/panel.labels');BR=labels(P/'runtime/bridge/bridge.labels')
def finish(n,out):
 f=n.f;m=f.m;n.resume();assert n.get('hdb_active')==b'\0'
 L.lc_clock_model_ratio(m,64);L.dos64_host_input_model_keys(m,bytes(7)+b'\xa4')
 r=L.v1_call(m,n.at('dos64_overlay_input_poll'),0x300,40000000);assert r.status==0 and n.get('dos64_modal_pending')==b'\1'
 r=L.v1_call(m,n.at('dos64_native_tick'),0x7000,40000000);assert r.regs.pc==0x7000
 r=L.dos64_run(m,B['modal_wait'],40000000);assert r.regs.pc==B['modal_wait']
 events=[]
 def go(matrix,final=False):
  start=L.dos64_host_input_model_reads(m,1);L.dos64_host_input_model_keys(m,bytes(matrix));passes=[];stop=B['modal_safe_idle']if final else B['modal_wait']
  for k in range(256):
   L.dos64_step(m);r=L.dos64_run(m,stop,40000000 if final else 5000000);reads=L.dos64_host_input_model_reads(m,1)-start;passes.append({'pass':k+1,'reads':reads,'clock':n.get('dos64_host_clock_status')[0],'ps_key':L.dos64_peek(m,UI['_ps_key'])})
   assert r.regs.pc==stop,(r.status,hex(r.regs.pc),passes,n.get('dos64_native_diag',19).hex())
   if final or reads>=9:break
  else:raise TimeoutError('256 heldCIA passes without fullscan')
  events.append({'matrix':bytes(matrix).hex(),'passes':passes,'terminal_safe':final})
  if not final and not any(matrix):assert L.dos64_peek(m,UI['_ps_key'])==0
 normal=[8,13,0x83,0x96,0x90,0x92,0x94,0x81,*map(ord,'3wa4zse'),0,*map(ord,'5rd6cftx'),*map(ord,'7yg8bhuv'),*map(ord,'9ij0mkon'),*map(ord,'+pl-.:@,'),ord('\\'),ord('*'),ord(';'),0x84,0,ord('='),ord('^'),ord('/'),ord('1'),9,0,ord('2'),ord(' '),0,ord('q'),27]
 go(bytes(8));keys=bytearray(8);index=normal.index(ord('f'));keys[index//8]|=1<<(index%8);go(keys)
 assert L.dos64_peek(m,UI['_mu_result'])==7,('not actual Finish confirmation',L.dos64_peek(m,UI['_mu_result']))
 go(bytes(8));snapshot=f.reu(0,4194304);commands=L.bulk_model_commands(m);target=n.get('hdc_target')[0]
 go(bytes([2])+bytes(7),True)
 assert L.dos64_peek(m,UI['_mu_result'])==6 and L.dos64_peek(m,BR['br_safe'])==1 and L.dos64_peek(m,BR['br_resume'])==0
 assert n.stage()==0xe1 and [L.bulk_model_open(m,i)for i in [1,2]]==[0,0]
 assert L.bulk_model_commands(m)-commands==1 and [L.bulk_model_command(m,commands,i)for i in [0,1]]==[target,3]
 assert f.reu(0,4194304)==snapshot
 data=f.file(V.PATHS[2]);out.mkdir(exist_ok=True);(out/'CIA_FINISH.json').write_text(json.dumps({'passed':True,'events':events,'actual_one_C_CLOSE':True,'target':target,'both_firmware_handles_closed':True,'private_safe':True,'no_resume':True,'full4M_exact':True,'scope':'all issued native HD work completed; application already exited and DOS redirection closed; no claim of forcing unclosed guest logical buffers'},indent=2)+'\n')
 return data

def opened(s):
 lines=s['text'].splitlines();return s['head']==s['tail']and V.menu(s)and'V1EDIT.PAS'in lines[1]and'NONAME00.PAS'not in s['text']and all(any(line.strip()==x for line in lines)for x in V.SOURCE)and all(x not in s['text']for x in ['Open a File','Save File As','Compiling'])
def reopen(n):
 n.type('TURBO C:\\V1EDIT.PAS\r','TURBO-reopen-saved');s=n.wait('IDE-reopened-exact-source',opened);n.key(s,0x2d00);n.wait('DOS-after-reopen-AltX',lambda s:s['prompt']);n.type('ECHO V1 REOPEN DONE\r','reopen-marker');n.wait('DOS-reopen-marker',lambda s:s['prompt']and any(line.strip()=='V1 REOPEN DONE'for line in s['text'].splitlines()))

def main():
 out=P/'execution';assert not out.exists();out.mkdir()
 # Record actual SDK dependencies for the freshly source-built native model.
 w=P/'start';sources=['tests/floppy_export/bridge.cpp','v1_bridge.cpp']+['third_party/peddle/Peddle/'+n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']]
 dep=subprocess.run(['clang++','-std=c++20','-M','-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle',*sources],cwd=w,capture_output=True,check=True);(out/'MODEL_DEPENDENCIES.txt').write_bytes(dep.stdout)
 paths=[P/'BUNDLE.json',P/'COLD_PARENT_MANIFEST.json',P/'v1_lane.py',Path(__file__).resolve()]
 for folder in ['start','inputs','runtime','gate','media','project']:
  paths.extend(p for p in(P/folder).rglob('*')if p.is_file()and'__pycache__'not in p.parts)
 bundle=json.loads((P/'BUNDLE.json').read_text())
 for row in bundle['products'].values():
  path=Path(row['path']);assert V.ident(path)=={k:row[k]for k in ['sha256','bytes']};paths.append(path)
 for token in shlex.split(dep.stdout.decode().replace('\\\n',' ')):
  if token.endswith(':'):continue
  p=Path(token);p=p if p.is_absolute()else w/p
  if p.is_file():paths.append(p.resolve())
 paths +=[Path(sys.executable).resolve(),Path(shutil.which('clang++')).resolve()]
 pins={str(p.resolve()):V.ident(p)for p in paths};V.verify(pins);(out/'INPUTS_BEFORE.json').write_text(json.dumps(pins,indent=2)+'\n')
 for n,v in pins.items():
  d=out/'copies'/n.lstrip('/');d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(n,d);assert V.ident(d)==v
 hd=(P/'media/C-original.IMG').read_bytes();result={'status':'FAILED','physical':False,'SUT':'806e/1b70/f17b/44dd exact frozen0c7356 source-built bundle','keyboard':'guestIDE native XT-word endpoint; native Finish actual heldCIA matrix; physicalhuman untested','initial_fixture':'canonical host-prepared20MiB CFG/media including unmodified originalTurbo; not newly executed SETUP/CONFIG','no_source_disk_injection_to_fake_save':True};f=n=None;primary=None
 try:
  first=out/'producer80';first.mkdir();f=V.Fixture(hd,80);n=V.launch(f,first);V.workflow(n);(first/'C-before-Finish-issued-writes-not-knownclosed.IMG').write_bytes(f.file(V.PATHS[2]));saved=finish(n,first);(out/'C-after-Finish.IMG').write_bytes(saved);result['producer']=V.inspect(hd,saved,first);result['producer_wire']=n.wire_summary(True);result['producer_guest']=n.guest();assert f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b;f.close();f=n=None
  d=out/'fresh40';d.mkdir();f=V.Fixture(saved,40);n=V.launch(f,d);V.fresh(n);fresh=finish(n,d);assert fresh==saved and f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b;result['fresh40_wire']=n.wire_summary(False);result['fresh40_guest']=n.guest();f.close();f=n=None
  d=out/'fresh80-reopen';d.mkdir();f=V.Fixture(saved,80);n=V.launch(f,d);reopen(n);after=n.close_readback();(out/'C-after-fresh80-native-readback.IMG').write_bytes(after)
  oldreport=V.DISK.inspect(saved,(640,4,16));at=oldreport['partition']['start_lba']*512;length=oldreport['bpb']['total_sectors']*512;before=V.DISK.Volume(saved[at:at+length]);new=V.DISK.Volume(after[at:at+length]);changes=[k for k,v in before.payloads.items()if new.payloads.get(k)!=v];added=sorted(set(new.payloads)-set(before.payloads));deleted=sorted(set(before.payloads)-set(new.payloads));allowed={'TURBO.DSK','TP/BIN/TURBO.DSK'};assert not deleted and all(k.upper()in allowed for k in changes+added),(changes,added,deleted)
  assert f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b
  (d/'FAT.json').write_text(json.dumps(V.DISK.inspect(after,(640,4,16)),indent=2)+'\n');writes=any(L.bulk_model_command(n.m,i,1)==5 for i in range(L.bulk_model_commands(n.m)));result['fresh80_wire']=n.wire_summary(writes);result.update(status='PASS_ACTUAL_NEW_COLD_TURBO_EDIT_SAVE_DISKCOMPILE_RUN_EXIT_CIA_FINISH_FRESH40_RUN_FRESH80_IDEREOPEN_FULL_NATIVE20M_READBACK',fresh80_guest=n.guest(),fresh80_metadata={'payload_changes':changes,'added':added,'deleted':deleted,'raw_changed_bytes':sum(a!=b for a,b in zip(saved,after))},full_after_Finish_sha256=V.sha(saved),full_after_reopen_sha256=V.sha(after))
 except BaseException as ex:
  primary=ex;result['error']=repr(ex)
  if isinstance(ex,Exception)and n is not None and f is not None and n.stage()in[4,5]and not getattr(n,'readback_started',False):
   try:
    for _ in range(4096):
     if n.get('hdb_active')==b'\0':break
     n.resume();n.tick(1)
    assert n.get('hdb_active')==b'\0';n.observe('failure-diagnostic',True);data=n.close_readback();(out/'C-first-failure-knownclose.IMG').write_bytes(data);result['diagnostic']='native-knownclose/fullreadback only; primaryfailure retained'
   except BaseException as secondary:result['diagnostic_error']=repr(secondary)
  raise
 finally:
  actions=[]
  if n is not None:actions.extend([lambda:result.update(guest=n.guest(),ticks=n.ticks,native_diag=n.get('dos64_native_diag',34).hex(),observations=n.observations,keys=n.keys),lambda:(out/'final-or-failed-RAM.bin').write_bytes(n.ram())])
  if f is not None:actions.extend([lambda:(out/'C-model-current.IMG').write_bytes(f.file(V.PATHS[2])),f.close])
  actions.extend([lambda:V.verify(pins),lambda:(out/'INPUTS_AFTER.json').write_text(json.dumps(pins,indent=2)+'\n')])
  for action in actions:
   try:action()
   except BaseException as ex:
    result.setdefault('secondary_errors',[]).append(repr(ex))
    if primary is None:primary=ex
  result['total_native_cycles']=V.TOTAL_NATIVE_CYCLES
  try:(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
  except BaseException as ex:
   if primary is None:primary=ex
  if primary is not None and sys.exc_info()[0]is None:raise primary
if __name__=='__main__':main()
