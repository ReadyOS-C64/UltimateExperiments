"""Private R28/C21 code/styled dirty-row reuse with actual semantic workers."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
from bindings import verify
from overlays import wrap
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
BASE=ROOT/'build/geos-incremental-editor/20261025T094258320916Z/fixture'

def run(out,base,smoke=False):
 frozen=out/'fixture';shutil.copytree(base,frozen)
 spec=importlib.util.spec_from_file_location('edit_class_build',ROOT/'src/render/geos/edit-class-candidate/build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);sizes=m.build(out/'leaves',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen
 names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True);frames=[]
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)}
 def install(x,seo):
  slot,ident=seo[5:7]
  for i in range(x.s['se_overlay_capacity']):
   if x.m.read(x.s['se_overlay_ids']+i)==ident and x.m.read(x.s['image_slot']+i)==slot:x.m.write(x.s['se_overlay_ids']+i,0)
  x.m.write(x.s['se_overlay_active']+slot,0);x.m.load(x.s['se_overlay_header'],seo[:36]);x.m.load(0x5000,seo[36:]);assert not x.call('se_overlay_import').p&1
 def setup(data,at):
  for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
  install(g,(out/'leaves/page.seo').read_bytes());install(g,(out/'leaves/delta.seo').read_bytes())
 def check(tag,data,at,byte,accepted=True):
  setup(data,at)
  for x in(f,g):x.key(byte)
  assert g.m.read(0xcfe8)==1,(tag,'C6witness')
  before=[x.canonical()for x in(f,g)];reu=g.reu();counts=[]
  for x in(f,g):
   n=x.total_instructions;x.render();counts.append(x.total_instructions-n)
  assert g.m.read(0x9148)==(2 if accepted else 0),(tag,'path',g.m.read(0x9148),g.read(0x9149,47).hex())
  assert f.merged()==g.merged() and f.canonical()==before[0] and g.canonical()==before[1],(tag,'source/history/clip')
  pixels,attrs,_,_=semantic.expected(g,g.merged(),fonts)
  actual=g.read(0x6000,8000);colors=g.read(0x4000,1000)
  if actual!=pixels or colors!=attrs:
   (out/(tag+'-actual.bin')).write_bytes(actual+colors);(out/(tag+'-expected.bin')).write_bytes(pixels+attrs)
  assert actual==f.read(0x6000,8000)==pixels,(tag,'pixels',[(i,a,b)for i,(a,b)in enumerate(zip(actual,pixels))if a!=b][:16])
  assert colors==f.read(0x4000,1000)==attrs,(tag,'attributes')
  fc,fb=f.raw_cache();gc,gb=g.raw_cache();assert fc[:64]==gc[:64],(tag,'header')
  for row in range(fc[1]):
   a=0x200+row*0x800;assert fc[a:a+842]==gc[a:a+842],(tag,'packet',row,[(i,a,b)for i,(a,b)in enumerate(zip(fc[a:a+842],gc[a:a+842]))if a!=b][:16])
  # Only the owned FE cache may change during derived rendering; every other
  # source/history/clipboard/overlay allocation remains byte exact.
  now=g.reu();p=gb*65536;assert now[:p]==reu[:p] and now[p+65536:]==reu[p+65536:]
  assert not any(g.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job']) and g.read(0xc600,1024)==g.shim
  fold.geos.png(actual,colors,out/(tag+'.png'));item=dict(tag=tag,accepted=accepted,baseline_instructions=counts[0],candidate_instructions=counts[1],reduction=1-counts[1]/counts[0],first_strip=g.m.read(0x914e),end_strip=g.m.read(0x914f));frames.append(item);print('PASS',item,flush=True)
 try:
  basic=fold.geos.native_text('Intro.\r:::basic\r10 PRINT "HELLO":REM KEEP\r20 GOTO 10\r:::\rTail.\r')
  asm=fold.geos.native_text('Intro.\r:::asm\rstart: lda #$2A ; comment\rnext: sta $D020\r:::\rTail.\r')
  styled=fold.geos.native_text('Intro.\rPlain **bold words** and *italic*.\rFollowing row.\rTail.\r')
  check('basic-string',basic,basic.index(fold.geos.native_text('HELLO'))+2,fold.geos.native_text('X')[0])
  check('asm-comment',asm,asm.index(fold.geos.native_text('comment'))+3,fold.geos.native_text('i')[0])
  check('bold-interior',styled,styled.index(fold.geos.native_text('bold'))+2,fold.geos.native_text('X')[0])
  if not smoke:
   check('basic-delete-string',basic,basic.index(fold.geos.native_text('HELLO'))+3,0x14)
   check('asm-delete-comment',asm,asm.index(fold.geos.native_text('comment'))+4,0x14)
   check('italic-interior',styled,styled.index(fold.geos.native_text('italic'))+2,fold.geos.native_text('q')[0])
   check('unmatched-inline',fold.geos.native_text('Intro.\rPlain **unmatched tail.\rFollowing.\r'),16,fold.geos.native_text('Q')[0])
   # Deleting the ordinary X completes a closing fence. New kind/height must
   # refuse the transaction, then full parsing reclassifies the following row.
   closing=fold.geos.native_text('Intro.\r:::basic\r:::X\r10 PRINT 1\r:::\rTail.')
   check('code-closure-reinterpretation',closing,closing.index(fold.geos.native_text('X'))+1,0x14,False)
  # Parent promotion adds the explicit carry refusal. Build that exact extra
  # branch in a disposable cloned source; released candidate files stay intact.
  prod=out/'leaves/production';src=prod/'src/render/geos/edit-class-candidate/edit-cache.s';text=src.read_text();needle=' adc GEX_HEIGHT\n cmp #193';assert text.count(needle)==1;src.write_text(text.replace(needle,' adc GEX_HEIGHT\n jcs miss\n cmp #193'))
  obj=out/'leaves/delta-hardened.o';subprocess.run(['ca65','-g','-I',str(out/'leaves'),'-I',str(prod/'src'),'-o',str(obj),str(src)],cwd=ROOT,check=True)
  target=out/'leaves/delta-hardened.bin';subprocess.run(['ld65','-C',str(prod/'cfg/overlay-r.cfg'),'-o',str(target),str(obj),str(out/'leaves/cache-delta.o'),str(out/'leaves/delta-aliases.o')],cwd=ROOT,check=True)
  seal=verify(frozen/'build/editor.prg',frozen/'build/editor.lbl')['digest'];hard=wrap(target.read_bytes(),0,28,api=(g.s['se_overlay_call'],g.s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/'leaves/delta-hardened.seo').write_bytes(hard)
  setup(basic,basic.index(fold.geos.native_text('HELLO'))+2);g.key(fold.geos.native_text('X')[0]);install(g,hard);cache,bank=g.raw_cache();row=cache[42]
  offset=0x200+row*0x800+15;g.m.load(0x8080,b'\xf8');g.put('se_reu_logical',g.get('se_gc_handle',1),1);g.put('se_reu_offset',offset,2);g.put('se_reu_c64',0x8080,2);g.put('se_reu_length',1,2);assert not g.call('se_reu_copy',0).p&1
  canonical=g.canonical();reu=g.reu();pixels=g.read(0x6000,8000);attrs=g.read(0x4000,1000);g.put('se_f_owner',4,1);g.m.write(g.s['se_overlay_frame'],0);r,n=g.fast_call(g.s['se_overlay_call'],a=28,x=0)
  assert r.a==2 and not r.p&1 and g.get('se_f_owner',1)==4 and g.canonical()==canonical and g.reu()==reu and g.read(0x6000,8000)==pixels and g.read(0x4000,1000)==attrs and g.m.read(0x9149)==0,('malformedTOP248',r.a,r.p)
  g.put('se_f_owner',0,1);g.render();eb,ea,_,_=semantic.expected(g,g.merged(),fonts);assert g.read(0x6000,8000)==eb and g.read(0x4000,1000)==ea
  fault=dict(tag='parent-promotedTOP248-carry-refusal',R28_bytes=len(target.read_bytes()),instructions=n,REU_writes=0,source_changes=0)
  print('FAULT',fault,flush=True)
  result=dict(status='passed',sizes=sizes,fault=fault,frames=frames,scope='Private actual packaged root with R28/C21 replacements, real C24/C20/C25/C26. Whole source/history/otherREU/shim and independent allpixels/full-producer packets. CPU counts only.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-c64.bin').write_bytes(g.read(0,65536));(out/'failure-reu.bin').write_bytes(g.reu());raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-edit-class-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)
