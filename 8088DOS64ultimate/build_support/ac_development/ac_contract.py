"""Purpose-bound A+C registration; no mutation of prior runtime/media allowlists."""
import bootstrap
from pathlib import Path
import hashlib,json,re,zlib
from c64u_native_application import labels_from,resident_from_map,pinned_hashes,FIELDS
from c64u_native_application_support import patch_config
from c64u_native_shadow_identity import metadata_from_paths
HD_SHA='ac1cea543ad27f4fad4d3ba9d15e482bac05e9e48c4be6373c889bca4bc6c197'
A_SHA='bb75cdeb527f292c623c5ef4f0ea32388373c12f373b5546d1d371007d7abb13'
A_CRC=2865884643
SERVICE_SHA='40fe690953c245c8093c7cd5e5cb91684df7290602d8afa44dbd2e0b5b30d09e'
PURPOSE='owned-dos64-ac-development'
def sha(b):return hashlib.sha256(b).hexdigest()
def read_json(path):return json.loads(Path(path).read_text())
def checked_file(path,meta):
 b=Path(path).read_bytes()
 if len(b)!=meta['bytes'] or sha(b)!=meta['sha256']:raise ValueError('Pinned artifact differs: '+str(path))
 return b
class Registration:
 def __init__(self,proof_path,proof_sha,artifacts=None):
  raw=Path(proof_path).read_bytes()
  if sha(raw)!=proof_sha:raise ValueError('Explicit native purpose proof hash differs')
  proof=json.loads(raw);self.proof=proof;self.proof_path=Path(proof_path).resolve();self.proof_sha=proof_sha
  if proof.get('schema')!='dos64-ac-native-proof-1' or proof.get('status')!='passed':raise ValueError('Successful exact A+C native proof required')
  media=proof['media']
  if media['HD_sha256']!=HD_SHA or media['interactive_BOOT_A_sha256']!=A_SHA:raise ValueError('Exact complete DOS/TP media proof required')
  required=['no_direct_CPU_steps_or_DOS_API_shortcuts','genuine_A_boot_C_detected','VER_and_3_archive_DIR','BASIC_load_write_close_SYSTEM','original_TPC_compile_and_HELLO_run','all360_original_payloads_unchanged','strict_full_FAT16_clean']
  if any(proof['execution'].get(k) is not True for k in required):raise ValueError('Native functional acceptance incomplete')
  self.pins={str(self.proof_path):sha(raw)}
  for n,meta in proof['files'].items():checked_file(n,meta);self.pins[str(Path(n).resolve())]=meta['sha256']
  rows=proof['execution_source_closure']
  if len(rows)<300 or len({r['executed_source'] for r in rows})!=len(rows) or len({r['immutable_copy'] for r in rows})!=len(rows):raise ValueError('Complete unique source execution closure required')
  for row in rows:
   for k in ['executed_source','immutable_copy']:
    checked_file(row[k],row);self.pins[str(Path(row[k]).resolve())]=row['sha256']
    if k=='immutable_copy' and str(Path(row[k]).resolve()) not in proof['files']:raise ValueError('Immutable source copy pin missing')
  self.paths={n:Path((artifacts or {}).get(n,meta['path'])) for n,meta in proof['artifacts'].items()}
  self.blobs={n:checked_file(self.paths[n],meta) for n,meta in proof['artifacts'].items()}
  for n,path in self.paths.items():self.pins[str(path.resolve())]=sha(self.blobs[n])
  if sha(self.blobs['dos64.prg'])!=proof['target']['runtime_sha256'] or sha(self.blobs['dos64-tests.prg'])!=proof['target']['unit_sha256']:raise ValueError('Exact runtime/unit target differs')
  self.labels=labels_from(self.paths['dos64.labels']);self.segments=resident_from_map(self.paths['dos64.map'])
  self.build_identity=json.loads(self.blobs['manifest.json']);digests=pinned_hashes(self.build_identity)
  if not {proof['target']['runtime_sha256'],proof['target']['unit_sha256']}<=digests:raise ValueError('Paired native build manifest required')
  self.shadow_metadata=metadata_from_paths(self.paths['dos64-overlay-package.json'],self.paths['dos64.memory.json'],digests)
 def configure(self,media_record,floppy,hd):
  r=verify_media(media_record,floppy,hd);base=self.blobs['dos64.prg'];labels=self.labels
  if sha(base)!=self.proof['target']['runtime_sha256'] or sha(self.blobs['dos64.labels'])!=self.proof['artifacts']['dos64.labels']['sha256']:raise ValueError('Registered source bytes changed before configuration')
  if len(base)!=45057 or base[:14]!=b'\x01\x08\x0b\x08\x0a\x00\x9e2061\x00\x00\x00' or labels['dos64_entry']!=2061:raise ValueError('Original BASIC2061 packaged entry required')
  n=labels['dos64_native_config']-0x801+2
  if base[n:n+5]!=b'D64N\0' or base[n+5:n+7]!=b'\x04\x01' or base[n+8:n+10]!=b'\x1c\xdf':raise ValueError('Disabled original DF1C/4MiB config required')
  patched,patch=patch_config(base,labels['dos64_native_config'],FIELDS,r['files']['floppy']['native_path'],A_CRC)
  h=labels['hdc_config']-0x801+2
  if base[h:h+5]!=b'D64H\0':raise ValueError('Disabled exact HD config required')
  path=r['files']['hd']['native_path'].encode('ascii')+b'\0'
  if len(path)>128:raise ValueError('HD path too long')
  config=b'D64H'+bytes([0xa5,1,1,0,0,2,2,len(path)])+path+bytes(128-len(path))
  out=bytearray(patched);out[h:h+140]=config;out=bytes(out)
  allowed={n+4,n+7}|set(range(n+10,n+142))|set(range(h+4,h+140))
  if len(out)!=len(base) or any(x!=y and i not in allowed for i,(x,y) in enumerate(zip(base,out))):raise ValueError('Configuration escaped exact A+C cold blocks')
  for name,want in [('dos64_cold_open',0xa5),('dos64_native_started',0)]:
   if out[labels[name]-0x801+2]!=want:raise ValueError('Cold launch guard differs')
  return out,{'floppy':patch,'HD_config_address':labels['hdc_config'],'HD_config_sha256':sha(config),'configured_sha256':sha(out),'changed_offsets':[i for i,(x,y) in enumerate(zip(base,out)) if x!=y]}
