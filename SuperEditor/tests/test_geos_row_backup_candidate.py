"""Private R28 write-only row-backup removal, exact production A/B and FE poison."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as body
D=ROOT/'src/render/geos/row-backup-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
OriginalFixture=body.Fixture
observations=[]

class PoisonMixin:
 def source(self,*args,**kwargs):
  self.backup_initialized=False
  return super().source(*args,**kwargs)
 def render(self,*args,**kwargs):
  check=getattr(self,'backup_initialized',False)
  if check:
   old=self.reu();handle=self.get('se_gc_handle',1);bank=self.m.read(self.s['se_reu_map']+handle);assert handle and bank
  r=super().render(*args,**kwargs)
  if not self.get('se_gc_handle',1):return r
  if check:
   new=self.reu();assert new[bank*65536+0xd568:bank*65536+0xe568]==old[bank*65536+0xd568:bank*65536+0xe568], 'Removed backup spans were written during real render/recovery'
   observations.append(dict(kind='unchanged4096',bank=bank))
  else:
   # Explicit derived scratch corruption through the real capability-checked
   # DMA service, after initial actual page publication and before any edit.
   canonical=self.canonical();handle=self.get('se_gc_handle',1);assert handle
   self.call('se_doc_invalidate')
   poison=bytes((i*37+0x63)&255 for i in range(128))
   self.m.load(0x8000,poison)
   for offset in range(0xd568,0xe568,128):
    for n,v,w in [('se_reu_logical',handle,1),('se_reu_offset',offset,2),('se_reu_length',128,2),('se_reu_c64',0x8000,2)]:self.put(n,v,w)
    assert not self.call('se_reu_copy',0).p&1
   assert self.canonical()==canonical
   self.backup_initialized=True;observations.append(dict(kind='checked_poison4096'))
  return r

class PoisonFixture(PoisonMixin,OriginalFixture):pass

def run(out,base,variant='candidate',smoke=False,packaged=False):
 body.D=D if variant=='candidate'else D/'control'
 body.Fixture=PoisonFixture if variant=='candidate'else OriginalFixture
 result=body.run(out,base,'candidate',smoke=smoke,packaged=packaged,diverse=True,append=True)
 result['variant']=variant
 result['backup_poison']=list(observations);result['scope']='Private full R28 baseline semantics unchanged except write-only 2x2048B backups removed; real C24/C20/C22 and independent/full renderer, tight4096B poisoned FE preservation within original16MiB guards.'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--smoke',action='store_true');p.add_argument('--packaged',action='store_true');a=p.parse_args();out=ROOT/'build/geos-row-backup'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 with zipfile.ZipFile(out/'verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for f in ['tests/test_geos_row_backup_candidate.py','tests/test_geos_heading_body_candidate.py','src/render/geos/row-backup-candidate/append-edit-cache.s','src/render/geos/row-backup-candidate/append-build.py']:z.write(ROOT/f,f)
 run(out,a.fixture.resolve(),a.variant,a.smoke,a.packaged)
