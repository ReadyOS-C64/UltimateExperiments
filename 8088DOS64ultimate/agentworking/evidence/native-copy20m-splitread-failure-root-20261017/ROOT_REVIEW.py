from pathlib import Path
import json,hashlib,shutil,sys,os
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[3];p=root/'agentworking/scratch/native-copy20m-splitread-purpose-20261017';physical=p/'physical';h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert h(physical/'MANIFEST.json')=='11e03d3c99c6ca01ee2ab45d2fbaf47b11e54abae1ceab7608535598aae7a657'
files=json.loads((physical/'MANIFEST.json').read_text())['files']
for n,r in files.items():
 f=physical/n;assert f.stat().st_size==r['bytes']and h(f)==r['sha256'],n
m=json.loads((p/'work/LAUNCH_MANIFEST.json').read_text());sys.path.insert(0,str(p/'work'));from purpose import sources
streams,directory,reader=sources(m);s=physical/'retained-run/session';expected=Path(m['expected_file']).read_bytes();prefix=(s/'DOSHD-independent20MiB.img').read_bytes();assert len(prefix)==2490368 and prefix==expected[:len(prefix)]
assert h(s/'initial4MiB.bin')=='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3'
for i in range(1,77):
 halves=[next(s.glob(f'RAM-half-*-file_frame_RAM_{i}-{part}.bin'))for part in (0,1)]
 raw=b''.join(f.read_bytes()for f in halves);assert len(raw)==65536;assert reader.frame(raw,i)==expected[(i-1)*32768:i*32768]
 receipts=[json.loads(f.with_suffix('.json').read_text())for f in halves];assert receipts[0]['epoch']==receipts[1]['epoch']and receipts[0]['endpoint']==receipts[1]['endpoint']
for i,route in [(1,'machine:writemem?address=260&data=4C00'),(2,'machine:pause'),(3,'configs/U64%20Specific%20Settings/Turbo%20Control?value=C64U%20Turbo%20Registers')]:
 r=json.loads((s/f'HTTP-failure-{i:03}.json').read_text());assert r['route']==route and r['received_bytes']==0 and(s/f'HTTP-failure-{i:03}.bin').read_bytes()==b''
direct=json.loads((physical/'DIRECT_RESULT.json').read_text());assert direct['GO_ACKs']==75 and direct['GO76_attempted']is False
for pid in (38328,38335):
 try:os.kill(pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError(pid)
assert h(root/'agentworking/ACTIVE_HARDWARE_SESSION.json')=='364cdf7f114f4334ca94bc6c52f5c5d8187685ce13d129d6d3805d2d05a43d70'
out=root/'agentworking/evidence/native-copy20m-splitread-failure-root-20261017';out.mkdir(exist_ok=True)
for n in ('DIRECT_RESULT.json','PROCESS_FINAL.json','SOURCE_FINAL.json','HANDOFF.md'):shutil.copyfile(physical/n,out/n)
receipt={'status':'ROOT_ACCEPTED_FAILED_PHYSICAL_COPY_READBACK_PREFIX_ONLY_RESERVED','manifest':str(physical/'MANIFEST.json'),'manifest_sha256':h(physical/'MANIFEST.json'),'pins_verified':len(files),'actual_source_mapping_CRC_frames_revalidated':76,'durable_prefix_bytes':len(prefix),'prefix_exact_expected':True,'initial4MiB_ac43_exact':True,'first_failure':'SEQ76 PUT reset54, zero bytes before headers; GO76 never attempted','subsequent_pause_and_profile_restore_PUTs_also_failed':True,'original_profile_restored':False,'last_observed_turbo_control':'Manual','FILES_known_quiet':False,'BASIC_resume_final4MiB_full20MiB_product_acceptance':False,'owned_PIDs_absent':[38328,38335],'reaped_exit':1,'watchdog':False,'current_ACTIVE_sha256':h(root/'agentworking/ACTIVE_HARDWARE_SESSION.json'),'next':'Sole CIA owner offline source-backed READONLY WAIT76 cancellation/recovery analysis; no current recovery dispatch or retry.'}
(root/'agentworking/evidence/native-copy20m-splitread-failure-root-20261017.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
