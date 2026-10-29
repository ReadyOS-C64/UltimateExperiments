"""Bounded CR transaction: prepublication refusals, history/far/bottom rows."""
from pathlib import Path
import argparse,binascii,hashlib,json
import test_grid_cr_suffix as public
ROOT=public.ROOT;observer=public.observer;profile=public.profile;wrapped=public.wrapped
def run(out,fixture):
 out.mkdir(parents=True);g=public.make_gate(out,fixture);f=g.f;cases=[];faults=[]
 def setup(width,data,at):
  f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f)
  if at>65535:f.position(len(data));profile.drain(f)
  f.position(at);profile.drain(f)
 def check(data,tag):
  assert f.merged()==data and f.read(0xc600,1024)==f.shim
  (bits,attrs),_,_,_=observer.geos.grid.expected(f,data);assert f.read(0x6000,8000)+f.read(0x4000,1000)==bits+attrs,(tag,'independent pixels')
  wrapped.packet_check(f,data,tag);assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_error'))
 def stash(data,offset,logical=None):
  f.m.load(0x9000,data);f.put('se_reu_logical',f.get('se_gc_handle',1)if logical is None else logical,1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x9000,2);f.put('se_reu_length',len(data),2);r=f.call('se_reu_copy',0);assert not r.p&1
 try:
  for width in(60,80):
   prefix=b'Prefix\r'*9400
   specs=[('empty',b'',0),('single-CR',b'\r',0),('full-body',b'A'*width+b'\rTail.\r',width),('near-full',b'A'*(width-1)+b'\rTail.\r',width-1),('far',prefix+b'Alpha words.\rTail.\r',len(prefix)+5),('row20',b'Prefix\r'*20+b'Alpha words.\rTail.\r',20*7+5),('row21-safe-fallback',b'Prefix\r'*21+b'Alpha words.\rTail.\r',21*7+5)]
   for tag,data,at in specs:
    setup(width,data,at);new=data[:at]+b'\r'+data[at:]
    for op,wanted,name in((None,new,'insert'),(16,data,'undo'),(17,new,'redo')):
     audit=g.audit_begin()
     if op is None:f.key(13)
     else:f.command(op)
     canonical=f.canonical();stable=g.stable();profile.drain(f);g.audit_end(audit,tag);assert f.canonical()==canonical and g.stable()==stable;check(wanted,(width,tag,name));cases.append(dict(width=width,tag=tag,operation=name,route=f.m.read(0x89ff)))
     print('PASS',width,tag,name,flush=True)
   for tag in('foreign-owner','source-lease','source-token','FE-epoch','FE-owner','missing-R29','missing-native','old-row-role','old-row-inverse','old-row-byte','font-window-corrupt'):
    data=b'Alpha words.\rBeta words.\rTail.\r';at=5;setup(width,data,at);f.key(13);wanted=data[:at]+b'\r'+data[at:];saved=[];knownbank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1))*65536
    def replace(address,value):saved.append((address,f.m.read(address)));f.m.write(address,value)
    if tag=='foreign-owner':replace(f.s['se_f_owner'],3)
    elif tag=='source-lease':replace(f.s['se_doc_read_locks'],1)
    elif tag=='source-token':replace(f.s['se_doc_original'],f.m.read(f.s['se_doc_original'])^1)
    elif tag=='FE-epoch':replace(f.s['se_gc_epoch'],f.m.read(f.s['se_gc_epoch'])^1)
    elif tag=='FE-owner':replace(f.s['se_reu_physical_owner']+f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1)),253)
    elif tag in('missing-R29','missing-native'):
     ident=29 if tag=='missing-R29'else 17 if width==60 else 16;i=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and not f.m.read(f.s['image_slot']+i)&1);replace(f.s['se_overlay_ids']+i,0)
    elif tag.startswith('old-row'):
     cache,_=f.raw_cache();row=10 if tag!='old-row-byte'else 0;p=bytearray(cache[row*240:(row+1)*240]);p[80 if tag.endswith('role')else 160 if tag.endswith('inverse')else 0]^=1;stash(p,row*240);h=bytearray(cache[0x1500:0x1600]);h[209+row*2:211+row*2]=binascii.crc_hqx(p,65535).to_bytes(2,'little');h[254:]=binascii.crc_hqx(h[:254],65535).to_bytes(2,'little');stash(h,0x1500)
    else:
     # A normal managed backing write revokes its verified memo. Admission
     # must decline, then repair only after the original sealed image returns.
     image=f.assets['grid60'if width==60 else'grid80'];ident=17 if width==60 else 16;i=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and not f.m.read(f.s['image_slot']+i)&1);logical=f.m.read(f.s['se_overlay_asset']+(i>>4));off=(i&15)*4096+0x800;byte=image[36+0x800];stash(bytes((byte^1,)),off,logical);saved.append(('font',logical,off,byte))
    before=g.audit_begin();bits=f.read(0x6000,8000)+f.read(0x4000,1000);phase=f.read(0x8d00,0x480);cache=before[knownbank:knownbank+65536];canonical=f.canonical();stable=g.stable();f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1);g.audit_end(before,tag);after=g.reu();newcache=after[knownbank:knownbank+65536]
    assert r.a==2 and not r.p&1,(width,tag,'MISS',r.a,r.p);assert bits==f.read(0x6000,8000)+f.read(0x4000,1000)and newcache[:0x1680]==cache[:0x1680],(width,tag,'no VIC/packet/header publication');assert canonical==f.canonical()and stable==g.stable()
    # Optional scratch staging only: authenticated FE4000..549F. No other
    # REU byte may change, including original packets/header and asset banks.
    h=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+h)*65536;assert before[:bank+0x4000]==after[:bank+0x4000]and before[bank+0x54a0:]==after[bank+0x54a0:]
    if tag=='foreign-owner':assert phase==f.read(0x8d00,0x480)and f.get('se_f_owner',1)==3
    for item in saved:
     if item[0]=='font':_,logical,off,byte=item;stash(bytes((byte,)),off,logical)
     else:f.m.write(*item)
    # Restore deliberately malformed derived packets through full render.
    f.put('se_f_owner',0,1);f.put('se_e_redraw',1,1);profile.drain(f);check(wanted,(width,tag,'repair'));faults.append(dict(width=width,tag=tag,instructions=n));print('REFUSE',width,tag,flush=True)
  result=dict(status='PASS',scope=__doc__,cases=cases,faults=faults);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out.resolve(),a.fixture.resolve())
