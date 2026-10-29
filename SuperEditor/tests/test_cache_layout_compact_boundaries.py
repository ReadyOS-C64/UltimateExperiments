"""Small independent COUNT-live reconstruction/capacity proof, not a product hook."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,sys
import test_cache_layout_compact as lane
from geos_packet import rows as decode_rows
from test_geos_nowrap_editor import nowrap_expected
ROOT=lane.ROOT;geos=lane.geos;semantic=lane.semantic

def run(out,base):
 out.mkdir(parents=True);print('RUN',out,flush=True);image=lane.build(out/'component',base)
 identity=json.loads((base/'freeze.json').read_text());geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=base;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,base,dll,True);results=[]
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def store(offset,data):
  for i in range(0,len(data),128):
   p=data[i:i+128];f.m.load(0x8000,p);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset+i,2);f.put('se_reu_c64',0x8000,2);f.put('se_reu_length',len(p),2);assert not f.call('se_reu_copy',0).p&1
  f.call('se_doc_invalidate')
 def step(op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=34,x=0);assert(f.m.read(0xDF07)|(f.m.read(0xDF08)<<8))<=128;return r,n
 def drain(op):
  r,n=step(op);count=1;total=n
  while not r.p&1 and r.a==1:r,n=step(18);count+=1;total+=n;assert count<10000
  assert not r.p&1 and r.a==0,(r.a,r.p,count);return count,total
 try:
  cases=[('empty',b'',None,None),('blank-CR',geos.native_text('\r\r'),None,None),('161-clip',geos.native_text('.'*200+'\rTail.'),None,1),('22-native',geos.native_text(':::basic\r'+''.join(str(i+10)+' PRINT 1\r'for i in range(40))+':::\r'),9,None),('cross-scatter-inline',geos.native_text(''.join('row%02d **Wim** @x@ body.\r'%i for i in range(25))),None,None)]
  for tag,data,top,pan in cases:
   f.source(data);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1;f.command(99)
   if top is not None:f.position(top);f.put('se_v_top',top)
   if pan is not None:f.command(77);f.put('se_l_pan',pan);f.put('se_l_manual',1,1)
   f.render();raw,physical=f.raw_cache();expected=decode_rows(raw);payload=lane.packet_payload(raw);canonical=f.canonical();shim=f.read(0xC600,1024);pixels=f.read(0x6000,8000)+f.read(0x4000,1000);locks=f.get('se_doc_read_locks',1)
   f.put('se_f_owner',4,1);f.m.load(lane.STATE,bytes(64));capture=drain(16)
   # Poison all842 bytes of each active primary packet. Restore must replace
   # every live byte while leaving all omitted tails/gaps exactly poisoned.
   for i in range(raw[1]):store(0x200+i*0x800,bytes([0xA7])*842)
   before=whole();f.m.load(lane.STATE,bytes(64));f.m.load(lane.STATE+26,raw[32:35]);restore=drain(17);after=whole();restored,_=f.raw_cache()
   assert decode_rows(restored)==expected and lane.packet_payload(restored)==payload,tag
   cursor=0
   for a,b in lane.live_primary(raw):
    a+=physical*65536;b+=physical*65536;assert before[cursor:a]==after[cursor:a],(tag,hex(cursor),hex(a));cursor=b
   assert before[cursor:]==after[cursor:],tag
   assert f.canonical()==canonical and f.merged()==data and f.read(0xC600,1024)==shim and f.get('se_doc_read_locks',1)==locks
   assert f.read(0x6000,8000)+f.read(0x4000,1000)==pixels,'restore does not paint'
   # C21 deliberately refuses its existing cached repaint in nowrap mode.
   # Exercise the real public C22 BEGIN/STEP packet consumer directly here;
   # main compact gate separately proves automatic C21 consumption in wrap.
   c20=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==20 and f.m.read(f.s['image_slot']+i)&1);f.m.write(f.s['se_overlay_ids']+c20,0)
   f.put('se_overlay_frame',2,1);r,n=f.fast_call(f.s['se_overlay_call'],a=22,x=1);assert not r.p&1 and r.a==0
   f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=22,x=1);paintsteps=1
   while not r.p&1 and r.a==1:
    f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=22,x=1);paintsteps+=1;assert paintsteps<10000
   assert not r.p&1 and r.a==0,(tag,'actualC22',r.a,r.p)
   f.m.write(f.s['se_overlay_ids']+c20,20);f.put('se_f_owner',0,1)
   fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};bits,attrs,*_=nowrap_expected(f,data,fonts)
   assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
   geos.png(bits,attrs,out/(tag+'.png'))
   result=dict(tag=tag,rows=raw[1],counts=[r['count']for r in expected],live_payload=len(payload),capture=dict(steps=capture[0],instructions=capture[1]),restore=dict(steps=restore[0],instructions=restore[1]),inactive_tails_remain_poison=True,actual_C22_missing_C20_consumer_pass=True)
   results.append(result);print('PASS',json.dumps(result),flush=True)
  assert any(161 in r['counts']for r in results) and any(r['rows']==22 for r in results) and any(0 in r['counts']for r in results)
  (out/'result.json').write_text(json.dumps(dict(status='passed',component_bytes=len(image)-36,cases=results,full_REU_guard_bytes=16777216,scope='COUNT-live-only; no source/pixel oracles changed; no lifecycle/product hook'),indent=2)+'\n')
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();run(ROOT/'build/cache-layout-compact-boundaries'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),a.fixture.resolve())
