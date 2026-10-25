"""Private actual C14/R14 publication + exact C33/R25 consumer; no shared builds."""
from pathlib import Path
import sys,json,subprocess,hashlib,zipfile,binascii,shutil,importlib.util
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);project=out/'project';project.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and not n.endswith('/'):
    p=project/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 seal=verify(base/'build/editor.prg',base/'build/editor.lbl');digest=seal['digest'];symbols=json.load(open(base/'build/editor-report.json'))['symbols']
 header='.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n'
 for n in ['editor-api.inc','style-api.inc']:(out/n).write_text(header)
 plan=project/'src/style/plan.s';s=plan.read_text();s='.import se_sc_begin,se_sc_event,se_sc_finish\n'+s
 for old,new in [('    jsr checkpoint_begin','    jsr checkpoint_begin\n    jsr se_sc_begin'),('    jeq next_line\n    lda #0\n    sta st_inline','    jeq next_line\n    jsr se_sc_event\n    lda #0\n    sta st_inline'),('    jsr se_fs_guard\n    jcs failure\n    jsr release\n    inc se_st_generation','    jsr se_fs_guard\n    jcs failure\n    jsr se_sc_finish\n    jsr release\n    inc se_st_generation')]:
  assert s.count(old)==1,old;s=s.replace(old,new)
 plan.write_text(s)
 reader=project/'src/style/reader-dispatch.s';reader.write_text(reader.read_text()+'''
.import se_mode
.export se_sc_begin,se_sc_event,se_sc_finish
se_sc_begin: lda #3
 bne certificate
se_sc_event: lda #4
 bne certificate
se_sc_finish: lda #5
certificate:
 ldx se_mode
 bne invoke
 lda #0
 clc
 rts
''')
 entry=project/'src/overlays/source-view.s';s=entry.read_text();old='    lda #$B0\n    sec\n    rts';assert s.count(old)==1;s=s.replace(old,'''    cmp #3
    beq sc_begin
    cmp #4
    beq sc_event
    cmp #5
    beq sc_finish
    lda #$B0
    sec
    rts
sc_begin:jmp se_sc_begin
sc_event:jmp se_sc_event
sc_finish:jmp se_sc_finish''');entry.write_text('.import se_sc_begin,se_sc_event,se_sc_finish\n'+s)
 products={};budget={}
 def compile(name,items,segmentcfg,slot,ident):
  objs=[]
  for index,(path,defs)in enumerate(items):
   obj=out/(name+str(index)+'.o');cmd=['ca65','-g','-I',out,'-I',D,'-I',project/'src','-I',ROOT/'src/render/grid/caret']
   for definition in defs:cmd+=['-D',definition]
   subprocess.run([*cmd,'-o',obj,path],check=True);objs.append(obj)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True)
  obj=out/(name+'-aliases.o');subprocess.run(['ca65','-o',obj,out/(name+'-aliases.s')],check=True);objs.append(obj)
  cfg=out/(name+'.cfg');cfg.write_text(segmentcfg);subprocess.run(['ld65','-C',cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs],check=True)
  raw=(out/(name+'.bin')).read_bytes();seo=wrap(raw,slot,ident,api=(symbols['se_overlay_call'],symbols['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);products[name]=seo;budget[name]=dict(payload=len(raw),sha256=hashlib.sha256(seo).hexdigest());return raw
 compile('styler',[(project/'src/style'/n,defs)for n,defs in [('entry.s',[]),('plan.s',['SE_STYLE_LEXICAL=1','SE_STYLE_GRID=1']),('editor-control.s',[]),('reader-dispatch.s',[])]]+[(project/'src/supermark'/n,['SE_SM_CODE_ONLY=1'])for n in ['block.s','inline.s']], 'MEMORY {IMAGE:file=%O,start=$B000,size=$1000;} SEGMENTS {STYLE_CODE:load=IMAGE,type=ro;SM_BLOCK:load=IMAGE,type=ro;SM_INLINE:load=IMAGE,type=ro;CODE:load=IMAGE,type=ro,optional=yes;RODATA:load=IMAGE,type=ro,optional=yes;}',1,14)
 compile('viewsource',[(project/'src/overlays/source-view.s',[]),(project/'src/fold/source-context.s',[]),(project/'src/fold/source-read.s',[]),(D/'producer.s',[])], 'MEMORY {IMAGE:file=%O,start=$A000,size=$1000;} SEGMENTS {FOLD_SOURCE_CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro,optional=yes;}',0,14)
 # Start from the self-contained qualified local-status pair, not live canonical files.
 for n in ['caret.s','helper.s','grid.cfg','geostail.cfg']:shutil.copy2(ROOT/'src/render/grid/typing-candidate/local-released'/n,out/n)
 caret=(out/'caret.s').read_text();old=' jsr row_bit\n lda H+N_CR,x';assert caret.count(old)==1;caret=caret.replace(old,' jsr row_bit\n tax ;overlay dispatcher preserves A but clobbers X\n lda H+N_CR,x');old=' cmp #22\n jcc @row\n jsr locate';assert caret.count(old)==1;caret=caret.replace(old,' cmp #22\n bcc @row ;range proven by assembler\n jsr locate');(out/'caret.s').write_text(caret)
 helper=(out/'helper.s').read_text();a=helper.index(' ; Conservative semantic proof from BOF');b=helper.index(' SUB24 END,POS,DELTA',a);helper=helper[:a]+' jsr sc_check\n jcs invalid\n'+helper[b:]
 old=' lda #1\n sta OP\n sta se_v_seen';assert helper.count(old)==1;helper=helper.replace(old,' jsr sc_rekey\n jcs invalid\n'+old)
 helper+='\n.segment "CODE"\n'+(D/'consumer.s').read_text();(out/'helper.s').write_text(helper)
 native=(base/'fonts/native8.bin').read_bytes();(out/'native8.bin').write_bytes(native);witness=[]
 for name,ident in [('grid80',16),('grid60',17)]:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes();assert image[36+0xc00:36+0x1000]==native;witness.append('NATIVE_CRC'+str(ident)+'='+str(int.from_bytes(image[12:14],'little')))
 (out/'native-witness.inc').write_text('\n'.join(witness)+'\n')
 raw=compile('geostail',[(out/'helper.s',[])],(out/'geostail.cfg').read_text(),0,25);(out/'helper-witness.inc').write_text('HELPER_SIZE='+str(len(raw))+'\nHELPER_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
 compile('grid',[(out/'caret.s',[]),(project/'src/render/geos/typing/status-normal.s',[])],(out/'grid.cfg').read_text(),1,33)
 (out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return products,budget
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2]))[1])
