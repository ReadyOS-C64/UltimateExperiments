from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);objects=[]
 def run(a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 for name,path in [('measure',ROOT/'src/render/geos/measure.s'),('glyph',ROOT/'src/render/geos/glyph.s'),('assets',ROOT/'src/render/geos/assets.s'),('loans',D/'coverage-loans.s')]:
  obj=out/(name+'.o');run(['ca65','-g','-I',ROOT/'src','-o',obj,path]);objects.append(obj)
 run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-g','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C',D/'probe.cfg','-o',out/'glyph.bin','-Ln',out/'glyph.lbl',*objects,out/'aliases.o']);ls={p[2].lstrip('.'):int(p[1],16)for l in(out/'glyph.lbl').read_text().splitlines()if(p:=l.split())and p[0]=='al'};return ls,(out/'glyph.bin').read_bytes()
