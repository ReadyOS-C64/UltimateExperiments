"""Execute the linked platform input code in Peddle, not a host UI substitute."""
import unittest,ctypes as C
from test_select import UI,L

def shifted(c):
 if 97<=c<=122:return c-32
 if 49<=c<=57:return c-16
 if 0x90<=c<=0x96:return c+1
 return {8:0x85,9:0,45:95,64:96,94:126,0x83:0x82,0x81:0x80,46:62,44:60,58:91,59:93,47:63,92:124}.get(c,c)
class Keys(unittest.TestCase):
 def setUp(self):self.u=UI();self.f=self.u.f
 def tearDown(self):self.u.close()
 def publish(self,keys):
  self.assertEqual(self.f.readat(0xc6,1),b'\0');L.dos64_load(self.f.m,0x277,bytes(keys),len(keys));L.dos64_poke(self.f.m,0xc6,len(keys))
 def poll(self):return self.u.call('_ps_key_poll'),self.f.byte('_ps_key')
 def test_all256_physical_shift_values_unchanged(self):
  for c in range(256):self.assertEqual(self.u.call('_ps_shifted',c),shifted(c),hex(c))
 def test_standard_count_last_FIFO_and_navigation_function_keys(self):
  for src,wanted in [([13,3,27,9,20,19,17,145,29,157],[13,27,27,9,8,0x84,0x81,0x80,0x83,0x82]),([133,137,134,138,135,139,136,140],[0x90+i for i in range(8)]),([ord(x)for x in 'Abc09/:.'],[ord(x)for x in 'Abc09/:.'])]:
   self.publish(src)
   for i,v in enumerate(wanted):self.assertEqual(self.poll(),(1,v));self.assertEqual(self.f.readat(0xc6,1),bytes([len(src)-i-1]))
   self.assertEqual(self.poll(),(0,0))
 def test_body_without_count_does_not_inject_and_unknown_key_drains(self):
  L.dos64_load(self.f.m,0x277,b'\r',1);self.assertEqual(self.poll(),(0,0));self.publish([255,13]);self.assertEqual(self.poll(),(0,0));self.assertEqual(self.poll(),(1,13))
 def test_bad_count_is_bounded_and_init_drops_stale_launch_queue(self):
  L.dos64_poke(self.f.m,0x281,0xa7)
  for count in [11,127,255]:
   L.dos64_poke(self.f.m,0xc6,count);self.assertEqual(self.poll(),(0,0));self.assertEqual(self.f.readat(0xc6,1),b'\0');self.assertEqual(self.f.readat(0x281,1),b'\xa7')
  self.publish([13]);self.u.call('_ps_init');self.assertEqual(self.poll(),(0,0))
 def test_actual_native_browser_consumes_buffer_and_preserves_matrix_path(self):
  u=self.u;u.directory(b'/',[(16,b'Home')]);u.directory(b'/Home',[(32,b'DOS1.IMG')]);self.assertEqual(u.begin(),1);u.ready();self.publish([13]);u.poll();u.ready();self.assertEqual(self.f.page()['path'],b'/Home');self.publish([133]);u.poll();u.ready();self.assertEqual(self.f.byte('_ss_stage'),1)
  # Genuine CIA matrix edge still selects the file after buffered navigation.
  u.key(0,1);self.assertEqual(self.f.byte('_ss_stage'),2)
if __name__=='__main__':unittest.main(verbosity=2)
