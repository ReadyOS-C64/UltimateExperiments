"""Actual short-row key/render/idle attribution on an immutable62 product.

CPU instructions only; no native clock/IRQ/wall-time latency claim. Initial
source setup uses real document/provider APIs and actual registered capsules;
mode/preset/GOTO/caret/input actions are public editor commands. No product code,
semantic state or cache authority is substituted. No app build is performed.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,bisect,ctypes as C,hashlib,importlib.util,json,re,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as ob
import test_plain_geos as plain
from test_cache_rebase_registered import metadata
spec=importlib.util.spec_from_file_location('warm_input_runner',ROOT/'src/render/geos/warm-input-profile-probe/runner.py');profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
BASE=ROOT/'build/cache-rebase-committed/20261026T224637147761Z/fixture'
def syms(p):return [(int(a,16),n)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',p.read_text())]

def run(out,base,pairs=5,only=None):
 out.mkdir(parents=True);(out/'verifier.py').write_bytes(Path(__file__).read_bytes())
 import font_fixture
 font_fixture.ROOT=base
 oldrunner=ob.runner;ob.runner=profile.build
 try:g=ob.Gate(out/'gate',base)
 finally:ob.runner=oldrunner
 f=g.f;names=g.identity['names'];assert len(names)==62
 font_fixture.ROOT=g.frozen
 symbols={'resident':syms(base/'build/editor.lbl')};payloads={'resident':None};paths={}
 for name in names:
  p=metadata(base,name);raw=p.with_suffix('.bin').read_bytes();assert raw==f.assets[name][36:]
  symbols[name]=syms(p.with_suffix('.lbl'));payloads[name]=raw;paths[name]=str(p)
 stage=payloads['type'][32:];symbols['type-stage']=symbols['type'];payloads['type-stage']=stage
 g.dll.wp_config(f.s['se_overlay_active'],f.s['se_reu_copy'],f.s['se_reu_logical'],f.s['se_reu_length'],f.s['se_reu_logical_owner'],len(stage),(C.c_uint8*16).from_buffer_copy(stage[:16]))
 g.dll.wp_extra(f.s['se_overlay_call'],f.s['se_overlay_frame'],f.s['se_gf_state']+21)
 fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)}
 def decode(k):
  if k<65536:return 'resident',k
  tag=(k-65536)//4096
  if tag==64:return 'type-stage',0x5000+(k&4095)
  name=names[tag];return name,(0xB000 if f.assets[name][5]else 0xA000)+(k&4095)
 def named(k):
  name,pc=decode(k);near=[(a,n)for a,n in symbols[name]if a<=pc and not n.startswith('@')and (name=='resident'or a&0xf000==pc&0xf000)]
  a,n=max(near,default=(pc,'?'))
  return dict(asset=name,pc=f'{pc:04X}',symbol=n,offset=pc-a)
 def collect():
  arr=[]
  for typ in range(3):
   buf=(C.c_uint64*profile.N)();g.dll.wp_dump(typ,buf);arr.append(buf)
  selfs,inc,calls=arr;modules={};functions={};entries={};crc=[]
  for k,n in enumerate(selfs):
   if not n:continue
   item=named(k);name=item['asset'];modules[name]=modules.get(name,0)+int(n);key=name+':'+item['symbol'];functions[key]=functions.get(key,0)+int(n)
   if item['offset']==0 and item['symbol']in('entry','se_sm_init','se_sm_feed','se_si_init','se_si_feed','se_sl_init','se_sl_feed','se_gct_stage','se_gst_transaction','se_typing_patch','se_typing_color_patch','se_gtt_certify','se_gcc_status'):entries[key]=int(n)
  # Exact known entry PCs, independent of same-address label aliases.
  for name,ss in symbols.items():
   for pc,fn in ss:
    if fn not in ('entry','se_sm_init','se_sm_feed','se_si_init','se_si_feed','se_sl_init','se_sl_feed','se_gct_stage','se_gst_transaction','se_typing_patch','se_typing_color_patch','se_gtt_certify','se_gcc_status'):continue
    if name=='resident':k=pc
    elif name=='type-stage':
     if not 0x5000<=pc<0x5000+len(stage):continue
     k=65536+64*4096+(pc-0x5000)
    else:
     origin=0xb000 if f.assets[name][5]else 0xa000
     if not origin<=pc<origin+len(payloads[name]):continue
     k=65536+names.index(name)*4096+(pc-origin)
    if selfs[k]:entries[name+':'+fn]=int(selfs[k])
  for k,n in enumerate(calls):
   if not n:continue
   name,pc=decode(k);raw=f.read(pc,3)if name=='resident'else payloads[name][pc-(0x5000 if name=='type-stage'else 0xb000 if f.assets[name][5]else 0xa000):][:3]
   if len(raw)==3 and raw[0]==0x20 and int.from_bytes(raw[1:],'little')==f.s['se_crc_byte']:crc.append(dict(**named(k),calls=int(n),inclusive_instructions=int(inc[k])))
  top=[dict(**named(k),calls=int(calls[k]),inclusive_instructions=int(inc[k]))for k in sorted(range(profile.N),key=lambda k:inc[k],reverse=True)[:30]if inc[k]]
  io=[dict(direction='stash'if d==0 else'fetch',owner=owner,calls=int(g.dll.wp_io(d,owner,0)),bytes=int(g.dll.wp_io(d,owner,1)))for d in range(2)for owner in range(256)if g.dll.wp_io(d,owner,0)]
  stage_detail={}
  for k,n in enumerate(selfs):
   if not n or k<65536+64*4096:continue
   pc=0x5000+(k&4095);near=[(a,fn)for a,fn in symbols['type-stage']if 0x5000<=a<=pc];a,fn=max(near,default=(pc,'?'));stage_detail[f'{a:04X}:'+fn]=stage_detail.get(f'{a:04X}:'+fn,0)+int(n)
  events=[]
  for i in range(g.dll.wp_event_count()):
   at,key,id,slot,op,kind=[int(g.dll.wp_event(i,j))for j in range(6)];events.append(dict(at=at,previous_instruction=named(key),old=id,new=slot)if kind else dict(at=at,asset=next((n for n in names if f.assets[n][6]==id and f.assets[n][5]==slot),f'ID{id}'),id=id,slot=slot,op=op))
  return dict(overlay_and_window_events=events,exclusive_stage_labels=dict(sorted(stage_detail.items(),key=lambda x:-x[1])[:50]),exclusive_modules=modules,exclusive_named_regions=dict(sorted(functions.items(),key=lambda p:-p[1])[:45]),overlapping_module_inclusive={name:int(g.dll.wp_module(i))for name,i in ([(n,j+1)for j,n in enumerate(names)]+[('type-stage',65)])if g.dll.wp_module(i)},entry_counts=entries,crc_calls=crc,top_call_sites=top,DMA=io)
 records=[]
 try:
  sources=[('ordinary',ob.geos.native_text('Ordinary words here.\rSecond source row.\rLast.'),5,caps)for caps in (0,1,3)]
  styled=ob.geos.native_text('Ordinary **strong words** here.\rSecond source row.\rLast.')
  sources.append(('strong',styled,styled.index(ob.geos.native_text('strong'))+3,3))
  if only:sources=[x for x in sources if x[0]+'-'+str(x[3])==only]
  for dataset,initial,at,caps in sources:
   f.source(initial);f.typed(ob.geos.native_text('syntax '+{0:'plain',1:'markdown',3:'full'}[caps]));f.typed(ob.geos.native_text('mode hires'));f.typed(ob.geos.native_text('top'))
   for _ in range(at):f.key(0x1d)
   f.render();assert f.get('se_mode',1)==3 and f.get('se_render_caps',1)==caps and f.get('se_hot_caret')==at
   data=initial;caret=at
   actions=[(f'pair{i}-'+op,key)for i in range(pairs)for op,key in [('insert',ob.Q),('back',0x14)]]+[(f'caret{i}-'+op,key)for i in range(2)for op,key in [('right',0x1d),('left',0x9d)]]
   for tag,key in actions:
    if key==ob.Q:data=data[:caret]+bytes([key])+data[caret:];caret+=1
    elif key==0x14:data=data[:caret-1]+data[caret:];caret-=1
    else:caret+=1 if key==0x1d else -1
    before=g.audit_begin();g.dll.pb_arena_begin(True);loads=f.get('se_overlay_loads',2);calls=f.get('se_overlay_calls',2);start=f.total_instructions;catalog=f.catalog();revision=f.get('se_r_revision',4)
    gf=f.m.read(f.s['se_gf_state']+21);g.dll.wp_begin();f.key(key);after_input=f.total_instructions;canonical=f.canonical();f.render();first=f.total_instructions
    assert f.canonical()==canonical,'render changed canonical source/history/hot buffer'
    # Real public idle iterations, only until current requested work quiesces.
    ticks=0
    while ticks==0 or f.get('se_e_job',1)or f.get('se_e_redraw',1)or f.get('se_st_request',1)==1 or f.get('se_f_owner',1):
     f.tick();ticks+=1;assert ticks<4000,('idle never quiesced',f.debug())
    g.dll.wp_end();assert not g.dll.wp_depth_left(),('unresolved host JSR attribution',g.dll.wp_depth_left());used=int(g.dll.wp_count());assert used==f.total_instructions-start,(used,f.total_instructions-start)
    g.audit_end(before,tag);g.dll.pb_arena_begin(False)
    cost=collect();after=g.reu();_,bank=f.raw_cache();allowed=bytearray(before)
    for lo,hi in ((0,64),(0x200,0xEA88)):allowed[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
    assert after==allowed,(dataset,caps,tag,'REU outside authenticated source/GTF FE reservation')
    assert f.merged()==data and f.get('se_hot_caret')==caret and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
    bits,attrs,_=plain.expected(f,data,fonts,caps);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(dataset,caps,tag,'independent pixels')
    assert not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_draw_busy'))
    if caps==0:assert not any(v for k,v in cost['entry_counts'].items()if any(t in k for t in(':se_sm_',':se_si_',':se_sl_'))),(tag,'Plain parser work')
    rec=dict(dataset=dataset,caps=caps,tag=tag,total_instructions=used,input_instructions=after_input-start,first_publication_instructions=first-start,optional_idle_instructions=f.total_instructions-first,idle_ticks=ticks,loads=(f.get('se_overlay_loads',2)-loads)&65535,overlay_calls=(f.get('se_overlay_calls',2)-calls)&65535,shared_window_valid_before=gf,shared_window_valid_after=f.m.read(f.s['se_gf_state']+21),revision_before=revision,revision_after=f.get('se_r_revision',4),pixels_sha256=hashlib.sha256(bits+attrs).hexdigest(),**cost)
    records.append(rec);(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('WARM_INPUT',dataset,caps,tag,used,rec['loads'],sorted(cost['exclusive_modules'].items(),key=lambda x:-x[1])[:5],flush=True)
    if tag in('pair0-insert','pair4-back','caret1-left'):ob.geos.png(bits,attrs,out/(dataset+'-'+str(caps)+'-'+tag+'.png'))
   assert data==initial and caret==at
   # Real public Undo/Redo source witness, outside measured profile intervals.
   f.key(ob.Q);expected=data[:caret]+bytes([ob.Q])+data[caret:];f.render();assert f.merged()==expected
   f.key(0x1a);f.render();assert f.merged()==data
   f.key(0x19);f.render();assert f.merged()==expected
  result=dict(status='PASS',fixture=str(base),identity=g.identity,records=records,pairs=pairs,typed_DMA_intervals=g.exact_dma_intervals,scope='Real public input/render/service/idle CPU instruction attribution, not native cycles/IRQ/physicalkey latency. Original registered62 code unchanged. Independent pixels/source/history-render immutability, actual Undo/Redo source witness, shim/catalog and whole16MiB outside authenticated source/GTF FE reservation. Source fixture initialization/ROM transport and disclosed public CPU PC/SP call seams retained; no semantic/layout/proof seed.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:g.dll.wp_end();g.dll.fr_end();g.dll.pb_arena_begin(False);f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--pairs',type=int,default=5);p.add_argument('--only',choices=['ordinary-0','ordinary-1','ordinary-3','strong-3']);p.add_argument('--out',type=Path);a=p.parse_args();o=a.out or ROOT/'build/geos-warm-input-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',o,flush=True);run(o.resolve(),a.fixture.resolve(),a.pairs,a.only)
