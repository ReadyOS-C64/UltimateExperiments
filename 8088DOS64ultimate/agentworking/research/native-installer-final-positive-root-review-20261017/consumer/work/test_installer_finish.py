from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
REPORT=Path(os.environ['REPORT_DIRECTORY']);REPORT.mkdir(parents=True,exist_ok=False)
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-handoff-entry');assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,unittest,zlib,struct
from test_journal_start import Journal as Menu,SYMS,L
from test_actual import ptr
from test_actual import Regs
from dos_lane import Lane
MAIN={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P.parent/'inputs/build/dos64.labels').read_text().splitlines()if l.startswith('al ')}
E=P.parent/'runtime'
UI={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(E/'ui/panel.labels').read_text().splitlines()if l.startswith('al ')}
BRIDGE={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(E/'bridge/bridge.labels').read_text().splitlines()if l.startswith('al ')}
BROKER={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(E/'broker/broker.labels').read_text().splitlines()if l.startswith('al ')}
L.dos64_step.argtypes=[ptr];L.dos64_step.restype=None
L.coupled_fault_bits.argtypes=[ptr];L.coupled_fault_bits.restype=C.c_uint32
def get(m,n,size=1):return bytes(L.dos64_peek(m,MAIN[n]+i)for i in range(size))
def call(m,n,stop=0x300,budget=40000000):
 ret=0x2ff;L.dos64_poke(m,0x1ff,ret>>8);L.dos64_poke(m,0x1fe,ret&255);L.dos64_set_regs(m,Regs(MAIN[n],0xfd,0x71,0x82,0x93,0x24,0,0));return L.dos64_run(m,stop,budget)
