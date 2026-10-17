from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-role-replay-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import argparse,json,hashlib,ctypes as C,unittest
ap=argparse.ArgumentParser();ap.add_argument('--role',choices=['unit','runtime'],required=True);ap.add_argument('--exclude-unit',action='store_true');args=ap.parse_args();role=args.role
assert json.loads((P/'UI_BUILD_RESULT.json').read_text())['role']==role
from role_oracle import verify
oracle=verify(role);excluded=[]
if role=='runtime':
 if args.exclude_unit:
  d=P.parent/('proof-excluded-unit-'+str(os.getpid()));d.mkdir()
  for f in sorted((P/'work/build').glob('dos64-tests*')):excluded.append({'name':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()});f.rename(d/f.name)
 assert not list((P/'work/build').glob('dos64-tests*')),'UNIT image/labels/sidecars must be absent for runtime proof'
os.environ['DOS64_MEDIA_TEST_ROLE']=role
from test_sequence_ui import *
from test_online_save import ROLE as actual_role,NATIVE
assert actual_role==role and NATIVE==('dos64'if role=='runtime'else'dos64-tests')
if role=='runtime':assert symbols['fixture_return']==0x0300
allowed={}
for name in ['work/build/'+NATIVE+'.prg','broker/broker.prg']:
 b=(P/name).read_bytes();allowed[(int.from_bytes(b[:2],'little'),len(b)-2,hashlib.sha256(b[2:]).hexdigest())]=name
loaded=[];original_load=L.dos64_load
def checked_load(machine,address,data,count):
 raw=data if isinstance(data,bytes)else C.string_at(data,count);key=(address,count,hashlib.sha256(raw).hexdigest());assert key in allowed,('unexpected CPU image load',key);loaded.append({'path':allowed[key],'address':address,'bytes':count,'payload_sha256':key[2]});return original_load(machine,address,data,count)
L.dos64_load=checked_load
cases=[(SequenceUI,'test01_two_actualCIA_jobs_sequences2_4_not_tickets1_2'),(SequenceFaults,'test06_allocator_sourceCRC_refuses_before_any_FILE_job')]
if role=='runtime':cases += [(SequenceUI,'test02_fresh_session_archive1_skips_to2_Ctarget2_A'),(SequenceFaults,'test07_clock_failure_in_allocator_then_recovery_cannot_Resume_or_SAVE'),(SequenceFaults,'test09_unknown_CLOSE_one_attempt_no_restore_or_Resume')]
suite=unittest.TestSuite(cls(name)for cls,name in cases);r=unittest.TextTestRunner(verbosity=2).run(suite)
out={'passed':r.wasSuccessful(),'groups':r.testsRun,'oracle':oracle,'host_return':symbols['fixture_return'],'UNIT_products_excluded':excluded,'CPU_loads':loaded,'workflow_records':records,'scope':'actual selected native role+realCIA repeatedsequence/clock/closure+modeledUCI/syntheticFAT; no coldSTART/DOS/hardware'};(P.parent/('SEQUENCE_'+role.upper()+'_RESULT.json')).write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
