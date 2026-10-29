"""One C20 substitution, preserving first-certificate coordinator/all47 assets."""
from pathlib import Path
import json,zipfile,shutil,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
D=Path(__file__).resolve().parent
def cmd(*a):
 p=subprocess.run(list(map(str,a)),cwd=ROOT,capture_output=True,text=True);assert not p.returncode,p.stdout+p.stderr

def build(out,base,control=False):
 out.mkdir(parents=True);src=out/'source';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 assert 'SC_CONSUME' in(src/'src/render/geos/page.s').read_text(),'requires released firstcertificate baseline'
 inc=out/'include/render/geos';inc.mkdir(parents=True)
 if not control:
  for p in D.iterdir():
   if p.suffix in('.s','.inc'):shutil.copy2(p,inc/p.name)
 r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols'];seal=r['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 frozen=json.loads((base/'freeze.json').read_text());font_inputs={}
 for n in('bsw9-original.bin','bsw9-widths.bin'):
  p=base/'fonts'/n;h=hashlib.sha256(p.read_bytes()).hexdigest();assert frozen['fonts'][n]==h;font_inputs[n]=h
 a=(src/'src/render/geos/assets.s').read_text().replace('"assets/fonts/generated/','"'+str(base.resolve()/'fonts')+'/');(out/'assets.s').write_text(a)
 objects=[]
 for tag,path in [('source-line',src/'src/render/geos/source-line.s'if control else D/'source-line.s'),('line',src/'src/render/geos/line.s'),('measure',src/'src/render/geos/measure.s'),('assets',out/'assets.s')]:
  o=out/(tag+'.o');cmd('ca65','-g',*(['-D','SE_EDITOR_GEOS_INLINE=1']if tag=='source-line'else[]),'-I',out,'-I',out/'include','-I',src/'src','-o',o,path);objects.append(o)
 cmd(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'bindings.s',*objects);cmd('ca65','-o',out/'bindings.o',out/'bindings.s');cmd('ld65','-C',src/'cfg/geos-editor-layout.cfg','-o',out/'geosline.bin','-Ln',out/'geosline.lbl','-m',out/'geosline.map',*objects,out/'bindings.o')
 raw=(out/'geosline.bin').read_bytes();assert len(raw)<=4096;image=wrap(raw,1,20,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/'geosline.seo').write_bytes(image)
 if control:assert image==(base/'build/overlays/geosline.seo').read_bytes(),'frozen firstcertificate didnotrebuildbyteidentically'
 result={'payload':len(raw),'sha256':hashlib.sha256(image).hexdigest(),'control':control,'font_inputs':font_inputs,'new_BSS':0,'new_ZP':0,'new_resident':0,'binding':seal};(out/'C20-build.json').write_text(json.dumps(result,indent=2)+'\n')
 if not control:
  objects=[]
  for tag,path in [('fold-entry',D/'fold-entry.s'),('fold-query',src/'src/render/geos/fold-query.s'),('body-cache',D/'body-cache.s')]:
   obj=out/(tag+'.o');cmd('ca65','-g','-I',out,'-I',out/'include','-I',src/'src','-o',obj,path);objects.append(obj)
  cmd(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'rbindings.s',*objects);cmd('ca65','-o',out/'rbindings.o',out/'rbindings.s');cmd('ld65','-C',src/'cfg/overlay-r.cfg','-o',out/'geosfold.bin','-Ln',out/'geosfold.lbl','-m',out/'geosfold.map',*objects,out/'rbindings.o')
  rraw=(out/'geosfold.bin').read_bytes();assert len(rraw)<=4096;rimage=wrap(rraw,0,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/'geosfold.seo').write_bytes(rimage);result['geosfold']={'payload':len(rraw),'sha256':hashlib.sha256(rimage).hexdigest()}
 (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return image,result

def install(out,base,control=False):
 image,result=build(out/'link',base,control);target=out/'fixture';shutil.copytree(base,target);i=json.loads((target/'freeze.json').read_text());(target/'build/overlays/geosline.seo').write_bytes(image);i['assets']['geosline']=result['sha256'];
 if not control:
  shutil.copy2(out/'link/geosfold.seo',target/'build/overlays/geosfold.seo');i['assets']['geosfold']=result['geosfold']['sha256']
 i['private_CPU_substitutions']=['geosline','geosfold'] if not control else []; i['native_disk_packaged']=False;(target/'freeze.json').write_text(json.dumps(i,indent=2)+'\n');return target
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('base',type=Path);p.add_argument('--control',action='store_true');a=p.parse_args();print(build(a.out.resolve(),a.base.resolve(),a.control)[1])
