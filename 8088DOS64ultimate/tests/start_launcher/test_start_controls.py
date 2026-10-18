import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-start-controls-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,json,unittest
from test_start import Start,SYMS,L
from test_controller import Controller
from test_actual import bind,ptr,u8,u16,u32,Regs
bind('bulk_model_seed_open',None,[ptr,u8,C.c_char_p,u8,u32]);bind('dos64_host_input_model_keys',None,[ptr,ptr]);bind('dos64_cia_clock_step',None,[ptr,u32]);bind('dos64_cia_clock_seed',None,[ptr,u16,u16]);bind('dos64_uci_model_stale',None,[ptr,u8]);bind('dos64_uci_model_block',None,[ptr,ptr,C.c_size_t,ptr,C.c_size_t])
REPORT={}
class Controls(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def stop(self):
  r=self.f.run(SYMS['sf_entry_idle']);assert not r.status,(r.status,hex(r.regs.pc));self.f.startup_guard();assert self.f.byte('_sf_status')==3
 def seedold(self,targets):
  f=self.f;self.old=[]
  for t in targets:
   path=b'/usb1/Old Session/'+str(t).encode()+b'.BIN';data=b'old file unchanged'*21;L.bulk_model_seed(f.m,path,data,len(data));L.bulk_model_seed_open(f.m,t,path,3,7);self.old.append((path,data))
 def oldunchanged(self):
  for path,data in self.old:
   out=C.create_string_buffer(len(data));assert L.bulk_model_read(self.f.m,path,out,len(data));self.assertEqual(out.raw,data)
 def test_invalid_owner_root_and_alias_have_zero_wire_even_old_handles(self):
  for owner,home in [(0,b'/usb1/home'),(0xa5,b'/'),(0xa5,b'/usb1/../home')]:
   self.f=Start(owner,home);self.seedold([1,2]);self.stop();self.assertEqual(L.bulk_model_commands(self.f.m),0);self.assertEqual([L.bulk_model_open(self.f.m,t) for t in [1,2]],[1,1]);self.oldunchanged();self.f.close();del self.f
  REPORT[self._testMethodName]={'cases':3,'wire':0,'unknown_channels_unclaimed':True}
 def test_true_entry_seeded_each_and_both_recovery_precedes_first_OPEN(self):
  rows=[]
  for targets in [[1],[2],[1,2]]:
   self.f=Start(0xa5);f=self.f;self.seedold(targets);f.seedfiles(True);r=f.run(SYMS['trampoline_start']);assert r.regs.pc==0x0200,(r.status,hex(r.regs.pc));f.startup_guard()
   self.assertEqual([(L.bulk_model_command(f.m,i,0),L.bulk_model_command(f.m,i,1)) for i in range(3)],[(1,3),(2,3),(1,2)]);self.assertEqual(L.bulk_model_commands(f.m),22);self.assertEqual([L.bulk_model_open(f.m,t) for t in [1,2]],[0,0]);self.oldunchanged();rows.append({'seeded':targets,'wire':22,'lc':f.read('_lc_result',3).hex()});f.close();del self.f
  REPORT[self._testMethodName]=rows
 def test_RUN_STOP_during_recovery_closes_both_without_OPEN(self):
  self.f=Start(0xa5);f=self.f;self.seedold([1,2]);f.seedfiles(True)
  r=f.run(SYMS['_sc_poll']);assert r.regs.pc==SYMS['_sc_poll'];keys=bytes(7)+b'\x80';L.dos64_host_input_model_keys(f.m,keys);self.stop()
  self.assertEqual(L.bulk_model_commands(f.m),2);self.assertEqual([L.bulk_model_open(f.m,t) for t in [1,2]],[0,0]);self.assertEqual(f.byte('_sf_error'),2);self.assertEqual(f.byte('_sc_error'),1);self.oldunchanged()
  REPORT[self._testMethodName]={'wire':2,'safety_closed':3,'sf_error':2,'sc_error':1}
 def test_RUN_STOP_during_LOAD_closes_and_never_handoffs(self):
  self.f=Start(0xa5);f=self.f;f.seedfiles(True)
  # Pause each real frontend poll until actual LOAD command has been pushed.
  for _ in range(2000):
   r=f.run(SYMS['_lc_poll']);assert r.regs.pc==SYMS['_lc_poll'];
   if L.bulk_model_commands(f.m)>=5:break
   # Advance one native instruction past the sentinel by stopping at sf_sample.
   r=f.run(SYMS['sf_sample']);assert r.regs.pc==SYMS['sf_sample']
  else:raise AssertionError('LOAD not reached')
  L.dos64_host_input_model_keys(f.m,bytes(7)+b'\x80');self.stop();self.assertEqual(f.byte('_sf_error'),2);self.assertEqual(f.read('_lc_result',2),b'\x03\x08');self.assertEqual(L.bulk_model_open(f.m,1),0);self.assertEqual(f.reu(0x3ff005,1),b'\0')
  REPORT[self._testMethodName]={'wire':L.bulk_model_commands(f.m),'lc':f.read('_lc_result',16).hex()}
 def test_clock_failure_during_recovery_cancels_with_safe_closure(self):
  self.f=Start(0xa5);f=self.f;self.seedold([1,2]);r=f.run(SYMS['_sc_poll']);assert r.regs.pc==SYMS['_sc_poll'];L.dos64_cia_clock_step(f.m,262144);self.stop();self.assertEqual(f.byte('_sf_error'),1);self.assertEqual(f.byte('_sc_error'),1);self.assertEqual(L.bulk_model_commands(f.m),2);self.assertEqual([L.bulk_model_open(f.m,t) for t in [1,2]],[0,0]);self.oldunchanged()
  REPORT[self._testMethodName]={'wire':2,'clock_failure':1,'cancel_safe_closed':3}
 def test_true_clock_wrap_during_successful_loading(self):
  self.f=Start(0xa5);f=self.f;f.seedfiles(True);r=f.run(SYMS['_ps_clock_poll']);assert r.regs.pc==SYMS['_ps_clock_poll'];L.dos64_cia_clock_seed(f.m,1023,2)
  r=f.run(SYMS['_sc_begin']);assert r.regs.pc==SYMS['_sc_begin'];initial=int.from_bytes(f.read('_sc_now',2),'little');assert initial>=65530
  r=f.run(SYMS['trampoline_start']);assert r.regs.pc==0x0200,(r.status,hex(r.regs.pc));f.startup_guard();final=int.from_bytes(f.read('_lc_now',2),'little');self.assertLess(final,initial);self.assertEqual(L.bulk_model_commands(f.m),22);self.assertEqual(f.read('_lc_result',2),b'\x05\0')
  REPORT[self._testMethodName]={'initial_ticks':initial,'final_ticks':final,'wire':22,'wrap_success':True}
 def test_stale_reset_queue_never_OPENs_and_preserves_unknown(self):
  rows=[]
  for state in [0x10,0x20]:
   self.f=Start(0xa5);f=self.f;self.seedold([1,2]);r=f.run(SYMS['_sc_begin']);assert r.regs.pc==SYMS['_sc_begin']
   if state==0x20:L.dos64_uci_model_block(f.m,None,0,b'00,OK',5)
   L.dos64_uci_model_stale(f.m,state);self.stop();self.assertEqual(L.bulk_model_commands(f.m),0);self.assertEqual(f.byte('_sc_error'),2);self.assertEqual(f.byte('_sc_transport'),6);self.assertEqual([L.bulk_model_open(f.m,t) for t in [1,2]],[1,1]);self.oldunchanged();rows.append({'state':state,'wire':0,'error':2,'transport':6});f.close();del self.f
  REPORT[self._testMethodName]=rows
 def test_dynamic_trampoline_partial_DMA_stays_low_without_main_call(self):
  self.f=Start(0xa5);f=self.f;f.seedfiles(True);r=f.run(SYMS['trampoline_start']);assert r.regs.pc==0x0200;f.startup_guard();L.dos64_reu_fail_after(f.m,0,17);r=f.run(SYMS['trampoline_failed'],20000);self.assertEqual(r.status,0);self.assertEqual(r.regs.pc,SYMS['trampoline_failed']);self.assertEqual(L.dos64_peek(f.m,0x3a0b),f.template[0x3a0b-0x0801+2]);REPORT[self._testMethodName]={'pc':r.regs.pc,'failure_before_main_consumer':True}
class Tickets(unittest.TestCase):
 def tearDown(self):self.f.close()
 def stage(self):
  self.f=Controller();f=self.f;f.seed_inputs(True);assert f.call('_lc_begin')==1 and f.finish_lc()[0]==2;return f
 def test_prepared_ticket_rejects_reentry_public_mutation_and_cancel(self):
  rows=[]
  for action in ['prepare_twice','mutate','cancel','consume_twice']:
   if hasattr(self,'f'):self.f.close();del self.f
   f=self.stage();self.assertEqual(f.call('_lc_prepare_handoff'),1)
   if action=='prepare_twice':self.assertEqual(f.call('_lc_prepare_handoff'),0)
   if action=='mutate':f.poke('_d64_release_output',0);self.assertEqual(f.call('_lc_consume_handoff'),0)
   if action=='cancel':f.call('_lc_cancel');self.assertEqual(f.call('_lc_consume_handoff'),0)
   if action=='consume_twice':self.assertEqual(f.call('_lc_consume_handoff'),1);self.assertEqual(f.call('_lc_consume_handoff'),0)
   self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertNotEqual(f.lc()[1],0);self.assertEqual(f.call('_lc_begin'),0);rows.append({'action':action,'lc':f.read('_lc_result',3).hex()})
  REPORT[self._testMethodName]=rows
if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [Controls,Tickets]]);r=unittest.TextTestRunner(verbosity=2).run(suite);(P.parent/'START_CONTROLS_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
