"""Private coherent SP2 + bounded long-prose C33/R25 capsule. No shared writes."""
from pathlib import Path
import sys,json,subprocess,hashlib,shutil,binascii,importlib.util
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
BASE=ROOT/'build/geos-preflush-product/20261025T193429355750Z/fixture'
LEAF=ROOT/'build/grid-prose-authority/20261025T190208381544Z/leaf'
def module(name):
 spec=importlib.util.spec_from_file_location(name,D/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def build(out,base=BASE):
 out.mkdir(parents=True,exist_ok=True);products,budget=module('build-authority').build(out/'authority',base);module('build-status').build(out/'compact',base)
 for n in ['editor-api.inc','native-witness.inc','helper-witness.inc']:
  shutil.copy2((out/'compact'/n)if(out/'compact'/n).exists()else LEAF/n,out/n)
 for n in ['status-font.bin','status-lookup.bin']:shutil.copy2(out/'compact'/n,out/n)
 sy=json.load(open(base/'build/editor-report.json'))['symbols'];digest=json.load(open(base/'build/editor-report.json'))['resident_binding']['digest']
 h=(LEAF/'helper.s').read_text();h=h.replace(' cmp #15\n jeq type_commit',' cmp #15\n jeq type_commit\n cmp #16\n jeq type_long_prepare\n cmp #17\n jeq long_packet\n cmp #18\n jeq long_glyph')
 h=h.replace('type_prepare:\n lda #1\n sta TYPING','type_long_prepare:\n lda #2\n bne type_admission\ntype_prepare:\n lda #1\ntype_admission:\n sta TYPING')
 h=h.replace(' jsr sc_check\n jcs invalid\n SUB24',' jsr sc_check\n jcs invalid\n lda TYPING\n lsr\n bcs :+\n rts\n:\n SUB24')
 h=h.replace(' lda B+2\n cmp #1\n jne invalid',' lda B+2\n cmp #2\n jne invalid')
 h=h.replace('type_commit:\n','type_commit:\n lda TYPING\n lsr\n bcc long_commit\n')
 h=h.replace(' ; Rebase all later canonical anchors, including viewport bottom.','long_commit:\n lda TYPING\n lsr\n bcs :+\n lda LS_NOEND\n jne long_revision\n:\n ; Rebase all later canonical anchors, including viewport bottom.')
 h=h.replace(' sta COL\n@row:\n lda COL',' sta COL\n cmp #22\n bcs @bottom\n@row:\n lda COL')
 h=h.replace(' ; Bottom is a separate VIEW field.','@bottom:\n ; Bottom is a separate VIEW field.')
 h=h.replace(' ldx #3\n@rev:\n lda se_r_revision,x\n sta se_l_revision,x','long_revision:\n ldx #3\n@rev:\n lda se_r_revision,x\n sta se_l_revision,x')
 h=h.replace('.include "prose.inc"','.include "prose2.inc"\n.include "long.inc"');h=h.replace(' lda SIGN\n cmp #1\n beq @insertion',' lda SIGN\n bpl @insertion')
 h+='\n.segment "CODE"\n'+(D/'packet.s').read_text().replace('.include "long.inc"','');(out/'helper.s').write_text(h)
 def compile(name,items,cfg,slot,id):
  obs=[]
  for k,(p,defs) in enumerate(items):
   ob=out/(name+str(k)+'.o');cmd=['ca65','-g','-I',out,'-I',D,'-I',ROOT/'src/render/grid/caret','-I',ROOT/'src']
   for d in defs:cmd+=['-D',d]
   subprocess.run([*cmd,'-o',ob,p],check=True);obs.append(ob)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*obs],check=True);subprocess.run(['ca65','-o',out/(name+'-aliases.o'),out/(name+'-aliases.s')],check=True);(out/(name+'.cfg')).write_text(cfg);subprocess.run(['ld65','-C',out/(name+'.cfg'),'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*obs,out/(name+'-aliases.o')],check=True);raw=(out/(name+'.bin')).read_bytes();seo=wrap(raw,slot,id,api=(sy['se_overlay_call'],sy['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);products[name]=seo;budget[name]={'payload':len(raw),'sha256':hashlib.sha256(seo).hexdigest()};return raw
 raw=compile('geostail',[(out/'helper.s',[])],(LEAF/'geostail.cfg').read_text(),0,25);(out/'helper-witness.inc').write_text(f'HELPER_SIZE={len(raw)}\nHELPER_CRC={binascii.crc_hqx(raw,65535)}\n')
 c=(out/'compact/caret.s').read_text();codes=json.load(open(out/'compact/budget.json'))['status_codes'];(out/'status-codes.bin').write_bytes(bytes(codes));c=c.replace(' tax\n lda status_lookup,x\n asl',' ldx #25\n@lookup:\n cmp status_codes,x\n beq @mapped\n dex\n bpl @lookup\n@mapped:\n txa\n asl').replace('status_lookup:.incbin \"status-lookup.bin\"','status_codes:.incbin \"status-codes.bin\"');
 # type_try has a single operation14 admission; old narrow path is unchanged.
 auth='''authenticate_helper:
 ldy #2
@image:
 ldx #0
@find:
 lda se_overlay_ids,x
 cmp auth_id,y
 bne @next
 lda image_slot,x
 and auth_mask,y
 cmp auth_slot,y
 beq @found
@next:
 inx
 cpx #64
 bcc @find
 sec
 rts
@found:
 lda image_size_lo,x
 cmp auth_size_lo,y
 bne @miss
 lda image_size_hi,x
 cmp auth_size_hi,y
 bne @miss
 lda image_crc_lo,x
 cmp auth_crc_lo,y
 bne @miss
 lda image_crc_hi,x
 cmp auth_crc_hi,y
 bne @miss
 dey
 bpl @image
 clc
 rts
@miss:
 sec
 rts
''';a=c.index('authenticate_helper:');z=c.index('locate:',a);c=c[:a]+auth+c[z:];raws=[(out/'geostail.bin').read_bytes(),(out/'authority/styler.bin').read_bytes(),(out/'authority/viewsource.bin').read_bytes()];c+='\n.segment "RODATA"\nauth_id:.byte 25,14,14\nauth_slot:.byte 0,$81,$80\nauth_mask:.byte 1,$FF,$FF\n.segment "TAIL"\n'+''.join(name+':.byte '+','.join(str((len(r)if kind=='size'else binascii.crc_hqx(r,65535))>>shift&255)for r in raws)+'\n'for name,kind,shift in [('auth_size_lo','size',0),('auth_size_hi','size',8),('auth_crc_lo','crc',0),('auth_crc_hi','crc',8)])
 old='type_try:\n lda #14\n jsr helper\n jcs miss';assert c.count(old)==1;c=c.replace(old,'type_try:\n lda #14\n jsr helper\n jcs long_try');op3=''' cmp #3
 bne ordinary_entry
 ldx se_f_owner
 beq @idle
 lda #$B2
 sec
 rts
@idle:
 ldx #2
@copy:
 lda se_hot_caret,x
 sta se_e_target,x
 dex
 bpl @copy
 lda #47
 sta se_e_command
 lda se_mode
 cmp #3
 bne @committed
 lda #1
 bne @done
@committed:
 lda #0
@done:
 clc
 rts
ordinary_entry:
''';c=c.replace('entry:\n lda se_overlay_frame\n','entry:\n lda se_overlay_frame\n'+op3,1);c='.import se_e_target,se_e_command\n'+c;c+='\n.segment "CODE"\n'+(D/'controller.s').read_text();(out/'caret.s').write_text(c)
 compile('grid',[(out/'caret.s',[]),(ROOT/'src/render/geos/typing/status-normal.s',[]),(D/'shift-row.s',['LPF=$8D40','LP_NO_CARRY=1','LP_TRUSTED=1'])],(out/'compact/grid.cfg').read_text().replace('NATIVE:load=IMAGE,type=ro,start=$BF00;','NATIVE:load=IMAGE,type=ro,start=$BF00;TAIL:load=IMAGE,type=ro,start=$BFD0;'),1,33)
 (out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return products,budget
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2])if len(sys.argv)>2 else BASE)[1])
