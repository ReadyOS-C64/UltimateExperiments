from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
os.chdir(P)
sys.dont_write_bytecode=True
sys.path.insert(0,str(P))
import ctypes as C,json,unittest
from test_online_save import Machine,L,symbols,Regs
for n,r,a in [('dos64_host_input_model_keys',None,[C.c_void_p,C.c_void_p]),('dos64_graphics_color_enable',None,[C.c_void_p]),('dos64_graphics_color_peek',C.c_uint8,[C.c_void_p,C.c_uint16]),('dos64_reu_fail_after',None,[C.c_void_p,C.c_uint64,C.c_uint32]),('dos64_step',None,[C.c_void_p])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
HEADER=(P/'HEADER.bin').read_bytes();BROKER=(P/('broker-runtime'if os.environ.get('DOS64_ENTRY_ROLE')=='runtime'else'broker')/'broker.prg').read_bytes()[2:]
UI=(P/'ui/panel.prg').read_bytes()[2:]
B={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P/('broker-runtime'if os.environ.get('DOS64_ENTRY_ROLE')=='runtime'else'broker')/'broker.labels').read_text().splitlines()if l.startswith('al ')}
records=[]
def keys(m,body):L.dos64_host_input_model_keys(m.m,C.create_string_buffer(body))
def reu(m):
 b=C.create_string_buffer(0x400000);assert L.dos64_reu_read(m.m,0,b,len(b));return b.raw
def ram(m,a,n):return m.get(a,n)
def prepare(target=2):
 m=Machine(target=target,warm=True)
 L.dos64_graphics_color_enable(m.m)
 m.call('dos64_bios_init',40000000);m.call('dos64_cold_release')
 m.p('dos64_host_input_claim',0xa5);m.call('dos64_overlay_input_init')
 m.call('dos64_native_timer_init',2000000)
 m.p(symbols['dos64_native_diag']+3,0)
 L.bulk_reu_seed(m.m,0x3da000,HEADER,len(HEADER));L.bulk_reu_seed(m.m,0x3da200,BROKER,len(BROKER))
 L.bulk_reu_seed(m.m,0x3daa00,UI,len(UI))
 cfg=bytearray(576);cfg[136:264]=b'/usb1/Owned/A.IMG'.ljust(128,b'\0');cfg[264:392]=b'/usb1/Owned/B.IMG'.ljust(128,b'\0');L.bulk_reu_seed(m.m,0x3ff000,bytes(cfg),576)
 m.call('dos64_cache_flush',2000000)
 # A full native PAUSE establishes the reference guest framebuffer.
 m.p('dos64_native_diag',4);m.p(symbols['dos64_native_diag']+3,2)
 m.call('dos64_native_tick',40000000)
 assert m.g('dos64_native_diag')==5
 keys(m,bytes(8))
 return m
