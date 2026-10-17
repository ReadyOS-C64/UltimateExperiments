from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-journal-invoke-test');assert not Path(sys.pycache_prefix).exists()
import unittest,json,ctypes as C,zlib
from test_modal import Menu,SYMS,L
from test_actual import ptr,u32
L.dos64_step.argtypes=[ptr]
G={l.split()[2].lstrip("."):int(l.split()[1],16)for l in(P.parent/"gate/gate.labels").read_text().splitlines()if l.startswith("al ")}
class Journal(Menu):
 def __init__(self,columns=80,gate=True):
  super().__init__(columns)
  self.gate=(P/'START.RCV').read_bytes()if gate is True else gate
  if self.gate is not None:L.bulk_model_seed(self.m,self.home+b'/START.RCV',self.gate,len(self.gate))
 def pending(self,fixture):
  self.home=b'/usb1/Owned';L.dos64_load(self.m,SYMS['_lc_control']+3,self.home.ljust(128,b'\0'),128)
  L.bulk_model_seed(self.m,self.home+b'/START.RCV',self.gate,len(self.gate))
  self.fixture={q.name:q.read_bytes()for q in(P.parent/'inputs/journal-fixtures'/fixture).iterdir()}
  for name,b in self.fixture.items():L.bulk_model_seed(self.m,self.home+b'/'+name.encode(),b,len(b))
 def advance_dispatch(self):
  L.dos64_step(self.m);return self.run(G['_jg_dispatch'])
