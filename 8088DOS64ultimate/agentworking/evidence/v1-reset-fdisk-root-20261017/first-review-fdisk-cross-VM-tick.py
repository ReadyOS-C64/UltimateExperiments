from pathlib import Path
import json,hashlib,importlib.util,shutil,sys
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[3];p=root/'agentworking/scratch/native-fdisk-reset-complete-20261017';h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert h(p/'MANIFEST.json')=='dd14e3954bf094d0e6cdcf92c8aaef60d1bb179acff5dda0dfa31df0d9fa4207'
m=json.loads((p/'MANIFEST.json').read_text())['files']
for n,r in m.items():
 f=p/n;assert f.stat().st_size==r['bytes'] and h(f)==r['sha256'],n
inputs=json.loads((p/'INPUTS_AFTER.json').read_text())['rows'];assert len(inputs)==1587
for name in ('INPUTS_BEFORE.json','SESSION_BEFORE.json'):
 for n,r in json.loads((p/name).read_text()).items():assert inputs[n]==r,n
for n,r in inputs.items():
 f=Path(n);assert f.stat().st_size==r['bytes'] and h(f)==r['sha256'],n
 f=p/'closed-inputs'/r['sha256'];assert f.stat().st_size==r['bytes'] and h(f)==r['sha256']
spec=importlib.util.spec_from_file_location('root_disk_inspect',root/'build_support/dos_disk_inspect.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
image=(p/'persisted/C.IMG').read_bytes();assert len(image)==2097152 and hashlib.sha256(image).hexdigest()=='158d819c0ca86e896cf78eff1cdd13d2987194c7e99c415dd473792d9f0b86d6'
report=D.inspect(image,(128,2,16));part=report['partition'];assert part['active']==128 and part['type']==1 and part['start_lba']==16 and part['sectors']==4080
v=D.Volume(image[16*512:4096*512]);a=D.Volume((p/'initial/A.IMG').read_bytes());assert set(v.payloads)=={'IO.SYS','MSDOS.SYS','COMMAND.COM','CONFIG.SYS'}
for n,b in v.payloads.items():assert b==a.payloads[n],n
for n in ('A.IMG','B.IMG'):assert (p/'initial'/n).read_bytes()==(p/'persisted'/n).read_bytes()
diag=json.loads((p/'RESET_DIAGNOSTICS.json').read_text());assert diag['passed_actual_normal_guest_reset']
for stage in ('before','after_date_prompt','after_fresh_C_execution'):
 d=diag[stage];assert d['HD_IVT41']=='400300f0' and d['HD_BDA475']=='01'
 assert d['PIC']['phase']=='00'and d['PIC']['isr']=='00'and d['PIC']['irr']=='00'and d['PIC']['base']=='08'
 assert d['hdb']['hdb_error']=='00'and d['hdb']['hd_error']=='00'and d['PIT_public']['error']=='00'
assert int.from_bytes(bytes.fromhex(diag['after_fresh_C_execution']['BDA_fields']['tick']),'little')>int.from_bytes(bytes.fromhex(diag['after_date_prompt']['BDA_fields']['tick']),'little')
finish=json.loads((p/'run/FINISH.json').read_text());assert finish['passed']and finish['bothknownclosed']and finish['A_B_exact']and finish['third_arena_exact']
assessment=json.loads((p/'FINAL_MEDIA_ASSESSMENT.json').read_text());assert assessment['passed']and assessment['after_fresh_DIR_TYPE_C_COMMAND_exact']and assessment['fresh_Finish']
out=root/'agentworking/evidence/v1-reset-fdisk-root-20261017';out.mkdir(exist_ok=True)
for n in ('HANDOFF.md','RESULT.json','ACCEPTANCE.json','POST_SYS_FAT.json','FINAL_MEDIA_ASSESSMENT.json','RESET_DIAGNOSTICS.json'):
 shutil.copyfile(p/n,out/n)
for n in ('FINISH.json','FRESH_BOOT.json','STEPS.json'):shutil.copyfile(p/'run'/n,out/n)
receipt={'status':'ROOT_ACCEPTED_FINAL1506_GENUINE_FDISK_WARMRESET_FORMAT_SYS_COPY_FRESH_PERSISTENCE_MODEL','manifest':str(p/'MANIFEST.json'),'manifest_sha256':h(p/'MANIFEST.json'),'pins_verified':len(m),'source_provider_model_rows_verified':len(inputs),'immutable_unique_copies_verified':len(list((p/'closed-inputs').iterdir())),'actual_guest_reset':True,'complete_C_sha256':hashlib.sha256(image).hexdigest(),'exact_original_A_system_payloads':list(v.payloads),'healthy_PIC_HD_vectors_and_ticking_guest_after_reboot':True,'two_nativeCIAFinish_A_B_third_arena_preserved':True,'host_observer_limitations_retained_no_mutating_command_replay':True,'source_prepared_initial2MiB':True,'boot_from_C_or_physical_V1_claim':False}
(root/'agentworking/evidence/v1-reset-fdisk-root-20261017.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
