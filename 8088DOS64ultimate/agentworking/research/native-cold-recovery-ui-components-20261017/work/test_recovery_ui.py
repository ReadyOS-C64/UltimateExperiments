from pathlib import Path
import sys,os,json,ctypes as C,zlib,struct,unittest,time
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-cold-ui-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
from test_modal import Menu,SYMS,L
from test_actual import Regs,ptr
G={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P.parent/'gate/gate.labels').read_text().splitlines()if l.startswith('al ')}
records=[]
def fat(text):
 b=bytearray(368640);b[:11]=b'\xeb\x3c\x90SYNTH   ';struct.pack_into('<HBHBHHBHHHI',b,11,512,2,1,2,112,720,0xfd,2,9,2,0);b[510:512]=b'\x55\xaa'
 for s in [1,3]:b[s*512:s*512+6]=b'\xfd\xff\xff\xff\x0f\0'
 b[2560:2571]=b'HELLO   TXT';b[2571]=32;struct.pack_into('<HI',b,2586,2,len(text));b[6144:6144+len(text)]=text
 return bytes(b)
class Cold(Menu):
 def __init__(self,case='precommit',worker=True):
  super().__init__();self.home=b'/usb1/Owned';L.dos64_load(self.m,SYMS['_lc_control']+3,self.home.ljust(128,b'\0'),128)
  self.gate=(P/'START.RCV').read_bytes();self.worker=(P/'START.RFW').read_bytes()if worker is True else worker
  self.original={q.name:q.read_bytes()for q in(P.parent/'inputs/journal-fixtures'/case).iterdir()}
  for n,b in self.original.items():self.seedfile(n,b)
  for n,b in [('START.RCV',self.gate),('START.RFW',self.worker),('START.INO',self.asset),('DOS64.INI',self.ini),('DOS64.REL',self.rel),('DOS64.PRG',self.main),('DOS64.MNU',self.menu)]:
   if b is not None:self.seedfile(n,b)
  a=fat(b'ORIGINAL A\r\n');b=fat(b'ORIGINAL B\r\n');assert zlib.crc32(a)==0x2ee4e4ab
  for n,b in [(b'/usb1/Media/A.IMG',a),(b'/sd/Media/B.IMG',b)]:L.bulk_model_seed(self.m,n,b,len(b))
  self.before=self.reu(0,0x400000)
 def seedfile(self,name,b):L.bulk_model_seed(self.m,self.home+b'/'+name.encode(),b,len(b))
 def file(self,n):
  name=self.home+b'/'+n.encode();size=L.bulk_model_size(self.m,name)
  if size==0xffffffff:return None
  b=C.create_string_buffer(size);assert L.bulk_model_read(self.m,name,b,size);return b.raw
 def advance(self,sym,budget=1_300_000_000):
  L.dos64_step(self.m);target=SYMS.get(sym,sym);r=self.run(target,budget);assert r.status in (0,2) and r.regs.pc==target,(r.status,hex(r.regs.pc),hex(target));return r
 def keys(self,row=None,col=None):
  matrix=bytearray(8)
  if row is not None:matrix[row]=1<<col
  L.dos64_host_input_model_keys(self.m,bytes(matrix))
 def prompt(self):
  r=self.run(SYMS['sf_recovery_idle'],1_300_000_000);assert r.status in (0,2) and r.regs.pc==SYMS['sf_recovery_idle'],(r.status,hex(r.regs.pc),self.read('_lc_result',16).hex())
  assert self.read('_lc_result',3)==b'\6\0\0';assert self.byte('_sf_status')==1
  assert L.dos64_peek(self.m,G['_jg_state_observed'])==2
  for at in [0x3da005,0x3ff005,0x3ff505]:assert self.reu(at,1)==b'\0'
  for n,b in self.original.items():assert self.file(n)==b
  assert all(L.bulk_model_command(self.m,i,1)!=10 for i in range(L.bulk_model_commands(self.m)))
  self.keys(2,4);r=self.advance('sf_recovery_confirm',2_000_000);assert r.status in (0,2)
  self.keys();r=self.advance('sf_recovery_confirm',2_000_000);assert r.status in (0,2)
  return r
 def confirm(self):
  if getattr(self,'human_delay',0):
   L.dos64_cia_clock_advance.argtypes=[ptr,C.c_uint32];L.dos64_cia_clock_advance(self.m,self.human_delay*1024)
  self.keys(0,1);r=self.advance('_lc_recovery_begin',2_000_000);assert r.status in (0,2)
  self.keys()
 def stopped(self):
  r=self.advance('sf_entry_idle');assert r.status==0,(r.status,hex(r.regs.pc),self.read('_lc_result',16).hex());assert self.byte('_sf_status')==3
  for a in [0x3da005,0x3ff005,0x3ff505]:assert self.reu(a,1)==b'\0'
  return r
 def complete(self):
  self.prompt();self.confirm()
  r=self.advance(0xa000);assert r.status in (0,2),(r.status,hex(r.regs.pc));assert bytes(L.dos64_peek(self.m,0xa000+i)for i in range(len(self.worker)))==self.worker
  self.cpu_guard(allow_install=True);L.dos64_clear_writes(self.m)
  # This is the first restored RCV dispatch, after every RFW frame returned.
  r=self.advance(G['_jg_dispatch']);assert r.status in (0,2),(r.status,hex(r.regs.pc),self.read('_lc_result',16).hex())
  assert r.regs.a==0 # fresh init selector, not a fabricated DONE/boot flag
  assert L.dos64_peek(self.m,G['_jg_initialized'])==0
  assert bytes(L.dos64_peek(self.m,0x6000+i)for i in range(len(self.gate)))==self.gate
  j=self.original['DOS64.JRN'];assert self.file('DOS64.CFG')==j[704:1280];assert self.file('S0001.OLD')==j[128:704];assert self.file('S0001.JRN')==j
  for n in ['DOS64.JRN','DOS64.NEW','DOS64.OLD']:assert self.file(n)is None
  assert self.file('SAVE0001.IMG')==self.original['SAVE0001.IMG']
  assert L.bulk_model_open(self.m,1)==0
  # Fresh original RCV NONE validation is the only route to normal CFG/INO.
  r=self.advance('trampoline_start');assert r.status in (0,2),(r.status,hex(r.regs.pc),self.read('_lc_result',16).hex());assert self.read('_lc_result',3)==b'\5\0\0'
  assert self.reu(0x3ff005,1)==b'\xa5' and self.reu(0x3ff505,1)==b'\xa5'
  assert bytes(L.dos64_peek(self.m,0x6000+i)for i in range(len(self.asset)))==self.asset
  assert self.reu(0x380000,368640)==self.before[0x380000:0x3da000]
  assert self.reu(0x3f4000,0x4000)==self.before[0x3f4000:0x3f8000]
  assert L.bulk_model_open(self.m,1)==0
  assert self.read('sp',2)==b'\xff\xcf'
  assert (L.dos64_peek(self.m,0),L.dos64_peek(self.m,1))==(0x2f,0x35)
  self.cpu_guard()
  assert bytes(L.dos64_peek(self.m,0xa000+i)for i in range(len(self.worker)))==self.worker
  return {'private_prompt':True,'CIA_C_then_Return':True,'RFW_whole_RAM_crc':True,'fresh_RCV_init_before_NONE':True,'normal_INO_then_handoff':True,'third_floppy_full':True,'synthetic_media_not_DOS_boot':True}
 def cpu_guard(self,allow_install=False):
  # Install writes are allowed only in the first, separately checked interval.
  smc=set()
  for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']:smc.update([SYMS[n]+1,SYMS[n]+2])
  end=SYMS['__DEVICESTATE_RUN__']+SYMS['__DEVICESTATE_SIZE__']
  allowed=lambda a:a in [0,1,0xfffa,0xfffb,SYMS['sf_entered'],SYMS['_ps_color']] or 0x20<=a<0x3e or 0x100<=a<0x300 or 0x400<=a<0x7e8 or 0x8000<=a<end or SYMS['_br_config']<=a<SYMS['_br_config']+134 or 0x6000<=a<0x6000+max(len(self.gate),len(self.asset)) or 0x9000<=a<G['__RECOVER_BSS_RUN__']+G['__RECOVER_BSS_SIZE__'] or 0x9800<=a<0x9b67 or 0xcd00<=a<0xd000 or 0xc000<=a<0xc800 or 0xc900<=a<0xcd00 or 0xd800<=a<0xdbe8 or 0xdf00<=a<=0xdf0a or a in [0xdf1c,0xdf1d,0xd019,0xd01a,0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdc00,0xdc02,0xdc03,0xdc0d,0xdd00,0xdd02,0xdd04,0xdd05,0xdd06,0xdd07,0xdd0d,0xdd0e,0xdd0f] or (allow_install and 0xa000<=a<0xa000+len(self.worker)) or a in smc
  assert L.lc_check_writes(self.m,bytes(int(allowed(a))for a in range(65536)))==65536
