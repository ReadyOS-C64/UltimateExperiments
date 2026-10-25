"""Long-prose baseline attribution plus compact C33 status subset qualification."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,hashlib,shutil
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/grid-prose-authority/20261025T190208381544Z/fixture'
def run(out):
 frozen=out/'fixture';shutil.copytree(BASE,frozen);spec=importlib.util.spec_from_file_location('statusbuild',ROOT/'src/render/grid/long-prose-candidate/build-status.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);image,budget,labels=b.build(out/'leaf');(frozen/'build/overlays/grid.seo').write_bytes(image);i=json.load(open(frozen/'freeze.json'));i['assets']['grid']=hashlib.sha256(image).hexdigest();(frozen/'freeze.json').write_text(json.dumps(i,indent=2)+'\n');dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=i['names'];f=fold.Fixture(out,frozen,dll,True);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=BASE;g=fold.Fixture(out,BASE,dll,True);cases=[];statuses=[]
 def check(tag,raw):
  want,attrs=grid.expected(f,raw)[0];assert f.read(0x6000,8000)==g.read(0x6000,8000)==want,(tag,'bitmap',[(i,a,b,c)for i,(a,b,c)in enumerate(zip(f.read(0x6000,8000),g.read(0x6000,8000),want))if a!=b or b!=c][:10]);assert f.read(0x4000,1000)==g.read(0x4000,1000)==attrs,(tag,'attrs');assert f.canonical()==g.canonical()and f.merged()==g.merged()==raw and f.read(0xc600,1024)==f.shim
 try:
  for width in(60,80):
   raw=grid.native_text('Alpha paragraph having ample room.\rTail.')
   for x in(f,g):x.source(raw);x.command(97 if width==60 else 98);x.position(12);x.render();x.finish_style()
   for key in(81,82,20,20,0x1d,0x9d):
    for x in(f,g):x.key(key);x.render();x.finish_style()
    check(str(width)+'-'+str(key),f.merged())
   # Existing full dynamic formatter is the actual reachable glyph authority.
   # All hex nibble values, both strings, and inverse bit use exactly23glyphs.
   for nibble in range(16):
    for pending,dirty in((0,0),(0,1),(1,0),(1,1)):
     for reverse in(0,128):
      caret=int(hex(nibble)[2:]*6,16)
      for x in(f,g):
       x.put('se_hot_caret',caret);x.put('se_hot_pending',pending,1);x.put('se_h_dirty',dirty,1);x.put('se_ink_reverse',reverse,1);x.m.load(0xb000,x.assets['grid'][36:])
      r,n=f.fast_call(labels['status']);oldlabels={p[2].lstrip('.'):int(p[1],16)for line in(b.LEAF/'grid.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};rg,ng=g.fast_call(oldlabels['status']);assert not r.p&1 and not rg.p&1
      assert f.read(0x7e00,320)==g.read(0x7e00,320)and f.read(0x43c0,40)==g.read(0x43c0,40),(width,nibble,pending,dirty,reverse,'status exact')
      statuses.append(dict(width=width,nibble=nibble,pending=pending,dirty=dirty,reverse=reverse,instructions=n,old_instructions=ng))
   # Actual root baseline cost on a continuation row. No invented semantic
   # admission: both versions must still take the released whole pipeline.
   raw=grid.native_text(':::basic\r10 PRINT 1\r:::\rAlpha '+('word '*100)+'ends.\rTail.')
   at=raw.index(grid.native_text('word'))+width*2+2
   for x in(f,g):x.source(raw);x.command(97 if width==60 else 98);x.position(at);x.render();x.finish_style()
   for key in(81,20):
    values=[]
    for x in(f,g):
     x.key(key);start=x.total_instructions;loads=x.get('se_overlay_loads',2);x.render();first=x.total_instructions-start;x.finish_style();values.append(dict(first_instructions=first,settled_instructions=x.total_instructions-start,loads=(x.get('se_overlay_loads',2)-loads)&65535))
    check('long-'+str(width)+'-'+str(key),f.merged());cases.append(dict(width=width,key=key,candidate=values[0],baseline=values[1]));print('BASELINE',cases[-1],flush=True)
  result=dict(status='passed',budget=budget,status_vectors=len(statuses),status_cases=statuses,long_baseline=cases,scope='Compact font preparatory component only; long prose still falls back safely.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()
if __name__=='__main__':
 out=ROOT/'build/grid-long-prose'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
