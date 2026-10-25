"""Actual resident GEOS PAN routing: canonical pending data and public repaint.

No controller seam or leaf substitution. CPU screenshots do not prove VIC/IRQ
hardware behavior; the independent oracle uses source bytes and reference fonts.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,hashlib
import test_geos_inline_bridge as inline
semantic=inline.semantic;geos=inline.geos;ROOT=geos.ROOT

def run(out,previous=None,smoke=False):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 (out/'frozen-ready.json').write_text(json.dumps(identity,indent=2)+'\n')
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True)
 fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
 cases=[];frames=[];faults=[]
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def stable():return f.canonical(),f.catalog(),f.get('se_v_top'),f.get('se_l_preferred'),f.get('se_n_preferred_valid',1)
 def released():
  assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_e_job','se_e_error'])
  assert not f.m.read(0x912C) and not f.m.read(0x912D) #saved FS bytes are opaque once context-valid is0
  assert f.read(0xC600,1024)==f.shim
 def setup(text,caret=0,old=0,mode=1,pending=False):
  data=geos.native_text(text);f.source(data);f.command(99);f.position(caret)
  if pending:
   q=geos.native_text('Q');f.key(q[0]);data=data[:caret]+q+data[caret:];caret+=1
   assert f.get('se_hot_pending',1)
  f.put('se_l_mode',mode,1);f.put('se_l_pan',old);f.put('se_l_manual',0,1)
  f.put('se_l_preferred',0x123456);f.put('se_n_preferred_valid',2,1)
  return data,caret
 def metric(data,caret):
  model=inline.classify(data);lo=data.rfind(b'\r',0,caret)+1;hi=data.find(b'\r',lo)
  if hi<0:hi=len(data)
  def advance(p):return 8 if model.code[p] else fonts['bsw9-widths.bin'][geos.native(data[p])]+(model.styles[p]&1)+(model.styles[p]&2)
  return sum(advance(p) for p in range(lo,hi)),sum(advance(p) for p in range(lo,caret))
 def public_pan(data,caret,command,old,tag):
  before=stable();reu=whole();mode=f.get('se_l_mode',1);used=f.total_instructions
  width,_=metric(data,caret);wanted=min(max(0,old+(-20 if command==74 else 20)),max(0,width-320))
  f.put('se_e_error',0,1);r=f.call('se_editor_command',command)
  assert not r.p&1 and f.get('se_e_job',1)==12,('resident did not route directly to C23',f.debug())
  assert stable()==before and whole()==reu,'PAN entry flushed/mutated pending document'
  trace=[]
  while f.get('se_e_job',1):
   request,op=f.m.read(0x9135),f.m.read(0x9136);assert request in (20,23,24,26)
   r=f.call('se_editor_service');trace.append([request,op,r.a,r.p&1,f.get('se_e_job',1)])
   assert not r.p&1 and f.get('se_e_job',1) in (0,12),('PAN wrongly entered load/flush',trace[-1],f.debug())
   assert stable()==before,'PAN service changed source/history/caret/top/preferred'
   assert len(trace)<100000
  assert trace[-1][0]==23 and f.get('se_e_redraw',1)==1,'PAN A2 did not finish in redraw'
  assert f.get('se_l_pan')==wanted and f.get('se_l_mode',1)==f.get('se_l_manual',1)==1
  assert f.get('se_e_target')==caret and whole()==reu
  released();assert f.merged()==data
  cases.append(dict(tag=tag,command=command,old_mode=mode,old_pan=old,new_pan=wanted,pixel_width=width,pending=f.get('se_hot_pending',1),steps=len(trace),instructions=f.total_instructions-used,trace=trace))
  (out/'progress.json').write_text(json.dumps(dict(cases=cases,frames=frames,faults=faults),indent=2)+'\n')
 def frame(data,tag):
  canonical=f.canonical();catalog=f.catalog();before=whole();f.render();model=inline.classify(data)
  assert not any(model.code),'this oracle gate deliberately isolates proportional prose PAN'
  bits,attrs,rows=semantic.raster(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor') if f.get('se_sel_mark',1) else None,styles=model.styles,roles=model.roles,reverse=model.reverse,code=model.code,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
  matrix,colors,popup=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
  actual=f.read(0x6000,8000);attributes=f.read(0x4000,1000)
  for name,value in [('actual-bitmap',actual),('expected-bitmap',bits),('actual-attrs',attributes),('expected-attrs',attrs)]: (out/(tag+'-'+name+'.bin')).write_bytes(value)
  geos.png(actual,attributes,out/(tag+'-cpu.png'))
  assert actual==bits,(tag,'pixels',next((i,a,b) for i,(a,b) in enumerate(zip(actual,bits)) if a!=b))
  assert attributes==attrs,(tag,'attributes',next((i,a,b) for i,(a,b) in enumerate(zip(attributes,attrs)) if a!=b))
  cache,physical=f.cache();after=whole();start=physical*65536
  assert before[:start]==after[:start] and before[start+65536:]==after[start+65536:],'non-FE REU changed during page paint'
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data
  released();frames.append(dict(tag=tag,pan=f.get('se_l_pan'),manual=f.get('se_l_manual',1),rows=len(rows),bitmap_sha256=hashlib.sha256(actual).hexdigest(),attrs_sha256=hashlib.sha256(attributes).hexdigest()))
 try:
  data,caret=setup('W'*100+'\rnext row',3,0,0,True)
  public_pan(data,caret,75,0,'pending-wrap-to-nowrap')
  print('FIRST PUBLIC PAN PASS: pending source/history/preferred/full16MiB unchanged; job12->redraw, mode1/manual1/pan20',flush=True)
  if not smoke:
   frame(data,'pending-manual-hide')
   for text,at,old,mode,pending,command in [
    ('W'*100+'\r',0,20,1,False,75),('W'*100+'\r',0,40,1,False,74),
    ('W'*100+'\r',0,10,1,False,74),('W'*100+'\r',0,475,1,False,75),
    ('i'*200+'\r',0,0,1,False,75),('short\r',0,40,1,True,75),
    ('**'+('Wim '*35)+'**\r',40,20,0,True,75),('',0,20,0,False,74),
    ('W'*12000+'\r',6000,65520,1,True,75),('W'*12000+'\r',6000,95680,1,False,75)]:
    data,caret=setup(text,at,old,mode,pending);public_pan(data,caret,command,old,'pan-'+str(len(cases)))
    if len(data)<1000:frame(data,'pan-frame-'+str(len(frames)))
   # Public rendering detects a horizontally hidden caret and routes E47,
   # rather than treating canonical vertical membership as horizontal visibility.
   for caret,old,wanted in [(5,200,40),(60,0,161),(40,1,1),(9000,65500,71681)]:
    text='W'*(12000 if caret>100 else 100)+'\r'
    data,at=setup(text,caret,old,1,False)
    document=f.read(f.s['se_doc_roots'],512)+f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_doc_length'],3)
    history=f.read(f.s['se_h_current'],4)+f.read(f.s['se_h_saved'],4)
    f.render()
    assert f.get('se_l_pan')==wanted and f.get('se_l_manual',1)==0,(caret,old,wanted,f.get('se_l_pan'))
    assert f.get('se_hot_caret')==caret and f.merged()==data
    assert f.read(f.s['se_doc_roots'],512)+f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_doc_length'],3)==document
    assert f.read(f.s['se_h_current'],4)+f.read(f.s['se_h_saved'],4)==history
    released();cases.append(dict(tag='public-horizontal-reveal',caret=caret,old_pan=old,new_pan=wanted))
    if len(data)<1000:frame(data,'automatic-reveal-'+str(caret))
   # Manual pan may deliberately hide the caret. Ordinary local motion clears
   # manual override, so the next public paint reveals it again.
   data,caret=setup('W'*100+'\r',0,100,1,False)
   f.put('se_l_manual',1,1);frame(data,'manual-hidden-left')
   assert f.get('se_l_pan')==100 and f.merged()==data
   f.key(0x1D);assert f.get('se_hot_caret')==1 and f.get('se_l_manual',1)==0
   f.render();assert f.get('se_l_pan')==8 and f.merged()==data
   frame(data,'local-motion-reveals');cases.append(dict(tag='local-motion-clears-manual',new_pan=8))
   # Direct public E47 also takes the normal A0/reload path, not PAN's A2 path.
   data,caret=setup('W'*100+'\r',60,0,1,False)
   f.call('se_editor_reveal');f.settle();assert f.get('se_hot_caret')==60 and f.get('se_l_pan')==161
   assert f.merged()==data;released();frame(data,'explicit-E47');cases.append(dict(tag='explicit-E47',target=60,new_pan=161))
   # STOP reaches the real service queue while a shared source lease exists.
   data,caret=setup('**'+('Wim '*90)+'**\r',12,40,0,True)
   before=stable();reu=whole();assert not f.call('se_doc_read_acquire').p&1
   f.call('se_editor_command',75)
   for _ in range(10000):
    if f.m.read(0x912D):break
    assert f.get('se_e_job',1)==12;f.call('se_editor_service')
   else:raise AssertionError('PAN source lease not reached')
   assert f.get('se_doc_read_locks',1)==2
   f.queued(3);f.call('se_editor_service')
   assert not f.get('se_e_job',1) and not f.get('se_f_owner',1)
   assert f.get('se_doc_read_locks',1)==1 and stable()==before and whole()==reu
   assert f.get('se_l_pan')==40 and f.get('se_l_mode',1)==0 and f.get('se_l_manual',1)==0
   f.call('se_doc_read_release');released();faults.append('queued STOP cancels pending PAN without publication or foreign lease loss')
   # Exercise missing leaves through the actual public dispatcher, with a
   # pending gap still owned by the editor. No leaf/IO success is simulated.
   for missing in (23,20,24,26):
    data,caret=setup('**'+('Wim '*90)+'**\r',12,40,0,True)
    before=stable();reu=whole();idx=None
    if missing!=23:
     f.call('se_editor_command',75)
     for _ in range(20000):
      if f.m.read(0x9135)==missing:break
      assert not f.call('se_editor_service').p&1
      assert f.get('se_e_job',1)==12
     else:raise AssertionError(('missing requested worker',missing))
    idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==missing and f.m.read(f.s['image_slot']+i)==1)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+1,0)
    r=f.call('se_editor_command',75) if missing==23 else f.call('se_editor_service')
    assert r.p&1 and f.get('se_e_error',1)==0x17,(missing,r.a,r.p,f.debug())
    assert not f.get('se_e_job',1) and not f.get('se_f_owner',1) and not f.get('se_doc_read_locks',1)
    assert not f.m.read(0x912C) and not f.m.read(0x912D)
    f.m.write(f.s['se_overlay_ids']+idx,missing) #undo only the injected catalog fault before comparing
    assert stable()==before and whole()==reu
    assert f.get('se_l_pan')==40 and f.get('se_l_mode',1)==0 and f.get('se_l_manual',1)==0
    f.m.write(f.s['se_overlay_ids']+idx,missing);f.put('se_e_error',0,1)
    released();faults.append('missing C'+str(missing)+' reports17 and releases only owned PAN state')
  result=dict(status='passed',identity=identity,cases=cases,frames=frames,faults=faults,scope='Actual resident E74/75 command and job12 dispatcher; CPU-only independent prose pixel oracle')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',cases=len(cases),frames=len(frames),faults=len(faults),out=str(out)),indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args()
 out=ROOT/'build/geos-pan-dispatch'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 run(out,a.fixture,a.smoke)
