"""Private one-past empty suffix: actual checked kernel and public publication."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,re,sys
import test_grid_raw_wrapped as wrapped
ROOT=wrapped.ROOT;D=ROOT/'src/render/grid/probes/row-geometry-extend';G=0x8d80
raw=wrapped.raw;profile=raw.caret.profile;observer=profile.observer
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def kernel(out,fixture,labels):
 out.mkdir();g=observer.Gate(out,fixture);f=g.f;symbols={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',labels.read_text())};tested=[]
 def invoke(name):return f.fast_call(symbols[name])[0]
 def plan(first,count,direction):f.m.load(G,bytes((1,direction&255,first,count))+bytes([0xa7])*21)
 try:
  f.source(b'Plain\rTail\r',physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(98);profile.drain(f)
  for name in('se_i_ready','se_i_count','se_n_cache_count'):f.put(name,0,1)
  f.put('se_f_owner',4,1);f.put('se_ef_valid',0,1);f.put('se_overlay_frame',0,1);assert not f.fast_call(f.s['se_overlay_call'],a=24,x=0)[0].p&1
  reu=g.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000)
  for first in range(25):
   for count in range(25):
    for direction in(-1,0,1,2,127):
     plan(first,count,direction);before=f.read(0,65536);r=invoke('se_rg_prepare');after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];want[G:G+25]=after[G:G+25]
     assert after==want,('wholeRAM prepare',first,count,direction)
     valid=direction in(-1,1)and first<=22 and count<=22 and 0<=first+direction<=22 and first+direction+count<=22 and first+count<=22
     assert bool(r.p&1)!=valid,(first,count,direction,r.a,r.p)
     assert r.a==(0 if valid else 0x90)
     tested.append((first,count,direction,valid))
  assert g.reu()==reu and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels
  plan(22,0,-1);assert not invoke('se_rg_prepare').p&1;assert f.read(G+9,6)==bytes.fromhex('007ec07c0000')
  # A zero-byte interval executes no DMA, does not invalidate GC and writes
  # only derived control/stack; prove full RAM and all16MiB rather than a mask.
  f.m.load(f.s['se_gc_valid'],bytes([1,1,1]));before=f.read(0,65536);reu=g.reu();dmas=f.get('se_reu_dma_calls',2);r=invoke('se_rg_apply');after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];want[G:G+25]=after[G:G+25]
  assert not r.p&1 and r.a==0 and after==want and reu==g.reu()and dmas==f.get('se_reu_dma_calls',2)and f.read(f.s['se_gc_valid'],3)==bytes([1,1,1])
  for at in range(9,15):
   plan(22,0,-1);assert not invoke('se_rg_prepare').p&1;f.m.write(G+at,f.m.read(G+at)^1);before=g.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);r=invoke('se_rg_apply');assert r.p&1 and r.a==0x90 and g.reu()==before and pixels==f.read(0x6000,8000)+f.read(0x4000,1000)
  result=dict(status='PASS',plans=len(tested),newly_admitted=[x for x in tested if x[0]==22 and x[3]],zero_DMA=True,whole64KiB=True,whole16MiB=True,derived_address_faults=6,scope='Explicit internal-kernel component seam after actual FE initialization and index retirement; public C33 proof separate.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
def public(out,fixture,baseline=False):
 out.mkdir();g=observer.Gate(out,fixture);f=g.f;cases=[]
 try:
  for width in(60,80):
   for row in(19,20,21):
    data=b'P\r'*row+b'A'*(width-1)+b'\r';at=2*row+5;f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(at);profile.drain(f);source=data;where=at
    for key in(observer.Q,20):
     audit=g.audit_begin();initial=f.total_instructions;f.key(key);profile.drain(f);used=f.total_instructions-initial;g.audit_end(audit,'edge')
     source=source[:where]+bytes([key])+source[where:]if key!=20 else source[:where-1]+source[where:];where+=1 if key!=20 else -1
     assert f.merged()==source and f.read(0xc600,1024)==f.shim
     (bits,attrs),_,_,_=observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs;wrapped.packet_check(f,source,(width,row,key))
     route=f.m.read(0x89ff);expected=0 if row==21 or(baseline and row==20 and key==20)else 2;assert route==expected,(width,row,key,route,expected)
     cases.append(dict(width=width,terminal=row,key=key,route=route,instructions=used,pixels=hashlib.sha256(bits+attrs).hexdigest()))
  result=dict(status='PASS',cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
def run(out,builddir=None):
 out.mkdir(parents=True);builder=load('empty_suffix_build',D/'build.py')
 if builddir is None:fixture,budget=builder.build(out/'pair');builddir=out/'pair'
 else:fixture=builddir/'fixture';budget=json.loads((builddir/'result.json').read_text())
 k=kernel(out/'kernel',fixture,builddir/'candidate/leaf.lbl');p=public(out/'public',fixture);c=public(out/'control',builder.RELEASE/'fixture',True)
 # Also rerun the exact released20-case actual public source/history/NC/16MiB proof.
 broad=load('released_geometry_public',ROOT/'src/render/grid/probes/row-geometry/full/public.py').run(out/'public20',fixture)
 result=dict(status='PASS',budget=budget,kernel=k,candidate=p,control=c,public20=broad,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out.resolve()if a.out else ROOT/'build/grid-row-geometry-extend'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.build.resolve()if a.build else None)
