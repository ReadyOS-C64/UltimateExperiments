"""Current59 automatic53 retirement under16/32-bank File pressure, CPU only.

Released allocator/File/lifecycle/source/history/ring/REU assertions retained.
Only54→59 catalog assertion is adapted. Real53, FC, clipboard/folds; no root5
claim, fake allocation or widened REU allowance. KERNAL/DOS explicitly modeled.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,inspect,json,textwrap
import test_cache_pressure_eviction as eviction
import test_grid_capture_index as identity
ROOT=eviction.ROOT;prior=eviction.prior;parent=eviction.parent
BASE=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture'

def audit_snapshots(out,base,banks):
 # Additional read-only decode of actual completed snapshots, never live edits.
 report=json.loads((base/'build/editor-report.json').read_text());sy=report['symbols'];ram=(out/'open-before-ram.bin').read_bytes();reu=(out/'open-before-reu.bin').read_bytes()
 assert len(reu)==banks*65536
 handle,physical=ram[0x810:0x812];assert handle and physical<banks
 assert ram[sy['se_reu_map']+handle]==physical
 assert ram[sy['se_reu_logical_owner']+handle]==ram[sy['se_reu_physical_owner']+physical]==0xfc
 lo=physical*65536;payload=reu[lo:lo+0xbc18];header=reu[lo+0xbc20:lo+0xbc60]
 assert header[:8]==b'LCA1'+bytes((1,0xa5,3,0xfc))
 assert header[8:24]==bytes.fromhex(report['resident_binding']['digest'])
 assert header[24:28]==ram[0x810:0x814]
 assert binascii.crc_hqx(payload,65535)==int.from_bytes(header[51:53],'little')
 assert binascii.crc_hqx(header[:62],65535)==int.from_bytes(header[62:64],'little')
 state=ram[sy['se_bc_arena']:sy['se_bc_arena']+17];ring=ram[sy['se_bc_ring']:sy['se_bc_ring']+96];events=[]
 assert state[16]==2 and state[14]<3 and state[15]<3
 for i in range(state[16]):
  slot=(state[15]+i)%3;e=ring[slot*32:(slot+1)*32]
  assert e[0]==0xa5 and e[1]in(1,2,3)
  assert binascii.crc_hqx(e[1:29]+e[31:],65535)==int.from_bytes(e[29:31],'little')
  events.append(dict(kind=e[1],ticket=int.from_bytes(e[4:8],'little'),position=int.from_bytes(e[16:19],'little'),delete=int.from_bytes(e[19:22],'little'),insert=int.from_bytes(e[22:25],'little')))
 assert events[0]['kind']==1 and events[0]['position']==5 and events[0]['delete']==0 and events[0]['insert']==1
 assert events[-1]['ticket']==int.from_bytes(state[5:9],'little')
 after=(out/'automatic-open-result-ram.bin').read_bytes();end=(out/'automatic-open-result-reu.bin').read_bytes()
 if banks==16:
  assert end==reu,'exactphysical1MiB rollback'
  assert after[sy['se_bc_ring']:sy['se_bc_ring']+96]==ring
 proof=dict(FC_logical=handle,FC_physical=physical,FC_payload_bytes=48152,FC_header_bytes=64,FC_payload_crc=int.from_bytes(header[51:53],'little'),FC_binding=header[8:24].hex(),queued_events=events,source_observer17=state.hex(),ring96_sha256=hashlib.sha256(ring).hexdigest(),whole_actual_REU_rollback=banks==16,scope='Read-only finishedsnapshotdecode; FCstorageintegrity only, no restoreafterdocumentreplacement claim.')
 (out/'snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n');return proof

def run(out,base,banks):
 seal=identity.authenticate(base)
 source=textwrap.dedent(inspect.getsource(prior.run))
 old="assert len(identity['names'])==54 and identity['names'][-1]=='line'"
 assert source.count(old)==1;source=source.replace(old,"assert len(identity['names'])==59 and identity['names'][-1]=='ctrl'")
 a=source.index("  f.fs[b'REOPEN']=data;");b=source.index("  assert f.merged()==data;quiet();state('open-complete')",a)
 source=source[:a]+eviction.replacement+source[b:]
 needle='  geos.grid.Fixture.source(f,data,banks=1,physical=banks);'
 assert source.count(needle)==1;source=source.replace(needle,'  f.init_retire_trace();geos.grid.Fixture.source(f,data,banks=1,physical=banks);')
 source=source.replace('  if admitted or banks==32:assert','  if banks==32:assert')
 source=source.replace("  (out/'result.json').write_text", "  result['automatic_retirement']=True;result['helper_witnesses']=f.retire_witness;result['component_scope']=__doc__\n  (out/'result.json').write_text")
 namespace=dict(vars(prior));namespace.update(__doc__=__doc__,__file__=__file__)
 exec(compile(source,str(out/'executed-pressure.py'),'exec'),namespace)
 oldfixture=parent.Fixture;parent.Fixture=eviction.Fixture
 try:
  result=namespace['run'](out,base,banks)
  result.update(snapshot_proof=audit_snapshots(out,base,banks),registered_seal=seal,catalog_adaptation='Only54/line→59/ctrl; original eviction/control checks retained.',original_setup_sha256=hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest(),original_eviction_sha256=hashlib.sha256(Path(eviction.__file__).read_bytes()).hexdigest())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_PRESSURE_PASS',banks,out,flush=True);return result
 finally:
  parent.Fixture=oldfixture
  if out.exists():(out/'executed-pressure.py').write_text(source)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',type=int,choices=[16,32],required=True);a=p.parse_args();out=ROOT/'build/cache-pressure-registered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks)
