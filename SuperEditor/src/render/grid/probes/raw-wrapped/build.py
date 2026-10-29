"""New private raw fixed-row carry probe; no released source is modified."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[5]
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def patch(s,a,b):assert s.count(a)==1,a;return s.replace(a,b)
def build(out,base):
 out.mkdir(parents=True);raw=load(ROOT/'src/render/grid/probes/raw-typing/build.py','released_raw');rawfixture,rawbudget=raw.build(out/'raw-release',base)
 tree=out/'raw-release/caret-release/tree';d=tree/'src/render/grid/caret';source=tree/'src/overlays/source-view.s';old=source.read_text();seal=json.loads((base/'build/editor-bindings.json').read_text());digest=json.loads((base/'freeze.json').read_text())['binding'] if 'binding'in json.loads((base/'freeze.json').read_text())else None
 # Reuse the already generated actual-binding import-only header.
 def r14(folder):
  folder.mkdir();shutil.copyfile(out/'raw-release/candidate/editor-api.inc',folder/'editor-api.inc');objs=[]
  for i,rel in enumerate(['src/overlays/source-view.s','src/fold/source-context.s','src/fold/source-read.s','src/render/grid/paragraph/producer.s','src/render/grid/paragraph/shift-row.s']):
   obj=folder/(str(i)+'.o');extra=['-D','LPF=$8D40']if rel.endswith('shift-row.s')else[]
   subprocess.run(['ca65','-g',*extra,'-I',folder,'-I',tree/'src/render/grid/paragraph','-I',tree/'src','-o',obj,tree/rel],check=True);objs.append(obj)
  subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',folder/'aliases.s',*objs],check=True);subprocess.run(['ca65','-o',folder/'aliases.o',folder/'aliases.s'],check=True);objs.append(folder/'aliases.o')
  subprocess.run(['ld65','-C',tree/'cfg/source-r.cfg','-o',folder/'viewsource.bin','-Ln',folder/'viewsource.lbl','-m',folder/'viewsource.map',*objs],check=True)
  sys.path.insert(0,str(tree/'tools'));from overlays import wrap
  from bindings import verify
  s=json.loads((base/'build/editor-report.json').read_text())['symbols'];binding=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];image=wrap((folder/'viewsource.bin').read_bytes(),0,14,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(folder/'viewsource.seo').write_bytes(image);return image
 original=r14(out/'r14-control');assert original==(base/'build/overlays/viewsource.seo').read_bytes(),'R14 control must byte-match packaged'
 new=patch(old,'    cmp #7\n    bne pixel_argument\n    lda se_f_owner\n    cmp #4\n    bne pixel_argument\n    jmp se_lp_shift_row\n','    cmp #7\n    beq pixel_owner\n    cmp #6\n    bne pixel_argument\npixel_owner:\n    ldx se_f_owner\n    cpx #4\n    bne pixel_argument\n    cmp #6\n    beq pixel_prime\n    jmp se_lp_shift_row\npixel_prime:\n    lda #0\n    clc\n    rts\n')
 context=tree/'src/fold/source-context.s';ct=context.read_text()
 for aa,bb in [('jne @hot','bne @hot'),('jcc @ordered','bcc @ordered')]:ct=patch(ct,aa,bb)
 assert ct.count('jcc @length')==2;ct=ct.replace('jcc @length','bcc @length')
 context.write_text(ct)
 source.write_text(new);worker=r14(out/'r14-candidate')
 # Build the C33/R25 pair against the actual new R14 image witness.
 fixture=out/'fixture';shutil.copytree(rawfixture,fixture);(fixture/'build/overlays/viewsource.seo').write_bytes(worker)
 ident=json.loads((fixture/'freeze.json').read_text());ident['assets']['viewsource']=hashlib.sha256(worker).hexdigest();(fixture/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n')
 c=(d/'caret.s').read_text();h=(d/'helper.s').read_text();controller=tree/'src/render/grid/paragraph/controller.inc';ctrl=controller.read_text()
 c=patch(c,' lda se_render_caps\n jeq miss\n jmp long_try\n',' jmp long_try\n')
 c=patch(c,'auth_id:.byte 25,14,14','auth_id:.byte 25,14,14,14');c=patch(c,'auth_slot:.byte 0,$81,$80','auth_slot:.byte 0,$81,$80,0');c=patch(c,'auth_mask:.byte 1,$FF,$FF','auth_mask:.byte 1,$FF,$FF,1')
 c=patch(c,' dey\n bpl @image\n clc\n rts\n@miss:', ' cpy #3\n beq @authenticated\n dey\n bpl @image\n@authenticated:\n clc\n rts\n@miss:')
 c=patch(c,'.segment "TAIL"\nauth_size_lo:', '.segment "RODATA"\nauth_size_lo:')
 for suffix in ('size_lo','size_hi','crc_lo','crc_hi'):
  line=next(x for x in c.splitlines()if x.startswith('auth_'+suffix+':'));new_line=line+','+line.split(',')[-1];c=patch(c,line,new_line)
 h=patch(h,'type_long_prepare:\n lda se_render_caps\n jeq invalid\n lda #2\n','type_long_prepare:\n lda #2\n')
 ctrl=patch(ctrl,'long_try:\n lda #16\n','long_try:\n lda se_render_caps\n bne @prepared_worker\n ldy #3\n jsr authenticate_dependencies\n jcs miss\n@prepared_worker:\n lda #16\n')
 ctrl=patch(ctrl,' lda EDIT\n beq @bad1\n clc\n adc #1\n cmp W\n bcs @bad1\n',' lda se_render_caps\n beq @raw_edit\n lda EDIT\n beq @bad1\n clc\n adc #1\n cmp W\n bcs @bad1\n jmp @edit_ready\n@raw_edit:\n lda SIGN\n bpl @raw_index\n lda OLDCOL\n bne @raw_index\n lda ROW\n jeq miss\n dec ROW\n lda W\n sec\n sbc #1\n sta EDIT\n jsr bounds\n jcs miss\n SUB24 END,POS,DELTA\n lda DELTA+1\n ora DELTA+2\n jne miss\n lda DELTA\n cmp W\n jne miss\n@raw_index:\n lda EDIT\n cmp W\n jcs miss\n@edit_ready:\n')
 ctrl=patch(ctrl,' lda OLDCOL\n clc\n adc SIGN\n sta NEWCOL\n cmp W\n bcs @bad1\n',' lda se_render_caps\n beq @raw_caret\n lda OLDCOL\n clc\n adc SIGN\n sta NEWCOL\n cmp W\n bcs @bad1\n jmp @caret_ready\n@raw_caret:\n lda EDIT\n ldx SIGN\n cpx #1\n bne :+\n clc\n adc #1\n: sta NEWCOL\n cmp W\n bcc @caret_ready\n lda #0\n sta NEWCOL\n inc NEWROW\n lda NEWROW\n cmp #22\n jcs miss\n@caret_ready:\n')
 ctrl=patch(ctrl,' jsr row_bit\n tax\n lda B+111,x\n and BITMASK\n beq @bad1\n',' lda se_render_caps\n beq @raw_row\n jsr row_bit\n tax\n lda B+111,x\n and BITMASK\n beq @bad1\n@raw_row:\n')
 ctrl=patch(ctrl,'long_alnum:\n cmp', 'long_alnum:\n ldx se_render_caps\n bne :+\n cmp #13\n beq @bad\n clc\n rts\n:\n cmp')
 ctrl=patch(ctrl,'@staged_glyph:\n jsr se_doc_invalidate\n','@staged_glyph:\n lda se_render_caps\n bne @worker_ready\n lda #6\n sta se_overlay_frame\n lda #14\n ldx #0\n jsr se_overlay_call\n jcs miss\n@worker_ready:\n jsr se_doc_invalidate\n')
 packet=tree/'src/render/grid/paragraph/packet.inc';packet.write_text(patch(packet.read_text(),' sta P-1,x\n bne @left\n',' sta P-1,x\n jmp @left\n'))
 # This version retains the original no-new/no-removed-physical-row geometry.
 ctrl=ctrl.replace('bcs @bad1','jcs @bad1').replace('beq @bad1','jeq @bad1')
 (d/'caret.s').write_text(c);(d/'helper.s').write_text(h);controller.write_text(ctrl)
 m=load(d/'build.py','wrapped_pair_build');m.build(out/'candidate',fixture)
 for name in ('grid','geostail'):
  image=(out/'candidate'/(name+'.seo')).read_bytes();(fixture/'build/overlays'/(name+'.seo')).write_bytes(image);ident['assets'][name]=hashlib.sha256(image).hexdigest()
 ident['private_change']='Raw unchanged-physical-row carry; exact R14 pixel-prime before writes.';(fixture/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n')
 result=dict(status='built',raw_release=rawbudget,newBSS=0,newZP=0,R14_original_byte_identical=True,assets={n:ident['assets'][n]for n in('grid','geostail','viewsource')})
 for name in ('grid','geostail'):result[name]=(out/'candidate'/(name+'.map')).read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip()
 result['R14_payload']=len(worker)-36;(out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])
