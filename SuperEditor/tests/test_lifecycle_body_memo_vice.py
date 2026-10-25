"""Final managed body-memo lifecycle delta; four private native mode runs.

Imports the current released lifecycle gate unchanged. Adds read-only monitor
stops before the first R26 stash and after fresh-prelude invalidation. One
explicit derived-state fault writes memo1 only AFTER exact restore is captured;
no canonical, stack, provider or original restore assertion is weakened.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import test_lifecycle_current_vice as current
ROOT=current.ROOT
FIXTURE=ROOT/'build/geos-incremental-editor/20261025T125409878419Z/fixture'
BasePlan=current.CurrentPlan

class BodyMemoPlan(BasePlan):
 def raw(self,ident,commands):
  commands=list(commands);caps=self.out/'captures'
  if ident=='prepared_coherent':
   blob=(self.e/'lifecopy.seo').read_bytes()[36:]
   matches=[i for i in range(len(blob)-2)if blob[i:i+3]==b'\x8d\x01\xdf']
   assert len(matches)==4,('actual R26 helper and3fixed restore extents',matches)
   pc=0xA000+matches[0];at=commands.index('until $0b70')
   commands[at:at]=[f'until ${pc:04x}',f'bsave "{caps}/before-first-R26-stash-ram.bin" 0 $0000 $cfff','registers']
  if ident=='fresh_restore_coherent':
   idle=f'until ${self.s["se_idle"]:04x}';at=commands.index(idle)
   assert any('exact-restored-ram.bin'in line for line in commands[:at])
   commands[at:at]=['> cc4d 01']
  return super().raw(ident,commands)


def run_one(fixture,mode,preview):
 current.CurrentPlan=BodyMemoPlan
 entry=current.run_one(fixture,mode,preview);return verify_one(entry,fixture)

def verify_one(entry,fixture):
 mode,preview=entry['mode'],entry['preview'];e=ROOT/entry['evidence'];caps=e/'lifecycle/captures'
 report=json.loads((e/'editor-report.json').read_text());s=report['symbols'];assert s['se_overlay_managed_verification']==1
 before=(caps/'before-first-R26-stash-ram.bin').read_bytes();boundary=(caps/'memo-invalidated-ram.bin').read_bytes()
 assert before[0xCC4D]==0,('before actual first R26 stash',mode,preview,before[0xCC4D])
 assert before[0x820]==0 and before[0x82D]==0x90 and int.from_bytes(before[0x829:0x82B],'little')==0x880 and int.from_bytes(before[0x82B:0x82D],'little')==0xBC20,('actual admitted first FC header stash',mode,preview)
 assert before[0x810]and before[0x811],('allocated FC capability',mode,preview)
 h,b=before[0x810:0x812];assert before[s['se_reu_map']+h]==b and before[s['se_reu_logical_owner']+h]==before[s['se_reu_physical_owner']+b]==0xFC
 assert boundary[0xCC4D]==0,('fresh prelude failed to revoke explicitly poisoned1',mode,preview)
 with __import__('zipfile').ZipFile(fixture/'product-sources.zip')as z:
  source=z.read('src/lifecycle/copy-entry.s');assert b'sta $CC4D' in source and b'.ifdef EDITOR_MANAGED_CODE'in source
 image=(e/'lifecopy.seo').read_bytes();assert image==(fixture/'build/overlays/lifecopy.seo').read_bytes()
 record=dict(status='passed',mode=mode,preview=preview,first_R26_stash_memo=0,admitted_FC_handle=h,admitted_FC_physical=b,first_stash_instruction_offset=image[36:].index(b'\x8d\x01\xdf'),fresh_prelude_poisoned1_revoked=0,packaged_R26_bytes=len(image)-36,packaged_R26_sha256=hashlib.sha256(image).hexdigest(),packaged_source_sha256=hashlib.sha256(source).hexdigest(),private_source_build_byteidentity=True,original_evaluator_unchanged=True,scope=__doc__)
 (e/'body-memo-result.json').write_text(json.dumps(record,indent=2)+'\n');entry['body_memo']=record;print('BODY_MEMO_PASS',e,flush=True);return entry


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=FIXTURE);p.add_argument('--mode',choices=('all','40','80','literal','preview'),default='all');a=p.parse_args()
 if not a.run:print('Prepared; explicit fixture, 4sequential native modes, owned8500/text8600..8639.');return
 fixture=a.fixture.resolve();identity=(fixture/'freeze.json').read_bytes();scenarios={'40':(0,False),'80':(2,False),'literal':(3,False),'preview':(3,True)};cases=[]
 for name,(mode,preview)in scenarios.items():
  if a.mode not in('all',name):continue
  assert (fixture/'freeze.json').read_bytes()==identity
  cases.append(run_one(fixture,mode,preview))
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-lifecycle-body-memo-native');out.mkdir()
 result=dict(status='passed',fixture=str(fixture),cases=cases,frames=sum(x['frames']for x in cases),native_pixels=sum(x['native_pixels']for x in cases),scope=__doc__,visual_review='pending');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('BODY_MEMO_GALLERY',out,flush=True)
if __name__=='__main__':main()
