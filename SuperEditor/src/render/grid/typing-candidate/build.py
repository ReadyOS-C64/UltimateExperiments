"""Private exact C33/R25 factoring; no canonical source/build mutation."""
from pathlib import Path
import sys,json,subprocess,re,hashlib
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap
HELPERS=['admit','fields','header_crc','store_header','fetch_header','fetch_row','row_request','packet_crc','verify_row','bounds','retreat','row_bit']
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];seal=verify(base/'build/editor.prg',base/'build/editor.lbl');digest=seal['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 source=(ROOT/'src/render/grid/caret/caret.s').read_text();prefix=source[:source.index('.segment "CODE"')];start=source.index('.import se_overlay_capacity');end=source.index('locate:');shared=source[start:end]
 wrappers='invalid:\n sec\n rts\n'
 for i,name in enumerate(HELPERS):
  wrappers+=name+':\n'
  if name=='fetch_row':wrappers+=' sta PTR\n stx PTR+1\n'
  wrappers+=f' lda #{i+2}\n jmp helper\n'
 wrappers+='helper:\n sta se_overlay_frame\n ldx #0\n@find:\n lda se_overlay_ids,x\n cmp #25\n bne @next\n lda image_slot,x\n and #1\n beq @found\n@next:\n inx\n cpx #64\n bcc @find\n sec\n rts\n@found:\n lda image_size_lo,x\n cmp #<HELPER_SIZE\n bne @miss\n lda image_size_hi,x\n cmp #>HELPER_SIZE\n bne @miss\n lda image_crc_lo,x\n cmp #<HELPER_CRC\n bne @miss\n lda image_crc_hi,x\n cmp #>HELPER_CRC\n bne @miss\n lda #25\n ldx #0\n jmp se_overlay_call\n@miss:\n sec\n rts\n'
 wrappers='.include "helper-witness.inc"\n'+wrappers
 caret=source[:start]+wrappers+source[end:]
 caret=caret.replace(' jsr admit\n jcs miss',' lda #0\n sta C+63\n lda OP\n beq :+\n ldx #3\n@typed_revision:\n lda se_r_revision,x\n cmp se_l_revision,x\n jne type_try\n dex\n bpl @typed_revision\n:\n jsr admit\n jcs miss',1)
 caret+='\n.segment "CODE"\n'+(D/'caller.s').read_text()
 # Catalog is immutable during one uninterrupted foreground C33 operation.
 # Authenticate the helper once, not once per bounded row-CRC call.
 caret=caret.replace('helper:\n sta se_overlay_frame\n ldx #0', 'helper:\n sta se_overlay_frame\n lda #25\n ldx #0\n jmp se_overlay_call\nauthenticate_helper:\n ldx #0')
 caret=caret.replace(' lda #25\n ldx #0\n jmp se_overlay_call\n@miss:', ' clc\n rts\n@miss:')
 caret=caret.replace(' sta se_f_owner\n lda #0\n sta C+63', ' sta se_f_owner\n jsr authenticate_helper\n jcs miss\n lda #0\n sta C+63',1)
 (out/'caret.s').write_text(caret)
 # Existing R25 policy is retained and dispatcher expanded only after op1.
 tail=(ROOT/'src/render/geos/tail-entry.s').read_text();tail=tail[tail.index('S=GPP_STATE'):];tail=tail.replace('.segment "CODE"\n OVL_BINDING\n.export entry\nentry:', '.segment "CODE"\n OVL_BINDING\n.export entry\nentry:')
 tail=tail.replace(' lda se_overlay_frame\n jne selection_bounds', ' lda se_overlay_frame\n cmp #2\n bcc original\n jmp helpers\noriginal:\n cmp #0\n jne selection_bounds')
 dispatch='helpers:\n'
 for i,name in enumerate(HELPERS):
  dispatch+=f' cmp #{i+2}\n bne :+\n'
  if name=='fetch_row':dispatch+=' lda PTR\n ldx PTR+1\n'
  dispatch+=f' jmp {name}\n:\n'
 dispatch+=' cmp #14\n jeq type_prepare\n cmp #15\n jeq type_commit\n'
 dispatch+=' lda #$90\n sec\n rts\n'
 shared=shared.replace(' ldx #3\n@revision:', ' lda C+63\n bne @revision_done\n ldx #3\n@revision:').replace(' ldx #1\n@generation:', '@revision_done:\n ldx #1\n@generation:')
 shared=shared.replace('@compare:\n lda (text_ptr),y', '@compare:\n lda C+63\n beq @read\n cpy #N_KEY+17\n bcc @read\n cpy #N_KEY+24\n bcc @skip\n cpy #N_PENDING\n beq @skip\n cpy #N_HOTLEN\n beq @skip\n cpy #N_HOTLEN+1\n beq @skip\n@read:\n lda (text_ptr),y').replace(' cmp H,y\n jne invalid\n iny', ' cmp H,y\n jne invalid\n@skip:\n iny')
 helper=prefix.replace('.include "document/math24.inc"\n','')+'.include "render/geos/editor.inc"\n.include "render/geos/page-paint.inc"\n'+tail+'\n'+dispatch+shared+'\n.segment "CODE"\n'+(D/'typing.s').read_text()+'\n.segment "RODATA"\nbits:.byte 1,2,4,8,16,32,64,128\n'
 (out/'helper.s').write_text(helper)
 results={};seos={}
 for name,paths,slot,ident in [('geostail',[out/'helper.s'],0,25),('grid',[out/'caret.s',ROOT/'src/render/geos/typing/status-normal.s'],1,33)]:
  objs=[]
  for j,path in enumerate(paths):
   o=out/(name+str(j)+'.o');subprocess.run(['ca65','-g','-I',out,'-I',ROOT/'src/render/grid/caret','-I',ROOT/'src','-o',o,path],check=True);objs.append(o)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True)
  a=out/(name+'-aliases.o');subprocess.run(['ca65','-o',a,out/(name+'-aliases.s')],check=True);objs.append(a)
  cfg=out/(name+'.cfg');cfg.write_text('MEMORY {IMAGE:file=%O,start=$'+('B000'if slot else'A000')+',size=$1000,type=ro;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
  subprocess.run(['ld65','-C',cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs],check=True)
  raw=(out/(name+'.bin')).read_bytes();
  if name=='geostail':
   import binascii
   (out/'helper-witness.inc').write_text('HELPER_SIZE='+str(len(raw))+'\nHELPER_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
  seo=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);seos[name]=seo;results[name]=dict(payload=len(raw),sha256=hashlib.sha256(seo).hexdigest())
 (out/'budget.json').write_text(json.dumps(results,indent=2)+'\n');return seos,results
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2]))[1])
