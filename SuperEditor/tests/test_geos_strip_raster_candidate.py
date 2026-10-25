"""Private exact strip-height R21 work avoidance; no production/shared build."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
import test_geos_literal_byte_candidate as proof
from overlays import wrap
ROOT=proof.ROOT;D=ROOT/'src/render/geos/strip-raster-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'

def build(out,base,variant):
 out.mkdir(parents=True);src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 fonts=src/'assets/fonts/generated';fonts.mkdir(parents=True,exist_ok=True)
 for n in ('bsw9-original.bin','bsw9-widths.bin','bsw9.bin'):shutil.copy2(base/'fonts'/n,fonts/n)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];binding=report['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_f_owner\n.importzp text_ptr,screen_ptr\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');objects=[]
 for name in proof.leaf.SOURCES:
  stem=name.rsplit('/',1)[-1];source=(D/(stem+'.s')if variant=='candidate'else src/'src/render/geos/literal-byte'/(stem+'.s'))if stem in ('row','measure','glyph','assets')else src/('src/'+name+'.s');obj=out/(name.replace('/','-')+'.o')
  subprocess.run(['ca65','-g','-I',str(out),'-I',str(src/'src'),'-o',str(obj),str(source)],cwd=src,check=True);objects.append(obj)
 def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects);command('ca65','-g','-o',out/'aliases.o',out/'aliases.s');command('ld65','-C',src/'cfg/geos-editor-row.cfg','-o',out/'geosrow.bin','-Ln',out/'geosrow.lbl','-m',out/'geosrow.map',*objects,out/'aliases.o')
 raw=(out/'geosrow.bin').read_bytes();assert len(raw)<=4096
 labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'geosrow.lbl').read_text())};assert labels['se_geos_packed']==0xabf3 and labels['se_geos_widths']==0xaedb and labels['row_clear']==0xaf5b
 image=wrap(raw,0,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(out/'geosrow.seo').write_bytes(image)
 if variant=='control':assert image==(base/'build/overlays/geosrow.seo').read_bytes(),'actualcurrentR21notbyteidentical'
 modules={}
 for name,body in re.findall(r'^(\S+)\.o:\n(.*?)(?=^\S+\.o:|^Segment list:)',(out/'geosrow.map').read_text(),re.M|re.S):modules[name]={n:(int(o,16),int(size,16))for n,o,size in re.findall(r'^\s+(\w+)\s+Offs=([0-9A-F]+)\s+Size=([0-9A-F]+)',body,re.M)}
 return src,s,labels,raw,image,modules

def prepare(out,base,variant):
 link=out/'link';src,s,labels,raw,image,modules=build(link,base,variant);return link,src,s,labels,raw,image,modules

def main():
 p=argparse.ArgumentParser();p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--suite',choices=['fit','component','inline','incremental','fold'],default='fit');p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-strip-raster'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 proof.prepare=prepare;proof.PRIVATE=D
 if a.suite=='fit':
  _,_,_,_,raw,image,modules=prepare(out,a.base.resolve(),a.variant);result=dict(status='fits',variant=a.variant,payload=len(raw),sha256=hashlib.sha256(image).hexdigest(),segments=modules);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
 elif a.suite=='component':proof.component(out,a.base.resolve(),a.variant)
 else:proof.public_gate(out,a.base.resolve(),a.variant,a.suite)
if __name__=='__main__':main()
