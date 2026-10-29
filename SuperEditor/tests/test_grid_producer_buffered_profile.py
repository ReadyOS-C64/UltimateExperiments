"""Actual immutable203233 versus private producer: scoped instruction attribution."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json,ctypes as C,subprocess
import test_grid_reflow_profile as profile
import test_geos_fold_editor as fold,test_grid_modes as grid
import test_grid_editor_vice as native
import font_fixture
ROOT=profile.ROOT;BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture';CAND=ROOT/'build/grid-producer-buffered-proof/20261025T211124724943Z/fixture';LEAF=CAND.parent/'leaf'
def instrument(out):
 src=inspect.getsource(profile.run).split(' ident=json.load')[0].replace('def run(out):','def instrument(out):')+' return pd\n'
 resident=json.load(open(BASE/'build/editor-report.json'))['symbols'];scope='if(lp_entry[i]&&(i>=10||(zeropage_peddle_read(m,'+str(resident['se_overlay_active'])+ ')==14&&zeropage_peddle_read(m,'+str(resident['se_overlay_busy'])+')==1))&&'
 src=src.replace("cpp.write_text(s);","s=s.replace('if(lp_entry[i]&&',"+repr(scope)+");cpp.write_text(s);")
 ns=dict(profile.__dict__);exec(compile(src,__file__+':instrument','exec'),ns);return ns['instrument'](out)
def run(out):
 pd=instrument(out);cases=[]
 for variant,base,label in [('control',BASE,ROOT/'build/grid-geowrite-current/producer-control/viewsource.lbl'),('live',CAND,LEAF/'viewsource.lbl')]:
  ident=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=ident['names'];f=fold.Fixture(out,base,pd,True);sy=profile.labels(label);names=['scan','close','event','begin','finish','current','publish','checksum','producer_guard','source_guard','REU_copy'];pcs=[sy.get('guard')if n=='producer_guard'else sy.get('se_fs_guard')if n=='source_guard'else f.s['se_reu_copy']if n=='REU_copy'else sy.get(n)if n in ('current','publish','checksum')else sy['se_sc_'+n]for n in names]
  try:
   for tag,raw,pos in [('mixed422',native.fixture(),0),('dirty4000',grid.native_text('Alpha *'+('word '*800)+'\rTail.'),32),('code4000',grid.native_text(':::asm\r')+b'X'*4000+grid.native_text('\r:::\rTail.'),24),('clean4000',grid.native_text('Alpha '+('word '*800)+'\rTail.'),32)]:
    for width in (60,80):
     f.source(raw);f.command(97 if width==60 else 98);f.position(pos);f.render();f.finish_style();f.key(81);f.put('se_gc_valid',0,1);expected=f.merged();canonical=f.canonical();pd.lp_init((C.c_uint16*16)(*pcs,*([0]*(16-len(pcs)))));start=f.total_instructions;f.render();first=f.total_instructions-start;f.finish_style();total=f.total_instructions-start;want,attrs=grid.expected(f,expected)[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
     metrics={name:dict(calls=pd.lp_count_get(i),inclusive_instructions=pd.lp_total_get(i))for i,name in enumerate(names)};r=dict(variant=variant,tag=tag,width=width,first=first,settled=total,metrics=metrics);cases.append(r);print(json.dumps(r),flush=True)
  finally:f.close()
 result=dict(status='passed',cases=cases,scope='PC-entry/return inclusive instruction counts overlap; actual full public render/style completion with independent allpixels/attributes,canonical andshim. Not nativecycles.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 out=ROOT/'build/grid-producer-buffered-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
