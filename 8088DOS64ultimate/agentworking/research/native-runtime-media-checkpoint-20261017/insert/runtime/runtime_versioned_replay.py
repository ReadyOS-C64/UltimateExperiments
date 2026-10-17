from pathlib import Path
import os,sys,hashlib,json,ctypes as C,unittest
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-runtime-versioned');assert not Path(sys.pycache_prefix).exists()
assert not list((P/'work/build').glob('dos64-tests*')),'runtime proof excludes UNIT products'
os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
from role_oracle import verify,constants,labels
oracle=verify('runtime');n=labels(P/'work/build/dos64.labels');b=labels(P/'broker/broker.labels');imports=constants(P/'finish/imports.inc')
for k,v in imports.items():assert v==(b[k[7:]]if k.startswith('broker_')else n[k]),k
from test_versioned_save import *
from test_finish_ui import FN,FinishUI
allowed={};loaded=[]
for name in ['work/build/dos64.prg','broker/broker.prg']:
 raw=(P/name).read_bytes();allowed[(int.from_bytes(raw[:2],'little'),len(raw)-2,hashlib.sha256(raw[2:]).hexdigest())]=name
original=L.dos64_load
def checked(machine,address,data,count):
 raw=data if isinstance(data,bytes)else C.string_at(data,count);key=(address,count,hashlib.sha256(raw).hexdigest());assert key in allowed,key;loaded.append(allowed[key]);return original(machine,address,data,count)
L.dos64_load=checked
extra=[]
class Composition(unittest.TestCase):
 def chain(self,target,drive,bank):
  m,old,f=writable(self,target,drive,bank)
  try:
   prefix=b'/usb1/Owned/';letter=b'B'if drive else b'A';keep={b'S0001.OLD':b'old prior',letter+b'0002.IMG':b'orphan prior',b'S0004.JRN':b'one sided prior'}
   for name,v in keep.items():seed(m,prefix+name,v)
   enter(self,m);before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);hd=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);hdb=m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']);high=m.get(128,96);ports={a:m.g(a)for a in [0,1,0xdc02,0xdc03]};stack=L.dos64_get_regs(m.m).sp;pos=L.save_model_position(m.m,target);out=[];oldcfg=old
   for seq in [3,5]:
    path=prefix+letter+('%04X.IMG'%seq).encode();ticket=save_key(self,m,seq,path,drive);self.assertNotEqual(ticket,seq);guard_C(self,m,ctx,pos);self.assertEqual(m.get('hd_state_start',len(hd)),hd);self.assertEqual(m.get('hdb_state_start',len(hdb)),hdb);self.assertEqual(m.get(128,96),high);self.assertEqual({a:m.g(a)for a in ports},ports);self.assertEqual(L.dos64_get_regs(m.m).sp,stack);self.assertEqual(m.bytes(path,368640),f['working']);self.assertEqual(m.bytes(prefix+('S%04X.OLD'%seq).encode(),576),oldcfg);oldcfg=m.bytes(prefix+b'DOS64.CFG',576);self.assertEqual(reu(m,0x3ff020,576),oldcfg);out.append({'seq':seq,'ticket':ticket,'path':path.decode()})
   guard_REU(self,before,reu(m,0,4194304))
   for name,v in keep.items():self.assertEqual(m.bytes(prefix+name,len(v)),v)
   self.assertEqual(m.bytes(b'/usb1/Media/A.IMG',368640),A);self.assertEqual(m.bytes(b'/sd/Media/B.IMG',368640),OLD_B)
   # Actual CIA Finish on the same session after both ordinaryS jobs.
   press(self,m,ord('f'))
   if drive==0:
    self.assertEqual(m.g(UI['_mu_result']),2);press(self,m,ord('d')) # B's unrelated dirty working image is explicitly discarded.
   self.assertEqual(m.g(UI['_mu_result']),7)
   keys(m,bytes(8));loop(self,m);ncmd=L.bulk_model_commands(m.m);safeREU=reu(m,0,4194304);keys(m,bytes([2,0,0,0,0,0,0,0]));L.dos64_step(m.m)
   r=L.dos64_run(m.m,FN['fn_take_restart'],10000000);self.assertEqual((r.status,r.regs.pc),(2,FN['fn_take_restart']))
   self.assertEqual(m.g(FN['ready']),0xa5);r=L.dos64_run(m.m,BR['modal_safe_idle'],10000000);self.assertEqual((r.status,r.regs.pc),(2,BR['modal_safe_idle']));self.assertEqual(m.g(FN['ready']),0);self.assertEqual(m.g(BE['br_safe']),1);self.assertEqual(m.g(BE['br_resume']),0);self.assertEqual(m.g(UI['_mu_result']),6);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g('hdb_online'),0);self.assertEqual(L.bulk_model_open(m.m,target),0);self.assertEqual(L.bulk_model_commands(m.m)-ncmd,1);self.assertEqual([L.bulk_model_command(m.m,ncmd,k)for k in range(2)],[target,3]);self.assertEqual(reu(m,0,4194304),safeREU);self.assertEqual(m.get(128,96),high);self.assertEqual(m.bytes(prefix+b'C.IMG',len(HD)),HD)
   keys(m,bytes([0,0,2,0,0,0,0,0]));r=L.dos64_run(m.m,0x0300,100000);self.assertEqual(r.status,3);self.assertEqual(m.g(UI['_mu_result']),6);self.assertEqual(L.bulk_model_commands(m.m)-ncmd,1);self.assertEqual(m.g('dos64_native_diag'),0xe1)
   extra.append({'target':target,'drive':drive,'bank':bank,'actualCIA_S_jobs':out,'Finish_private_ready_consumed':True,'one_known_CLOSE':True,'SafeUI_noResume':True,'FILES25_HD129_HDB47_high96_full4M':True,'Finish_full4M_exact':True})
  finally:m.close()
 def test_repeated_S_C1_B38_then_Finish(self):self.chain(1,1,0x10)
 def test_repeated_S_C2_A18_then_Finish(self):self.chain(2,0,0x18)

suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Composition),unittest.defaultTestLoader.loadTestsFromTestCase(Versioned),unittest.defaultTestLoader.loadTestsFromTestCase(Faults),Tests('test_08_public_event_forgery_after_take_uses_private_capture'),FinishUI('test06_public_SAFE_reply_is_not_private_intent'),FinishUI('test05_unknown_CLOSE_never_safe_or_retry')])
r=unittest.TextTestRunner(verbosity=2).run(suite)
(P/'RUNTIME_VERSIONED_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'oracle':oracle,'Finish_imports':len(imports),'CPU_loads':loaded,'versioned_records':results,'composition':extra,'scope':'actual runtime/CIA/ordinaryS+Finish; allUNITabsent; synthetic mountedmedia, no coldSTART/DOS/device'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
