"""Resume registered stress with only the privately qualified C19 replacement.
Only the exact D81 seal changes; all source/pixel/history/typed-DMA assertions stay.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json
import test_stress_registered as stress
import test_retention_grammar as grammar
ROOT=grammar.ROOT

def run(out,fixture,banks=32,rounds=96):
 ident=json.loads((fixture/'freeze.json').read_text());baseline=json.loads((grammar.BASE/'freeze.json').read_text())
 assert ident['names']==baseline['names'] and ident['prg_sha256']==baseline['prg_sha256']
 assert {n for n in ident['assets']if ident['assets'][n]!=baseline['assets'][n]}=={'foldctl'}
 assert len((fixture/'build/overlays/foldctl.seo').read_bytes())-36==1555
 source=inspect.getsource(stress.run);old='446a5fa688886d7065b1da21491cf75c76f497bc111c37b83c3673c1a930171e';new=hashlib.sha256((fixture/'build/supereditor.d81').read_bytes()).hexdigest();assert source.count(old)==1
 # The legacy soak writes its complete result and returns None. Read that
 # result before adding registered metadata; do not rerun the finished proof.
 missing="result=ns['run'](out,base,rounds,seed);result['registered_seal']=seal;"
 fixed="ns['run'](out,base,rounds,seed);result=json.loads((out/'result.json').read_text());result['registered_seal']=seal;"
 assert source.count(missing)==1;source=source.replace(missing,fixed)
 ns=dict(vars(stress));exec(compile(source.replace(old,new),str(__file__)+'::only-private-disk-seal','exec'),ns)
 return ns['run'](out,fixture,banks,rounds)
def finalize(out):
 r=json.loads((out/'result.json').read_text());assert r['status']=='passed' and r['rounds']==96 and len(r['events'])==97 and len(r['pixel_checks'])==87
 assert r['checks'][-1]['tag']=='above64KiB-mode3'
 r['mutation_history_operations']=sum(3 for e in r['events']if e['delta'])+12
 r['qualification']='All actual workload checks finished before a decorator-only None-return metadata error; original result/log retained. This finalizer performs no emulator work.'
 r['allocation_scope']='Checkpoint highwater16 banks/6 objects. Raw STA monitor values40/8 include source-reset initialization and are NOT a physical32-bank live-allocation bound.'
 r['scope']='96 mixed public edit/UndoRedo groups plus32 repeated native keys and four above64KiB mode edits; 148 canonical/history checkpoints,87 independent fullpixels/attrs, real fragmentation and checked full16MiB typedDMA. CPU ROM/source/file seams; no native latency/physical claim.'
 (out/'result-final.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ['status','rounds','mutation_history_operations','checkpoint_max_allocated_banks','checkpoint_max_objects','qualification']},indent=2));return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--finalize',type=Path);p.add_argument('--banks',type=int,choices=[16,32],default=32);p.add_argument('--rounds',type=int,default=96);a=p.parse_args()
 if a.finalize:finalize(a.finalize)
 else:
  assert a.fixture;out=ROOT/'build/retention-grammar-stress'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture,a.banks,a.rounds)
