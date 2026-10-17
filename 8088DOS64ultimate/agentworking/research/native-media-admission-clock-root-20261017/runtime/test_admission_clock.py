from pathlib import Path
import sys,os
sys.dont_write_bytecode=True
os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import ctypes as C,json,unittest
from controller_fixture import initial
from fixture_base import L,symbols,load,labels
from test_online_save import HD

P=Path(__file__).resolve().parent
for n,r,a in [('dos64_cia_clock_seed',None,[C.c_void_p,C.c_uint16,C.c_uint16]),('dos64_cia_clock_reads',C.c_uint32,[C.c_void_p,C.c_uint8])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
records=[]

class Tests(unittest.TestCase):
 def case(self,worker,kind):
  m,old,f=initial(self,target=2)
  try:
   if worker=='wire':
    table=labels('phase/transaction-wire.labels');load(m,'phase/transaction-wire.prg')
    m.put(table['tw_home'],b'/usb1/Owned\0'.ljust(128,b'\0'))
    for n,v,size in [('tw_mode',2,1),('tw_drive',1,1),('tw_sequence',1,2),('tw_limit',30000,2)]:m.put(table[n],v.to_bytes(size,'little'))
    begin,poll,state='tw_begin','tw_poll','tw_state'
   else:
    table=labels('phase/modal-save.labels');load(m,'phase/modal-save.prg')
    m.p(table['ms_drive'],1);m.put(table['ms_path'],f['path'].ljust(128,b'\0'))
    begin,poll,state='ms_begin','ms_poll','ms_state'
   symbols.update({n:table[n]for n in [begin,poll,state]})
   ctx=m.get('dos64_files_state_start',25);hd=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);hdb=m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']);pos=L.save_model_position(m.m,2);commands=L.bulk_model_commands(m.m)
   m.put('dos64_elapsed_now',b'\x24\x7f');old_now=m.get('dos64_elapsed_now',2);old_ticks=m.get('dos64_host_clock_ticks',4)
   L.dos64_cia_clock_seed(m.m,0xffff,0xfffe)
   L.dos64_cia_clock_step(m.m,1 if kind=='pending_ready'else 0)
   if kind=='owner':m.p('dos64_host_clock_claim',0)
   if kind=='unready':m.p('dos64_host_clock_ready',0)
   if kind=='control':
    # Debug poke bypasses mapped I/O; issue a real CPU STA to stop CIA2 A.
    code=bytes.fromhex('a9008d0edd60');L.dos64_load(m.m,0x0200,code,len(code));symbols['stop_clock']=0x0200;m.call('stop_clock')
   reads=L.dos64_cia_clock_reads(m.m,5)
   r=m.call(begin,2_000_000)
   delta=L.dos64_cia_clock_reads(m.m,5)-reads
   status=m.g('dos64_host_clock_status')
   if kind=='pending_ready':
    self.assertEqual(r.regs.a,1,(worker,status,delta));self.assertEqual(status,0);self.assertGreater(delta,8)
    for count in range(250000):
     s=m.call(state).regs.a
     if s!=1:break
     m.call(poll,2_000_000)
    self.assertEqual(s,2,(worker,s,count,{n:m.g(n)for n in ['dos64_native_diag','dos64_export_state','dos64_export_error','dos64_files_state','dos64_files_error','dos64_uci_state','sav_error','sav_context_phase','dos64_host_clock_status']}));self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(L.save_model_position(m.m,2),pos)
    if worker=='save':self.assertEqual(m.bytes(f['path'],368640),f['working'])
   else:
    self.assertEqual(r.regs.a,0);self.assertEqual(status,{'pending_stalled':4,'owner':1,'unready':2,'control':3}[kind]);self.assertEqual(delta,2048 if kind=='pending_stalled'else 0)
    self.assertEqual(L.bulk_model_commands(m.m),commands);self.assertEqual(m.get('dos64_elapsed_now',2),old_now);self.assertEqual(m.get('dos64_host_clock_ticks',4),old_ticks)
    self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(L.save_model_position(m.m,2),pos)
    self.assertEqual(m.get('hd_state_start',len(hd)),hd);self.assertEqual(m.get('hdb_state_start',len(hdb)),hdb)
   self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old)
   records.append({'worker':worker,'case':kind,'TAHI_reads':delta,'clock_status':status,'actual_native_admission_A':r.regs.a,'completed_poll_count':count if kind=='pending_ready'else None,'C_and_CFG_exact':True})
  finally:m.close()

for worker in ['wire','save']:
 for kind in ['pending_ready','pending_stalled','owner','unready','control']:
  def test(self,w=worker,k=kind):self.case(w,k)
  setattr(Tests,'test_'+worker+'_'+kind,test)

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 (P/'ADMISSION_CLOCK_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':records,'scope':'actual linked WIRE/Save APIs with real modeled CIA sampler; synthetic media, no cold/DOS/physical'},indent=2)+'\n')
 raise SystemExit(not r.wasSuccessful())
