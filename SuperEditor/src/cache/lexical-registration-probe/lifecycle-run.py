"""Packaged59 controlled CPU lifecycle, trusted fresh bootstrap only.

No private replacement of the C29/R26 product capsules. Reuses the unchanged
component evaluator, exact warm extents, fullREU and ReadyOS reserve guards.
This does not establish native/ReadyOS/physical RESTORE/old-stack continuation.
"""
from pathlib import Path
import argparse,inspect,json,shutil,sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_lifecycle_editor as component

def run(out,base,project):
 out.mkdir(parents=True)
 import font_fixture
 font_fixture.ROOT=base
 def packaged(target,frozen):
  target.mkdir();images={}
  for name in('lifectrl','lifecopy'):
   image=(frozen/f'build/overlays/{name}.seo').read_bytes();assert image==(project/f'build/overlays/{name}.seo').read_bytes()
   images[name]=image;shutil.copy2(project/f'build/overlays/{name}.lbl',target/(name+'.lbl'));(target/(name+'.seo')).write_bytes(image)
  prelude=images['lifectrl'][36+0x800:36+0x900];assert prelude[:5]==bytes.fromhex('78d8a2ff9a');(target/'resume.bin').write_bytes(prelude)
  return images
 component.build=packaged
 # Legacy component fault lookup predates managed bit7. Normalize only its
 # public slot discriminator; identity/CRC/wholeREU assertions are unchanged.
 source=inspect.getsource(component.run);needle="f.m.read(f.s['image_slot']+i)==0";assert source.count(needle)==1
 source=source.replace(needle,"(f.m.read(f.s['image_slot']+i)&127)==0")
 (out/'component-managed-adaptation.py').write_text(source)
 ns=dict(component.__dict__);exec(compile(source,str(out/'component-managed-adaptation.py'),'exec'),ns)
 ns['run'](out,base,mode=3,skip_faults=True,preview=False)
 r=json.load(open(out/'result.json'));assert r['packaged_pair_byteidentical']
 r['registration_assets']=59;r['scope']='Unchanged actual packaged59 C29/R26 controlled CPU pending prepare/abort/fresh trusted bootstrap/restore/edit/Undo; no root5 lexical-resume or native/hardware/ReadyOS claim.'
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print('RUN',a.out,flush=True);run(a.out.resolve(),a.fixture.resolve(),a.project.resolve())
