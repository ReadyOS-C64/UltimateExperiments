"""Private exact C33/R25 factoring; no canonical source/build mutation."""
from pathlib import Path
import sys,json,subprocess,re,hashlib
ROOT=Path(__file__).resolve().parents[4];D=ROOT/'src/render/grid/typing-candidate'
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap
HELPERS=['admit','fields','header_crc','store_header','fetch_header','fetch_row','row_request','packet_crc','verify_row','bounds','retreat','row_bit']
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];seal=verify(base/'build/editor.prg',base/'build/editor.lbl');digest=seal['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 import shutil
 shutil.copy2(base/'fonts/native8.bin',out/'native8.bin')
 native=(out/'native8.bin').read_bytes();assert len(native)==1024
 witness=[]
 for name,ident in [('grid80',16),('grid60',17)]:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes()
  assert image[5:7]==bytes((0,ident)) and image[36+0xc00:36+0x1000]==native
  import binascii
  assert len(image)==36+4096 and image[20:36]==image[36:52]==bytes.fromhex(digest)
  assert binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
  assert hashlib.sha256(image).hexdigest()==json.loads((base/'freeze.json').read_text())['assets'][name]
  witness.append('NATIVE_CRC'+str(ident)+'='+str(int.from_bytes(image[12:14],'little')))
 (out/'native-witness.inc').write_text('\n'.join(witness)+'\n')
 for name in ['caret.s','helper.s']:
  shutil.copy2(D/'local-released'/name,out/name)
 caret=(out/'caret.s').read_text();old=' jsr row_bit\n lda H+N_CR,x';assert caret.count(old)==1;caret=caret.replace(old,' jsr row_bit\n tax ;A survives resident overlay return; X does not\n lda H+N_CR,x');old=' cmp #22\n jcc @row\n jsr locate';assert caret.count(old)==1;caret=caret.replace(old,' cmp #22\n bcc @row ;assembler proves relative range\n jsr locate');(out/'caret.s').write_text(caret)
 results={};seos={}
 for name,paths,slot,ident in [('geostail',[out/'helper.s'],0,25),('grid',[out/'caret.s',ROOT/'src/render/geos/typing/status-normal.s'],1,33)]:
  objs=[]
  for j,path in enumerate(paths):
   o=out/(name+str(j)+'.o');subprocess.run(['ca65','-g','-I',out,'-I',ROOT/'src/render/grid/caret','-I',ROOT/'src','-o',o,path],check=True);objs.append(o)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True)
  a=out/(name+'-aliases.o');subprocess.run(['ca65','-o',a,out/(name+'-aliases.s')],check=True);objs.append(a)
  cfg=out/(name+'.cfg');shutil.copy2(D/'local-released'/(name+'.cfg'),cfg)
  subprocess.run(['ld65','-C',cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs],check=True)
  raw=(out/(name+'.bin')).read_bytes();
  if name=='geostail':
   import binascii
   (out/'helper-witness.inc').write_text('HELPER_SIZE='+str(len(raw))+'\nHELPER_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
  seo=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);seos[name]=seo;results[name]=dict(payload=len(raw),sha256=hashlib.sha256(seo).hexdigest())
 (out/'budget.json').write_text(json.dumps(results,indent=2)+'\n');return seos,results
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2]))[1])
