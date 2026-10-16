import unittest,struct,json
from pathlib import Path
from dos_fat_populate import Populate,short
from dos_disk_inspect import Volume,inspect
import os
P=Path(os.environ['DOS64_COMPLETE_FIXTURE_PACKAGE']).resolve()
A=sorted((P/'inputs').glob('*.img'))[0].read_bytes()
HD=(P/'inputs/large/disk.raw.img').read_bytes();START=struct.unpack_from('<I',HD,454)[0]*512
class Tests(unittest.TestCase):
 def test_fat12_and_fat16_cluster_boundaries(self):
  for original in [A,HD[START:]]:
   w=Populate(original)
   for i,n in enumerate([0,1,w.cb-1,w.cb,w.cb+1,2*w.cb+7]):w.put('TEST/F'+str(i)+'.BIN',bytes([i+1])*n)
   out,r=w.finish();v=Volume(out)
   for i,n in enumerate([0,1,w.cb-1,w.cb,w.cb+1,2*w.cb+7]):self.assertEqual(v.payloads['TEST/F'+str(i)+'.BIN'],bytes([i+1])*n)
 def test_multicluster_directory_dots_and_nested_paths(self):
  w=Populate(HD[START:]);w.remove('CROSS16.BIN')
  for i in range(100):w.put('TOP/DEEP/F%03d.TXT'%i,b'x')
  out,r=w.finish();v=Volume(out)
  row=next(x for x in v.directories if x['name']=='TOP/DEEP');self.assertGreater(len(row['clusters']),1)
  self.assertEqual(v.payloads['TOP/DEEP/F099.TXT'],b'x')
 def test_root_order_system_chains_and_boot_unchanged(self):
  w=Populate(HD[START:]);v=w.v;w.remove('CROSS16.BIN');w.put('TOOLS/NEW.TXT',b'abc');out,r=w.finish();o=Volume(out)
  self.assertEqual(out[:512],v.data[:512])
  for name in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:
   old=next(x for x in v.files if x['name']==name);new=next(x for x in o.files if x['name']==name);self.assertEqual(old,new)
  self.assertEqual(out[v.root_sector*512:v.root_sector*512+96],v.data[v.root_sector*512:v.root_sector*512+96])
 def test_explicit_duplicate_replacement_and_empty_release(self):
  w=Populate(A);w.put('OWN.TXT',b'x'*2048)
  with self.assertRaisesRegex(ValueError,'explicit replacement'):w.put('OWN.TXT',b'z')
  w.put('OWN.TXT',b'',replace=True);out,r=w.finish();self.assertEqual(Volume(out).payloads['OWN.TXT'],b'')
 def test_directory_file_collision(self):
  w=Populate(A);w.put('OWN',b'')
  with self.assertRaisesRegex(ValueError,'file blocks directory'):w.put('OWN/NEW.TXT',b'x')
 def test_invalid_names_and_attributes(self):
  for name in ['../X','lower.txt','LONGER123.TXT','A.ABCD','A B','A:B','A//B','/A']:
   with self.assertRaises(ValueError):Populate(A).put(name,b'x')
  for attr in [8,16,64,128]:
   with self.assertRaises(ValueError):Populate(A).put('OWN.TXT',b'x',attr)
 def test_root_full(self):
  w=Populate(A)
  for i in range(w.root_slots-len(w.tree)+1):w.put('R%07d'%i,b'')
  with self.assertRaisesRegex(ValueError,'root directory full'):w.finish()
 def test_disk_full_does_not_mutate_source(self):
  w=Populate(A);before=bytes(A)
  with self.assertRaisesRegex(ValueError,'disk full'):w.put('BIG.BIN',bytes(len(A)*2))
  self.assertEqual(A,before)
 def test_oracle_rejects_mirror_corruption(self):
  w=Populate(A);w.put('D/A.TXT',b'hello');out,r=w.finish();bad=bytearray(out);bad[w.v.bpb['reserved_sectors']*512+4]^=1
  with self.assertRaisesRegex(ValueError,'FAT size/copies'):Volume(bad)
 def test_oracle_rejects_dotdot_corruption(self):
  w=Populate(A);w.put('D/A.TXT',b'hello');out,r=w.finish();v=Volume(out);d=v.directories[0];bad=bytearray(out);at=(v.data_sector+(d['first_cluster']-2)*v.spc)*512+32+26;struct.pack_into('<H',bad,at,2)
  with self.assertRaises(ValueError):Volume(bad)
 def test_all_floppy_archives_and_resolved_variants_exact(self):
  data=(P/'outputs/full-tp/HD.IMG').read_bytes();v=Volume(data[START:]);resolved={}
  for i,f in enumerate(sorted((P/'inputs').glob('*.img')),1):
   for name,payload in Volume(f.read_bytes()).payloads.items():
    self.assertEqual(v.payloads['DOS/DISK%d/'%i+name],payload);resolved.setdefault(name,payload)
  for name,payload in resolved.items():self.assertEqual(v.payloads['DOS/'+name],payload)
 def test_tp_manifest_rejects_changed_hash(self):
  from dos_complete_fixture import verify_tp
  meta=json.loads((P/'inputs/TP701_INSTALL_TREE.json').read_text());meta['files']['BIN/TPC.EXE']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'byte identity'):verify_tp(P/'inputs/tp701-install-tree',meta)
 def test_tp_manifest_rejects_changed_size(self):
  from dos_complete_fixture import verify_tp
  meta=json.loads((P/'inputs/TP701_INSTALL_TREE.json').read_text());meta['files']['BIN/TPC.EXE']['bytes']+=1
  with self.assertRaisesRegex(ValueError,'byte identity'):verify_tp(P/'inputs/tp701-install-tree',meta)
 def test_tp_manifest_rejects_extra_or_missing_member(self):
  from dos_complete_fixture import verify_tp
  meta=json.loads((P/'inputs/TP701_INSTALL_TREE.json').read_text());del meta['files']['BIN/TPC.EXE']
  with self.assertRaisesRegex(ValueError,'member set'):verify_tp(P/'inputs/tp701-install-tree',meta)
 def test_all_tp_install_tree_exact(self):
  v=Volume((P/'outputs/full-tp/HD.IMG').read_bytes()[START:]);manifest=json.loads((P/'inputs/TP701_INSTALL_TREE.json').read_text())
  import hashlib
  for path,entry in manifest['files'].items():
   payload=v.payloads['TP/'+path.upper()];self.assertEqual(hashlib.sha256(payload).hexdigest(),entry['sha256'])
  files=[p for p in (P/'inputs/tp701-install-tree').rglob('*') if p.is_file()];self.assertEqual(len(files),233)
  for p in files:self.assertEqual(v.payloads['TP/'+p.relative_to(P/'inputs/tp701-install-tree').as_posix().upper()],p.read_bytes())
 def test_owned_A_preserves_all_original_files_except_owned_startup_text(self):
  old=Volume(A);new=Volume((P/'outputs/full-tp/BOOT-A.IMG').read_bytes())
  self.assertEqual(new.data[:512],old.data[:512]);self.assertEqual(set(new.payloads),set(old.payloads)|{'AUTOEXEC.BAT'})
  for name,payload in old.payloads.items():
   if name not in ['AUTOEXEC.BAT','CONFIG.SYS']:self.assertEqual(new.payloads[name],payload)
  auto=new.payloads['AUTOEXEC.BAT'];self.assertNotIn(b'\n',auto.replace(b'\r\n',b''));self.assertIn(b'C:\\TP\\BIN',auto)
if __name__=='__main__':unittest.main(verbosity=2)
