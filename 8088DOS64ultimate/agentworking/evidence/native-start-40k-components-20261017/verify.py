from pathlib import Path
import sys,hashlib,json,subprocess
P=Path(__file__).resolve().parent;W=P/'work';D=lambda p:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
record={str(q):D(q)for q in P.rglob('*')if q.is_file()and(q.suffix in ['.c','.h','.hpp','.inc','.cfg','.py','.cpp','.s','.dylib','.prg']or q.name in ['DOS64.MNU','START.RCV','START.INO','START.REL','DOS64.REL'])and not(q.suffix=='.s'and q.with_suffix('.c').exists())}
(P/'EXEC_INPUTS_BEFORE.json').write_text(json.dumps(record,indent=2)+'\n')
with(P/'ACTUAL5.stdout').open('wb')as out,(P/'ACTUAL5.stderr').open('wb')as err:subprocess.run([sys.executable,'-B','test_40k.py'],cwd=W,stdout=out,stderr=err,check=True)
for n,v in record.items():assert D(Path(n))==v,n
(P/'EXEC_INPUTS_AFTER.json').write_text(json.dumps(record,indent=2)+'\n');(P/'RESULT.json').write_text(json.dumps({'status':'passed','actual_native_groups':5,'input_products_before_after':len(record),'new_slot_contents_data_fixture_only':True,'RCVcache_retired_before_overlap':True,'third_floppy_and_remaining16KiB_guards':True,'new_BINDslot_first_STORE_and_last_target_CRC_controls':True,'public_promotion':False,'physical':False},indent=2)+'\n');print('PASS actual5; unchanged source/products',len(record))
