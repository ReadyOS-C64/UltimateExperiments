"""Measure actual existing R16/R17 service space; no shared build or new IDs."""
from pathlib import Path
import sys,json,hashlib,zipfile,shutil,subprocess,re
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'agentsworking/evidence/M8/20261026T083129610982Z-grid-capture-cost/fixture'
SOURCES=ROOT/'agentsworking/evidence/M8/20261026T083129610982Z-grid-capture-cost/release/generated-sources.zip'
def build(out):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(SOURCES)as z:z.extractall(tree)
 fonts=tree/'assets/fonts/generated';fonts.mkdir(parents=True,exist_ok=True)
 for n in('narrow4.bin','narrow5.bin','native8.bin'):shutil.copy2(BASE/'fonts'/n,fonts/n)
 s=json.loads((BASE/'build/editor-report.json').read_text())['symbols'];digest=json.loads((BASE/'build/editor-report.json').read_text())['resident_binding']['digest']
 (out/'editor-api.inc').write_text('se_overlay_frame=$%04x\ntext_ptr=$%02x\nscreen_ptr=$%02x\nse_petscii_screen=$%04x\n.macro OVL_BINDING\n.byte '%(s['se_overlay_frame'],s['text_ptr'],s['screen_ptr'],s['se_petscii_screen'])+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 results={}
 for width,ident,paths in[(80,16,['src/overlays/grid.s','src/render/narrow/row80.s','src/render/narrow/cell8.s','src/render/narrow/font4.s','src/render/narrow/native8.s']),(60,17,['src/overlays/grid.s','src/render/narrow/row.s','src/render/narrow/arbitrate.s','src/render/narrow/cell8.s','src/render/narrow/font5.s','src/render/narrow/native8.s'])]:
  d=out/str(width);d.mkdir();objs=[]
  for i,path in enumerate(paths):
   defs=['-D','GRID60=1']if width==60 and i==0 else['-D','SE_FIXED_NARROW_FONT=1']if path.endswith('font4.s')else[];o=d/(str(i)+'.o');subprocess.run(['ca65','-g',*defs,'-I',out,'-I',tree/'src','-o',o,tree/path],cwd=tree,check=True);objs.append(o)
  subprocess.run(['ld65','-C',tree/'cfg/grid-r.cfg','-o',d/'grid.bin','-Ln',d/'grid.lbl','-m',d/'grid.map',*objs],check=True)
  raw=(d/'grid.bin').read_bytes();image=(BASE/'build/overlays'/('grid'+str(width)+'.seo')).read_bytes();assert raw==image[36:],str(width)+' renderer control is not byte-identical'
  label={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(d/'grid.lbl').read_text())};assert label['se_native_font8']==0xac00 and label['se_narrow_font'+('4'if width==80 else'5')]==0xa800
  results[str(width)]={'payload':len(raw),'byte_identical':True,'segments':(d/'grid.map').read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip(),'sha256':hashlib.sha256(image).hexdigest()}
 (out/'result.json').write_text(json.dumps({'status':'PASS','results':results},indent=2)+'\n');return results
if __name__=='__main__':print(json.dumps(build(Path(sys.argv[1]).resolve()),indent=2))
