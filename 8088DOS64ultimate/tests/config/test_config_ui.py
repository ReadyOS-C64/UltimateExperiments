from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-config-ui-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,unittest
from config_fixture import F,L,Regs,REPORT,cfg
P=Path(__file__).resolve().parent;assert Path.cwd()==P
class UI:
 def __init__(self,stale=(),auto=True):
  self.f=F(stale,auto);self.state=0
  self.directory(b'/',[(16,b'Existing'),(16,b'Release'),(16,b'New launch')])
  for path in [b'/Existing',b'/Release',b'/New launch']:self.directory(path,[])
  self.original=cfg(b'/Existing',ro=3);self.oldstart=b'UNMODIFIED START'+bytes(18432-16)
  L.bulk_model_seed(self.f.m,b'/Existing/DOS64.CFG',self.original,len(self.original))
  L.bulk_model_seed(self.f.m,b'/Existing/START.PRG',self.oldstart,len(self.oldstart))
 def close(self):self.f.close()
 def directory(self,path,rows):
  L.dir_model_path(self.f.m,path)
  for attr,name in rows:L.dir_model_row(self.f.m,path,attr,name,len(name))
 def begin(self,timeout=1000):self.f.write('_cg_request',b'\xa5'+struct.pack('<IH',0x400000,timeout));return self.f.call('_cg_begin')
 def poll(self):L.dos64_cia_clock_advance(self.f.m,1024);self.f.call('_cg_poll');self.state=self.f.call('_cg_state');return self.state
 def ready(self):
  for _ in range(3000):
   self.poll()
   if self.state not in (1,3) and not(self.state==2 and self.f.read('_db_result',1)==b'\1'):return self.state
  raise AssertionError('bounded UI')
 def key(self,row,col,shift=False):
  key=bytearray(8);key[row]|=1<<col
  if shift:key[1]|=128
  L.dos64_host_input_model_keys(self.f.m,bytes(key));self.poll();L.dos64_host_input_model_keys(self.f.m,bytes(8));self.poll();return self.ready()
 def inspect(self):
  assert self.begin()==1;assert self.ready()==2
  self.key(0,1);assert self.f.read('_db_selected_path',128).split(b'\0')[0]==b'/Existing'
  return self.key(0,4)
 def finish(self,columns=80):
  assert self.inspect()==4
  if columns==40:self.key(0,7,True)
  self.key(0,1) # release folder browser
  self.key(0,7);self.key(0,1);self.key(0,4)
  self.key(0,7);self.key(0,7);self.key(0,1);self.key(0,4)
  assert self.state==5
  return self.key(0,1)
 def receipt(self):
  assert self.f.call('_cg_get')==1
  b=self.f.read('_cg_receipt',429)
  return {'session':int.from_bytes(b[:2],'little'),'identity':int.from_bytes(b[2:6],'little'),'capacity':int.from_bytes(b[6:10],'little'),'paths':[b[10+i*128:138+i*128].split(b'\0')[0]for i in range(3)],'columns':b[394],'ini_length':int.from_bytes(b[395:397],'little'),'ini':b[397:429]}
