"""Private C24 baseline reproduction + pure incoming-checkpoint codec fit."""
from pathlib import Path
import binascii,json,re,sys,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 shutil.copytree(D,src/'src/render/geos/semantic-consumer-candidate',dirs_exist_ok=True)
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def cmd(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 result={}
 for name in ['control','codec','seed']:
  d=out/name;d.mkdir();objects=[]
  sources=['src/render/geos/semantic.s','src/supermark/block.s']+(['src/render/geos/semantic-consumer-candidate/codec.s']if name!='control'else[])
  if name=='seed':
   original=(src/'src/render/geos/semantic.s').read_text()
   candidate=original.replace(' cmp #GSEM_CANCEL',' cmp #3\n jeq gsc_begin\n cmp #GSEM_CANCEL',1)
   candidate=candidate.replace('begin:\n','begin:\n lda #0\n sta GSC_TRY\n jmp gsc_begin_common\ngsc_begin:\n lda GSC_SELECTOR\n cmp #2\n jcs argument\n lda #1\n sta GSC_TRY\ngsc_begin_common:\n',1)
   candidate=candidate.replace(' sta F+GSEM_ACTIVE\n sta F+GSEM_ERROR',' sta F+GSEM_ACTIVE\n sta GSC_CAPTURED\n sta GSC_PROOF\n sta GSC_PREVIOUS_VALID\n sta F+GSEM_ERROR',1)
   candidate=candidate.replace('@valid:\n lda #1','@valid:\n lda GSC_TRY\n jne gsc_try\n lda #1',1)
   candidate=candidate.replace(' cmp #1\n jne restart\n lda se_l_mode',' cmp #1\n beq :+\n cmp #2\n jne restart\n: lda se_l_mode',1)
   candidate=candidate.replace(' CMP24 F+GSEM_QUERY,F+GSEM_CP_QUERY',' lda F+GSEM_CP_VALID\n cmp #2\n jeq gsc_restore_seed\n CMP24 F+GSEM_QUERY,F+GSEM_CP_QUERY',1)
   candidate=candidate.replace('@later:\n','@later:\n',1).replace(' ldx #78\n@restore:', 'gsc_restore_seed:\n CMP24 F+GSEM_QUERY,F+GSEM_CP_NEXT\n jcc restart\n ldx #78\n@restore:',1)
   # gsc_restore_seed is a new global scope; @later/@restore are local to it.
   candidate=candidate.replace(' bcc @later',' bcc gsc_later').replace('@later:\n','gsc_later:\n')
   candidate=candidate.replace(' lda GS_PACKET,x\n jsr se_sm_feed',' lda GS_PACKET,x\n cmp #13\n bne @gsc_literal\n jsr gsc_boundary\n lda #13\n@gsc_literal:\n jsr se_sm_feed',1)
   candidate=candidate.replace('eof:\n jsr se_sm_finish','eof:\n jsr gsc_incoming\n jsr se_sm_finish',1)
   candidate=candidate.replace('.include "render/geos/preview-handoff.inc"','.include "render/geos/semantic-consumer-candidate/seed.inc"\n.include "render/geos/preview-handoff.inc"')
   candidate=candidate.replace('.include "editor-api.inc"','.include "editor-api.inc"\n.include "render/geos/semantic-consumer-candidate/codec.inc"',1)
   (d/'semantic-seed.s').write_text(candidate);sources[0]=str(d/'semantic-seed.s')

  for i,source in enumerate(sources):
   p=d/(str(i)+'.o');cmd('ca65','-g',*(['-D','GSC_RESTORE_ONLY=1']if name=='seed'else[]),'-I',out,'-I',src/'src','-o',p,src/source);objects.append(p)
  cmd(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects);cmd('ca65','-o',d/'aliases.o',d/'aliases.s');cmd('ld65','-C',src/'cfg/geos-editor-semantic.cfg','-o',d/'geossema.bin','-Ln',d/'geossema.lbl','-m',d/'geossema.map',*objects,d/'aliases.o')
  raw=(d/'geossema.bin').read_bytes();seo=wrap(raw,1,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'geossema.seo').write_bytes(seo)
  if name=='control':assert seo==(base/'build/overlays/geossema.seo').read_bytes(),'C24control differs fromactualfreeze'
  result[name]=dict(bytes=len(raw),CODECadded=len(raw)-2781)
 # Exact code identity gates the optional op3 and derived metadata producer.
 seedraw=(out/'seed/geossema.bin').read_bytes()
 (out/'consumer-witness.inc').write_text('GSC_SEED_SIZE='+str(len(seedraw))+'\nGSC_SEED_CRC='+str(binascii.crc_hqx(seedraw,65535))+'\n')
 # A separate actual C21 link proves the producer fits without new state/slot.
 d=out/'producer';d.mkdir();page=(src/'src/render/geos/page.s').read_text()
 page=page.replace('    sta se_f_owner\n    lda #0','    sta se_f_owner\n    lda GEC_VALID\n    sta GSC_ALLOW_EDIT\n    lda #0',1)
 page=page.replace('classified:\n','classified:\n',1).replace('@ready:\n    lda #0','@ready:\n    jsr gsc_publish\n    lda #0',1)
 page=page.replace('    cmp #6\n    jeq classified','    cmp #13\n    jeq gsc_seed_done\n    cmp #6\n    jeq classified',1)
 needle='    lda #6\n    sta PS\n    lda #GSEM_ID\n    ldx #GSEM_BEGIN\n    jmp request\nclassified:'
 replacement='''    lda GSEM_FRAME+GSEM_CP_VALID
    bne gsc_classify_direct
    jsr gsc_cap
    bcs gsc_classify_direct
    lda #0
    sta GSC_SELECTOR
    lda #13
    sta PS
    lda #GSEM_ID
    ldx #3
    jmp request
gsc_seed_done:
    lda GSC_PROOF
    bne gsc_classify_direct
    lda GSC_SELECTOR
    bne gsc_classify_direct
    inc GSC_SELECTOR
    lda #GSEM_ID
    ldx #3
    jmp request
gsc_classify_direct:
    lda #6
    sta PS
    lda #GSEM_ID
    ldx #GSEM_BEGIN
    jmp request
classified:'''
 assert needle in page
 page=page.replace(needle,replacement,1)
 page+='\n.include "render/geos/semantic-consumer-candidate/publish.inc"\n'
 # Absolute input symbols must be known before the first instruction.
 page=page.replace('.include "editor-api.inc"','.include "editor-api.inc"\n.include "render/geos/semantic-consumer-candidate/codec.inc"',1)
 page+='\n.include \"render/geos/semantic-consumer-candidate/consumer.inc\"\n'
 (d/'page.s').write_text(page);objects=[]
 for i,source in enumerate([d/'page.s',src/'src/render/geos/cache.s']):
  p=d/(str(i)+'.o');cmd('ca65','-g','-I',out,'-I',src/'src','-o',p,source);objects.append(p)
 cmd(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects);cmd('ca65','-o',d/'aliases.o',d/'aliases.s');cmd('ld65','-C',src/'cfg/geos-editor-page.cfg','-o',d/'geospage.bin','-Ln',d/'geospage.lbl','-m',d/'geospage.map',*objects,d/'aliases.o')
 raw=(d/'geospage.bin').read_bytes();seo=wrap(raw,1,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'geospage.seo').write_bytes(seo);result['producer']=dict(bytes=len(raw))
 # Require the original C21 and its cache object to reproduce as well.
 d=out/'page-control';d.mkdir();objects=[]
 for i,source in enumerate([src/'src/render/geos/page.s',src/'src/render/geos/cache.s']):
  p=d/(str(i)+'.o');cmd('ca65','-g','-I',out,'-I',src/'src','-o',p,source);objects.append(p)
 cmd(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects);cmd('ca65','-o',d/'aliases.o',d/'aliases.s');cmd('ld65','-C',src/'cfg/geos-editor-page.cfg','-o',d/'geospage.bin','-Ln',d/'geospage.lbl','-m',d/'geospage.map',*objects,d/'aliases.o')
 raw=(d/'geospage.bin').read_bytes();seo=wrap(raw,1,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'geospage.seo').write_bytes(seo);assert seo==(base/'build/overlays/geospage.seo').read_bytes(),'C21control differs fromactualfreeze';result['page-control']=dict(bytes=len(raw))
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
