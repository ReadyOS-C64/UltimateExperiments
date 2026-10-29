"""Private checked contiguousC22 packet gather, no product/sharedbuild edits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile,inspect
import test_geos_identity_candidate as identity
import test_geos_literal_byte_candidate as public
from overlays import wrap,HEADER
ROOT=identity.ROOT;D=ROOT/'src/render/geos/paint-packet-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T174216345896Z/fixture'
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True);assert not p.returncode,p.stdout+p.stderr

def build(out,base,variant='candidate'):
 out.mkdir(parents=True);src=out/'source';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];seal=report['resident_binding']['digest'];api=out/'editor-api.inc';api.write_text('.import se_overlay_call,se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');objects=[]
 for tag,name in [('entry','page-paint-entry'),('paint','page-paint'),('pan','native-pan'),('cache','cache-paint')]:
  source=D/'page-paint.s'if variant=='candidate'and tag=='paint'else src/'src/render/geos'/(name+'.s');obj=out/(tag+'.o');command('ca65','-g','-I',out,'-I',src/'src','-o',obj,source);objects.append(obj)
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'bindings.s',*objects);command('ca65','-g','-o',out/'bindings.o',out/'bindings.s');command('ld65','-C',src/'cfg/geos-editor-page.cfg','-o',out/'paint.bin','-Ln',out/'paint.lbl','-m',out/'paint.map',*objects,out/'bindings.o')
 raw=(out/'paint.bin').read_bytes();assert len(raw)<=4096
 image=wrap(raw,1,22,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/'geospaint.seo').write_bytes(image)
 if variant=='control':assert image==(base/'build/overlays/geospaint.seo').read_bytes(),'sealedcurrentC22notbyteidentical'
 (out/'build.json').write_text(json.dumps(dict(status='fits',variant=variant,payload=len(raw),sha256=hashlib.sha256(image).hexdigest(),new_BSS=0,new_ZP=0,new_state=0),indent=2)+'\n');return image

def install(out,base,variant):
 image=build(out/'link',base,variant);fixture=out/'fixture';shutil.copytree(base,fixture);(fixture/'build/overlays/geospaint.seo').write_bytes(image);i=json.loads((fixture/'freeze.json').read_text());i['assets']['geospaint']=hashlib.sha256(image).hexdigest();i['private_C22_packet_gather']=variant;(fixture/'freeze.json').write_text(json.dumps(i,indent=2)+'\n');return fixture

def main():
 p=argparse.ArgumentParser();p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--suite',choices=['fit','inline','fold','incremental','boundaries','identity'],default='fit');p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-paint-packet'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);base=a.base.resolve()
 if a.suite=='fit':print('FIT',len(build(out/'link',base,a.variant))-36,flush=True);return
 fixture=install(out,base,a.variant);target=out/'public';target.mkdir()
 if a.suite=='inline':import test_geos_semantic_editor as gate;result=gate.run(target,fixture,inline_case=True)
 elif a.suite=='fold':import test_geos_fold_editor as gate;result=gate.run(target,fixture)
 elif a.suite=='incremental':import test_geos_incremental_editor as gate;result=gate.run(target,fixture)
 else:
  def pair_build(where,frozen):return build(where/'candidate',frozen,'candidate'),build(where/'control',base,'control')
  identity.build=pair_build
  if a.suite=='boundaries':
   # Reuse the exact current actual-C21/A-B/wholeRAM/16MiB guard body, with
   # explicit packet seam cases. No historical nowrap FE allowlist mutation.
   source=inspect.getsource(identity.run)
   needle="  data=semantic.FIXTURE;setup(data,15);check(data,'mixed-full')"
   replacement=needle+"\n"+"\n".join([
    "  for count in(1,34,63,64,65,127,128,129,160):",
    "   data=b'.'*count+b'\\rTail.';setup(data);check(data,'packet-count-'+str(count))",
    "  data=b'.'*200+b'\\rTail.';setup(data,1)",
    "  for x in(f,g):x.command(75);x.put('se_l_pan',1);x.put('se_l_manual',1,1)",
    "  check(data,'packet-count161-negative-left')"])
   assert source.count(needle)==1
   ns=dict(identity.__dict__);exec(source.replace(needle,replacement),ns)
   result=ns['run'](target,fixture,smoke=True)
  else:result=identity.run(target,fixture)
  result['scope']='ActualABI3 C21-generated rows, candidate/control C22, independent pixel/layout model and poisoned unused legacy arrays; original fullRAM/16MiB/source/foreignowner/dirty-band guards retained. No source map migration claim.'
 if result is None:result=json.loads((target/'result.json').read_text())
 result['packet_gather_variant']=a.variant;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
