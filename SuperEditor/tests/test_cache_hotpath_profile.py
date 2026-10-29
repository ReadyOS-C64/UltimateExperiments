"""Frozen packaged public-input costs through first publication and settled idle.

Read-only instruction instrumentation, CPU IEC/font fixture seams. No native
cycles/physical-key latency claim; no product replacements or shared label reads.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,json,shutil,zipfile
import test_cache_observer as observer
import test_plain_geos as plain
import test_grid_editor_vice as diverse
ROOT=observer.ROOT
BASE=ROOT/'build/cache-editor-product/20261026T052628862819Z/fixture'

def quiet(f):
 return not any(f.get(n,1)for n in('se_e_job','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks'))and f.get('se_st_request',1)!=1

def drain(f):
 for i in range(100000):
  if quiet(f):assert not f.get('se_e_error',1),f.debug();return i
  f.tick()
 raise AssertionError(('not quiescent',f.debug()))

def points(f):
 s=f.s;prg=f.read(0x1000,0xb600)
 def calls(n):
  a=s[n];needle=bytes((0x20,a&255,a>>8));return[0x1000+i+3 for i in range(len(prg)-2)if prg[i:i+3]==needle]
 returns=calls('jump_overlay');assert len(returns)==1
 result=s['call_result'];busy=s['se_overlay_busy'];suffix=bytes((0x8d,result&255,result>>8,0x68,0xaa,0xa9,0,0x9d,busy&255,busy>>8,0xad,result&255,result>>8,0x60))
 assert f.read(returns[0],len(suffix))==suffix
 return [s['se_overlay_call'],s['jump_overlay'],returns[0],returns[0]+len(suffix)-1,s['crc_stage'],0,0,0],calls('crc_stage')

def run(out,base,smoke=False):
 out.mkdir(parents=True)
 spec=importlib.util.spec_from_file_location('hotpath_runner',ROOT/'src/cache/hotpath-profile-probe/runner.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 saved=observer.runner;observer.runner=r.build
 try:g=observer.Gate(out,base)
 finally:observer.runner=saved
 f=g.f;dll=g.dll;names=g.identity['names'];assets={n:hashlib.sha256(v).hexdigest()for n,v in f.assets.items()};resident=f.read(0x1000,0x2f00)
 ps,cr=points(f);assert len(cr)<=8
 dll.hp_config(f.s['se_overlay_active'],f.s['se_overlay_frame'],f.s['se_e_draw_sequence'],(C.c_uint16*8)(*ps),len(cr),(C.c_uint16*len(cr))(*cr),names.index('gtype')+1,names.index('code')+1)
 fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)};data=diverse.fixture();cases=[]
 def check_pixels(source,mode,caps,tag):
  if mode==3:bits,attrs,_=plain.expected(f,source,fonts,caps)
  else:(bits,attrs),_,_,_=observer.geos.grid.expected(f,source)
  at=0xd800 if mode==0 else 0x4000
  assert f.read(0x4000 if mode==0 else 0x6000,1000 if mode==0 else 8000)==bits,(tag,'independent pixels')
  assert f.read(at,1000)==attrs,(tag,'independent attrs')
  if mode:
   observer.geos.png(bits,attrs,out/(tag+'.png'))
  return hashlib.sha256(bits+attrs).hexdigest()
 try:
  for mode in ([2]if smoke else(0,2,3)):
   for preset,caps in [('plain',0),('full',3)]:
    for action in ('right','down','up','insert'):
     f.source(data,physical=256);f.typed(observer.geos.native_text('syntax '+preset));f.command((96,97,98,99)[mode]);drain(f)
     # Public GOTO + RIGHT prepares an interior prose caret after the heading.
     f.typed(observer.geos.native_text('goto 2'))
     for _ in range(5):f.key(0x1d)
     drain(f);assert f.get('se_hot_caret')==data.index(b'\r')+6
     if action=='right':f.key(0x1d);drain(f) #prime the admitted hot caret path
     if action=='up':f.key(0x11);drain(f)
     at=f.get('se_hot_caret');before=g.audit_begin();stable=g.stable();catalog=f.catalog();initial=f.total_instructions;loads=f.get('se_overlay_loads',2);dmas=f.get('se_reu_dma_calls',2);dma_bytes=f.get('se_reu_dma_bytes',3);key={'right':0x1d,'down':0x11,'up':0x91,'insert':observer.Q}[action]
     allow_baseline=mode==3 and caps!=0 and action=='insert';dll.pb_arena_begin(allow_baseline)
     dll.hp_begin(f.get('se_e_draw_sequence',2))
     try:f.key(key);ticks=drain(f)
     finally:dll.hp_end()
     g.audit_end(before,f'{mode}-{preset}-{action}')
     baseline_writes=int(dll.pb_arena_get());dll.pb_arena_begin(False);assert baseline_writes==(2 if allow_baseline else 0)
     used=f.total_instructions-initial;assert dll.hp_get(0,0)==used and dll.hp_get(0,4)==0
     source=data[:at]+bytes((key,))+data[at:]if action=='insert'else data
     assert f.merged()==source and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
     if action!='insert':assert g.stable()==stable
     tag=f'm{mode}-{preset}-{action}';pixels=check_pixels(source,mode,caps,tag)
     self_counts={('resident'if i==0 else names[i-1]if i<=len(names)else'stage32'if i==65 else'stage31'if i==66 else str(i)):int(dll.hp_get(1,i))for i in range(68)if dll.hp_get(1,i)}
     assert sum(self_counts.values())==used
     entries={n:dict(calls=int(dll.hp_get(3,i+1)),ops={str(j):int(dll.hp_op(i+1,j))for j in range(256)if dll.hp_op(i+1,j)})for i,n in enumerate(names)if dll.hp_get(3,i+1)}
     groups=[]
     for index in range(128):
      if dll.hp_group(index,0):groups.append(dict(slot=index//64,id=index%64,**{k:int(dll.hp_group(index,j))for j,k in enumerate(('calls','total','admission','payload_inclusive','payload_self'))}))
     if caps==0:assert not set(entries)&{'styler','lexical','geossema','geoslex','geosinln','sema','inln','page','line'}
     item=dict(tag=tag,mode=mode,caps=caps,action=action,first_publication_instructions=int(dll.hp_get(0,1)),settled_instructions=used,idle_ticks=ticks,loads=(f.get('se_overlay_loads',2)-loads)&65535,DMA_calls=(f.get('se_reu_dma_calls',2)-dmas)&65535,DMA_bytes=(f.get('se_reu_dma_bytes',3)-dma_bytes)&0xffffff,overlay_CRC_instructions=int(dll.hp_get(0,2)),overlay_CRC_calls=int(dll.hp_get(0,3)),self_instructions=self_counts,entries=entries,overlay_intervals=groups,pixels_sha256=pixels,caret=f.get('se_hot_caret'),top=f.get('se_v_top'))
     cases.append(item);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS',tag,used,'first',item['first_publication_instructions'],'loads',item['loads'],'topself',sorted(self_counts.items(),key=lambda a:-a[1])[:5],flush=True)
     if action=='insert':f.command(16);drain(f);assert f.merged()==data;check_pixels(data,mode,caps,tag+'-undo')
  assert assets=={n:hashlib.sha256(v).hexdigest()for n,v in f.assets.items()}and f.read(0x1000,0x2f00)==resident
  result=dict(status='PASS',identity=g.identity,cases=cases,source=data.hex(),scope=__doc__,CPU_clock='Instruction counts only; no PAL/NTSC or physical-key latency inference.',admission_scope='Overlay-call entry to jump_overlay; interval cleanup excluded. Module self includes onlyPCinside module, resident includesloader/guard/DMA/root; stage32/31 separately ownedPC5000 ranges.',runtime_points=ps,crc_returns=cr)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
   for folder in('tests','tools'):
    for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
   p=ROOT/'src/cache/hotpath-profile-probe/runner.py';z.write(p,p.relative_to(ROOT))
  return result
 finally:dll.pb_arena_begin(False);f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/cache-hotpath-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.smoke)
