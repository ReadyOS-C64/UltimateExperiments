"""PrivateR27/C16 replacements on actualpublicpreview/grid/semantic UI gates."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys
import test_geos_chrome_rows as core
from overlays import wrap
ROOT=core.ROOT

def run(out,base,lane):
 budget=core.build(out/'leaf',base);r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols'];images={name:wrap((out/'leaf'/file).read_bytes(),slot,id_,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(r['resident_binding']['digest']))for name,file,slot,id_ in [('geoscaret','r27.bin',0,27),('gridedit','c16.bin',1,16)]}
 if lane=='preview':
  import test_geos_preview_editor as public
  original=public.Fixture;results={}
  for variant in('control','candidate'):
   costs=[]
   class Private(original):
    def __init__(self,*a,**kw):
     super().__init__(*a,**kw)
     if variant=='candidate':self.assets.update(images)
    def render(self):
     preview=bool(self.get('se_r_presentation',1));n=self.total_instructions;c=self.get('se_overlay_calls',2);rr=super().render()
     if preview:costs.append(dict(instructions=self.total_instructions-n,calls=(self.get('se_overlay_calls',2)-c)&65535))
     return rr
   public.Fixture=Private;target=out/variant;target.mkdir()
   try:public.run(target,base)
   finally:public.Fixture=original
   result=json.loads((target/'result.json').read_text());assert len(result['frames'])==len(costs)
   for f,c in zip(result['frames'],costs):f['CPU_render']=c
   (target/'result.json').write_text(json.dumps(result,indent=2)+'\n');results[variant]=result
  pairs=[]
  for a,b in zip(results['control']['frames'],results['candidate']['frames']):
   assert a['tag']==b['tag']and a['bitmap_sha256']==b['bitmap_sha256']and a['top']==b['top']and a['bottom']==b['bottom']and a['rows']==b['rows'];pairs.append(dict(tag=a['tag'],control=a['CPU_render'],candidate=b['CPU_render']))
  result=dict(status='passed',lane=lane,budget=budget,frames=68,pairs=pairs,scope='Actualpublic68+A/B allpixels/source/history/catalog/shim/precisefull16MiBpreviewguard; privateactualtwoSEOreplacements only, no nativecycles.')
 else:
  if lane=='grid':
   import test_grid_modes as gate;original=gate.Fixture
  else:
   import test_geos_semantic_editor as gate;original=gate.geos.Fixture
  class Private(original):
   def __init__(self,*a,**kw):super().__init__(*a,**kw);self.assets.update(images)
   def remove(self,identity,slot):
    # Existingmodefixture predates managed-verificationbit2/catalog64. Only
    # thisprivatewrapper corrects lookup; actualabsencefaultremainsunchanged.
    at=next(i for i in range(self.s['se_overlay_capacity'])if self.m.read(self.s['se_overlay_ids']+i)==identity and(self.m.read(self.s['image_slot']+i)&1)==slot)
    self.m.write(self.s['se_overlay_ids']+at,0);self.m.write(self.s['se_overlay_active']+slot,0);return at
  if lane=='grid':gate.Fixture=Private
  else:gate.geos.Fixture=Private
  target=out/lane;target.mkdir()
  try:
   if lane=='grid':gate.run(target,base,True)
   else:gate.run(target,base,inline_case=True)
  finally:
   if lane=='grid':gate.Fixture=original
   else:gate.geos.Fixture=original
  result=dict(status='passed',lane=lane,budget=budget,gate=json.loads((target/'result.json').read_text()),scope='Actualunchangedpublicmode/UIoracle withonlyprivateC16/R27SEO; no nativeclaim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--lane',choices=['preview','grid','semantic'],required=True);a=p.parse_args();out=ROOT/('build/geos-chrome-rows-'+a.lane)/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.lane)
