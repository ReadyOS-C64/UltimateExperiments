"""Read-only precise first-publication/settled structural-edit attribution."""
from pathlib import Path
import ctypes as C,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[5];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_boundary as test
raw=test.raw;observer=raw.caret.profile.observer
def run(out,base):
 out.mkdir(parents=True);spec=importlib.util.spec_from_file_location('boundary_hotpath',ROOT/'src/cache/hotpath-profile-probe/runner.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner);saved=observer.runner;observer.runner=runner.build
 try:g=observer.Gate(out,base)
 finally:observer.runner=saved
 f=g.f;dll=g.dll;names=g.identity['names'];points,returns=raw.caret.profile.points(f)
 dll.hp_config(f.s['se_overlay_active'],f.s['se_overlay_frame'],f.s['se_e_draw_sequence'],(C.c_uint16*8)(*points),len(returns),(C.c_uint16*len(returns))(*returns),names.index('gtype')+1,names.index('code')+1)
 cases=[]
 try:
  for width in(60,80):
   data=observer.geos.native_text('Plain editable words.\r'+'Alpha words '*18+'\r'+'A'*(width-1)+'\rUntouched tail.\r')
   edge=data.index(b'\r',data.index(b'\r')+1)+1
   for tag,at,key in [('new-row',edge+5,observer.Q),('CR',5,13)]:
    f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);raw.caret.profile.drain(f);f.position(at);raw.caret.profile.drain(f);source=data;where=at
    for operation in(key,20):
     before=g.audit_begin();initial=f.total_instructions;loads=f.get('se_overlay_loads',2);dmas=f.get('se_reu_dma_calls',2);dma_bytes=f.get('se_reu_dma_bytes',3);dll.hp_begin(f.get('se_e_draw_sequence',2))
     try:f.key(operation);raw.caret.profile.drain(f)
     finally:dll.hp_end()
     total=f.total_instructions-initial;assert dll.hp_get(0,0)==total and not dll.hp_get(0,4)
     g.audit_end(before,tag);source=source[:where]+bytes((operation,))+source[where:]if operation!=20 else source[:where-1]+source[where:];where+=1 if operation!=20 else -1
     assert f.merged()==source and f.read(0xc600,1024)==f.shim
     (bits,attrs),_,_,_=observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(width,tag,operation,'full pixels')
     counts={('resident'if i==0 else names[i-1]if i<=len(names)else str(i)):int(dll.hp_get(1,i))for i in range(68)if dll.hp_get(1,i)}
     entries={n:dict(calls=int(dll.hp_get(3,i+1)),ops={str(j):int(dll.hp_op(i+1,j))for j in range(256)if dll.hp_op(i+1,j)})for i,n in enumerate(names)if dll.hp_get(3,i+1)}
     groups=[dict(slot=i//64,id=i%64,**{n:int(dll.hp_group(i,j))for j,n in enumerate(('calls','total','admission','payload_inclusive','payload_self'))})for i in range(128)if dll.hp_group(i,0)]
     item=dict(width=width,tag=tag,key=operation,first_publication=int(dll.hp_get(0,1)),settled=total,loads=(f.get('se_overlay_loads',2)-loads)&65535,DMA_calls=(f.get('se_reu_dma_calls',2)-dmas)&65535,DMA_bytes=(f.get('se_reu_dma_bytes',3)-dma_bytes)&0xffffff,CRC_instructions=int(dll.hp_get(0,2)),counts=counts,entries=entries,groups=groups,pixels=hashlib.sha256(bits+attrs).hexdigest());cases.append(item);print('PROFILE',width,tag,operation,item['first_publication'],total,flush=True)
  result=dict(status='PASS',fixture=str(base),cases=cases,scope='Actual public input; PC read-only observer pins first draw-sequence change and settled idle. CPU instruction counts, not native cycles/physical key latency.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
