"""Read-only plan for a future physical comparison of copied RAM shadow bytes."""
import hashlib,json,re
from pathlib import Path

def plan(prg,labels,memory):
 if not memory['passed'] or memory['load']['shadow'] is None:raise ValueError('verified HD packaged memory contract required')
 shadow=memory['load']['shadow'];source=shadow['source'];run=shadow['run'];size=shadow['window_bytes'];offset=source-0x801+2
 symbols={n.lstrip('.'):int(a,16)for a,n in re.findall(r'^al ([0-9A-Fa-f]+) (\S+)',labels,re.M)}
 if prg[:2]!=b'\x01\x08'or len(prg)!=42497 or(source,run,size)!=(0xa000,0xf000,3584):raise ValueError('unexpected reviewed source/run/window contract')
 expected=prg[offset:offset+size]
 if len(expected)!=3584:raise ValueError('incomplete initialized source window')
 return {'schema_version':1,'kind':'dos64-copied-host-shadow-identity-plan','source_prg_sha256':hashlib.sha256(prg).hexdigest(),'capture_required_bytes':65536,'shadow':{'source_start':source,'capture_run_start':run,'bytes':size,'linked_bytes':shadow['linked_bytes'],'zero_tail_bytes':size-shadow['linked_bytes'],'expected_window_sha256':hashlib.sha256(expected).hexdigest(),'expected_bytes_source':'reviewed packaged PRG A000-ADFF; never compare reused live A000 cache bytes','loaded_guard_address':symbols['hdb_extension_ready'],'loaded_guard_required':0xa5,'normalizations':[],'excluded_vectors':{'start':0xfe00,'bytes':512}},'failure_retention_order':['Stop target and retain complete64KiB RAM before a recovery service changes code, state, guest frames or UCI buffers','Retain and independently verify authoritative REU350000-3501FF and handoff352000-3521FF; retain broader changed REU if needed','Retain owned remote HD image/readback and request/status/path identities without discarding uncertain-write authority','Only after those new-run artifacts are safe, restore and verify the complete original4MiB backup and prior machine/media configuration'],'limits':['This is a plan, not a physical execution or captured-identity claim','Existing ordinary resident checker needs an explicit source-to-run mapping for HDBIOS','Original4MiB backup restores user prior state but does not preserve newly uncertain HD data','No filesystem power-loss durability claim']}

def main():
 for name in ['dos64','dos64-tests']:
  p=Path('build')/name
  record=plan(p.with_suffix('.prg').read_bytes(),p.with_suffix('.labels').read_text(),json.loads(p.with_suffix('.memory.json').read_text()))
  (Path('build')/(name+'-hd-identity-plan.json')).write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
