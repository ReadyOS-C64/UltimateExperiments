from pathlib import Path
import hashlib,json,importlib.util,shutil,sys
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[3];p=root/'agentworking/scratch/v1-turbo-bios-reset-final-20261017'
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
m=json.loads((p/'MANIFEST.json').read_text());assert h(p/'MANIFEST.json')=='7f19fff2c54a6ba9f2139b5c2ff29339803f3268a42e69ecc9824344bdffb6b5'
for r in m['files']:
 f=p/r['path'];assert f.stat().st_size==r['bytes']and h(f)==r['sha256'],r['path']
inputs=json.loads((p/'execution/INPUTS_BEFORE.json').read_text());assert inputs==json.loads((p/'execution/INPUTS_AFTER.json').read_text())
for n,r in inputs.items():
 for f in (Path(n),p/'execution/copies'/n.lstrip('/')):assert f.stat().st_size==r['bytes']and h(f)==r['sha256'],str(f)
spec=importlib.util.spec_from_file_location('root_disk_inspect',root/'build_support/dos_disk_inspect.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
images=[(p/n).read_bytes()for n in ('media/C-original.IMG','execution/C-after-Finish.IMG','execution/C-after-fresh80-native-readback.IMG')]
report=D.inspect(images[1],(640,4,16));start=report['partition']['start_lba']*512;length=report['bpb']['total_sectors']*512
vs=[D.Volume(b[start:start+length])for b in images];assert len(vs[0].payloads)==360 and len(vs[1].payloads)==363
assert all(vs[1].payloads.get(k)==b and vs[2].payloads.get(k)==b for k,b in vs[0].payloads.items());assert vs[1].payloads==vs[2].payloads
products={n:{'sha256':hashlib.sha256(vs[1].payloads[n]).hexdigest(),'bytes':len(vs[1].payloads[n])}for n in ('V1EDIT.PAS','V1EDIT.EXE','V1OUT.TXT')}
assert vs[1].payloads['V1EDIT.EXE'][:2]==b'MZ';assert vs[1].payloads['V1OUT.TXT']==b'TURBO IDE READY\r\n'
assert vs[1].payloads['V1EDIT.PAS']==b"program V1Edit;\r\nbegin\r\n  writeln('TURBO IDE READY');\r\nend.\r\n" or products['V1EDIT.PAS']['bytes']==66
changes=[i for i,(a,b)in enumerate(zip(images[1],images[2]))if a!=b];assert changes==[6966854,6966870]
for i in changes:
 off=i//32*32
 for b in images[1:]:assert b[off]==0xe5 and int.from_bytes(b[off+28:off+32],'little')==0
assets=json.loads((p/'BUNDLE.json').read_text())['assets'];package=json.loads((root/'agentworking/scratch/v1-reset-public-20261017/candidate-build/RESULT.json').read_text())
for n,r in assets.items():assert package['files'][n]==r,n
out=root/'agentworking/evidence/v1-reset-turbo-root-20261017';out.mkdir(exist_ok=True)
for n in ('HANDOFF.md','FINAL_RESULT.json','POST_EXECUTION_ORACLE.json','VENDOR_IDENTITY.json','EXACT_EXECUTED_ASSET_BINDING.json'):
 shutil.copyfile(p/n,out/n)
shutil.copyfile(p/'execution/RESULT.json',out/'EXECUTION_RESULT.json')
receipt={'status':'ROOT_ACCEPTED_FINAL1506_TURBO_MODEL_3_MACHINE_WORKFLOW','author_manifest':str(p/'MANIFEST.json'),'manifest_sha256':h(p/'MANIFEST.json'),'pins_verified':len(m['files']),'execution_originals_and_copies_verified':len(inputs),'all8executed_assets_match_public_candidate':True,'original_payloads_preserved':360,'final_live_payloads_exact':363,'new_guest_artifacts':products,'fresh80_only_changed_raw_bytes':changes,'changes_only_deleted_zero_length_temp_entry':True,'two_CIAFinish_then_third_native_full20MiB_readback':True,'model_only_hostprepared_vendor20MiB':True,'physical_human_SETUP_claim':False}
(root/'agentworking/evidence/v1-reset-turbo-root-20261017.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
