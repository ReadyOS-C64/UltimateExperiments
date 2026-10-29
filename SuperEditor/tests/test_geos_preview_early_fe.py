"""Private early optional FE allocation A/B; actual public C27/R23 and guards."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,json,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_preview_editor as reference
import test_geos_preview_cache_candidate as cache
from geos_preview_model import render,FontCatalog,with_chrome
BASE=ROOT/'build/geos-incremental-editor/20261025T131207214412Z/fixture'
D=ROOT/'src/render/geos/preview-early-fe-candidate'

def builder():
 s=importlib.util.spec_from_file_location('early_build',D/'build.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def run(out,base):
 images,budgets=builder().build(out/'leaves',base);frames=[];faults=[]
 samples={'diverse':reference.DIVERSE,'repeat':cache.geos.native_text('The quick brown fox repeated words. '*8+'\r'+'Ordinary repeated body text. '*7+'\r'),'empty':b'','short':cache.geos.native_text('A short line.\r')}
 def fixture(path,label,data):
  path.mkdir();frozen,identity=cache.geos.freeze(path,base);target=frozen/'build/overlays/geospreview.seo';target.write_bytes(images[label]);identity['assets']['geospreview']=hashlib.sha256(images[label]).hexdigest();(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
  cache.geos.grid.editor_fixture.ROOT=cache.geos.grid.cpu_editor.ROOT=frozen;cache.geos.grid.editor_fixture.NAMES=cache.geos.grid.cpu_editor.NAMES=identity['names'];dll=cache.profiled_runner(path,json.loads((frozen/'build/editor-report.json').read_text())['symbols']);f=reference.Fixture(path,frozen,dll,True);f.source(data);assert f.get('se_mode',1)==0 and not f.get('se_gc_handle',1)
  if not(frozen/'genuine').exists():shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
  fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes());return f,dll,fonts
 def compare(f,data,fonts,tag,before,canonical,catalog):
  expected=render(data,f.read(f.s['se_editor_settings'],64),catalog=fonts,top=f.get('se_v_top'));matrix,colors,rect=cache.geos.grid.logical_ui(f,data);assert rect is None;bits,attrs=with_chrome(expected.bitmap,expected.attrs,matrix,colors,fonts.native)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independentpixels');assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim,(tag,'source/history/catalog/shim')
  assert not any(f.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
  after=f.reu()
  if f.get('se_gc_handle',1):guard=reference.guard_preview_reu(f,before,after,tag)
  else:assert after==before;guard=dict(all_REU_readonly=True)
  return bits,attrs,guard
 for label in ['before','after']:
  for name,data in samples.items():
   p=out/(label+'-'+name);f,dll,fonts=fixture(p,label,data)
   try:
    # Public mode/preview commands before any literal render: GC remains0.
    f.command(99);assert not f.get('se_gc_handle',1);f.command(102);canonical=f.canonical();catalog=f.catalog();before=f.reu();dll.pc_zero();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dma=f.get('se_reu_dma_calls',2);f.render();n=f.total_instructions-start;bits,attrs,guard=compare(f,data,fonts,label+'-'+name,before,canonical,catalog)
    cache.geos.png(bits,attrs,p/'first.png');frames.append(dict(variant=label,sample=name,phase='cold40-to-preview-without-intervening-literal-paint',instructions=n,loads=(f.get('se_overlay_loads',2)-loads)&65535,DMAcalls=(f.get('se_reu_dma_calls',2)-dma)&65535,calls={str(i):dll.pc_calls(i)for i in[14,23,24,25,26,27]},bitmap_sha256=hashlib.sha256(bits+attrs).hexdigest(),FE=f.get('se_gc_handle',1),REUguard=guard))
    before=f.reu();dll.pc_zero();start=f.total_instructions;f.put('se_e_redraw',1,1);f.render();n=f.total_instructions-start;bits,attrs,guard=compare(f,data,fonts,label+'-'+name+'-warm',before,canonical,catalog);assert before==f.reu();frames.append(dict(variant=label,sample=name,phase='unchanged-body-hit',instructions=n,bitmap_sha256=hashlib.sha256(bits+attrs).hexdigest(),REUguard=guard))
   finally:f.close()
 # Real allocator pressure: cache is optional and cannot fail rendering.
 for label in ['before','after']:
  data=samples['short'];p=out/(label+'-pressure');f,dll,fonts=fixture(p,label,data)
  try:
   hogs=[]
   while True:
    r=f.call('se_reu_alloc',0xa5)
    if r.p&1:break
    hogs.append(r.a)
   f.command(99);f.command(102);canonical=f.canonical();catalog=f.catalog();before=f.reu();f.render();compare(f,data,fonts,label+'-pressure',before,canonical,catalog);assert not f.get('se_gc_handle',1)and f.reu()==before
   faults.append(dict(variant=label,case='realallocationexhaustion',A5allocations=len(hogs),rendered_without_FE=True,wholeREU_readonly=True))
   for h in reversed(hogs):r,_=f.fast_call(f.s['se_reu_free'],x=h);assert not r.p&1
  finally:f.close()
 # Cancel before first glyph: one retained optional FE at most, never new
 # allocations on repeated cancellations; source/foreign backing remains exact.
 for label in ['before','after']:
  data=samples['short'];p=out/(label+'-STOP');f,dll,fonts=fixture(p,label,data)
  try:
   f.command(99);f.command(102);canonical=f.canonical();before=f.reu();seen=[]
   for attempt in range(3):
    f.put('se_e_redraw',1,1);f.call('se_editor_render')
    for _ in range(20):
     if f.get('se_f_owner',1)==4 and f.m.read(0x9135)==24:break
     f.call('se_editor_service')
    else:raise AssertionError('no first semantic handoff')
    seen.append(f.get('se_gc_handle',1));f.queued(3);f.call('se_editor_service');assert not any(f.get(n,1)for n in ['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned'])and f.canonical()==canonical and f.reu()==before
   assert len(set(seen))==1 and(bool(seen[0])==(label=='after'))
   faults.append(dict(variant=label,case='STOP-before-first-glyph3times',FEhandles=seen,source_lease_foreign_REU_exact=True))
  finally:f.close()
 # Checked metadata invalidation uses the same header/body guards after the
 # early-allocation path; normal rebuilt pixels still match full source model.
 data=samples['short'];p=out/'after-metadata';f,dll,fonts=fixture(p,'after',data)
 try:
  f.command(99);f.command(102);f.render();canonical=f.canonical();catalog=f.catalog();bank,physical=f.raw_cache();f.m.write(0x8000,bank[0xea88]^1);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_c64',0x8000,2);f.put('se_reu_offset',0xea88,2);f.put('se_reu_length',1,2);assert not f.call('se_reu_copy').p&1
  before=f.reu();f.put('se_e_redraw',1,1);f.render();compare(f,data,fonts,'metadata-repair',before,canonical,catalog);faults.append(dict(variant='after',case='checkedmetadataCRCfault',repaired=True))
 finally:f.close()
 comparisons=[]
 for name in samples:
  a=next(x for x in frames if x['variant']=='before'and x['sample']==name and x['phase'].startswith('cold'));b=next(x for x in frames if x['variant']=='after'and x['sample']==name and x['phase'].startswith('cold'));assert a['bitmap_sha256']==b['bitmap_sha256'];comparisons.append(dict(sample=name,before=a['instructions'],after=b['instructions'],saved=a['instructions']-b['instructions'],percent_saved=round(100*(a['instructions']-b['instructions'])/a['instructions'],3)))
 result=dict(status='passed',fixture=str(base),budgets=budgets,frames=frames,faults=faults,comparisons=comparisons,scope=__doc__+' Source40-to-mode3-to-preview public commands are consecutive before any literal paint; no physical key/native timing claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-preview-early-fe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve())