class Tests(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def test_01_pending_OLD_actual_SYS_CIA_recovery_fresh_NONE_handoff(self):
  f=self.f=Cold();records.append(f.complete())
 def test_02_pending_prompt_CIA_STOP_no_mutation(self):
  f=self.f=Cold();f.prompt();f.keys(7,7);f.stopped();self.assertEqual(f.read('_lc_result',3),b'\3\10\0')
  for n,b in f.original.items():self.assertEqual(f.file(n),b)
  self.assertEqual(f.file('S0001.JRN'),None);records.append({'CIA_STOP_prompt':True,'all_original_files_exact':True})
 def test_03_corrupted_RFW_file_never_executes(self):
  b=bytearray((P/'START.RFW').read_bytes());b[-1]^=1;f=self.f=Cold(worker=bytes(b));f.prompt();f.confirm();f.stopped();self.assertEqual(f.read('_lc_result',3),b'\3\4\0')
  for n,b in f.original.items():self.assertEqual(f.file(n),b)
  self.assertEqual(bytes(L.dos64_peek(f.m,0xa000+i)for i in range(32)),bytes(32));records.append({'bad_worker_crc':True,'no_worker_entry_or_rename':True})
 def test_04_pending_MISSING_actual_confirmation_and_fresh_NONE(self):
  f=self.f=Cold('missing');records.append(f.complete())
 def test_05_pending_NEW_actual_confirmation_and_fresh_NONE(self):
  f=self.f=Cold('committed');records.append(f.complete())
 def test_06_nojournal_40_80_needs_no_RFW_and_handoff(self):
  for col in [40,80]:
   f=self.f=Menu(col);gate=(P/'START.RCV').read_bytes();L.bulk_model_seed(f.m,f.home+b'/START.RCV',gate,len(gate))
   r=f.run(SYMS['trampoline_start']);self.assertIn(r.status,[0,2]);self.assertEqual(r.regs.pc,SYMS['trampoline_start']);self.assertEqual(f.read('_lc_result',3),b'\5\0\0')
   self.assertEqual(bytes(L.dos64_peek(f.m,0xa000+i)for i in range(8192)),bytes(8192));self.assertEqual(f.read('sp',2),b'\xff\xcf');f.close();del self.f
  records.append({'nojournal_40_80_without_RFW_file':True})
 def test_07_failed_first_RFW_install_FETCH_never_enters_worker(self):
  f=self.f=Cold();f.prompt();f.confirm();r=f.advance('_overlay_poll');self.assertEqual(f.read('_lc_result',4),b'\1\0\0\20')
  L.dos64_reu_fail_after(f.m,0,1);f.stopped();self.assertEqual(f.read('_lc_result',3),b'\3\7\0')
  for n,b in f.original.items():self.assertEqual(f.file(n),b)
  self.assertEqual(bytes(L.dos64_peek(f.m,0xa000+i)for i in range(32)),bytes(32));records.append({'failed_RFW_install':True,'no_incomplete_code_execution':True})
 def test_08_RFW_unknown_CLOSE_once_blocks_boot_and_generic_drain(self):
  f=self.f=Cold();f.prompt();f.confirm();f.advance(0xa000);start=L.bulk_model_commands(f.m)
  L.save_model_fail_close.argtypes=[ptr,C.c_int];L.save_model_fail_close(f.m,1);f.stopped();self.assertEqual(f.read('_lc_result',3),b'\3\13\2')
  cmds=[L.bulk_model_command(f.m,i,1)for i in range(start,L.bulk_model_commands(f.m))];self.assertEqual(cmds.count(3),1);self.assertNotIn(10,cmds);self.assertEqual(L.bulk_model_open(f.m,1),1)
  for n,b in f.original.items():self.assertEqual(f.file(n),b)
  records.append({'unknown_RFW_CLOSE_once':True,'native_failure_blocks_boot':True})
 def test_09_human_confirmation_delay_uses_fresh_OPEN_deadline(self):
  f=self.f=Cold();f.human_delay=6000;records.append(dict(f.complete(),human_idle_timer_ticks=6000))
 def test_10_unknown_RFW_load_CLOSE_no_generic_second_CLOSE(self):
  f=self.f=Cold();f.prompt();f.confirm();start=L.bulk_model_commands(f.m)
  L.save_model_fail_close.argtypes=[ptr,C.c_int];L.save_model_fail_close(f.m,1);f.stopped();self.assertEqual(f.read('_lc_result',3),b'\3\2\2')
  cmds=[L.bulk_model_command(f.m,i,1)for i in range(start,L.bulk_model_commands(f.m))];self.assertEqual(cmds.count(3),1);self.assertNotIn(10,cmds);self.assertEqual(L.bulk_model_open(f.m,1),1)
  for n,b in f.original.items():self.assertEqual(f.file(n),b)
  self.assertEqual(bytes(L.dos64_peek(f.m,0xa000+i)for i in range(32)),bytes(32));records.append({'ambiguous_loader_CLOSE_count':1,'no_incomplete_worker_or_boot':True})
if __name__=='__main__':
 start=time.monotonic();r=unittest.main(exit=False,verbosity=2).result;(P/'RECOVERY_UI_RESULT.json').write_text(json.dumps({'pass':r.wasSuccessful(),'groups':r.testsRun,'seconds':time.monotonic()-start,'records':records,'scope':'actual SYS/CIA/controller/loadCRC/JG/RFW/freshNONE/INO/handoff; synthetic journal/media, no DOS/public/physical'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
