"""Independent complete20MiB FAT/payload oracle for bounded genuine DOS writes."""
import bootstrap,struct
from dos_disk_inspect import Volume,inspect
from ac_contract import sha
ALLOWED={'CHECK.BAS','BASIC.TXT','HELLO.EXE','TP/BUILD.LOG','TP/HELLO.EXE','TP/HELLO.TXT','TP/DONE.TXT'}
HELLO_SHA='0a3e4e74192374885e80a5d7709c020fdde26e69eb9a1259cc8c0c56bf55eaca'
def _cluster_sectors(v,cluster):
 start=v.data_sector+(cluster-2)*v.spc
 return set(range(start,start+v.spc))
def _directory_slots(v):
 slots={};active={}
 regions=[('',[(v.root_sector*512,v.bpb['root_entries']*32)])]
 for row in v.directories:regions.append((row['name'],[((v.data_sector+(c-2)*v.spc)*512,v.spc*512) for c in row['clusters']]))
 for prefix,spans in regions:
  ended=False
  for start,count in spans:
   for at in range(start,start+count,32):
    raw=v.data[at:at+32];slots[at]=raw
    if raw[0]==0:ended=True
    if ended or raw[0]==0xe5:continue
    base=raw[:8].decode('cp437').rstrip();ext=raw[8:11].decode('cp437').rstrip();name=base+('.'+ext if ext else '')
    full=prefix+'/'+name if prefix else name;active[full]=(at,raw)
 return slots,active

def verify_owned_mutations(source,changed):
 """Independent sector/entry/allocation ownership; caller separately restricts added names."""
 inspect(source,(640,4,16));inspect(changed,(640,4,16));start=struct.unpack_from('<I',source,454)[0]*512
 if source[:start+512]!=changed[:start+512]:raise ValueError('MBR/partition/boot changed')
 before=Volume(source[start:]);now=Volume(changed[start:]);oldrows={r['name']:r for r in before.files};newrows={r['name']:r for r in now.files};new_names=set(newrows)-set(oldrows)
 for name,row in oldrows.items():
  if newrows.get(name)!=row:raise ValueError('Original file bytes/attributes/allocation changed: '+name)
 before_slots,before_entries=_directory_slots(before);after_slots,after_entries=_directory_slots(now)
 for name,(at,raw) in before_entries.items():
  if name not in after_entries or after_entries[name]!=(at,raw):raise ValueError('Original directory-entry metadata/location changed: '+name)
 after_at={at:name for name,(at,raw) in after_entries.items()}
 for at,raw in before_slots.items():
  actual=now.data[at:at+32]
  if actual!=raw and not(raw[0] in (0,0xe5) and after_at.get(at) in new_names):raise ValueError('Unowned original directory slot/padding changed')
 allowed=set();b=before.bpb
 for mirror in range(2):allowed.update(range(b['reserved_sectors']+mirror*b['sectors_per_fat'],b['reserved_sectors']+(mirror+1)*b['sectors_per_fat']))
 allowed.update(range(before.root_sector,before.data_sector))
 dirs_before={r['name']:r for r in before.directories};dirs_after={r['name']:r for r in now.directories}
 if set(dirs_before)!=set(dirs_after):raise ValueError('Unexpected directory tree mutation')
 for name,row in dirs_before.items():
  after=dirs_after[name]
  if row['first_cluster']!=after['first_cluster'] or after['clusters'][:len(row['clusters'])]!=row['clusters']:raise ValueError('Original directory allocation moved')
  for c in after['clusters']:
   if c not in row['clusters'] and before.entry(c)!=0:raise ValueError('Directory extension took a nonfree original cluster')
   allowed.update(_cluster_sectors(now,c))
 for name in new_names:
  for c in newrows[name]['clusters']:
   if before.entry(c)!=0:raise ValueError('Generated file took a nonfree original cluster')
   allowed.update(_cluster_sectors(now,c))
 absolute={sector+start//512 for sector in allowed};sectors=[i//512 for i in range(0,len(source),512) if source[i:i+512]!=changed[i:i+512]]
 if not set(sectors)<=absolute:raise ValueError('Changed sector outside exact FAT/root/directory/new-file ownership')
 return {'passed':True,'allowed_changed_sectors':sorted(absolute),'changed_sectors':sectors,'original_file_entries_and_allocations_exact':True,'original_directory_entries_exact':True}

def verify_collection(source,changed,complete=True):
 if len(source)!=20*1024*1024 or len(changed)!=len(source):raise ValueError('Complete exact20MiB image required')
 baseline=inspect(source,(640,4,16));after=inspect(changed,(640,4,16));start=struct.unpack_from('<I',source,454)[0]*512
 if source[:start+512]!=changed[:start+512]:raise ValueError('MBR/partition/boot changed')
 before=Volume(source[start:]);now=Volume(changed[start:])
 if len(before.payloads)!=360:raise ValueError('Exact360-file source collection required')
 for name,body in before.payloads.items():
  if now.payloads.get(name)!=body:raise ValueError('Original collection file changed: '+name)
 added=set(now.payloads)-set(before.payloads)
 if not added<=ALLOWED or complete and added!=ALLOWED:raise ValueError('Only bounded exact generated/proof paths may be added')
 if len(now.directories)!=len(before.directories) or now.bad_clusters!=before.bad_clusters:raise ValueError('Unexpected directory/badcluster changes')
 for name in added:
  if len(now.payloads[name])>8192:raise ValueError('Generated proof file exceeds bound')
 for name in ['TP/HELLO.EXE','HELLO.EXE']:
  if name in added and sha(now.payloads[name])!=HELLO_SHA:raise ValueError('Compiled/copied HELLO bytes differ from exact independent/native proof')
 for name,expected in [('BASIC.TXT',b'DOS64 BASIC OK\r\n\x1a'),('TP/HELLO.TXT',b'HELLO FROM TURBO PASCAL 7.01 ON DOS 3.3\r\n'),('TP/DONE.TXT',b'TP701_COMPILE_RUN_OK \r\n')]:
  if name in added and now.payloads[name]!=expected:raise ValueError('Generated closed guest result differs: '+name)
 if 'CHECK.BAS' in added and b'30 CLOSE #1:SYSTEM' not in now.payloads['CHECK.BAS']:raise ValueError('Genuine BASIC SYSTEM fixture missing')
 ownership=verify_owned_mutations(source,changed);sectors=ownership['changed_sectors']
 if len(sectors)>512:raise ValueError('Generated workflow changed more than512 sectors')
 return {'passed':True,'complete_workflow':complete,'original_files_checked':360,'added_files':sorted(added),'changed_sectors':sectors,'strict_full_FAT16_clean':True,'inspection_sha256':after['sha256'],'free_bytes':after['free_bytes'],'sector_and_entry_ownership':ownership}
