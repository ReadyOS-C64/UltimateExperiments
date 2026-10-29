"""Private frozen C37 hint build. No main sources or outputs are written."""
from pathlib import Path
import sys,json,zipfile,subprocess,re,difflib,hashlib
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
FLAGS=['BCQ_EDITOR_ACTIVE=1','BCQ_CLASSIFY=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_PAGE_REUSE=1','BCQ_FORWARD_SEED=1','BCQ_FORWARD_QUERY=1']
OLD=' inc F+GSEM_INLINE           ;hint only, no INLINE grammar reuse certificate\n@not_inline:'
NEW=''' ; Only a completed, canonical empty INLINE certificate proves no work.
 lda BQ_CR+2
 and #4
 beq @has_inline
 lda BQ_CR+44
 ora BQ_CR+45
 ora BQ_CR+46
 bne @has_inline
 lda BQ_CR+40
 and BQ_CR+41
 and BQ_CR+42
 and BQ_CR+43
 cmp #$FF
 beq @inline_done
@has_inline:
 inc F+GSEM_INLINE
@inline_done:
 lda F+GSEM_KIND
@not_inline:'''
GUARDED='.ifdef BCQ_EMPTY_INLINE_HINT\n'+NEW.removesuffix('@not_inline:')+'.else\n'+OLD.removesuffix('@not_inline:')+'.endif\n@not_inline:'

def command(a):
 r=subprocess.run(list(map(str,a)),cwd=ROOT,text=True,capture_output=True);assert not r.returncode,(a,r.stdout,r.stderr);return r.stdout

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);project=out/'project';z=zipfile.ZipFile(base/'product-sources.zip')
 for n in z.namelist():
  if n.startswith('src/')and n.endswith(('.inc','.s')):
   p=project/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 source=z.read('src/cache/query/fast-entry.s').decode();assert source.count(OLD)==1
 r=json.loads((base/'build/editor-report.json').read_text());digest=r['resident_binding']['digest'];s=r['symbols'];results={}
 for variant in ('baseline','guarded-off','hint'):
  d=out/variant;d.mkdir();(d/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  (d/'fast-entry.s').write_text(source if variant=='baseline'else source.replace(OLD,GUARDED));objects=[]
  files=[(d/'fast-entry.s',FLAGS+(['BCQ_EMPTY_INLINE_HINT=1']if variant=='hint'else[]))]+[(project/'src/cache/query'/(n+'.s'),FLAGS)for n in ('query','source','records')]+[(project/'src/cache/arena'/(n+'.s'),['BCA_READONLY_OPEN=1'])for n in ('core','page')]
  for i,(path,flags)in enumerate(files):
   obj=d/(str(i)+'.o');command(['ca65','-g','-I',d,'-I',project/'src',*[v for flag in flags for v in ('-D',flag)],'-o',obj,path]);objects.append(obj)
  command([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects]);command(['ca65','-o',d/'aliases.o',d/'aliases.s']);objects.append(d/'aliases.o')
  (d/'image.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }')
  command(['ld65','-C',d/'image.cfg','-o',d/'page.bin','-Ln',d/'page.lbl','-m',d/'page.map',*objects]);raw=(d/'page.bin').read_bytes();im=wrap(raw,1,37,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'page.seo').write_bytes(im);results[variant]=dict(bytes=len(raw),sha256=hashlib.sha256(im).hexdigest())
 assert(out/'guarded-off/page.seo').read_bytes()==(out/'baseline/page.seo').read_bytes(),'default-off guarded image differs'
 assert(out/'baseline/page.seo').read_bytes()==(base/'build/overlays/page.seo').read_bytes(),'baseline C37 reassembly differs'
 # Measure the identical source predicate's C35 object cost, without linking an oversized image.
 c35=z.read('src/cache/query/classify-entry.s').decode();assert c35.count(OLD)==1
 for variant in ('baseline','hint'):
  d=out/variant;(d/'classify-entry.s').write_text(c35 if variant=='baseline'else c35.replace(OLD,NEW))
  command(['ca65','-I',d,'-I',project/'src',*[v for flag in FLAGS[:-1]for v in ('-D',flag)],'-o',d/'classify.o',d/'classify-entry.s'])
  dump=command(['od65','--dump-segments',d/'classify.o']);results[variant]['C35_selector_CODE']=int(re.search(r'Name:\s+"CODE".*?Size:\s+(\d+)',dump,re.S)[1])
 added=results['hint']['C35_selector_CODE']-results['baseline']['C35_selector_CODE'];results['C35_proposed_total']=len((base/'build/overlays/inln.seo').read_bytes())-36+added
 results.update(added_bytes=results['hint']['bytes']-results['baseline']['bytes'],new_BSS=0,new_ZP=0)
 (out/'ready.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),source.replace(OLD,GUARDED).splitlines(True),fromfile='a/src/cache/query/fast-entry.s',tofile='b/src/cache/query/fast-entry.s')))
 (out/'guarded-fast-entry.s').write_text(source.replace(OLD,GUARDED))
 (out/'budget.json').write_text(json.dumps(results,indent=2)+'\n');print('FIT',results,flush=True);return results
