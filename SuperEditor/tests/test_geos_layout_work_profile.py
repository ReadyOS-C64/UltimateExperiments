"""Private C20 GL/metric selfwork profile; no product edits or machine-state probes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,json,re
import test_geos_page_cost_profile as cost
import test_geos_semantic_editor as semantic
import test_geos_fold_editor as fold
import test_grid_editor_vice
ROOT=cost.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture'
def run(out,base):
 spec=importlib.util.spec_from_file_location('layout_window_builder',ROOT/'src/render/geos/style-window-candidate/build-once.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 fixture=b.install(out,base,False)
 fixture,identity=semantic.geos.freeze(out/'profile',fixture)
 # The install directory holds the exact link used in this test.
 candidates=list(out.rglob('geosline.lbl'));assert len(candidates)==1,candidates
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',candidates[0].read_text())}
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=fixture
 names=identity['names'];semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=names
 gate=out/'gate';gate.mkdir();dll=cost.runner(gate);f=fold.Fixture(gate,fixture,dll,True)
 targets=[]
 for n in ['se_geos_line_begin','se_geos_line_step','se_geos_line_finish','se_geos_measure','packet','consumed','map_cell','caret','inline_request','inline_resume','window_try','window_copy','style_remember','reader','style_check']:
  assert n in labels,n
  # CARET/read aliases are local to this single C20 link, never another slot.
  targets.append((n,labels[n],2,names.index('geosline')+1))
 for n in ['se_view_init','se_doc_validate','se_object_validate','se_reu_copy','se_petscii_screen']:
  targets.append((n,f.s[n],0,0))
 for n,slot in [('geosline',2),('geospage',2),('geossema',2),('geosinln',2),('viewsource',1),('geosrow',1),('geospaint',2)]:
  targets.append(('overlay-'+n,0xB010 if slot==2 else 0xA010,slot,names.index(n)+1))
 records=[]
 try:
  fonts={n:(fixture/'fonts'/n).read_bytes() for n in semantic.geos.GEOS_FONTS+('native8.bin',)}
  for tag,data in [('diverse422',test_grid_editor_vice.fixture()),('inline406',semantic.INLINE_FIXTURE),('long863',semantic.geos.native_text('**'+('Wim. '*170)+'end**\rTail.'))]:
   f.source(data);f.command(99);f.position(0);f.put('se_v_top',0);f.render()
   for n in ['se_r_valid','se_gc_valid','se_gc_width']:f.put(n,0,1)
   f.m.write(0xCF90,0);f.m.write(0xCFE8,0)
   canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();f.audit_begin();before=f.total_instructions
   dll.cp_begin(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*[t[1]for t in targets]),(C.c_uint8*len(targets))(*[t[2]for t in targets]),(C.c_uint8*len(targets))(*[t[3]for t in targets]))
   f.render();dll.cp_end();f.dll.fr_end();writes=f.audit_end(reu,tag)
   used=f.total_instructions-before
   assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xC600,1024)==f.shim
   expected=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==expected[0] and f.read(0x4000,1000)==expected[1]
   semantic.geos.png(expected[0],expected[1],gate/(tag+'.png'))
   functions=[]
   for i,(n,pc,slot,ovl) in enumerate(targets):
    m=(C.c_uint64*3)();dll.cp_metrics(i,m);functions.append(dict(name=n,pc=hex(pc),slot=slot,tag=ovl,calls=m[0],inclusive_instructions=m[1],exclusive_instructions=m[2]))
   row=dict(tag=tag,source_bytes=len(data),source_sha256=hashlib.sha256(data).hexdigest(),instructions=used,derived_stashes=writes,functions=functions);records.append(row)
   print(tag,used,[(r['name'],r['calls'],r['inclusive_instructions'],r['exclusive_instructions'])for r in functions if r['name'].startswith('se_geos')],flush=True)
   (out/'progress.json').write_text(json.dumps(records,indent=2)+'\n')
  result=dict(status='passed',identity=identity,records=records,labels=str(candidates[0].relative_to(ROOT)),scope='Actual public forcedfresh TOP0 with released style-window C20 substitution; independent320x200pixels/attrs/source/history/catalog/shim and typed full16MiB guards. Read-only PC/stack observer counts CPU instructions, not cycles. Inclusive nested frames may overlap; exclusive excludes only other listed tracked child functions. No native execution or canonical edits.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-layout-work-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base.resolve())
