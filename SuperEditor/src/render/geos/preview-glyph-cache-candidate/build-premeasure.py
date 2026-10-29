from pathlib import Path
import sys,zipfile,subprocess,json,re,binascii
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_catalog_byte_candidate as helper

def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 # Borrow unchanged realfontstore/metadata/binding recipe and freezesincludes.
 helper.build(out/'base',base,True,ROOT/'src/render/geos/preview-only-candidate')
 pack=(out/'base/font-pack.bin').read_bytes();entry=next(pack[32+i*16:48+i*16]for i in range(pack[5])if pack[32+i*16:36+i*16]==bytes((2,255,255,9)));at=int.from_bytes(entry[8:11],'little');n=int.from_bytes(entry[11:13],'little');assert n==744;(out/'base/cache-font.inc').write_text(f'CACHE_FONT_CRC=${binascii.crc_hqx(pack[at:at+n],65535):04X}\n')
 objects=[];segments={}
 for tag,source in [('entry',D/'cache-entry.s'),('preview',D/'premeasure-preview.s'),('codec',D/'premeasure-codec.s'),('controller',D/'premeasure-controller.s')]:
  o=out/(tag+'.o');helper.command('ca65','-g','-I',out/'base','-I',out/'base/includes','-o',o,source);objects.append(o);dump=subprocess.check_output(['od65','--dump-segments',str(o)],text=True);segments[tag]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dump,re.S)}
 objects.append(out/'base/font-store.o');helper.command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'bindings.s',*objects);helper.command('ca65','-o',out/'bindings.o',out/'bindings.s')
 helper.command('ld65','-C',out/'base/r23.cfg','-o',out/'cache.bin','-m',out/'cache.map','-Ln',out/'cache.lbl',*objects,out/'bindings.o');raw=(out/'cache.bin').read_bytes();result=dict(bytes=len(raw),free=4096-len(raw),segments=segments);(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
