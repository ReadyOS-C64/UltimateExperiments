"""Current62 public styles/fallbacks + unchanged worker authority fault paths.

No production changes. The only initial CPU catalog substitution is the new
source-rebuilt C32/R30 pair, explicitly described by warm-shift/build.py.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_warm_input_profile as prof
import test_cache_observer as ob
from geos_packet import rows
DEFAULT=ROOT/'build/geos-warm-shift/public3/build-after/fixture'

def gate(out,base):
 old=ob.runner;ob.runner=prof.profile.build
 try:g=ob.Gate(out,base)
 finally:ob.runner=old
 g.dll.wp_extra(g.f.s['se_overlay_call'],g.f.s['se_overlay_frame'],g.f.s['se_gf_state']+21)
 g.dll.wp_config(g.f.s['se_overlay_active'],g.f.s['se_reu_copy'],g.f.s['se_reu_logical'],g.f.s['se_reu_length'],g.f.s['se_reu_logical_owner'],len(g.f.assets['type'][68:]),(C.c_uint8*16).from_buffer_copy(g.f.assets['type'][68:84]))
 return g

def run(out,base):
 out.mkdir(parents=True);g=gate(out/'public',base);f=g.f;(out/'reference').mkdir();ref=ob.geos.Fixture(out/'reference',g.frozen,g.dll,True);fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)};frames=[];faults=[]
 from test_cache_rebase_registered import metadata
 syms=dict((name,dict((n,a)for a,n in prof.syms(metadata(base,name).with_suffix('.lbl'))))for name in('gtype','type'))
 txn=65536+64*4096+(syms['type']['se_gst_transaction']-0x5000)
 def setup(text,word,delta=2):
  data=ob.geos.native_text(text);at=data.index(ob.geos.native_text(word))+delta
  for x in(f,ref):
   x.source(data,physical=256);x.typed(ob.geos.native_text('syntax full'));x.typed(ob.geos.native_text('mode hires'));x.typed(ob.geos.native_text('top'))
   for _ in range(at):x.key(0x1d)
   x.render()
  return data
 def check(tag,key,want=True):
  for x in(f,ref):x.key(key)
  old=g.audit_begin();g.dll.pb_arena_begin(True);canonical=f.canonical();before=f.read(0,65536);g.dll.wp_begin();f.render();ram_after=f.read(0,65536);g.dll.wp_end();g.audit_end(old,tag);g.dll.pb_arena_begin(False)
  buf=(C.c_uint64*prof.profile.N)();g.dll.wp_dump(0,buf);direct=bool(buf[txn]);assert direct==want,(tag,'actualC32transaction',direct,want)
  ref.m.write(0xcfe8,0);ref.m.write(0xcf90,0);ref.render();data=f.merged();assert data==ref.merged()and f.canonical()==canonical
  eb,ea,_=prof.plain.expected(f,data,fonts,3);assert f.read(0x6000,8000)==eb==ref.read(0x6000,8000)and f.read(0x4000,1000)==ea==ref.read(0x4000,1000),(tag,'independent/fullpixels')
  now=g.reu();_,bank=f.raw_cache();wanted=bytearray(old)
  for lo,hi in((0,64),(0x200,0xEA88)):wanted[bank*65536+lo:bank*65536+hi]=now[bank*65536+lo:bank*65536+hi]
  assert now==wanted,(tag,'precise16MiB')
  after=ram_after;wanted=bytearray(before)
  for lo,hi in((2,0x1c),(0x100,0x200),(0x4000,0x43e8),(0x5000,0x9180),(0xa000,0xc600),(0xca00,0xd000),(0xd000,0xe000),(f.s['se_doc_offset'],f.s['se_doc_c64']+2),(f.s['doc_cache_slot'],f.s['se_doc_read_done']+2),(f.s['se_object_id'],f.s['validate_type']+1)):wanted[lo:hi]=after[lo:hi]
  assert after==wanted,(tag,'whole64KiB',[(hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b][:8])
  assert f.read(0xc600,1024)==f.shim and not f.get('se_f_owner',1)and not f.get('se_doc_read_locks',1)
  if direct:
   a,_=f.raw_cache();b,_=ref.raw_cache();assert a[:64]==b[:64]
   for x,y in zip(rows(a),rows(b)):
    assert x['prefix'][:30]==y['prefix'][:30]
    for field in('chars','styles','roles','x'):assert x[field]==y[field],(tag,field)
  ob.geos.png(eb,ea,out/(tag+'.png'));frames.append(dict(tag=tag,direct=direct,instructions=int(g.dll.wp_count()),pixels_sha256=hashlib.sha256(eb+ea).hexdigest()));print('PUBLIC',frames[-1],flush=True)
 try:
  for style,marker in [('plain',''),('bold','**'),('italic','*'),('combined','***')]:
   setup('Alpha '+marker+'interiorwords'+marker+' omega.\rSecond source row.\rTail.','interiorwords')
   for name,key in [('Q',ob.Q),('BACK',0x14),('W',ob.geos.native_text('W')[0]),('M',ob.geos.native_text('M')[0]),('BACK-M',0x14),('BACK-W',0x14)]:check(style+'-'+name,key)
  setup('Alpha interiorwords omega.\rSecond source row.\rTail.','interiorwords')
  for x in(f,ref):x.command(68);x.key(0x1d);x.render()
  check('selection-replace',ob.Q,False)
  setup('Alpha interiorwords omega.\rSecond source row.\rTail.','interiorwords')
  for x in(f,ref):x.command(77);x.render()
  check('nowrap-refusal',ob.Q,False)
 finally:g.dll.wp_end();g.dll.pb_arena_begin(False);f.close();ref.close()
 # Fresh actual product import per fault prevents damaged handles from leaking
 # into another vector. Deliberate faults below are disclosed input seams.
 for kind in ['owner1','owner2','owner3','GEC0','GTC1','GTC-crc','font-glyph','font-width','stage-binding','stage-body','catalog-crc','catalog-size','catalog-owner','physical-owner','stale-epoch','missing-stage','missing-worker','source-token']:
  g=gate(out/('fault-'+kind),base);f=g.f
  try:
   data=ob.geos.native_text('Alpha **interiorwords** omega.\rSecond source row.\rTail.');at=data.index(ob.geos.native_text('interiorwords'))+3;f.source(data,physical=256);f.typed(ob.geos.native_text('mode hires'));f.typed(ob.geos.native_text('top'))
   for _ in range(at):f.key(0x1d)
   f.render();f.key(ob.Q);assert f.m.read(0x9149)==2
   index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==32 and(f.m.read(f.s['image_slot']+i)&1)==1);code=2;carry=False
   if kind.startswith('owner'):f.put('se_f_owner',int(kind[-1]),1)
   elif kind=='GEC0':f.m.write(0xcfe8,0)
   elif kind=='GTC1':f.m.write(0x9149,1)
   elif kind=='GTC-crc':f.m.write(0x9149+45,f.m.read(0x9149+45)^1)
   elif kind.startswith('font-'):p=0x8b4a if kind=='font-glyph'else 0x8b43;f.m.write(p,f.m.read(p)^1)
   elif kind.startswith('stage-'):
    h=f.m.read(f.s['se_overlay_asset']+(index>>4));p=f.m.read(f.s['se_reu_map']+h)*65536+(index&15)*4096+(0 if kind=='stage-binding'else 40);v=g.reu()[p];f.m.load(0x8080,bytes([v^1]));f.put('se_reu_logical',h,1);f.put('se_reu_offset',p&65535,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',1,2);assert not f.call('se_reu_copy',0).p&1;code=0x11 if kind=='stage-binding'else 0x94;carry=True
   elif kind=='catalog-crc':f.m.write(f.s['image_crc_lo']+index,f.m.read(f.s['image_crc_lo']+index)^1);code=0x94;carry=True
   elif kind=='catalog-size':f.m.write(f.s['image_size_lo']+index,f.m.read(f.s['image_size_lo']+index)^1);code=0x94;carry=True
   elif kind=='catalog-owner':h=f.m.read(f.s['se_overlay_asset']+(index>>4));f.m.write(f.s['se_reu_logical_owner']+h,99);code=0x18;carry=True
   elif kind=='physical-owner':h=f.m.read(f.s['se_overlay_asset']+(index>>4));p=f.m.read(f.s['se_reu_map']+h);f.m.write(f.s['se_reu_physical_owner']+p,99);code=4;carry=True
   elif kind=='stale-epoch':f.m.write(f.s['asset_epoch'],f.m.read(f.s['asset_epoch'])^1);code=0x18;carry=True
   elif kind=='missing-stage':f.m.write(f.s['se_overlay_ids']+index,0);code=0x17;carry=True
   elif kind=='missing-worker':i=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==30 and(f.m.read(f.s['image_slot']+i)&1)==0);f.m.write(f.s['se_overlay_ids']+i,0);code=0x17;carry=True
   elif kind=='source-token':f.m.write(f.s['se_doc_original']+1,f.m.read(f.s['se_doc_original']+1)^1);code=0x74;carry=True
   before=f.canonical();reu=g.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);owner=f.get('se_f_owner',1);phase=f.read(0x8d00,0x480);f.put('se_overlay_frame',3,1);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=0)
   assert (r.a,bool(r.p&1))==(code,carry),(kind,r.a,r.p,code,carry)
   assert f.canonical()==before and g.reu()==reu and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels and f.get('se_f_owner',1)==owner and f.read(0xc600,1024)==f.shim,(kind,'failure mutation')
   if owner:assert f.read(0x8d00,0x480)==phase,(kind,'foreignphase')
   faults.append(dict(kind=kind,A=r.a,carry=bool(r.p&1),instructions=n));print('FAULT',faults[-1],flush=True)
  finally:f.close()
 r=dict(status='PASS',fixture=str(base),frames=frames,faults=faults,scope='Actual public root and forced full reference + independent glyph oracle. Typed checked DMA/whole16MiB exact outside FE[0,64)+[0200,EA88), whole64KiB declared display/phase/derived writes. Negative explicit R30 entry seam proves untouched canonical/history/pixels/fullREU/shim, foreignphase opaque. No native/physical IRQ claim.')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--out',type=Path);a=p.parse_args();o=a.out or ROOT/'build/geos-warm-shift-guards'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',o,flush=True);run(o.resolve(),a.fixture.resolve())
