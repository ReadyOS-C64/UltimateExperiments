"""Checked C12 optional-cache retirement leaf on the actual frozen product.

Direct leaf entry isolates owner/capability/extent refusal before public pressure
OPEN tests. No replacement code, private allocator, source seed or native claim.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, shutil
import test_cache_observer as observer
ROOT=observer.ROOT

def run(out,base,stem):
 g=observer.Gate(out,base);f=g.f;cases=[]
 try:
  payload=f.assets['fileio'][36:]
  assert stem.with_suffix('.bin').read_bytes()==payload,'C12 labels do not match frozen payload'
  shutil.copy2(stem.with_suffix('.lbl'),out/'fileio.lbl')
  symbols={n:int(a,16)for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\w+)',(out/'fileio.lbl').read_text())}
  entry=symbols['f_cache_retire'];assert 0xb000<=entry<0xc000
  data=observer.geos.native_text('Ordinary retained source.\rSecond row.\r')
  f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render()
  assert f.get('se_bc_flags',1)&15==1
  # A real pending edit supplies an unread observation which retirement must
  # preserve. The public File caller flushes first; that path is tested apart.
  f.position(0);f.key(observer.Q);f.render();assert f.get('se_bc_count',1)>0
  token=f.read(f.s['se_bc_arena'],5);oid=token[0]
  logical=list(f.read(f.s['object_extents']+oid*16,f.m.read(f.s['object_banks']+oid)))
  physical=[f.m.read(f.s['se_reu_map']+b)for b in logical]
  oldflags=f.get('se_bc_flags',1);stable=g.stable();original=f.read(f.s['se_doc_original'],5)
  phase=bytes((i*29+7)&255 for i in range(1152));f.m.load(0x8d00,phase)
  def leaf(tag,expect=False):
   before=g.reu();authority=f.read(f.s['se_bc_arena'],17);ring=f.read(f.s['se_bc_ring'],96)
   objects=f.read(f.s['object_owner'],8);generation=f.read(f.s['object_gen_lo'],8)+f.read(f.s['object_gen_hi'],8)
   f.m.load(0xb000,payload);r,n=f.fast_call(entry)
   assert g.reu()==before,(tag,'whole16MiB changed')
   after=f.read(f.s['se_bc_arena'],17)
   assert after[5:13]+after[14:]==authority[5:13]+authority[14:] and f.read(f.s['se_bc_ring'],96)==ring,(tag,'observation lost')
   assert g.stable()==stable and f.read(0xc600,1024)==f.shim,(tag,'source/history/shim')
   assert f.read(0x8d00,1152)==phase,(tag,'File phase overwritten')
   if expect:
    assert after[:5]==bytes(5) and after[13]==(authority[13]&~33)|2
    assert f.m.read(f.s['object_owner']+oid)==0
    assert f.m.read(f.s['object_gen_lo']+oid)==(token[1]+1)&255
    assert all(f.m.read(f.s['se_reu_logical_owner']+b)==0 for b in logical)
    assert all(f.m.read(f.s['se_reu_physical_owner']+b)==0 for b in physical)
    assert all(f.m.read(f.s['object_owner']+i)==objects[i]for i in range(8)if i!=oid)
   else:
    assert after==authority and f.read(f.s['object_owner'],8)==objects
    assert f.read(f.s['object_gen_lo'],8)+f.read(f.s['object_gen_hi'],8)==generation
   item=dict(tag=tag,instructions=n,released=expect);cases.append(item);print('PASS',item,flush=True)
  for owner in(0,4):f.put('se_f_owner',owner,1);leaf('owner-'+str(owner))
  f.put('se_f_owner',1,1)
  for flag in(4,8,12):f.put('se_bc_flags',oldflags|flag,1);leaf('busy-'+str(flag))
  f.put('se_bc_flags',oldflags,1)
  for index in(1,3):
   bad=bytearray(token);bad[index]^=1;f.m.load(f.s['se_bc_arena'],bad);leaf('stale-token-'+str(index))
  f.m.load(f.s['se_bc_arena'],original);leaf('valid-source-object-not-cache')
  f.m.load(f.s['se_bc_arena'],token)
  p=f.s['se_reu_physical_owner']+physical[0];old=f.m.read(p);f.m.write(p,0x54);leaf('foreign-extent');f.m.write(p,old)
  leaf('release-valid-cache',True)
  result=dict(status='PASS',cases=cases,fixture=str(base),resident=g.identity['prg_sha256'],C12_sha256=hashlib.sha256(payload).hexdigest(),scope=__doc__)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--stem',type=Path,default=ROOT/'build/overlays/fileio');a=p.parse_args()
 out=ROOT/'build/cache-file-retire'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.stem)
