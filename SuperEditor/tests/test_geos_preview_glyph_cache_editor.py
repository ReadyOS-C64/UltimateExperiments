"""Actualpublic68 preview A/B with only private sealedR23 substitution."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,hashlib,shutil
import test_geos_preview_editor as public
from overlays import wrap
ROOT=public.ROOT;BASE=ROOT/'build/geos-incremental-editor/20261025T115028786969Z/fixture';D=ROOT/'src/render/geos/preview-glyph-cache-candidate'

def run(out,base=BASE,build_script="build-cache.py"):
 buildout=out/'leaf';spec=importlib.util.spec_from_file_location('cachebuild',D/build_script);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(buildout,base);report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];image=wrap((buildout/'cache.bin').read_bytes(),0,23,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
 baseclass=public.Fixture;originalguard=public.guard_preview_reu;results={}
 for variant in('control','candidate'):
  costs=[]
  class Private(baseclass):
   def __init__(self,*args,**kw):
    super().__init__(*args,**kw)
    if variant=='candidate':self.assets['geosfontrow']=image
   def render(self):
    preview=bool(self.get('se_r_presentation',1));start=self.total_instructions;loads=self.get('se_overlay_loads',2);before_handle=self.get('se_gc_handle',1);r=super().render()
    if preview:costs.append(dict(instructions=self.total_instructions-start,loads=(self.get('se_overlay_loads',2)-loads)&65535,FE_before=before_handle,FE_after=self.get('se_gc_handle',1)))
    return r
  def guard(f,before,after,tag):
   if variant=='control':return originalguard(f,before,after,tag)
   handle=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+handle);p=bank*65536+0xeb69;q=p+4160;normalized=after[:p]+before[p:q]+after[q:];r=originalguard(f,before,normalized,tag);r['allowed_relative_half_open'].append([0xeb69,0xfba9]);r['allowed_bytes']+=4160;r['changed_glyphcache_bytes']=sum(a!=b for a,b in zip(before[p:q],after[p:q]));return r
  public.Fixture=Private;public.guard_preview_reu=guard;target=out/variant;target.mkdir()
  try:public.run(target,base)
  finally:public.Fixture=baseclass;public.guard_preview_reu=originalguard
  result=json.loads((target/'result.json').read_text());assert len(costs)==len(result['frames']),(variant,len(costs),len(result['frames']))
  for frame,cost in zip(result['frames'],costs):frame['CPU_render']=cost
  result['scope']='PublicrootC27/R23preview with exactpackagedcontrol oronlyprivatesealedR23image replacement. Independentfullpixels/settings/source/history/catalog, full16MiB except originalpreviewcache+exact4160glyphcacheinownedFE.';(target/'result.json').write_text(json.dumps(result,indent=2)+'\n');results[variant]=result
 for a,b in zip(results['control']['frames'],results['candidate']['frames']):assert a['tag']==b['tag']and a['bitmap_sha256']==b['bitmap_sha256']and a['bottom']==b['bottom']and a['top']==b['top']and a['rows']==b['rows'],('A/B',a['tag'])
 pairs=[dict(tag=a['tag'],control=a['CPU_render'],candidate=b['CPU_render'])for a,b in zip(results['control']['frames'],results['candidate']['frames'])];result=dict(status='passed',budget=budget,frames=len(pairs),pairs=pairs,scope='Actualpublic68 fullsource+fontoracle A/B, no production/nativeclaim. Bothlanesmodehiresbeforepreview establishFE; directsource40firstpagecacheabsence is separatecaveat.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PUBLICPASS',out,flush=True)
if __name__=='__main__':
 out=ROOT/'build/geos-preview-glyph-cache-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
