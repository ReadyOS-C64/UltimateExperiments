from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-handoff-entry');assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,unittest,zlib,struct
from test_modal import Menu,SYMS,L,ptr
from test_actual import Regs
from dos_lane import Lane
MAIN={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P.parent/'inputs/build/dos64.labels').read_text().splitlines()if l.startswith('al ')}
E=P.parents[1]/'live-media-runtime-assets-root-20261017'
BROKER={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(E/'broker-runtime/broker.labels').read_text().splitlines()if l.startswith('al ')}
L.dos64_step.argtypes=[ptr]
def get(m,n,size=1):return bytes(L.dos64_peek(m,MAIN[n]+i)for i in range(size))
def call(m,n,stop=0x300,budget=40000000):
 ret=0x2ff;L.dos64_poke(m,0x1ff,ret>>8);L.dos64_poke(m,0x1fe,ret&255);L.dos64_set_regs(m,Regs(MAIN[n],0xfd,0x71,0x82,0x93,0x24,0,0));return L.dos64_run(m,stop,budget)
class Test(unittest.TestCase):
 def test_actual_START_to_runtime_hotkey_CUI_Resume_and_resident_return(self):
  f=Menu();m=f.m
  refs=sorted(q for q in (P.parent/'inputs/reference').glob('*.img')if q.name!='C-2M.img');a=refs[0].read_bytes();b=refs[1].read_bytes()
  cfg=bytearray(f.config);cfg[522]=0;struct.pack_into('<I',cfg,528,zlib.crc32(a));struct.pack_into('<I',cfg,532,zlib.crc32(b));struct.pack_into('<I',cfg,572,zlib.crc32(cfg[:572]))
  for n,data in [('A.IMG',a),('B.IMG',b),('DOS64.CFG',bytes(cfg)),('C.IMG',(P.parent/'inputs/reference/C-2M.img').read_bytes())]:L.bulk_model_seed(m,f.home+b'/'+n.encode(),data,len(data))
  try:
   r=f.run(MAIN['dos64_native_loop'],600000000);self.assertEqual(r.regs.pc,MAIN['dos64_native_loop'],(r.status,hex(r.regs.pc),get(m,'dos64_native_diag',19).hex(),get(m,'dos64_cold_open').hex()))
   for i in range(4096):
    stage=get(m,'dos64_native_diag')[0]
    if stage==4:break
    self.assertIn(stage,[2,6],(get(m,'dos64_native_diag',19).hex(),get(m,'hd_state',1).hex(),get(m,'hd_error',1).hex(),get(m,'dos64_files_state_start',25).hex()));r=call(m,'dos64_native_cold_poll');self.assertEqual(r.status,0)
   self.assertEqual(get(m,'dos64_native_diag')[0],4,(i,get(m,'hdc_phase').hex(),get(m,'hd_state').hex(),get(m,'dos64_files_state_start',25).hex()));self.assertEqual(get(m,'dos64_cold_open'),b'\0')
   L.lc_clock_model_ratio(m,0)
   lane=Lane(f,a);dos=lane.run()
   (P/'DOS_BEFORE_MENU.json').write_text(json.dumps(dos,indent=2)+'\n')
   lane.command(3);L.lc_clock_model_ratio(m,64)
   before=get(m,'dos64_files_state_start',25)
   L.dos64_host_input_model_keys(m,bytes(7)+b'\xa4');r=call(m,'dos64_overlay_input_poll');self.assertEqual(r.status,0)
   self.assertEqual(get(m,'dos64_modal_pending'),b'\1')
   r=call(m,'dos64_native_tick',0x7000);self.assertEqual(r.regs.pc,0x7000);self.assertEqual(get(m,'dos64_overlay_busy'),b'\0')
   r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait']);self.assertEqual(get(m,'dos64_cache_limit'),b'\0')
   L.dos64_host_input_model_keys(m,bytes(8));L.dos64_step(m);r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait'])
   # R is CIA row2bit1 on the existing scanner.
   L.dos64_host_input_model_keys(m,bytes([0,0,2,0,0,0,0,0]));r=L.dos64_run(m,0x300,40000000);self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_cache_limit'),b'\x20');self.assertEqual(get(m,'dos64_files_state_start',25),before)
   r=call(m,'dos64_native_tick');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_native_diag')[0],5)
   r=call(m,'dos64_overlay_input_poll');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_native_diag',4)[3],3)
   r=call(m,'dos64_native_tick');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_native_diag')[0],4)
  finally:f.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'HANDOFF_ENTRY_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'scope':'actual START runtime-role asset/main coldboot with genuine DOS A/B and valid2MiB C; genuine VER/DIR then native CIA/CUI Resume chain; no Turbo/physical acceptance'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
