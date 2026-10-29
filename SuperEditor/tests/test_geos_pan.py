"""Actual private C23 pixel PAN through unchanged real C24/C20/C26 leaves."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,hashlib
import test_geos_navigation as nav
import test_geos_inline_bridge as inline
geos=nav.geos;ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-inline-bridge/20261025T033706659879Z/fixture'

def run(out,previous,smoke=False):
 frozen,identity=geos.freeze(out,previous);image,labels=nav.build(out/'leaf',frozen)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);f.assets['geosnav']=image
 widths=(frozen/'fonts/bsw9-widths.bin').read_bytes();cases=[];faults=[];requestlog=[];normal=[]
 def reu():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def invoke(id_,op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=id_,x=1);requestlog.append((id_,op,r.a,r.p&1));return r,n
 def setup(data,caret,pan=0,mode=1,pending=False):
  f.source(data);f.command(99);f.position(caret)
  if pending:
   byte=geos.native_text('Q');f.key(byte[0]);data=data[:caret]+byte+data[caret:];caret+=1;assert f.get('se_hot_pending',1)
  f.put('se_l_pan',pan);f.put('se_l_mode',mode,1);f.put('se_l_manual',0,1);f.put('se_l_preferred',0x123456);f.put('se_n_preferred_valid',2,1)
  return data,caret
 def width(data,caret):
  lo=data.rfind(b'\r',0,caret)+1;hi=data.find(b'\r',lo);hi=len(data) if hi<0 else hi;model=inline.classify(data)
  return sum(8 if model.code[p] else widths[geos.native(data[p])]+(model.styles[p]&1)+(model.styles[p]&2) for p in range(lo,hi))
 def snapshot():return f.canonical(),reu(),f.catalog(),f.get('se_v_top'),f.get('se_l_preferred'),f.get('se_n_preferred_valid',1)
 def begin(command):f.put('se_e_command',command,1);return invoke(23,0)[0]
 def pump(r,callback=None):
  steps=0;maxlease=0
  while not r.p&1 and r.a==1:
   requested,op=f.m.read(0x9135),f.m.read(0x9136);assert requested in (20,23,24,26),(requested,op)
   old=f.get('se_doc_read_locks',1);maxlease=max(maxlease,old)
   if callback and callback(requested,op,steps):return r,steps,maxlease
   r,n=invoke(requested,op);steps+=1
   if not r.p&1 and r.a==0 and requested!=23:
    f.m.write(0x9135,23);f.m.write(0x9136,1);r.a=1 #host resident-dispatch seam only
   assert steps<1000000,'nonconvergence'
  return r,steps,maxlease
 def pan(data,caret,command,old=0,mode=1,pending=False,load=True):
  if load:data,caret=setup(data,caret,old,mode,pending)
  else:
   assert f.get('se_hot_caret')==caret;f.put('se_l_pan',old);f.put('se_l_mode',mode,1)
  before=snapshot();logical=width(data,caret);maximum=max(0,logical-320);wanted=min(max(0,old+(-20 if command==74 else 20)),maximum)
  r=begin(command);assert not r.p&1 and r.a==1
  r,steps,peak=pump(r);assert not r.p&1 and r.a==2,('PAN completion',r.a,r.p,f.read(0x9134,68).hex())
  assert f.get('se_l_pan')==wanted,(logical,old,command,wanted,f.get('se_l_pan'))
  assert f.get('se_l_mode',1)==f.get('se_l_manual',1)==1 and f.get('se_e_target')==caret
  assert snapshot()==before,'view-only PAN changed canonical/source/REU/catalog/top/preferred'
  assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks')) and not f.m.read(0x9048) and not f.m.read(0x912D) and f.read(0xC600,1024)==f.shim
  cases.append(dict(length=len(data),caret=caret,command=command,old=old,mode=mode,pending=pending,logical_width=logical,max_pan=maximum,new=wanted,steps=steps,peak_leases=peak))
  (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');return data,caret
 try:
  data=geos.native_text('W'*60+'\r');pan(data,0,75,mode=0)
  if not smoke:
   for text,caret in [('i'*200+'\r',25),('W'*100+'\r',80),('**'+('Wim '*30)+'**\r',40),('before\rshort\r'+'W'*80,10),(':::asm\nlda #$12 ; '+('x'*100)+'\n:::\n',20),('',0),('\r',0),('a\r',1)]:
    data=geos.native_text(text)
    for command,old,mode in [(75,0,1),(75,20,1),(75,40,1),(74,40,1),(74,10,1),(75,0xFFFFFE,1),(75,0,0)]:pan(data,caret,command,old,mode)
   data=geos.native_text('**'+('Wim '*30)+'**\r');pan(data,40,75,40,0,True)
   # Logical pixel width, not byte count, crosses65535 and retains all24 bits.
   data=geos.native_text('W'*12000+'\r');logical=width(data,6000);assert logical>65535
   for command,old in [(75,65520),(75,logical-325),(75,logical-320),(74,logical-320),(74,65540)]:pan(data,6000,command,old)
   # E47 completes ordinary navigation with A0 but also reveals horizontal
   # logical pixel origins; its manual/preferred state must remain unchanged.
   for text,caret,target,old,mode,manual,pending in [
    ('W'*100+'\r',5,40,0,1,0,False),('W'*100+'\r',5,40,1,1,0,False),
    ('W'*100+'\r',5,40,2,1,1,False),('W'*100+'\r',5,1,100,1,1,False),
    ('W'*100+'\r',5,1,0xFFFFFE,1,0,False),('W'*100+'\r',5,40,80,0,0,False),
    ('**'+('Wim '*50)+'**\r',40,80,20,1,0,True),
    ('W'*12000+'\r',5,9000,65500,1,0,False),
    ('W'*12000+'\r',5,9000,73000,1,1,False),
    ('W'*12000+'\r',5,9000,71800,1,0,False)]:
    data,caret=setup(geos.native_text(text),caret,old,mode,pending);f.put('se_l_manual',manual,1);f.put('se_e_target',target)
    model=inline.classify(data);lo=data.rfind(b'\r',0,target)+1;x=sum(8 if model.code[p] else widths[geos.native(data[p])]+(model.styles[p]&1)+(model.styles[p]&2) for p in range(lo,target))
    wanted=old if not mode else x if x<old else x-319 if x-old>=320 else old
    before=snapshot();r=begin(47);assert not r.p&1 and r.a==1;r,steps,peak=pump(r)
    assert not r.p&1 and r.a==0 and f.get('se_e_target')==target
    assert f.get('se_l_pan')==wanted and f.get('se_l_manual',1)==manual and f.get('se_l_mode',1)==mode,(x,old,wanted,f.get('se_l_pan'))
    assert snapshot()==before,'E47 changed source/caret/preferred/top/REU'
    cases.append(dict(kind='reveal',command=47,target=target,logical_caret_x=x,old=old,new=wanted,mode=mode,manual=manual,pending=pending,steps=steps))
   # Existing normal wrapped navigation remains identical to its independent
   # row/source oracle for cached and cold UP/DOWN/PAGE/E47 paths.
   data=geos.native_text('Wim wide word\r\ri short\r'+('Mixed word '*30)+'\r'+('tail\r'*28))
   for command,caret in [(37,5),(36,17),(39,5),(38,17),(47,17)]:
    for cached in [True,False]:
     data,caret=setup(data,caret,0,0);f.put('se_l_preferred',37);f.put('se_n_preferred_valid',2,1);f.render()
     top=f.get('se_v_top');wanted=nav.oracle(data,widths,caret,top,command,37)
     if not cached:f.put('se_gc_width',0,1)
     f.put('se_e_target',caret);before=f.canonical(),reu(),f.catalog();r=begin(command);r,steps,_=pump(r)
     assert not r.p&1 and r.a==0 and (f.get('se_e_target'),f.get('se_v_top'))==wanted[:2],(command,cached,wanted,f.get('se_e_target'),f.get('se_v_top'))
     assert (f.canonical(),reu(),f.catalog())==before and f.get('se_l_preferred')==37 and f.get('se_n_preferred_valid',1)==2
     normal.append(dict(command=command,cached=cached,steps=steps,target=wanted[0],top=wanted[1]))
   data=geos.native_text('before\r**'+('Wim '*90)+'**\rafter');data,caret=setup(data,12,40,0,True)
   before=snapshot();assert not f.call('se_doc_read_acquire').p&1;f.put('se_e_command',75,1);r=f.call('se_geos_navigate');assert not r.p&1
   for _ in range(10000):
    if f.m.read(0x912D):break
    assert not f.call('se_editor_service').p&1
   else:raise AssertionError('PAN source lease not reached')
   assert f.get('se_doc_read_locks',1)==2
   f.queued(3);f.call('se_editor_service');assert not f.get('se_e_job',1) and not f.get('se_f_owner',1)
   assert f.get('se_doc_read_locks',1)==1 and f.get('se_l_pan')==40 and f.get('se_l_mode',1)==0 and snapshot()==before
   assert not f.call('se_doc_read_release').p&1;faults.append('actual queued STOP preserves foreign lease and does not publish partial PAN')
   for fault in ['revision','pan','mode','caret','missing20','missing24','missing26','missing23']:
    data,caret=setup(geos.native_text('**'+('Wim '*90)+'**\r'),40,20,0,True);before=f.canonical();r=begin(75);assert not r.p&1
    idx=None;id_=None
    if fault.startswith('missing'):
     id_=int(fault[7:]);slot=1
     # Let normal scheduling reach the desired missing leaf before admission.
     r,_,_=pump(r,lambda id2,op,n:id2==id_)
     idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)==slot)
     f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0)
    elif fault=='revision':f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
    elif fault=='pan':f.put('se_l_pan',21)
    elif fault=='mode':f.put('se_l_mode',1,1)
    elif fault=='caret':f.put('se_hot_caret',caret+1)
    r,_,_=pump(r);assert r.p&1 and r.a==(0x17 if idx is not None else 0x74),(fault,r.a)
    f.call('se_geos_cancel');assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks')) and not f.m.read(0x9048) and not f.m.read(0x912D)
    assert f.get('se_l_manual',1)==0 and f.get('se_l_pan')==(21 if fault=='pan' else 20) and f.get('se_l_mode',1)==(1 if fault=='mode' else 0)
    if fault!='caret':assert f.canonical()==before
    if idx is not None:f.m.write(f.s['se_overlay_ids']+idx,id_)
    faults.append(fault+' fails without PAN publication/owned lease')
  result=dict(status='passed',identity=identity,payload_bytes=len(image)-36,new_BSS=0,new_ZP=0,cases=cases,normal_navigation=normal,faults=faults,scope='Actual private C23 pixel PAN through real C24/C20/C26 and resident cancel; parent routing/rendering/native remain separate')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',cases=len(cases),faults=len(faults),payload_bytes=len(image)-36,out=str(out)),indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-pan'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture,a.smoke)
