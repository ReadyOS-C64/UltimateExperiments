"""Actual committed-window replay A/B: forced repaint after real W_LOAD.

No source/cache/lease result is seeded. Small251 and sparse66012 sources expose
both the additional small-case overhead and saved full-prefix block parsing.
CPU instructions only; no native cycle/physical-key latency inference.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,re,shutil
import test_cache_observer as observer
import test_plain_geos as plain
ROOT=observer.ROOT
OLD=ROOT/'build/cache-editor-product/20261026T021924007962Z/fixture'
NEW=ROOT/'build/cache-editor-product/20261026T023640840756Z/fixture'

def run(out,old,new):
 result=[]
 for variant,base in [('old',old),('committed',new)]:
  directory=out/variant;directory.mkdir();g=observer.Gate(directory,base);f=g.f
  try:
   fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
   stem=ROOT/'build/overlays/geossema';assert stem.with_suffix('.bin').read_bytes()==f.assets['geossema'][36:],'C24 labels do not match frozen source';shutil.copy2(stem.with_suffix('.lbl'),directory/'geossema.lbl');syms={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',stem.with_suffix('.lbl').read_text())}
   inline=ROOT/'build/overlays/geosinln';assert inline.with_suffix('.bin').read_bytes()==f.assets['geosinln'][36:],'C26 labels do not match frozen source';shutil.copy2(inline.with_suffix('.lbl'),directory/'geosinln.lbl');ils={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',inline.with_suffix('.lbl').read_text())}
   targets=[('C35',0xB010,'inln'),('C37',0xB010,'page'),('C24',0xB010,'geossema'),('C24feed',syms['se_sm_feed'],'geossema'),('C34',0xB010,'sema'),('C26',0xB010,'geosinln'),('C26init',ils['se_si_init'],'geosinln'),('C26feed',ils['se_si_feed'],'geosinln')]
   g.dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*(x[1]for x in targets)),(C.c_uint8*len(targets))(*([2]*len(targets))),(C.c_uint8*len(targets))(*(g.identity['names'].index(x[2])+1 for x in targets)),(C.c_uint8*(16*len(targets)))())
   for tag,data,position in [('251',plain.SOURCE,1),('66012',b'A'*66000+observer.geos.native_text('\r# Far\rTail.'),65999)]:
    f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render()
    assert f.get('se_bc_flags',1)&15==1 and f.get('se_bc_count',1)==0
    f.position(position);assert f.get('se_hot_caret')==position and not f.get('se_hot_pending',1)
    top=f.get('se_v_top');before=g.reu();stable=g.stable();trace=[];call=f.call;by_job={}
    def tracked(name,a=0):
     if name=='se_editor_service'and f.get('se_e_job',1)==11:
      req,op=f.read(0x9135,2)
      if req in (35,37):trace.append([req,op])
     job=f.get('se_e_job',1)
     before_counts=[int(g.dll.pb_get(i))for i in range(len(targets))]
     r=call(name,a)
     delta=[int(g.dll.pb_get(i))-v for i,v in enumerate(before_counts)]
     if any(delta):
      bucket=by_job.setdefault(str(job),{t[0]:0 for t in targets})
      for t,v in zip(targets,delta):bucket[t[0]]+=v
     return r
    f.call=tracked;start=f.total_instructions;g.dll.pb_begin()
    try:
     f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);f.render()
    finally:g.dll.pb_end();f.call=call
    used=f.total_instructions-start;counts={n:int(g.dll.pb_get(i))for i,(n,_,_)in enumerate(targets)}
    bits,attrs,rows=plain.expected(f,data,fonts,1)
    assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,variant,'independent pixels')
    assert f.merged()==data and g.stable()==stable and f.read(0xC600,1024)==f.shim
    assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
    assert f.get('se_bc_count',1)==0 and f.get('se_bc_flags',1)&15==1
    _,bank=f.raw_cache();after=g.reu();wanted=bytearray(before);spans=[(0,64),(0x600,0x680),(0xB200,0xD8B2),(0xE568,0xEA88),(0xFC00,0xFDA0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
    for lo,hi in spans:wanted[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
    assert after==wanted,(tag,variant,'whole16MiB outside precise FE spans')
    assert counts['C34']==0
    if variant=='committed':assert by_job.get('11',{}).get('C24feed',0)==0 and[37,3]in trace and[35,1]in trace
    else:assert counts['C24feed']>0 and[37,3]not in trace
    observer.geos.png(bits,attrs,directory/(tag+'.png'));item=dict(variant=variant,tag=tag,source_bytes=len(data),W_LOAD=position,viewport_top_before=top,viewport_top=f.get('se_v_top'),instructions=used,counters=counts,counters_by_root_job=by_job,route_counts={str(k):trace.count(list(k))for k in sorted(set(map(tuple,trace)))},bitmap_sha256=hashlib.sha256(bits).hexdigest(),attrs_sha256=hashlib.sha256(attrs).hexdigest(),source_sha256=hashlib.sha256(data).hexdigest());result.append(item);(out/'progress.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',item,flush=True)
  finally:f.close()
 for tag in ('251','66012'):
  pair=[i for i in result if i['tag']==tag];assert pair[0]['bitmap_sha256']==pair[1]['bitmap_sha256']and pair[0]['attrs_sha256']==pair[1]['attrs_sha256']and pair[0]['viewport_top']==pair[1]['viewport_top']
 summary=dict(status='PASS',cases=result,scope=__doc__,guard_scope='Actual public W_LOAD and renderer; independent bitmap8000/attrs1000; source/history/clipboard/shim; all16MiB outside precisely listed derived FE spans unchanged, typed53 arena immutable. Actual public caret-reveal included when root changes viewport; no host viewport/map seeding. Initial baseline cost excluded and remains separate.');(out/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
def faults(out,base):
 directory=out/'boundary-faults';directory.mkdir();g=observer.Gate(directory,base);f=g.f;cases=[];data=plain.SOURCE
 fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
 def guard_pixels(source,tag):
  bits,attrs,_=plain.expected(f,source,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,tag;observer.geos.png(bits,attrs,directory/(tag+'.png'))
 try:
  for action in ('missing-C37','queued-STOP','queued-Q'):
   f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render();f.position(1)
   f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);assert not f.call('se_editor_render').p&1
   for step in range(10000):
    if f.get('se_e_job',1)==11 and f.read(0x9135,2)==bytes((37,3)):break
    assert f.get('se_e_job',1)==11,('op3 not reached',f.debug());f.call('se_editor_service')
   else:raise AssertionError('op3 boundary absent')
   assert f.get('se_bc_flags',1)&8 and f.get('se_doc_read_locks',1)==1
   canonical=f.canonical();stable=g.stable();before=g.reu();bitmap=f.read(0x6000,8000)+f.read(0x4000,1000);idx=None;tail=f.get('se_input_tail',1)
   if action=='missing-C37':
    idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==37 and f.m.read(f.s['image_slot']+i)&1==1)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+1,0)
   else:f.queued(3 if action=='queued-STOP'else observer.Q)
   f.call('se_editor_service')
   assert f.get('se_e_error',1)==(0x17 if idx is not None else 0)
   assert not any(f.get(n,1)for n in ('se_f_owner','se_doc_read_locks','se_e_job','se_e_draw_busy'))and not f.get('se_bc_flags',1)&8
   assert f.canonical()==canonical and g.stable()==stable and g.reu()==before and f.merged()==data and f.read(0xC600,1024)==f.shim
   assert f.read(0x6000,8000)+f.read(0x4000,1000)==bitmap
   if idx is not None:
    f.m.write(f.s['se_overlay_ids']+idx,37);f.key(0x8B);f.key(0x8B);source=data
   else:
    assert f.get('se_input_tail',1)==tail and f.get('se_input_head',1)!=(tail&63),'queued key consumed by optional-job preemption'
    f.put('se_status',1,1);f.tick();f.settle();source=data[:1]+bytes([observer.Q])+data[1:]if action=='queued-Q'else data
    assert f.get('se_input_tail',1)==f.get('se_input_head',1)and f.merged()==source
   f.render();guard_pixels(source,action+'-recovered');assert not any(f.get(n,1)for n in ('se_f_owner','se_doc_read_locks','se_e_job','se_e_error'))and f.read(0xC600,1024)==f.shim
   assert g.stable()==stable
   _,bank=f.raw_cache();after=g.reu();wanted=bytearray(before);spans=[(0,64),(0x600,0x680),(0xB200,0xD8B2),(0xE568,0xEA88),(0xFC00,0xFDA0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
   for lo,hi in spans:wanted[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
   assert after==wanted,(action,'entire recovery16MiB outside preciseFE spans')
   cases.append(dict(action=action,steps_to_boundary=step,held_reader=1,prepaint_reu_unchanged=True,recovered_source_sha256=hashlib.sha256(source).hexdigest()));print('FAULT PASS',cases[-1],flush=True)
  (directory/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases,scope='Actual root job11 C35→C37op3 boundary; deliberate catalog-ID loss and queued realinput-ring keys. Preemption releases reader without consuming key; next realidle processes retained input. Entire16MiB and physical bitmap unchanged through cancellation.'),indent=2)+'\n')
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--faults-only',action='store_true');p.add_argument('--old',type=Path,default=OLD);p.add_argument('--new',type=Path,default=NEW);a=p.parse_args();out=ROOT/'build/cache-navigation-cost'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);faults(out,a.new)if a.faults_only else run(out,a.old,a.new)
