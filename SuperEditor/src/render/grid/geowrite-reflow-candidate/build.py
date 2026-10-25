"""Private batched R14pixel worker using immutable releasedSP2 inputs."""
from pathlib import Path
import sys,json,subprocess,binascii,hashlib,shutil
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
RELEASE=ROOT/'agentsworking/evidence/M8/20261025T201720331556Z-grid-long-prose';BASE=RELEASE/'fixture';LEAF=RELEASE/'leaf'
def build(out,base=BASE):
 out.mkdir(parents=True,exist_ok=True);shutil.copytree(LEAF/'authority',out/'authority');project=out/'authority/project';entry=project/'src/overlays/source-view.s';s=entry.read_text();old='    lda #$B0\n    sec\n    rts';assert s.count(old)==1;s=s.replace(old,'''    cmp #7
    bne pixel_argument
    lda se_f_owner
    cmp #4
    bne pixel_argument
    jmp se_lp_shift_row
pixel_argument:
    lda #$B0
    sec
    rts''');entry.write_text('.import se_f_owner,se_lp_shift_row\n'+s)
 for n in ['editor-api.inc','native-witness.inc','helper-witness.inc','status-font.bin','status-codes.bin','helper.s']:shutil.copy2(LEAF/n,out/n)
 for n in ['producer2.s','prose2.inc']:shutil.copy2(ROOT/'src/render/grid/long-prose-candidate'/n,out/n)
 sy=json.load(open(base/'build/editor-report.json'))['symbols'];digest=json.load(open(base/'build/editor-report.json'))['resident_binding']['digest'];products={};budget={}
 def compile(name,items,cfg,slot,id):
  objs=[]
  for j,(p,defs)in enumerate(items):
   ob=out/(name+str(j)+'.o');cmd=['ca65','-g','-I',out,'-I',D,'-I',ROOT/'src/render/grid/caret','-I',project/'src','-I',ROOT/'src']
   for define in defs:cmd+=['-D',define]
   subprocess.run([*cmd,'-o',ob,p],check=True);objs.append(ob)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True);subprocess.run(['ca65','-o',out/(name+'-aliases.o'),out/(name+'-aliases.s')],check=True);(out/(name+'.cfg')).write_text(cfg);subprocess.run(['ld65','-C',out/(name+'.cfg'),'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs,out/(name+'-aliases.o')],check=True);raw=(out/(name+'.bin')).read_bytes();seo=wrap(raw,slot,id,api=(sy['se_overlay_call'],sy['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);products[name]=seo;budget[name]={'payload':len(raw),'sha256':hashlib.sha256(seo).hexdigest()};return raw
 cfg=(LEAF/'authority/viewsource.cfg').read_text().replace('RODATA:', 'CODE:load=IMAGE,type=ro;RODATA:');raw=compile('viewsource',[(entry,[]),(project/'src/fold/source-context.s',[]),(project/'src/fold/source-read.s',[]),(out/'producer2.s',[]),(D/'shift-row.s',['LPF=$8D40'])],cfg,0,14)
 c=(LEAF/'caret.s').read_text();at=c.index('; Private C33 long-row coordinator');c=c[:at]+(D/'controller.s').read_text();old=next(line for line in c.splitlines()if line.startswith('auth_size_lo:'));# Tables generatedfromactualnewR14; C14/R25 remainbyteidenticalrelease.
 for name,shift in [('auth_size_lo',0),('auth_size_hi',8),('auth_crc_lo',0),('auth_crc_hi',8)]:
  old=next(line for line in c.splitlines()if line.startswith(name+':'));values=old.split('.byte ')[1].split(',');values[2]=str((len(raw)if 'size'in name else binascii.crc_hqx(raw,65535))>>shift&255);c=c.replace(old,name+':.byte '+','.join(values))
 (out/'caret.s').write_text(c);compile('grid',[(out/'caret.s',[]),(ROOT/'src/render/geos/typing/status-normal.s',[])],(LEAF/'grid.cfg').read_text(),1,33)
 for n in ['geostail','styler']:products[n]=(BASE/'build/overlays'/(n+'.seo')).read_bytes()
 (out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return products,budget
if __name__=='__main__':print(build(Path(sys.argv[1]))[1])