class Config(unittest.TestCase):
 def make(self,**kw):u=UI(**kw);self.addCleanup(u.close);return u
 def test_real_CIA_full_selection_prefs_private_receipt_and_no_mutation(self):
  for columns in [40,80]:
   u=self.make(stale=(1,2));f=u.f
   self.assertEqual(u.finish(columns),6);self.assertEqual(f.call('_cg_error'),0);self.assertEqual(f.call('_cg_closed_quiet'),1)
   r=u.receipt();self.assertEqual(r['paths'],[b'/Existing',b'/Release',b'/New launch']);self.assertEqual(r['columns'],columns)
   self.assertEqual(r['ini'],b'[emulator]\r\ninitial_columns='+str(columns).encode()+b'\r\n');self.assertEqual(r['ini_length'],32)
   self.assertEqual(r['identity'],zlib.crc32(u.original[:572]));self.assertEqual(r['capacity'],0x400000)
   self.assertEqual(f.commands(),[b'\1\3',b'\2\3',b'\1\2',b'\1\7',b'\1\4',b'\1\4',b'\1\4',b'\1\4',b'\1\3'])
   self.assertEqual([L.bulk_model_open(f.m,t)for t in [1,2]],[0,0]);self.assertEqual(L.bulk_model_command(f.m,2,2),1)
   for path,data in [(b'/Existing/DOS64.CFG',u.original),(b'/Existing/START.PRG',u.oldstart),(b'/Old',b'UNCHANGED')]:
    out=C.create_string_buffer(len(data));self.assertEqual(L.bulk_model_read(f.m,path,out,len(data)),1);self.assertEqual(out.raw,data)
   f.write('_cg_receipt',bytes(429));f.write('_ri_receipt',bytes(710));f.write('_cg_result',b'\7'+bytes(7));self.assertEqual(u.receipt(),r)
   REPORT['success_'+str(columns)]={**r,'paths':[x.decode()for x in r['paths']],'ini':r['ini'].decode()}
 def test_startup_cancel_never_browses_or_mints_private_receipt(self):
  u=self.make(stale=(1,2));f=u.f;self.assertEqual(u.begin(),1);u.key(7,7)
  self.assertEqual(u.state,7);self.assertEqual(f.call('_cg_error'),5);self.assertEqual(L.dir_model_commands(f.m),0)
  self.assertEqual(f.call('_cg_get'),0);self.assertEqual(f.call('_ri_attach'),0);self.assertEqual(f.call('_sc_ready'),0)
 def test_public_done_and_selected_path_cannot_bypass_active_directory(self):
  u=self.make();f=u.f;u.begin()
  for _ in range(100):
   u.poll()
   if u.state==2:break
  f.write('_cg_result',b'\6'+bytes(6)+b'\xa5');f.write('_db_result',b'\2'+bytes(9));f.write('_db_selected_path',b'/Forged'.ljust(128,b'\0'))
  self.assertEqual(f.call('_cg_get'),0);u.ready();u.key(0,1);u.key(0,4);self.assertEqual(u.state,4)
  self.assertEqual(f.commands()[:3],[b'\1\3',b'\2\3',b'\1\2'])
 def test_bad_existing_CFG_is_readonly_terminal_with_known_cleanup(self):
  u=self.make();bad=bytearray(u.original);bad[10]^=1;L.bulk_model_seed(u.f.m,b'/Existing/DOS64.CFG',bytes(bad),len(bad))
  self.assertEqual(u.inspect(),7);self.assertEqual(u.f.call('_cg_error'),4);self.assertEqual(u.f.call('_cg_closed_quiet'),1);self.assertEqual(u.f.call('_cg_get'),0)
 def test_attach_requires_real_startup_and_no_active_UI_lease_and_is_one_shot(self):
  u=self.make();f=u.f;self.assertEqual(f.call('_ri_boot'),0);self.assertEqual(f.call('_ri_attach'),0)
  f.write('_sc_state',b'\2');f.write('_sc_closed',b'\3');self.assertEqual(f.call('_ri_attach'),0)
  self.assertEqual(f.call('_sc_begin',0xa5),1)
  for i in range(300):
   f.write('_sc_now',struct.pack('<H',i));s=f.call('_sc_poll')
   if s!=1:break
  self.assertEqual(s,2);self.assertEqual(f.call('_sc_ready'),1);self.assertEqual(f.call('_bc_ui_acquire'),1)
  self.assertEqual(f.call('_ri_attach'),0);self.assertEqual(f.call('_bc_files_closed'),0)
  self.assertEqual(f.call('_bc_ui_release'),1);self.assertEqual(f.call('_ri_attach'),1);self.assertEqual(f.call('_ri_attach'),0)
  self.assertEqual(f.call('_ri_boot'),0);self.assertEqual(f.call('_sc_begin',0xa5),0);self.assertEqual(f.commands(),[b'\1\3',b'\2\3'])
 def test_lease_after_done_refuses_getter_without_destroying_private_choices(self):
  u=self.make();self.assertEqual(u.finish(),6);before=u.receipt();f=u.f
  self.assertEqual(f.call('_bc_ui_acquire'),1);f.write('_cg_result',b'\6'+bytes(6)+b'\xa5');self.assertEqual(f.call('_cg_get'),0)
  self.assertEqual(f.call('_bc_ui_release'),1);self.assertEqual(u.receipt(),before)
 def test_late_directory_error_wins_same_poll_RunStop(self):
  u=self.make();f=u.f;u.directory(b'/',[(16,('Folder %02d'%i).encode())for i in range(25)])
  L.dir_model_fault(f.m,0x14,24,1);L.fw_stop_after_error_write(f.m,f.labels['_db_result']+1)
  self.assertEqual(u.begin(),1);self.assertEqual(u.ready(),7);self.assertEqual(f.call('_cg_error'),3)
  self.assertEqual(f.read('_cg_result',8)[2],4);self.assertEqual(f.call('_cg_get'),0);self.assertEqual(f.call('_cg_closed_quiet'),1)
  self.assertEqual(f.commands(),[b'\1\3',b'\2\3'])
 def test_short_CFG_READ_first_cause_and_final_CLOSE_failure_remain_truthful(self):
  for fail,short in [(-1,5),(9,-1)]:
   u=self.make();f=u.f;L.bulk_model_faults(f.m,fail,short,-1,0,-1);L.fw_stop_after_error_write(f.m,f.labels['_ri_result']+1)
   self.assertEqual(u.inspect(),7);self.assertEqual(f.call('_cg_error'),4);self.assertEqual(f.read('_cg_result',8)[2],2)
   self.assertEqual(f.call('_cg_get'),0);self.assertEqual(f.commands().count(b'\1\3'),2)
   self.assertEqual(f.call('_cg_closed_quiet'),0 if fail==9 else 1)
 def test_clock_failure_stays_first_and_pending_drain_is_bounded(self):
  u=self.make();f=u.f;u.begin()
  for _ in range(100):
   u.poll()
   if u.state==2:break
  L.dos64_uci_model_stuck(f.m,1);L.dos64_cia_clock_step(f.m,0x40000);u.poll();self.assertEqual(f.call('_cg_error'),6)
  L.dos64_cia_clock_step(f.m,0);n=0
  while u.state!=7 and n<300:u.poll();n+=1
  self.assertEqual(u.state,7);self.assertLessEqual(n,256);self.assertEqual(f.call('_cg_error'),6);self.assertEqual(f.call('_cg_get'),0);self.assertEqual(f.call('_cg_closed_quiet'),0)
 def test_actual_SYS_entry_runs_without_injected_component_calls(self):
  u=self.make(stale=(1,2),auto=False);f=u.f
  L.dos64_poke(f.m,0,0x2f);L.dos64_poke(f.m,1,0x37)
  # The native BASIC SYS address establishes both C runtime and engine once.
  L.dos64_set_regs(f.m,Regs(0x80d,0xfd,0x71,0x82,0x93,0x24,0,0))
  stop=f.labels['config_poll_return'];loop=f.labels['config_poll_loop']
  for i in range(500):
   L.dos64_clear_writes(f.m);r=L.dos64_run(f.m,stop,5000000);self.assertEqual((r.status,r.regs.pc,r.regs.sp),(2,stop,0xfd))
   self.assertEqual(L.browser_bad_write(f.m,f.guard),65536)
   # State is read only after the real poll frame fully returned.
   if f.read('_cg_result',8)[0]==2 and f.read('_db_result',1)==b'\2':break
   r=L.dos64_run(f.m,loop,1000);self.assertEqual((r.status,r.regs.pc,r.regs.sp),(2,loop,0xfd));L.dos64_cia_clock_advance(f.m,1024)
  else:self.fail('native SYS bounded startup/browser')
  self.assertEqual(f.commands(),[b'\1\3',b'\2\3']);self.assertGreater(L.dir_model_commands(f.m),0)
  self.assertEqual(L.browser_bank(f.m)&0x7ff,0x52f)
 def test_new_preference_label_is_honest_and_old_INI_is_untouched(self):
  u=self.make();f=u.f;old=b'[emulator]\r\ninitial_columns=40\r\n';L.bulk_model_seed(f.m,b'/Existing/DOS64.INI',old,len(old))
  self.assertEqual(u.inspect(),4);self.assertEqual(f.read('_cg_result',8)[6],80)
  glyph=lambda t:bytes(c-96 if 97<=c<=122 else c for c in t)
  self.assertEqual(bytes(L.dos64_peek(f.m,0x400+2*40+i)for i in range(28)),glyph(b'New initial DOS text columns'))
  self.assertEqual(bytes(L.dos64_peek(f.m,0x400+10*40+i)for i in range(34)),glyph(b'New setting; old INI is unchanged.'))
  out=C.create_string_buffer(len(old));self.assertEqual(L.bulk_model_read(f.m,b'/Existing/DOS64.INI',out,len(old)),1);self.assertEqual(out.raw,old)
  self.assertEqual(len(f.commands()),9)
 def test_actual_browser_names_are_unambiguous_raw_choices_and_paginated(self):
  names=[b'A_B',b'A-B',b'A%5FB',b'A{B',b'A[B'];encoded=[b'A%5FB',b'A-B',b'A%255FB',b'A%7BB',b'A[B']
  for selected in range(5):
   u=self.make();f=u.f;u.directory(b'/',[(16,n)for n in names])
   for n in names:u.directory(b'/'+n,[])
   u.begin();self.assertEqual(u.ready(),2)
   for i,e in enumerate(encoded):self.assertEqual(bytes(L.dos64_peek(f.m,0x400+(5+i)*40+2+j)for j in range(len(e))),bytes(27 if c==91 else c for c in e))
   for _ in range(selected):u.key(0,7)
   u.key(0,1);self.assertEqual(f.read('_db_selected_path',128).split(b'\0')[0],b'/'+names[selected])
  u=self.make();f=u.f;u.directory(b'/',[(16,('Folder%02d'%i).encode())for i in range(25)]);u.begin();u.ready()
  u.key(0,6);self.assertEqual(f.read('_db_result',1),b'\2')
  # Row0 on page2 is raw Folder12, rather than a stale first-page selection.
  u.key(0,1);self.assertEqual(f.read('_db_selected_path',128).split(b'\0')[0],b'/Folder12')
 def test_reserved_publisher_state_and_complete_REU_remain_untouched(self):
  u=self.make();f=u.f;at=f.labels['__CONFIG_PUBSTATE_RUN__'];size=f.labels['__CONFIG_PUBSTATE_SIZE__'];self.assertEqual(size,1100)
  pattern=bytes((i*73+19)&255 for i in range(size));L.dos64_load(f.m,at,pattern,size)
  before=C.create_string_buffer(0x400000);after=C.create_string_buffer(0x400000);self.assertEqual(L.dos64_reu_read(f.m,0,before,0x400000),1)
  self.assertEqual(u.finish(40),6);self.assertEqual(bytes(L.dos64_peek(f.m,at+i)for i in range(size)),pattern)
  self.assertEqual(L.dos64_reu_read(f.m,0,after,0x400000),1);self.assertEqual(before.raw,after.raw)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Config));(P.parent/'UI_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
