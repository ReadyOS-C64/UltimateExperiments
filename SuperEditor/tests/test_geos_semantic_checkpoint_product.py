"""Private actual C21 producer + C24 seed; all other48 assets remain frozen."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as heading
from test_geos_semantic_checkpoint_codec import Fixture
geos=heading.geos;semantic=heading.semantic;D=ROOT/'src/render/geos/semantic-checkpoint-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
F=0x8b40

def run(out,base):
 spec=importlib.util.spec_from_file_location('checkpoint_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'link',base)
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);f.assets['geossema']=(out/'link/seed/geossema.seo').read_bytes();f.assets['geospage']=(out/'link/producer/geospage.seo').read_bytes();fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def check(tag,data):
  before=f.reu();canonical=f.canonical();catalog=f.catalog();f.render();assert f.catalog()==catalog and f.canonical()==canonical and f.merged()==data;bits,attrs,rows,_=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  cache,bank=f.raw_cache();r=cache[0x600:0x640];top=f.get('se_v_top');assert r[:4]==bytes([0x53,1,64,1])and int.from_bytes(r[4:7],'little')==top,(tag,top,r.hex());assert binascii.crc_hqx(r[:62],0xffff)==int.from_bytes(r[62:64],'little')
  key=f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4)+len(data).to_bytes(3,'little')+f.read(f.s['se_reu_epoch'],2)+f.read(f.s['se_doc_epoch'],2);assert r[7:35]==key
  # Only declared source-page packets/bitmap/backups and the64B checkpoint may
  # change. No FEwide mask, no source/font/history/foreign-bank mutation.
  allowed=[(0,64),(0x600,0x640),(0xb200,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)];allowed=sorted((bank*65536+a,bank*65536+b)for a,b in allowed);after=f.reu();cursor=0
  for a,b in allowed:assert after[cursor:a]==before[cursor:a],(tag,'outside FE scopes',cursor,a);cursor=max(cursor,b)
  assert cache[0xe9e8:0xea68]==fonts['bsw9-widths.bin']
  assert cache[0xe568:0xe9e8]==bytes(fonts['bsw9.bin'][i*18+y*2]for i in range(128)for y in range(9))
  assert after[cursor:]==before[cursor:],(tag,'tail REU',cursor,next(((i,a,b)for i,(a,b)in enumerate(zip(before,after))if i>=cursor and a!=b),None))
  assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned']),(tag,'shim/leases',f.debug())
  geos.png(bits,attrs,out/(tag+'.png'));entry=dict(tag=tag,top=top,source_bytes=len(data),rows=len(rows),checkpoint=r.hex());cases.append(entry);print('PASS',entry,flush=True)
  # This is the ACTUAL emitted producer record, not host packed/substituted.
  f.put('se_f_owner',4,1)
  for n in ['se_i_ready','se_i_count','se_n_cache_count']:f.put(n,0,1)
  f.m.load(F,top.to_bytes(3,'little'));f.m.write(F+179,0);f.m.write(f.s['se_overlay_frame'],3);before=f.reu();r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=1);assert not r.p&1 and r.a==0 and f.m.read(F+180)==1 and f.read(F+170,3)==top.to_bytes(3,'little');assert f.reu()==before and not f.get('se_doc_read_locks',1);f.put('se_f_owner',0,1)
 try:
  documents=[('prose',geos.native_text('First prose.\rSecond row.\rTail.'),0),('heading-region',geos.native_text(':::region A\r# Heading words.\rBody.\r:::end\rTail.'),14),('BASIC',geos.native_text(':::basic\r10 PRINT "Hi"\r20 REM word\r:::\rTail.'),12),('far64k',geos.native_text('prefix\r')*9400+geos.native_text(':::asm\rstart: lda #1\r:::\rTail.'),65810)]
  for tag,data,at in documents:
   f.source(data);f.command(99);f.position(at);check(tag,data)
  # Foreign phase must remain completely opaque before C21's owner claim.
  f.put('se_f_owner',1,1);f.m.write(f.s['se_overlay_frame'],2);r,n=f.fast_call(f.s['se_overlay_call'],a=21,x=1);assert r.p&1 and r.a==0xb2
  f.m.write(f.s['se_overlay_frame'],0);ram=f.read(0,65536);reu=f.reu();r,n=f.fast_call(0xb010);after=f.read(0,65536);assert r.p&1 and r.a==0xb2 and after[:0x100]==ram[:0x100]and after[0x200:]==ram[0x200:]and f.reu()==reu;f.put('se_f_owner',0,1)
  result=dict(status='passed',budget=budget,identity=identity,cases=cases,scope='Actual public editor mode3/C21/C24/R14/R21 producer frames, private two sealed overlay substitutions only. Exact fullpixel/canonical/history/catalog/16MiB scopes; actual emitted64B CP feeds actual TRY_SEED. No C23 integration or automatic lookup/source-performance claim yet.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-semantic-checkpoint-product'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);result=run(out,a.fixture.resolve());print('RESULT',result['status'],'cases',len(result['cases']),'budget',result['budget'])
