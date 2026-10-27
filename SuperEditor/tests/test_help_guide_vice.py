"""Offline-first native supplement for the sealed private161 paged Help guide.

Default authenticates/freezes/packages/builds/compiles only, never launches VICE.
Future --run owns9700/text9800..9839, one PID/disk/unique runtime directory.
Real FileOpen/IRQ keys; no document/PC/font/settings/map seeds. No hardware.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ast,binascii,hashlib,json,os,re,shutil,signal,socket,subprocess,time,zipfile
import test_standalone_acceptance_vice as engine
import test_cache_rebase_standalone_acceptance as inputs
import test_help_guide as guide
import test_retention_grammar_vice as grammar
from test_fold_retention_vice import Captured
from test_geos_navigation_vice import object_bytes
from overlay_catalog_policy import catalog_identity
from png_pixels import read_png
from d81_image import D81Image
ROOT=engine.ROOT;live=engine.live
BASE=ROOT/'build/help-guide-probe/20261027T011411597788Z/link/fixture'
PARENT=ROOT/'build/warm-shift-committed/20261027T002602997186Z/fixture'
PORT=9700;PORTS=(PORT,*range(9800,9840));FRAMES=29
# Independent specification, not decoded from emitted labels or imported pages.
PAGES=[['SuperEditor keys 1/3','Type / Return / DEL / cursors','F1 menus; View P preview/source','View S settings; Settings H syntax','F4 wrap; F8/CTRL-F8 modes','F2 mark; CTRL-C/K copy','CTRL-X cut / CTRL-V paste','CTRL-Z undo / CTRL-Y redo','HOME/CTRL-E line; F7 commands','F7 find/goto; Help D diag','F3/F5 pages; F6/STOP close'],['SuperMark inline 2/3','# to ###### + space: headings','**bold**  *italic*  ***both***','@@code@@; no backticks','- item / * item: bullets','1. item preserves typed numbers','Pound escape: £* £# £@ ££','Escape only syntax; not in code','CR ends inline; unmatched literal','No underscore/backslash markup','F3/F5 pages; F6/STOP close'],['SuperMark blocks 3/3',':::basic / :::asm / :::text','Close with same colon count','3-15 colons; longer fence quotes','a shorter closing line literally',':::region title / :::end nest','Blocks start in column zero','Source keeps controls; View P','shows formatted GEOS preview','Other Markdown forms stay literal','F3/F5 pages; F6/STOP close']]
ROWS=(4,6,7,8,9,10,11,12,13,14,17)
LAZY_MODULES=('diagnostics_model',) # imported by raster only; included in source seal

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def free_ports(ports=PORTS):
 for port in ports:
  with socket.socket()as s:
   s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   try:s.bind(('127.0.0.1',port))
   except OSError as e:raise AssertionError(f'occupied port{port}; no process stopped')from e

def authenticate(base):
 d=json.load(open(base/'freeze.json'));parent=json.load(open(PARENT/'freeze.json'));report=json.load(open(base/'build/editor-report.json'))
 assert len(d['names'])==62 and d['names']==parent['names'] and d['source_parent_commit']==parent['git_commit']=='16125239094435223a0d6e355e8ee98204fbc330'
 assert d['git_commit']is None and d['private_changed_assets']==['menu40','popups']
 assert sha(base/'build/editor.prg')==d['prg_sha256']==parent['prg_sha256']==report['sha256']
 assert report['resident_binding']['digest']=='39cea9cc8e4af5b2970e1030d502d7a4'
 assert sha(base/'build/supereditor.d81')==d['disk_sha256'];disk=D81Image((base/'build/supereditor.d81').read_bytes());old=D81Image((PARENT/'build/supereditor.d81').read_bytes())
 assert disk.read(b'SUPEREDITOR',kind=2).data==(base/'build/editor.prg').read_bytes()
 changed=[];raw_pairs={}
 for name in d['names']:
  raw=(base/f'build/overlays/{name}.seo').read_bytes();assert sha(base/f'build/overlays/{name}.seo')==d['assets'][name]
  assert disk.read(name.upper().encode(),kind=1).data==raw
  assert raw[20:36]==raw[36:52]==bytes.fromhex(report['resident_binding']['digest']) and binascii.crc_hqx(raw[36:],65535)==int.from_bytes(raw[12:14],'little')
  assert int.from_bytes(raw[8:10],'little')==len(raw)-36<=4096
  assert (base/f'build/overlays/{name}.bin').read_bytes()==raw[36:]
  if raw!=(PARENT/f'build/overlays/{name}.seo').read_bytes():changed.append(name)
  for ext in ('bin','lbl','map'):assert(base/f'build/overlays/{name}.{ext}').exists()
  raw_pairs[name]={ext:sha(base/f'build/overlays/{name}.{ext}')for ext in('bin','lbl','map')}
 assert changed==['menu40','popups']
 for ent in old.entries():
  wanted=(base/f'build/overlays/{ent.name.decode().lower()}.seo').read_bytes()if ent.name in(b'MENU40',b'POPUPS')else old.read(ent.name).data
  assert disk.read(ent.name).data==wanted
 assert {e.name for e in disk.entries()}=={e.name for e in old.entries()}
 with zipfile.ZipFile(base/'product-sources.zip')as z,zipfile.ZipFile(PARENT/'product-sources.zip')as a:
  assert z.namelist()==a.namelist();changes=[n for n in z.namelist()if z.read(n)!=a.read(n)]
  assert set(changes)==set(guide.CHANGES)
  for n in changes:assert digest(z.read(n))==d['sources'][n]
 # Recompiled controls/candidate already have exact byte/map/label proof; pin
 # these pairs to that sealed component rather than consulting mutable build.
 seal=json.load(open(ROOT/'build/help-guide-probe/release/manifest.json'))
 assert seal['asset_sha256']=={n:d['assets'][n]for n in changed}
 assert seal['source_zip_sha256']==sha(base/'product-sources.zip')
 assert tuple(map(len,[disk.read(b'MENU40',kind=1).data,disk.read(b'POPUPS',kind=1).data]))==(4037,4122)
 return dict(fixture=str(base),PRG=d['prg_sha256'],binding=report['resident_binding']['digest'],D81=d['disk_sha256'],sources=sha(base/'product-sources.zip'),changed_assets=changed,changed_sources=changes,raw_label_map_sha256=raw_pairs,guide_seal_sha256=sha(ROOT/'build/help-guide-probe/release/manifest.json'))

class Plan(engine.Plan):
 def plan(self):
  p=super().plan();p['plan_id']='supereditor-guide-'+self.e.parent.name;p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1
  assert p['steps'][0]['params']['kill_stale']is False
  return p
 def shot(self,tag,data,mode,*,kind='help',page=None,ui=1,presentation=0,pending=0,caret=4,group=None):
  super().shot(tag,data,mode,ui=ui,pending=pending,caret=caret,clip=live.grid.fixture()[:4],kind=kind)
  self.cases[-1].update(presentation=presentation,page=page,readonly_group=group,caps=3)
  self.memory(tag+'_presentation','se_r_presentation',presentation)
  self.memory(tag+'_caps','se_render_caps',3)
  if page is not None:
   self.memory(tag+'_help_menu','se_e_menu',6);self.memory(tag+'_guidepage','se_e_text_length',page)
  elif kind=='settings':self.memory(tag+'_settings_menu','se_e_menu',8)
  elif kind=='diag':self.memory(tag+'_diagnostic_menu','se_e_menu',7)

def scenario(e):
 n=Plan(e,json.load(open(e/'editor-report.json')),'gallery');data=live.grid.fixture();n.boot();n.open('open_diverse',b'DIVERSE')
 n.send('genuine_mark4',b'\x89'+b'\x1d'*4);n.send('genuine_copy0B',b'\x0b');n.send('unmark',b'\3');n.memory('actual_clip4','se_clip_length',4,3)
 n.switch('prime_real_baseline',3)
 for mode in range(4):
  n.switch('mode'+str(mode),mode)
  if mode<3:n.memory('m'+str(mode)+'_styles_ready','se_st_valid',1);n.memory('m'+str(mode)+'_styles_done','se_st_request',0)
  n.send('help_open'+str(mode),b'\x8b',ui=1)
  for page in range(3):
   n.shot(f'm{mode}-guide{page}',data,mode,page=page,group='m'+str(mode))
   if page<2:n.send(f'm{mode}_next{page}',b'\x87',ui=1)
  if mode==0:
   n.send('wrap_forward',b'\x87',ui=1);n.memory('wrapped0','se_e_text_length',0);n.send('reverse_wrap',b'\x86',ui=1);n.shot('m0-reverse2',data,0,page=2,group='m0')
  n.send('help_close'+str(mode),b'\3'if mode==1 else b'\x8b')
  n.send('view_settings'+str(mode),b'\x85V',ui=1);n.memory('view_menu'+str(mode),'se_e_menu',3)
  n.send('choose_settings'+str(mode),b'S'if mode%2==0 else b'\x11'*8+b'\r',ui=1)
  n.shot('m'+str(mode)+'-settings',data,mode,kind='settings',group='m'+str(mode))
  n.send('settings_H'+str(mode),b'H',ui=1);n.memory('Plain_H'+str(mode),'se_render_caps',0)
  n.send('settings_R'+str(mode),b'R',ui=1);n.memory('Full_reset'+str(mode),'se_render_caps',3)
  n.memory('defaults_reset'+str(mode),'se_editor_settings',(e/'editor-defaults.bin').read_bytes())
  n.send('settings_close'+str(mode),b'\3')
 n.send('View_P_preview',b'\x85VP',ui=4);n.shot('preview-before',data,3,kind='preview',ui=4,presentation=1)
 n.send('preview_help',b'\x8b',ui=1)
 for page in range(3):
  n.shot('preview-guide'+str(page),data,3,page=page,presentation=1,group='preview-help')
  if page<2:n.send('preview_help_next'+str(page),b'\x87',ui=1)
 n.send('preview_help_back',b'\x86',ui=1);n.memory('preview_help_back1','se_e_text_length',1);n.send('preview_F6_close',b'\x8b',ui=4)
 n.shot('preview-returned',data,3,kind='preview',ui=4,presentation=1)
 n.send('preview_View_S',b'\x85VS',ui=1);n.shot('preview-settings-before',data,3,kind='settings',presentation=1)
 n.send('preview_H',b'H',ui=1);n.memory('preview_plain_H','se_render_caps',0);n.send('preview_R',b'R',ui=1);n.shot('preview-settings-reset',data,3,kind='settings',presentation=1)
 n.send('preview_settings_STOP',b'\3',ui=4);n.send('preview_help_STOP_open',b'\x8b',ui=1);n.send('preview_help_STOP_close',b'\3',ui=4)
 n.send('preview_View_source',b'\x85V',ui=1);n.send('preview_arrow_Return_source',b'\x11'*7+b'\r');n.shot('source-restored',data,3,kind='literal',ui=0)
 n.send('diag_help_open',b'\x8b',ui=1);n.send('Help_D',b'D',ui=1);n.shot('Help-D',data,3,kind='diag');n.send('diag_close',b'\3')
 n.send('diag_select_help',b'\x8b',ui=1);n.send('diag_selected_page',b'\x11\x87',ui=1);n.memory('D_selection_not_page','se_e_item',1);n.memory('D_page1','se_e_text_length',1);n.send('D_Return',b'\r',ui=1);n.shot('selected-Return-diag',data,3,kind='diag');n.send('diag2_close',b'\3')
 edited=data[:4]+live.grid.native_text('Q')+data[4:];n.send('pending_Q',live.grid.native_text('Q'));n.memory('pending_real','se_hot_pending',1)
 n.send('pending_help',b'\x8b\x87',ui=1);n.shot('pending-guide1',edited,3,page=1,pending=1,caret=5,group='pending-help');n.send('pending_STOP',b'\3');n.shot('pending-restored',edited,3,kind='literal',ui=0,pending=1,caret=5)
 assert len(n.cases)==FRAMES,len(n.cases)
 return n

def spans(e):
 with zipfile.ZipFile(e/'product-sources.zip')as z:
  require={'src/render/geos/editor.inc':[b'GP_CACHE_VERSION=3',b'GP_SLOT_BASE=$0200',b'GP_SLOT_SIZE=$0800',b'GPR_USED=842',b'GP_MAX_LINES=22'],
   'src/render/grid/cache.inc':[b'GRID_CACHE_ROWS=22',b'GRID_CACHE_PACKET=240'],
   'src/render/grid/caret/api.inc':[b'NC_REU=$1500',b'NC_SIZE=256'],
   'src/render/grid/long-prose-candidate/prose2.inc':[b'SC_REU=$1600',b'SC_SIZE=128'],
   'src/render/geos/edit-cache.inc':[b'GEX_OLD_HEADER=$D528',b'GEX_ROW_BACKUPS=0'],
   'src/render/geos/typing-font-cache.inc':[b'GTF_DATA=$E568',b'GTF_META=$EA68'],
   'src/render/geos/preview-cache.inc':[b'PPC_META_REU=$EA88',b'PPC_SIZE=225'],
   'src/render/geos/preview-glyph-cache.inc':[b'PGC_BASE=$EB69',b'PGC_END=$FBA9',b'PGC_BYTES=4160']}
  for name,terms in require.items():assert all(t in z.read(name)for t in terms),(name,'unknown span contract')
  assert b'lda #6\n sta GP_IO_OFFSET+1'in z.read('src/render/geos/checkpoint/publish.inc')
  assert b'adc #7\n sta GSC_WRITE_OFFSET+1'in z.read('src/render/geos/checkpoint/outgoing.s')
 return [(0,22*240),(0x1500,0x1600),(0x1600,0x1680),(0x600,0x680)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]+[(0xb200,0xd528),(0xd528,0xd568),(0xe568,0xea88),(0xea88,0xeb69),(0xeb69,0xfba9)]

def raster(e,c,f,fonts,catalog):
 data=bytes.fromhex(c['source']);bare=guide.Bare(f);mode=c['mode'];rect=None
 if mode==0:(bits,attrs),_,_,_=live.geos.grid.expected(bare,data)
 elif c['presentation']:
  model=engine.folds.preview(data,(e/'editor-defaults.bin').read_bytes(),[],catalog=catalog,top=f.get('se_v_top'));bits,attrs=model.bitmap,model.attrs
  assert f.get('se_v_bottom')==model.bottom
  assert f.read(f.s['se_v_rows'],len(model.anchors)*3)==b''.join(x.to_bytes(3,'little')for x in model.anchors)
 elif mode==3:bits,attrs,_,_=engine.folds.raster(data,fonts,[],top=f.get('se_v_top'),caret=c['caret'],nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
 else:(bits,attrs),_,_,_,_=engine.folds.grid_fold.expected(bare,data,[],f.get('se_v_top'))
 matrix,colors,_=live.geos.grid.logical_ui(bare,data)
 if c['kind']=='help':
  ui=live.grid.UI(live.grid.source40(data,f.get('se_v_top'),c['caret'],pending=bool(c['pending'])));ui.box(1,3,38,16)
  for row,text in zip(ROWS,PAGES[c['page']]):ui.put(row,3,text.replace('£','\\'))
  matrix,colors,rect=ui.matrix,ui.colors,(1,3,38,16)
 elif c['kind']=='settings':
  ui=engine.folds.previous.settings_ui(f,data,(e/'editor-defaults.bin').read_bytes(),0,True);ui.put(20,3,'H source mode:');ui.put(20,17,'Full');matrix,colors,rect=ui.matrix,ui.colors,(1,3,38,20)
 elif c['kind']=='diag':
  from diagnostics_model import diagnostic_popup
  d=f.read(0x8800,128);assert d[:8]==b'DGS1\1\x80\2\1'and int.from_bytes(d[8:11],'little')==len(data)and int.from_bytes(d[13:16],'little')==c['caret']and int.from_bytes(d[22:24],'little')==binascii.crc_hqx(data,65535)
  model=diagnostic_popup(live.grid.source40(data,f.get('se_v_top'),c['caret']),d);matrix,colors,rect=model.matrix,model.colors,(1,3,38,20)
 if mode==0:
  cells,ink=bytearray(bits),bytearray(attrs)
  if rect:
   x,y,w,h=rect
   for row in range(y,y+h):at=row*40+x;cells[at:at+w]=matrix[at:at+w];ink[at:at+w]=colors[at:at+w]
  assert f.read(0x4000,1000)==cells and bytes(v&15 for v in f.colors)==ink,(c['id'],'all1000 independent logical cells/colors')
  rom=(e/'chargen.bin').read_bytes()[2048:4096];assert f.read(0x4800,2048)==rom
  bits=bytearray(8000);attrs=bytearray(1000)
  for at,code in enumerate(cells):bits[(at//40)*320+(at%40)*8:(at//40)*320+(at%40)*8+8]=rom[code*8:code*8+8];attrs[at]=ink[at]*16+6
  return bytes(bits),bytes(attrs)
 return live.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],rect)

def help_close_redraw(e,mode,oldram,oldreu,ram,reu):
 # Help paging is read-only, but closing Help publishes the source before View S.
 # Reconstruct the ONLY documented writes across that actual input interval.
 s=json.load(open(e/'editor-report.json'))['symbols'];h=ram[s['se_gc_handle']];p=ram[s['se_reu_map']+h]
 assert oldram[s['se_gc_handle']]==h and oldram[s['se_reu_map']+h]==p
 seq=lambda r:int.from_bytes(r[s['se_e_draw_sequence']:s['se_e_draw_sequence']+2],'little')
 source_sequence=(seq(oldram)+1)&65535;expected=bytearray(oldreu);base=p*65536
 with zipfile.ZipFile(e/'product-sources.zip')as z:
  nc=z.read('src/render/grid/caret/api.inc');gcc=z.read('src/render/geos/caret-cache.inc');writer=z.read('src/render/geos/caret-cache.s');page=z.read('src/render/geos/page.s')
  assert all(x in nc for x in [b'NC_REU=$1500',b'NC_SIZE=256',b'N_SEQUENCE=202',b'N_CRC=254'])
  assert all(x in gcc for x in [b'GCC_BITMAP=$B200',b'GCC_ATTRIBUTES=GCC_BITMAP+8000',b'GCC_END=GCC_ATTRIBUTES+1000',b'GCC_SEQUENCE=GCC_STATE+1',b'GCC_STATE=$CF90'])
  assert b'lda #0\n jsr bitmap'in writer and b'lda #0\n jsr attributes'in writer and b'sta GCC_SEQUENCE'in writer
  assert b'finish_caret:'in page and b'lda #2\n    jsr caret_call'in page
 if mode in(1,2):
  at=base+0x1500;header=bytearray(oldreu[at:at+256]);assert int.from_bytes(header[254:],'little')==binascii.crc_hqx(header[:254],65535)
  header[202:204]=source_sequence.to_bytes(2,'little');header[254:]=binascii.crc_hqx(header[:254],65535).to_bytes(2,'little');expected[at:at+256]=header
 elif mode==3:
  assert int.from_bytes(ram[0xcf91:0xcf93],'little')==source_sequence
  # R27 stores all8000+1000 after the source paint, before C16 finalizes
  # chrome. This interval's body is identical: only captured chrome may differ.
  expected[base+0xd000:base+0xd140]=ram[0x7e00:0x7f40]
  expected[base+0xd140:base+0xd190]=ram[0x4000:0x4050]
  expected[base+0xd500:base+0xd528]=ram[0x43c0:0x43e8]
 else:assert mode==0
 assert bytes(expected)==reu,(mode,'close Help/source publication exact whole16MiB reconstruction')
 return dict(mode=mode,source_publication_sequence=source_sequence,changed_bytes=sum(a!=b for a,b in zip(oldreu,reu)),scope='exact NC sequence+CRC or GCC captured chrome; all other16MiB identical')

def evaluate(e):
 inputs.validate(e);out=e/'gallery';s=json.load(open(e/'editor-report.json'))['symbols'];d=json.load(open(e/'freeze.json'));cases=json.load(open(out/'cases.json'));assert len(cases)==FRAMES
 images=live.grid.reu_images(out/'run');fonts={n:(e/n).read_bytes()for n in live.geos.GEOS_FONTS+('native8.bin',)};pack=(e/'font-pack.bin').read_bytes();catalog=engine.folds.previous.pack_catalog(pack,fonts['native8.bin']);allowed=spans(e)
 palette={};catalog0=arena0=outside=FE=observer0=None;stable={};readonly={};observations=[];intervals=0;help_tail={};close_gaps=[]
 for c in cases:
  tag=c['id'];ram=(out/'captures'/(tag+'-ram.bin')).read_bytes();colors=(out/'captures'/(tag+'-colors.bin')).read_bytes();reu=images[tag];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert len(reu)==16777216 and f.get('se_reu_banks',2)==256
  assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret']and f.get('se_hot_pending',1)==c['pending']
  assert (f.get('se_mode',1),f.get('se_e_ui',1),f.get('se_r_presentation',1),f.get('se_render_caps',1))==(c['mode'],c['ui'],c['presentation'],3)
  assert (f.get('se_h_current',4),f.get('se_h_saved',4),f.get('se_h_dirty',1),f.get('se_h_end',2),f.get('se_h_cursor',2))==(1,1,0,0,0)
  assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_e_draw_busy','se_e_redraw','se_f_owner','se_doc_read_locks','se_sel_mark','se_clip_busy'))
  assert f.read(0xc600,1024)==bytes((i*73+29)&255 for i in range(1024))and f.read(s['se_editor_settings'],64)==(e/'editor-defaults.bin').read_bytes()
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'DIVERSE'and f.get('se_f_current_device',1)==8
  cc=catalog_identity(f.read(s['se_overlay_ids'],384),s);catalog0=cc if catalog0 is None else catalog0;assert cc==catalog0
  assert f.get('se_clip_length')==4 and object_bytes(f,reu,f.read(s['se_clip_token'],5),4)==live.grid.fixture()[:4]
  a=grammar.arena(f,reu);arena0=a if arena0 is None else arena0;assert a==arena0,(tag,'whole authenticated53 immutable, no53 mask')
  assert f.get('se_bc_flags',1)&1 and not f.get('se_bc_flags',1)&14
  observer=f.read(s['se_bc_arena'],17);ring=f.read(s['se_bc_ring'],96)
  if not c['pending']:
   assert observer[16]==0 and observer[14]==observer[15]
   if observer0 is None:observer0=observer
   assert observer[:13]+observer[14:]==observer0[:13]+observer0[14:],(tag,'observer authority/queue changed without edit')
  else:
   assert observer[:5]==observer0[:5]and observer[9:13]==observer0[9:13]
   assert int.from_bytes(observer[5:9],'little')==int.from_bytes(observer0[5:9],'little')+1
   assert (observer[14],observer[15],observer[16])==((observer0[14]+1)%3,observer0[15],1)
   ev=ring[observer[15]*32:observer[15]*32+32]
   assert ev[0]==0xa5 and ev[1]==1 and int.from_bytes(ev[29:31],'little')==binascii.crc_hqx(ev[1:29]+ev[31:],65535)
   assert int.from_bytes(ev[4:8],'little')==int.from_bytes(observer[5:9],'little')and[int.from_bytes(ev[a:a+3],'little')for a in(16,19,22)]==[4,0,1]
  assert f.read(0xcbc0,1)==b'\xa5'and f.read(0xcbc3,2)==f.read(s['se_reu_epoch'],2)and f.read(0xcbc6,1)==f.read(0xcbc8,1)==b'\0'
  for i,h in enumerate(f.read(0xcbc1,2)):
   p=ram[s['se_reu_map']+h];assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfd;part=pack[i*65536:(i+1)*65536];assert reu[p*65536:p*65536+len(part)]==part
  for slot,name in enumerate(d['catalog']):
   h=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);p=ram[s['se_reu_map']+h];assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==2;raw=(e/(name+'.seo')).read_bytes()[36:];at=p*65536+(slot&15)*4096;assert reu[at:at+len(raw)]==raw
  h=f.get('se_gc_handle',1);p=ram[s['se_reu_map']+h];assert h and p and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfe
  fe=(h,p);FE=fe if FE is None else FE;assert fe==FE
  masked=bytearray(reu)
  for lo,hi in allowed:masked[p*65536+lo:p*65536+hi]=bytes(hi-lo)
  v=digest(masked);outside=v if outside is None else outside;assert v==outside,(tag,'whole16MiB outside exact source-authenticated FE spans')
  group='pending'if c['pending']else'original';st=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],w)for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_bc_ticket',4),('se_bc_incarnation',4),('se_bc_ring',96)])
  assert stable.setdefault(group,st)==st,(tag,'source/history/observer17+ring96')
  if c['kind']=='settings'and not c['presentation']:
   oldram,oldreu=help_tail[c['mode']];close_gaps.append(help_close_redraw(e,c['mode'],oldram,oldreu,ram,reu))
  if c['readonly_group']and c['page']is not None:
   hv=digest(reu);g=c['readonly_group'];intervals+=int(g in readonly);assert readonly.setdefault(g,hv)==hv,(tag,'same-key UI whole16MiB readonly')
  if c['page']is not None and not c['presentation']:help_tail[c['mode']]=(ram,reu)
  if c['page']is not None:assert f.get('se_e_menu',1)==6 and f.get('se_e_text_length',1)==c['page']
  bits,attrs=raster(e,c,f,fonts,catalog)
  if c['mode']:assert ram[0x6000:0x7f40]==bits and ram[0x4000:0x43e8]==attrs,(tag,'allbitmap/attributes')
  w,hh,pixels=read_png(out/('native-'+tag+'.png'));assert(w,hh)==(384,272)
  for y in range(200):
   for x in range(320):
    at=(y//8)*40+x//8;bit=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attrs[at]>>4 if bit else attrs[at]&15;actual=pixels[(35+y)*w+32+x];assert actual==palette.setdefault(color,actual),(tag,'actual VIC pixel',x,y,color)
  observations.append(dict(id=tag,mode=c['mode'],kind=c['kind'],page=c['page'],pending=c['pending'],png_sha256=sha(out/('native-'+tag+'.png'))))
 assert len(set(palette.values()))==len(palette)
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-only rawD81 changed'
 assert len(close_gaps)==4 and intervals==11
 result=dict(status='PASS',scope=__doc__,close_help_source_redraw_reconstructions=close_gaps,frames=observations,native_pixels=64000*FRAMES,attributes=1000*FRAMES,same_key_whole16MiB_readonly_intervals=intervals,precise_FE_cross_capture_intervals=FRAMES-1,analysis53=arena0,no_53_allowance=True,visual_review='pending')
 dump(out/'result.json',result);return result

def validate_plan(n,p):
 assert len(n.cases)==FRAMES and len({c['id']for c in n.cases})==FRAMES
 assert len(p['steps'])==len({s['id']for s in p['steps']})
 assert p['run_mode']=='gui_vice'and p['global_defaults']['monitor_port_start']==9700 and p['global_defaults']['monitor_port_span']==1
 v=p['global_defaults']['vice'];assert v['disk8']==str(n.e/'working.d81')and v['drive8_type']==1581 and not v['autostart_enabled']and not v['true_drive']and v['close_vice']
 assert not p['steps'][0]['params']['kill_stale']
 for s in p['steps']:
  if s['type']=='memory.write':assert s['params']['start']==0xc600 and bytes.fromhex(s['params']['bytes_hex'])==n.canary,'only1024B reserve canary seed is permitted'
  if s['type']=='monitor.command':
   cmd=s['params']['command'];assert cmd.startswith('raw: playback ')
   path=Path(cmd.split('"')[1]);assert path.is_relative_to(n.out)
   for line in path.read_text().splitlines():
    assert re.match(r'^(delete$|break exec \$[0-9a-f]+ if |x$|step \$10000$|screenshot |bsave |resourceset |resourceget |warp$)',line),(s['id'],'unsupported raw command',line)
 for mode in range(4):assert {c['page']for c in n.cases if c['mode']==mode and c['kind']=='help'and not c['presentation']}=={0,1,2}
 assert {c['page']for c in n.cases if c['presentation']and c['kind']=='help'}=={0,1,2}
 return dict(frames=len(n.cases),steps=len(n.steps),IRQ_bytes=n.keys,binary=9700,text_block=[9800,9839],no_source_or_PC_seeds=True)

def private_project(n):
 project=live.grid.synchronous_project(n.out);p=project.parent/'Program.cs';text=p.read_text();old='Path.Combine("logs", "vice_auto_" + TimeEx.TsForPath() + "_" + Guid.NewGuid().ToString("N")[..12])'
 assert text.count(old)==1
 text=text.replace(old,'Path.Combine('+json.dumps(str(n.out/'runtime-logs'))+', "vice_auto_" + TimeEx.TsForPath() + "_" + Guid.NewGuid().ToString("N")[..12])')
 old='_viceProc = Process.Start(psi) ?? throw new AutomationException("E_VICE_START_FAILED", "failed to start VICE process");';assert text.count(old)==1
 extra='''
        var ownershipPath = Environment.GetEnvironmentVariable("SUPEREDITOR_HELP_OWNED");
        if (!string.IsNullOrWhiteSpace(ownershipPath))
        {
            try
            {
                File.WriteAllText(ownershipPath, JsonEx.Serialize(new {
                    pid = _viceProc.Id, startedUtc = _viceProc.StartTime.ToUniversalTime(),
                    executable = exe, args, binary = monitorPort, text = textMonitorPort,
                    disk = Path.GetFullPath(defaults.Vice.Disk8), reu = _reuImagePath
                }));
            }
            catch { _viceProc.Kill(entireProcessTree: true); throw; }
        }
'''
 text=text.replace(old,old+extra);p.write_text(text)
 dump(project.parent/'help-guide-host-adapter.json',dict(private_program_sha256=sha(p),changes=['native runtime logs beneath owned output with GUID','persist exact launchedPID/args/disk/ports/REU before monitor connect','new-process record-write failure closes only that process'],no_app_changes=True))
 return project

def source_snapshot(out,project):
 files=set();todo=[Path(__file__).resolve()]+[ROOT/'tools'/(n+'.py')for n in LAZY_MODULES]
 while todo:
  p=todo.pop()
  if p in files:continue
  files.add(p)
  for n in ast.walk(ast.parse(p.read_text())):
   names=[x.name for x in n.names]if isinstance(n,ast.Import)else[n.module]if isinstance(n,ast.ImportFrom)and n.module else[]
   for name in names:
    for root in(ROOT/'tests',ROOT/'tools'):
     q=root/(name.split('.')[0]+'.py')
     if q.exists():todo.append(q.resolve())
 records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)for p in sorted(files)]
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for r in records:z.write(ROOT/r['path'],r['path'])
  for p in sorted(project.parent.glob('*')):
   if p.is_file()and p.suffix in('.cs','.csproj','.json'):z.write(p,'host/'+p.name)
 dump(out/'verification-sources.json',dict(local_python_imports=records,explicit_lazy_imports=list(LAZY_MODULES),zip_sha256=sha(out/'verification-sources.zip')))
 return records

def negative_controls(n,p):
 # No native ports are opened. Use one temporary ephemeral listener to prove
 # that the same occupancy guard refuses without stopping/touching its owner.
 with socket.socket()as s:
  s.bind(('127.0.0.1',0));s.listen();port=s.getsockname()[1]
  try:free_ports((port,))
  except AssertionError:occupied='refused; listener still owned/open'
  else:raise AssertionError('occupied port admitted')
  assert s.getsockname()[1]==port
 for label,mutate in [('wrong-binary',lambda q:q['global_defaults'].update(monitor_port_start=9701)),('source-write',lambda q:q['steps'].append(dict(id='invalid-source-seed',type='memory.write',params=dict(start=0x9200,bytes_hex='00'))))]:
  q=json.loads(json.dumps(p));mutate(q)
  try:validate_plan(n,q)
  except AssertionError:pass
  else:raise AssertionError((label,'invalid plan admitted'))
 assert PAGES==guide.PAGES and list(ROWS)==guide.ROWS,'independent text contract drift'
 return dict(occupied_port=occupied,wrong_binary_refused=True,source_write_refused=True,no_native_execution=True)

def prepare(base,out):
 out.mkdir(parents=True);auth=authenticate(base);e=inputs.freeze(base,out/'native');inputs.validate(e);assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
 # Preserve the inherited161 packager receipt as ancestry, not current truth.
 inherited=e/'disk-manifest.json';os.link(inherited,e/'input-161-disk-manifest.json');inherited.unlink();disk=D81Image((e/'supereditor.d81').read_bytes())
 dump(inherited,dict(schema='private-guide-package1',disk=str(e/'supereditor.d81'),sha256=sha(e/'supereditor.d81'),source_parent='16125239094435223a0d6e355e8ee98204fbc330',declared_asset_changes=['menu40','popups'],input_packager_manifest=sha(e/'input-161-disk-manifest.json'),members=[dict(name=v.name.decode(),sha256=digest(disk.read(v.name).data),bytes=len(disk.read(v.name).data),sectors=[dict(track=t,sector=q,sha256=digest(raw))for t,q,raw in disk.read(v.name).sectors])for v in disk.entries()]))
 # The frozen CPU disk has no divergent DIVERSE; freeze always starts with
 # supereditor.d81 and packages exactly once, never reuses an old working disk.
 n=scenario(e);p=n.plan();record=validate_plan(n,p);dump(n.out/'plan.yaml',p);dump(n.out/'cases.json',n.cases);dump(out/'authentication.json',auth);dump(out/'negative-controls.json',negative_controls(n,p))
 allowed=spans(e);dump(out/'FE-spans.json',dict(spans=allowed,no_whole_bank_mask=True,protect_reserved_row_tails=True,unused_edit_row_backups_protected=True))
 project=private_project(n)
 b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 command=['dotnet','run','--no-build','--project',str(project),'--','compile-plan','--plan',str(n.out/'plan.yaml'),'--output-root',str(out/'compiled')]
 c=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120);(out/'compile-plan.stdout.txt').write_text(c.stdout);(out/'compile-plan.stderr.txt').write_text(c.stderr);assert c.returncode==0
 compiled=list((out/'compiled').rglob('compiled_plan.json'));assert len(compiled)==1
 deps=source_snapshot(out,project)
 cpu_review=ROOT/'build/help-guide-root-review/visual-review.json'
 host_files=[dict(path=str(p),sha256=sha(p))for p in sorted((project.parent/'bin/Debug/net8.0').iterdir())if p.is_file()]
 result=dict(host_files=host_files,CPU_review=dict(path=str(cpu_review),sha256=sha(cpu_review))if cpu_review.exists()else None,status='OFFLINE_PREPARED_COMPILED_NOT_NATIVE',adapter_sha256=sha(Path(__file__)),fixture=str(base),native=str(e),source_policy=json.load(open(e/'freeze.json'))['source_policy'],authentication=auth,plan=record,plan_sha256=sha(n.out/'plan.yaml'),cases_sha256=sha(n.out/'cases.json'),project=str(project),compiled_plan=str(compiled[0]),compiled_plan_sha256=sha(compiled[0]),private_program_sha256=sha(project.parent/'Program.cs'),dependencies=deps,ports=[9700,9800,9839],ownership_receipt=str(n.out/'owned-process.json'),storage=dict(planned_REU_dumps=FRAMES,raw_capture_bytes=FRAMES*16777216,live_REU_bytes=16777216,estimated_total_bounded_bytes=560*1024*1024,host_final_copy='hardlink only after successful closedrun; failed runtime files retained'),native_run=False,limits='Preparation/compile only. No emulator/native pixel/source/cleanup performance success claimed. Future --run requires parent storage/port release; no hardware.')
 dump(out/'prepare-result.json',result);return result

def close_owned(out,e):
 receipt=out/'owned-process.json';record=dict(receipt=str(receipt),actions=[])
 if not receipt.exists():record.update(status='no-record-no-process-targeted');dump(out/'closure.json',record);return
 r=json.load(open(receipt));assert r['binary']==9700 and 9800<=r['text']<=9839 and Path(r['disk']).resolve()==(e/'working.d81').resolve()
 reu=Path(r['reu']).resolve();assert reu.is_relative_to(out/'runtime-logs')
 pid=int(r['pid']);record.update(pid=pid,disk=r['disk'],REU=r['reu'],binary=r['binary'],text=r['text'])
 def command():return subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout.strip()
 def owned(cmd):return str(reu)in cmd and str(e/'working.d81')in cmd and '127.0.0.1:9700'in cmd and Path(r['executable']).name in cmd
 cmd=command()
 if cmd:
  assert owned(cmd),('PID identity changed; no process stopped',pid,cmd);record['command']=cmd;os.kill(pid,signal.SIGTERM);record['actions'].append('SIGTERM exact ownedPID')
  for _ in range(40):
   if not command():break
   time.sleep(.1)
  cmd=command()
  if cmd:
   assert owned(cmd);os.kill(pid,signal.SIGKILL);record['actions'].append('SIGKILL exact still-ownedPID')
   for _ in range(40):
    if not command():break
    time.sleep(.1)
 assert not command(),('owned process still present',pid)
 record['status']='ownedPID-command-absent';dump(out/'closure.json',record)

def execute(prepared):
 meta=json.load(open(prepared/'prepare-result.json'));assert meta['status']=='OFFLINE_PREPARED_COMPILED_NOT_NATIVE'and meta['adapter_sha256']==sha(Path(__file__))
 for row in meta['dependencies']:assert sha(ROOT/row['path'])==row['sha256'],('verifier changed since preparation',row['path'])
 for row in meta['host_files']:assert sha(row['path'])==row['sha256'],('host binary changed',row['path'])
 assert sha(Path(meta['project']).parent/'Program.cs')==meta['private_program_sha256']
 e=Path(meta['native']);out=e/'gallery';inputs.validate(e);assert sha(out/'plan.yaml')==meta['plan_sha256']and sha(Path(meta['compiled_plan']))==meta['compiled_plan_sha256']
 assert not(out/'owned-process.json').exists()and not(out/'run').exists(),'do not overwrite an earlier owned run; prepare fresh'
 free_ports();proc=None;env=dict(os.environ,SUPEREDITOR_HELP_OWNED=str(out/'owned-process.json'))
 cmd=['dotnet','run','--no-build','--project',meta['project'],'--','run-compiled','--compiled',meta['compiled_plan'],'--close-vice','--no-tui']
 dump(out/'launch-command.json',dict(command=cmd,ports=PORTS,disk=str(e/'working.d81'),working_directory=str(ROOT)))
 try:
  with(out/'run-plan.stdout.txt').open('w')as stdout,(out/'run-plan.stderr.txt').open('w')as stderr:
   proc=subprocess.Popen(cmd,cwd=ROOT,stdout=stdout,stderr=stderr,env=env,start_new_session=True);dump(out/'owned-cli.json',dict(pid=proc.pid,command=cmd));rc=proc.wait(timeout=1800)
  assert rc==0,('native runner failed; original runtime preserved',rc)
 finally:
  # The harness normally closes its process. This receipt-bound fallback also
  # runs for failed CLI/timeout; never signal a process selected by port alone.
  try:close_owned(out,e)
  finally:
   if proc is not None and proc.poll()is None:
    proc.terminate()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
  free_ports()
 outcome=json.loads((out/'run-plan.stdout.txt').read_text());assert outcome['Status']=='success'
 manifest=json.load(open(outcome['Manifest'],encoding='utf-8-sig'));assert manifest['status']=='success'
 runtime=Path(outcome['RunDir']).resolve();assert runtime.is_relative_to(out/'runtime-logs')
 # All aliases are created only after terminal success and exact owned closure.
 receipts=[]
 def link(a,b):
  a,b=Path(a),Path(b);h=sha(a);os.link(a,b);assert a.stat().st_ino==b.stat().st_ino and sha(b)==h;receipts.append(dict(source=str(a),target=str(b.relative_to(out)),bytes=a.stat().st_size,sha256=h));return str(b)
 shutil.copytree(runtime,out/'run',copy_function=link);dump(out/'closed-hardlinks.json',dict(files=receipts,terminal_closed_success=True));dump(out/'owned-manifest.json',manifest)
 return evaluate(e)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--output',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args();assert not(a.run and a.verify)
 if a.run:assert a.prepared;print(json.dumps(execute(a.prepared.resolve()),indent=2))
 elif a.verify:assert a.prepared;print(json.dumps(evaluate(a.prepared.resolve()/'native'),indent=2))
 else:
  out=a.output or ROOT/'build/help-guide-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('PREPARE',out,flush=True);r=prepare(a.fixture.resolve(),out.resolve());print('OFFLINE_COMPILED',r['plan'],flush=True)
