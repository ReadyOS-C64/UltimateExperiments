from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
archive=ROOT/'agentworking/research/v1-config-relocation-gap-root-20261017';archive.mkdir()
for name in ['prepare.py','test_gap.py','record.py','INPUTS_BEFORE.json','INPUTS_AFTER.json','RESULT.json','test.stdout','test.stderr']:
 shutil.copyfile(P/name,archive/name)
manifest={str(p.relative_to(archive)):digest(p) for p in sorted(archive.rglob('*')) if p.is_file()}
(archive/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
receipt={'status':'CONFIRMED_OPEN_V1_CONFIG_RELOCATION_GAP','scratch':str(P),'archive':str(archive),'manifest':digest(archive/'MANIFEST.json'),'pins':len(manifest),'actual_native_groups':2,'source_model_inputs':len(json.loads((P/'INPUTS_BEFORE.json').read_text())),'parent_full_source_authority':'v1-final-public-producer-consumer-20261017 /92bb5658e2aeebeb7ff1b5516401aaf46e75e0c81038b0b500a262be67aebfda','CONFIG_sha256':'3deb783d9d94848b7595310d174e6ce3490bcc19b2e4510d1852f901f048635d','not_fixed':True,'native_changes':False,'physical':False,'limits':'No new compile or hardware; source/model borrowed unchanged from qualified final generated chain. Actual unmodified SETUP files seeded at original or moved directory, no host CFG home rewrite. Old saved home absent in moved model. Runtime media untouched because RI_HOME refuses before RM/CP.'}
(ROOT/'agentworking/evidence/v1-config-relocation-gap-root-20261017.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
