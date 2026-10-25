"""Private complete resident+48assets build, never writes canonical products."""
from pathlib import Path
import argparse,json,hashlib,shutil,subprocess,sys,zipfile,os
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'
PLAN='''
; Pure source-grid layout admission, moved verbatim from resident preflight.
; Called only after resident se_ef_prepare; no buffer/phase/C nesting.
se_grid_plan:
 lda se_ef_valid
 beq @ordinary
 lda se_l_valid
 beq @start
 ldx #1
@fold_generation:
 lda se_ef_generation,x
 cmp se_ef_projection_generation,x
 bne @start
 dex
 bpl @fold_generation
 CMP24 se_hot_caret,se_l_caret
 bne @start
 CMP24 se_v_top,se_l_top
 bne @start
@ordinary:
 lda se_l_mode
 bne @context
 lda se_l_need_wrap
 beq @ready
@start:
 lda #1
 clc
 rts
@context:
 lda #2
 clc
 rts
@ready:
 lda #0
 clc
 rts
'''
def change(p,old,new):
 s=p.read_text();assert old in s,(str(p),old[:90]);p.write_text(s.replace(old,new,1))
def prepare(out,base=BASE):
 work=out/'tree';work.mkdir(parents=True);(work/'build/overlays').mkdir(parents=True)
 with zipfile.ZipFile(base/'product-sources.zip') as z:z.extractall(work)
 for p in (ROOT/'src').rglob('*.py'):
  q=work/p.relative_to(ROOT)
  if not q.exists():q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 for name in ['tools','config']:
  shutil.copytree(ROOT/name,work/name,ignore=shutil.ignore_patterns('__pycache__'))
 shutil.copytree(ROOT/'assets/fonts',work/'assets/fonts')
 shutil.copytree(ROOT/'build/geos-font-catalog',work/'build/geos-font-catalog')
 shutil.copytree(ROOT/'src/render/grid/caret-candidate',work/'src/render/grid/caret-candidate',ignore=shutil.ignore_patterns('integration','__pycache__'),dirs_exist_ok=True)
 p=work/'src/render/grid/caret-candidate/caret.s'
 change(p,' lda se_overlay_frame\n cmp #2',' lda se_overlay_frame\n cmp #2\n bne :+\n jmp se_grid_plan\n:\n cmp #2')
 with p.open('a') as f:f.write('\n.segment "CODE"\n.import se_l_caret\n'+PLAN)
 p=work/'src/layout/dispatch.s';s=p.read_text();start=s.index('    lda se_ef_valid\n');end=s.index('@start:\n',start)
 s=s[:start]+'''    ; Keep the common source40/wrapped-ready predicate resident: no C load.
    lda se_ef_valid
    bne @folded
    lda se_l_mode
    bne @no_wrap
    lda se_l_need_wrap
    beq ready
    bne @start
@folded:
    lda #2 ;pure fold/layout decision, no phase/private scratch access
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
    bcs failed
    lsr ;private C33 returns only0ready/1start/2context
    bcs @start
    beq ready
@no_wrap:
    lda #A_LAYOUT_CONTEXT
    sta se_overlay_frame
    lda #AUX_ID
    ldx #1
    jsr se_overlay_call
    bcs failed
    tax
    beq ready
'''+s[end:];p.write_text(s.replace('    cmp #1\n    beq @queued','    tax ;se_ef_prepare returns only0ready/1queued\n    bne @queued'))
 p=work/'src/editor/main.s'
 change(p,':\n    jsr se_layout_prepare\n', ''':
    tax
    beq @ordinary
    lda #1
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
    bcs @ordinary
    tax
    bne @ordinary
    sta se_e_redraw
    jmp se_er_publish_only
@ordinary:
    jsr se_layout_prepare
''')
 change(p,'se_er_published:\n    inc se_e_draw_sequence', '''se_er_published:
    jsr se_er_publish_only
    ldx se_mode
    beq @done
    cpx #3
    bcs @done
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
@done:
    lda #0
    clc
    rts
se_er_publish_only:
    inc se_e_draw_sequence''')
 p=work/'src/editor/startup.s';change(p,'cpx #47','cpx #48');change(p,'failure_hint: .asciiz "Disk / REU?"','failure_hint: .asciiz "Disk/REU?"');change(p,'file46=file43+1','file47=file15 ;GRID shares the existing GRIDEDIT prefix\nfile46=file43+1')
 s=p.read_text().replace(',<file46\n',',<file46,<file47\n').replace(',>file46\n',',>file46,>file47\n').replace(',5,5,4,4,4\n',',5,5,4,4,4,4\n');p.write_text(s)
 p=work/'Makefile';s=p.read_text();s+='''
# Private C33 complete build only.
build/overlays/grid.seo: build/editor.prg src/render/grid/caret-candidate/caret.s
	$(PYTHON) src/render/grid/caret-candidate/build.py build/grid-caret $(CURDIR)
	cp build/grid-caret/gridcaret.seo $@
editor: build/overlays/grid.seo
''';p.write_text(s)
 return work

def build(out,base=BASE):
 work=prepare(out,base);env=dict(os.environ,GEOS_BSW_SOURCE=str(ROOT.parent.parent/'GEOS20/reference/geos/kernal/bswfont/bswfont.s'))
 with (out/'build.log').open('w') as f:subprocess.run(['make','-j1','editor'],cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 identity=json.loads((base/'freeze.json').read_text());identity['names'].append('grid');identity['assets']={n:hashlib.sha256((work/f'build/overlays/{n}.seo').read_bytes()).hexdigest() for n in identity['names']};identity['prg_sha256']=identity['resident_sha256']=hashlib.sha256((work/'build/editor.prg').read_bytes()).hexdigest()
 frozen=out/'fixture';shutil.copytree(base,frozen)
 for n in ['editor.prg','editor.lbl','editor.map','editor-report.json','editor-binding.json']:
  if (work/'build'/n).exists():shutil.copy2(work/'build'/n,frozen/'build'/n)
 for n in identity['names']:shutil.copy2(work/f'build/overlays/{n}.seo',frozen/f'build/overlays/{n}.seo')
 identity['private_unpacked_48']=True;identity['source_fixture']=str(base);identity['integration_source_hashes']={str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [work/'src/editor/main.s',work/'src/editor/startup.s',work/'src/layout/dispatch.s',work/'src/render/grid/caret-candidate/caret.s',work/'Makefile']}
 with zipfile.ZipFile(frozen/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in [work/'Makefile',*sorted((work/'src').rglob('*')),*sorted((work/'cfg').rglob('*'))]:
   if p.is_file() and (p.name=='Makefile' or p.suffix in ('.s','.inc','.cfg','.py')):z.write(p,p.relative_to(work))
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');return frozen,identity
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);print(build(a.out,a.base)[0])
