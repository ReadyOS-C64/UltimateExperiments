"""Source-authenticated corrected62 adaptation of the released mutation soak.

The actual seeded workload, independent canonical/history/clipboard model,
fullpixel checkpoints, fragmentation and instruction-observed typed DMA guards
remain unchanged. Only obsolete cohort identity/scope text is replaced. CPU
modeled ROM/source import; no native/hardware/timing or full-goal claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,zipfile
import test_stress_registered as prior
import test_cache_rebase_registered as identity
ROOT=identity.ROOT
BASE=ROOT/'build/rebase-refusal-committed/20261026T235419243481Z/fixture'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def source_view(out,base):
 out.mkdir(parents=True);project=out/'project';project.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   path=project/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
 (project/'build').symlink_to(base/'build',target_is_directory=True)
 seal=identity.authenticate(base,project)
 (out/'authentication.json').write_text(json.dumps(seal,indent=2)+'\n')
 return project,seal


def adapted(out):
 source=inspect.getsource(prior.run)
 replacements=[
  ("assert len(manifest['names'])==59 and hashlib.sha256(disk).hexdigest()=='446a5fa688886d7065b1da21491cf75c76f497bc111c37b83c3673c1a930171e'", "assert len(manifest['names'])==62 and manifest['names'][-2:]==['parse','xform'] and hashlib.sha256(disk).hexdigest()==manifest['disk_sha256']"),
  ("assets=59,C33=", "assets=62,C33="),
  ("result=ns['run'](out,base,rounds,seed);result['registered_seal']=seal;", "ns['run'](out,base,rounds,seed);result=json.loads((out/'result.json').read_text());result['registered_seal']=seal;"),
  ("Registered59 CPU scoped profile;", "Registered corrected62 CPU scoped profile;"),
 ]
 for old,new in replacements:
  assert source.count(old)==1,('review legacy adaptation',old,source.count(old));source=source.replace(old,new)
 (out/'registered62-run.py').write_text(source)
 namespace=dict(vars(prior));exec(compile(source,str(out/'registered62-run.py'),'exec'),namespace)
 return namespace['run']


def run(out,base,banks,rounds=96,seed=0x53454f53):
 out.mkdir(parents=True);project,seal=source_view(out/'source-view',base)
 import font_fixture
 font_fixture.ROOT=base
 invoke=adapted(out);groups={}
 for count in banks:
  dest=out/f'banks{count}';print('PROFILE',count,flush=True)
  result=invoke(dest,base,count,rounds,seed)
  assert result['status']=='passed'and result['physical_banks']==count and result['rounds']==rounds
  assert result['identity']['prg_sha256']==seal['resident'] and result['registered_seal']['assets']==62
  groups[str(count)]=dict(status=result['status'],events=len(result['events']),checks=len(result['checks']),mutation_history_operations=result['mutation_history_operations'],checkpoint_banks=result['checkpoint_max_allocated_banks'],checkpoint_objects=result['checkpoint_max_objects'],raw_STA_scope='Raw STA peaks include reset initialization; not live physical allocation highwater.',pixel_checks=len(result['pixel_checks']),peak_banks=result['observed_STA_bank_peak'],peak_objects=result['observed_STA_object_peak'],piece_peak=result['piece_peak'],peak_instructions=result['peak_instructions'],result=str(dest/'result.json'),result_sha256=sha(dest/'result.json'))
 result=dict(status='PASS',identity=seal,groups=groups,source_sha256=sha(__file__),legacy_source_sha256=sha(prior.__file__),generated_sha256=sha(out/'registered62-run.py'),scope=__doc__,adaptations='Only obsolete59 identity and scope label replaced; original mutation/UndoRedo/clipboard/grammar/mode/preview/fragmentation/source/pixel/full16MiB typed-DMA assertions unchanged. 16-bank skips stored fold/far phase exactly as released;32-bank includes them.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REBASE_STRESS_PASS',out,flush=True);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',choices=('16','32','both'),default='both');p.add_argument('--rounds',type=int,default=96);p.add_argument('--seed',type=lambda n:int(n,0),default=0x53454f53);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/rebase-stress-adapter'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out.resolve(),a.fixture.resolve(),(16,32)if a.banks=='both'else(int(a.banks),),a.rounds,a.seed)
