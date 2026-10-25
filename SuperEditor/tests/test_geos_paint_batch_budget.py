"""Actual per-public-STEP preparation/leaf budget and yield proof."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,ctypes as C
import test_geos_paint_batch_candidate as batch
import test_geos_page_cost_profile as profile
import test_geos_identity_candidate as identity
import test_geos_semantic_editor as semantic
ROOT=batch.ROOT

def run(out):
 fixture=batch.install(out,batch.BASE,'candidate');labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',(out/'link/paint.lbl').read_text())}
 identity.semantic.geos.grid.editor_fixture.ROOT=identity.semantic.geos.grid.cpu_editor.ROOT=fixture
 names=json.loads((fixture/'freeze.json').read_text())['names'];identity.semantic.geos.grid.editor_fixture.NAMES=identity.semantic.geos.grid.cpu_editor.NAMES=names
 gate=out/'gate';gate.mkdir();dll=profile.runner(gate);f=identity.Fixture(gate,fixture,dll,True);records=[]
 try:
  data=semantic.FIXTURE;f.source(data);f.command(99);f.m.write(0xCF90,0);f.render();canonical=f.canonical();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);reu=f.reu();f.put('se_f_owner',4,1);f.m.load(0x8B40,bytes(192));f.m.write(0x9148,0)
  targets=[(0xA010,1,names.index('geosrow')+1),(0xA010,1,names.index('grid80')+1),(labels['se_gp_cache_read'],2,names.index('geospaint')+1)]
  op=0
  for step in range(1000):
   phase=f.m.read(0x8B43);dll.cp_begin(f.s['se_overlay_active'],len(targets),(C.c_uint16*3)(*[x[0]for x in targets]),(C.c_uint8*3)(*[x[1]for x in targets]),(C.c_uint8*3)(*[x[2]for x in targets]));f.audit_begin();r,n=f.invoke(op);dll.cp_end();f.dll.fr_end();assert not r.p&1,(step,r.a)
   counts=[]
   for i in range(3):m=(C.c_uint64*3)();dll.cp_metrics(i,m);counts.append(m[0])
   row,cell,read=counts
   assert row<=1 and cell<=8 and read<=8,(step,phase,counts)
   if row:assert phase in(7,16)and not cell and not read,(step,'R21 must have its own public STEP',phase,counts)
   assert f.reu()==reu and f.canonical()==canonical
   records.append(dict(step=step,phase_in=phase,phase_out=f.m.read(0x8B43),instructions=n,R21_calls=row,R16_calls=cell,cache_reads=read))
   if not r.a:break
   op=1
  else:raise AssertionError('batch painter did not converge')
  assert f.read(0x6000,8000)+f.read(0x4000,1000)==pixels
  result=dict(status='passed',steps=records,max_cache_reads=max(x['cache_reads']for x in records),max_R16=max(x['R16_calls']for x in records),R21_count=sum(x['R21_calls']for x in records),scope='Actual C21/source-generated mixed page; C22 publicSTEP full64KiB allowlist+16MiB readonly guards. EachR21 exclusivelyin a publicSTEP with no packetreads/nativecells; <=8 preparation/cell micro-ops betweenpublicguards. IRQqueuesinputonly; rootSTOPhandledbetweenpublicSTEPs.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='steps'},indent=2));return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-paint-batch-budget'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
