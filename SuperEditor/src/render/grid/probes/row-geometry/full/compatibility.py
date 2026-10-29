"""Actual mixed-generation/fallback/history proof; private coherent SEO seams."""
from pathlib import Path
import hashlib,json,shutil,sys
from importlib.util import spec_from_file_location,module_from_spec
D=Path(__file__).resolve().parent;ROOT=D.parents[5]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_boundary as boundary
import test_grid_raw_wrapped as wrapped
raw=wrapped.raw;profile=raw.caret.profile;observer=profile.observer

def module(name,path):
 s=spec_from_file_location(name,path);m=module_from_spec(s);s.loader.exec_module(m);return m

def mixed(out,base,candidate,name,asset):
 dst=out/name;shutil.copytree(candidate,dst);identity=json.loads((dst/'freeze.json').read_text())
 p=dst/'build/overlays'/(asset+'.seo');p.write_bytes((base/'build/overlays'/(asset+'.seo')).read_bytes());identity['assets'][asset]=hashlib.sha256(p.read_bytes()).hexdigest();identity['private_change']='Actual mixed-generation '+name
 (dst/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');return dst

def history(out,fixture):
 out.mkdir();g=observer.Gate(out,fixture);f=g.f;cases=[]
 def check(data,tag):
  assert f.merged()==data and f.read(0xc600,1024)==f.shim
  (bits,attrs),_,_,_=observer.geos.grid.expected(f,data)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'full raster')
  wrapped.packet_check(f,data,tag);assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_error'))
  cases.append(dict(tag=tag,pixels=hashlib.sha256(bits+attrs).hexdigest()))
 try:
  for width in(60,80):
   data=b'A'*(width-1)+b'\rUntouched tail.\r';f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(5);profile.drain(f)
   inserted=data[:5]+bytes([observer.Q])+data[5:]
   for command,wanted,tag in ((None,inserted,'insert'),(16,data,'undo'),(17,inserted,'redo')):
    audit=g.audit_begin()
    if command is None:f.key(observer.Q)
    else:f.command(command)
    profile.drain(f);g.audit_end(audit,tag);check(wanted,str(width)+'-'+tag)
   for key in(0x1d,0x9d):
    stable=g.stable();audit=g.audit_begin();f.key(key);profile.drain(f);g.audit_end(audit,'caret');assert g.stable()==stable;check(inserted,str(width)+'-caret-'+str(key))
  result=dict(status='PASS',cases=cases,scope='Actual public insert, Undo, Redo and caret; no seeded NC/packet authority.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

def missing(out,fixture):
 out.mkdir();g=observer.Gate(out,fixture);f=g.f;cases=[]
 try:
  for width in(60,80):
   data=b'A'*(width-1)+b'\rUntouched tail.\r';f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(5);profile.drain(f);f.key(observer.Q)
   s=f.s;idx=next(i for i in range(s['se_overlay_capacity'])if f.m.read(s['se_overlay_ids']+i)==24 and not f.m.read(s['image_slot']+i)&1)
   addr=s['se_overlay_ids']+idx;old=f.m.read(addr);f.m.write(addr,0)
   before=g.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);seq=f.get('se_e_draw_sequence',2);header=f.raw_cache()[0][0x1500:0x1600]
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(s['se_overlay_call'],a=33,x=1)
   assert r.a==2 and not r.p&1 and not f.get('se_f_owner',1)
   assert g.reu()==before and pixels==f.read(0x6000,8000)+f.read(0x4000,1000) and seq==f.get('se_e_draw_sequence',2) and header==f.raw_cache()[0][0x1500:0x1600],('missingR24 prewrite',width)
   f.m.write(addr,old);f.put('se_e_redraw',1,1);profile.drain(f);wanted=data[:5]+bytes([observer.Q])+data[5:];assert f.merged()==wanted
   (bits,attrs),_,_,_=observer.geos.grid.expected(f,wanted);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
   cases.append(dict(width=width,instructions=n,miss=2,prewrite=True,repaired=True))
  result=dict(status='PASS',cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

def opaque(out,fixture):
 out.mkdir();g=observer.Gate(out,fixture);f=g.f;cases=[]
 try:
  f.source(b'Plain\rTail.\r',physical=256)
  for owner in(0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);f.m.load(0x8d00,bytes([0xa7])*0x480);phase=f.read(0x8d00,0x480)
   for op in(3,4,5):
    before=g.reu();f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=0)
    assert r.p&1 and r.a==0xb2 and f.get('se_f_owner',1)==owner and f.read(0x8d00,0x480)==phase and g.reu()==before,(owner,op,'owner-first phase opacity')
    cases.append(dict(owner=owner,op=op))
  result=dict(status='PASS',cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

def run(out,base,candidate):
 out.mkdir(parents=True);pub=module('geometry_public',D/'public.py')
 a=mixed(out,base,candidate,'newC33-oldR24','geosfold');b=mixed(out,base,candidate,'oldC33-newR24','grid')
 result=dict(status='PASS',mixed_newC33=pub.run(out/'newC33-oldR24-proof',a,True,True),mixed_oldC33=pub.run(out/'oldC33-newR24-proof',b,True,True),history=history(out/'history',candidate),missing=missing(out/'missing',candidate),opaque=opaque(out/'opaque',candidate))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve())
