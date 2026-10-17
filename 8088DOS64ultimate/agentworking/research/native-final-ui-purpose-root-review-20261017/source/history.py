"""Offline exact historical backup adoption. No fresh remote-byte claim."""
from pathlib import Path
import json,hashlib,zlib
from native_file import configure,sha
PHYSICAL='0ce2e435b72e8629d61e764893c4929e3325ddfa372bb1ba8ee150085280b551'
AC43='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3'
PATH='/usb1/DOS64_TEST/reu-native-8d8d2b9db2b345a3a9f3accd5d5c06f6-p1/BACKUP.REU'
def verify(work,baseline,service):
 work=Path(work);body=(work/'historical-PHYSICAL_MANIFEST.json').read_bytes()
 if sha(body)!=PHYSICAL or len(baseline)!=4194304 or sha(baseline)!=AC43:raise ValueError('Exact accepted physical history and immutableac43')
 old=json.loads(body)
 for name,r in old['files'].items():
  b=Path(name).read_bytes()
  if len(b)!=r['bytes']or sha(b)!=r['sha256']:raise ValueError('Historical referenced source changed '+name)
 closure=json.loads((work/'historical-PHYSICAL_CLOSURE.json').read_text());root=json.loads((work/'historical-ROOT-receipt.json').read_text());stage=json.loads((work/'historical-stage.json').read_text());base=(work/'native-file-base.prg').read_bytes()
 if closure.get('verdict')!='ORIGINAL_AC43_WHOLEFILE_RECOVERY_PASSED'or closure.get('child_exit_code')!=0 or closure.get('original4MiB_sha256')!=AC43 or closure.get('all4194304_afterbytes_equal_original')is not True or closure.get('full_before_and_post_FTP_all_bytes_verified')is not True:raise ValueError('Historical successful complete-source staging/recovery required')
 if root.get('physical_manifest_sha256')!=PHYSICAL or root.get('REU_sha256')!=AC43 or root.get('ROOT_original_after_allbytes_equal')!=4194304:raise ValueError('Independent historical ROOT byte proof')
 if stage.get('status')!='verified'or stage.get('source_unchanged')is not True or stage.get('backup_crc32')!=zlib.crc32(baseline)or stage.get('marker_readback_sha256')!=stage.get('marker_sha256'):raise ValueError('Historical stage/source/marker proof')
 b=stage['files']['backup'];r=stage['files']['restore']
 if b.get('remote_path')!=PATH or b.get('sha256')!=AC43 or b.get('remote_readback_sha256')!=AC43 or b.get('bytes')!=4194304 or b.get('remote_readback_bytes')!=4194304:raise ValueError('Historical exact complete backup source')
 if service!=configure(base,baseline,PATH)or service!=(work/'historical-configured-restore.prg').read_bytes()or r.get('sha256')!=sha(service)or r.get('remote_readback_sha256')!=sha(service)or r.get('bytes')!=len(service)or r.get('remote_readback_bytes')!=len(service):raise ValueError('Exact configured path/CRC/native history')
 return {'historical_files_verified':len(old['files']),'historical_physical_manifest_sha256':PHYSICAL,'backup_path':PATH,'fresh_remote_backup_before_write_read':False,'native_CRC_after_writes':True,'mandatory_final_all4MiB_host_comparison':True,'fresh_FTP_connections':0}
