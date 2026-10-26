"""Private C7/R22 View discovery: exact control, real public keys, no shared build.

CPU uses unchanged packaged resident/other57 capsules with explicit ROM/font
transport seams. Candidate D81 is real; no native or physical-key claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile,os,re
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_geos_editor as geos
import test_geos_semantic_editor as semantic
import test_geos_preview_editor as preview
import test_geos_preview_settings as settings_ui
import font_fixture
from overlays import wrap
from d81_image import D81Image
from geos_preview_model import render,FontCatalog
BASE=ROOT/'build/nr-committed/20261026T210259832190Z/fixture'
PRIVATE=ROOT/'src/tui/view-menu-probe'
DATA=geos.native_text('Menu text stays unchanged.\rAnother source line.\rTail.')
LABELS=['4  40 columns / source','6  60 columns / source','8  80 columns / source',
 'H  GEOS hires','W  Toggle soft wrap     F4','L  Pan left 20 columns',
 'R  Pan right 20 columns','P  Preview / source (GEOS)','S  Preview settings...']
def sha(data):return hashlib.sha256(data).hexdigest()
def shell(*args,cwd=ROOT):subprocess.run([str(x)for x in args],cwd=cwd,check=True,stdout=subprocess.DEVNULL)
def labels(p):return {x[2].lstrip('.'):int(x[1],16)for l in p.read_text().splitlines()if len(x:=l.split())==3}
def build(out,base):
 out.mkdir(parents=True);tree=out/'source';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  queue=['src/overlays/editor-menu.s','src/overlays/editor-popups.s','src/tui/box40.s','cfg/overlay-c.cfg','cfg/overlay-r.cfg'];seen=set()
  while queue:
   n=queue.pop()
   if n in seen:continue
   seen.add(n);data=z.read(n);p=tree/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   for inc in re.findall(rb'\.include\s+"([^"\n]+)"',data):
    name=inc.decode();candidates=['src/'+name,str(Path(n).parent/name)]
    found=next((v for v in candidates if v in z.namelist()),None)
    if found:queue.append(found)
 report=json.loads((base/'build/editor-report.json').read_text());digest=bytes.fromhex(report['resident_binding']['digest'])
 extras='object_owner object_banks object_size_lo object_size_mid object_size_hi tui_putc40 tui_color tui_box_x tui_box_y tui_box_w tui_box_h box_rx box_ry text_ptr screen_ptr'.split()
 shell(sys.executable,ROOT/'tools/overlay_api.py','--report',base/'build/editor-report.json','--output',tree/'editor-api.inc','--all-public','--symbols',*extras)
 defs=tree/'build/editor-settings';defs.mkdir(parents=True)
 raw=(base/'build/overlays/menu40.bin').read_bytes();lab=labels(base/'build/overlays/menu40.lbl')
 for filename,start,end in [('editor-defaults.bin','settings_defaults','settings_defaults_end'),('editor-font-catalog.bin','settings_catalog','settings_catalog_end')]:
  (defs/filename).write_bytes(raw[lab[start]-0xb000:lab[end]-0xb000])
 assert (defs/'editor-defaults.bin').stat().st_size==64 and (defs/'editor-font-catalog.bin').stat().st_size==220
 (defs/'presentation-defaults.inc').write_text('SE_PRESENTATION_DEFAULT='+str(report['symbols']['se_presentation_default'])+'\n')
 records={};budgets={}
 for variant in ('control','candidate'):
  dest=out/variant;dest.mkdir()
  if variant=='candidate':shutil.copy2(PRIVATE/'menu-data.inc',tree/'src/editor/menu-data.inc')
  for name,source,defines in [('menu40','src/overlays/editor-menu.s',()),('popups','src/overlays/editor-popups.s',()),('box40','src/tui/box40.s',('-D','EDITOR_OVERLAY=1'))]:
   shell('ca65','-g',*defines,'-I',tree/'src','-I',tree,'-I',defs,'-o',dest/(name+'.o'),tree/source,cwd=tree)
  for name,cfg,objs,slot,id_ in [('menu40','overlay-c.cfg',['menu40'],1,7),('popups','overlay-r.cfg',['popups','box40'],0,22)]:
   shell('ld65','-C',tree/'cfg'/cfg,'-o',dest/(name+'.bin'),'-Ln',dest/(name+'.lbl'),'-m',dest/(name+'.map'),*[dest/(n+'.o')for n in objs])
   payload=(dest/(name+'.bin')).read_bytes();assert len(payload)<=4096
   image=wrap(payload,slot,id_,api=(report['symbols']['se_overlay_call'],report['symbols']['se_overlay_frame']),binding_digest=digest)
   (dest/(name+'.seo')).write_bytes(image);budgets[variant+'_'+name]=len(payload)
   if variant=='control':assert image==(base/f'build/overlays/{name}.seo').read_bytes(),(name,'control not byte-identical')
   else:records[name]=image
 private=out/'fixture';shutil.copytree(base,private,copy_function=os.link)
 identity=json.loads((private/'freeze.json').read_text());identity['private_view_menu_base']=str(base)
 identity['source_parent_commit']=identity.get('git_commit');identity['git_commit']=None
 identity['source_policy']='Private source variant: exact committed parent archive except declared src/editor/menu-data.inc; not an exact Git checkout.'
 identity['private_source_changes']=['src/editor/menu-data.inc']
 for name,image in records.items():
  target=private/f'build/overlays/{name}.seo';target.unlink();target.write_bytes(image)
  for suffix in ['bin','lbl','map']:
   target=private/'build/overlays'/(name+'.'+suffix);target.unlink();shutil.copy2(out/'candidate'/(name+'.'+suffix),target)
  identity['assets'][name]=sha(image)
 disk=private/'build/supereditor.d81';disk.unlink();shutil.copy2(base/'build/supereditor.d81',disk)
 for name in records:shell('c1541','-attach',disk,'-delete',name,'-write',private/f'build/overlays/{name}.seo',name+',s')
 a=D81Image((base/'build/supereditor.d81').read_bytes());b=D81Image(disk.read_bytes())
 for e in a.entries():assert b.read(e.name).data==(records.get(e.name.decode().lower()) or a.read(e.name).data),(e.name,'undeclared disk member changed')
 (private/'product-sources.zip').unlink()
 with zipfile.ZipFile(base/'product-sources.zip')as z,zipfile.ZipFile(private/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as w:
  for n in z.namelist():w.writestr(n,(PRIVATE/'menu-data.inc').read_bytes()if n=='src/editor/menu-data.inc'else z.read(n))
 identity['sources']['src/editor/menu-data.inc']=sha((PRIVATE/'menu-data.inc').read_bytes());identity['disk_sha256']=sha(disk.read_bytes());identity['private_changed_assets']=list(records)
 (private/'freeze.json').unlink()
 (private/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 return private,budgets
class Bare:
 def __init__(self,f):self.f=f
 def get(self,n,w=3):return 0 if n in ('se_e_ui','se_e_menu')else self.f.get(n,w)
 def __getattr__(self,n):return getattr(self.f,n)
def popup(f,data):
 matrix,colors,_=geos.grid.logical_ui(Bare(f),data);matrix,colors=bytearray(matrix),bytearray(colors)
 for y in range(11):
  for x in range(35):
   at=(y+3)*40+x+1;border=x in (0,34)or y in(0,10);v=32
   if y==0:v=0x70 if x==0 else 0x6e if x==34 else 0x40
   elif y==10:v=0x6d if x==0 else 0x7d if x==34 else 0x40
   elif x in(0,34):v=0x5d
   matrix[at]=v;colors[at]=14 if border else 1
 for i,label in enumerate(LABELS):
  raw=bytes(geos.grid.screen_code(v)for v in geos.native_text(label));at=(i+4)*40+3
  if i==f.get('se_e_item',1):raw=bytes(v^128 for v in raw)
  matrix[at:at+len(raw)]=raw;colors[at:at+len(raw)]=bytes([3 if i==f.get('se_e_item',1)else 1])*len(raw)
 return bytes(matrix),bytes(colors)
def run(out,base,reuse=None):
 out.mkdir(parents=True,exist_ok=True)
 if reuse:
  private,budget=reuse
 else:private,budget=build(out/'link',base)
 ident=json.loads((private/'freeze.json').read_text())
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=font_fixture.ROOT=private
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=ident['names'];assert len(ident['names'])==59
 # Immutable font pack comes from the same packaged disk, not a mutable build.
 pack=private/'build/geos-font-catalog/font-pack.bin';expected_pack=D81Image((private/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
 if pack.exists():assert pack.read_bytes()==expected_pack,'frozen fontpack mismatch'
 else:pack.parent.mkdir(parents=True,exist_ok=True);pack.write_bytes(expected_pack)
 dll=geos.grid.runner(out);f=preview.Fixture(out,private,dll,True);frames=[];checks=[]
 fonts={n:(private/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};defaults=(out/'link/source/build/editor-settings/editor-defaults.bin').read_bytes();data=DATA
 def key(v,error=0):return f.key(geos.native_text(v)[0]if isinstance(v,str)else v,error)
 def state():return (f.canonical(),f.catalog(),f.read(f.s['se_bc_ticket'],4)+f.read(f.s['se_bc_incarnation'],4)+f.read(f.s['se_bc_ring'],96),f.merged())
 def guard(before,tag):
  assert state()==before,(tag,'canonical/history/selection/clipboard/catalog/observer source changed')
  assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in('se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned')),(tag,'owned job/lease or shim')
  checks.append(tag)
 def frame(tag,kind=None):
  before=state();r=f.reu();f.render();guard(before,tag)
  after=f.reu()
  if kind=='preview':preview.guard_preview_reu(f,r,after,tag)
  else:
   # UI-only draws are read-only; source/caret cache publication is primed before interval.
   assert r==after,(tag,'whole16MiB changed on UI draw')
  mode=f.get('se_mode',1)
  if kind=='view':matrix,colors=popup(f,data);rect=(1,3,35,11)
  elif kind=='settings':
   # The released dialog oracle is explicitly source40-only. Borrow its
   # dialog rectangle, never interpret a narrow bitmap as logical characters.
   class Logical40(Bare):
    def get(self,n,w=3):return 0 if n=='se_mode'else self.f.get(n,w)
   sm,sc=settings_ui.popup_model(Logical40(f),data,f.read(f.s['se_editor_settings'],64),None)
   matrix,colors,_=geos.grid.logical_ui(Bare(f),data);matrix,colors=bytearray(matrix),bytearray(colors);rect=(1,3,38,20)
   for row in range(3,23):
    at=row*40+1;matrix[at:at+38]=sm[at:at+38];colors[at:at+38]=sc[at:at+38]

  else:matrix,colors,rect=geos.grid.logical_ui(f,data)
  if mode==0:
   (want,attrs),_,_,_=geos.grid.expected(Bare(f),data)
   if kind in('view','settings'):
    want=bytearray(want);attrs=bytearray(attrs);x,y,w,h=rect
    for row in range(y,y+h):
     for col in range(x,x+w):at=row*40+col;want[at]=matrix[at];attrs[at]=colors[at]
   actual=f.read(0x4000,1000);aa=f.read(0xd800,1000)
  else:
   if mode==3 and f.get('se_r_presentation',1):
    model=render(data,f.read(f.s['se_editor_settings'],64),catalog=FontCatalog(native=fonts['native8.bin']),top=f.get('se_v_top'));want,attrs=model.bitmap,model.attrs
   elif mode==3:want,attrs,_,_=semantic.expected(Bare(f),data,fonts)
   else:(want,attrs),_,_,_=geos.grid.expected(Bare(f),data)
   want,attrs=geos.with_chrome(want,attrs,matrix,colors,fonts['native8.bin'],rect)
   actual=f.read(0x6000,8000);aa=f.read(0x4000,1000)
  assert actual==bytes(want),(tag,'independent pixels',next((i,a,b)for i,(a,b)in enumerate(zip(actual,want))if a!=b))
  assert aa==bytes(attrs),(tag,'independent attributes',next((i,a,b)for i,(a,b)in enumerate(zip(aa,attrs))if a!=b))
  frames.append(dict(tag=tag,mode=mode,kind=kind,bitmap_sha256=sha(actual),attrs_sha256=sha(aa),item=f.get('se_e_item',1)))
  (out/'progress.json').write_text(json.dumps(dict(frames=frames,checks=checks),indent=2)+'\n')
 def view():
  before=state();key(0x85);key('v');guard(before,'F1-View');assert (f.get('se_e_ui',1),f.get('se_e_menu',1),f.get('se_e_item',1))==(1,3,0)
 def choose(index):
  for _ in range(index):key(0x11)
  assert f.get('se_e_item',1)==index
  key(13,0x77 if index==7 and f.get('se_mode',1)!=3 else 0)
 try:
  f.source(DATA);f.command(99);f.render();f.command(96);f.render()
  # Genuine selection and private clipboard, not forged metadata.
  f.command(68)
  for _ in range(4):f.command(2)
  f.command(69);assert f.get('se_clip_length')==4 and f.get('se_sel_mark',1)==1
  canonical=f.canonical()
  for mode in range(4):
   f.command(96+mode);f.render();assert f.canonical()==canonical
   view();frame(f'm{mode}-view','view')
   before=state();key('s');guard(before,f'm{mode}-S');assert (f.get('se_e_ui',1),f.get('se_e_menu',1))==(1,8)
   frame(f'm{mode}-settings','settings')
   before=state();key('h');assert f.get('se_render_caps',1)==0;guard(before,f'm{mode}-H')
   key('r');assert f.get('se_render_caps',1)==3 and f.read(f.s['se_editor_settings'],64)==defaults;guard(before,f'm{mode}-reset')
   key(3);assert f.get('se_e_ui',1)==0;f.render()
   view();choose(8);assert f.get('se_e_menu',1)==8;frame(f'm{mode}-arrow-settings','settings');key(13);f.render()
   view();before=state();key('p',0 if mode==3 else 0x77);guard(before,f'm{mode}-P')
   if mode!=3:
    assert f.get('se_r_presentation',1)==0 and f.get('se_e_ui',1)==0
    f.command(96+mode);f.render();view();choose(7);assert f.get('se_r_presentation',1)==0;f.command(96+mode);f.render()
   else:
    assert f.get('se_e_ui',1)==4 and f.get('se_r_presentation',1)==1;frame('geos-preview','preview')
    view();choose(8);frame('preview-settings','settings');key(3);assert f.get('se_e_ui',1)==4
    view();before=state();choose(7);guard(before,'preview-arrow-source');assert f.get('se_e_ui',1)==0 and f.get('se_r_presentation',1)==0;f.render()
    view();choose(7);frame('geos-arrow-preview','preview');view();key('p');f.render();assert f.get('se_e_ui',1)==0
  assert f.canonical()==canonical and f.merged()==DATA
  # A genuinely pending edit also survives menu/settings and read-only preview.
  f.command(50);key('Q');at=f.get('se_hot_caret')-1;data=DATA[:at]+geos.native_text('Q')+DATA[at:];f.render();assert f.get('se_hot_pending',1)==1
  before=state();view();key('s');key(3);guard(before,'pending-settings-cancel');f.render();view();key('p');frame('pending-preview','preview');view();key('p');f.render();guard(before,'pending-preview-source');assert f.get('se_hot_pending',1)==1
 finally:f.m.close()
 result=dict(status='PASS',fixture=str(private),budget=budget,frames=frames,guard_intervals=len(checks),names=len(ident['names']),disk_sha256=ident['disk_sha256'],scope='Private exactcontrol C7/R22 +4/+50 only, real public F1 letters/arrows/Return/all4; independent pixels and whole16MiB UI readonly/precise preview spans. CPU ROM/font seams, no native/physical claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='frames'},indent=2),flush=True)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/view-menu-current'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture)
