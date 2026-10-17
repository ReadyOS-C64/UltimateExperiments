from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-consumer');assert not Path(sys.pycache_prefix).exists()
import json,hashlib,shutil,traceback,re
import run_debug as R
V=R.V;L=R.L;FH=R.FH
# Guest BIOS XT words explicitly carry both scan and ASCII; this fixes only
# the host mapper's missing quotation mark, no native keyboard/UI change.
original_key=V.key
extra_keys={'"':0x2822,'=':0x0d3d,'_':0x0c5f}
V.key=lambda ch:extra_keys[ch] if ch in extra_keys else original_key(ch)
assert V.key('"')==0x2822 and V.key('F')==original_key('F')
all_commands=['CLS\r','TYPE C:\\DEBUG.DON\r',*[('FIND "IP='+ip+'" C:\\DEBUG.LOG\r')for ip in ['0103','0104','0107']],'C:\\V1TRAP.COM\rECHO V1_FRESH_RUN_OK\r']
preflight={ch:hex(V.key(ch))for ch in sorted(set(''.join(all_commands)))}
assert preflight['"']=='0x2822'and preflight['=']=='0xd3d'and preflight['_']=='0xc5f'
(P/'KEYBOARD_PREFLIGHT.json').write_text(json.dumps({'every_typed_character_preflighted':preflight,'no_VM_created':True},indent=2)+'\n')
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def compact(s):return ''.join(s.split())
def main():
 D=P/'execution';D.mkdir();paths=[p for p in P.rglob('*')if p.is_file()and not p.is_relative_to(D)and'__pycache__'not in p.parts and p.name not in ['RUN.stdout','RUN.stderr']];records={str(p):V.ident(p)for p in paths};records[str(Path(sys.executable).resolve())]=V.ident(Path(sys.executable).resolve());save(D/'INPUTS_BEFORE.json',records)
 for i,(p,w)in enumerate(sorted(records.items())):q=D/'copies'/('%05d'%i);q.parent.mkdir(exist_ok=True);shutil.copyfile(p,q);assert V.ident(q)==w
 hd=(P/'media/C-closed-debug.IMG').read_bytes();volume=V.DISK.Volume(hd[8192:]);log=volume.payloads['DEBUG.LOG'].decode('ascii');expected={ip:next(line for line in log.splitlines()if 'IP='+ip in line)for ip in ['0103','0104','0107']}
 result={'passed':False,'scope':'fresh40 only, reusable immutable native-closed DEBUG producer C, no producer replay','physical':False,'borrowed_source_built_model_unchanged':V.ident(P/'start/journal-peddle.dylib'),'XT_quote_word':'2822','read_predicate':'exact full persisted IP register line after FIND output header, excludes command echo'};f=n=None;primary=None
 try:
  d=D/'fresh40';d.mkdir();f=R.Fixture(hd,40,'published40');n=V.launch(f,d)
  def clear(tag):
   n.type('CLS\r','clear-'+tag);n.wait('cleared-'+tag,lambda s:s['prompt']and all(not line.strip()or line.strip()=='C>'for line in s['text'].splitlines()))
  clear('marker');n.type('TYPE C:\\DEBUG.DON\r','fresh-marker');n.wait('fresh-marker-read',lambda s:s['prompt']and any(line.strip()=='V1_DEBUG_COMPLETE'for line in s['text'].splitlines()))
  for ip,line in expected.items():
   clear(ip);n.type('FIND "IP='+ip+'" C:\\DEBUG.LOG\r','fresh-log-'+ip)
   def shown(s):
    return s['prompt']and'----------'in s['text']and compact(line)in compact(s['text'].rsplit('----------',1)[-1])
   n.wait('fresh-exact-log-line-'+ip,shown)
  clear('COM');n.type('C:\\V1TRAP.COM\rECHO V1_FRESH_RUN_OK\r','fresh-COM')
  n.wait('fresh-COM-returned',lambda s:s['prompt']and any(line.strip()=='V1_FRESH_RUN_OK'for line in s['text'].splitlines())and'Bad command'not in s['text'])
  after=FH.finish(n,d);assert after==hd and f.file(V.PATHS[0])==f.a and f.file(V.PATHS[1])==f.b;(D/'C-after-fresh-Finish.IMG').write_bytes(after);save(D/'FULL_FAT.json',V.DISK.inspect(after,(128,2,16)));result.update(passed=True,fresh40_guest=n.guest(),fresh40_wire=n.wire_summary(False),full_C_byteexact=True,all_original_A_B_byteexact=True,full_C_sha256=V.sha(after),expected_register_lines=expected)
 except BaseException as ex:
  primary=ex;result['error']=repr(ex);result['traceback']=traceback.format_exc()
  if n is not None:
   try:save(D/'FAILURE_OBSERVATIONS.json',n.observations);(D/'failure-RAM.bin').write_bytes(n.ram());(D/'C-failure-not-knownclosed.IMG').write_bytes(f.file(V.PATHS[2]))
   except BaseException as other:result['diagnostic_error']=repr(other)
  raise
 finally:
  actions=[]
  if f is not None:actions.append(f.close)
  actions +=[lambda:V.verify(records),lambda:save(D/'INPUTS_AFTER.json',records)]
  for action in actions:
   try:action()
   except BaseException as ex:
    result.setdefault('secondary_errors',[]).append(repr(ex))
    if primary is None:primary=ex
  result['native_cycles_including_observer_not_perf']=V.TOTAL_NATIVE_CYCLES
  save(D/'RESULT.json',result)
  if primary is not None and sys.exc_info()[0]is None:raise primary
if __name__=='__main__':main()
