"""Actual59 CFG extension: two byte-checked finite local dispatches, no opacity."""
from pathlib import Path
import argparse,hashlib,importlib.util,inspect,json,sys,textwrap
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
p=Path(__file__).with_name('staged-stack.py');spec=importlib.util.spec_from_file_location('registered59staged',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);m.ROOT=ROOT

def run(out,base,project):
 out.mkdir(parents=True);proof={}
 for tag,slot,id_,targets in [('tail',0,36,['opened','verified','header_read','bca_bad','record_read']),('ctrl',1,49,['opened','verified','header_read','find','record_read','record_write','seal_header','page_valid','directory','directory_valid','new_verified','root_write','root_valid'])]:
  image=(base/f'build/overlays/{tag}.seo').read_bytes();assert image[5:7]==bytes((slot,id_))
  raw=image[36:];assert raw==(project/f'build/lexical/{tag}.bin').read_bytes()
  labels={a[2].lstrip('.'):int(a[1],16)for s in(project/f'build/lexical/{tag}.lbl').read_text().splitlines()if len(a:=s.split())==3 and a[0]=='al'}
  origin=0xb000 if slot else 0xa000;at=labels['step'];table=labels['step_table'];bad=labels['bca_bad'];word=lambda v:v.to_bytes(2,'little')
  expected=bytes.fromhex('ad008d38e901c9')+bytes((len(targets),))+bytes.fromhex('90034c')+word(bad)+bytes.fromhex('0aaabd')+word(table)+bytes.fromhex('8d108dbd')+word(table+1)+bytes.fromhex('8d118d6c108d')
  assert raw[at-origin:table-origin]==expected,(tag,'guarded indexed jump bytes')
  addresses=tuple(labels[n]for n in targets);assert raw[table-origin:table-origin+2*len(targets)]==b''.join(map(word,addresses))
  assert all(origin+16<=a<origin+len(raw)for a in addresses)
  m.LEX_TABLES[('C:'if slot else'R:')+tag]=addresses
  proof[tag]=dict(state=0x8d00,pointer=0x8d10,guard_start=at,guard_bytes=expected.hex(),targets=dict(zip(targets,addresses)),sealed_sha256=hashlib.sha256(image).hexdigest())
 # Expand only explicitly enumerated, authenticated local vectors. Every target
 # is traversed with identical stack/flags; all other unknown indirects reject.
 old=m.original.Analysis.analyze;src=textwrap.dedent(inspect.getsource(old));needle="target=self.vectors[target]\n    enqueue((target,st,flags),state);continue"
 replacement="targets=self.vectors[target]\n     if isinstance(targets,tuple):\n      for destination in targets:enqueue((destination,st,flags),state)\n      continue\n     target=targets\n    enqueue((target,st,flags),state);continue"
 assert src.count(needle)==1
 ns=dict(m.original.__dict__);exec(compile(src.replace(needle,replacement),str(Path(__file__))+':finite-vector','exec'),ns);m.original.Analysis.analyze=ns['analyze']
 (out/'finite-dispatch-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 m.original.calibration();result=m.run(out,base,m.original.ROM,None)
 result['lexical_finite_dispatch']=proof;result['scope59']='All actual59assets traversed; finite local state tables are conservatively expanded without opaque edges. No matching native idle witness for this private resident; relative bound only.'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print('RUN',a.out,flush=True);run(a.out.resolve(),a.fixture.resolve(),a.project.resolve())
