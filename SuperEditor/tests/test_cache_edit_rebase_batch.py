"""Private current-schema repeatable rebase through genuine root job routing.

The public edit/WRAP_OFF flush/render sequence is untouched. Two substituted
command capsules and two newly imported private assets exercise a proposed
61-asset runtime, with the frozen resident unchanged. Not a packaged startup
or native proof. All classifiers/LEX readers remain original flags5 consumers.
"""
import sys
from pathlib import Path
ROOT_IMPORT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT_IMPORT/"tests"),str(ROOT_IMPORT/"tools")]
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, importlib.util, json, re
import test_cache_observer as ob
import test_cache_splice as sp
import test_plain_geos as plain
from supermark_model import blocks
ROOT=ob.ROOT
BASE=ROOT/'build/cache-rebase-cold62-prep/fixture'
VARIANT_DIR=ROOT/'build/cache-rebase-churn/batch4'
F=0x8d00

def labels(path):return {n:int(a,16) for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\w+)',path.read_text())}

def run(out,base,length=8000,repeats=3,protocols=False,variant="candidate"):
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes())
 import font_fixture
 font_fixture.ROOT=base
 images={'parse':(VARIANT_DIR/'parse.seo').read_bytes()};g=ob.Gate(out/'gate',base);f=g.f;original=dict(f.assets)
 import font_fixture
 font_fixture.ROOT=g.frozen
 fonts={n:(g.frozen/'fonts'/n).read_bytes() for n in ob.geos.GEOS_FONTS+('native8.bin',)}
 source=ob.geos.native_text('Intro\r:::basic\r10 PRINT "Hi":REM '+'x'*length+'\r:::\rMiddle ordinary line.\rTail.')
 at=source.index(ob.geos.native_text('ordinary'))+3
 results=[];service_trace=[]
 original_call=f.call
 def observed_call(name,a=0):
  if name=='se_editor_service':
   before=dict(request=f.m.read(0x9135),op=f.m.read(0x9136),ps=f.m.read(0x9134),s=f.m.read(F+1),phase=f.m.read(F+94),queue=g.queue()[0].hex())
   service_trace.append(before);service_trace[:]=service_trace[-64:]
  r=original_call(name,a)
  if name=='se_editor_service' and f.get('se_e_error',1):
   (out/'service-failure.json').write_text(json.dumps(dict(trace=service_trace,error=f.get('se_e_error',1),frame=f.read(F,576).hex(),root=f.read(0x8880,128).hex(),event=f.read(0x8a80,32).hex(),rekey=f.read(0x8940,32).hex()),indent=2)+'\n')
  return r
 f.call=observed_call
 def arena():
  t=f.read(f.s['se_bc_arena'],5);h=f.m.read(f.s['object_extents']+t[0]*16);bank=f.m.read(f.s['se_reu_map']+h)
  return bank,g.reu()[bank*65536:(bank+1)*65536]
 def check(tag,data):
  bits,attrs,rows=plain.expected(f,data,fonts,3)
  actual=f.read(0x6000,8000)+f.read(0x4000,1000)
  assert actual==bits+attrs,(tag,'independent pixels',f.get('se_v_top'),hex(f.get('se_e_error',1)))
  raw,_=f.raw_cache();assert raw[0]==1 and raw[1]==len(rows)
  for i,row in enumerate(rows):
   p=raw[0x200+i*0x800:0x220+i*0x800]
   assert tuple(int.from_bytes(p[o:o+3],'little') for o in (0,3,6))==(row.start,row.end,row.next),(tag,'canonical row',i)
   assert(p[14],p[15])==(row.height,row.top),(tag,'geometry',i)
  assert f.merged()==data and f.read(0xc600,1024)==f.shim
  assert not any(f.get(n,1) for n in ('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_draw_busy'))
  ob.geos.png(bits,attrs,out/(tag+'.png'))
  return hashlib.sha256(actual).hexdigest()
 def counters():
  wanted=[('rebase',41,VARIANT_DIR/'parse.lbl'),('geossema',24,base/'build/overlays/geossema.lbl'),('geoslex',25,base/'build/overlays/geoslex.lbl')]
  wanted += [(n,i,base/'build/cache-editor'/(n+'.lbl')) for n,i in [('sema',34),('inln',35),('page',37),('line',39)]]
  wanted.append(('edit',45,base/'build/lexical/edit.lbl'))
  rows=[]
  for name,ident,path in wanted:
   if name=='rebase' and variant=='control':continue
   syms=labels(path)
   indexes=[i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==1]
   if not indexes:continue
   for fn in ('entry','se_sm_init','se_sm_feed','se_sl_init','se_sl_feed'):
    if fn in syms:rows.append((name+':'+fn,syms[fn],2,indexes[0]+1))
  g.dll.pb_config(f.s['se_overlay_active'],len(rows),(C.c_uint16*len(rows))(*(r[1]for r in rows)),(C.c_uint8*len(rows))(*(r[2]for r in rows)),(C.c_uint8*len(rows))(*(r[3]for r in rows)),(C.c_uint8*(16*len(rows)))())
  return rows
 def assert_records(raw,data):
  root=sp.roots(raw)[2];page=root[104];n=int.from_bytes(root[112:115],'little');expected=blocks(data)
  assert root[31]==5 and n==len(expected)
  for i,e in enumerate(expected):
   cr=raw[page*4096+64+i*96:page*4096+160+i*96];a=int.from_bytes(cr[16:19],'little')
   assert (cr[3],a,a+int.from_bytes(cr[19:22],'little'),a+int.from_bytes(cr[22:25],'little'),cr[69],cr[70])==tuple(e[k]for k in ('kind','start','end','body','language','level')),(i,'all real CR classification')
   assert int.from_bytes(cr[12:16],'little')==f.get('se_bc_ticket',4)
  return root
 try:
  hashes={}
  for variant in (variant,):
   f.assets=dict(original)
   if variant=='candidate':f.assets.update(images)
   f.source(source);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render();f.typed(ob.geos.native_text('syntax full'));f.render()
   f.position(at);f.render();bank,raw=arena();initial=sp.roots(raw)
   assert initial[2][31]==5 and f.get('se_bc_count',1)==0
   data=source
   for k in range(repeats):
    previous=g.reu();old=sp.roots(arena()[1]);canonical=f.canonical();ts=counters();g.dll.pb_begin();begin=f.total_instructions;loads_before=f.get('se_overlay_loads',2);calls_before=f.get('se_overlay_calls',2)
    f.key(ob.Q);data=data[:at+k]+bytes([ob.Q])+data[at+k:]
    assert f.merged()==data
    if variant=='candidate' and length>=4096:assert f.get('se_bc_count',1)==1
    # Actual public no-wrap command flushes C6 pending changes via R2, then
    # invalidates derived row geometry. It does not seed any cache authority.
    f.command(77)
    assert f.merged()==data
    if k==0 or variant=='candidate' and length>=4096:assert f.get('se_bc_count',1)==2,('actual SPLICE+REKEY',g.queue()[0].hex())
    before_render=g.reu();q=g.queue();stable=f.canonical();mid=f.total_instructions
    ram_before=f.read(0,65536);provider_before=f.read(f.s['object_owner'],184)+f.read(f.s['se_reu_map'],772)
    f.render();cost=f.total_instructions-begin;paint=f.total_instructions-mid;g.dll.pb_end()
    counts={r[0]:int(g.dll.pb_get(i))for i,r in enumerate(ts)}
    assert f.canonical()==stable,'render changed source/history/clipboard'
    assert provider_before==f.read(f.s['object_owner'],184)+f.read(f.s['se_reu_map'],772),'render changed object descriptors/provider ownership'
    ram_after=f.read(0,65536);ram_allowed=bytearray(ram_before)
    # Declared CPU loans: borrowed ZP/stack; visible/plan screen RAM; overlay
    # staging/slots; document read cache; owner4 scratch+view; actual API state;
    # catalog managed bits, font/preview derived validity and REU/VIC registers.
    # Canonical source/history/hot buffer and provider descriptors independently
    # remain exact above, even where an API state segment is mutable.
    ram_spans=[(2,26),(0x100,0x200),(0x4000,0x4800),(0x5000,0x8000),(0x8000,0x8800),(0x8880,0x9200),(0x9a00,0x9de5),(0x9e00,0x9fc6),(0xa000,0xc000),(0xc000,0xc600),(0xca00,0xcb80),(0xcbc0,0xd000),(0xd000,0xd040),(0xdf00,0xdf0c)]
    for lo,hi in ram_spans:ram_allowed[lo:hi]=ram_after[lo:hi]
    assert ram_after==ram_allowed,('undeclared64KiBRAM write',[hex(i)for i,(x,y)in enumerate(zip(ram_after,ram_allowed))if x!=y][:32])
    digest=check(variant+'-'+str(k),data);hashes[(variant,k)]=digest
    nowbank,now=arena();assert nowbank==bank
    after=g.reu();allowed=bytearray(before_render)
    fe=f.raw_cache()[1];allowed[fe*65536:(fe+1)*65536]=after[fe*65536:(fe+1)*65536]
    if variant=='candidate' and length>=4096:
     root=assert_records(now,data)
     pair=12 if old[2][104]==14 else 14
     assert root[104]==pair and f.get('se_bc_count',1)==0,(k,'published pair/retired events',root[104],pair,g.queue()[0].hex())
     n=int.from_bytes(root[112:115],'little');lexused=int.from_bytes(now[(pair+1)*4096+21:(pair+1)*4096+23],'little')
     start=old[2][30]
     for lo,hi in ((old[1]^128,(old[1]^128)+128),(0x100+pair*8,0x100+(pair+2)*8),(0x900+start*32,0x900+(start+2)*32),(pair*4096,pair*4096+64+n*96),((pair+1)*4096,(pair+1)*4096+64+lexused)):
      allowed[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
     assert now[old[1]:old[1]+128]==old[2],'previous selected root overwritten'
     assert counts.get('rebase:se_sm_feed',0)>0 and counts.get('inln:entry',0)>0 and counts.get('edit:entry',0)>0
     assert counts.get('geossema:se_sm_feed',0)==counts.get('sema:se_sm_feed',0)==counts.get('geoslex:se_sl_feed',0)==0,counts
    else:
     assert counts.get('rebase:entry',0)==0,('small documents must not dispatch worker',counts)
     assert counts.get('geossema:se_sm_feed',0)>0
     assert g.queue()==q,'legacy render retired observations'
    assert after==allowed,('whole16MiB render writes beyond precise COW + actual FE',variant,k,[hex(i)for i,(x,y)in enumerate(zip(after,allowed))if x!=y][:32])
    item=dict(variant=variant,repeat=k,loads=(f.get('se_overlay_loads',2)-loads_before)&65535,overlay_calls=(f.get('se_overlay_calls',2)-calls_before)&65535,total_edit_flush_repaint_instructions=cost,repaint_instructions=paint,counts=counts,pixels_sha256=digest,cr_page=sp.roots(now)[2][104],journal_count=sp.roots(now)[2][30])
    results.append(item);print('REPEAT_REBASE',json.dumps(item),flush=True)
  faults=[]
  if protocols:
   f.assets=dict(original);f.assets.update(images)
   def prepare_pending():
    f.source(source);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render();f.typed(ob.geos.native_text('syntax full'));f.render();f.position(at);f.render();f.key(ob.Q)
    data=source[:at]+bytes([ob.Q])+source[at:]
    return data
   def prepare_root():
    data=prepare_pending();f.command(77)
    assert f.get('se_bc_count',1)==2
    f.call('se_editor_render')
    return data
   def reach(state,phase=None):
    for _ in range(800):
     assert f.get('se_e_job',1)==11 and not f.get('se_e_error',1)
     if f.m.read(0x9135)==41 and f.m.read(F+1)==state and (phase is None or f.m.read(F+94)==phase):return
     f.call('se_editor_service')
    raise AssertionError(('root continuation not reached',state,phase,service_trace[-8:]))
   def snap():return dict(reu=g.reu(),canonical=f.canonical(),queue=g.queue(),pixels=f.read(0x6000,8000)+f.read(0x4000,1000),root=sp.roots(arena()[1]))
   def unchanged(snapshot,tag,allowed_journal=None):
    expected=bytearray(snapshot['queue'][0]);expected[13]&=~(8|32)
    assert g.queue()==(bytes(expected),snapshot['queue'][1]),(tag,'intent retired or changed')
    after=g.reu();expected_reu=bytearray(snapshot['reu'])
    if allowed_journal is not None:
     bank,_=arena();lo=bank*65536+0x900+allowed_journal*32
     expected_reu[lo:lo+32]=after[lo:lo+32]
    assert after==expected_reu and f.canonical()==snapshot['canonical'],(tag,'whole REU/source/history outside exact final uncommitted journal record')
    assert f.read(0x6000,8000)+f.read(0x4000,1000)==snapshot['pixels'],(tag,'incomplete pixels published')
    assert not any(f.get(n,1) for n in ('se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned')),(tag,'root cleanup',service_trace[-5:])
    assert f.read(0xc600,1024)==f.shim
   def recover(data,tag):
    f.key(3);f.render();check('recovery-'+tag,data)
   # A true pending-source baseline followed by representation-only flush.
   # Force fresh derived layout through the same declared benchmark seam used
   # by existing repaint tests; no semantic/source/proof result is seeded.
   data=prepare_pending()
   for name in ('se_gc_width','se_r_valid','se_l_valid'):f.put(name,0,1)
   f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_l_need_wrap',1,1)
   f.render();assert f.get('se_bc_count',1)==0 and f.get('se_hot_pending',1)==1
   oldpending=sp.roots(arena()[1]);assert oldpending[2][62]==1
   ticket=f.get('se_bc_ticket',4);g.flush();assert f.get('se_bc_count',1)==1 and f.get('se_bc_ticket',4)==ticket
   assert g.queue()[1][f.get('se_bc_tail',1)*32+1]==2
   f.command(77);before=f.total_instructions;f.render();check('pure-REKEY',data)
   assert f.get('se_bc_count',1)==0 and f.get('se_bc_ticket',4)==ticket
   root=assert_records(arena()[1],data);assert root[30]==2 and root[62]==0
   faults.append(dict(case='pending materialize then actual flush REKEY-only',render_instructions=f.total_instructions-before))
   # Every public C41 continuation can be cancelled, including replay writes.
   # The point snapshot is after permissible draft work; STOP itself writes no
   # REU and does not retire/alter any queued event or publish partial pixels.
   for state,phase in [(1,None),(2,None),(3,None),(4,None)]+[(5,x)for x in (1,3,5,6,8,10)]:
    data=prepare_root();reach(state,phase);snapshot=snap();tail=f.get('se_input_tail',1)
    assert f.get('se_doc_read_locks',1)==1 and f.get('se_bc_flags',1)&8
    f.queued(3);f.call('se_editor_service');assert f.get('se_input_tail',1)==tail
    tag='queued-STOP-'+str(state)+'-'+str(phase);unchanged(snapshot,tag)
    f.tick();f.settle();f.render();check('recovery-'+tag,data)
    # Retry may overwrite only the now-unreachable draft pair and must finish.
    assert f.get('se_bc_count',1)==0 and sp.roots(arena()[1])[2][104]==14
    faults.append(dict(case=tag,retry_reclaimed=True));print('REBASE_PROTOCOL',tag,flush=True)
   for fault in ('missing-C7','missing-R14','missing-R34','missing-C41','stale-asset-epoch','binding-C41'):
    data=prepare_root();reach(4)
    if fault=='missing-R34':reach(5,1)
    if fault=='missing-C7':
     # State7 hands the actual live source lease to C7op11. This C7 request
     # can be missing too; it must not depend on a loaded outer C41 capsule.
     data=prepare_root()
     for _ in range(100):
      if f.m.read(0x9135)==7 and f.m.read(0x9136)==11:break
      f.call('se_editor_service')
     else:raise AssertionError('C7 source-proof handoff absent')
    ident={'missing-C7':7,'missing-R14':14,'missing-R34':34}.get(fault,41);slot=int(ident not in (14,34))
    idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==slot)
    repair=None
    if fault.startswith('missing-'):
     f.m.write(f.s['se_overlay_ids']+idx,0);repair=lambda:f.m.write(f.s['se_overlay_ids']+idx,ident)
    elif fault=='stale-asset-epoch':
     syms=labels(base/'build/editor.lbl');address=syms['asset_epoch'];old=f.read(address,2);f.m.write(address,old[0]^1);repair=lambda:f.m.load(address,old)
    else:
     handle=f.m.read(f.s['se_overlay_asset']+idx//16);offset=(idx%16)*4096;bank=f.m.read(f.s['se_reu_map']+handle);old=g.reu()[bank*65536+offset]
     def code_write(value):
      f.put('se_reu_logical',handle,1);f.put('se_reu_offset',offset,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x8800,2);f.m.write(0x8800,value)
      r,n=f.fast_call(f.s['se_reu_copy'],a=0);assert not r.p&1
     code_write(old^1);repair=lambda:code_write(old)
    f.m.write(f.s['se_overlay_active']+slot,0);snapshot=snap()
    for _ in range(60):
     f.call('se_editor_service')
     if f.get('se_e_error',1):break
    else:raise AssertionError(('missing worker never reached',fault))
    assert f.get('se_e_error',1)==(0x17 if fault.startswith('missing-') else 0x18 if fault=='stale-asset-epoch' else 0x11),(fault,hex(f.get('se_e_error',1)))
    unchanged(snapshot,fault);repair();recover(data,fault);assert f.get('se_bc_count',1)==0
    faults.append(dict(case=fault,held_lease=True,resident_cleanup=True));print('REBASE_PROTOCOL',fault,flush=True)
   # Held source/journal authority is rechecked after every foreground yield.
   for name,width in (('se_r_revision',4),('se_bc_ticket',4),('se_bc_incarnation',4),('se_bc_head',1)):
    data=prepare_root();reach(4);snapshot=snap();value=f.get(name,width);f.put(name,value^1,width)
    f.call('se_editor_service');f.put(name,value,width)
    assert f.get('se_e_error',1)==(0xb1 if name=='se_r_revision' else 0xc1),(name,'held authority change not refused')
    unchanged(snapshot,'changed-'+name);recover(data,'changed-'+name)
    faults.append(dict(case='yielded-'+name+'-change'))
   for target in ('selected-root','draft-CR','draft-LEX'):
    data=prepare_root();reach(5,10);bank,raw=arena();live=sp.roots(raw)
    offset=live[1] if target=='selected-root' else 0xe040 if target=='draft-CR' else 0xf040
    saved=raw[offset:offset+(128 if target=='selected-root' else 1)]
    changed=bytearray(saved);changed[18 if target=='selected-root' else 0]^=1
    if target=='selected-root':
     import binascii
     changed[119:121]=binascii.crc_hqx(changed[:5]+changed[6:119]+changed[121:],65535).to_bytes(2,'little')
    def cache_write(payload):
     f.m.load(0x8800,payload);f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',offset);f.put('se_object_length',len(payload),2);f.put('se_object_c64',0x8800,2)
     assert not f.call('se_object_copy',0).p&1
    cache_write(changed);snapshot=snap();f.call('se_editor_service')
    assert f.get('se_e_error',1) in (0xc1,0xc2)
    unchanged(snapshot,'checked-'+target,live[2][30]+1);cache_write(saved);recover(data,'checked-'+target)
    faults.append(dict(case='checked-'+target+'-write-before-critical-publication'))
   # Unsupported real edits/cache geometry use the original parser. The
   # optional worker must not convert a routine BACK/markup/inline edit into
   # a user-visible source error or retire observations before a baseline.
   refusal_cases=[('markup',source,at,'insert',42),('before-code',source,2,'insert',ob.Q),('delete',source,at,'delete',0),('back',source,at,'back',0),('inline-elsewhere',ob.geos.native_text('Intro **bold**')+source[5:],at+9,'insert',ob.Q),('CR',source,at,'insert',13)]
   for tag,initial,position,action,byte in refusal_cases:
    f.source(initial);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render();f.typed(ob.geos.native_text('syntax full'));f.render();f.position(position);f.render()
    if action=='insert':f.key(byte);data=initial[:position]+bytes([byte])+initial[position:]
    elif action=='delete':f.command(4);data=initial[:position]+initial[position+1:]
    else:f.command(3);data=initial[:position-1]+initial[position:]
    f.command(77);before=g.reu();q=g.queue();canonical=f.canonical();f.render();check('refusal-'+tag,data)
    after=g.reu();allowed=bytearray(before);fe=f.raw_cache()[1];allowed[fe*65536:(fe+1)*65536]=after[fe*65536:(fe+1)*65536]
    assert after==allowed and g.queue()==q and f.canonical()==canonical,(tag,'optional refusal mutated semantic cache/event/source',g.queue()[0].hex(),q[0].hex(),f.canonical()==canonical,[hex(i)for i,(x,y)in enumerate(zip(after,allowed))if x!=y][:32],sp.roots(arena()[1])[2][30])
    faults.append(dict(case='safe-legacy-'+tag));print('REBASE_PROTOCOL legacy-'+tag,flush=True)
  result=dict(passed=True,base=str(base),identity=g.identity,verifier_sha256=hashlib.sha256((out/'verifier.py').read_bytes()).hexdigest(),source_length=len(source),repeats=repeats,records=results,protocols=faults,budgets=json.loads((VARIANT_DIR/'budget.json').read_text()) if variant=='candidate' else {},scope='Private bounded4 C41 substitution; real cold62 source-integrated C7/C21/C41/R34 + public edit/flush/root render; actual packaged private62 cohort; no native' if variant=='candidate' else 'Frozen realcold60 paired control; same edit/flush/render and independent oracles')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()

def main():
 global VARIANT_DIR
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--length',type=int,default=8000);p.add_argument('--repeats',type=int,default=3);p.add_argument('--out',type=Path);p.add_argument('--protocols',action='store_true');p.add_argument('--profile',type=Path,default=VARIANT_DIR);p.add_argument('--variant',choices=('candidate','control'),default='candidate')
 a=p.parse_args();VARIANT_DIR=a.profile.resolve();out=a.out or ROOT/'build/cache-edit-rebase-production'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);print('RUN',out,flush=True);run(out,a.base.resolve(),a.length,a.repeats,a.protocols,a.variant)
if __name__=='__main__':main()
