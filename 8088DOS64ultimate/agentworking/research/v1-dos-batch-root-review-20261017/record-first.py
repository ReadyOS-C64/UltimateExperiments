from pathlib import Path
import hashlib,json,shutil,gzip
R=Path(__file__).resolve().parent;ROOT=R.parents[2];P=ROOT/'agentworking/scratch/v1-dos-batch-control-c7-corrected-20261017'
def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
assert digest(P/'MANIFEST.json')['sha256']=='734a0d17e1d6b6480995b8ab1c7762438912606d9c7da507d33a208f062b1c12'
files=json.loads((P/'MANIFEST.json').read_text())['files']
for n,w in files.items():assert digest(Path(n)if Path(n).is_absolute()else P/n)==w,n
archive=ROOT/'agentworking/research/v1-dos-batch-root-review-20261017';archive.mkdir()
selected=['HANDOFF.md','RESULT.json','FIXTURE_PROVENANCE.json','START_GUARD_ADAPTATION.json','ORIGINS.json','V1TEST.BAT','V1SUB.BAT','V1EXIT.BAT','run_batch.py','prepare.py','v1_lane.py','independent/FAT.json','execution/RESULT.json']
selected+=[str(p.relative_to(P))for p in P.rglob('CIA_FINISH.json')]
for n in selected:
 p=P/n;assert p.is_file(),n;dest=archive/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
with gzip.GzipFile(filename=str(archive/'PARENT_MANIFEST.json.gz'),mode='wb',mtime=0)as g:g.write((P/'MANIFEST.json').read_bytes())
shutil.copyfile(R/'record.py',archive/'record.py')
m={str(p.relative_to(archive)):digest(p)for p in sorted(archive.rglob('*'))if p.is_file()};(archive/'MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')
r={'status':'ACCEPT_BOUNDED_ACTUAL_DOS_BATCH_CHKDSK_AND_C_PERSISTENCE','parent_manifest':digest(P/'MANIFEST.json'),'parent_pins':len(files),'Root_all_pins_verified':True,'Root_new_execution':False,'native_cohort':'c7/407f/2f8','actual_cold_machines':2,'producer':'80columns, actualSETUP-generated2MiB C plus3explicitinputBATs; actualDOScreatedall26outputs/DEBUG_RET1','consumer':'fresh actualCONFIG40 START, genuineDOSreads/knownFinish, completeCbyteexact/zeroWRITE','inputs_and_copies_exact':146,'preserved_payloads':115,'original_DOS_payloads':112,'free_bytes_DOS_and_independent_FAT':139264,'C_WRITE05_commands':682,'C_WRITE05_count_each':256,'scope':'shell,files,dirs,batch,readonly/wildcard/binary/empty,env/prompt/control/ERRORLEVEL,DATE/TIME/VOL,read-onlyCHKDSK,DEBUGenter/write/exit,actualCIAFinish/fresh40persistence','not_closed':['FullDOSutilitymatrix','DEBUG INT3/TF/trace','FORMAT/SYS/nativeSave/freshboot/DISKCOPY-DISKCOMP nextlane','Physical/human/finalV1','20MiB C stress in this2MiB lane'], 'physical':False,'performance_claim':False,'first_failure':'Prior1e94cc6a/363 hostoracle capitalisation/DATE-TIME redirect/FINDstatus assumptions retained; no knownclosed persistence authority. Corrected successor recorded separately.','archive':{'path':str(archive),'manifest':digest(archive/'MANIFEST.json'),'pins':len(m)}}
(ROOT/'agentworking/evidence/v1-dos-batch-root-review-20261017.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
