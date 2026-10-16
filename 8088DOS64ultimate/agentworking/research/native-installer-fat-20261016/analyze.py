#!/usr/bin/env python3
"""Read-only sizing experiment; writes JSON notes here, never a disk image."""
from pathlib import Path
import sys,json,struct
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
assert P.name=='native-installer-fat-20261016' and ROOT.name=='8088DOS64ultimate'
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.source-cache-must-remain-absent');sys.path.insert(0,str(ROOT/'build_support'))
from dos_disk_inspect import Volume,inspect,sha
from dos_fat_populate import Populate,short
BASE=ROOT/'agentworking/scratch/hd-complete-dos-tp-fixture/inputs'
inputs=[*sorted((ROOT/'reference').glob('*.img')),BASE/'small/disk.raw.img',BASE/'large/disk.raw.img',BASE/'HANGMAN.BAS',ROOT/'agentworking/scratch/hd-complete-dos-tp-fixture/outputs/full-tp/HD.IMG']
source_names=['build_support/dos_fat_populate.py','build_support/dos_complete_fixture.py','build_support/dos_disk_inspect.py','build_support/dos_hd_fixture.py','src/disk.s','src/bios.s','src/native_runtime.s','src/hd_cold.s','src/hd_bios.s','src/hd_cache.s','src/files.s','include/files.inc','include/image_import.inc','include/overlays.inc','include/hd_cache.inc','include/memory.inc','src/reu.s']
inputs.extend(ROOT/n for n in source_names);inputs.append(Path(__file__).resolve());pins={str(f):{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in inputs}
r={'research_only':True,'native_installer_implemented':False,'profiles':{},'floppies':[]};vols=[]
for path in sorted((ROOT/'reference').glob('*.img')):
 b=path.read_bytes();v=Volume(b);vols.append(v);r['floppies'].append({'path':str(path),'sha256':sha(b),'bpb':v.bpb,'width':v.width,'files':len(v.files),'labels':v.labels,'payload_bytes':sum(map(len,v.payloads.values())),'allocated_file_cluster_bytes':sum(len(f['clusters'])*v.spc*512 for f in v.files),'FAT_bytes':v.bpb['sectors_per_fat']*512,'root_bytes':v.bpb['root_entries']*32,'raw_bytes':len(b)})
resolved={};variants={}
for i,v in enumerate(vols,1):
 for n,b in v.payloads.items():resolved.setdefault(n,b);variants.setdefault(n,[]).append({'disk':i,'bytes':len(b),'sha256':sha(b)})
r['DOS_inputs']={'all_files':sum(len(v.files) for v in vols),'all_payload_bytes':sum(sum(map(len,v.payloads.values())) for v in vols),'unique_names':len(resolved),'resolved_payload_bytes':sum(map(len,resolved.values())),'archive_plus_convenient_payload_bytes':sum(sum(map(len,v.payloads.values())) for v in vols)+sum(map(len,resolved.values())),'duplicate_variants':{n:rows for n,rows in variants.items() if len(rows)>1}}
budgets={}
for profile,geo in [('small',(128,2,16)),('large',(640,4,16))]:
 path=BASE/profile/'disk.raw.img';raw=path.read_bytes();ins=inspect(raw,geo);start=ins['partition']['start_lba']*512;v=Volume(raw[start:]);spf=v.bpb['sectors_per_fat'];roots=(v.bpb['root_entries']*32+511)//512;pre=start//512
 r['profiles'][profile]={'path':str(path),'sha256':sha(raw),'geometry':geo,'raw_bytes':len(raw),'raw_sectors':len(raw)//512,'partition':ins['partition'],'bpb':v.bpb,'fat_bits':v.width,'cluster_count':v.clusters,'one_FAT_bytes':spf*512,'both_FAT_bytes':spf*1024,'root_bytes':roots*512,'metadata_in_volume_sectors':v.data_sector,'metadata_plus_MBR_gap_sectors':pre+v.data_sector,'metadata_plus_MBR_gap_bytes':(pre+v.data_sector)*512,'raw_sector_count_WRITE256_calls_onepass':len(raw)//256,'full_readback_READ512_calls':len(raw)//512,'trailing_unclustered_sectors':ins['trailing_unclustered_sectors']}
 w=Populate(raw[start:])
 for name in list(w.expected):
  if name not in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:w.remove(name)
 selected={}
 for i,src in enumerate(vols,1):
  for name,payload in src.payloads.items():
   entry=next(f for f in src.files if f['name']==name);root_at=src.root_sector*512;offset=next(pos for pos in range(0,src.bpb['root_entries']*32,32) if src.data[root_at+pos:root_at+pos+11]==short(name));template=src.data[root_at+offset:root_at+offset+32];w.put('DOS/DISK%d/'%i+name,payload,entry['attributes'],template=template);selected.setdefault(name,(payload,entry['attributes'],template))
 for name,(payload,attr,template) in sorted(selected.items()):w.put('DOS/'+name,payload,attr,template=template)
 game=(BASE/'HANGMAN.BAS').read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n');w.put('GAMES/GWBASIC.EXE',vols[2].payloads['GWBASIC.EXE']);w.put('GAMES/HANGMAN.BAS',game)
 for name,payload in [('BASIC.BAT',b'@ECHO OFF\r\nC:\\GAMES\\GWBASIC.EXE %1 %2 %3\r\n'),('HANGMAN.BAT',b'@ECHO OFF\r\nC:\\GAMES\\GWBASIC.EXE C:\\GAMES\\HANGMAN.BAS\r\n'),('AUTOEXEC.BAT',b'@ECHO OFF\r\nPATH C:\\DOS;C:\\GAMES;C:\\\r\nPROMPT $N$G\r\nC:\r\nCD \\\r\n'),('CONFIG.SYS',b'FILES=25\r\nBUFFERS=25\r\n')]:w.put(name,payload)
 import copy
 data_plan=copy.deepcopy(w)
 try:
  result,_=w.finish();now=Volume(result);filebytes=sum(len(f['clusters'])*now.spc*512 for f in now.files);dirbytes=sum(len(d['clusters'])*now.spc*512 for d in now.directories);sectors=pre+now.data_sector+(filebytes+dirbytes)//512
  budgets[profile]={'fits':True,'model_only_not_native_execution':True,'files':len(now.files),'payload_bytes':sum(map(len,now.payloads.values())),'allocated_file_bytes':filebytes,'directories':len(now.directories),'allocated_directory_bytes':dirbytes,'free_bytes':now.free_clusters*now.spc*512,'fully_initialized_metadata_and_used_cluster_sectors':sectors,'populated_write256_calls_if_zero_firstpass_then_overwrite':len(raw)//256+2*sectors,'zero_then_populate_reopen_READ512_verification_calls':len(raw)//512,'fullraw_single_composed_pass_write256_calls':len(raw)//256,'singlepass_occupied_sectors':sectors,'metadata_template_is_proposed_not_boot_acceptance':True}
  for system_name in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:data_plan.remove(system_name)
  data_only,_=data_plan.finish();data_volume=Volume(data_only);data_file_bytes=sum(len(f['clusters'])*data_volume.spc*512 for f in data_volume.files);data_dir_bytes=sum(len(d['clusters'])*data_volume.spc*512 for d in data_volume.directories)
  budgets[profile]['boot_A_data_only_C']={'files':len(data_volume.files),'payload_bytes':sum(map(len,data_volume.payloads.values())),'allocated_file_bytes':data_file_bytes,'allocated_directory_bytes':data_dir_bytes,'free_bytes':data_volume.free_clusters*data_volume.spc*512,'note':'No root system files; DOS archives/convenient DOS system copies still preserved; boot uses derived A only'}
 except ValueError as error:budgets[profile]={'fits':False,'reason':str(error)}
full=inputs[6].read_bytes();v=Volume(full[struct.unpack_from('<I',full,454)[0]*512:]);tp={n:b for n,b in v.payloads.items() if n.startswith('TP/')};r['accepted_full_collection']={'sha256':sha(full),'files':len(v.files),'payload_bytes':sum(map(len,v.payloads.values())),'allocated_file_bytes':sum(len(f['clusters'])*v.spc*512 for f in v.files),'directories':len(v.directories),'directory_clusters':sum(len(d['clusters']) for d in v.directories),'directory_bytes':sum(len(d['clusters'])*v.spc*512 for d in v.directories),'free_bytes':v.free_clusters*v.spc*512,'TP_files':len(tp),'TP_payload_bytes':sum(map(len,tp.values()))}
changed=[n for n,m in pins.items() if sha(Path(n).read_bytes())!=m['sha256']]
if changed:raise RuntimeError('Read-only inputs changed: '+str(changed))
r['source_pins']={n:m for n,m in pins.items() if n.endswith(('.py','.s','.inc'))};r['all_input_pins']=pins;r['source_and_original_images_unchanged']=True
(P/'OBSERVED_LAYOUTS.json').write_text(json.dumps(r,indent=2)+'\n');(P/'DOS_ONLY_BUDGET.json').write_text(json.dumps(budgets,indent=2)+'\n');print(json.dumps({'research_only':True,'profiles':{n:{k:q[k] for k in ['fat_bits','cluster_count','one_FAT_bytes','root_bytes','metadata_plus_MBR_gap_sectors']} for n,q in r['profiles'].items()},'dos_only':budgets,'input_pins':len(pins),'originals_unchanged':True},indent=2))
