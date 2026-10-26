"""Actual packaged automatic optional-cache retirement under File pressure.

Reuses the released current54 pressure setup and all public file/allocator
services. Adds an observation-only PC seam at the byte-authenticated C12 helper
entry/return: no register, memory, ownership or control-flow substitution.
KERNAL/DOS remain explicitly modeled; no native/OS/physical-key claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,textwrap
import test_lifecycle_cache_pressure_current as prior
ROOT=prior.ROOT;parent=prior.parent
BASE=ROOT/'build/cache-editor-product/20261026T035310363807Z/fixture'
OLD_SHA='9fff8a55aa8919dcdadfdc00916f51332a74a4ba96d064d1f4d5e5bbc113f988'
assert hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest()==OLD_SHA

class Fixture(parent.Fixture):
 def init_retire_trace(self):
  image=self.assets['fileio'];raw=image[36:];s=self.s
  prefix=bytes([0xad])+s['se_f_owner'].to_bytes(2,'little')+bytes([0xc9,1,0xd0])
  assert raw.count(prefix)==1,'exact helper entry prefix must be unique in sealed C12'
  self.retire_entry=0xb000+raw.index(prefix)
  jsr=bytes([0x20])+self.retire_entry.to_bytes(2,'little');assert raw.count(jsr)==1
  self.retire_return=0xb000+raw.index(jsr)+3
  # Active tags are one-based catalog slots, not the SEO public module ID.
  self.retire_id=prior.geos.grid.cpu_editor.NAMES.index('fileio')+1
  self.retire_witness=[];self.retire_saved=None
 def retirement_observe(self):
  pc=self.m.regs().pc
  if pc not in(self.retire_entry,self.retire_return):return
  if self.get('se_overlay_active',1+1)>>8 != self.retire_id:return
  if pc==self.retire_entry:
   assert self.get('se_f_owner',1)==1
   self.retire_saved=(self.canonical(),self.read(0x8d00,1152),self.read(self.s['se_bc_arena'],17),self.read(self.s['se_bc_ring'],96),self.reu())
  else:
   assert self.retire_saved is not None
   canonical,phase,state,ring,reu=self.retire_saved
   assert self.canonical()==canonical and self.read(0x8d00,1152)==phase
   assert self.read(self.s['se_bc_ring'],96)==ring
   after=self.read(self.s['se_bc_arena'],17)
   if any(state[:5]):
    assert not state[13]&12,'positive workload must not retire active/mutating arena'
    assert after[:5]==bytes(5) and after[5:13]==state[5:13] and after[14:]==state[14:]
    assert after[13]==((state[13]&~33)|2),'exact ARMED/PAGEPROOF revoke, LOST set'
   assert self.reu()==reu,'retirement itself wrote REU payload'
   self.retire_witness.append(dict(before=state.hex(),after=after.hex(),source_phase_ring_preserved=True,all_REU_bytes_preserved=True))
   self.retire_saved=None

# The original Python file-pump already steps every actual instruction through
# ca_step. This read-only probe executes immediately before those real steps.
call=parent._call.replace('self.dll.ca_step(m.handle)','self.retirement_observe();self.dll.ca_step(m.handle)')
ns=dict(parent._namespace);exec(compile(call,__file__+'::actual-file-pump-with-readonly-observation','exec'),ns);Fixture.call=ns['call']

replacement='''  f.fs[b'REOPEN']=data;f.start(operation='O');f.enter_name(b'REOPEN');before=stable();ram,reu=snap('open-before');owners=ram[f.s['se_reu_physical_owner']:f.s['se_reu_physical_owner']+banks]
  f.key(13);s=state('automatic-open-result');snap('automatic-open-result')
  assert f.retire_witness and any(bytes.fromhex(v['before'])[:5]!=bytes(5) for v in f.retire_witness),'actual retirement helper not witnessed'
  assert f.read(f.s['se_bc_arena'],5)==bytes(5)
  admitted=not f.get('se_f_owner',1)
  if banks==32:
   assert admitted and f.get('se_f_error',1)==0
   assert f.reu()[phys*65536:(phys+1)*65536]==fc_bytes
   assert f.read(f.s['se_clip_token'],5)==ram[f.s['se_clip_token']:f.s['se_clip_token']+5]
  else:
   assert not admitted and f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3 and f.get('se_f_error',1)==0x99 and not f.get('se_fd_confirm',1)
   unchanged(before);assert f.reu()[:banks*65536]==reu,'refusal changed actual1MiB REU'
   # Only optional cache extent ownership may disappear before rollback.
   after_owners=f.read(f.s['se_reu_physical_owner'],banks);removed=[b for b in range(banks)if owners[b]!=after_owners[b]]
   assert len(removed)==1 and owners[removed[0]]==0x53 and after_owners[removed[0]]==0
   f.key(3);quiet();unchanged(before);assert f.reu()[:banks*65536]==reu;state('automatic-refusal-cancelled')
   r,n=f.fast_call(f.s['se_reu_free'],x=fc);assert not r.p&1
   f.start(operation='O');f.enter_name(b'REOPEN');f.key(13)
   assert not f.get('se_f_owner',1) and f.get('se_f_error',1)==0
   state('retry-after-explicit-FC-release')
'''

def run(out,base,banks):
 source=textwrap.dedent(inspect.getsource(prior.run))
 source=source.replace("stages=[];catalog=None","stages=[];catalog=None")
 a=source.index("  f.fs[b'REOPEN']=data;");b=source.index("  assert f.merged()==data;quiet();state('open-complete')",a)
 source=source[:a]+replacement+source[b:]
 source=source.replace("  geos.grid.Fixture.source(f,data,banks=1,physical=banks);", "  f.init_retire_trace();geos.grid.Fixture.source(f,data,banks=1,physical=banks);")
 source=source.replace("  if admitted or banks==32:assert", "  if banks==32:assert")
 source=source.replace("  (out/'result.json').write_text", "  result['automatic_retirement']=True;result['helper_witnesses']=f.retire_witness;result['component_scope']=__doc__\n  (out/'result.json').write_text")
 namespace=dict(vars(prior));namespace.update(__doc__=__doc__,__file__=__file__)
 exec(compile(source,__file__+'::released-pressure-with-automatic-admission-assertions','exec'),namespace)
 old=parent.Fixture;parent.Fixture=Fixture
 try:
  result=namespace['run'](out,base,banks)
  (out/'executed-pressure.py').write_text(source);return result
 finally:parent.Fixture=old

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',type=int,choices=[16,32],required=True);a=p.parse_args()
 out=ROOT/'build/cache-pressure-eviction'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks)
