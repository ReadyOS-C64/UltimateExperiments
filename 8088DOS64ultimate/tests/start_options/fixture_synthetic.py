"""Synthetic caller-owned inputs; no DOS/installer/full-main execution claim."""
import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-synthetic-ini-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import struct,zlib
from test_start import Start,SYMS,L,MAIN
from test_actual import Regs
from test_controller import cfg
from start_template_metadata import patch
from make_release_options import descriptor
class Generated(Start):
 def __init__(self,columns=80,ini_data=True):
  self.columns=columns;self.ini=(b'[emulator]\ninitial_columns='+str(columns).encode()+b'\n')if ini_data is True else ini_data
  self.asset=(P/'START.INO').read_bytes();self.home=b'/Home';self.template=(P/'controller.prg').read_bytes();self.prg=patch((P/'START.REL').read_bytes(),self.template,self.home);self.labels=SYMS;at=SYMS['_lc_control']-0x0801+2;self.control=self.prg[at:at+131]
  self.a=bytes((i*13+3)&255 for i in range(368640));self.b=bytes((i*7+19)&255 for i in range(368640));self.c=bytes(2097152)
  c=bytearray(cfg(self.a,self.b))
  for at,value in [(8,self.home),(136,self.home+b'/A.IMG'),(264,self.home+b'/B.IMG'),(392,self.home+b'/C.IMG')]:c[at:at+128]=value.ljust(128,b'\0')
  struct.pack_into('<I',c,572,zlib.crc32(c[:572]));self.config=bytes(c)
  self.main=(P.parent/'inputs/build/dos64.prg').read_bytes();self.rel=(P/'DOS64.REL').read_bytes();assert descriptor(self.main,(P.parent/'inputs/build/dos64.labels').read_text(),options=True)==self.rel
  self.m=L.dos64_create();L.dos64_load(self.m,0x0801,self.prg[2:],len(self.prg)-2);L.dos64_load(self.m,0x8000,b'\xa5'*8192,8192);L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x37);assert L.dos64_enable_reu_sized(self.m,4096)==1;L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.bulk_model_enable(self.m)
  L.dos64_graphics_color_enable(self.m);L.dos64_cia_clock_enable(self.m);L.dos64_native_display_enable(self.m);L.dos64_host_input_model_enable(self.m);L.native_runtime_control_enable(self.m);L.lc_clock_model_ratio(self.m,64);L.native_runtime_require_nmi_order(self.m,SYMS['ps_rti'])
  guard=self.template[SYMS['_ps_guard']-0x0801+2:];offset=guard.index(b'\xa9\x35\x85\x01\x60')+4;L.lc_nmi_at_pc(self.m,SYMS['_ps_guard']+offset)
  for name,b in [('START.INO',self.asset),('DOS64.INI',self.ini),('DOS64.CFG',self.config),('DOS64.REL',self.rel),('DOS64.PRG',self.main),('A.IMG',self.a),('B.IMG',self.b),('C.IMG',self.c)]:
   if b is not None:L.bulk_model_seed(self.m,self.home+b'/'+name.encode(),b,len(b))
  L.dos64_clear_writes(self.m);L.dos64_set_regs(self.m,Regs(2061,0xff,0,0,0,0x24,0,0))
