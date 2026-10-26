"""Private source-matched C22 cell-visibility fix; no shared output writes."""
from pathlib import Path
import sys,json,zipfile,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(ROOT/'tools')]
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);tree=out/'source';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(tree)
 report=json.loads((base/'build/editor-report.json').read_text())
 subprocess.run([sys.executable,tree/'src/fold/editor-leaves/binding.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc'],check=True)
 original=tree/'src/render/geos/page-paint.s';text=original.read_text()
 needle='''caret_line:
    lda GPP_LINE
    cmp GP_HEADER+GPH_CARET_ROW
    bne @no
    lda R+GPR_CARET_VALID'''
 assert text.count(needle)==1
 assert text.count('lda R+GPR_CARET_VALID')==2
 changed=text.replace('lda R+GPR_CARET_VALID','lda R+GPR_MEMBER')
 old='''    jsr caret_line
    jcc selected_tail
    lda R+GPR_CARET_X+1
    cmp #1
    bcc @tail
    jne selected_tail
    lda R+GPR_CARET_X
    cmp #64
    jcs selected_tail
@tail:
'''
 new='''    jsr caret_line
    jcc selected_tail
    ; A source boundary can be offscreen while its virtual cell intersects.
    ; TAIL_VALID authenticates the signed/clipped cell, not a clamped point.
    lda R+GPR_TAIL_VALID
    jeq selected_tail
@tail:
'''
 assert changed.count(old)==1;changed=changed.replace(old,new)
 candidate=out/'page-paint-clipped.s';candidate.write_text(changed)
 def compile(tag,body):
  d=out/tag;d.mkdir();objs=[]
  for i,p in enumerate([tree/'src/render/geos/page-paint-entry.s',body,tree/'src/render/geos/native-pan.s',tree/'src/render/geos/cache-paint.s']):
   o=d/(str(i)+'.o');subprocess.run(['ca65','-g','-I',str(out),'-I',str(tree/'src'),'-o',str(o),str(p)],check=True);objs.append(o)
  subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objs],check=True)
  subprocess.run(['ca65','-o',str(d/'aliases.o'),str(d/'aliases.s')],check=True);objs.append(d/'aliases.o')
  subprocess.run(['ld65','-C',str(tree/'cfg/geos-editor-page.cfg'),'-o',str(d/'image.bin'),'-Ln',str(d/'image.lbl'),'-m',str(d/'image.map'),*map(str,objs)],check=True)
  return (d/'image.bin').read_bytes()
 before=compile('original',original);assert before==(base/'build/overlays/geospaint.seo').read_bytes()[36:],'original C22 must source-match frozen capsule'
 after=compile('candidate',candidate);assert len(after)<=4096
 s=report['symbols'];image=wrap(after,1,22,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
 (out/'candidate/image.seo').write_bytes(image)
 result=dict(original_bytes=len(before),candidate_bytes=len(after),saving=len(before)-len(after),original_sha256=hashlib.sha256(before).hexdigest(),candidate_sha256=hashlib.sha256(after).hexdigest(),no_new_BSS=0,no_new_ZP=0,source_matched=True,patches=['caret_line uses authenticated logical row membership, not point visibility','virtual tail uses authenticated intersecting cell TAIL_VALID, not boundary point range'])
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return image,result
