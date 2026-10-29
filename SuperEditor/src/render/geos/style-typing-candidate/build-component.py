from pathlib import Path
import json,sys,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parents[4]
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);prod=out/'production';prod.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith(('src/','assets/')) and not name.endswith('/'):
    p=prod/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 target=prod/'assets/fonts/generated';target.mkdir(parents=True,exist_ok=True)
 for name in ['bsw9-original.bin','bsw9-widths.bin']:shutil.copy2(base/'fonts'/name,target/name)
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'loans.s').write_text(f'.exportzp se_gg_context,se_gg_pointer\nse_gg_context=${s["text_ptr"]:02x}\nse_gg_pointer=${s["screen_ptr"]:02x}\n')
 objects=[]
 def run(a):subprocess.run(list(map(str,a)),cwd=prod,check=True)
 for name,path in [('transform',ROOT/'src/render/geos/style-typing-candidate/transform.s'),('measure',prod/'src/render/geos/measure.s'),('glyph',prod/'src/render/geos/glyph.s'),('assets',prod/'src/render/geos/assets.s'),('converter',prod/'src/tui/petscii.s'),('inline',prod/'src/supermark/inline.s'),('loans',out/'loans.s')]:
  o=out/(name+'.o');run(['ca65','-g','-I',prod/'src','-I',ROOT/'src','-o',o,path]);objects.append(o)
 run(['ld65','-C',ROOT/'src/render/geos/style-typing-candidate/component.cfg','-o',out/'component.bin','-Ln',out/'component.lbl','-m',out/'component.map',*objects]);image=(out/'component.bin').read_bytes();labels={p[2].lstrip('.'):int(p[1],16)for line in(out/'component.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};assert len(image)<=4096;return image,labels
if __name__=='__main__':p,l=build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve());print('component',len(p))
