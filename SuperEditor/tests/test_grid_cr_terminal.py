"""Actual public terminal edit correctness, delete/UndoRedo and prewrite faults."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import test_grid_raw_wrapped as wrapped
ROOT=wrapped.ROOT;profile=wrapped.raw.caret.profile;observer=profile.observer
def run(out,fixture):
 out.mkdir(parents=True);g=observer.Gate(out,fixture);f=g.f;cases=[];faults=[]
 def check(data,tag,caps):
  assert f.merged()==data and f.read(0xc600,1024)==f.shim
  (bits,attrs),_,_,_=observer.geos.grid.expected(f,data);a=f.read(0x6000,8000);b=f.read(0x4000,1000)
  if a!=bits or b!=attrs:
   observer.geos.png(a,b,out/'actual-failure.png');observer.geos.png(bits,attrs,out/'expected-failure.png');raise AssertionError((tag,'full pixels',next((i,x,y)for i,(x,y)in enumerate(zip(a+b,bits+attrs))if x!=y)))
  if caps==0:wrapped.packet_check(f,data,tag)
  assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_error'))
  return hashlib.sha256(a+b).hexdigest()
 try:
  for width in(60,80):
   for caps in(0,3):
    for length in(0,12,width-2,width-1,width,width+5):
     data=b'A'*length+b'\rBeta words.\rTail.\r'
     for key in(13,observer.Q):
      f.source(data,physical=256);f.typed(observer.geos.native_text('syntax '+('plain'if caps==0 else'full')));f.command(97 if width==60 else 98);profile.drain(f);f.position(length);profile.drain(f);source=data;where=length
      for op in(key,20):
       audit=g.audit_begin();initial=f.total_instructions;f.key(op);profile.drain(f);used=f.total_instructions-initial;g.audit_end(audit,'terminal')
       source=source[:where]+bytes([op])+source[where:]if op!=20 else source[:where-1]+source[where:];where+=1 if op!=20 else -1
       tag=(width,caps,length,key,op);pixels=check(source,tag,caps);cases.append(dict(width=width,caps=caps,length=length,insert=key,key=op,route=f.m.read(0x89ff),instructions=used,pixels=pixels))
      assert source==data
   # Public history on both an actual CR and a glyph at the wrap boundary.
   for key in(13,observer.Q):
    data=b'A'*(width-1)+b'\rTail.\r';at=width-1;f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(at);profile.drain(f);new=data[:at]+bytes([key])+data[at:]
    for command,wanted,tag in((None,new,'insert'),(16,data,'undo'),(17,new,'redo')):
     audit=g.audit_begin()
     if command is None:f.key(key)
     else:f.command(command)
     profile.drain(f);g.audit_end(audit,tag);pixels=check(wanted,(width,key,tag),0);cases.append(dict(width=width,insert=key,history=tag,pixels=pixels))
  for width in(60,80):
   for fault in('foreign-owner','source-lease','source-token','FE-epoch','native-catalogue-missing'):
    data=b'Alpha words.\rBeta words.\r';at=data.index(b'\r');f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(at);profile.drain(f);f.key(13);wanted=data[:at]+b'\r'+data[at:]
    if fault=='foreign-owner':address=f.s['se_f_owner'];value=3
    elif fault=='source-lease':address=f.s['se_doc_read_locks'];value=1
    elif fault=='source-token':address=f.s['se_doc_original'];value=f.m.read(address)^1
    elif fault=='FE-epoch':address=f.s['se_gc_epoch'];value=f.m.read(address)^1
    else:
     ident=17 if width==60 else 16;idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and not f.m.read(f.s['image_slot']+i)&1);address=f.s['se_overlay_ids']+idx;value=0
    saved=f.m.read(address);f.m.write(address,value);reu=g.reu();bits=f.read(0x6000,8000)+f.read(0x4000,1000);phase=f.read(0x8d00,0x480);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
    assert r.a==2 and not r.p&1 and reu==g.reu()and bits==f.read(0x6000,8000)+f.read(0x4000,1000),(width,fault,'prewrite MISS')
    if fault=='foreign-owner':assert f.get('se_f_owner',1)==3 and f.read(0x8d00,0x480)==phase
    if fault=='source-lease':assert f.get('se_doc_read_locks',1)==1
    f.m.write(address,saved);f.put('se_e_redraw',1,1);profile.drain(f);check(wanted,(width,fault,'repair'),0);faults.append(dict(width=width,fault=fault,instructions=n,prewrite=True,repair=True))
  result=dict(status='PASS',cases=cases,faults=faults,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(cases),'public',len(faults),'faults',flush=True);return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out.resolve()if a.out else ROOT/'build/grid-cr-terminal'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())
