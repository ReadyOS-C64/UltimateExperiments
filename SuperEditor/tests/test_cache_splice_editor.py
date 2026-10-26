"""Actual private C21/C20/C22 render after public edit + one-SPLICE rebase.

Only the independently assembled resident CMP operand and a byte-matched C21
profile are substituted. Source/edit/parser/REU proof, scheduler and raster are
actual code; semantic/layout outputs and page proofs are never host seeds.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,hashlib,ctypes as C,re
import test_cache_observer as ob
import test_cache_splice as sp
import test_plain_geos as plain
from supermark_model import blocks
import binascii
ROOT=ob.ROOT;BASE=ROOT/'build/cache-editor-product/20261026T051042908519Z/fixture'
F=0x8D00
DATA=ob.geos.native_text('Alpha ordinary text.\rMiddle ordinary line.\rOmega tail.\r')

def build(out,base):
 p=ROOT/'src/cache/splice-editor-probe/build.py';s=importlib.util.spec_from_file_location('editorbuild',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m.build(out,base)

def labels(p):return {n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}

def run(out,base,case='ordinary',smoke=False,caps=1):
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes());images,patch=build(out/'build',base);g=ob.Gate(out/'gate',base);f=g.f
 for n,v in images.items():f.assets[n]=v
 source=DATA
 if case=='mixed':source=ob.geos.native_text('# Heading\rAlpha ordinary text.\rMiddle ordinary line.\r- item\r:::basic\r10 PRINT "X"\r:::\r:::region Group\rOmega tail.\r:::end\r')
 if case=='inline':source=ob.geos.native_text('Alpha ordinary text.\rMiddle ordinary line.\rTail **bold** and *italic* @@code@@.\r')
 if case=='long-inline':source=ob.geos.native_text('Alpha ordinary text.\rMiddle ordinary line.\rTail **bold** '+('words '*700)+' @@code@@.\r')
 if case=='region':source=ob.geos.native_text(':::region Group\rAlpha ordinary text.\rMiddle ordinary line.\r:::end\rOmega tail.\r')
 fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)};frames=[];calls=[];faults=[];completed_hits=[]
 original_call=f.call
 def observed_call(name,a=0):
  before_id=f.m.read(0x9135);before_state=f.m.read(F+1)
  r=original_call(name,a)
  if name=='se_editor_service'and before_id==41 and before_state==6 and f.m.read(F+1)==0 and f.m.read(0x9135)==21 and f.m.read(0x9136)==1 and f.m.read(0x8B40+24)==0:
   assert not f.get('se_bc_flags',1)&32 and f.m.read(0x8B40+28)==0,'mapped result forged old page/CP proof'
   completed_hits.append(dict(query=int.from_bytes(f.read(0x8B40,3),'little'),kind=f.m.read(0x8B45),start=int.from_bytes(f.read(0x8B49,3),'little'),end=int.from_bytes(f.read(0x8B4C,3),'little'),page_proof=0,parser_CP=0,frame_ABI=f.m.read(F)))
  return r
 f.call=observed_call
 def call(ident,op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=ident,x=1);calls.append(dict(id=ident,op=op,a=r.a,carry=r.p&1,n=n,state=f.m.read(F+1)));return r
 def queue():return f.read(f.s['se_bc_arena'],13)+f.read(f.s['se_bc_head'],3)+f.read(f.s['se_bc_ring'],96)
 def arena():
  t=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+t[0]*16);bank=f.m.read(f.s['se_reu_map']+logical);return bank,g.reu()[bank*65536:(bank+1)*65536]
 def configure():
  names=list(f.assets);targets=[]
  spec=[('sema',34,out/'build/cache-labels/sema.lbl'),('inln',35,out/'build/cache-labels/inln.lbl'),('page',37,out/'build/cache-labels/page.lbl'),('line',39,out/'build/cache-labels/line.lbl'),('geossema',24,out/'build/geossema/image.lbl'),('geoslex',25,out/'build/geoslex/image.lbl'),('geosinln',26,out/'build/geosinln/image.lbl'),('splicequery',41,out/'build/splicequery/image.lbl')]
  for asset,ident,p in spec:
   syms=labels(p);idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==1)
   for fn in ('entry','se_sm_init','se_sm_feed','se_sm_finish','se_si_init','se_si_feed','se_sl_init','se_sl_feed'):
    if fn in syms:targets.append((asset+':'+fn,syms[fn],2,idx+1))
  g.dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*(x[1]for x in targets)),(C.c_uint8*len(targets))(*(x[2]for x in targets)),(C.c_uint8*len(targets))(*(x[3]for x in targets)),(C.c_uint8*(16*len(targets)))());return targets
 def full():
  f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);f.render()
 def check(tag,data):
  bits,attrs,rows=plain.expected(f,data,fonts,caps);actual=f.read(0x6000,8000);colors=f.read(0x4000,1000)
  (out/(tag+'-source.bin')).write_bytes(data);(out/(tag+'-actual.bin')).write_bytes(actual+colors);(out/(tag+'-expected.bin')).write_bytes(bits+attrs)
  assert actual==bits and colors==attrs,(tag,'independent pixels')
  # Compare every emitted canonical row and geometry to independent layout.
  raw,bank=f.raw_cache();assert raw[0]==1 and raw[1]==len(rows)
  for i,row in enumerate(rows):
   rec=raw[0x200+i*0x800:0x200+i*0x800+32];assert tuple(int.from_bytes(rec[o:o+3],'little')for o in(0,3,6))==(row.start,row.end,row.next),(tag,'canonical map',i,rec.hex(),row)
   assert (rec[14],rec[15])==(row.height,row.top)
  assert f.merged()==data and f.read(0xC600,1024)==f.shim and not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks'))
  ob.geos.png(actual,colors,out/(tag+'.png'));return bank
 def counted(tag,data,action,require_cached=False):
  stable=f.canonical();before=g.reu();q=queue();hit_start=len(completed_hits);targets=configure();g.dll.pb_begin();n=f.total_instructions
  try:action()
  finally:g.dll.pb_end()
  counts={x[0]:int(g.dll.pb_get(i))for i,x in enumerate(targets)};cost=f.total_instructions-n;bank=check(tag,data)
  assert f.canonical()==stable and queue()==q,(tag,'source/history/queue changed')
  after=g.reu();want=bytearray(before)
  spans=[(0,64),(0x600,0x680),(0xB200,0xD568),(0xE568,0xEA88),(0xFC00,0xFDA0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]
  # Real C24 (or authenticated baseline C35) may publish the existing
  # independent outgoing64 certificate at0700+0800*row. Validate each changed
  # certificate against the current key and canonical block oracle before
  # admitting only that exact64-byte span; never mask the slot spare wholesale.
  raw=after[bank*65536:(bank+1)*65536];oracle=blocks(data);rows=plain.expected(f,data,fonts,caps)[2]
  for i,row in enumerate(rows):
   lo=0x700+i*0x800;hi=lo+64;rec=raw[lo:hi]
   if rec==before[bank*65536+lo:bank*65536+hi]:continue
   assert rec[:4]==b'C\x02\x40\x01' and rec[7:35]==raw[4:32],(tag,'outgoing certificate type/key',i,rec.hex())
   assert binascii.crc_hqx(rec[:62],65535)==int.from_bytes(rec[62:64],'little')
   logical=next((e for e in oracle if e['start']==row.start),None)
   next_source=(logical['end']+int(logical['end']<len(data)and data[logical['end']]==13))if logical else len(data)
   assert int.from_bytes(rec[4:7],'little')==next_source and rec[41:44]==raw[32:35],(tag,'outgoing canonical anchor',i)
   spans.append((lo,hi))
  for lo,hi in spans:want[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
  if after!=want:
   changes=[]
   for physical in range(256):
    lo=physical*65536;old,new=bytes(want[lo:lo+65536]),after[lo:lo+65536];ix=[i for i,(a,b)in enumerate(zip(old,new))if a!=b]
    if ix:changes.append(dict(physical=physical,owner=f.m.read(f.s['se_reu_physical_owner']+physical),count=len(ix),first=ix[:40],last=ix[-20:]))
   (out/(tag+'-unexpected-REU.json')).write_text(json.dumps(changes,indent=2)+'\n')
  assert after==want,(tag,'whole16MiB outside exact FE allowed ranges')
  if require_cached:
   assert counts['splicequery:entry']>0 and len(completed_hits)>hit_start
   assert not any(v for k,v in counts.items()if k.startswith(('sema:','geossema:'))),(tag,'fell back to block parser',counts)
   assert counts['page:entry']==counts['line:entry']==0,(tag,'incompatible forward/INLINE proof consumed',counts)
  item=dict(tag=tag,instructions=cost,counts=counts,rows=len(plain.expected(f,data,fonts,caps)[2]),proof=f.get('se_bc_flags',1)&32);frames.append(item);print('RENDER PASS',tag,cost,{k:v for k,v in counts.items()if v},flush=True);return counts
 def seed():
  f.source(source);assert f.m.read(patch['address'])==patch['old'];f.m.write(patch['address'],patch['new']);f.typed(ob.geos.native_text('syntax full'if caps==3 else'syntax markdown'));f.command(99);f.render();check('initial-baseline',source);assert f.get('se_bc_count',1)==0 and f.get('se_bc_flags',1)&1
 def rebase():
  at=source.index(ob.geos.native_text('ordinary'),source.index(ob.geos.native_text('Middle')))+3;f.position(at);f.key(ob.Q);wanted=source[:at]+bytes([ob.Q])+source[at:];assert f.merged()==wanted and f.get('se_bc_count',1)==1
  bank,raw=arena();old=sp.roots(raw);before=g.reu();q=queue();stable=f.canonical();f.put('se_f_owner',4,1);r=call(40,0)
  for _ in range(200):
   assert not r.p&1,('rebase',r.a,calls[-10:])
   if r.a==0:break
   assert r.a==1 and queue()==q and f.canonical()==stable
   r=call(40,1)
  assert r.a==0 and f.get('se_bc_count',1)==0;after=g.reu();want=bytearray(before)
  for lo,hi in((old[1]^128,(old[1]^128)+128),(0x178,0x180),(0x900,0x920),(0xF000,0xF120)):want[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
  assert after==want and after[bank*65536+old[1]:bank*65536+old[1]+128]==old[2];feeds=int.from_bytes(f.read(F+58,3),'little');f.put('se_f_owner',0,1);return wanted,feeds
 try:
  seed();counted('baseline-selector-original-C35',source,full)
  wanted,feeds=rebase();counted('mapped-after-insert',wanted,full,True)
  if not smoke:
   def pending_query():
    f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
    r=f.call('se_editor_render');assert not r.p&1
    for _ in range(200):
     if f.m.read(0x9135)==41 and f.get('se_bc_flags',1)&8 and f.m.read(F+1)==6 and f.get('se_doc_read_locks',1):return
     assert f.get('se_e_job',1)==11 and not f.get('se_e_error',1)
     f.call('se_editor_service')
    raise AssertionError('actual held C41 query not reached')
   def stop():
    pending_query();before=g.reu();canonical=f.canonical();q=queue();tail=f.get('se_input_tail',1);f.queued(3);f.call('se_editor_service')
    assert f.get('se_input_tail',1)==tail and f.get('se_f_owner',1)==0 and not f.get('se_doc_read_locks',1)and g.reu()==before and f.canonical()==canonical and queue()==q
    f.tick();f.settle();f.render();faults.append('actual-queued-STOP-held-C41-and-repaint')
   counted('mapped-STOP-recovered',wanted,stop,True)
   for ident,slot in ((34,0),(41,1)):
    def missing():
     pending_query();before=g.reu();canonical=f.canonical();q=queue();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==slot)
     f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0);f.call('se_editor_service')
     assert f.get('se_e_error',1)==0x17 and not any(f.get(n,1)for n in ('se_e_job','se_f_owner','se_doc_read_locks'))
     assert g.reu()==before and queue()==q and f.canonical()==canonical and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels
     f.m.write(f.s['se_overlay_ids']+idx,ident);f.key(3);f.render();faults.append('missing-'+str(ident)+'-actual-root-cleanup-and-public-STOP-recovery')
    counted('mapped-missing-'+str(ident)+'-recovered',wanted,missing,True)
   for feature in (5,7):
    def unknown():
     semantic_bank,raw=arena();live=sp.roots(raw)
     def stash(payload):
      f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',live[1]);f.put('se_object_length',128,2);f.put('se_object_c64',0x8000,2);f.m.load(0x8000,payload);r=f.call('se_object_copy');assert not r.p&1;f.call('se_doc_invalidate')
     bad=bytearray(live[2]);bad[31]=feature;bad[119:121]=binascii.crc_hqx(bad[:5]+bad[6:119]+bad[121:],65535).to_bytes(2,'little');stash(bad)
     before=g.reu();canonical=f.canonical();q=queue();pixels=f.read(0x6000,8000)+f.read(0x4000,1000)
     f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
     r=f.call('se_editor_render')
     for _ in range(200):
      if f.get('se_e_error',1):break
      assert f.get('se_e_job',1)==11
      f.call('se_editor_service')
     assert f.get('se_e_error',1)==0xC2 and not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_job'))
     after=g.reu();_,fe=f.raw_cache();allowed=bytearray(before);allowed[fe*65536:fe*65536+64]=after[fe*65536:fe*65536+64]
     assert after==allowed and after[semantic_bank*65536:(semantic_bank+1)*65536]==before[semantic_bank*65536:(semantic_bank+1)*65536]and queue()==q and f.canonical()==canonical and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels
     stash(live[2]);f.key(3);f.render();faults.append('unknown-feature-'+str(feature)+'-actual-root-error-and-recovery')
    counted('unknown-'+str(feature)+'-recovered',wanted,unknown,True)
   # Representation-only flush is an actual queued REKEY. The feature3 map
   # cannot compose it; its unread record must force the real legacy path.
   g.flush();assert f.merged()==wanted and f.get('se_bc_count',1)>0
   c=counted('actual-flush-unread-REKEY-fallback',wanted,full)
   assert c['splicequery:entry']==0 and c['geossema:entry']>0
   faults.append('unread-REKEY-never-pretended-cached')

  def checked_action(action,tag):
   before=g.reu();g.dll.fr_begin(*[f.s[n]for n in ('se_reu_copy','se_reu_logical','se_reu_offset','se_reu_length','se_reu_map','se_reu_logical_owner','se_reu_physical_owner')])
   try:action()
   finally:g.dll.fr_end()
   assert g.dll.fr_bad()==0,(tag,'nonpermitted typed REU write')
   mask=C.create_string_buffer(len(before));g.dll.fr_mask(mask);allowed=mask.raw;after=g.reu();assert all(a==b or allowed[i]for i,(a,b)in enumerate(zip(before,after))),(tag,'whole16MiB outside exact actual checked typed DMA spans')
   return int(g.dll.fr_writes())
  if case=='long-inline':
   # Public BOTTOM leaves the cached viewport, flushing the pending letter via
   # the real history path. It must safely use legacy classification for the
   # now-unread REKEY; this is not feature3 navigation reuse.
   targets=configure();g.dll.pb_begin();n=f.total_instructions;dma=checked_action(lambda:(f.command(35),f.render()),'publicBOTTOM');g.dll.pb_end();c={x[0]:int(g.dll.pb_get(i))for i,x in enumerate(targets)}
   check('public-BOTTOM-after-mapping',wanted);assert f.get('se_hot_caret')==len(wanted)and not f.get('se_hot_pending',1)and f.document()==wanted and f.get('se_bc_count',1)>0 and c['splicequery:entry']==0 and c['geossema:entry']>0
   frames.append(dict(tag='public-BOTTOM-safe-unread-REKEY-fallback',instructions=f.total_instructions-n,counts=c,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),checked_DMA_writes=dma,whole16MiB_checked=True,note='actual flush + out-of-page reveal; not mapped navigation reuse'))
   checked_action(lambda:(f.command(16),f.render()),'publicUndo');check('public-Undo-after-BOTTOM',source);faults.append('public-BOTTOM-flush-reveal-and-Undo-exact-source')
  (out/'result.json').write_text(json.dumps(dict(status='PASS-private-mapped-render',fixture=g.identity,case=case,caps=caps,frames=frames,calls=calls,faults=faults,actual_dirty_parser_feeds=feeds,completed_mapped_hits_without_old_proof=completed_hits,integration=json.loads((out/'build/integration.json').read_text()),scope=__doc__),indent=2)+'\n');print('SPLICE EDITOR PASS',out,flush=True)
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=frames,calls=calls),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--case',choices=('ordinary','mixed','region','inline','long-inline'),default='ordinary');p.add_argument('--smoke',action='store_true');p.add_argument('--full',action='store_true');a=p.parse_args();out=ROOT/'build/cache-splice-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.case,a.smoke,3 if a.full else 1)
