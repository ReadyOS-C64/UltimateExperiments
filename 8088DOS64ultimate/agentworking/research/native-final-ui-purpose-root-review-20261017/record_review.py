from pathlib import Path
import json,hashlib,shutil,gzip
R=Path(__file__).resolve().parent;ROOT=R.parents[2];P=ROOT/'agentworking/scratch/native-final-ui-purpose-20261017'
def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def check(p,w):
 d=digest(p);assert d['sha256']==(w if isinstance(w,str)else w['sha256']),p
 if isinstance(w,dict)and 'bytes'in w:assert d['bytes']==w['bytes'],p
assert digest(P/'MANIFEST.json')['sha256']=='2b98652749f9ad069e8c21ce765cdd7dc72d72f9434d76fbffe01d56fd39cda1'
parent=json.loads((P/'MANIFEST.json').read_text())['files']
for name,w in parent.items():check(Path(name)if Path(name).is_absolute()else P/name,w)
launch=json.loads((P/'work/LAUNCH_MANIFEST.json').read_text())
assert digest(P/'work/LAUNCH_MANIFEST.json')['sha256']=='9919eb99904002fa708eaf41a5ef66f5b6345a65afec622f970b27a4147a0721'
for name,w in launch['files'].items():check(Path(name),w)
copies=json.loads((P/'EXECUTED_SOURCE_COPIES.json').read_text())
for name,w in copies.items():check(Path(name),w);check(Path(w['copy']),w)
assert json.loads((R/'OFFLINE.stdout').read_text())['status']=='OFFLINE_CONSTRUCTOR_PASS_NO_DEVICE_CALLS'
assert not (R/'OFFLINE.stderr').read_bytes()
for name in ['dispatch-claim','supervisor.pid','detached']:assert not(P/'work'/name).exists()
assert (ROOT/'agentworking/ACTIVE_HARDWARE_SESSION.json').read_bytes()==(P/'ACTIVE-predecessor.json').read_bytes()
(R/'FIRST_REVIEW_FAILURE.json').write_text(json.dumps({'scope':'ROOT metadata reader before any native execution/network','error':'FileNotFoundError: parent/status','cause':'Root initially iterated wrapper keys rather than MANIFEST.files. Exact immutable manifest digest was correct; normalized only Root reader. No parent/source/product changed.','native_failure':False},indent=2)+'\n')
archive=ROOT/'agentworking/research/native-final-ui-purpose-root-review-20261017';archive.mkdir()
for name in ['HANDOFF.md','RESULT.json','PARENTS.json','INTAKE.json','ACTUAL_PRODUCT.json','DETACHED_CONTROL.json','MANIFEST.json','EXECUTED_SOURCE_COPIES.json']:
 shutil.copyfile(P/name,archive/('parent-'+name))
for name in ['CLOSED_test_product','CLOSED_test_product_policy','CLOSED_test_ui_purpose','CLOSED_test_detached','CLOSED_OFFLINE']:
 for suffix in ['stdout','stderr']:shutil.copyfile(P/(name+'.'+suffix),archive/(name+'.'+suffix))
with gzip.GzipFile(filename=str(archive/'LAUNCH_MANIFEST.json.gz'),mode='wb',mtime=0)as g:g.write((P/'work/LAUNCH_MANIFEST.json').read_bytes())
for source in copies:
 target=archive/'source'/Path(source).name;target.parent.mkdir(exist_ok=True);shutil.copyfile(source,target)
for name in ['record_review.py','OFFLINE.stdout','OFFLINE.stderr','FIRST_REVIEW_FAILURE.json']:shutil.copyfile(R/name,archive/name)
manifest={str(p.relative_to(archive)):digest(p)for p in sorted(archive.rglob('*'))if p.is_file()}
(archive/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
review={'status':'ACCEPT_CONCRETE_STARTUP_UI_CANCEL_PURPOSE_PENDING_HUMAN_AVAILABILITY','parent_manifest':digest(P/'MANIFEST.json'),'parent_pins':len(parent),'launch_manifest':str(P/'work/LAUNCH_MANIFEST.json'),'launch_manifest_identity':digest(P/'work/LAUNCH_MANIFEST.json'),'launch_inputs_exact_after_Root_offline':len(launch['files']),'executed_host_source_copies_exact':len(copies),'Root_offline_constructor':{'exit':0,'socket_connect_forbidden':True,'stdout':digest(R/'OFFLINE.stdout')},'reviewed':'product/product_transport/ui_backend/preserved_product/purpose/launch/setup_observer and focused product/policy/detached controls; native bc_files_closed/selectable correspondence; all consumed authority pins required','inherited_controls':{'actual_Peddle':6,'transport_cleanup':7,'constructor_missing_pin':7,'detached_surrogate':3},'Root_new_native_replay':False,'single_dispatch_condition':'Human explicitly available for short physical native keyboard/RunStop test, soleCIA ownership and exact currentpredecessor/source audits still pass; exact reviewed9919 manifest/wrapper only. No device operation in this review.','scope':'SETUP startup/human UI/cancel component; sixteen CREATE_NEW sourcefiles; knownclosed terminal before changed4M/one originalrestore/final4M; 600score+90BASIC+45profile,120shuman/180srestore reserve','limits':['No fullinstall/DOS/Turbo/V1 acceptance','Trusted registeredLOAD/bootstrap; hidden preSYS RAM equality unverified','Human window expiry/unknownwriter retainsreservation with no syntheticSTOP/reset/restore','No restoredoriginal CPU/RAM/application claim; coldBASIC only','Historical backupadoption explicit/nativeCRC/finalindependent4M required; no upper12M'], 'physical':False,'device_calls':0,'dispatch_occurred':False,'human_availability_confirmed':False,'ACTIVE_unchanged':True,'archive':{'path':str(archive),'manifest':digest(archive/'MANIFEST.json'),'pins':len(manifest)}}
(ROOT/'agentworking/evidence/native-final-ui-purpose-root-review-20261017.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(review,indent=2))
