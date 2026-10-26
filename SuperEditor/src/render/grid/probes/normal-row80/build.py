"""Private R16 all-normal row specialization; exact committed control first."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[5];D=Path(__file__).resolve().parent
BASE=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture'
def command(*args):
 r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
def build(out,base=BASE):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(tree)
 report=json.loads((base/'build/editor-report.json').read_text());digest=report['resident_binding']['digest'];s=report['symbols']
 (out/'editor-api.inc').write_text('\n'.join(f'{k} = ${v:04X}'for k,v in s.items())+'\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 for name in ('narrow4','native8'):
  target=tree/f'assets/fonts/generated/{name}.bin';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/f'fonts/{name}.bin',target)
 def link(name,row):
  folder=out/name;folder.mkdir();objects=[]
  paths=[tree/'src/overlays/grid.s',row,*[tree/f'src/render/narrow/{x}.s'for x in ('cell8','font4','native8')]]
  for i,path in enumerate(paths):
   obj=folder/f'{i}.o';command('ca65','-g','-D','SE_FIXED_NARROW_FONT=1','--bin-include-dir',tree,'-I',out,'-I',tree/'src','-o',obj,path);objects.append(obj)
   segments=command('od65','--dump-segments',obj)
   for seg,size in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',segments,re.S):
    assert not(seg in ('BSS','ZEROPAGE','DATA')and int(size)),(seg,size)
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',folder/'aliases.s',*objects)
  command('ca65','-o',folder/'aliases.o',folder/'aliases.s');objects.append(folder/'aliases.o')
  command('ld65','-C',tree/'cfg/grid-r.cfg','-o',folder/'leaf.bin','-Ln',folder/'leaf.lbl','-m',folder/'leaf.map',*objects)
  raw=(folder/'leaf.bin').read_bytes();assert len(raw)==4096
  assert raw[0x800:0xc00]==(base/'fonts/narrow4.bin').read_bytes()
  assert raw[0xc00:]==(base/'fonts/native8.bin').read_bytes()
  return raw
 original=link('control',tree/'src/render/narrow/row80.s');assert original==(base/'build/overlays/grid80.seo').read_bytes()[36:],'control must exactly reassemble committed R16'
 candidate=link('candidate',D/'row80.s')
 sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
 seo=wrap(candidate,0,16,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'candidate/leaf.seo').write_bytes(seo)
 result=dict(status='PASS',control_exact=True,control_sha256=hashlib.sha256(original).hexdigest(),candidate_sha256=hashlib.sha256(candidate).hexdigest(),resident=report['sha256'],binding=digest,new_BSS=0,new_ZP=0,payload=4096,font_addresses=[0xa800,0xac00],font_bytes_exact=True)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
def packaged(out,base=BASE):
 """Keep native-font authentication: rebuild C33 against the actual R16 CRC."""
 budget=build(out,base);fixture=out/'fixture';shutil.copytree(base,fixture)
 identity=json.loads((fixture/'freeze.json').read_text())
 image=(out/'candidate/leaf.seo').read_bytes();(fixture/'build/overlays/grid80.seo').write_bytes(image)
 identity['assets']['grid80']=hashlib.sha256(image).hexdigest()
 (fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 spec=importlib.util.spec_from_file_location('normal_row80_c33_builder',ROOT/'src/render/grid/caret/build.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
 control,_,_=bridge.build(out/'control-c33',base)
 assert control==(base/'build/overlays/grid.seo').read_bytes(),'exact C33 reassembly before witness change'
 candidate,_,_=bridge.build(out/'candidate-c33',fixture)
 assert (out/'control-c33/geostail.seo').read_bytes()==(base/'build/overlays/geostail.seo').read_bytes(),'exact R25 control reassembly'
 helper=(out/'candidate-c33/geostail.seo').read_bytes();(fixture/'build/overlays/geostail.seo').write_bytes(helper);identity['assets']['geostail']=hashlib.sha256(helper).hexdigest()
 (fixture/'build/overlays/grid.seo').write_bytes(candidate);identity['assets']['grid']=hashlib.sha256(candidate).hexdigest()
 for name,origin in [('grid80',out/'candidate/leaf'),('grid',out/'candidate-c33/grid'),('geostail',out/'candidate-c33/geostail')]:
  for ext in ('bin','lbl','map'):shutil.copyfile(origin.with_suffix('.'+ext),fixture/f'build/overlays/{name}.{ext}')
 # Same-sized replacements preserve all directory metadata/sector links. An
 # independent reader then authenticates every file, including untouched ones.
 from d81_image import D81Image
 disk=bytearray((base/'build/supereditor.d81').read_bytes());old=D81Image(disk)
 for name in ('grid80','grid','geostail'):
  file=old.read(name.upper().encode(),kind=1);data=(fixture/f'build/overlays/{name}.seo').read_bytes();assert len(data)==len(file.data)
  position=0
  for track,sector,raw in file.sectors:
   n=254 if raw[0]else raw[1]-1;at=((track-1)*40+sector)*256+2;disk[at:at+n]=data[position:position+n];position+=n
  assert position==len(data)
 checked=D81Image(disk)
 assert checked.entries()==old.entries()
 for entry in old.entries():
  before=old.read(entry.name);after=checked.read(entry.name)
  if entry.name in (b'GRID80',b'GRID',b'GEOSTAIL'):assert after.data==(fixture/f'build/overlays/{entry.name.decode().lower()}.seo').read_bytes()
  else:assert before==after,(entry.name,'untouched file bytes/chains')
 (fixture/'build/supereditor.d81').write_bytes(disk);identity['disk_sha256']=hashlib.sha256(disk).hexdigest()
 # Derivation source differs in exactly the private row implementation. C33
 # source is unchanged; its generated witness uses the genuine new R16.
 src=fixture/'product-sources.zip';saved=src.read_bytes()
 import io
 with zipfile.ZipFile(io.BytesIO(saved))as z,zipfile.ZipFile(src,'w',zipfile.ZIP_DEFLATED)as dest:
  for name in z.namelist():dest.writestr(name,(D/'row80.s').read_bytes()if name=='src/render/narrow/row80.s'else z.read(name))
 identity['sources']['src/render/narrow/row80.s']=hashlib.sha256((D/'row80.s').read_bytes()).hexdigest();identity['source_policy']='Private R16 normal-role row plus exact-generated C33 native witness; other56 assets and resident unchanged.'
 (fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 budget.update(packaged_assets_changed=['grid80','grid','geostail'],D81_files_audited=len(old.entries()),D81=identity['disk_sha256'],C33_witness_authentic=True)
 (out/'result.json').write_text(json.dumps(budget,indent=2)+'\n');return fixture,budget
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--packaged',action='store_true');a=p.parse_args();print(packaged(a.out.resolve())[1]if a.packaged else build(a.out.resolve()))
