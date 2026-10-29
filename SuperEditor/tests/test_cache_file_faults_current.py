"""Current54 native media/File regression with an actual pre-existing type53.

Existing file-fault scenarios and evaluators are reused unchanged. The NEW
setup first renders FBASE in GEOS through typed IRQ commands, authenticates
ARMED and a real type53 capability, and returns source40 before the original
clipboard/edit setup. Only private ports and dynamic catalog provenance differ.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,socket,inspect,hashlib,zipfile
import test_current_file_faults_vice as current
ROOT=current.ROOT
CASES=['missing-device','write-protected','disk-full','cancel-read','cancel-write','candidate-seq','promotion-ack-injected','missing-c12-open','missing-c12-save','missing-both-read','native-at16']

class Plan(current.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;return p
 def open(self,ident,name,*args,**kwargs):
  super().open(ident,name,*args,**kwargs)
  if ident=='baseline_open':
   # Public IRQ command input, not a seeded cache object/header/flag.
   self.send('cache_arm_geos',b'\x88'+current.prior.old.native_text('mode hires')+b'\r',owner=0)
   self.memory('cache_arm_mode3','se_mode',3)
   self.memory('cache_arm_flags','se_bc_flags',17)
   self.send('cache_return40',b'\x88'+current.prior.old.native_text('mode 40')+b'\r',owner=0)
   self.memory('cache_arm_mode0','se_mode',0)


def free_ports():
 for port in [8300,*range(8400,8440)]:
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as error:raise AssertionError(f'owned port {port} busy')from error


def execute(e,case):
 current.Plan=Plan;current.free_ports=free_ports
 # Original executable evaluator and media protocol are unchanged. Only its
 # explicit owned-port assertion is rebound to the newly assigned port.
 source=inspect.getsource(current.execute);assert source.count('==8500')==1
 source=source.replace('==8500','==8300')
 ns=dict(vars(current),Plan=Plan,free_ports=free_ports,__file__=__file__)
 exec(compile(source,str(e/'cache-execute.py'),'exec'),ns)
 (e/'cache-execute.py').write_text(source)
 result=ns['execute'](e,case);r=json.loads((e/'editor-report.json').read_text());s=r['symbols'];out=e/case
 records=[]
 for item in json.loads((out/'observations.json').read_text()):
  ram=(out/'captures'/(item['id']+'-ram.bin')).read_bytes();t=ram[s['se_bc_arena']:s['se_bc_arena']+5];owners=[i for i in range(8)if ram[s['object_owner']+i]==0x53]
  if t!=bytes(5):
   oid=t[0];assert oid<8 and owners==[oid]
   assert t[1:3]==bytes((ram[s['object_gen_lo']+oid],ram[s['object_gen_hi']+oid]))and t[3:5]==ram[s['se_object_epoch']:s['se_object_epoch']+2]
  else:assert not owners,(item['id'],'unbound type53 object')
  records.append(dict(id=item['id'],arena_token=t.hex(),type53_objects=owners,flags=ram[s['se_bc_flags']]))
 assert records[0]['id']=='before'and records[0]['type53_objects'],('no actual pre-existing cache',records)
 if case in ('native-at16','missing-c12-open'):
  assert all(not x['type53_objects']and x['arena_token']=='0000000000'for x in records[1:]),('Open did not retire checked optional cache',records)
 result.update(cache_preexists=True,cache_records=records,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),owned_ports=[8300,'8400..8439'],scope=__doc__)
 (out/'cache-result.json').write_text(json.dumps(result,indent=2)+'\n');print('CACHE_NATIVE_PASS',case,'actual53',records,flush=True);return result


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--case',choices=CASES,action='append');a=p.parse_args()
 assert a.run,'explicit --run required';free_ports();e=current.freeze(a.fixture.resolve());(e/'cache-wrapper.py').write_bytes(Path(__file__).read_bytes())
 with zipfile.ZipFile(e/'cache-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for f in sorted((ROOT/folder).glob('*.py')):z.write(f,f.relative_to(ROOT))
 print('CACHE_NATIVE_RUN',e,flush=True);results=[]
 for case in a.case or CASES:
  r=execute(e,case);results.append(dict(case=case,status=r['status'],screens=r['screens'],pixels=r['pixels'],cache=r['cache_records']))
 result=dict(status='passed',fixture=str(a.fixture.resolve()),catalog=len(json.loads((e/'freeze.json').read_text())['catalog']),cases=results,screens=sum(x['screens']for x in results),pixels=sum(x['pixels']for x in results),ports_released=True,scope=__doc__,visual_review='pending')
 (e/'cache-summary.json').write_text(json.dumps(result,indent=2)+'\n');print('CACHE_NATIVE_COMPLETE',e,flush=True)
if __name__=='__main__':main()
