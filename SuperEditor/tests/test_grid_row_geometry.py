"""Private R24 vertical transport proof; no editor geometry publication claim.

Real checked provider/DMA, bounded body-only derived addresses, ephemeral FE
scratch, exact independent overlapping-copy model, whole RAM and 16MiB guards.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,random,re,sys
import test_cache_hotpath_profile as profile
ROOT=profile.ROOT;D=ROOT/'src/render/grid/probes/row-geometry';G=0x8d80

def run(out,builddir=None):
 out.mkdir(parents=True)
 if builddir is None:
  spec=importlib.util.spec_from_file_location('geometry_r24',D/'r24-budget.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);base,budget=builder.build(out/'pair')
 else:
  base=builddir/'fixture';budget=json.loads((builddir/'result.json').read_text())
 work=out/'cpu';work.mkdir();g=profile.observer.Gate(work,base);f=g.f;cases=[];faults=[]
 image=(base/'build/overlays/geosfold.seo').read_bytes();payload=image[36:]
 def invoke(op,owner=4):
  f.put('se_f_owner',owner,1);f.put('se_overlay_frame',op,1);before=f.read(0,65536);canonical=f.canonical();locks=f.get('se_doc_read_locks',1);r,used=f.fast_call(f.s['se_overlay_call'],a=24,x=0);after=f.read(0,65536)
  want=bytearray(before)
  fields=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2)]
  allowed=[(f.s[n],f.s[n]+w)for n,w in fields]+[(0x100,0x200),(f.s['se_reu_c64'],f.s['dma_physical']+1),(0xdf00,0xdf0b)]
  idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==24 and f.m.read(f.s['image_slot']+i)&1==0);allowed +=[(f.s['image_slot']+idx,f.s['image_slot']+idx+1)]
  h=f.s['se_overlay_header'];allowed +=[(h+8,h+10),(h+12,h+14),(0xa000,0xa000+len(payload)),(0x5000,0x5000+len(payload))]
  if owner==4:
   allowed +=[(G+4,G+25),(f.s['se_gc_valid'],f.s['se_gc_valid']+3)]
  if not r.p&1 and op==4:
   first=before[G+2];count=before[G+3];direction=1 if before[G+1]==1 else -1
   for at,size in ((0x6280,320),(0x4050,40)):
    lo=at+(first+direction)*size;hi=lo+count*size;want[lo:hi]=before[at+first*size:at+(first+count)*size]
  for lo,hi in allowed:want[lo:hi]=after[lo:hi]
  assert after==want,('wholeRAM/body/attrs/shim/CF/FS/GLneighbor',op,owner,r.a,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
  assert f.canonical()==canonical and f.get('se_doc_read_locks',1)==locks and f.read(0xc600,1024)==f.shim
  return r,used,before,after
 def plan(first,count,direction):f.m.load(G,bytes([1,direction&255,first,count])+bytes([0xa7])*21)
 try:
  data=profile.observer.geos.native_text('Plain geometry source.\rUntouched tail.\r');f.source(data,physical=256);f.typed(profile.observer.geos.native_text('syntax plain'));f.command(98);profile.drain(f)
  raw,bank=f.raw_cache();handle=f.get('se_gc_handle',1);assert bank and handle
  # Explicit component fixture seam: borrow the sparse-index phase only after
  # retiring its retained authority, exactly as the real C33 long_try does.
  # This is not evidence that a caller may enter merely because owner==4.
  for key in ('se_i_ready','se_i_count','se_n_cache_count'):f.put(key,0,1)
  plan(0,1,1);r,*_=invoke(3);assert not r.p&1 and r.a==0
  # A nontrivial complete physical pattern makes copy direction/overlap visible.
  rng=random.Random(0x6510);bitmap=rng.randbytes(8000);attrs=rng.randbytes(1000)
  vectors=[]
  for direction in(-1,1):
   for first in range(22):
    if 0<=first+direction<22:
     for count in sorted({0,1,min(3,22-first-max(direction,0)),22-first-max(direction,0)}):
      if count>=0 and first+count<=22 and first+direction+count<=22:vectors.append((first,count,direction))
  for index,(first,count,direction)in enumerate(vectors):
   f.m.load(0x6000,bitmap);f.m.load(0x4000,attrs);f.m.load(f.s['se_gc_valid'],b'\1\1\1');plan(first,count,direction)
   before=g.reu();r,n0,_,_=invoke(3);assert not r.p&1 and r.a==0 and g.reu()==before,(index,'PREPARE')
   r,n1,old,now=invoke(4);assert not r.p&1 and r.a==0,(index,'APPLY',r.a)
   after=g.reu();want=bytearray(before)
   if count:
    lo=bank*65536;want[lo+0x2000:lo+0x2000+count*320]=old[0x6280+first*320:0x6280+(first+count)*320];want[lo+0x3c00:lo+0x3c00+count*40]=old[0x4050+first*40:0x4050+(first+count)*40]
    assert f.read(f.s['se_gc_valid'],3)==bytes(3)
   assert after==want,(index,'whole16MiB/source/fonts/history/clip/typed53')
   cases.append(dict(first=first,count=count,direction=direction,prepare=n0,apply=n1))
  # Invalid plans never reach DMA or pixels; no accepted raw pointer is supplied.
  invalid=[(22,0,1),(0,23,1),(0,1,-1),(21,1,1),(1,22,-1),(0,1,0),(0,1,2)]
  for first,count,direction in invalid:
   plan(first,count,direction);before=g.reu();bits=f.read(0x6000,8000)+f.read(0x4000,1000);r,*_=invoke(3);assert r.p&1 and r.a==0x90 and before==g.reu() and bits==f.read(0x6000,8000)+f.read(0x4000,1000);faults.append('invalid-plan-'+str((first,count,direction)))
  for owner in (0,1,2,3,5,255):
   f.m.load(G,b'\xa7'*128);opaque=f.read(G,128);before=g.reu()
   for op in(3,4):r,*_=invoke(op,owner);assert r.p&1 and r.a==0xb2 and f.read(G,128)==opaque and before==g.reu()
   faults.append('opaque-owner-'+str(owner))
  for at in range(9,15):
   plan(1,20,-1);assert not invoke(3)[0].p&1;f.m.write(G+at,f.m.read(G+at)^1);before=g.reu();r,*_=invoke(4);assert r.p&1 and r.a==0x90 and before==g.reu();faults.append('damaged-derived-plan-'+str(at))
  for name,delta,expected in [('se_gc_epoch',0,0x18),('se_reu_epoch',0,0x18),('se_reu_retired',0,0x18),('se_reu_logical_owner',handle,0x18),('se_reu_physical_owner',bank,0x18),('se_reu_map',handle,0x18),('se_render_caps',0,0x90),('se_sel_mark',0,0x90),('se_mode',0,0x90)]:
   plan(1,20,-1);assert not invoke(3)[0].p&1;a=f.s[name]+delta;v=f.m.read(a);f.m.write(a,0 if name=='se_mode'else v^1);before=g.reu();r,*_=invoke(4);assert r.p&1 and r.a==expected and before==g.reu(),(name,r.a,r.p);f.m.write(a,v);faults.append('changed-'+name)
  # Direct internal source guard component: same loaded R24 image, no host
  # source snapshot supplied. The code captures all59 fields from live state.
  source_faults=[]
  labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',((builddir if builddir else out/'pair')/'candidate/leaf.lbl').read_text())}
  fields=[('se_reu_epoch',2),('se_doc_epoch',2),('se_doc_generation',2),('se_doc_meta',5),('se_doc_original',5),('se_doc_append',5),('se_doc_length',3),('se_doc_root_count',1),('se_r_revision',4),('se_hot_ready',1),('se_hot_pending',1),('se_hot_phase',1),('se_hot_owned',1),('se_hot_fault',1),('se_hot_epoch',2),('se_hot_generation',2),('se_hot_original',5),('se_hot_append',5),('se_hot_base',3),('se_hot_old_length',2),('se_hot_length',2),('se_hot_left',2),('se_hot_right',2)]
  def source_call(name):
   before=f.read(0,65536);reu=g.reu();r,n=f.fast_call(labels[name]);after=f.read(0,65536);want=bytearray(before)
   allow=[(G+25,G+91),(f.s['text_ptr'],f.s['text_ptr']+2)]
   for key,size in [('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_object_id',12),('validate_index',1),('validate_extent',1),('validate_type',1)]:allow.append((f.s[key],f.s[key]+size))
   allow.append((0x100,0x200))
   for a,b in allow:want[a:b]=after[a:b]
   assert after==want,('sourceguard wholeRAM',name,r.a,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
   assert reu==g.reu() and not f.get('se_doc_read_locks',1)
   return r,n
  f.put('se_f_owner',4,1)
  r,n=source_call('se_rg_capture_source');assert not r.p&1 and r.a==0
  actual=b''.join(f.read(f.s[name],size)for name,size in fields);assert len(actual)==59 and f.read(G+32,59)==actual
  assert not source_call('se_rg_check_source')[0].p&1
  for name,size in fields:
   a=f.s[name];old=f.read(a,size);f.m.write(a,old[0]^1)
   r,n=source_call('se_rg_check_source');assert r.p&1,(name,'changed FS59 must refuse');assert f.read(G+32,59)==actual,(name,'must not recapture')
   f.m.load(a,old);source_faults.append(name)
  for name in ('se_doc_busy','se_h_phase','se_b_phase','se_clip_busy','se_snapshot_busy'):
   a=f.s[name];old=f.m.read(a);f.m.write(a,1);r,n=source_call('se_rg_capture_source');assert r.p&1 and f.read(G+32,59)==actual;f.m.write(a,old);source_faults.append(name)
  faults.append('actual-FS59-component-'+str(len(source_faults))+'-source-and-busy-groups')
  # Original fold no-map identity remains functional after all geometry calls.
  f.put('se_ef_valid',0,1);f.m.load(0xcf00,bytes(48));f.put('se_overlay_frame',0,1);f.put('se_f_owner',4,1);before=g.reu();r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=0);assert not r.p&1 and r.a==0 and f.read(0xcf04,3)==bytes(3) and before==g.reu();faults.append('original-fold-op0-no-map-identity')
  result=dict(status='PASS',scope=__doc__,budget=budget,cases=cases,faults=faults,geometry_cases=len(cases),fault_groups=len(faults),source_faults=source_faults,wholeRAM=True,whole16MiB=True,source_lease_shim=True,source_editor_integration=False)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(cases),'geometry vectors',len(faults),'fault groups',flush=True);return result
 finally:f.close()
def transaction(out,builddir,baseline):
 """Complete actual editor proof, distinct from the component API above."""
 def load(name,path):
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 out.mkdir(parents=True);fixture=builddir/'fixture';full=D/'full'
 positive=load('geometry_public',full/'public.py').run(out/'public',fixture)
 faults=load('geometry_faults',full/'faults.py').run(out/'faults',fixture,builddir/'r24/leaf.lbl')
 compatibility=load('geometry_compatibility',full/'compatibility.py').run(out/'compatibility',baseline,fixture)
 edges=load('geometry_edges',full/'edges.py').run(out/'edges',fixture)
 regressions=load('geometry_regressions',full/'regressions.py').run(out/'regressions',fixture)
 stack=load('geometry_stack',full/'stack.py').run(out/'stack',fixture)
 timing=load('geometry_precise',ROOT/'src/render/grid/probes/raw-boundary/profile.py')
 control=timing.run(out/'control-cost',baseline);candidate=timing.run(out/'candidate-cost',fixture)
 result=dict(status='PASS',scope='Private complete C33/R24 structural transaction; CPU transport seams, no native claim.',positive=positive,faults=faults,compatibility=compatibility,edges=edges,regressions=regressions,stack=stack,control=control,candidate=candidate)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path);p.add_argument('--transaction-build',type=Path);p.add_argument('--baseline',type=Path,default=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture');p.add_argument('--out',type=Path);a=p.parse_args();out=a.out.resolve()if a.out else ROOT/'build/grid-row-geometry'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True)
 if a.transaction_build:transaction(out,a.transaction_build.resolve(),a.baseline.resolve())
 else:run(out,a.build.resolve()if a.build else None)
