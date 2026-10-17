from pathlib import Path
import hashlib,json,importlib.util,shutil,sys,zlib
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[3];p=root/'agentworking/scratch/v1-final-public-installer-chain-20261017';h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert h(p/'MANIFEST.json')=='3b0b36a523e128e939487725a7af3d18ef5fb792810c301623e12763d08548f8'
rows=json.loads((p/'MANIFEST.json').read_text())['files']
for n,r in rows.items():
 f=p/n;assert h(f)==r['sha256']and f.stat().st_size==r['bytes'],n
counts={}
for n in ('closed-producer','execution/CONFIG','execution/SETUP80','execution/CONFIG40','execution/CONFIG80'):
 q=p/n;records=json.loads((q/'INPUTS_BEFORE.json').read_text());assert records==json.loads((q/'INPUTS_AFTER.json').read_text());counts[n]=len(records)
 for name,r in records.items():
  f=Path(name);assert h(f)==r['sha256']and f.stat().st_size==r['bytes'],name
  copy=q/'copies'/r['sha256']
  assert copy.is_file()and h(copy)==r['sha256']and copy.stat().st_size==r['bytes']
spec=importlib.util.spec_from_file_location('root_disk_inspect',root/'build_support/dos_disk_inspect.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
out=p/'root-output';a,b,c=[(out/n).read_bytes()for n in ('A.IMG','B.IMG','C.IMG')];assert len(a)==len(b)==368640 and len(c)==2097152 and a!=b;D.inspect(c,(128,2,16));vol=D.Volume(c[8192:]);assert D.Volume(b).payloads=={}
num=0
for i in (1,2,3):
 for name,data in D.Volume((p/'inputs'/f'disk{i}.img').read_bytes()).payloads.items():assert vol.payloads[f'DOS/DISK{i}/'+name]==data;num+=1
assert num==58
candidate=json.loads((root/'agentworking/scratch/v1-reset-public-20261017/candidate-build/RESULT.json').read_text())
for name in ('DOS64.PRG','DOS64.REL','DOS64.MNU','START.INO','START.RCV','START.RFW'):assert {'sha256':h(out/name),'bytes':(out/name).stat().st_size}==candidate['files'][name]
tpl=(p/'producer/release-assets/START.TPL').read_bytes();rel=(p/'producer/release-assets/START.REL').read_bytes();at=int.from_bytes(rel[24:28],'little')
for folder,home,col in ((out,b'/Home',None),(p/'config/published-40',b'/New launch',40),(p/'config/published-80',b'/New launch',80)):
 start=(folder/'START.PRG').read_bytes();expected=bytearray(tpl);expected[at:at+131]=b'\xa5\x1c\xdf'+home.ljust(128,b'\0');assert start==expected
 cfg=(folder/'DOS64.CFG').read_bytes();assert len(cfg)==576 and zlib.crc32(cfg[:572])==int.from_bytes(cfg[572:],'little')and cfg[8:136].split(b'\0')[0]==home
 if col is not None:
  assert cfg[136:572]==(out/'DOS64.CFG').read_bytes()[136:572]
  assert(folder/'DOS64.INI').read_bytes()==b'[emulator]\r\ninitial_columns='+str(col).encode()+b'\r\n'
summary=json.loads((p/'FINAL_RESULT.json').read_text());assert summary['passed']and summary['actual_native_machines']==6
for name,v in summary['consumers'].items():assert v['Finish_privateSafe']and v['one_known_C_CLOSE']and v['whole4M_C_exact']and v['A_entries']==36 and v['free_bytes']==8192
archive=root/'agentworking/evidence/v1-reset-installer-config-root-20261017';archive.mkdir(exist_ok=True)
for n in ('HANDOFF.md','FINAL_RESULT.json','INDEPENDENT_OUTPUTS.json','FIRST_FAILURES.json'):shutil.copyfile(p/n,archive/n)
for name in ('closed-producer','execution/CONFIG','execution/SETUP80','execution/CONFIG40','execution/CONFIG80'):
 dest=archive/(name.replace('/','-')+'-RESULT.json');shutil.copyfile(p/name/'RESULT.json',dest)
receipt={'status':'ROOT_ACCEPTED_FINAL1506_NATIVE_SETUP_CONFIG40_80_UNMODIFIED_GENERATED_START_DOS_FINISH_MODEL','author_manifest':str(p/'MANIFEST.json'),'manifest_sha256':h(p/'MANIFEST.json'),'pins_verified':len(rows),'actual_native_machines':6,'source_execution_ledger_counts':counts,'independent_original_DOS_payloads_exact':num,'C_bytes':len(c),'C_created_native_not_host':True,'valid_empty_B_A_independent':True,'all3generated_START_exact131byte_homepatch':True,'CONFIG40_80_correct_INI_CFG_CRC_media_preserved':True,'all3DOS_fullA_listing_and_nativeCIAFinish_privateSafe_one_known_C_CLOSE_full4M_C_unchanged':True,'borrowed_source_qualified_models_no_recompile':True,'physical_human_V1_or_new_Turbo_Save_Insert_claim':False}
(root/'agentworking/evidence/v1-reset-installer-config-root-20261017.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