def verify_media(record,floppy,hd):
 if len(floppy)!=368640 or sha(floppy)!=A_SHA or zlib.crc32(floppy)!=A_CRC or len(hd)!=20*1024*1024 or sha(hd)!=HD_SHA:raise ValueError('Exact purpose A+20MiBHD bytes required')
 if record.get('schema')!=1 or record.get('purpose')!=PURPOSE or record.get('status')!='verified' or record.get('created_directory') is not True or record.get('original_sources_unchanged') is not True:raise ValueError('Fresh actual complete media staging required')
 run=record.get('run_id','');directory='/usb1/DOS64_TEST/'+run
 if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',run) or record.get('remote_directory')!=directory or not re.fullmatch(r'[0-9a-f]{64}',record.get('marker_sha256','')):raise ValueError('Fresh owned media directory/marker required')
 if set(record['files'])!={'floppy','hd'}:raise ValueError('Exactly owned A and HD required')
 for role,body,leaf in [('floppy',floppy,'DOS33A.IMG'),('hd',hd,'DOSHD.IMG')]:
  item=record['files'][role];expected={'source_sha256':sha(body),'source_bytes':len(body),'remote_readback_sha256':sha(body),'remote_readback_bytes':len(body),'native_path':directory+'/'+leaf}
  if any(item.get(k)!=v for k,v in expected.items()):raise ValueError('Complete media readback binding differs: '+role)
 return record
