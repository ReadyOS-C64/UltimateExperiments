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
 import shutil
 for name in ['caret.s','helper.s']:
  shutil.copy2(D/'released'/name,out/name)
 # Private variant: sealed native status font stays in C33 across all R calls.
 native=(base/'fonts/native8.bin').read_bytes();assert len(native)==1024
 expected=[]
 for name in ['grid80','grid60']:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes();assert image[36+0xc00:36+0x1000]==native
  expected.append(int.from_bytes(image[12:14],'little'))
 (out/'native8.bin').write_bytes(native)
 caret=(out/'caret.s').read_text()
 admission=' ; Admit the exact font leaf before any pixel/cache publication.\n lda #2\n jsr leaf\n jcs miss\n'
 assert caret.count(admission)==1;caret=caret.replace(admission,' ; Guarded verified backing + C33-owned native font; no R16 execution.\n')
 begin=caret.index('\nstatus:\n')+1;end=caret.index('.segment "RODATA"',begin)
 caret=caret[:begin]+(D/'status-local.s').read_text()+caret[end:]
 caret+='\n.segment "NATIVE"\nlocal_native8:\n.incbin "native8.bin"\n.assert local_native8=$BC00,lderror,"C33 native font ABI"\n.assert *-local_native8=1024,error,"C33 native font size"\n'
 (out/'caret.s').write_text(caret)
 helper=(out/'helper.s').read_text();needle='@found:\n stx FCAP+1';assert helper.count(needle)==1
 auth='@found:\n lda image_slot,x\n and #$80\n jeq invalid\n lda BACKEND\n sec\n sbc #16\n tay\n lda image_crc_lo,x\n cmp native_crc_lo,y\n jne invalid\n lda image_crc_hi,x\n cmp native_crc_hi,y\n jne invalid\n stx FCAP+1'
 helper=helper.replace(needle,auth)
 helper+='\n.import se_overlay_managed_verification\n.assert se_overlay_managed_verification=1,lderror,"local status requires coherent managed backing"\n.segment "RODATA"\nnative_crc_lo:.byte '+','.join(str(x&255)for x in expected)+'\nnative_crc_hi:.byte '+','.join(str(x>>8)for x in expected)+'\n'
 (out/'helper.s').write_text(helper)
 results={};seos={}
 for name,paths,slot,ident in [('geostail',[out/'helper.s'],0,25),('grid',[out/'caret.s',ROOT/'src/render/geos/typing/status-normal.s'],1,33)]:
  objs=[]
  for j,path in enumerate(paths):
   o=out/(name+str(j)+'.o');subprocess.run(['ca65','-g','-I',out,'-I',ROOT/'src/render/grid/caret','-I',ROOT/'src','-o',o,path],check=True);objs.append(o)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True)
  a=out/(name+'-aliases.o');subprocess.run(['ca65','-o',a,out/(name+'-aliases.s')],check=True);objs.append(a)
  cfg=out/(name+'.cfg');cfg.write_text('MEMORY {IMAGE:file=%O,start=$'+('B000'if slot else'A000')+',size=$1000,type=ro'+(',fill=yes'if slot else'')+';} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;'+('NATIVE:load=IMAGE,type=ro,start=$BC00;'if slot else'')+'}')
  subprocess.run(['ld65','-C',cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs],check=True)
  raw=(out/(name+'.bin')).read_bytes();
  if name=='geostail':
   import binascii
   (out/'helper-witness.inc').write_text('HELPER_SIZE='+str(len(raw))+'\nHELPER_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
  seo=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);seos[name]=seo;results[name]=dict(payload=len(raw),sha256=hashlib.sha256(seo).hexdigest())
 (out/'budget.json').write_text(json.dumps(results,indent=2)+'\n');return seos,results
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2]))[1])
