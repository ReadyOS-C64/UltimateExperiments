"""Actual privately linked48-image root versus frozen production full renderer.

No canonical products/shared builds/native runs. The private resident's genuine
cold table imports48 images, and actual root performs TRY/CAPTURE/publication.
The reference machine uses unchanged47-image production full rendering. Direct
negative leaf calls are explicit admission tests, not the successful root route.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,ctypes as C,hashlib,importlib.util,json,shutil,sys
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'src/render/grid/caret-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'

def run(out,base,smoke=False):
 frozen=out/'fixture';shutil.copytree(base,frozen);identity=json.loads((frozen/'freeze.json').read_text());assert identity['names'][-1]=='grid' and len(identity['names'])==48
 budget=json.loads((base.parent/'tree/build/grid-caret/budget.json').read_text()) if (base.parent/'tree/build/grid-caret/budget.json').exists() else json.loads((base.parent/'budget.json').read_text()) if (base.parent/'budget.json').exists() else {'payload':3706}
 dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];f=fold.Fixture(out,frozen,dll,True)
 baseline=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture';oldidentity=json.loads((baseline/'freeze.json').read_text());grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=baseline;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=oldidentity['names'];g=fold.Fixture(out,baseline,dll,True);frames=[];faults=[];captures=[]
 def candidate(op):
  f.m.write(f.s['se_overlay_frame'],op);return f.fast_call(f.s['se_overlay_call'],a=33,x=1)
 def ready(x):
  x.render();x.finish_style()
 def capture(tag):
  import binascii
  bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));h=f.reu()[bank*65536+0x1500:bank*65536+0x1600]
  assert h[:4]==b'NC\1\xa5' and binascii.crc_hqx(h[:254],65535)==int.from_bytes(h[254:],'little'),(tag,'real root captured header')
  assert int.from_bytes(h[202:204],'little')==f.get('se_e_draw_sequence',2),(tag,'exactpublishedsequence')
  captures.append(dict(tag=tag,actual_root_publication=True));return 0
 def setup(raw,width,at=3,configure=None):
  for x in(f,g):
   x.source(raw);x.command(97 if width==60 else 98);x.position(at);ready(x)
   if configure:configure(x);ready(x)
  assert f.merged()==g.merged()
  if not configure:assert f.merged()==raw
  return capture('setup'+str(width))
 def check(tag,command=2,collapsed=False):
  for x in(f,g):x.command(command)
  canonical=f.canonical();before=f.reu();phase=f.read(0x8d00,1152);immutable=[(a,f.read(a,n)) for a,n in [(0x1000,0x3000),(0x4400,0xc00),(0xc600,1024)]];loads=f.get('se_overlay_loads',2)
  start=f.total_instructions;sequence=f.get('se_e_draw_sequence',2);r=f.render();n=f.total_instructions-start
  assert r.a==0 and not r.p&1 and f.get('se_e_draw_sequence',2)==(sequence+1)&65535,(tag,'actualrootpublication')
  assert f.m.read(0x89c0)==1,(tag,'actualTRYsuccess-not-fullCAPTUREfallback')
  start=g.total_instructions;g.render();g.finish_style();full=g.total_instructions-start;data=f.merged();expected=fold.projection.expected(f,data,[replace(t,flags=1) for t in fold.tree(data)] if collapsed else fold.tree(data),f.get('se_v_top')) if f.get('se_ef_valid',1) else grid.expected(f,data);(wanted,attrs)=expected[0]
  assert f.read(0x6000,8000)==wanted==g.read(0x6000,8000),(tag,'all64000pixels')
  assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(tag,'all1000attributes',[(i,a,b,c) for i,(a,b,c) in enumerate(zip(f.read(0x4000,1000),attrs,g.read(0x4000,1000))) if a!=b or a!=c][:30])
  assert all(f.read(a,len(b))==b for a,b in immutable),(tag,'resident/style-plan/font/shim readonly')
  assert f.canonical()==canonical and f.merged()==g.merged() and f.read(0x8d00,1152)==phase and f.read(0xc600,1024)==f.shim,(tag,'source/history/clip/phase/shim')
  for name,w in [('se_v_seen',1),('se_v_caret_row',1),('se_v_caret_col',1),('se_v_bottom',3)]:assert f.get(name,w)==g.get(name,w),(tag,'publishedcoordinates',name,f.get(name,w),g.get(name,w))
  bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));at=bank*65536;old=[int.from_bytes(before[at+0x1500+off:at+0x1500+off+1],'little')for off in (199,200)];newrow=f.get('se_v_caret_row',1);allowed=[(at+0x1500,at+0x1600)]
  if old[0]:allowed.append((at+old[1]*240,at+(old[1]+1)*240))
  if f.get('se_v_seen',1):allowed.append((at+newrow*240,at+(newrow+1)*240))
  now=f.reu();cursor=0
  for a,z in sorted(set(allowed)):
   if a<cursor:continue
   assert now[cursor:a]==before[cursor:a],(tag,'foreignREU',cursor,a);cursor=z
  assert now[cursor:]==before[cursor:],(tag,'REUtail')
  fold.geos.png(wanted,attrs,out/(tag+'.png'));item=dict(tag=tag,instructions=n,full_render_instructions=full,loads=(f.get('se_overlay_loads',2)-loads)&65535,caret=f.get('se_hot_caret'));frames.append(item);print('PASS',item,flush=True)
 def decline(tag,mutate,transport_error=False,op=1):
  mutate();canonical=f.canonical();before=f.reu();phase=f.read(0x8d00,1152);bits=f.read(0x6000,8000);attrs=f.read(0x4000,1000)
  r,n=candidate(op);assert (r.a==2 and not r.p&1) or (transport_error and r.a==0x18 and r.p&1),(tag,'expectedoptional-miss-or-explicit-transport-fault',r.a,r.p)
  assert f.canonical()==canonical and f.reu()==before and f.read(0x8d00,1152)==phase and f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.read(0xc600,1024)==f.shim,(tag,'failedTRYreadonly')
  faults.append(dict(tag=tag,instructions=n,result=r.a,carry=bool(r.p&1)));print('MISS',tag,n,flush=True)
 try:
  raw=grid.native_text('Alpha **bold** and *italic* words.\rSecond plain source row.\r:::basic\r10 PRINT "Hi"\r:::\rLast.')
  for width in (60,80):
   setup(raw,width);check(f'{width}-right');check(f'{width}-left',1)
   if smoke:break
  if not smoke:
   for width in (60,80):
    for tag,raw,at,op,configure in [
     ('crossCR',grid.native_text('First row\rSecond row'),9,2,None),
     ('crossSoft',b'X'*180, width-1,2,None),
     ('EOF',grid.native_text('End'),2,2,None),
     ('emptyEOF',b'',0,2,None),
     ('markForward',grid.native_text('Marked words\rSecond row'),3,2,lambda x:x.command(68)),
     ('markReverse',grid.native_text('Marked words\rSecond row'),3,1,lambda x:x.command(68)),
     ('markCrossCR',grid.native_text('First row\rSecond row'),9,2,lambda x:x.command(68)),
     ('pending',grid.native_text('Ordinary pending words'),3,0,lambda x:x.key(81)),
     ('nowrap',b'X'*180,25,2,lambda x:x.command(77)),
     ('manualHidden',b'X'*180,3,0,lambda x:(x.command(77),x.command(75))),
    ]:
     setup(raw,width,at,configure);check(f'{width}-{tag}',op)
     if tag=='pending':
      g.command(2);decline(f'{width}-actual-known-flush',lambda:f.command(2));ready(f);ready(g);capture(f'{width}-after-flush');check(f'{width}-after-flush')
   for width in (60,80):
    setup(fold.TINY,width,fold.TINY.index(13,6)-1,lambda x:x.command(115));check(f'{width}-fold-summary',collapsed=True)
   high=b'X\r'*32770+grid.native_text('High source boundary\rTail')
   setup(high,80,65545);check('80-high24bit')
   # Every refusal below starts from one current real full-render witness.
   setup(grid.native_text('Guarded row\rSecond row'),80)
   for name,width,value in [('se_f_owner',1,1),('se_f_owner',1,2),('se_f_owner',1,3),('se_f_owner',1,255),('se_e_ui',1,1),('se_e_job',1,7),('se_st_request',1,1),('se_r_revision',4,f.get('se_r_revision',4)+1),('se_l_pan',3,1),('se_v_top',3,1),('se_sel_anchor',3,4),('se_st_valid',1,0),('se_gc_width',1,60),('se_reu_retired',1,1),('se_reu_epoch',2,f.get('se_reu_epoch',2)+1),('se_gc_valid',1,254),('se_st_generation',2,f.get('se_st_generation',2)+1),('se_ef_projection_generation',2,f.get('se_ef_projection_generation',2)+1)]:
    old=f.read(f.s[name],width);workspace=f.read(0x8880,0x380)
    decline(name+'-'+str(value),lambda name=name,width=width,value=value:f.put(name,value,width),transport_error=name=='se_reu_epoch')
    if name=='se_f_owner':
     assert f.read(0x8880,0x380)==workspace,'foreignowner workspace opaque'
     decline('capture-'+name+'-'+str(value),lambda:None,op=0);assert f.read(0x8880,0x380)==workspace
    f.m.load(f.s[name],old)
   for handle_name in ('se_gc_handle','se_overlay_asset'):
    handle=f.get(handle_name,1);address=f.s['se_reu_logical_owner']+handle;old=f.m.read(address)
    decline(handle_name+'-foreign-owner',lambda address=address:f.m.write(address,0xA5),transport_error=handle_name=='se_overlay_asset');f.m.write(address,old)
   # Explicit checked-DMA derived-cache fault seams, never raw source mutation.
   def cache_byte(offset,value=None):
    f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x8880,2)
    if value is None:
     assert not f.call('se_reu_copy',1).p&1;return f.m.read(0x8880)
    f.m.write(0x8880,value);assert not f.call('se_reu_copy',0).p&1
   for tag,offset in [('header-CRC',0x1500+20),('old-row-CRC',3)]:
    old=cache_byte(offset);decline(tag,lambda offset=offset,old=old:cache_byte(offset,old^1));cache_byte(offset,old)
   fontindex=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==16 and f.m.read(f.s['image_slot']+i)&1==0)
   address=f.s['se_overlay_ids']+fontindex;old=f.m.read(address);decline('missing-native-leaf',lambda:f.m.write(address,0));f.m.write(address,old)
   check('80-after-refusals')
   setup(grid.native_text('First row\rSecond row'),80,9)
   for x in (f,g):x.command(2)
   old=cache_byte(240+3);decline('new-row-CRC',lambda:cache_byte(240+3,old^1));cache_byte(240+3,old);check('80-after-new-row-fault',0)
   # Real shared help popup invalidates the old narrow witness and remains a
   # readonly optional miss; closing/redrawing needs a new trusted CAPTURE.
   for x in (f,g):x.command(66);ready(x)
   decline('actual-help-popup',lambda:None)
   for x in (f,g):x.command(66);ready(x)
   capture('after-popup');check('80-after-popup')
  if not smoke:
   # Current40-column common case must retain resident layout admission and
   # zero overlay loads. This route never invokes the C33 capture/TRY seam.
   raw=grid.native_text('Source forty resident row\rSecond row')
   for x in(f,g):x.source(raw);x.command(96);x.position(3);ready(x)
   for command,tag in [(2,'40-right'),(1,'40-left')]:
    counts=[];changes=[]
    for x in(f,g):
     x.command(command);old=x.canonical();reu=x.reu();loads=x.get('se_overlay_loads',2);start=x.total_instructions;x.render();counts.append(x.total_instructions-start);changes.append((x.get('se_overlay_loads',2)-loads)&65535);assert x.canonical()==old and x.reu()==reu
    expected=grid.expected(f,raw)[0];assert (f.read(0x4000,1000),f.read(0xd800,1000))==expected==(g.read(0x4000,1000),g.read(0xd800,1000))
    assert changes==[0,0],(tag,'residentfastpredicate',changes)
    frames.append(dict(tag=tag,instructions=counts[0],full_render_instructions=counts[1],loads=0,caret=f.get('se_hot_caret')));print('PASS',frames[-1],flush=True)
  result=dict(status='passed',budget=budget,frames=frames,faults=faults,captures=captures,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=ROOT/'build/grid-caret-integration/20261025T163000/fixture');p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/grid-caret-root'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)
