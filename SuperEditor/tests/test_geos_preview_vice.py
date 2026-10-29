"""Actual D81 cold-font import and read-only formatted GEOS preview.

Private binary7900/text8000, isolated disk/output/PID. No debugger document,
font, map, style, settings or PC replacement. Public IRQ bytes are not physical
keyboard-chord proof. Full raster oracle is supplied by geos_preview_model.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile,sys,binascii
import test_geos_semantic_io_vice as io
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan,cpu_editor
from bindings import verify as verify_binding
from cache_job_build import editor_pair_index
ROOT=io.ROOT;live=io.live

class Plan(io.Plan):
 def typed(self,ident,text,ui=0):self.send(ident,bytes([0x88])+live.grid.native_text(text)+b'\r',ui=ui)
 def capture(self,ident,data,mode=3,ui=0,kind='source',**extra):
  if mode<3 and ui==0:
   self.memory(ident+'_stylevalid','se_st_valid',1);self.memory(ident+'_styledone','se_st_request',0)
  self.snapshot(ident,data,mode,ui);self.cases[-1].update(kind=kind,**extra)


def freeze():
 e=ROOT/'agentsworking/evidence/M7'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-geos-preview-native');e.mkdir(parents=True)
 build=ROOT/'build';report=json.loads((build/'editor-report.json').read_text());seal=verify_binding(build/'editor.prg',build/'editor.lbl')
 assert report['sha256']==seal['resident_sha256'] and seal['digest']==report['resident_binding']['digest']
 names=list(cpu_editor.NAMES)
 for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81']:shutil.copy2(build/name,e/name)
 disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
 for name in names:
  image=(build/'overlays'/(name+'.seo')).read_bytes();assert image[20:36]==image[36:52]==bytes.fromhex(seal['digest'])
  assert disk.read(name.upper().encode(),kind=1).data==image; (e/(name+'.seo')).write_bytes(image)
 pack=(build/'geos-font-catalog/font-pack.bin').read_bytes();assert disk.read(b'GEOSFONTS',kind=1).data==pack
 (e/'font-pack.bin').write_bytes(pack)
 for name in live.geos.GEOS_FONTS+('native8.bin',):shutil.copy2(ROOT/'assets/fonts/generated'/name,e/name)
 # Read-only source40 oracle needs ROM uppercase/lowercase aliases too.
 manifest=json.loads((ROOT/'assets/fonts/generated/manifest.json').read_text())
 chargen=ROOT/'assets/fonts/generated/chargen.bin'
 if chargen.exists():shutil.copy2(chargen,e/'chargen.bin')
 else:
  rom=Path(manifest['native_source']);assert hashlib.sha256(rom.read_bytes()).hexdigest()==manifest['native_sha256']
  shutil.copy2(rom,e/'chargen.bin')
 for name in ['editor-defaults.bin','editor-font-catalog.bin']:shutil.copy2(build/'editor-settings'/name,e/name)
 files=[ROOT/'Makefile']+[p for folder in ('src','cfg','assets','tools') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix not in ('.pyc',)]
 with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in files:z.write(p,p.relative_to(ROOT))
 identity=dict(prg_sha256=report['sha256'],resident_binding=seal['digest'],disk_sha256=hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest(),catalog=names,asset_sha256={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in names},font_pack_sha256=hashlib.sha256(pack).hexdigest(),product_sources_sha256=hashlib.sha256((e/'product-sources.zip').read_bytes()).hexdigest(),wide_colors=True,row_cache=True,font_family_names=True)
 (e/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 shutil.copy2(e/'supereditor.d81',e/'working.d81');data=live.grid.fixture();(e/'diverse.bin').write_bytes(data)
 p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'diverse.bin'),'diverse,s'],capture_output=True,text=True);(e/'package.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 assert D81Image((e/'working.d81').read_bytes()).read(b'DIVERSE',kind=1).data==data
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');print('FROZEN '+str(e),flush=True);return e


def scenario(e,smoke=False):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');data=live.grid.fixture()
 settings=bytearray((e/'editor-defaults.bin').read_bytes());catalog=(e/'editor-font-catalog.bin').read_bytes();selected=0
 def capture(ident,mode=3,ui=0,kind='source',**extra):
  n.capture(ident,data,mode,ui,kind,settings=settings.hex(),selected=selected,**extra)
 def settings_keys(ident,keys):
  nonlocal selected
  for key in keys:
   if key in '12345678':selected=int(key)-1;continue
   offset=8+selected*7
   if key=='R':settings[:]=(e/'editor-defaults.bin').read_bytes();continue
   if key in 'FGSCBIU':
    if key in 'FS':
     current=bytes(settings[offset:offset+4]);rows=[catalog[i:i+5] for i in range(0,len(catalog),5)];index=next(i for i,v in enumerate(rows) if v[:4]==current)
     for step_ in range(1,len(rows)+1):
      nxt=rows[(index+step_)%len(rows)];same=nxt[:3]==current[:3]
      if ((key=='S' and same) or (key=='F' and not same)) and (selected!=7 or nxt[4]):settings[offset:offset+4]=nxt[:4];break
    elif key in 'CG':j=offset+(4 if key=='C' else 5);settings[j]=(settings[j]+1)&15
    else:settings[offset+6]^={'B':1,'I':2,'U':4}[key]
  n.send(ident,keys.encode(),ui=1)
 n.boot();n.memory('fontpack_ready',0xCBC0,0xA5);n.memory('fontchannel_closed',0xCBC8,0)
 n.open('open_diverse',b'DIVERSE');n.mode_to(2);capture('source80',2)
 n.typed('literal_geos','mode hires');capture('literal-geos')
 n.typed('formatted_preview','preview',ui=4);capture('preview-default',ui=4,kind='preview')
 if smoke:return n
 n.send('preview_readonly_keys',b'Q\x14\x1D',ui=4);capture('preview-readonly',ui=4,kind='preview')
 n.typed('open_settings','settings',ui=1);capture('settings-default',ui=1,kind='settings')
 # Profile1 body. Every mutation is a real Settings keystroke, not host bytes.
 for ident,key in [('family','FF'),('size','S'),('bold','B'),('italic','I'),('underline','U'),('foreground','C'),('background','G')]:
  settings_keys('settings_'+ident,key)
 capture('settings-custom',ui=1,kind='settings')
 n.send('settings_close',b'\r',ui=4);capture('preview-custom',ui=4,kind='preview')
 n.send('preview_next_page',b'\x87',ui=4);capture('preview-page2',ui=4,kind='preview',page='next')
 n.send('preview_previous_page',b'\x86',ui=4);capture('preview-page1',ui=4,kind='preview',page='previous')
 n.typed('headings_settings','settings',ui=1);settings_keys('heading1_profile','2FFSSSSSU');capture('settings-heading1',ui=1,kind='settings')
 n.send('headings_close',b'\r',ui=4);capture('preview-heading1',ui=4,kind='preview')
 n.send('preview_to_source',b'\r');capture('literal-restored')
 n.mode_to(2);capture('source80-restored',2)
 return n


def pack_catalog(pack,native):
 import geos_preview_model as model
 catalog=model.FontCatalog.__new__(model.FontCatalog);catalog.native=native;catalog.faces={(0,1,8):model.Face(native=native)}
 for i in range(pack[5]):
  e=pack[32+i*16:48+i*16];offset=int.from_bytes(e[8:11],'little');length=int.from_bytes(e[11:13],'little')
  key=(0,0,e[3]) if e[0]==2 else (1,int.from_bytes(e[1:3],'little'),e[3])
  assert key not in catalog.faces;catalog.faces[key]=model.Face(pack[offset:offset+length],native=native)
 return catalog


def settings_ui(f,data,settings,selected,named_fonts=False):
 # Independent fixed ReadyOS physical40-cell dialog specification.
 ui=live.grid.UI(live.grid.source40(data,f.get('se_v_top'),f.get('se_hot_caret')));ui.box(1,3,38,20)
 for row,col,text in [(4,3,'Session text settings'),(6,3,'1 Body'),(7,3,'2 H1'),(8,3,'3 H2'),(9,3,'4 H3'),(10,3,'5 H4'),(11,3,'6 H5'),(12,3,'7 H6'),(13,3,'8 Code'),(6,16,'Font'),(8,16,'Size $'),(9,16,'Ink  $'),(10,16,'Paper$'),(12,16,'B / I / U'),(15,3,'F font  S size  C ink  G paper'),(17,3,'B/I/U toggle; arrows/1-8 profile'),(19,3,'R reset defaults; Return closes'),(21,3,'Session only / no disk writes')]:ui.put(row,col,text)
 row=6+selected
 for col in range(3,11):ui.matrix[row*40+col]^=128;ui.colors[row*40+col]=3
 p=settings[8+selected*7:15+selected*7];family=int.from_bytes(p[1:3],'little')
 if p[0] and named_fonts:
  from test_geos_preview_settings import FAMILY_NAMES
  ui.put(7,16,FAMILY_NAMES[family])
 else:
  ui.put(7,16,'GEOS $' if p[0] else 'BSW / 9' if family==0 else 'Native / 8')
  if p[0]:ui.put(7,22,f'{family:04X}',7)
 for row,value in [(8,p[3]),(9,p[4]),(10,p[5])]:ui.put(row,22,f'{value:02X}',7)
 for col,letter,mask in [(16,'b',1),(20,'i',2),(24,'u',4)]:ui.put(13,col,letter,3 if p[6]&mask else 1,inverse=bool(p[6]&mask))
 return ui


def raster_check(e,c,f,data,reu,palette,catalog):
 import geos_preview_model as model
 native=(e/'native8.bin').read_bytes();fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS};fonts['native8.bin']=native
 if c['kind'] in ('preview','settings'):
  settings=bytes.fromhex(c['settings']);expected=model.render(data,settings,catalog=catalog,top=f.get('se_v_top'))
  assert f.get('se_v_bottom')==expected.bottom and int.from_bytes(f.read(0xCC07,3),'little')==expected.bottom,(c['id'],'preview canonical bottom',f.get('se_v_bottom'),expected.bottom)
  assert f.read(f.s['se_v_rows'],len(expected.anchors)*3)==b''.join(a.to_bytes(3,'little') for a in expected.anchors),(c['id'],'preview canonical anchors')
  matrix,colors,_=live.geos.grid.logical_ui(f,data)
  bits,attrs=model.with_chrome(expected.bitmap,expected.attrs,matrix,colors,native)
  if c['kind']=='settings':
   ui=settings_ui(f,data,settings,c['selected'],json.loads((e/'freeze.json').read_text()).get('font_family_names',False));bits=bytearray(bits);attrs=bytearray(attrs);live.grid.paint_native(bits,attrs,ui,native);bits,attrs=bytes(bits),bytes(attrs)
 elif c['mode']==3:bits,attrs,_,_=io.semantic.expected(f,data,fonts)
 else:(bits,attrs),_,_,_=live.geos.grid.expected(f,data)
 actual=f.read(0x6000,8000);attributes=f.read(0x4000,1000)
 for name,value in [('expected-bitmap',bits),('expected-attrs',attrs)]: (e/'gallery'/(c['id']+'-'+name+'.bin')).write_bytes(value)
 assert actual==bits,(c['id'],'independent bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(actual,bits)) if a!=b))
 assert attributes==attrs,(c['id'],'independent attributes',next((i,a,b) for i,(a,b) in enumerate(zip(attributes,attrs)) if a!=b))
 w,h,pixels=read_png(e/'gallery'/('native-'+c['id']+'.png'));assert(w,h)==(384,272)
 for y in range(200):
  for x in range(320):
   a=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=a>>4 if ink else a&15;pixel=pixels[(35+y)*w+32+x]
   assert pixel==palette.setdefault(color,pixel),(c['id'],'actual VIC pixel',x,y,color)
 return dict(bottom=expected.bottom,anchors=expected.anchors) if c['kind'] in ('preview','settings') else {}


def evaluate(e):
 # Full semantic and VIC oracle is filled once the frozen model is released.
 out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');pack=(e/'font-pack.bin').read_bytes()
 catalog=None;source_state=None;observed=[];palette={};fonts=pack_catalog(pack,(e/'native8.bin').read_bytes());outside_cache=None;intervals=0
 for c in cases:
  ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert live.merged(f,reu)==data,(ident,'canonical source')
  assert all(f.get(k,1)==0 for k in ('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_f_owner','se_e_error'))
  assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
  assert f.get('se_e_ui',1)==c['ui'] and f.get('se_mode',1)==c['mode']
  assert f.get('se_hot_caret')==0 and not f.get('se_sel_mark',1) and not f.get('se_hot_pending',1) and not f.get('se_h_dirty',1),(ident,'readonly caret/selection/pending/history')
  assert f.read(0xCBC6,1)==b'\0',(ident,'font provider error')
  assert f.read(0xCB80,64)==bytes.fromhex(c['settings']),(ident,'actual settings choices vs independent key model')
  assert f.read(0xCBC0,1)==b'\xA5' and f.read(0xCBC5,1)==b'\0' and f.read(0xCBC8,1)==b'\0'
  assert f.read(0xCBC3,2)==f.read(s['se_reu_epoch'],2)
  for bank,h in enumerate(f.read(0xCBC1,2)):
   ph=ram[s['se_reu_map']+h];assert h and ph and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+ph]==0xFD
   part=pack[bank*65536:(bank+1)*65536];assert reu[ph*65536:ph*65536+len(part)]==part,(ident,'actual coldimported genuine fontpack')
  cat=f.read(s['se_overlay_ids'],384)
  if catalog is None:catalog=cat
  assert cat==catalog
  for order,name in enumerate(json.loads((e/'freeze.json').read_text())['catalog']):
   image=(e/(name+'.seo')).read_bytes();slot=editor_pair_index(image[5],image[6]) if 'catalog_index' in s else order
   h=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);ph=ram[s['se_reu_map']+h]
   assert h and ph and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+ph]==2
   payload=image[36:];a=ph*65536+(slot&15)*4096;assert reu[a:a+len(payload)]==payload
  state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w) for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
  if source_state is None:source_state=state
  assert state==source_state,(ident,'readonly source/history')
  cache=f.get('se_gc_handle',1);ph=ram[s['se_reu_map']+cache];assert cache and ph and ram[s['se_reu_logical_owner']+cache]==ram[s['se_reu_physical_owner']+ph]==0xFE
  masked=reu[:ph*65536]+bytes(65536)+reu[(ph+1)*65536:];digest=hashlib.sha256(masked).hexdigest()
  if outside_cache is None:outside_cache=digest
  else:intervals+=1
  assert outside_cache==digest,(ident,'whole16MiB outside authenticated disposable FE cache')
  raster=raster_check(e,c,f,data,reu,palette,fonts)
  observed.append(dict(id=ident,kind=c['kind'],mode=c['mode'],ui=c['ui'],source_bytes=len(data),raster=raster,native_image_sha256=hashlib.sha256((out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
 result=dict(status='passed',frames=observed,pixels=len(cases)*64000,attributes=len(cases)*1000,whole16MiB_readonly_intervals=intervals,scope='Actual native coldGFC1/IRQFileOpen/readonlypreview/settings/source roundtrip; independent rawfont-bit/canonical parser model and every native VIC pixel')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e,smoke=False):
 n=scenario(e,smoke);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for module in (__file__,io.__file__,io.native.__file__,live.__file__,live.grid.__file__,live.geos.__file__,ROOT/'tests/test_editor_file_vice.py',ROOT/'tests/test_fold_retention_vice.py',ROOT/'tools/vice_plan.py',ROOT/'tools/vice_config.py',ROOT/'tools/d81_image.py'):
   p=Path(module);z.write(p,p.relative_to(ROOT))
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 print('NATIVE '+str(e)+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' frames='+str(len(n.cases)),flush=True)
 vice_plan.run_plan(plan,n.out);return evaluate(e)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--freeze',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(a.verify.resolve())
 elif a.run:execute((a.fixture or freeze()).resolve(),a.smoke)
 elif a.freeze:freeze()
 else:print('Prepared only: private7900/text8000; requires explicit parent stable-product grant')
