from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P.parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-format-runtime');assert not Path(sys.pycache_prefix).exists()
import unittest,json,struct,ctypes as C,zlib,hashlib
from test_actual import L,Regs,ptr
N={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P.parent/'runtime/work/build/dos64.labels').read_text().splitlines()if l.startswith('al ')}
IMAGE=(P.parent/'runtime/work/build/dos64.prg').read_bytes()
class Runtime:
 def __init__(self,corrupt=None):
  self.m=L.dos64_create();L.dos64_load(self.m,0x801,IMAGE[2:],len(IMAGE)-2);L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x35);L.dos64_enable_reu(self.m)
  if corrupt is not None:L.dos64_poke(self.m,corrupt,L.dos64_peek(self.m,corrupt)^1)
  self.call('dos64_overlay_init');self.put('dos64_overlay_reu_mib',b'\4');self.boot=self.call('dos64_overlay_bootstrap',budget=3000000)
  if not self.boot.regs.p&1:
   self.call('dos64_cpu_reset');self.put('dos64_cache_limit',b'\x20');self.call('dos64_cache_init');self.call('dos64_disk_init');self.put('dos64_disk_loaded',b'\1');self.put('dos64_disk_b_descriptor',bytes.fromhex('000018d0022800020901'))
 def close(self):L.dos64_destroy(self.m)
 def get(self,n,size=1):return bytes(L.dos64_peek(self.m,N[n]+i)for i in range(size))
 def put(self,n,b):L.dos64_load(self.m,N[n],b,len(b))
 def load(self,at,b):L.dos64_load(self.m,at,b,len(b))
 def seed(self,at,b):L.bulk_reu_seed(self.m,at,b,len(b))
 def reu(self,a,n):b=C.create_string_buffer(n);assert L.dos64_reu_read(self.m,a,b,n);return b.raw
 def call(self,n,p=0x24,budget=3000000):
  ret=0x2ff;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(N[n],0xfd,0x71,0x82,0x93,p,0,0));r=L.dos64_run(self.m,0x300,budget);assert r.status==0,(n,r.status,hex(r.regs.pc),self.get('dos64_overlay_error').hex());assert r.regs.sp==0xff,(n,r.regs.sp);return r
 def prepare(self,drive=1,track=0,head=0,fill=0xf6,ids=None,es=0,bx=0x2000):
  words=[0x509,track<<8,(head<<8)|drive,bx,0x4444,0x5555,0x6666,0x7777,es,0x9999,0xaaaa,0xbbbb,0xcccc,0xdddd];self.put('dos64_guest',struct.pack('<14H',*words))
  ids=ids if ids is not None else bytes(v for s in range(1,10)for v in(track,head,s,2))
  self.seed(((es<<4)+bx)&0xfffff,ids);self.seed(0x78,struct.pack('<HH',0x3000,0));self.seed(0x3008,bytes([fill]));self.call('dos64_cache_init')
  return words
 def format(self,**kw):
  self.prepare(**kw);return self.call('dos64_disk_transfer')
