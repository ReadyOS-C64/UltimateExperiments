"""Actual C6 neighbor ink-role certification; private sealed replacement only."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,shutil,importlib.util
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
BASE=ROOT/'build/geos-incremental-editor/20261025T104900415766Z/fixture'

def run(out,base=BASE):
 frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('neighbor_build',ROOT/'src/render/geos/style-typing-candidate/build-c6-neighbors.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);payload,image=b.build(out/'candidate',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};cases=[];faults=[]
 def install():
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==6 and f.m.read(f.s['image_slot']+i)==1:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active']+1,0);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
 def setup(data,at):f.source(data);f.command(99);f.position(at);f.render();install()
 def check(tag,key,wanted):
  canonical=f.canonical();reu=f.reu();before=f.merged();caret=f.get('se_hot_caret');f.key(key);assert f.m.read(0x9149)==wanted,(tag,'cert',f.m.read(0x9149));pending=f.canonical();changed=f.merged();loads=f.get('se_overlay_loads',2);start=f.total_instructions;f.render();instructions=f.total_instructions-start
  bits,attrs,_,_=semantic.expected(f,changed,fonts);actual=f.read(0x6000,8000);colors=f.read(0x4000,1000);assert actual==bits and colors==attrs,(tag,'fullpixels',[(i,a,b)for i,(a,b)in enumerate(zip(colors,attrs))if a!=b][:10])
  assert f.canonical()==pending and f.read(0xc600,1024)==f.shim and not f.get('se_f_owner',1)
  cache,bank=f.raw_cache();at=bank*65536;now=f.reu();assert now[:at]==reu[:at] and now[at+65536:]==reu[at+65536:],(tag,'foreign16MiB')
  fold.geos.png(actual,colors,out/(tag+'.png'));item=dict(tag=tag,certified=wanted,instructions=instructions,loads=(f.get('se_overlay_loads',2)-loads)&65535,attr160=colors[160]);cases.append(item);print('PASS',item,flush=True)
 def write_fe(offset,data):
  f.m.load(0x8080,data);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',len(data),2);assert not f.call('se_reu_copy',0).p&1
 try:
  setup(fold.geos.native_text('Intro.\rjjj\r- .\rTail.'),9);assert f.read(0x4000+120,80)==bytes([0x16])*80;check('minority-neighbor-correct36',0x14,0);assert cases[-1]['attr160']==0x36
  data=fold.geos.native_text('Plain row having ample room\rSecond plain row\rTail.');setup(data,7);check('normal-insert',ord('X'),1);check('normal-backspace',0x14,1);assert cases[-1]['loads']==0
  data=fold.geos.native_text('Plain row having ample room\rAnother white row\rThird white row\r- colored list\rTail.');setup(data,7);check('nonintersecting-color-insert',ord('Q'),1);check('nonintersecting-color-delete',0x14,1)
  # Explicit malformed derived-cache injection: bounds must never turn the
  # role read into a span outside the fixed161byte array or ownedFE bank.
  for count,role,wanted in [(161,0,1),(161,7,0),(162,0,0),(256,0,0),(65535,0,0)]:
   data=fold.geos.native_text('Plain row having ample room\rSecond plain row\rTail.');setup(data,7);row=1;offset=0x200+row*0x800;write_fe(offset+12,count.to_bytes(2,'little'));write_fe(offset+356,bytes(160)+bytes([role]));snapshot=f.reu();f.key(ord('X'));assert f.m.read(0x9149)==wanted,(count,role,wanted,f.m.read(0x9149));assert f.reu()==snapshot and not f.get('se_f_owner',1) and f.read(0xc600,1024)==f.shim
   faults.append(dict(tag='neighbor-role-count',count=count,last_role=role,certified=wanted));print('FAULT',faults[-1],flush=True)
  for field in ['se_gc_epoch','se_reu_logical_owner','se_reu_physical_owner']:
   setup(data,7);handle=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+handle);offset=handle if field.endswith('logical_owner')else physical if field.endswith('physical_owner')else 0;address=f.s[field]+offset;old=f.m.read(address);f.m.write(address,old^1);snapshot=f.reu();f.key(ord('X'));assert f.m.read(0x9149)==0 and f.reu()==snapshot and not f.get('se_f_owner',1),(field,'refusal');f.m.write(address,old);faults.append(dict(tag=field,certified=0))
  result=dict(status='passed',C6=len(payload),newBSS=0,newZP=0,cases=cases,faults=faults,scope='Private actual C6 producer replacement on immutable46; actual pending edits/rootR30 or existingR28/fullfallback. Independent everypixel/attribute/source/history/foreign16MiB/shim, explicit derivedcache faults. No canonical production edits/native claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-neighbor-proof'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
