"""Private R21 uniform-role resolve/idiom A/B; canonical sources unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_literal_profile as profile
import test_geos_literal_byte_candidate as comprehensive
from overlays import wrap
HERE=ROOT/'src/render/geos/probes/raster-next'
MODE=True
DEFAULT=ROOT/'build/cache-editor-product/20261026T045019460982Z/fixture'
spec=importlib.util.spec_from_file_location('raster_next_build',HERE/'build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def prepare(out,base,variant):
 d=out/'link';src,s,labels,payload=builder.build(d,base,MODE if variant=='candidate'else False);report=json.loads((base/'build/editor-report.json').read_text());image=wrap(payload,0,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']));(d/'geosrow.seo').write_bytes(image);return d,src,s,labels,payload,image,{}

class Fixture(comprehensive.Fixture):
 def check(self,*a,**k):
  start=self.m.regs().cycles;r=super().check(*a,**k);self.last_cycles=self.m.regs().cycles-start;return r

def run(out,base,full):
 results={};comprehensive.prepare=prepare;comprehensive.Fixture=Fixture
 if full:
  for variant in('control','candidate'):
   d=out/(variant+'-full');d.mkdir();results[variant]=comprehensive.component(d,base,variant)
  assert results['control']['aggregate_outputs_sha256']==results['candidate']['aggregate_outputs_sha256']
 metrics={};vertical_edges={}
 for variant in('control','candidate'):
  d=out/variant;d.mkdir();link,src,s,ls,payload,image,_=prepare(d,base,variant);f=Fixture(link,base,src,s,ls,payload);rows=[]
  try:
   before=f.reu()
   samples=[('blank',[],(0,320,0,8)),('prose',[profile.rec(b'Wim. gjpqy Mixed UPPER/lower')],(0,320,0,8)),('heading',[profile.rec(b'# Heading **strong** and *emphasis*',role=2,flag=1)],(0,320,0,8)),('colored',[profile.rec(b'Wim. gjpqy '*9,style=3,role=7)],(0,320,0,8)),('selected',[profile.rec(b'Wim. gjpqy '*9,style=3,flag=6,role=7)],(0,320,0,8)),('partial',[profile.rec(b'Wim. gjpqy Mixed UPPER/lower')],(7,319,1,7)),('two-runs',[profile.rec(b'gjpqy Previous line',y=-8,style=2,role=3),profile.rec(b'Next logical line',y=1,style=1,flag=2,role=8)],(0,320,0,8)),('native',[profile.rec(bytes([0x5c,0x5e,0x7f,0xa1,0xff])*10,style=3,role=2)],(0,320,0,8)),('same-uniform',[profile.rec(b'Prior',y=-8,role=2),profile.rec(b'Current inverse row',y=1,role=2,flag=1)],(0,320,0,8))]
   for label,runs,clip in samples:
    used,counts,hist=f.check(runs,clip=clip);rows.append(dict(label=label,instructions=used,cycles=None,bitmap=hashlib.sha256(f.read(0x6280,320)).hexdigest(),attrs=hashlib.sha256(f.read(0x4050,40)).hexdigest(),histogram=hashlib.sha256(f.read(profile.leaf.F+98,560)).hexdigest(),resolve_instructions=sum(counts[ls['resolve']:ls['complete']]),byte_row_instructions=sum(counts[ls['byte_row']:ls['validate']])));print('PROFILE',variant,rows[-1],flush=True)
   if full:
    edge_count=0
    for origin in range(-8,8):
     for top in range(9):
      for bottom in range(top,9):
       raw=b'Wim. gjpq';n=len(raw)
       runs=[(raw,bytes(i%4 for i in range(n)),bytes(i%14 for i in range(n)),bytes(i%8 for i in range(n)),1,origin)]
       f.check(runs,row=(origin+top+bottom)%25,clip=(0,320,top,bottom));edge_count+=1
    vertical_edges[variant]=edge_count
   assert f.reu()==before
  finally:f.close()
  metrics[variant]=rows
 for a,b in zip(metrics['control'],metrics['candidate']):
  assert a['label']==b['label']and all(a[n]==b[n]for n in('bitmap','attrs','histogram'))
  b.update(instruction_delta=b['instructions']-a['instructions'],instruction_reduction_percent=round((1-b['instructions']/a['instructions'])*100,3))
 result=dict(status='PASS',fixture=str(base),mode=str(MODE),component=results,vertical_edges=vertical_edges,metrics=metrics,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('RESULT',out,flush=True);return result
def public(out,base):
 import test_cache_observer as observer
 import test_plain_geos as plain
 import test_grid_editor_vice as native
 results={}
 for variant in('control','candidate'):
  d=out/variant;d.mkdir();g=observer.Gate(d,base);f=g.f
  link=d/'leaf';tree,s,ls,payload=builder.build(link,base,MODE if variant=='candidate'else False)
  report=json.loads((base/'build/editor-report.json').read_text());image=wrap(payload,0,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
  if variant=='control':assert image==(base/'build/overlays/geosrow.seo').read_bytes()
  else:f.assets['geosrow']=image
  (link/'geosrow.seo').write_bytes(image)
  fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
  cases=[]
  try:
   data=native.fixture();assert len(data)==422
   for preset,caps in(('plain',0),('markdown',1),('full',3)):
    f.source(data);f.typed(observer.geos.native_text('syntax '+preset));f.command(99);f.render();f.command(35);f.render()
    before=g.audit_begin();stable=g.stable();catalog=f.catalog();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dma=f.get('se_reu_dma_calls',2)
    f.command(34);f.render();elapsed=f.total_instructions-start;g.audit_end(before,preset)
    assert g.stable()==stable and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim
    assert not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
    bits,attrs,_=plain.expected(f,data,fonts,caps);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
    observer.geos.png(bits,attrs,d/(preset+'.png'));item=dict(preset=preset,instructions=elapsed,loads=(f.get('se_overlay_loads',2)-loads)&65535,dma=(f.get('se_reu_dma_calls',2)-dma)&65535,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());cases.append(item);print('PUBLIC',variant,item,flush=True)
  finally:f.close()
  results[variant]=cases
 for a,b in zip(results['control'],results['candidate']):
  assert all(a[n]==b[n]for n in('preset','loads','dma','top','caret','bitmap','attrs'));b.update(instruction_reduction_percent=round((1-b['instructions']/a['instructions'])*100,3))
 (out/'result.json').write_text(json.dumps(dict(status='PASS',mode=str(MODE),results=results,scope='Private R21-only packagedimage replacement in actual resident fullTOP renderer; independent fullVIC/source/history/catalog/shim/checkedDMA whole16MiB. CPUinstructions only, no native timing claim.'),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--full',action='store_true');p.add_argument('--public',action='store_true');p.add_argument('--variant',choices=['uniform','vertical','vertical-zero'],default='uniform');a=p.parse_args();MODE=a.variant if a.variant.startswith('vertical')else True;out=ROOT/'build/geos-raster-next'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);
 if a.public:public(out,a.fixture)
 else:run(out,a.fixture,a.full)