class Tests(unittest.TestCase):
 def use(self,**kw):f=Runtime(**kw);self.addCleanup(f.close);return f
 def test_actual_runtime_bootstrap_and_full_track(self):
  f=self.use();self.assertFalse(f.boot.regs.p&1);f.seed(0x180000,b'\x91'*368640);f.prepare();before=f.reu(0,0x400000);g=f.get('dos64_guest',28);r=f.call('dos64_disk_transfer');self.assertFalse(r.regs.p&1);self.assertEqual(f.get('dos64_guest',2),b'\x09\0');self.assertEqual(f.get('dos64_guest',28)[2:],g[2:]);self.assertEqual(f.get('dos64_overlay_current'),b'\10');self.assertEqual(f.get('dos64_overlay_busy'),b'\0');after=f.reu(0,0x400000);self.assertEqual(after[:0x180000],before[:0x180000]);self.assertEqual(after[0x180000:0x181200],b'\xf6'*4608);self.assertEqual(after[0x181200:],before[0x181200:]);self.assertEqual(f.get('dos64_disk_dirty',2),b'\0\1');self.assertEqual(f.get('dos64_disk_content_generation',8),bytes(4)+b'\1\0\0\0')
 def test_track_head_last_and_arena_addresses(self):
  f=self.use()
  for drive,track,head,base,fill in [(0,0,0,0x100000,0),(1,39,1,0x180000,0x3c),(0,17,1,0x380000,0xa7)]:
   f.put('dos64_disk_reu_base'if drive==0 else'dos64_disk_b_descriptor',base.to_bytes(3,'little'));f.seed(base,b'\x93'*368640);f.prepare(drive,track,head,fill);r=f.call('dos64_disk_transfer');self.assertFalse(r.regs.p&1);start=(track*2+head)*4608;self.assertEqual(f.reu(base,368640),b'\x93'*start+bytes([fill])*4608+b'\x93'*(368640-start-4608))
 def test_reordered_IDs_and_full_native_P(self):
  f=self.use();ids=bytes(v for s in [9,7,5,3,1,8,6,4,2]for v in(0,0,s,2))
  for p in range(256):
   f.prepare(ids=ids);r=f.call('dos64_disk_transfer',p=p);self.assertFalse(r.regs.p&1);self.assertEqual(r.regs.p&0xce,p&0xce)
 def test_invalid_IDs_geometry_absent_readonly_and_dma_bounds(self):
  f=self.use();cases=[]
  original=bytes(v for s in range(1,10)for v in(0,0,s,2))
  for at,value in [(0,1),(1,1),(2,0),(2,10),(3,1),(6,1)]:
   ids=bytearray(original);ids[at]=value;cases.append(({'ids':bytes(ids)},4))
  cases +=[({'track':40},4),({'head':2},4),({'drive':2},0x80),({'bx':0xffdd},9)]
  for kw,status in cases:
   before=f.reu(0x100000,0x2da000);f.prepare(**kw);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1,(kw,r.regs.a));self.assertEqual(f.get('dos64_guest',2),bytes([0,status]),kw);self.assertEqual(f.reu(0x100000,0x2da000),before)
  for name,offset,val,status in [('dos64_disk_b_descriptor',9,0,0x80),('dos64_disk_b_descriptor',8,8,4),('dos64_disk_readonly',1,1,3)]:
   old=f.get(name,10 if name.endswith('descriptor') else 2);f.prepare();L.dos64_poke(f.m,N[name]+offset,val);before=f.reu(0x180000,368640);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1);self.assertEqual(f.get('dos64_guest',2),bytes([0,status]));self.assertEqual(f.reu(0x180000,368640),before);f.put(name,old)
 def test_partial_STORE_dirty_generation_and_completed_sector_count(self):
  for page in [0,1,2,8,17]:
   f=self.use();f.format();f.seed(0x180000,b'\x91'*368640);f.prepare(fill=0x3c)
   # Warm actual coherent ID/vector/DPT pages so12 overlay DMA requests precede STORE.
   for address in [0x2000,0x78,0x3008]:f.put('dos64_address',address.to_bytes(3,'little'));self.assertFalse(f.call('dos64_mem_read').regs.p&1)
   f.put('dos64_disk_dirty',b'\0\0');f.put('dos64_disk_content_generation',bytes(8));before=f.reu(0,0x400000)
   L.dos64_reu_fail_after(f.m,12+page,17);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1,(page,r.regs.a));self.assertEqual(f.get('dos64_guest',2),bytes([page//2,0x20]));self.assertEqual(f.get('dos64_disk_host_error'),b'\0');self.assertEqual(f.get('dos64_disk_dirty',2),b'\0\1');self.assertEqual(f.get('dos64_disk_content_generation',8),bytes(4)+b'\1\0\0\0');after=f.reu(0,0x400000);count=page*256+17;self.assertEqual(after[0x180000:0x180000+count],b'\x3c'*count);self.assertEqual(after[:0x180000],before[:0x180000]);self.assertEqual(after[0x180000+count:],before[0x180000+count:])
 def test_retired_cold_RAM_and_immutable_native_RAM_UCI_ZP_preserved(self):
  f=self.use();f.put('dos64_cold_open',b'\0');f.load(0x7000,b'\xcc'*4096);self.assertTrue(f.call('dos64_overlay_init').regs.p&1)
  f.prepare();ranges=[(0x801,0x4000),(0x5000,0x6000),(0x80,0xe0),(0xc100,0xc900),(0xf000,0xfe00)]
  before=[bytes(L.dos64_peek(f.m,i)for i in range(lo,hi))for lo,hi in ranges];r=f.call('dos64_disk_transfer',p=0xcd);self.assertFalse(r.regs.p&1)
  for (lo,hi),expected in zip(ranges,before):self.assertEqual(bytes(L.dos64_peek(f.m,i)for i in range(lo,hi)),expected,(hex(lo),hex(hi)))
  self.assertEqual(L.dos64_peek(f.m,0)&0x3f,0x2f);self.assertEqual(L.dos64_peek(f.m,1)&7,5)
 def test_cache_failure_before_mutation_is_fatal_without_dirty_claim(self):
  f=self.use();f.prepare();before=f.reu(0x180000,368640);L.dos64_reu_fail_after(f.m,12,0);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1);self.assertEqual(f.get('dos64_disk_host_error'),b'\1');self.assertEqual(f.get('dos64_disk_dirty',2),b'\0\0');self.assertEqual(f.get('dos64_guest',2),b'\0\x20');self.assertEqual(f.reu(0x180000,368640),before)
 def test_each_overlay_DMA_failure_before_FORMAT_has_no_image_mutation(self):
  for skip in range(12):
   f=self.use();f.prepare();before=f.reu(0x180000,368640);L.dos64_reu_fail_after(f.m,skip,1);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1,skip);self.assertEqual(f.get('dos64_disk_dirty',2),b'\0\0');self.assertEqual(f.get('dos64_overlay_busy'),b'\0');self.assertEqual(f.get('dos64_overlay_error'),b'\5');self.assertEqual(f.reu(0x180000,368640),before)
 def test_normal_CGA_line_uses_original_GFX_after_FORMAT(self):
  f=self.use();f.format();f.put('dos64_cold_open',b'\0');f.seed(0x449,b'\6');f.seed(0x44e,b'\0\0');f.seed(0x462,b'\0');f.seed(0x466,b'\x0f');f.seed(0xb8000,b'\xaa'*80);f.call('dos64_cache_init');f.put('dos64_render_graphics_request',bytes(4));before=f.get('fc_crc',4);r=f.call('dos64_overlay_render_graphics_line',p=0xec);self.assertFalse(r.regs.p&1);self.assertEqual(f.get('dos64_render_graphics_request',4),b'\0\x28\1\0');self.assertEqual(f.get('dos64_overlay_current'),b'\5');self.assertEqual(f.get('fc_crc',4),before);self.assertEqual(bytes(L.dos64_peek(f.m,0x6000+i*8)for i in range(40)),b'\xff'*40)
 def test_generation_saturation_and_coherent_dirty_ID_cache(self):
  f=self.use();f.prepare();f.put('dos64_disk_content_generation',bytes(4)+b'\xff'*4);r=f.call('dos64_disk_transfer');self.assertFalse(r.regs.p&1);self.assertEqual(f.get('dos64_disk_content_generation',8),bytes(4)+b'\xff'*4);self.assertEqual(f.get('dos64_disk_exhausted',2),b'\0\1')
  f.prepare();f.put('dos64_address',(0x2000).to_bytes(3,'little'));f.put('dos64_mem_value',b'\1');self.assertFalse(f.call('dos64_mem_write').regs.p&1);before=f.reu(0x180000,368640);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1);self.assertEqual(f.get('dos64_guest',2),b'\0\4');self.assertEqual(f.reu(0x180000,368640),before)
 def test_cold_GFX_nested_header_body_and_padding_corruptions(self):
  meta=json.loads((P.parent/'runtime/work/build/dos64-overlay-package.json').read_text())['format'];nested=meta['nested_slot_offset']
  for at in [0x9000,0x9010,0x9000+nested,0x9010+nested,0x97ff]:
   f=self.use(corrupt=at);self.assertTrue(f.boot.regs.p&1,hex(at));self.assertEqual(f.get('dos64_overlay_ready'),b'\0');self.assertEqual(f.get('dos64_overlay_busy'),b'\0');self.assertEqual(f.reu(0x340000,0x4000),bytes(0x4000))
 def test_runtime_selector8_corruptions_refuse_but_normal_GFX_policy_unchanged(self):
  meta=json.loads((P.parent/'runtime/work/build/dos64-overlay-package.json').read_text())['format'];nested=meta['nested_slot_offset']
  for off in [16,nested,nested+16,2047]:
   f=self.use();original=f.reu(0x342000,2048);bad=bytearray(original);bad[off]^=1;f.seed(0x342000,bytes(bad));f.prepare();before=f.reu(0x180000,368640);r=f.call('dos64_disk_transfer');self.assertTrue(r.regs.p&1);self.assertEqual(f.get('dos64_overlay_error'),b'\11');self.assertEqual(f.reu(0x180000,368640),before);self.assertEqual(f.get('dos64_overlay_busy'),b'\0')
   # Ordinary GFX continues exact header-only policy; never run corrupted GFX.
   f.put('dos64_overlay_requested',b'\5');r=f.call('dos64_overlay_acquire');self.assertFalse(r.regs.p&1);f.call('dos64_overlay_release')
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P.parent/'FORMAT_RUNTIME_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'runtime':hashlib.sha256(IMAGE).hexdigest(),'scope':'actual optional FORMAT1 runtime; full UNIT1 overflow retained, not claimed'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
