from test_ui_saveas import *
import unittest
T=unittest.TestCase();m,old,f=initial(T,admit=False);L.dos64_graphics_color_enable(m.m)
try:
 b=(P/'MODAL.MNU').read_bytes()
 for a,v in [(0x3da000,b[:0x6000]),(0x3f0000,b[0x6000:])]:L.bulk_reu_seed(m.m,a,v,len(v))
 load(m,'broker/broker.prg');ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,BR['modal_wait'],5000000);keys(m,bytes(8));loop(T,m);press(T,m,ord('b'));press(T,m,ord('n'))
 for i in range(10):press(T,m,8)
 for c in b'/usb1/Owned/SAVE0001.IMG':press(T,m,c)
 keys(m,bytes(8));loop(T,m);keys(m,bytes([2,0,0,0,0,0,0,0]));L.dos64_step(m.m);r=L.dos64_run(m.m,BE['bridge_entry'],10000000)
 print('atbridge',r.status,hex(r.regs.pc),r.regs.sp,'vars',{n:m.g(BR[n])for n in ['modal_owned','modal_context','ui_ready','modal_error']},'native',m.get('dos64_native_diag',6).hex(),'cache',m.g('dos64_cache_limit'),'event',m.get(UI['_mu_event'],133).hex(),'clock',m.g('dos64_host_clock_status'))
 for i in range(35):
  r=L.dos64_get_regs(m.m);print(i,hex(r.pc),m.get(r.pc,3).hex(),hex(r.a),hex(r.x),hex(r.p));L.dos64_step(m.m)
finally:m.close()