def chord(m):keys(m,bytes(7)+b'\xa4')
def file_context(m):return m.get('dos64_files_state_start',25),L.save_model_position(m.m,m.target)
class Tests(unittest.TestCase):
 def test_01_actual_CIA_pause_resident_footer_broker_return_and_redraw(self):
  for target in [1,2]:
   m=prepare(target)
   try:
    bitmap=m.get(0x6000,8192);matrix=m.get(0x4000,1000);colors=bytes(L.dos64_graphics_color_peek(m.m,0xd800+i)for i in range(1000));before=reu(m);context=file_context(m)
    m.p('dos64_native_diag',4);chord(m);r=m.call('dos64_overlay_input_poll',2000000)
    self.assertTrue(r.regs.p&1);self.assertEqual(m.g('dos64_modal_pending'),1);self.assertEqual(m.g(symbols['dos64_native_diag']+3),2)
    # Stop at entry before executing any broker byte: every INPUT frame must
    # already have returned, including the resident lease-release wrapper.
    ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255)
    L.dos64_set_regs(m.m,Regs(symbols['dos64_native_tick'],0xfd,0x71,0x82,0x93,0x24,0,0))
    r=L.dos64_run(m.m,0x7000,40000000)
    self.assertEqual(r.status,2);self.assertEqual(r.regs.pc,0x7000);self.assertEqual(r.regs.sp,0xfd)
    self.assertEqual(m.g('dos64_overlay_busy'),0);self.assertEqual(m.g('dos64_overlay_current'),3)
    self.assertEqual(m.get(0x7000,len(BROKER)),BROKER)
    r=L.dos64_run(m.m,B['modal_wait'],2000000);self.assertEqual(r.status,2);self.assertEqual(r.regs.pc,B['modal_wait']);self.assertEqual(r.regs.sp,0xfd)
    self.assertEqual(m.g('dos64_cache_limit'),0);self.assertEqual(file_context(m),context)
    self.assertNotEqual(bytes(L.dos64_graphics_color_peek(m.m,0xd800+i)for i in range(1000)),colors)
    # Release the opening chord, arming the actual CUI scanner.
    keys(m,bytes(8));L.dos64_step(m.m)
    r=L.dos64_run(m.m,B['modal_wait'],2000000);self.assertEqual(r.status,2);self.assertEqual(r.regs.pc,B['modal_wait'])
    # R through the actual native CUI scanner/private intent/controller.
    keys(m,bytes([0,0,2,0,0,0,0,0]))
    r=L.dos64_run(m.m,symbols['fixture_return'],2000000);self.assertEqual(r.status,0)
    self.assertEqual((m.g('dos64_native_diag'),m.g('dos64_cache_limit'),m.g('dos64_modal_pending'),m.g(symbols['dos64_native_diag']+3)),(5,32,2,2))
    expected=bytearray(before);expected[0x3e2000:0x3e23e8]=colors
    self.assertEqual(file_context(m),context);self.assertEqual(reu(m),expected)
    self.assertNotEqual(m.get(0x7000,256),bitmap[4096:4352])
    self.assertEqual(bytes(L.dos64_graphics_color_peek(m.m,0xd800+i)for i in range(1000)),colors)
    m.call('dos64_native_tick',40000000)
    self.assertEqual(m.get(0x6000,8192),bitmap);self.assertEqual(m.get(0x4000,1000),matrix)
    self.assertEqual(bytes(L.dos64_graphics_color_peek(m.m,0xd800+i)for i in range(1000)),colors)
    self.assertEqual((m.g('dos64_native_diag'),m.g('dos64_modal_pending'),m.g(symbols['dos64_native_diag']+3)),(5,0,3))
    self.assertEqual(file_context(m),context);self.assertEqual(reu(m),expected)
    m.p('dos64_native_diag',4);m.p(symbols['dos64_native_diag']+3,0)
    m.call('dos64_overlay_input_poll',2000000);self.assertEqual(m.g('dos64_modal_edge'),2)
    m.call('dos64_cache_flush',2000000);self.assertEqual(reu(m),expected)
    keys(m,bytes([0,128,0,0,0,0,0,0]));m.call('dos64_overlay_input_poll',2000000);self.assertEqual(m.g('dos64_modal_edge'),0)
    records.append({'C_target':target,'entry_native_SP':0xfd,'overlay_busy_at_entry':0,'full_bitmap_matrix_colors_redrawn_before_RUN':True,'whole4MiB_exact_except_owned_color_snapshot':True,'FILES_C_position_exact':True,'actual_CUI_Resume':True})
   finally:m.close()
 def test_02_every_wrong_header_byte_blocks_broker_load_and_execution(self):
  m=prepare()
  try:
   context=file_context(m);m.put(0x7000,bytes([0xa6])*1792);sentinel=m.get(0x7000,1792)
   for i in range(64):
    bad=bytearray(HEADER);bad[i]^=1;L.bulk_reu_seed(m.m,0x3da000,bytes(bad),64)
    m.p('dos64_native_diag',5);m.p('dos64_modal_pending',1);m.p(symbols['dos64_native_diag']+3,0)
    m.call('dos64_native_tick',2000000)
    self.assertEqual((m.g('dos64_native_diag'),m.g('dos64_modal_pending'),m.g('dos64_cache_limit')),(0xe1,0,32))
    self.assertEqual(m.get(0x7000,1792),sentinel);self.assertEqual(m.g('dos64_overlay_busy'),0);self.assertEqual(file_context(m),context)
   records.append({'header_changed_positions':64,'broker_payload_never_loaded':True})
  finally:m.close()
 def test_03_active_C_request_defers_pause_without_losing_the_request(self):
  m=prepare()
  try:
   m.p('dos64_native_diag',4);m.p('hdb_active',1);chord(m);m.call('dos64_overlay_input_poll',2000000)
   self.assertEqual((m.g('dos64_modal_pending'),m.g(symbols['dos64_native_diag']+3)),(1,0))
   m.p('hdb_active',0);m.call('dos64_overlay_input_poll',2000000)
   self.assertEqual((m.g('dos64_modal_pending'),m.g(symbols['dos64_native_diag']+3)),(1,2))
  finally:m.close()
 def test_04_held_chord_coalesces_until_release(self):
  m=prepare()
  try:
   m.p('dos64_native_diag',4);m.p('dos64_modal_edge',1);chord(m);m.call('dos64_overlay_input_poll',2000000)
   self.assertEqual(m.g('dos64_modal_pending'),0);self.assertEqual(m.g(symbols['dos64_native_diag']+3),0)
   keys(m,bytes(8));m.call('dos64_overlay_input_poll',2000000);self.assertEqual(m.g('dos64_modal_edge'),0)
   chord(m);m.call('dos64_overlay_input_poll',2000000);self.assertEqual(m.g('dos64_modal_pending'),1)
  finally:m.close()
 def test_05_partial_header_or_broker_DMA_never_enters_broker(self):
  for skip,prefix in [(0,7),(1,312),(2,17),(3,312)]:
   m=prepare()
   try:
    context=file_context(m);m.p('dos64_modal_pending',1);L.dos64_reu_fail_after(m.m,skip,prefix)
    m.call('dos64_native_tick',2000000)
    self.assertEqual((m.g('dos64_native_diag'),m.g('dos64_modal_pending'),m.g('dos64_cache_limit')),(0xe1,0,32))
    self.assertEqual(m.g('dos64_overlay_busy'),0);self.assertEqual(file_context(m),context)
   finally:m.close()
 def test_06_failed_UI_or_path_DMA_never_calls_uninitialized_C(self):
  for skip in [5,7]:
   m=prepare()
   try:
    context=file_context(m);m.p('dos64_modal_pending',1);L.dos64_reu_fail_after(m.m,skip,64)
    r=m.call('dos64_native_tick',2000000)
    self.assertEqual((m.g('dos64_native_diag'),m.g('dos64_modal_pending'),m.g('dos64_cache_limit')),(0xe1,0,0))
    self.assertEqual(r.regs.sp,0xff);self.assertEqual(file_context(m),context);self.assertEqual(m.g('dos64_overlay_busy'),0)
   finally:m.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result
 (P/('RUNTIME_ENTRY_RESULT.json'if os.environ.get('DOS64_ENTRY_ROLE')=='runtime'else'ENTRY_RESULT.json')).write_text(json.dumps({'passed':r.wasSuccessful(),'tests':r.testsRun,'records':records,'scope':'actual CIA/INPUT/resident footer/matched unit broker admit-release/resident redraw; actual CUI Resume; no disk-worker or START container loader yet'},indent=2)+'\n')
 sys.exit(not r.wasSuccessful())
