"""Private actual C26 adaptive gate; old parser/control byte-identity first."""
from pathlib import Path
import sys,json,zipfile,hashlib
sys.path[:0]=['tests','tools']
from test_cache_query import command
from overlays import wrap
ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent

def build(out,base):
 out.mkdir();tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')and not name.endswith('/'):
    p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols'];digest=r['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 (out/'state.s').write_text('.export se_bc_flags,se_bc_count\nse_bc_flags=$9FC2\nse_bc_count=$9FC5\n');command('ca65','-o',out/'state.o',out/'state.s')
 def link(tag,adaptive=False):
  d=out/tag;d.mkdir();objs=[]
  for name,source in [('controller',tree/'src/render/geos/inline.s'),('parser',tree/'src/supermark/inline.s')]:
   obj=d/(name+'.o');command('ca65','-g','-I',out,'-I',tree/'src','-I',HERE,*(['-D','SE_EDITOR_CACHED_INLINE_SOURCE=1']if adaptive else[]),'-o',obj,source);objs.append(obj)
  objs.append(out/'state.o');command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objs);command('ca65','-o',d/'aliases.o',d/'aliases.s');objs.append(d/'aliases.o')
  (d/'image.cfg').write_text('MEMORY { IMAGE:file=%O,start=$B000,size=$1000,type=rw; PHASE:file="",start=$8D00,size=$01E0,type=rw; } SEGMENTS { GEOS_INLINE:load=IMAGE,type=ro; SM_INLINE:load=IMAGE,type=ro; SM_STATE:load=PHASE,type=bss,define=yes; }')
  command('ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objs);raw=(d/'image.bin').read_bytes();assert len(raw)<=4096
  image=wrap(raw,1,26,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'image.seo').write_bytes(image);return image
 control=link('control');assert control==(base/'build/overlays/geosinln.seo').read_bytes(),'actualC26controlnotbyteidentical'
 p=tree/'src/render/geos/inline.s';t=p.read_text();t=t.replace(' cmp #GI_SOURCE_BEGIN\n','.ifdef SE_EDITOR_CACHED_INLINE_SOURCE\n cmp #GI_SOURCE_FALLBACK ;never re-delegates\n jeq source_legacy\n.endif\n cmp #GI_SOURCE_BEGIN\n',1)
 t=t.replace('source_begin:\n ldx #1','source_begin:\n.ifdef SE_EDITOR_CACHED_INLINE_SOURCE\n.include "gate.inc"\nsource_legacy:\n.endif\n ldx #1',1);t=t.replace('.import se_f_owner,','.ifdef SE_EDITOR_CACHED_INLINE_SOURCE\n.import se_bc_flags,se_bc_count\n.endif\n.import se_f_owner,',1);t=t.replace('.include "render/geos/inline.inc"','.include "render/geos/inline.inc"\n.include "adaptive-api.inc"',1);p.write_text(t)
 default=link('default-after');assert default==control,'flagabsentC26changed'
 candidate=link('candidate',True);print('C26',len(control)-36,'→',len(candidate)-36,flush=True);return candidate
