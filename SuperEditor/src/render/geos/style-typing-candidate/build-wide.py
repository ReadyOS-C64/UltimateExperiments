from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[4]
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'loans.s').write_text(f'.exportzp gt_base,gt_bitmap\ngt_base=${s["text_ptr"]:02x}\ngt_bitmap=${s["screen_ptr"]:02x}\n')
 objects=[]
 for tag,path in [('wide',ROOT/'src/render/geos/style-typing-candidate/wide.s'),('loans',out/'loans.s')]:
  o=out/(tag+'.o');subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(o),str(path)],cwd=ROOT,check=True);objects.append(o)
 subprocess.run(['ld65','-C',str(ROOT/'src/render/geos/style-typing-candidate/transform.cfg'),'-o',str(out/'wide.bin'),'-Ln',str(out/'wide.lbl'),*map(str,objects)],cwd=ROOT,check=True);image=(out/'wide.bin').read_bytes();labels={p[2].lstrip('.'):int(p[1],16)for line in(out/'wide.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};return image,labels
if __name__=='__main__':p,s=build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve());print('wide',len(p))
