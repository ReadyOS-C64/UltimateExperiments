"""Private current59 flags5 materialization after an actual ordinary insertion.

No semantic/query/role/proof seeds and no reader changes. Explicit component
caller claims owner4 and invalidates derived indexes, as normal root admission
must do; the real public render then uses unchanged production readers.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,importlib.util,json,re
import test_cache_observer as ob
import test_cache_splice as sp
import test_plain_geos as plain
from supermark_model import blocks
ROOT=ob.ROOT;F=0x8d00
BASE=ROOT/'build/lexical-batch-current/20261026T194420618867Z/fixture'


def labels(path):return{n:int(a,16)for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\w+)',path.read_text())}


def run(out,base,length=8000,with_faults=False,mixed=False):
 p=ROOT/'src/cache/edit-rebase-current-probe/build.py';s=importlib.util.spec_from_file_location('current_edit_rebase',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 images=m.build(out/'leaf',base);g=ob.Gate(out/'gate',base);f=g.f;f.assets.update(images)
 source=ob.geos.native_text(('Intro **bold** and @@code@@.\r'if mixed else'Intro\r')+':::basic\r10 PRINT "Hi":REM '+'x'*length+'\r:::\rMiddle ordinary line.\rTail.')
 at=source.index(ob.geos.native_text('ordinary'))+3;wanted=source[:at]+bytes([ob.Q])+source[at:]
 fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)}
 records=[];calls=[]
 # Explicit CPU loans for the component plus existing checked loader/reader APIs.
 # All executable/resident/font/screen bytes, GSEM inputs and parent control are
 # outside these spans; canonical state inside the scratch segments is guarded
 # independently. This is not an allowlist inferred from observed writes.
 ram_spans=[(2,26),(0x100,0x200),(0x5000,0x6000),(0x8000,0x8800),(0x8880,0x8b40),(0x8d00,0x8f40),(0x9a00,0x9de5),(0x9e00,0x9fc6),(0xa000,0xc000),(0xc000,0xc600),(0xca00,0xcb80),(0xcbd5,0xcbd6),(0xdf00,0xdf0c)]
 def arena():
  t=f.read(f.s['se_bc_arena'],5);h=f.m.read(f.s['object_extents']+t[0]*16);bank=f.m.read(f.s['se_reu_map']+h);return bank,g.reu()[bank*65536:(bank+1)*65536]
 def invoke(op):
  f.put('se_overlay_frame',op,1);ram_before=f.read(0,65536);provider_before=f.read(f.s['object_owner'],184)+f.read(f.s['se_reu_map'],772)+f.read(f.s['se_reu_banks'],2);r,n=f.fast_call(f.s['se_overlay_call'],a=40,x=1);f.total_instructions+=n
  assert provider_before==f.read(f.s['object_owner'],184)+f.read(f.s['se_reu_map'],772)+f.read(f.s['se_reu_banks'],2),'component changed object descriptors/provider maps'
  ram_after=f.read(0,65536);ram_allowed=bytearray(ram_before)
  for lo,hi in ram_spans:ram_allowed[lo:hi]=ram_after[lo:hi]
  assert ram_after==ram_allowed,('component undeclared64KiBRAM writes',[hex(i)for i,(a,b)in enumerate(zip(ram_before,ram_after))if a!=b and not any(lo<=i<hi for lo,hi in ram_spans)][:32])
  row=dict(op=op,a=r.a,carry=r.p&1,instructions=n,state=f.m.read(F+1),phase=f.m.read(F+94));calls.append(row);return r
 def force():
  f.put('se_gc_width',0,1);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
  f.m.write(0xcf90,0);f.m.write(0xcfe8,0)
 def targets():
  spec=[('rebase',40,out/'leaf/rebase/image.lbl'),('geossema',24,out/'leaf/geossema/image.lbl'),('geoslex',25,out/'leaf/geoslex/image.lbl')]
  for name,id_ in(('sema',34),('inln',35),('page',37),('line',39)):
   raw=base/'build/cache-editor'/(name+'.bin');assert raw.read_bytes()==(base/'build/overlays'/(name+'.seo')).read_bytes()[36:]
   spec.append((name,id_,base/'build/cache-editor'/(name+'.lbl')))
  spec.append(('edit',45,base/'build/lexical/edit.lbl'))
  rows=[]
  for name,id_,path in spec:
   syms=labels(path);index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)&1==1)
   for fn in('entry','se_sm_init','se_sm_feed','se_sm_finish','se_sl_init','se_sl_feed','se_sl_finish'):
    if fn in syms:rows.append((name+':'+fn,syms[fn],2,index+1))
  g.dll.pb_config(f.s['se_overlay_active'],len(rows),(C.c_uint16*len(rows))(*(x[1]for x in rows)),(C.c_uint8*len(rows))(*(x[2]for x in rows)),(C.c_uint8*len(rows))(*(x[3]for x in rows)),(C.c_uint8*(16*len(rows)))());return rows
 def check(tag,data):
  bits,attrs,rows=plain.expected(f,data,fonts,3)
  (out/(tag+'-actual.bin')).write_bytes(f.read(0x6000,8000)+f.read(0x4000,1000));(out/(tag+'-expected.bin')).write_bytes(bits+attrs)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
  raw,bank=f.raw_cache();assert raw[0]==1 and raw[1]==len(rows)
  for i,row in enumerate(rows):
   p=raw[0x200+i*0x800:0x220+i*0x800]
   assert tuple(int.from_bytes(p[o:o+3],'little')for o in(0,3,6))==(row.start,row.end,row.next)
   assert(p[14],p[15])==(row.height,row.top)
  assert f.merged()==data and f.read(0xc600,1024)==f.shim
  assert not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_draw_busy'))
  ob.geos.png(bits,attrs,out/(tag+'.png'));return bank
 try:
  for variant in('fallback','materialized'):
   f.source(source);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render()
   f.typed(ob.geos.native_text('syntax full'));f.render();bank,raw=arena();old=sp.roots(raw)
   assert old[2][31]==5 and old[2][30]==0 and f.get('se_bc_count',1)==0
   f.position(at);f.render();assert f.get('se_v_top')==0 and f.get('se_l_mode',1)==1
   ts=targets();g.dll.pb_begin();start=f.total_instructions;f.key(ob.Q)
   assert f.merged()==wanted and f.get('se_hot_pending',1)and f.get('se_bc_count',1)==1
   before=g.reu();canon=f.canonical();queue=g.queue();bridge_start=f.total_instructions
   if variant=='materialized':
    for name in('se_i_ready','se_i_count','se_n_cache_count'):f.put(name,0,1)
    f.put('se_f_owner',4,1);r=invoke(0)
    for _ in range(500):
     assert not r.p&1,('bridge',r.a,calls[-12:])
     if r.a==0:break
     current=g.queue();expected=bytearray(queue[0]);expected[13]=(expected[13]|8)&~32
     assert r.a==1 and f.canonical()==canon and current==(bytes(expected),queue[1]),('pending preserves queue except own ACTIVE/proof',r.a,current[0].hex(),queue[0].hex())
     r=invoke(1)
    assert r.a==0 and f.get('se_bc_count',1)==0 and not f.get('se_doc_read_locks',1)
    after=g.reu();allowed=bytearray(before)
    crcount=int.from_bytes(old[2][112:115],'little');crpage=old[2][104]
    lexrefs=[raw[crpage*4096+64+i*96+47]for i in range(crcount)if raw[crpage*4096+64+i*96+2]&16];assert len(lexrefs)==1
    lexused=int.from_bytes(raw[lexrefs[0]*4096+21:lexrefs[0]*4096+23],'little')
    for lo,hi in((old[1]^128,(old[1]^128)+128),(0x170,0x180),(0x900,0x920),(0xe000,0xe040+crcount*96),(0xf000,0xf040+lexused)):
     allowed[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
    assert after==allowed,'whole16MiB rebase outside exactCOW ranges'
    assert after[bank*65536+old[1]:bank*65536+old[1]+128]==old[2]
    assert after[bank*65536+4096:bank*65536+14*4096]==before[bank*65536+4096:bank*65536+14*4096]
    _,now=arena();new=sp.roots(now);assert new[2][31]==5 and new[2][98]==1 and new[2][104]==14
    expected=blocks(wanted) # Current producer stores logical events, not an artificial EOF sentinel.
    assert len(expected)==crcount
    for i,eventmodel in enumerate(expected):
     cr=now[0xe040+i*96:0xe0a0+i*96];startcr=int.from_bytes(cr[16:19],'little')
     actual=(cr[3],startcr,startcr+int.from_bytes(cr[19:22],'little'),startcr+int.from_bytes(cr[22:25],'little'),cr[69],cr[70])
     assert actual==tuple(eventmodel[k]for k in('kind','start','end','body','language','level')),(i,actual,eventmodel)
     assert int.from_bytes(cr[12:16],'little')==f.get('se_bc_ticket',4) and int.from_bytes(cr[59:63],'little')==f.get('se_bc_ticket',4)
    oldlex=raw[lexrefs[0]*4096+64:lexrefs[0]*4096+64+lexused];newlex=now[0xf040:0xf040+lexused]
    assert newlex[:14]==oldlex[:14] and newlex[86:]==oldlex[86:],'unchanged real absolute lexical spans/metadata'
    assert newlex[14:27]==f.read(f.s['se_bc_arena'],13) and newlex[27:86]==f.read(F+173+27,59)
    event=queue[1][queue[0][15]*32:][:32]
    assert now[0x900:0x920]==event and f.get('se_bc_tail',1)==queue[0][14]
    f.put('se_f_owner',0,1)
   bridge_cost=f.total_instructions-bridge_start
   full_before=g.reu();stable=f.canonical();q=g.queue();force();paint_start=f.total_instructions;f.render();cost=f.total_instructions-start;paint=f.total_instructions-paint_start
   g.dll.pb_end();counts={x[0]:int(g.dll.pb_get(i))for i,x in enumerate(ts)};fe=check(variant,wanted)
   assert f.canonical()==stable and g.queue()==q
   after=g.reu();allowed=bytearray(full_before);a=fe*65536;allowed[a:a+65536]=after[a:a+65536];assert after==allowed,'whole16MiB public render outside actualFE'
   if variant=='fallback':assert counts['geossema:se_sm_feed']>0 and counts['geoslex:se_sl_feed']>0
   else:
    assert counts['rebase:se_sm_feed']>0 and counts['inln:entry']>0 and counts['page:entry']>0 and counts['edit:entry']>0
    assert not counts['geossema:se_sm_feed']and not counts['sema:se_sm_feed']and not counts['geoslex:se_sl_feed']
   row=dict(variant=variant,total_edit_rebase_forced_repaint_instructions=cost,bridge_instructions=bridge_cost,paint_instructions=paint,counts=counts,bitmap_attrs_sha256=hashlib.sha256(f.read(0x6000,8000)+f.read(0x4000,1000)).hexdigest())
   records.append(row);print('CURRENT_REBASE_FRAME',row,flush=True)
  assert records[0]['bitmap_attrs_sha256']==records[1]['bitmap_attrs_sha256']
  fault_records=[]
  if with_faults:
   small=ob.geos.native_text('Intro\r:::basic\r10 PRINT "Hi":REM '+'x'*1000+'\r:::\rMiddle ordinary line.\rTail.')
   small_at=small.index(ob.geos.native_text('ordinary'))+3
   def prepare(byte=ob.Q,position=small_at):
    f.source(small);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render();f.typed(ob.geos.native_text('syntax full'));f.render()
    f.position(position);f.render();f.key(byte);live=small[:position]+bytes([byte])+small[position:]
    assert f.merged()==live and f.get('se_bc_count',1)==1
    b,raw=arena();old=sp.roots(raw);n=int.from_bytes(old[2][112:115],'little');crpage=old[2][104]
    lexrefs=[raw[crpage*4096+64+i*96+47]for i in range(n)if raw[crpage*4096+64+i*96+2]&16];assert len(lexrefs)==1
    lexused=int.from_bytes(raw[lexrefs[0]*4096+21:lexrefs[0]*4096+23],'little')
    spans=[(old[1]^128,(old[1]^128)+128),(0x170,0x180),(0x900,0x920),(0xe000,0xe040+n*96),(0xf000,0xf040+lexused)]
    state=dict(bank=b,raw=raw,old=old,full=g.reu(),queue=g.queue(),canonical=f.canonical(),live=live,spans=spans)
    for name in('se_i_ready','se_i_count','se_n_cache_count'):f.put(name,0,1)
    f.put('se_f_owner',4,1);return state
   def pending(state,target):
    r=invoke(0)
    for _ in range(500):
     assert not r.p&1 and r.a==1,('reach',target,r.a,calls[-4:])
     if f.m.read(F+1)==target[0] and (target[0]!=5 or f.m.read(F+94)==target[1]):return
     r=invoke(1)
    raise AssertionError(('unreached',target))
   def preserved(state,tag):
    current=g.queue();q=state['queue'];expected=bytearray(q[0]);expected[13]&=~(8|32)
    assert current==(bytes(expected),q[1]),(tag,'unretired event/descriptor')
    assert f.canonical()==state['canonical']and f.merged()==state['live']and not f.get('se_doc_read_locks',1)
    after=g.reu();allowed=bytearray(state['full']);b=state['bank']
    for lo,hi in state['spans']:allowed[b*65536+lo:b*65536+hi]=after[b*65536+lo:b*65536+hi]
    assert after==allowed,(tag,'whole16MiB outside exact unused COW spans')
    assert after[b*65536+state['old'][1]:b*65536+state['old'][1]+128]==state['old'][2]
    f.put('se_f_owner',0,1);before=g.reu();force();f.render();fe=check('recovery-'+tag,state['live']);after=g.reu();allowed=bytearray(before);a=fe*65536;allowed[a:a+65536]=after[a:a+65536]
    assert after==allowed and g.queue()==(bytes(expected),q[1]),(tag,'fallback changed old cache/intent')
    fault_records.append(tag);print('CURRENT_REBASE_FAULT',tag,flush=True)
   for target in[(1,0),(2,0),(3,0),(4,0)]+[(5,n)for n in range(1,13)]:
    state=prepare();pending(state,target);r=invoke(2);assert not r.p&1 and r.a==0
    preserved(state,'cancel-'+str(target[0])+'-'+str(target[1]))
   # Both candidate pages were already sealed, but are revalidated in the
   # same terminal call as root VALID/retirement, with private expected CRCs.
   for offset in(0xe040,0xf040):
    state=prepare();pending(state,(5,12));value=g.reu()[state['bank']*65536+offset]
    f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',offset);f.put('se_object_length',1,2);f.put('se_object_c64',0x8800,2);f.m.write(0x8800,value^1)
    assert not f.call('se_object_copy',0).p&1
    r=invoke(1);assert r.p&1 and r.a in(0xc1,0xc2)
    preserved(state,'checked-candidate-payload-write-'+hex(offset))
   for tag,byte,pos in [('star',42,small_at),('CR',13,small_at),('shifted-lexical-range',ob.Q,2)]:
    state=prepare(byte,pos);r=invoke(0)
    for _ in range(500):
     if r.p&1 or r.a!=1:break
     r=invoke(1)
    assert r.p&1 or r.a==2;preserved(state,'refuse-'+tag)
   for ident in(14,34,40):
    state=prepare();pending(state,(4,0));slot=int(ident==40)
    idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==slot)
    f.m.write(f.s['se_overlay_ids']+idx,255);f.m.write(f.s['se_overlay_active']+slot,0)
    if ident==40:
     f.put('se_e_job',11,1);f.m.load(0x9135,bytes((40,1)));f.call('se_editor_service');f.put('se_e_error',0,1)
    else:
     for _ in range(500):
      r=invoke(1)
      if r.p&1 or r.a!=1:break
     assert r.p&1
    f.m.write(f.s['se_overlay_ids']+idx,ident);f.m.write(f.s['se_overlay_active']+slot,0)
    preserved(state,'missing-'+str(ident))
   state=prepare();pending(state,(5,12));f.put('se_e_job',11,1);f.m.load(0x9135,bytes((40,1)));f.queued(3);f.call('se_editor_service');preserved(state,'actual-queued-STOP-before-critical-commit')
   state=prepare();pending(state,(5,12));f.m.write(F+94,13);r=invoke(1);assert r.p&1;preserved(state,'invalid-publication-phase13')
   for name,width in[('se_r_revision',4),('se_bc_ticket',4),('se_bc_incarnation',4)]:
    state=prepare();pending(state,(4,0));old=f.get(name,width);f.put(name,old^1,width);r=invoke(1);f.put(name,old,width)
    assert r.p&1;preserved(state,'changed-'+name)
   # Actual flush adds a representation-only event; no single-SPLICE proof
   # may consume this unread SPLICE+REKEY pair or silently reticket old records.
   state=prepare();f.put('se_f_owner',0,1);g.flush();assert f.get('se_bc_count',1)==2
   before=g.reu();queue=g.queue();canon=f.canonical();f.put('se_f_owner',4,1);r=invoke(0)
   assert not r.p&1 and r.a==2 and g.reu()==before and g.queue()==queue and f.canonical()==canon
   f.put('se_f_owner',0,1);force();f.render();check('refuse-unread-SPLICE-REKEY',state['live']);assert g.queue()==queue
   fault_records.append('actual-unread-SPLICE-plus-REKEY-refused')
   # An unrelated legitimate reader must remain owned by its actual caller.
   state=prepare();assert not f.call('se_doc_read_acquire').p&1
   # Ordinary BEGIN initializes its caller-mode input byte; supply zero as
   # documented rather than treating inherited scratch as an immutable input.
   f.m.write(0x8b23,0)
   phase=f.read(F,576)+f.read(0x8880,0x2c0);before=g.reu();queue=g.queue();r=invoke(0)
   assert not r.p&1 and r.a==2 and f.get('se_doc_read_locks',1)==1 and g.reu()==before and g.queue()==queue and f.read(F,576)+f.read(0x8880,0x2c0)==phase
   assert not f.call('se_doc_read_release').p&1;f.put('se_f_owner',0,1)
   fault_records.append('foreign-reader-admission-opaque-and-not-released')
   # Source-matched checked root writes with valid CRC, explicitly unsupported
   # feature3/7. Restore injected root before independent old-path recovery.
   for feature in(3,7):
    state=prepare();h=bytearray(state['old'][2]);h[31]=feature;h[119:121]=binascii.crc_hqx(h[:5]+h[6:119]+h[121:],65535).to_bytes(2,'little')
    def putroot(payload):
     f.m.load(0x8800,payload);f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',state['old'][1]);f.put('se_object_length',128,2);f.put('se_object_c64',0x8800,2);assert not f.call('se_object_copy',0).p&1
    putroot(h);r=invoke(0)
    for _ in range(100):
     if r.p&1 or r.a!=1:break
     r=invoke(1)
    assert r.p&1 or r.a==2
    putroot(state['old'][2]);preserved(state,'unknown-root-feature-'+str(feature))
   # No older root snapshot may overwrite a checked changed baseline root.
   state=prepare();pending(state,(5,12));h=bytearray(state['old'][2]);h[18]^=1;h[119:121]=binascii.crc_hqx(h[:5]+h[6:119]+h[121:],65535).to_bytes(2,'little')
   def checked_root(payload):
    f.m.load(0x8800,payload);f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',state['old'][1]);f.put('se_object_length',128,2);f.put('se_object_c64',0x8800,2);assert not f.call('se_object_copy',0).p&1
   checked_root(h);r=invoke(1);assert r.p&1;checked_root(state['old'][2]);preserved(state,'checked-old-root-write-before-critical-commit')
   state=prepare();pending(state,(4,0));token=f.read(f.s['se_bc_arena'],5);f.m.load(f.s['se_bc_arena'],f.read(f.s['se_doc_original'],5));r=invoke(1);f.m.load(f.s['se_bc_arena'],token)
   assert r.p&1;preserved(state,'foreign-arena-token-during-yield')
   state=prepare();pending(state,(4,0));f.put('se_render_caps',0,1);r=invoke(1);f.put('se_render_caps',3,1)
   assert r.p&1;preserved(state,'Plain-during-yield')
   state=prepare();pending(state,(4,0));epoch=f.get('se_reu_epoch',2);f.put('se_reu_epoch',epoch^1,2)
   f.put('se_e_job',11,1);f.m.load(0x9135,bytes((40,1)));f.call('se_editor_service');assert f.get('se_e_error',1)
   # se_fs_end deliberately never decrements a lease from a different epoch.
   # The host fault restores the same lifetime only for test teardown; restore
   # the actual saved owned reader and finish that lease once, without deriving
   # a new ownership claim or treating rollback as production recovery.
   assert f.get('se_doc_read_locks',1)==1 and not f.get('se_fs_owned',1) and not f.get('se_f_owner',1)
   f.put('se_reu_epoch',epoch,2);f.put('se_e_error',0,1);f.m.load(f.s['se_fs_state'],f.read(F+173,86));assert not f.call('se_fs_end').p&1
   preserved(state,'provider-epoch-refusal-no-foreign-release-explicit-restored-lifetime-teardown')
   state=prepare();before=g.reu();phase=f.read(F,576)+f.read(0x8880,0x2c0);parent=f.read(0x9134,68)
   for owner in(0,1,2,3,5,255):
    f.put('se_f_owner',owner,1)
    for ident,slot,ops in[(40,1,(0,1,2)),(34,0,range(6))]:
     for op in ops:
      f.put('se_overlay_frame',op,1);ram_before=f.read(0,65536);provider_before=f.read(f.s['object_owner'],184)+f.read(f.s['se_reu_map'],772)+f.read(f.s['se_reu_banks'],2);r,n=f.fast_call(f.s['se_overlay_call'],a=ident,x=slot);f.total_instructions+=n
      assert r.p&1 and r.a==0xb2 and f.read(F,576)+f.read(0x8880,0x2c0)==phase and f.read(0x9134,68)==parent and g.reu()==before
   f.put('se_f_owner',4,1);f.put('se_render_caps',0,1);r=invoke(0);assert not r.p&1 and r.a==2 and f.read(F,576)+f.read(0x8880,0x2c0)==phase and g.reu()==before
   f.put('se_f_owner',0,1);fault_records.append('54-foreign-owner-calls-and-Plain-phase-opaque')
  result=dict(status='PASS_NARROW_PRIVATE',fixture=g.identity,budget=json.loads((out/'leaf/budget.json').read_text()),records=records,calls=calls,faults=fault_records,source_bytes=len(source),position=at,scope=__doc__,declared_component_RAM_spans=ram_spans)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS_CURRENT_EDIT_REBASE',out,flush=True)
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),records=records,calls=calls),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--length',type=int,default=8000);p.add_argument('--faults',action='store_true');p.add_argument('--mixed',action='store_true');a=p.parse_args()
 out=ROOT/'build/cache-edit-rebase-current'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.length,a.faults,a.mixed)
