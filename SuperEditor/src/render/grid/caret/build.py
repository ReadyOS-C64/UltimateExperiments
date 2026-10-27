"""Build C33/R25 using linked native-font and paragraph-producer witnesses."""
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
 import shutil,binascii
 fontpath=base/'fonts/native8.bin'
 if not fontpath.exists():fontpath=base/'assets/fonts/generated/native8.bin'
 (out/'native8.bin').write_bytes(fontpath.read_bytes())
 native=(out/'native8.bin').read_bytes();assert len(native)==1024
 # Hex glyphs lead so the direct renderer indexes them without a lookup.
 codes=[*range(48,58),*range(65,71),1,4,5,6,9,12,14,15,32,77]
 assert len(codes)==26
 (out/'status-font.bin').write_bytes(b''.join(native[i*8:i*8+8]for i in codes))
 witness=[]
 for name,ident in [('grid80',16),('grid60',17)]:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes()
  assert image[5:7]==bytes((0,ident)) and image[36+0xc00:36+0x1000]==native
  import binascii
  assert len(image)==36+4096 and image[20:36]==image[36:52]==bytes.fromhex(digest)
  assert binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
  if (base/'freeze.json').exists():assert hashlib.sha256(image).hexdigest()==json.loads((base/'freeze.json').read_text())['assets'][name]
  witness.append('NATIVE_CRC'+str(ident)+'='+str(int.from_bytes(image[12:14],'little')))
 (out/'native-witness.inc').write_text('\n'.join(witness)+'\n')
 # SP2 authority is admitted only from these actual linked C14/R14 images.
 witnesses=[]
 for name,slot,prefix in [('styler',1,'PARAGRAPH_CODE'),('viewsource',0,'PARAGRAPH_SOURCE')]:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes();raw=image[36:]
  assert image[5:7]==bytes((slot,14)) and len(raw)<=4096
  assert image[20:36]==raw[:16]==bytes.fromhex(digest)
  crc=binascii.crc_hqx(raw,65535)
  assert crc==int.from_bytes(image[12:14],'little')
  witnesses.extend([f'{prefix}_SIZE={len(raw)}',f'{prefix}_CRC={crc}'])
 (out/'paragraph-witness.inc').write_text('\n'.join(witnesses)+'\n')
 # Use canonical source; only generated includes/font live in the output directory.
 results={};seos={}
 for name,paths,slot,ident in [('geostail',[D/'helper.s'],0,25),('grid',[D/'caret.s',ROOT/'src/render/geos/typing/status-normal.s'],1,33)]:
  objs=[]
  for j,path in enumerate(paths):
   o=out/(name+str(j)+'.o');defs=['-D','LPF=$8D40','-D','LP_NO_CARRY=1','-D','LP_TRUSTED=1']if path.name=='shift-row.s'else[]
   subprocess.run(['ca65','-g',*defs,'--bin-include-dir',out,'-I',out,'-I',D,'-I',ROOT/'src/render/grid/paragraph','-I',ROOT/'src','-o',o,path],check=True);objs.append(o)
   dumped=subprocess.check_output(['od65','--dump-segments',str(o)],text=True)
   segments={n:int(size)for n,size in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dumped,re.S)}
   assert not any(segments.get(n,0)for n in ('BSS','ZEROPAGE','DATA'))
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True)
  a=out/(name+'-aliases.o');subprocess.run(['ca65','-o',a,out/(name+'-aliases.s')],check=True);objs.append(a)
  cfg=out/(name+'.cfg');shutil.copy2(D/(name+'.cfg'),cfg)
  subprocess.run(['ld65','-C',cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs],check=True)
  raw=(out/(name+'.bin')).read_bytes();
  if name=='geostail':
   import binascii
   (out/'helper-witness.inc').write_text('HELPER_SIZE='+str(len(raw))+'\nHELPER_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
  seo=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);seos[name]=seo;results[name]=dict(payload=len(raw),sha256=hashlib.sha256(seo).hexdigest())
 labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'grid.lbl').read_text())}
 for suffix in ['bin','map','lbl']:shutil.copyfile(out/('grid.'+suffix),out/('candidate.'+suffix))
 (out/'gridcaret.seo').write_bytes(seos['grid'])
 result=dict(payload=results['grid']['payload'],sha256=results['grid']['sha256'],pair=results,newBSS=0,newZP=0,resident=seal['resident_sha256'],native_sha256=hashlib.sha256(native).hexdigest())
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return seos['grid'],labels,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[2])
