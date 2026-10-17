from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
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
BROKER={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(E/'broker-runtime/broker.labels').read_text().splitlines()if l.startswith('al ')}
L.dos64_step.argtypes=[ptr]
def get(m,n,size=1):return bytes(L.dos64_peek(m,MAIN[n]+i)for i in range(size))
def call(m,n,stop=0x300,budget=40000000):
 ret=0x2ff;L.dos64_poke(m,0x1ff,ret>>8);L.dos64_poke(m,0x1fe,ret&255);L.dos64_set_regs(m,Regs(MAIN[n],0xfd,0x71,0x82,0x93,0x24,0,0));return L.dos64_run(m,stop,budget)
class Test(unittest.TestCase):
 def test_actual_START_to_runtime_hotkey_CUI_Resume_and_resident_return(self):
  f=Menu();m=f.m
  L.coupled_fault_bits.argtypes=[ptr];L.coupled_fault_bits.restype=C.c_uint32
  refs=sorted(q for q in (P.parent/'inputs/reference').glob('*.img')if q.name!='C-2M.img');a=refs[0].read_bytes();b=refs[1].read_bytes()
  cfg=bytearray(f.config);cfg[522]=0;struct.pack_into('<I',cfg,528,zlib.crc32(a));struct.pack_into('<I',cfg,532,zlib.crc32(b));struct.pack_into('<I',cfg,572,zlib.crc32(cfg[:572]))
  for n,data in [('A.IMG',a),('B.IMG',b),('DOS64.CFG',bytes(cfg)),('C.IMG',(P.parent/'inputs/reference/C-2M.img').read_bytes())]:L.bulk_model_seed(m,f.home+b'/'+n.encode(),data,len(data))
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
   (P/'FIXED_DOS_BEFORE_MENU.json').write_text(json.dumps(dos,indent=2)+'\n')
   lane.command(3);L.lc_clock_model_ratio(m,64)
   before=get(m,'dos64_files_state_start',25)
   L.dos64_host_input_model_keys(m,bytes(7)+b'\xa4');r=call(m,'dos64_overlay_input_poll');self.assertEqual(r.status,0)
   self.assertEqual(get(m,'dos64_modal_pending'),b'\1')
   r=call(m,'dos64_native_tick',0x7000);self.assertEqual(r.regs.pc,0x7000);self.assertEqual(get(m,'dos64_overlay_busy'),b'\0')
   r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait']);self.assertEqual(get(m,'dos64_cache_limit'),b'\0')
   L.dos64_host_input_model_keys(m,bytes(8));L.dos64_step(m);r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait'])
   # Full actual CIA SaveAs from this cold/DOS machine: no prepared native
   # SAVE/BIND fixture and no host worker entry calls or worker phase swaps.
   normal=[8,13,0x83,0x96,0x90,0x92,0x94,0x81,*map(ord,'3wa4zse'),0,*map(ord,'5rd6cftx'),*map(ord,'7yg8bhuv'),*map(ord,'9ij0mkon'),*map(ord,'+pl-.:@,'),ord('\\'),ord('*'),ord(';'),0x84,0,ord('='),ord('^'),ord('/'),ord('1'),9,0,ord('2'),ord(' '),0,ord('q'),27]
   def go(matrix,budget=5000000):
    L.dos64_host_input_model_keys(m,bytes(matrix));L.dos64_step(m);q=L.dos64_run(m,BROKER['modal_wait'],budget);self.assertEqual((q.status,q.regs.pc),(2,BROKER['modal_wait']),(q.status,hex(q.regs.pc),get(m,'dos64_native_diag',19).hex(),bytes(L.dos64_peek(m,BRIDGE['br_last']+i)for i in range(9)).hex()));return q
   def press(c,budget=5000000):
    go(bytes(8));shift=65<=c<=90;raw=c+32 if shift else c;at=normal.index(raw);keys=bytearray(8);keys[at//8]|=1<<(at%8)
    if shift:keys[1]|=128
    return go(keys,budget)
   snapshot=f.reu(0,4194304);high=bytes(L.dos64_peek(m,128+i)for i in range(96));path=f.home+b'/B0001.IMG'
   press(ord('b'));press(ord('w'));self.assertEqual(get(m,'dos64_disk_readonly',2),b'\0\0')
   # OrdinaryS creates a private immutable version path, never overwrites B.
   press(ord('s'),1600000000)
   self.assertEqual((L.dos64_peek(m,BRIDGE['br_success']),L.dos64_peek(m,BRIDGE['br_error'])),(1,0),bytes(L.dos64_peek(m,BRIDGE['br_last']+i)for i in range(9)).hex())
   self.assertEqual(bytes(L.dos64_peek(m,UI['_mu_view']+130+i)for i in range(128)),path.ljust(128,b'\0'))
   def file(name):
    n=L.bulk_model_size(m,name);self.assertNotEqual(n,0xffffffff,name);buf=C.create_string_buffer(n);self.assertEqual(L.bulk_model_read(m,name,buf,n),1);return buf.raw
   self.assertEqual(file(path),b);newcfg=file(f.home+b'/DOS64.CFG');self.assertEqual(newcfg[264:392],path.ljust(128,b'\0'));self.assertEqual(f.reu(0x3ff020,576),newcfg);self.assertEqual(file(f.home+b'/C.IMG'),(P.parent/'inputs/reference/C-2M.img').read_bytes());self.assertEqual(file(f.home+b'/A.IMG'),a);self.assertEqual(file(f.home+b'/B.IMG'),b)
   self.assertEqual(get(m,'dos64_files_state_start',25),before);self.assertEqual(bytes(L.dos64_peek(m,128+i)for i in range(96)),high)
   # Clean Eject and WriteProtect are actual private CIA intents, session-only.
   controls_commands=L.bulk_model_commands(m);saved_cfg=file(f.home+b'/DOS64.CFG');saved_binding=get(m,'dos64_disk_binding',8)
   press(ord('e'));self.assertEqual(L.dos64_peek(m,UI['_mu_result']),1);self.assertEqual(get(m,'dos64_disk_b_descriptor',10)[9],0)
   press(ord('a'));press(ord('w'));self.assertEqual(get(m,'dos64_disk_readonly',1),b'\1');self.assertEqual(L.dos64_peek(m,UI['_mu_result']),1);self.assertEqual(L.bulk_model_commands(m),controls_commands);self.assertEqual(file(f.home+b'/DOS64.CFG'),saved_cfg);self.assertEqual(get(m,'dos64_disk_binding',8),saved_binding);self.assertEqual(get(m,'dos64_files_state_start',25),before)
   after=f.reu(0,4194304)
   for lo,hi in [(0,0x3e0000),(0x3e0b04,0x3e2000),(0x3e23e8,0x3ff000),(0x3ff260,0x3ff500),(0x3ff520,0x400000)]:self.assertEqual(after[lo:hi],snapshot[lo:hi],(hex(lo),hex(hi)))
   (P/'COLD_MEDIA_ACTIONS.json').write_text(json.dumps({'passed':True,'actual_SYS_and_DOS_boot':True,'actual_CIA_hotkey_and_path':True,'no_host_worker_calls_or_swaps':True,'clean_mounted_B_ordinaryS_not_guest_edit':True,'actual_CIA_Eject_B_and_WriteProtect_A_session_only':True,'new_path':path.decode(),'image_sha256':__import__('hashlib').sha256(file(path)).hexdigest(),'CFG_sha256':__import__('hashlib').sha256(newcfg).hexdigest(),'C25_and_whole_C_exact':True,'all4MiB_outside_documented_work_and_anchor_spans_equal':True},indent=2)+'\n')
   go(bytes(8))
   # R is CIA row2bit1 on the existing scanner.
   L.dos64_host_input_model_keys(m,bytes([0,0,2,0,0,0,0,0]));r=L.dos64_run(m,0x300,40000000);self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_cache_limit'),b'\x20');self.assertEqual(get(m,'dos64_files_state_start',25),before)
   r=call(m,'dos64_native_tick');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_native_diag')[0],5)
   r=call(m,'dos64_overlay_input_poll');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_native_diag',4)[3],3)
   r=call(m,'dos64_native_tick');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_native_diag')[0],4)
   # Genuine DOS reads C after Resume, using the native keyboard/BDA ring.
   # No DOS API/file shortcut or direct BIOS success is injected.
   L.lc_clock_model_ratio(m,0);L.dos64_host_input_model_keys(m,bytes(8));read_start=L.bulk_model_commands(m)
   scans={'C':0x2e,'L':0x26,'S':0x1f,'T':0x14,'Y':0x15,'P':0x19,'E':0x12,' ':0x39,':':0x27,'\\':0x2b,'B':0x30,'O':0x18,'K':0x25,'.':0x34,'X':0x2d,'\r':0x1c}
   def pause_C_quiet():
    for _ in range(4096):
     if get(m,'hdb_active')!=b'\1':break
     lane.call('dos64_native_tick')
    else:self.fail('bounded active C request completion before coherent snapshot')
    lane.command(2)
   for cmd in ['CLS\r','TYPE C:\\BOOTOK.TXT\r']:
    for off in range(0,len(cmd),8):
     for c in cmd[off:off+8]:
      L.dos64_load(m,MAIN['dos64_native_diag']+5,bytes([ord(c),scans[c]]),2);lane.command(1)
     for drain in range(8192):
      lane.call('dos64_native_tick')
      if drain%64!=63:continue
      pause_C_quiet();ring=lane.read(0x41a,4);lane.command(3)
      if ring[:2]==ring[2:]:break
     else:self.fail('bounded actual BIOS keyboard drain')
   output=None
   for tick in range(8000):
    lane.call('dos64_native_tick')
    if tick%32:continue
    pause_C_quiet();bd=lane.read(0x400,256);cols=int.from_bytes(bd[0x4a:0x4c],'little');v=lane.read(0xb8000+int.from_bytes(bd[0x4e:0x50],'little'),cols*50);lines=[''.join(chr(v[(r*cols+c)*2])for c in range(cols))for r in range(25)];row,col=bd[0x51],bd[0x50]
    if any(s.strip()=='DOS64_HD_BOOT_OK'for s in lines)and col==2 and lines[row].strip()=='A>':output='\n'.join(lines);break
    lane.command(3)
   self.assertIsNotNone(output,'exact C file output and returned A> required');ops=[(L.bulk_model_command(m,i,0),L.bulk_model_command(m,i,1))for i in range(read_start,L.bulk_model_commands(m))];self.assertIn(get(m,'hdc_target')[0],[1,2]);self.assertTrue(any(t==get(m,'hdc_target')[0] and op==4 for t,op in ops),ops);self.assertEqual(file(f.home+b'/C.IMG'),(P.parent/'inputs/reference/C-2M.img').read_bytes());self.assertEqual(f.reu(0x100000,368640),a);self.assertEqual(f.reu(0x180000,368640),b);self.assertEqual(f.reu(0x380000,368640),bytes((i*13+(i>>7))&255 for i in range(368640)))
   (P/'DOS_C_AFTER_SAVEAS.json').write_text(json.dumps({'passed':True,'exact_output':output,'wire_after_Resume':ops,'actual_C_target':get(m,'hdc_target')[0],'C_whole_exact':True,'three_original_arenas_exact':True,'guest_instructions':lane.count(),'input':'CLS; TYPE C:\\BOOTOK.TXT'},indent=2)+'\n')

   lane.command(3);L.lc_clock_model_ratio(m,64);L.dos64_host_input_model_keys(m,bytes(7)+b'\xa4');r=call(m,'dos64_overlay_input_poll');self.assertEqual(r.status,0);self.assertEqual(get(m,'dos64_modal_pending'),b'\1');r=call(m,'dos64_native_tick',0x7000);self.assertEqual(r.regs.pc,0x7000);r=L.dos64_run(m,BROKER['modal_wait'],40000000);self.assertEqual(r.regs.pc,BROKER['modal_wait']);go(bytes(8));press(ord('f'));self.assertEqual(L.dos64_peek(m,UI['_mu_result']),7)
   go(bytes(8));finish_before=f.reu(0,4194304);commands=L.bulk_model_commands(m);target=get(m,'hdc_target')[0];L.dos64_host_input_model_keys(m,bytes([2])+bytes(7));L.dos64_step(m);r=L.dos64_run(m,BROKER['modal_safe_idle'],20000000);self.assertEqual(r.regs.pc,BROKER['modal_safe_idle'],(r.status,hex(r.regs.pc)));self.assertEqual(L.dos64_peek(m,UI['_mu_result']),6);self.assertEqual(L.dos64_peek(m,BRIDGE['br_safe']),1);self.assertEqual(L.dos64_peek(m,BRIDGE['br_resume']),0);self.assertEqual(get(m,'dos64_native_diag'),b'\xe1');self.assertEqual(L.bulk_model_open(m,1),0);self.assertEqual(L.bulk_model_open(m,2),0);self.assertEqual(L.bulk_model_commands(m)-commands,1);self.assertEqual([L.bulk_model_command(m,commands,i)for i in range(2)],[target,3]);self.assertEqual(f.reu(0,4194304),finish_before);self.assertEqual(file(f.home+b'/C.IMG'),(P.parent/'inputs/reference/C-2M.img').read_bytes())
   (P/'COLD_FINISH_RESULT.json').write_text(json.dumps({'passed':True,'same_cold_SYS_DOS_S_controls_Resume_Cread_session':True,'actual_CIA_Finish_confirmation':True,'privateSafe':True,'one_known_C_CLOSE':True,'noResume_nativeE1':True,'whole4MiB_and_C_exact':True},indent=2)+'\n')
  finally:f.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'COUPLED_MEDIA_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'scope':'actual START runtime-role asset/main coldboot with genuine DOS A/B and valid2MiB C; genuine VER/DIR then native CIA/CUI Resume chain; no Turbo/physical acceptance'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
