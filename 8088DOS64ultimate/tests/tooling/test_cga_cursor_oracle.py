import sys
sys.dont_write_bytecode=True
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build_support'))
from cga_cursor_oracle import render_text_capture
class CursorOracle(unittest.TestCase):
 def setup_capture(self,cols=80):
  b=bytearray(256);b[0x49]=3 if cols==80 else 1;b[0x4a:0x4c]=cols.to_bytes(2,'little');b[0x4c:0x4e]=(4096 if cols==80 else 2048).to_bytes(2,'little');v=bytes([32,7])*8192;r=bytearray(18);r[10]=6;r[11]=7;r[15]=1
  return dict(bda=b,cga=v,narrow=bytes(1024),wide=bytes(2048),registers=r,control=0x29 if cols==80 else 0x28,control_valid=0xa5,phase_valid=0xa5,field_phase=0,blink_visible=1,native_sha256='a'*64,expected_native_sha256='a'*64)
 def test_complete_both_widths_known_cursor(self):
  for cols in (40,80):
   a=self.setup_capture(cols);q=render_text_capture(**a);e=bytearray(8000);at=8 if cols==40 else 0;e[at+6:at+8]=bytes([255 if cols==40 else 15])*2;self.assertEqual(bytes(e),q['bitmap']);self.assertEqual(bytes([0xf0])*1000,q['matrix'])
 def test_all_external_internal_blink_phases(self):
  for mode in range(4):
   for phase in range(256):
    a=self.setup_capture();a['registers'][10]=mode*32+6;a['field_phase']=phase;got=render_text_capture(**a)['bitmap'][6];on=mode!=1 and phase&8==0 and (mode!=2 or phase&16==0) and (mode!=3 or phase&32==0);self.assertEqual(15 if on else 0,got)
 def test_adverse_capture_refuses_stale_foreign_graphics_source_shape(self):
  for key,value in [('phase_valid',0),('phase_valid',255),('control_valid',0),('native_sha256','b'*64),('blink_visible',2)]:
   a=self.setup_capture();a[key]=value
   with self.assertRaises(ValueError):render_text_capture(**a)
  for index,value in [(0x49,4),(0x62,4),(0x4f,16)]:
   a=self.setup_capture();a['bda'][index]=value
   with self.assertRaises(ValueError):render_text_capture(**a)
  for index,value in [(13,1),(10,8)]:
   a=self.setup_capture();a['registers'][index]=value
   with self.assertRaises(ValueError):render_text_capture(**a)
 def test_cursor14bit_does_not_alias_video_ram_and_blank_colors_black(self):
  a=self.setup_capture();a['registers'][14]=32;self.assertEqual(bytes(8000),render_text_capture(**a)['bitmap']);a['control']&=~8;self.assertEqual(bytes(1000),render_text_capture(**a)['matrix'])
if __name__=='__main__':unittest.main()
