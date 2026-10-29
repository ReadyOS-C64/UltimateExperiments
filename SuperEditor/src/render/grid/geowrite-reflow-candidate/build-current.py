"""Currentfrozenproduction SP2 plus privatebatchedR14/C33; no sharedwrites."""
from pathlib import Path
import json,sys,zipfile,shutil,subprocess,importlib.util,hashlib
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture'
def build(out,base=BASE,producer=None,pixel=True,dispatch=False):
 out.mkdir(parents=True,exist_ok=True);project=out/'project';project.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith(('src/','tools/'))and not name.endswith('/'):
    p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 if producer is not None:(project/'src/render/grid/paragraph/producer.s').write_text(Path(producer).read_text())
 report=json.load(open(base/'build/editor-report.json'));s=report['symbols'];digest=report['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');entry=project/'src/overlays/source-view.s';text=entry.read_text();old='    lda #$B0\n    sec\n    rts';assert text.count(old)==1
 if pixel:text=text.replace(old,'''    cmp #7
    bne pixel_argument
    lda se_f_owner
    cmp #4
    bne pixel_argument
    jmp se_lp_shift_row
pixel_argument:
    lda #$B0
    sec
    rts''')
 entry.write_text(('.import se_f_owner,se_lp_shift_row\n'if pixel else '')+text)
 objs=[]
 for i,path in enumerate([entry,project/'src/fold/source-context.s',project/'src/fold/source-read.s',project/'src/render/grid/paragraph/producer.s']+([D/'shift-row.s']if pixel else [])):
  ob=out/('r14-'+str(i)+'.o');subprocess.run(['ca65','-g','-D','LPF=$8D40','-I',out,'-I',D,'-I',project/'src/render/grid/paragraph','-I',project/'src','-o',ob,path],check=True);objs.append(ob)
 subprocess.run([sys.executable,project/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'r14-aliases.s',*objs],check=True);subprocess.run(['ca65','-o',out/'r14-aliases.o',out/'r14-aliases.s'],check=True);cfg=out/'r14.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$A000,size=$1000;} SEGMENTS {FOLD_SOURCE_CODE:load=IMAGE,type=ro;CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}');subprocess.run(['ld65','-C',cfg,'-o',out/'viewsource.bin','-Ln',out/'viewsource.lbl','-m',out/'viewsource.map',*objs,out/'r14-aliases.o'],check=True);raw=(out/'viewsource.bin').read_bytes();seo=wrap(raw,0,14,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'viewsource.seo').write_bytes(seo)
 private=out/'buildbase';(private/'build/overlays').mkdir(parents=True);shutil.copytree(base/'fonts',private/'fonts')
 for name in('editor.prg','editor.lbl','editor-report.json'):shutil.copy2(base/'build'/name,private/'build'/name)
 for name in('grid80','grid60','styler'):shutil.copy2(base/'build/overlays'/(name+'.seo'),private/'build/overlays'/(name+'.seo'))
 if dispatch:
  assert producer is not None
  reader=project/'src/style/reader-dispatch.s';text=reader.read_text();old='se_sc_event: lda #4\n bne certificate';new='''se_sc_event:
 lda se_sm_kind
 beq @call
 lda $89C3 ;phase-owned LIVE; absence can only suppress authority
 bne @call
 lda #0
 clc
 rts
@call: lda #4
 bne certificate''';assert text.count(old)==1;reader.write_text('.import se_sm_kind\n'+text.replace(old,new));(out/'style-api.inc').write_text((out/'editor-api.inc').read_text());objs=[]
  items=[(project/'src/style'/n,defs)for n,defs in [('entry.s',[]),('plan.s',['SE_STYLE_LEXICAL=1','SE_STYLE_GRID=1']),('editor-control.s',[]),('reader-dispatch.s',[])]]+[(project/'src/supermark'/n,['SE_SM_CODE_ONLY=1'])for n in ['block.s','inline.s']]
  for j,(path,defs)in enumerate(items):
   ob=out/('c14-'+str(j)+'.o');cmd=['ca65','-g','-I',out,'-I',project/'src']
   for flag in defs:cmd+=['-D',flag]
   subprocess.run([*cmd,'-o',ob,path],check=True);objs.append(ob)
  subprocess.run([sys.executable,project/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'c14-aliases.s',*objs],check=True);subprocess.run(['ca65','-o',out/'c14-aliases.o',out/'c14-aliases.s'],check=True);cfg=out/'c14.cfg'
  with zipfile.ZipFile(base/'product-sources.zip')as z:cfg.write_bytes(z.read('cfg/style-c.cfg'))
  subprocess.run(['ld65','-C',cfg,'-o',out/'styler.bin','-Ln',out/'styler.lbl','-m',out/'styler.map',*objs,out/'c14-aliases.o'],check=True);style=wrap((out/'styler.bin').read_bytes(),1,14,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'styler.seo').write_bytes(style);(private/'build/overlays/styler.seo').write_bytes(style)
 (private/'build/overlays/viewsource.seo').write_bytes(seo)
 # Productionpair recipe staysunchanged; it sees private modifiedsources only.
 if pixel:
  (project/'src/render/grid/paragraph/controller.inc').write_text((D/'controller.s').read_text());(project/'src/render/grid/paragraph/shift-row.s').write_text('.setcpu "6502"\n.segment "CODE"\n')
 spec=importlib.util.spec_from_file_location('privatecanonicalpair',project/'src/render/grid/caret/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);b.ROOT=project;b.D=project/'src/render/grid/caret';_,labels,budget=b.build(out/'pair',private);assert(out/'pair/geostail.seo').read_bytes()==(base/'build/overlays/geostail.seo').read_bytes(),'R25muststaybyteidentical'
 products={'viewsource':seo,'grid':(out/'pair/grid.seo').read_bytes(),'styler':(private/'build/overlays/styler.seo').read_bytes(),'geostail':(base/'build/overlays/geostail.seo').read_bytes()};result={name:{'payload':len(image)-36,'sha256':hashlib.sha256(image).hexdigest()}for name,image in products.items()};(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return products,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
