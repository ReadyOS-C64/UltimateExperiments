import unittest,ctypes as C
from test_ui_saveas import *
t=unittest.TestCase();m,old,f=initial(t,admit=False)
try:
 L.dos64_graphics_color_enable(m.m);b=(P/'MODAL.MNU').read_bytes()
 for a,v in [(0x3da000,b[:0x6000]),(0x3f0000,b[0x6000:])]:L.bulk_reu_seed(m.m,a,v,len(v))
 load(m,'broker/broker.prg');ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,BR['modal_wait'],5000000)
 def diag(label):
  print(label,m.get(UI['_mu_result'],6).hex(),'view',m.g(UI['_mu_view']),m.g(UI['_mu_view']+129),'loaded',m.get('dos64_disk_loaded',2).hex(),'key',m.get(UI['_ps_key'],4).hex(),'matrix',m.get(UI['_ps_matrix'],8).hex())
 diag('initial');keys(m,bytes(8));loop(t,m);diag('released');press(t,m,ord('b'));diag('b');press(t,m,ord('n'));diag('n')
finally:m.close()
