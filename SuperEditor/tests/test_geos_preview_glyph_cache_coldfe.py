"""Direct source40→preview has no FEbank during firstpage glyphs (caveat proof)."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,importlib.util,shutil
import test_geos_preview_editor as p
from geos_preview_model import FontCatalog,render,with_chrome
from overlays import wrap

def run(out,base,script='build-premeasure.py'):
 frozen,identity=p.geos.freeze(out,base);shutil.copytree(p.ROOT/'build/geos-font-catalog',frozen/'genuine',dirs_exist_ok=True);p.geos.grid.editor_fixture.ROOT=p.geos.grid.cpu_editor.ROOT=frozen;p.geos.grid.editor_fixture.NAMES=p.geos.grid.cpu_editor.NAMES=identity['names'];d=p.ROOT/'src/render/geos/preview-glyph-cache-candidate';spec=importlib.util.spec_from_file_location('cachebuild',d/script);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'leaf',frozen);s=json.loads((frozen/'build/editor-report.json').read_text());image=wrap((out/'leaf/cache.bin').read_bytes(),0,23,api=(s['symbols']['se_overlay_call'],s['symbols']['se_overlay_frame']),binding_digest=bytes.fromhex(s['resident_binding']['digest']));f=p.Fixture(out,frozen,p.geos.grid.runner(out),True);f.assets['geosfontrow']=image
 try:
  data=p.geos.native_text(''.join('Line '+str(i)+' **bold**\r'for i in range(90)));f.source(data);f.render();assert f.get('se_mode',1)==0 and f.get('se_gc_handle',1)==0;canonical=f.canonical();catalog=f.catalog();f.command(99);assert f.get('se_gc_handle',1)==0;f.command(102);start=f.total_instructions;f.render();cost=f.total_instructions-start;h=f.get('se_gc_handle',1);assert h
  bank=f.m.read(f.s['se_reu_map']+h);reu=f.reu();assert reu[bank*65536+0xeb69:bank*65536+0xfba9]==bytes(4160),'firstpageunexpectedglyphcache'
  fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes());settings=f.read(f.s['se_editor_settings'],64);want=render(data,settings,catalog=fonts);matrix,colors,popup=p.geos.grid.logical_ui(f,data);eb,ea=with_chrome(want.bitmap,want.attrs,matrix,colors,fonts.native);assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea and f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
  f.key(0x87);f.render();assert f.reu()[bank*65536+0xeb69:bank*65536+0xeb79]==f.read(0xa000,16),'secondpagecacheuninitialized'
  r=dict(status='passed',budget=budget,firstpage_instructions=cost,FE_before=0,FE_after=h,physicalbank=bank,firstpage_glyphcache_bytes_written=0,secondpage_header_published=True,scope='Actualpublicsource40→preview. Optionalglyphcache cannotpopulate firstpage because existingFEallocation occurs onlyafterpaint; no allocationpolicychange. Firstpage independentpixels/source/history/shim; no nativeclaim.');(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',out,flush=True)
 finally:f.close()
if __name__=='__main__':
 out=p.ROOT/'build/geos-preview-glyph-cache-coldfe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,Path(sys.argv[1]).resolve())
