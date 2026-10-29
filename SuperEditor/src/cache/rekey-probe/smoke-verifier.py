"""Private one-kind REKEY durable bridge on real pending baseline and flush."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,hashlib,binascii,ctypes as C,re
import test_cache_observer as observer
import test_plain_geos as plain
ROOT=observer.ROOT;BASE=ROOT/'build/cache-editor-product/20261026T031201729970Z/fixture'
DATA=observer.geos.native_text('Body **bold** text.\rTail.')

def builder():
 p=ROOT/'src/cache/rekey-probe/build.py';spec=importlib.util.spec_from_file_location('rekey_build',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(out,base):
 budget=builder().build(out/'build',base);g=observer.Gate(out/'gate',base);f=g.f;f.assets['rekey']=(out/'build/rekey.seo').read_bytes();steps=[]
 def invoke(op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=38,x=1);steps.append(dict(op=op,instructions=n,a=r.a,carry=r.p&1,phase=f.m.read(0x8D01),count=f.get('se_bc_count',1)));return r
 def unread():
  raw=f.read(f.s['se_bc_arena'],17);return raw[:13]+raw[14:],f.read(f.s['se_bc_ring'],96)
 def arena():
  token=f.read(f.s['se_bc_arena'],5);oid=token[0];logical=f.m.read(f.s['object_extents']+oid*16);bank=f.m.read(f.s['se_reu_map']+logical);return token,bank,g.reu()[bank*65536:(bank+1)*65536]
 def roots(raw):
  valid=[]
  for off in (0,128):
   h=raw[off:off+128]
   if h[:4]==b'BCA1'and h[5]==1 and binascii.crc_hqx(h[:5]+h[6:119]+h[121:],0xFFFF)==int.from_bytes(h[119:121],'little'):valid.append((int.from_bytes(h[18:22],'little'),off,h))
  assert valid;return sorted(valid)
 try:
  f.source(DATA);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render();f.position(5);f.key(observer.Q);wanted=DATA[:5]+bytes([observer.Q])+DATA[5:];assert f.merged()==wanted and f.get('se_hot_pending',1)and f.get('se_bc_count',1)==1
  # Explicit actual internal C7 baseline admission: source/cache results are not
  # seeded. These invalidations are the caller's documented phase-claim seam.
  for name in ('se_i_ready','se_i_count','se_n_cache_count'):f.put(name,0,1)
  f.put('se_f_owner',4,1);f.put('se_overlay_frame',9,1);r,n=f.fast_call(f.s['se_overlay_call'],a=7,x=1);assert not r.p&1 and r.a==1 and f.read(0x9135,2)==bytes((34,0));f.put('se_e_job',11,1);f.settle();f.render()
  assert f.merged()==wanted and f.get('se_hot_pending',1)and f.get('se_bc_count',1)==0 and f.get('se_bc_flags',1)&15==1
  token,bank,beforeflush=arena();oldroot=roots(beforeflush)[-1];assert oldroot[2][62]==1 #rootSOURCE32+pending30
  ticket=f.get('se_bc_ticket',4);generation=f.get('se_doc_generation',2);revision=f.get('se_r_revision',4);g.flush();assert f.merged()==wanted and f.document()==wanted and not f.get('se_hot_pending',1)
  assert f.get('se_bc_count',1)==1 and f.get('se_bc_ticket',4)==ticket and f.get('se_r_revision',4)==revision
  tail=f.get('se_bc_tail',1);event=f.read(f.s['se_bc_ring']+tail*32,32);assert event[1]==2 and event[4:8]==ticket.to_bytes(4,'little')
  stable=g.stable();before=g.reu();queue=unread();f.put('se_f_owner',4,1)
  r=invoke(0)
  while not r.p&1 and r.a==1 and len(steps)<50:
   assert unread()==queue and g.stable()==stable
   r=invoke(1)
  if r.p&1 or r.a!=0:
   (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure.json').write_text(json.dumps(steps,indent=2));raise AssertionError(('bridge',r.a,r.p,steps))
  assert f.get('se_bc_count',1)==0 and f.get('se_bc_ticket',4)==ticket and not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8
  _,samebank,afterbank=arena();(out/'before-arena.bin').write_bytes(before[bank*65536:(bank+1)*65536]);(out/'after-arena.bin').write_bytes(afterbank);(out/'bridge-ram.bin').write_bytes(f.read(0,65536));(out/'steps.json').write_text(json.dumps(steps,indent=2));print('ROOTS',[(x[0],x[1],x[2][30])for x in roots(afterbank)],'old',oldroot[0],oldroot[1],flush=True);assert samebank==bank;newroot=roots(afterbank)[-1];assert newroot[0]==oldroot[0]+1 and newroot[1]==oldroot[1]^128
  assert afterbank[oldroot[1]:oldroot[1]+128]==oldroot[2]and afterbank[0x900:0x920]==event
  assert newroot[2][22:30]==oldroot[2][22:30]and newroot[2][30]==1 and newroot[2][91:119]==oldroot[2][91:119]
  assert newroot[2][32:91]==f.read(0x8DAD+27,59)
  after=g.reu();want=bytearray(before)
  for lo,hi in [(newroot[1],newroot[1]+128),(0x900,0x920)]:want[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
  assert after==want and g.stable()==stable and f.read(0xC600,1024)==f.shim
  f.put('se_f_owner',0,1);fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
  # Genuine postbridge renderer/classifier, without changing any CR tickets.
  targets=[('C24',0xB010,'geossema'),('C34',0xB010,'sema'),('C35',0xB010,'inln'),('C37',0xB010,'page')]
  g.dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*(x[1]for x in targets)),(C.c_uint8*len(targets))(*([2]*len(targets))),(C.c_uint8*len(targets))(*(g.identity['names'].index(x[2])+1 for x in targets)),(C.c_uint8*(16*len(targets)))());g.dll.pb_begin()
  f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_l_valid',0,1);f.put('se_r_valid',0,1);f.put('se_l_need_wrap',1,1);start=f.total_instructions;f.render();cost=f.total_instructions-start;g.dll.pb_end();counts={x[0]:int(g.dll.pb_get(i))for i,x in enumerate(targets)};assert counts['C24']==counts['C34']==0 and counts['C35']>0
  bits,attrs,_=plain.expected(f,wanted,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.merged()==wanted;observer.geos.png(bits,attrs,out/'post-rekey.png')
  d=dict(status='PASS',budget=budget,source_bytes=len(wanted),ticket=ticket,generation_before=generation,generation_after=f.get('se_doc_generation',2),revision=revision,event_hex=event.hex(),steps=steps,postbridge_render_instructions=cost,postbridge_counters=counts,root_before_offset=oldroot[1],root_after_offset=newroot[1],scope='Actual pendingtyping→explicit realC7/C34 fullbaseline→realC6/R2 flushREKEY→private checkedC38. Source/history/shim/whole16MiB confined alternate128Broot+32Bjournal duringbridge; no CR rewrite or reticket. Private internal admission/owner/dispatch seams explicit; no native/mainintegration claim.');(out/'result.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2),flush=True)
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/cache-rekey'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
