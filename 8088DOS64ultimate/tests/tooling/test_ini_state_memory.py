import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-state-memory-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import importlib.util,re,unittest
s=importlib.util.spec_from_file_location('memory_sut',ROOT/'build_support/verify_memory.py');v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class State(unittest.TestCase):
 def setUp(self):
  p=ROOT/'build';self.map=(p/'dos64.map').read_text();self.labels=(p/'dos64.labels').read_text();self.prg=(p/'dos64.prg').read_bytes();self.p=p;self.symbols={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in self.labels.splitlines()if l.startswith('al ')};self.base=self.symbols['dos64_bios_initial_mode']
 def check(self,**kw):
  p=self.p;args={'map_text':self.map,'labels_text':self.labels,'prg':self.prg,'overlay_payloads':{n:(p/('dos64-resident.prg.'+f+'.bin')).read_bytes()for n,f in [('FILECODE','files'),('RENDERCODE','render'),('INPUTCODE','input'),('IRQMAIN','pit'),('GFXCODE','gfx'),('HDCODE','hd'),('DISKCODE','disk')]},'import_payload':(p/'dos64-resident.prg.import.bin').read_bytes(),'shadow_payload':(p/'dos64-resident.prg.hdb.bin').read_bytes(),'saver_payload':(p/'dos64-resident.prg.saver.bin').read_bytes()};args.update(kw);return v.verify(**args)
 def test_actual_new_eight_byte_defaults_and_positions_pass(self):
  self.assertTrue(self.check()['passed']);self.assertEqual(self.prg[self.base-0x801+2:self.base-0x801+10],bytes.fromhex('03A5000000000000'))
 def test_every_default_byte_is_required(self):
  for i in range(8):
   p=bytearray(self.prg);p[self.base-0x801+2+i]^=1;self.assertFalse(self.check(prg=p)['passed'],i)
 def test_every_named_offset_missing_or_moved_is_refused(self):
  for name in ['dos64_bios_initial_mode','dos64_cold_open','dos64_cold_error','n_started','dos64_native_started','hdb_boot_drive','hdb_extension_ready','dos64_loader_required','dos64_options_required']:
   for delta in [None,1]:
    changed=re.sub(r'^al [0-9A-F]+ \.'+name+r'$', ''if delta is None else f'al {self.symbols[name]+delta:06X} .{name}',self.labels,flags=re.M);self.assertFalse(self.check(labels_text=changed)['passed'],(name,delta))
 def test_state_span_cannot_expand_shrink_or_leave_resident_bounds(self):
  for start,size in [(self.base,7),(self.base,9),(0x4000,8)]:
   changed=re.sub(r'^NATIVESTATE\s+.*$',f'NATIVESTATE {start:06X} {start+size-1:06X} {size:06X} 00001',self.map,flags=re.M);self.assertFalse(self.check(map_text=changed)['passed'],(start,size))
 def test_explicit_legacy_five_and_six_byte_schemas_stay_strict(self):
  # Structural legacy fixtures only; never claim executing rewritten old code.
  for loader,count in [(True,6),(False,5)]:
   mp=re.sub(r'^NATIVESTATE\s+.*$',f'NATIVESTATE {self.base:06X} {self.base+count-1:06X} {count:06X} 00001',self.map,flags=re.M)
   labels=re.sub(r'^al [0-9A-F]+ \.(?:dos64_bios_initial_mode|dos64_options_required)$','',self.labels,flags=re.M)
   for name,offset in [('dos64_cold_open',0),('dos64_cold_error',1),('n_started',2),('dos64_native_started',2),('hdb_boot_drive',3),('hdb_extension_ready',4),('dos64_loader_required',5)]:
    labels=re.sub(r'^al [0-9A-F]+ \.'+name+r'$',f'al {self.base+offset:06X} .{name}',labels,flags=re.M)
   labels=re.sub(r'^al [0-9A-F]+ \.__MAIN_LAST__$',f'al {self.base+count:06X} .__MAIN_LAST__',labels,flags=re.M)
   raw=bytearray(self.prg);at=self.base-0x801+2;raw[at:at+8]=bytes(8);raw[at]=0xa5
   payloads={n:(self.p/('dos64-resident.prg.'+f+'.bin')).read_bytes()for n,f in [('FILECODE','files'),('RENDERCODE','render'),('INPUTCODE','input'),('IRQMAIN','pit'),('GFXCODE','gfx'),('HDCODE','hd'),('DISKCODE','disk')]}
   if not loader:
    mp=re.sub(r'^(LOADERCOLD|LOADERADOPT)\s.*\n','',mp,flags=re.M)
    labels=re.sub(r'^al [0-9A-F]+ \.(?:dos64_loader_\S*|__LOADER\S*)$','',labels,flags=re.M)
    old=self.symbols['__FILE_LAST__']-307;labels=re.sub(r'^al [0-9A-F]+ \.__FILE_LAST__$',f'al {old:06X} .__FILE_LAST__',labels,flags=re.M)
    raw[0x4000-0x801+2:0x4400-0x801+2]=bytes(1024);f=0x6000-0x801+2;raw[f+6:f+8]=(1464).to_bytes(2,'little');raw[f+16+1464:f+2048]=bytes(2048-16-1464);payloads['FILECODE']=payloads['FILECODE'][:1464]
   result=self.check(map_text=mp,labels_text=labels,prg=raw,overlay_payloads=payloads);self.assertTrue(result['passed'],result['errors'])
   for i in range(count):
    wrong=bytearray(raw);wrong[at+i]^=1;self.assertFalse(self.check(map_text=mp,labels_text=labels,prg=wrong,overlay_payloads=payloads)['passed'],(count,i))
if __name__=='__main__':unittest.main(verbosity=2)
