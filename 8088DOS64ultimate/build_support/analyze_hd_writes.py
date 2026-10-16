"""Independently explain real guest HD writes against explicit pinned fixtures."""
from pathlib import Path
import argparse,json,hashlib,collections
from dos_disk_inspect import inspect,read_volume_file
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--small-manifest',type=Path,required=True);parser.add_argument('--large-manifest',type=Path,required=True);parser.add_argument('--output-dir',type=Path,default=Path('build'));args=parser.parse_args();out=args.output_dir
sha=lambda b:hashlib.sha256(b).hexdigest()
for tag,manifest_path in [('small',args.small_manifest),('large',args.large_manifest)]:
 manifest=json.loads(manifest_path.read_text());assert manifest['schema_version']==1 and manifest['complete']and manifest['original_images_unchanged']and manifest['source_system_files_identical']
 g=manifest['geometry'];geom=(g['cylinders'],g['heads'],g['sectors_per_track']);source=Path(manifest['raw_image']['path']);source=source if source.is_absolute()else manifest_path.parent/source;original=source.read_bytes();assert len(original)==manifest['raw_image']['bytes']and sha(original)==manifest['raw_image']['sha256'];modified=(out/f'{tag}-modified.img').read_bytes();trace=json.loads((out/f'{tag}-write-trace.json').read_text())
 before=inspect(original,geom);assert json.loads(json.dumps(before))==manifest['inspection'];after=inspect(modified,geom);assert trace['original_sha256']==sha(original)and trace['modified_sha256']==sha(modified)
 start=before['partition']['start_lba'];bpb=before['bpb'];spf=bpb['sectors_per_fat'];reserved=bpb['reserved_sectors'];root=start+reserved+2*spf;data=start+before['data_sector_in_volume'];spc=bpb['sectors_per_cluster'];owners=collections.defaultdict(set)
 for view in [before,after]:
  for f in view['files']:
   for c in f['clusters']:
    for sector in range(data+(c-2)*spc,data+(c-1)*spc):owners[sector].add(f['name'])
 def kind(lba):
  if start+reserved<=lba<start+reserved+spf:return ['FAT1']
  if start+reserved+spf<=lba<root:return ['FAT2']
  if root<=lba<data:return ['root_directory']
  return sorted(owners[lba])or['unallocated_or_reserved']
 changed=[]
 for lba in range(len(original)//512):
  x,y=original[lba*512:(lba+1)*512],modified[lba*512:(lba+1)*512]
  if x!=y:changed.append({'lba':lba,'kind':kind(lba),'bytes_changed':sum(a!=b for a,b in zip(x,y)),'before_sha256':sha(x),'after_sha256':sha(y)})
 permitted={'FAT1','FAT2','root_directory','BOOTVER.TXT','BOOTDIR.TXT','BOOTOK.TXT'}
 for change in changed:assert set(change['kind'])<=permitted,change
 directory_changes=[]
 for off in range(root*512,data*512,32):
  x,y=original[off:off+32],modified[off:off+32]
  if x!=y:
   name=y[:8].decode('ascii').rstrip()+'.'+y[8:11].decode('ascii').rstrip();assert name in permitted,name
   directory_changes.append({'name':name,'byte_offsets_changed':[i for i in range(32)if x[i]!=y[i]],'before_hex':x.hex(),'after_hex':y.hex()})
 bf={f['name']:f for f in before['files']};af={f['name']:f for f in after['files']}
 assert bf.keys()==af.keys()
 for name in bf:
  if name not in permitted:assert bf[name]==af[name],name
 vol=modified[start*512:]
 assert b'MS-DOS Version 3.30' in read_volume_file(vol,'BOOTVER.TXT')
 assert read_volume_file(vol,'BOOTOK.TXT')==b'DOS64_HD_BOOT_OK \r\n'
 assert b'File(s)' in read_volume_file(vol,'BOOTDIR.TXT')
 summaries=[];counts=collections.Counter();byphase=collections.Counter()
 for i,w in enumerate(trace['file_writes']):
  q=trace['requests'][w['owner_request']];r=q['registers'];assert r[0]>>8==3 and q['phase']==0 and w['phase']==0
  cy=(r[1]>>8)|((r[1]&0xc0)<<2);he=r[2]>>8;se=r[1]&63;first=((cy*geom[1])+he)*16+se-1
  source_bytes=bytes.fromhex(q['source_hex']);offset=w['offset']-first*512;n=w.get('bytes',512);assert n in (256,512);payload=source_bytes[offset:offset+n]
  assert len(payload)==n and sha(payload)==w['payload_sha256']
  category=kind(w['lba']);assert set(category)<=permitted,category
  for name in category:counts[name]+=1
  byphase[str(w['phase'])]+=1
  summaries.append({'write_ordinal':i+1,'lba':w['lba'],'bytes':n,'half':w.get('half',0),'kind':category,'request_ordinal':w['owner_request'],'AH':r[0]>>8,'AL':r[0]&255,'CHS':[cy,he,se],'ES_BX':f'{r[8]:04X}:{r[3]:04X}','guest_return_CS_IP':f"{q['return_cs']:04X}:{q['return_ip']:04X}",'payload_sha256':w['payload_sha256']})
 assert sum((q['registers'][0]&255)for q in trace['requests']if q['registers'][0]>>8==3)*512==sum(w.get('bytes',512)for w in trace['file_writes'])
 logical_logs=[]
 for name in ['BOOTVER.TXT','BOOTDIR.TXT','BOOTOK.TXT']:
  prior=read_volume_file(original[start*512:],name);current=read_volume_file(vol,name)
  logical_logs.append({'name':name,'before_size':len(prior),'after_size':len(current),'before_sha256':sha(prior),'after_sha256':sha(current),'logical_payload_changed':prior!=current})
 repeated=[];previous={}
 for i,w in enumerate(trace['file_writes']):
  q=trace['requests'][w['owner_request']];r=q['registers'];cy=(r[1]>>8)|((r[1]&0xc0)<<2);first=((cy*geom[1]+(r[2]>>8))*16+(r[1]&63)-1)*512;n=w.get('bytes',512);key=(w['lba'],w.get('half',0),n);payload=bytes.fromhex(q['source_hex'])[w['offset']-first:w['offset']-first+n]
  if key in previous:
   ordinal,prior=previous[key];diff=[j for j in range(n)if prior[j]!=payload[j]]
   repeated.append({'previous_ordinal':ordinal,'ordinal':i+1,'lba':w['lba'],'bytes':n,'half':w.get('half',0),'kind':kind(w['lba']),'changed_byte_offsets':diff,'previous_text':prior.rstrip(b'\0').decode('ascii','replace')if kind(w['lba'])==['BOOTDIR.TXT']else None,'current_text':payload.rstrip(b'\0').decode('ascii','replace')if kind(w['lba'])==['BOOTDIR.TXT']else None})
  previous[key]=(i+1,payload)
 report={'fixture_manifest_sha256':sha(manifest_path.read_bytes()),'fixture_manifest':str(manifest_path),'logical_log_files':logical_logs,'repeated_sector_writes':repeated,'status':'all writes explained by actual guest AH03 source bytes and allowed FAT/root/log-file sectors','source_sha256_unchanged':sha(source.read_bytes()),'modified_sha256':sha(modified),'autoexec_text':read_volume_file(original[start*512:],'AUTOEXEC.BAT').decode('ascii'),'file_write_count':len(summaries),'counts_by_sector_owner':dict(counts),'counts_by_phase':dict(byphase),'changed_sectors':changed,'root_entry_changes':directory_changes,'writes':summaries,'before':before,'after':after}
 (out/f'{tag}-write-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
 print(tag,json.dumps({'writes':len(summaries),'owners':dict(counts),'changed_sectors':[(c['lba'],c['kind'])for c in changed],'autoexec':report['autoexec_text']}))