class Tests(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def test_no_journal_actual_SYS_restores_INO_then_reaches_handoff_40_80(self):
  for col in [40,80]:
   f=self.f=Journal(col);r=f.run(SYMS['trampoline_start'])
   self.assertEqual(r.regs.pc,0x200,(r.status,hex(r.regs.pc),f.read('_lc_result',16).hex()))
   self.assertEqual(f.read('_lc_result',2),b'\5\0');self.assertEqual(L.bulk_model_open(f.m,1),0)
   f.startup_guard()
   self.assertEqual(bytes(L.dos64_peek(f.m,0x6000+i)for i in range(len(f.asset))),f.asset)
   f.close();del self.f
 def test_unknown_CLOSE_never_rearmed_by_resident_failure_or_frontend_drain(self):
  f=self.f=Journal();f.pending('precommit')
  for _ in range(1000):
   r=f.run(G['_jg_dispatch'])
   self.assertEqual(r.regs.pc,G['_jg_dispatch'])
   if f.byte('dos64_files_op')==4 and f.byte('dos64_files_state')==1:break
   L.dos64_step(f.m)
  else:self.fail('no actual pending READ')
  before=L.bulk_model_commands(f.m);L.save_model_fail_close.argtypes=[ptr,C.c_int];L.save_model_fail_close(f.m,1)
  L.dos64_host_input_model_keys(f.m,bytes(7)+b'\x80');L.dos64_step(f.m)
  r=f.run(SYMS['sf_entry_idle']);self.assertEqual(r.status,0)
  (P.parent/'UNKNOWN_CLOSE_DIAG.json').write_text(json.dumps({'before':before,'after':L.bulk_model_commands(f.m),'result':f.read('_lc_result',16).hex(),'open':L.bulk_model_open(f.m,1)},indent=2))
  self.assertEqual(f.read('_lc_result',3),b'\3\13\2')
  after=L.bulk_model_commands(f.m)
  closes=[i for i in range(before,after)if L.bulk_model_command(f.m,i,1)==3]
  self.assertEqual(len(closes),1,(before,after,closes,f.read('_lc_result',16).hex()))
  self.assertEqual(L.bulk_model_open(f.m,1),1)
 def stopped(self,f,error,budget=600_000_000):
  r=f.run(SYMS['sf_entry_idle'],budget);self.assertEqual(r.status,0,(r.status,hex(r.regs.pc)))
  self.assertEqual(f.read('_lc_result',2),bytes([3,error]))
  for at in [0x3da005,0x3ff005,0x3ff505]:self.assertEqual(f.reu(at,1),b'\0')
  self.assertEqual(f.byte('_sf_status'),3)
 def unchanged_files(self,f):
  for name,data in f.fixture.items():
   path=f.home+b'/'+name.encode();self.assertEqual(L.bulk_model_size(f.m,path),len(data));v=C.create_string_buffer(len(data));self.assertEqual(L.bulk_model_read(f.m,path,v,len(data)),1);self.assertEqual(v.raw,data)
 def test_original_native_pending_OLD_MISSING_NEW_blocks_before_normal_CFG_acquisition(self):
  for fixture,kind in [('precommit',1),('missing',3),('committed',2)]:
   f=self.f=Journal();f.pending(fixture);before=f.reu(0,0x400000);self.stopped(f,11,1_300_000_000);f.startup_guard()
   self.assertEqual(L.dos64_peek(f.m,G['_jg_state_observed']),2);self.assertEqual(L.dos64_peek(f.m,G['_jg_error_observed']),0)
   self.assertEqual(L.bulk_model_open(f.m,1),0);self.unchanged_files(f)
   after=f.reu(0,0x400000);allowed=[(0x3da005,0x3da006),(0x3e0600,0x3e0b04),(0x3e1000,0x3e1240),(0x3e8000,0x3e8000+len(f.gate)),(0x3ff005,0x3ff006),(0x3ff505,0x3ff506)]
   at=0
   for lo,hi in allowed:self.assertEqual(before[at:lo],after[at:lo]);at=hi
   self.assertEqual(before[at:],after[at:]);self.assertEqual(f.reu(0x3e0600,1284),f.fixture['DOS64.JRN'])
   for i in range(L.bulk_model_commands(f.m)):self.assertIn(L.bulk_model_command(f.m,i,1),(2,3,4,7,0x21))
   f.close();del self.f
 def test_missing_short_and_corrupted_RCV_never_enters_gate_or_CFG(self):
  original=(P/'START.RCV').read_bytes()
  for body,error in [(None,2),(original[:-1],3),(original[:100]+bytes([original[100]^1])+original[101:],4)]:
   f=self.f=Journal(gate=body);self.stopped(f,error);self.assertEqual(L.bulk_model_open(f.m,1),0)
   self.assertEqual(bytes(L.dos64_peek(f.m,0x9000+i)for i in range(128)),b'\xa5'*128)
   f.close();del self.f
 def test_bad_gate_capsule_refuses_file_open_after_startup_closure(self):
  for offset in [0,6,12,14,16,18,23]:
   f=self.f=Journal();at=SYMS['_sj_gate_spec']+offset;L.dos64_poke(f.m,at,L.dos64_peek(f.m,at)^1)
   self.stopped(f,5 if offset!=6 else 3);self.assertEqual(L.bulk_model_commands(f.m),2 if offset!=6 else 5)
   f.close();del self.f
 def test_STOP_during_native_journal_READ_closes_once_and_blocks_boot(self):
  f=self.f=Journal();f.pending('precommit')
  for _ in range(1000):
   r=f.run(G['_jg_dispatch']);self.assertEqual(r.regs.pc,G['_jg_dispatch'])
   if f.byte('dos64_files_op')==4 and f.byte('dos64_files_state')==1:break
   L.dos64_step(f.m)
  else:self.fail('no actual pendingREAD')
  L.dos64_host_input_model_keys(f.m,bytes(7)+b'\x80');L.dos64_step(f.m);self.stopped(f,11)
  self.assertEqual(f.read('_lc_result',3),b'\3\13\0');self.assertEqual(L.bulk_model_open(f.m,1),0)
  self.assertEqual(L.dos64_peek(f.m,G['_jg_error_observed']),5);self.unchanged_files(f)
 def test_failed_native_clock_during_gate_never_rearms_or_boots(self):
  f=self.f=Journal();f.pending('precommit')
  for _ in range(1000):
   r=f.run(G['_jg_dispatch']);self.assertEqual(r.regs.pc,G['_jg_dispatch'])
   if f.byte('dos64_files_op')==4 and f.byte('dos64_files_state')==1:break
   L.dos64_step(f.m)
  else:self.fail('no actual pendingREAD')
  L.dos64_cia_clock_step.argtypes=[ptr,u32];L.dos64_cia_clock_step(f.m,262144);L.dos64_step(f.m);self.stopped(f,11)
  self.assertEqual(L.dos64_peek(f.m,G['_jg_error_observed']),6)
 def test_failed_first_RCV_install_FETCH_does_not_execute_recovery(self):
  f=self.f=Journal();r=f.run(SYMS['_overlay_poll']);self.assertEqual(r.regs.pc,SYMS['_overlay_poll'])
  L.dos64_reu_fail_after(f.m,0,1);self.stopped(f,7)
  self.assertEqual(bytes(L.dos64_peek(f.m,0x9000+i)for i in range(128)),b'\xa5'*128)
 def test_bad_journal_crc_from_real_START_blocks_without_changing_files(self):
  f=self.f=Journal();f.pending('precommit');b=bytearray(f.fixture['DOS64.JRN']);b[-1]^=1;f.fixture['DOS64.JRN']=bytes(b);L.bulk_model_seed(f.m,f.home+b'/DOS64.JRN',bytes(b),len(b))
  self.stopped(f,11);self.assertEqual(L.dos64_peek(f.m,G['_jg_error_observed']),4)
  self.assertEqual(L.bulk_model_open(f.m,1),0);self.unchanged_files(f)
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'JOURNAL_START_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun},indent=2)+'\n');sys.exit(not r.wasSuccessful())