class Test(unittest.TestCase):
 def test_actual_START_to_runtime_hotkey_CUI_Resume_and_resident_return(self):
  f=Menu(int(os.environ.get('EXPECTED_COLUMNS','80')));m=f.m
  L.coupled_fault_bits.argtypes=[ptr];L.coupled_fault_bits.restype=C.c_uint32
  published=Path(os.environ['PUBLISHED_DIRECTORY']);a=f.a;b=f.b;cfg=bytearray(f.config);original_c=f.c
  f.seed(bytes((i*13+(i>>7))&255 for i in range(368640)),0x380000)
  try:
   loaded=f.run(SYMS['trampoline_loaded'],1300000000);self.assertEqual(loaded.regs.pc,SYMS['trampoline_loaded']);r=f.run(MAIN['dos64_native_loop'],1300000000);self.assertEqual(r.regs.pc,MAIN['dos64_native_loop'],(r.status,hex(r.regs.pc),get(m,'dos64_native_diag',19).hex(),get(m,'dos64_cold_open').hex(),L.coupled_fault_bits(m),f.read('_lc_result',16).hex()))
   for i in range(4096):
    stage=get(m,'dos64_native_diag')[0]
    if stage==4:break
    self.assertIn(stage,[2,6],(get(m,'dos64_native_diag',19).hex(),get(m,'hd_state',1).hex(),get(m,'hd_error',1).hex(),get(m,'dos64_files_state_start',25).hex()));r=call(m,'dos64_native_cold_poll');self.assertEqual(r.status,0)
   self.assertEqual(get(m,'dos64_native_diag')[0],4,(i,get(m,'hdc_phase').hex(),get(m,'hd_state').hex(),get(m,'dos64_files_state_start',25).hex()));self.assertEqual(get(m,'dos64_cold_open'),b'\0');self.assertEqual(get(m,'dos64_disk_binding',8),bytes(cfg[528:536]))
   L.lc_clock_model_ratio(m,0)
   lane=Lane(f,a);dos=lane.run() if not os.environ.get('COLD_NO_DOS_DIAG') else {'scope':'actualSTART/native coherentpause diagnostic; noDOS'}
   if os.environ.get('COLD_NO_DOS_DIAG'):lane.command(2)
   (REPORT/'FIXED_DOS_BEFORE_MENU.json').write_text(json.dumps(dos,indent=2)+'\n')
   for name,address,length in [('native-bitmap',0x6000,8000),('native-screen',0x400,1000),('native-color',0xd800,1000),('native-vic',0xd000,64)]:
    (REPORT/(name+'.bin')).write_bytes(bytes(L.dos64_peek(m,address+i)for i in range(length)))
   (REPORT/'CAPTURE.json').write_text(json.dumps({'scope':'actual_native_model_C64_RAM_planes_not_physical_VIC_video','columns':int(os.environ.get('EXPECTED_COLUMNS','80')),'at':'coherent paused DOS DIR prompt before menu'},indent=2)+'\n')

   lane.command(3);L.lc_clock_model_ratio(m,64)
   before=get(m,'dos64_files_state_start',25)
   L.dos64_host_input_model_keys(m,bytes(7)+b'\xa4');r=call(m,'dos64_overlay_input_poll');self.assertEqual(r.status,0)
   self.assertEqual(get(m,'dos64_modal_pending'),b'\1')
   r=call(m,'dos64_native_tick',0x7000);self.assertEqual(r.regs.pc,0x7000);self.assertEqual(get(m,'dos64_overlay_busy'),b'\0')
   r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait']);self.assertEqual(get(m,'dos64_cache_limit'),b'\0')
   L.dos64_host_input_model_keys(m,bytes(8));L.dos64_step(m);r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait'])
   # Actual CIA Finish from the generated START/DOS machine; no host
   # Finish completion/leaf calls or replacement asset injection.
   normal=[8,13,0x83,0x96,0x90,0x92,0x94,0x81,*map(ord,'3wa4zse'),0,*map(ord,'5rd6cftx'),*map(ord,'7yg8bhuv'),*map(ord,'9ij0mkon'),*map(ord,'+pl-.:@,'),ord('\\'),ord('*'),ord(';'),0x84,0,ord('='),ord('^'),ord('/'),ord('1'),9,0,ord('2'),ord(' '),0,ord('q'),27]
   def go(matrix,budget=5000000):
    L.dos64_host_input_model_keys(m,bytes(matrix));L.dos64_step(m);q=L.dos64_run(m,BROKER['modal_wait'],budget);self.assertEqual((q.status,q.regs.pc),(2,BROKER['modal_wait']),(q.status,hex(q.regs.pc),get(m,'dos64_native_diag',19).hex(),bytes(L.dos64_peek(m,BRIDGE['br_last']+i)for i in range(9)).hex()));return q
   def press(c,budget=5000000):
    go(bytes(8));shift=65<=c<=90;raw=c+32 if shift else c;at=normal.index(raw);keys=bytearray(8);keys[at//8]|=1<<(at%8)
    if shift:keys[1]|=128
    return go(keys,budget)
   def file(name):
    n=L.bulk_model_size(m,name);self.assertNotEqual(n,0xffffffff);buf=C.create_string_buffer(n);self.assertEqual(L.bulk_model_read(m,name,buf,n),1);return buf.raw
   self.assertEqual(f.reu(0x100000,368640),a);self.assertEqual(f.reu(0x180000,368640),b);self.assertEqual(f.reu(0x380000,368640),bytes((i*13+(i>>7))&255 for i in range(368640)))
   self.assertEqual(file(f.a_path),a);self.assertEqual(file(f.b_path),b);self.assertEqual(file(f.c_path),original_c)
   go(bytes(8));press(ord('f'));self.assertEqual(L.dos64_peek(m,UI['_mu_result']),7)
   go(bytes(8));finish_before=f.reu(0,4194304);commands=L.bulk_model_commands(m);target=get(m,'hdc_target')[0];L.dos64_host_input_model_keys(m,bytes([2])+bytes(7));L.dos64_step(m);r=L.dos64_run(m,BROKER['modal_safe_idle'],20000000);self.assertEqual(r.regs.pc,BROKER['modal_safe_idle'],(r.status,hex(r.regs.pc)));self.assertEqual(L.dos64_peek(m,UI['_mu_result']),6);self.assertEqual(L.dos64_peek(m,BRIDGE['br_safe']),1);self.assertEqual(L.dos64_peek(m,BRIDGE['br_resume']),0);self.assertEqual(get(m,'dos64_native_diag'),b'\xe1');self.assertEqual(L.bulk_model_open(m,1),0);self.assertEqual(L.bulk_model_open(m,2),0);self.assertEqual(L.bulk_model_commands(m)-commands,1);self.assertEqual([L.bulk_model_command(m,commands,i)for i in range(2)],[target,3]);self.assertEqual(f.reu(0,4194304),finish_before);self.assertEqual(file(f.c_path),original_c)
   (REPORT/'COLD_FINISH_RESULT.json').write_text(json.dumps({'passed':True,'same_generated_START_SYS_DOS_VER_DIR_Finish_session':True,'actual_CIA_Finish_confirmation':True,'privateSafe':True,'one_known_C_CLOSE':True,'noResume_nativeE1':True,'whole4MiB_and_C_exact':True},indent=2)+'\n')
  finally:f.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(REPORT/'COUPLED_MEDIA_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'scope':'actual START runtime-role asset/main coldboot with genuine DOS A/B and valid2MiB C; genuine VER/fullDIR then native CIA/CUI Finish/knownCLOSE; no Turbo/physical acceptance'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
