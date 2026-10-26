"""Private current3a+View entries; real IRQ/FileOpen, owned8100/text8200..8239.
No shared build, source/map/status injection, hardware or physical-chord claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,socket,subprocess,zipfile
import test_standalone_acceptance_vice as engine
import test_view_menu_current as cpu
import test_retention_grammar_vice as grammar
from test_fold_retention_vice import Captured
from png_pixels import read_png
from closed_runtime_copy import run_with_closed_links
import vice_plan
ROOT=engine.ROOT;live=engine.live
BASE=ROOT/'build/view-menu-current/20261026T210541922992Z/link/fixture'
def free():
 for port in (8100,*range(8200,8240)):
  with socket.socket()as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',port))
def freeze(base):
 e=engine.folds.freeze(base);target=ROOT/'agentsworking/evidence/M8'/e.name.replace('geos-fold-native','view-menu-native');shutil.move(e,target);return target
class Plan(engine.Plan):
 def shot(self,ident,data,mode,ui=0,kind='literal',presentation=0):
  super().shot(ident,data,mode,ui=ui,kind=kind,caret=4,clip=data[:4])
  self.cases[-1].update(presentation=presentation)
  self.memory(ident+'_presentation','se_r_presentation',presentation)
  if kind=='view':self.memory(ident+'_view_menu','se_e_menu',3);self.memory(ident+'_item','se_e_item',0)
  if kind=='settings':self.memory(ident+'_settings_menu','se_e_menu',8)
def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');data=live.grid.fixture()
 n.boot();n.open('open_diverse',b'DIVERSE')
 n.send('select_four',b'\x89'+b'\x1d'*4);n.send('copy_native0B',b'\x0b');n.send('unmark',b'\3');n.memory('genuine_clip4','se_clip_length',4,3)
 n.switch('establish_semantic',3);n.memory('actual_baseline','se_bc_flags',17)
 for mode in range(4):
  n.switch('source_mode'+str(mode),mode);n.send('view_'+str(mode),b'\x85V',ui=1);n.shot('view-'+str(mode),data,mode,1,'view')
  n.send('settings_'+str(mode),b'S'if mode%2==0 else b'\x11'*8+b'\r',ui=1);n.shot('settings-'+str(mode),data,mode,1,'settings')
  n.send('preset_plain_'+str(mode),b'H',ui=1);n.memory('actual_plain_'+str(mode),'se_render_caps',0)
  n.send('reset_'+str(mode),b'R',ui=1);n.memory('actual_reset_'+str(mode),'se_render_caps',3)
  n.send('settings_close_'+str(mode),b'\3')
 n.send('view_preview',b'\x85VP',ui=4);n.shot('preview',data,3,4,'preview',1)
 n.send('preview_settings',b'\x85VS',ui=1);n.shot('preview-settings',data,3,1,'settings',1)
 n.send('preview_settings_cancel',b'\3',ui=4);n.shot('preview-restored',data,3,4,'preview',1)
 n.send('preview_view',b'\x85V',ui=1);n.send('arrow_return_source',b'\x11'*7+b'\r');n.shot('source-restored',data,3)
 return n

def raster(e,c,f,fonts,catalog):
 data=bytes.fromhex(c['source']);mode=c['mode'];bare=cpu.Bare(f)
 if mode==0:(matrix,colors),_,_,_=live.geos.grid.expected(bare,data);bits=attrs=None
 elif c['presentation']:
  result=engine.folds.preview(data,(e/'editor-defaults.bin').read_bytes(),[],catalog=catalog,top=f.get('se_v_top'));bits,attrs=result.bitmap,result.attrs
  assert f.get('se_v_bottom')==result.bottom
 elif mode==3:bits,attrs,_,_=engine.folds.raster(data,fonts,[],top=f.get('se_v_top'),caret=4,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
 else:(bits,attrs),_,_,_,_=engine.folds.grid_fold.expected(bare,data,[],f.get('se_v_top'))
 matrix,colors,_=live.geos.grid.logical_ui(bare,data)if mode else(matrix,colors,None)
 rect=None
 if c['kind']=='view':matrix,colors=cpu.popup(f,data);rect=(1,3,35,11)
 elif c['kind']=='settings':
  ui=engine.folds.previous.settings_ui(f,data,(e/'editor-defaults.bin').read_bytes(),0,True)
  ui.put(20,3,'H source mode:');ui.put(20,17,'Full');sm,sc=ui.matrix,ui.colors;matrix,colors=bytearray(matrix),bytearray(colors)
  rect=(1,3,38,20)
  for y in range(3,23):
   at=y*40+1;matrix[at:at+38]=sm[at:at+38];colors[at:at+38]=sc[at:at+38]
 if mode==0:
  # Build independent styled source40 first; logical chrome alone omits body.
  (want,ink),_,_,_=live.geos.grid.expected(bare,data);want,ink=bytearray(want),bytearray(ink)
  if rect:
   x,y,w,h=rect
   for row in range(y,y+h):
    for col in range(x,x+w):at=row*40+col;want[at]=matrix[at];ink[at]=colors[at]
  rom=(e/'chargen.bin').read_bytes()[2048:4096];assert f.read(0x4800,2048)==rom
  assert f.read(0x4000,1000)==want and bytes(v&15 for v in f.colors)==ink,(c['id'],'logical40 pixels/attrs')
  bits=bytearray(8000);attrs=bytearray(1000)
  for y in range(25):
   for x in range(40):
    at=y*40+x;bits[y*320+x*8:y*320+x*8+8]=rom[want[at]*8:want[at]*8+8];attrs[at]=ink[at]*16+6
  return bytes(bits),bytes(attrs)
 return live.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],rect)

def evaluate(e):
 original=engine.capacity.raster;names=engine.NAMES;engine.capacity.raster=raster;engine.NAMES=()
 # Released engine names its output editing and has no gallery scope label.
 # Alias only the host output path; all its source/pixel/disk assertions run.
 alias=e/'editing'
 if not alias.exists():alias.symlink_to('gallery',target_is_directory=True)
 assert alias.resolve()==(e/'gallery').resolve()
 try:result=engine.evaluate(e,'editing')
 finally:engine.capacity.raster=original;engine.NAMES=names
 out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');arena=None;states=None;outside=None;fe=None;mode_prior={};exact=0
 # Source-owned layouts authenticated from the exact frozen source contract.
 with zipfile.ZipFile(e/'product-sources.zip')as z:
  assert b'GRID_CACHE_ROWS=22'in z.read('src/render/grid/cache.inc') and b'GRID_CACHE_PACKET=240'in z.read('src/render/grid/cache.inc')
  for name,terms in [('src/render/geos/edit-cache.inc',[b'GEX_OLD_HEADER=$D528',b'GEX_TAIL_END=$E568']),('src/render/geos/typing-font-cache.inc',[b'GTF_DATA=$E568',b'GTF_META=$EA68']),('src/render/geos/preview-cache.inc',[b'PPC_META_REU=$EA88',b'PPC_SIZE=225']),('src/render/geos/preview-glyph-cache.inc',[b'PGC_BASE=$EB69',b'PGC_END=$FBA9'])]:
   body=z.read(name);assert all(term in body for term in terms)
 for c in cases:
  tag=c['id'];ram=(out/'captures'/(tag+'-ram.bin')).read_bytes();colors=(out/'captures'/(tag+'-colors.bin')).read_bytes();reu=images[tag];f=Captured(s,ram,colors,e)
  assert len(reu)==16777216 and f.get('se_render_caps',1)==3 and f.get('se_h_end',2)==f.get('se_h_cursor',2)==0
  assert f.get('se_r_presentation',1)==c['presentation']
  assert f.get('se_clip_busy',1)==0
  if c['mode']in(1,2):
   # 8EE8 is an inactive phase alias inside C33's proven512B CRC table.
   words=[binascii.crc_hqx(bytes((i,)),0)for i in range(256)]
   assert f.read(0x8d00,512)==bytes(v&255 for v in words)+bytes(v>>8 for v in words)
  else:assert f.get('se_fs_owned',1)==0
  assert f.get('se_bc_flags',1)&1 and not f.get('se_bc_flags',1)&14
  assert not any(f.get(n,1)for n in ('se_bc_head','se_bc_tail','se_bc_count'))
  state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],w)for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_counter',4),('se_bc_ticket',4),('se_bc_incarnation',4),('se_bc_ring',96)])
  if states is None:states=state
  assert states==state,(tag,'canonical/history/observer17/ring96')
  current=grammar.arena(f,reu)
  if arena is None:arena=current
  assert current==arena,(tag,'whole authenticated53 unchanged')
  h=f.get('se_gc_handle',1);p=ram[s['se_reu_map']+h];assert h and p and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfe
  if fe is None:fe=(h,p)
  assert fe==(h,p)
  masked=bytearray(reu)
  # Union of active grid packet/NC and GEOS source records/body/edit/font/preview
  # spans. Protect FBA9..FFFF, all other banks, every53/FD/code/source/clip byte.
  spans=[(0,64),(0x200,0xb200),(0,22*240),(0x1500,0x1600),(0xb200,0xd528),(0xd528,0xe568),(0xe568,0xea88),(0xea88,0xeb69),(0xeb69,0xfba9)]
  for lo,hi in spans:masked[p*65536+lo:p*65536+hi]=bytes(hi-lo)
  digest=hashlib.sha256(masked).hexdigest()
  if outside is None:outside=digest
  assert outside==digest,(tag,'whole16MiB outside exact authenticatedFEspans')
  if c['kind']in ('view','settings')and not c['presentation']:
   previous=mode_prior.setdefault(c['mode'],hashlib.sha256(reu).hexdigest())
   assert previous==hashlib.sha256(reu).hexdigest(),(tag,'UI same-mode whole16MiB readonly');exact+=int(c['kind']=='settings')
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
 result.update(status='PASS',phase='gallery',scope=__doc__,whole16MiB_precise_FE_intervals=len(cases)-1,same_mode_whole16MiB_UI_intervals=exact,analysis53_immutable=arena,visual_review='pending',no_file_writes=True)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def execute(e):
 n=scenario(e);plan=n.plan();(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for p in(ROOT/folder).glob('*.py'):z.write(p,p.relative_to(ROOT))
 print('NATIVE',e,'steps',len(n.steps),'IRQ',n.keys,'frames',len(n.cases),flush=True);free();manifest=run_with_closed_links(engine.capacity.run_owned_plan,plan,n.out,timeout=1200);free();(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');r=evaluate(e);print('VIEW_NATIVE_PASS',e,len(r['frames']),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--run',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(a.verify.resolve())
 elif a.run:free();execute(freeze(a.fixture.resolve()))
 else:print(__doc__)
