"""Private exact C33 dynamic-status font subset; previous releases immutable."""
from pathlib import Path
import json,sys,subprocess,hashlib,shutil,binascii
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from redraw_model import native_text,screen_code
from overlays import wrap
from bindings import verify
BASE=ROOT/'build/grid-prose-authority/20261025T190208381544Z/fixture'
LEAF=ROOT/'build/grid-prose-authority/20261025T190208381544Z/leaf'
def build(out,base=BASE):
 out.mkdir(parents=True,exist_ok=True);symbols=json.load(open(base/'build/editor-report.json'))['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');shutil.copy2(LEAF/'helper-witness.inc',out/'helper-witness.inc');(out/'native-witness.inc').write_text('\n'.join('NATIVE_CRC'+str(i)+'='+str(int.from_bytes((base/'build/overlays'/(n+'.seo')).read_bytes()[12:14],'little'))for n,i in [('grid80',16),('grid60',17)])+'\n')
 native=(base/'fonts/native8.bin').read_bytes();codes=sorted({*range(48,58),*range(65,71),*(screen_code(v)for v in native_text('ModifiedClean   '))});assert len(codes)==26;lookup=bytes(codes.index(i)if i in codes else 255 for i in range(128));(out/'status-font.bin').write_bytes(b''.join(native[i*8:i*8+8]for i in codes));(out/'status-lookup.bin').write_bytes(lookup)
 s=(LEAF/'caret.s').read_text();a=s.index(' pha\n asl\n asl\n asl\n sta text_ptr\n pla\n pha\n lsr\n lsr\n lsr\n lsr\n lsr\n and #3\n ora #$BC');s=s[:a]+s[a:].replace(' pha\n asl\n asl\n asl\n sta text_ptr\n pla\n pha\n lsr\n lsr\n lsr\n lsr\n lsr\n and #3\n ora #$BC',' pha\n and #127\n tax\n lda status_lookup,x\n asl\n asl\n asl\n sta text_ptr\n lda #>local_native8',1)
 s=s.replace(' sta text_ptr+1\n lda $DBC0,x',' sta text_ptr+1\n ldx BCOL\n lda $DBC0,x')
 s=s.replace('.incbin "native8.bin"','.incbin "status-font.bin"').replace('local_native8=$BC00','local_native8=$BF00').replace('*-local_native8=1024','*-local_native8=208');s+='\n.segment "RODATA"\nstatus_lookup:.incbin "status-lookup.bin"\n';(out/'caret.s').write_text(s);cfg=(LEAF/'grid.cfg').read_text().replace('start=$BC00','start=$BF00');(out/'grid.cfg').write_text(cfg);objs=[]
 for j,p in enumerate([out/'caret.s',ROOT/'src/render/geos/typing/status-normal.s']):
  o=out/('grid'+str(j)+'.o');subprocess.run(['ca65','-g','-I',out,'-I',ROOT/'src/render/grid/caret','-I',ROOT/'src','-o',o,p],check=True);objs.append(o)
 subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs],check=True);subprocess.run(['ca65','-o',out/'aliases.o',out/'aliases.s'],check=True);subprocess.run(['ld65','-C',out/'grid.cfg','-o',out/'grid.bin','-Ln',out/'grid.lbl','-m',out/'grid.map',*objs,out/'aliases.o'],check=True);raw=(out/'grid.bin').read_bytes();seo=wrap(raw,1,33,api=(symbols['se_overlay_call'],symbols['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'grid.seo').write_bytes(seo);labels={p[2].lstrip('.'):int(p[1],16)for line in(out/'grid.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};result=dict(payload=len(raw),font_bytes=208,lookup_bytes=128,status_codes=codes,font_address=labels['local_native8'],lookup_address=labels['status_lookup'],prefix_free=0xbf00-(labels['status_lookup']+128),sha256=hashlib.sha256(seo).hexdigest());(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return seo,result,labels
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2])if len(sys.argv)>2 else BASE)[1])
