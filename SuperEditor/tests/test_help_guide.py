"""Paged F6 keyboard/SuperMark help: exact-control C7/R22 qualification.

Only five copied C7/R22 sources change. Real public keys exercise all four
editable views and preview; independent text/bitmap/color oracles retain source,
history, selection, clipboard, observer, settings, shim and full16MiB guards.
Modeled ROM/font transport; no native/physical keyboard claim.
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
BASE=ROOT/'build/warm-shift-committed/20261027T002602997186Z/fixture'
DATA=geos.native_text('Menu text stays unchanged.\rAnother source line.\rTail.')
def sha(data):return hashlib.sha256(data).hexdigest()
def shell(*args,cwd=ROOT):subprocess.run([str(x)for x in args],cwd=cwd,check=True,stdout=subprocess.DEVNULL)
def labels(p):return {x[2].lstrip('.'):int(x[1],16)for l in p.read_text().splitlines()if len(x:=l.split())==3}
CHANGES=['src/overlays/editor-menu.s','src/overlays/editor-popups.s','src/overlays/editor-ui-draw.s','src/overlays/editor-settings-draw.s','src/diagnostics/ui.s']
def build(out,base):
 identity=json.loads((base/'freeze.json').read_text());assert identity['git_commit']=='16125239094435223a0d6e355e8ee98204fbc330'
 assert identity['prg_sha256']=='2924ddbc0379cdfdeba3b9d57c386d9bb0db0f764d6e174fdfc59e660021a686'
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
  if variant=='candidate':
   for n in CHANGES:shutil.copy2(ROOT/n,tree/n)
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
 identity=json.loads((private/'freeze.json').read_text());identity['private_help_guide_base']=str(base)
 identity['source_parent_commit']=identity.get('git_commit');identity['git_commit']=None
 identity['source_policy']='Private Help guide: exact committed parent archive except declared C7/R22 include sources; not an exact Git checkout.'
 identity['private_source_changes']=CHANGES
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
  for n in z.namelist():w.writestr(n,(ROOT/n).read_bytes()if n in CHANGES else z.read(n))
 identity['sources'].update({n:sha((ROOT/n).read_bytes())for n in CHANGES});identity['disk_sha256']=sha(disk.read_bytes());identity['private_changed_assets']=list(records)
 (private/'freeze.json').unlink()
 (private/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 return private,budgets

PAGES=[['SuperEditor keys 1/3', 'Type / Return / DEL / cursors', 'F1 menus; View P preview/source', 'View S settings; Settings H syntax', 'F4 wrap; F8/CTRL-F8 modes', 'F2 mark; CTRL-C/K copy', 'CTRL-X cut / CTRL-V paste', 'CTRL-Z undo / CTRL-Y redo', 'HOME/CTRL-E line; F7 commands', 'F7 find/goto; Help D diag', 'F3/F5 pages; F6/STOP close'], ['SuperMark inline 2/3', '# to ###### + space: headings', '**bold**  *italic*  ***both***', '@@code@@; no backticks', '- item / * item: bullets', '1. item preserves typed numbers', 'Pound escape: £* £# £@ ££', 'Escape only syntax; not in code', 'CR ends inline; unmatched literal', 'No underscore/backslash markup', 'F3/F5 pages; F6/STOP close'], ['SuperMark blocks 3/3', ':::basic / :::asm / :::text', 'Close with same colon count', '3-15 colons; longer fence quotes', 'a shorter closing line literally', ':::region title / :::end nest', 'Blocks start in column zero', 'Source keeps controls; View P', 'shows formatted GEOS preview', 'Other Markdown forms stay literal', 'F3/F5 pages; F6/STOP close']]
ROWS=[4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17]

class Bare:
 def __init__(self,f):self.f=f
 def get(self,n,w=3):return 0 if n in ('se_e_ui','se_e_menu')else self.f.get(n,w)
 def __getattr__(self,n):return getattr(self.f,n)

def logical_help(f,data,page):
 matrix,colors,_=geos.grid.logical_ui(Bare(f),data);matrix,colors=bytearray(matrix),bytearray(colors)
 for y in range(16):
  for x in range(38):
   at=(y+3)*40+x+1;border=x in(0,37)or y in(0,15);v=32
   if y==0:v=0x70 if x==0 else 0x6e if x==37 else 0x40
   elif y==15:v=0x6d if x==0 else 0x7d if x==37 else 0x40
   elif x in(0,37):v=0x5d
   matrix[at]=v;colors[at]=14 if border else 1
 for row,label in zip(ROWS,PAGES[page]):
  raw=bytes(geos.grid.screen_code(v)for v in geos.native_text(label.replace(chr(0xa3),chr(0x5c))));at=row*40+3;matrix[at:at+len(raw)]=raw
 return bytes(matrix),bytes(colors),(1,3,38,16)

def run(out,base,reuse=None):
 out.mkdir(parents=True,exist_ok=True)
 private,budget=build(out/'link',base)if not reuse else reuse
 ident=json.loads((private/'freeze.json').read_text());assert len(ident['names'])in(62,63)
 assert ident['names']==json.loads((base/'freeze.json').read_text())['names']
 if len(ident['names'])==63:assert ident['names'][-1]=='paint'
 assert ident['prg_sha256']==sha((base/'build/editor.prg').read_bytes())
 for n in ident['names']:
  if n not in ('menu40','popups'):assert (private/f'build/overlays/{n}.seo').read_bytes()==(base/f'build/overlays/{n}.seo').read_bytes()
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=font_fixture.ROOT=private
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=ident['names']
 from d81_image import D81Image
 pack=private/'build/geos-font-catalog/font-pack.bin';expected=D81Image((private/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
 assert pack.exists()and pack.read_bytes()==expected
 dll=geos.grid.runner(out);f=preview.Fixture(out,private,dll,True);fonts={n:(private/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 frames=[];checks=[];data=DATA
 def state():
  return f.canonical(),f.catalog(),f.read(f.s['se_bc_ticket'],4)+f.read(f.s['se_bc_incarnation'],4)+f.read(f.s['se_bc_ring'],96),f.merged(),f.read(f.s['se_editor_settings'],64),f.get('se_render_caps',1)
 def guard(before,tag):
  assert state()==before,(tag,'source/history/selection/clipboard/catalog/settings/cache observer')
  assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in('se_e_job','se_f_owner','se_doc_read_locks')),(tag,'owner/lease/shim')
  checks.append(tag)
 def key(v):f.key(geos.native_text(v)[0]if isinstance(v,str)else v)
 def diag_parity(tag):
  # Separate leaf differential: actual public Help-D has produced the checked
  # diagnostic snapshot. Reassemble-exact old/new R22 operation0 receive the
  # same RAM image; compare all1000 logical cells/colors before C16 conversion.
  # This is explicitly a component parity proof, not a second packaged route.
  saved=f.read(0,65536);r=f.reu();results=[]
  for variant in ('control','candidate'):
   f.m.load(0,saved);f.m.load(0xa000,(private.parent/variant/'popups.bin').read_bytes());f.m.write(f.s['se_overlay_frame'],0)
   regs,_=f.fast_call(0xa010);assert not regs.p&1
   results.append((f.read(0x4000,1000),f.read(0xd800,1000)))
   assert f.reu()==r and f.read(0xc600,1024)==f.shim,(tag,'R22 component REU/shim')
  f.m.load(0,saved);assert results[0]==results[1],(tag,'unchanged diagnostic cells/colors')
  checks.append(tag+'-R22-original/candidate-all1000-diagnostic-cells/colors')
 def frame(tag,kind='help'):
  before=state();r=f.reu();assert len(r)==16777216;f.render();guard(before,tag);assert r==f.reu(),(tag,'UI-only full16MiB changed')
  if kind=='help':matrix,colors,rect=logical_help(f,data,f.get('se_e_text_length',1))
  elif kind=='settings':
   class Logical40(Bare):
    def get(self,n,w=3):return 0 if n=='se_mode'else self.f.get(n,w)
   sm,sc=settings_ui.popup_model(Logical40(f),data,f.read(f.s['se_editor_settings'],64),None)
   matrix,colors,_=geos.grid.logical_ui(Bare(f),data);matrix,colors=bytearray(matrix),bytearray(colors);rect=(1,3,38,20)
   for row in range(3,23):
    at=row*40+1;matrix[at:at+38]=sm[at:at+38];colors[at:at+38]=sc[at:at+38]
  else:matrix,colors,rect=geos.grid.logical_ui(f,data)
  mode=f.get('se_mode',1)
  if mode==0:
   (want,attrs),_,_,_=geos.grid.expected(Bare(f),data);want,attrs=bytearray(want),bytearray(attrs)
   if rect:
    x,y,w,h=rect
    for row in range(y,y+h):
     at=row*40+x;want[at:at+w]=matrix[at:at+w];attrs[at:at+w]=colors[at:at+w]
   actual=f.read(0x4000,1000);aa=f.read(0xd800,1000)
  else:
   if mode==3 and f.get('se_r_presentation',1):
    model=render(data,f.read(f.s['se_editor_settings'],64),catalog=FontCatalog(native=fonts['native8.bin']),top=f.get('se_v_top'));want,attrs=model.bitmap,model.attrs
   elif mode==3:want,attrs,_,_=semantic.expected(Bare(f),data,fonts)
   else:(want,attrs),_,_,_=geos.grid.expected(Bare(f),data)
   want,attrs=geos.with_chrome(want,attrs,matrix,colors,fonts['native8.bin'],rect);actual=f.read(0x6000,8000);aa=f.read(0x4000,1000)
  assert actual==bytes(want),(tag,'pixels',next((i,a,b)for i,(a,b)in enumerate(zip(actual,want))if a!=b))
  assert aa==bytes(attrs),(tag,'attrs',next((i,a,b)for i,(a,b)in enumerate(zip(aa,attrs))if a!=b))
  frames.append(dict(tag=tag,mode=mode,page=f.get('se_e_text_length',1),pixels=sha(actual),attrs=sha(aa)))
  if mode:geos.png(actual,aa,out/(tag+'.png'))
  else:
   # Native8 RAM-text visualization, not a native VIC capture.
   bitmap=bytearray(8000)
   for cell,v in enumerate(actual):
    code=v&127
    for gy in range(8):bitmap[(cell//40)*320+(cell%40)*8+gy]=fonts['native8.bin'][code*8+gy]^(255 if v&128 else 0)
   geos.png(bitmap,bytes(((a&15)<<4)|6 for a in aa),out/(tag+'.png'))
  (out/'progress.json').write_text(json.dumps(dict(frames=frames,checks=checks),indent=2)+'\n')
 try:
  f.source(data);f.command(68)
  for _ in range(4):f.command(2)
  f.command(69);assert f.get('se_clip_length')==4 and f.get('se_sel_mark',1)==1
  canonical=f.canonical()
  for mode in range(4):
   f.command(96+mode);f.render();before=state();key(0x8b);assert (f.get('se_e_ui',1),f.get('se_e_menu',1),f.get('se_e_item',1),f.get('se_e_text_length',1))==(1,6,0,0);guard(before,f'm{mode}-F6-open')
   for page in range(3):
    assert f.get('se_e_text_length',1)==page;frame(f'm{mode}-guide{page}');key(0x87)
   assert f.get('se_e_text_length',1)==0;key(0x86);assert f.get('se_e_text_length',1)==2;frame(f'm{mode}-reverse2');key(0x8b);assert f.get('se_e_ui',1)==0
   # Original Help selection semantics remain separate from page state.
   key(0x8b);key(0x11);assert f.get('se_e_item',1)==1;key(0x91);assert f.get('se_e_item',1)==0;key(13);assert (f.get('se_e_ui',1),f.get('se_e_menu',1),f.get('se_e_text_length',1))==(1,6,0);key(3) #existing selected H closes menu then reopens Help
   key(0x8b);key('d');assert f.get('se_e_menu',1)==7;f.render();guard(before,f'm{mode}-Help-D');diag_parity(f'm{mode}-Help-D');key(3)
   # F1 Help/H and Help/D by arrows/Return, including fresh page initialization.
   key(0x85);key('h');key('h');assert f.get('se_e_menu',1)==6 and f.get('se_e_text_length',1)==0;key(3)
   key(0x85);key('h');key(0x11);key(0x87);assert f.get('se_e_item',1)==1 and f.get('se_e_text_length',1)==1;key(13);assert f.get('se_e_menu',1)==7;f.render();guard(before,f'm{mode}-arrow-diag');key(3)
   # The shared table printer also preserves the full existing Settings dialog.
   f.command(103);frame(f'm{mode}-settings','settings');key('h');assert f.get('se_render_caps',1)==0;key('r');assert f.get('se_render_caps',1)==3;frame(f'm{mode}-settings-reset','settings');key(3)
   # Prompt reuses length only after explicitly resetting it, not as help page.
   key(0x8b);key(0x87);key(0x88);assert f.get('se_e_ui',1)==2 and f.get('se_e_text_length',1)==0;key(3)
   key(0x88);key('u');key('p');key(3);key(0x85);key('h');assert f.get('se_e_text_length',1)==0;key(3)
   assert f.canonical()==canonical
  f.command(99);f.render();f.command(102);f.render();assert f.get('se_e_ui',1)==4
  before=state();key(0x8b);frame('preview-guide0');key(0x87);frame('preview-guide1');key(0x87);frame('preview-guide2');key(0x8b);assert f.get('se_e_ui',1)==4;guard(before,'preview-F6-restores-ui4')
  key(0x8b);key(3);assert f.get('se_e_ui',1)==4;guard(before,'preview-STOP-restores-ui4');key(13);f.render();assert not f.get('se_r_presentation',1)
  # Pending source survives all pages and a genuine typed command after close.
  f.command(50);key('Q');at=f.get('se_hot_caret')-1;data=DATA[:at]+geos.native_text('Q')+DATA[at:];f.render();assert f.get('se_hot_pending',1)==1
  before=state();key(0x8b);key(0x87);frame('pending-guide1');key(3);guard(before,'pending-help');f.typed(geos.native_text('help'));assert f.get('se_e_menu',1)==6 and f.get('se_e_text_length',1)==0;frame('typed-help0');key(3)
  # Genuine File owner1/modal phase: F6 remains file help, never source guide.
  f.hold_file_transport=True;f.put('se_e_key',15,1);f.put('se_e_mods',4,1);f.call('se_editor_input')
  # Pending Q is legitimately flushed before File may claim owner1. Stop at
  # the real modal boundary, before servicing any queued directory transport.
  for _ in range(25000):
   if f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3:break
   assert f.get('se_e_job',1),('File modal did not start',f.debug());f.call('se_editor_service')
  assert f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3
  phase=f.read(0x8d00,1152);r=f.reu();canonical_file=f.canonical();request=f.get('se_f_request',1)
  f.put('se_e_key',0x8b,1);f.put('se_e_mods',0,1);f.call('se_editor_input')
  # The genuine directory request is deliberately outstanding in this no-DOS
  # lane. Original C12 reports BUSY91 before file-help input, preserving owner1.
  assert f.get('se_e_ui',1)==3 and f.get('se_f_owner',1)==1 and f.get('se_e_error',1)==0x91
  assert f.get('se_f_request',1)==request and f.read(0x8d00,1152)==phase and f.reu()==r and f.canonical()==canonical_file
  f.call('se_editor_render');assert f.read(0x8d00,1152)==phase and f.read(0xc600,1024)==f.shim
  checks.append('real-File-owner1-pending-F6-busy-preserves-modal-phase-not-source-guide')
 finally:f.close()
 result=dict(status='PASS',fixture=str(private),budget=budget,frames=frames,guard_intervals=len(checks),assets=len(ident['names']),pages=3,scope='Actual public CPU C7/R22 Help/Settings over4editable views+read-only preview; independent allpixels/colors, whole16MiB UI readonly, real source/selection/clipboard/history/observer/settings/shim guards. Modeled ROM/font transport; no native/physical key claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='frames'},indent=2),flush=True);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--reuse',type=Path);a=p.parse_args();out=ROOT/'build/help-guide-probe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True)
 reuse=None
 if a.reuse:reuse=(a.reuse/'fixture',{k:len((a.reuse/v/(n+'.bin')).read_bytes())for v in ('control','candidate')for n in('menu40','popups')for k in[v+'_'+n]})
 run(out,a.fixture,reuse)
