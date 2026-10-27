"""Private48 actualIRQ C33 qualification; owned8300/text8400..8439 only.

No shared build, product mutation, PC/register/stack substitution or physical-key
claim. Literal48 D81/source/C14 span images must be explicitly sealed first.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,socket,subprocess,zipfile
import test_standalone_acceptance_vice as engine
from test_fold_retention_vice import Captured,decoded_fold
from test_geos_navigation_vice import object_bytes
from overlay_catalog_policy import catalog_identity
from d81_image import D81Image
from png_pixels import read_png
import vice_plan
from cache_job_build import editor_pair_index
ROOT=engine.ROOT;live=engine.live
DEFAULT=ROOT/'build/grid-caret-native-prepare/20261025T171500/fixture'

class Plan(engine.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False);return p

def ports_free():
 for port in [8300,*range(8400,8440)]:
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as ex:raise AssertionError(f'owned port {port} occupied')from ex

def freeze(base):
 e=engine.folds.freeze(base);target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-geos-fold-native','-grid-caret-native');shutil.move(e,target)
 identity=json.loads((target/'freeze.json').read_text());assert len(identity['catalog'])==48 and identity['catalog'][-1]=='grid'
 assert len((target/'grid.seo').read_bytes())-36==3914 and len((target/'styler.seo').read_bytes())-36==4047
 assert hashlib.sha256((target/'grid.seo').read_bytes()).hexdigest()=='e7704ed0de07b6123bf97487ea7269f907c3b2ee9146acc5d7214a4759e4b0e1'
 return target

def scenario(e,smoke=False):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'editing');data=live.grid.fixture();tree=[];caret=0;mark=False;anchor=None
 def shot(tag,mode,ui=0,fast=False,group=None):
  n.shot(tag,data,mode,ui=ui,caret=caret,mark=mark,anchor=anchor,tree=tree,group=group)
  n.cases[-1].update(fast=fast)
  if fast:n.memory(tag+'_actual_C33_TRY',0x89c0,1)
 def goto(tag,at):
  nonlocal caret
  line=data[:at].count(b'\r')+1;col=at-(data.rfind(b'\r',0,at)+1);n.typed(tag,f'goto {line}')
  if col:n.send(tag+'_col',b'\x1d'*col)
  caret=at
 n.boot();n.open('open_diverse',b'DIVERSE');goto('source40_at3',3);shot('40-base',0,group='40caret')
 n.send('source40_right',b'\x1d');caret+=1;shot('40-right',0,group='40caret')
 n.send('source40_left',b'\x9d');caret-=1;shot('40-left',0,group='40caret')
 for mode,width in [(1,60),(2,80)]:
  n.switch('switch'+str(width),mode);goto('start'+str(width),3);shot(str(width)+'-base',mode,group=str(width)+'caret')
  n.send('right'+str(width),b'\x1d');caret+=1;shot(str(width)+'-right',mode,fast=True,group=str(width)+'caret')
  n.send('left'+str(width),b'\x9d');caret-=1;shot(str(width)+'-left',mode,fast=True,group=str(width)+'caret')
  if smoke:continue
  # Real CR crossing changes two row packets; no debugger caret insertion.
  firstcr=data.index(13);goto('cross'+str(width),firstcr);shot(str(width)+'-cross-before',mode)
  n.send('cross_right'+str(width),b'\x1d');caret+=1;shot(str(width)+'-cross-after',mode,fast=True)
  goto('markstart'+str(width),3);mark=True;anchor=3;n.send('mark'+str(width),b'\x89')
  n.send('markright'+str(width),b'\x1d');caret+=1;shot(str(width)+'-selected',mode,fast=True)
  n.send('unmark'+str(width),b'\3');mark=False;anchor=None
  n.send('menu'+str(width),b'\x85F',ui=1);shot(str(width)+'-menu',mode,1)
  n.send('menustop'+str(width),b'\3');n.send('help'+str(width),b'\x8b',ui=1);shot(str(width)+'-help',mode,1)
  n.send('helpclose'+str(width),b'\x8b');shot(str(width)+'-restored',mode)
  n.modal('filemodal'+str(width),'O');shot(str(width)+'-Fileowner1',mode,3)
  n.send('fileSTOP'+str(width),b'\3',owner=0);shot(str(width)+'-FileSTOP-restored',mode)
  # Folded pure planner C33op2 returns before resident C11/AUX admission.
  goto('foldtop'+str(width),0);n.typed('foldall'+str(width),'fold all');tree=engine.folds.folded.tree(data);tree,caret=engine.folds.action_model(tree,3,0,caret,0,caret);shot(str(width)+'-folded',mode)
  n.typed('unfoldall'+str(width),'unfold all');tree,caret=engine.folds.action_model(tree,4,0,caret,0,caret);shot(str(width)+'-expanded',mode)
 return n

def modal_oracle(e):
 # The old grid oracle covers only the pre-DOS empty listing. Extend only our
 # verifier with an independent actual-D81 list and the existing UI spec.
 import test_grid_modes as modes
 from types import SimpleNamespace
 original=modes.logical_ui
 entries=[x.name for x in D81Image((e/'initial-fixtures.d81').read_bytes()).entries()if x.kind==1][:8]
 def logical(f,data):
  if f.get('se_e_ui',1)!=3:return original(f,data)
  class Plain:
   s=f.s
   def get(self,n,w=3):return 0 if n=='se_e_ui' else f.get(n,w)
   def read(self,a,n):return f.read(a,n)
  matrix,colors,_=original(Plain(),data)
  assert f.get('se_fd_page',2)==0 and f.get('se_fd_list_count',1)==len(entries) and f.get('se_fd_list_index',1)==0 and not f.get('se_fd_confirm',1)
  for i,name in enumerate(entries):assert f.read(f.s['se_fd_list_lengths']+i,1)==bytes([len(name)])and f.read(f.s['se_fd_list_names']+16*i,len(name))==name,('actualROMlisting/rawD81',i,name)
  assert f.get('se_f_name_len',1)==7 and f.read(f.s['se_f_name'],7)==b'DIVERSE'
  ui=live.grid.UI(SimpleNamespace(matrix=matrix,colors=colors));ui.file_dialog(8,b'DIVERSE',entries,index=0)
  assert tuple(f.get(n,1)for n in ('tui_box_x','tui_box_y','tui_box_w','tui_box_h'))==(1,4,38,19)
  return ui.matrix,ui.colors,(1,4,38,19)
 modes.logical_ui=logical
 # Both fold/body and final chrome consumers use this same pure UI function.
 assert live.geos.grid is modes

def evaluate(e):
 modal_oracle(e)
 out=e/'editing';identity=json.loads((e/'freeze.json').read_text());s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');fonts={n:(e/n).read_bytes()for n in live.geos.GEOS_FONTS+('native8.bin',)};catalog=engine.folds.previous.pack_catalog((e/'font-pack.bin').read_bytes(),fonts['native8.bin']);palette={};groups={};states={};observed=[];old_catalog=None
 for c in cases:
  tag=c['id'];ram=(out/'captures'/(tag+'-ram.bin')).read_bytes();colors=(out/'captures'/(tag+'-colors.bin')).read_bytes();reu=images[tag];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source']);tree=[decoded_fold(bytes.fromhex(x))for x in c['folds']]
  assert len(reu)==16*1024*1024 and live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'],(tag,'canonical')
  assert (f.get('se_mode',1),f.get('se_e_ui',1),f.get('se_f_owner',1))==(c['mode'],c['ui'],int(c['ui']==3))
  assert not any(f.get(k,1)for k in ('se_e_job','se_e_error','se_e_redraw','se_e_draw_busy','se_doc_read_locks','se_hot_pending'))
  assert f.read(0xc600,1024)==bytes((i*73+29)&255 for i in range(1024))
  assert bool(f.get('se_sel_mark',1))==c['mark']
  if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
  assert f.get('se_h_current',4)==f.get('se_h_saved',4)==1 and f.get('se_h_end',2)==0 and f.get('se_h_dirty',1)==0
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'DIVERSE' and f.get('se_f_current_device',1)==8
  current=catalog_identity(f.read(s['se_overlay_ids'],384),s)
  if old_catalog is None:old_catalog=current
  assert current==old_catalog,(tag,'full64 catalog fields except published bit7 policy')
  for order,name in enumerate(identity['catalog']):
   image=(e/(name+'.seo')).read_bytes();index=editor_pair_index(image[5],image[6]) if 'catalog_index' in s else order
   h=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[index>>4],1);b=ram[s['se_reu_map']+h]
   assert h and b and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+b]==2
   blob=image[36:];at=b*65536+(index&15)*4096;assert reu[at:at+len(blob)]==blob,(tag,'whole48 assets',name)
  if f.get('se_ef_valid',1):
   assert f.get('se_ef_count',2)==len(tree) and object_bytes(f,reu,f.read(s['se_ef_token'],5),32*len(tree))==b''.join(t.bytes()for t in tree)
  if c.get('fast'):
   assert ram[0x89c0]==1,(tag,'actualTRY-not-CAPTUREfallback')
   h=f.get('se_gc_handle',1);b=ram[s['se_reu_map']+h];head=reu[b*65536+0x1500:b*65536+0x1600];assert head[:4]==b'NC\1\xa5' and binascii.crc_hqx(head[:254],65535)==int.from_bytes(head[254:],'little')
   assert int.from_bytes(head[202:204],'little')==f.get('se_e_draw_sequence',2)
  bits,attrs=engine.capacity.raster(e,c,f,fonts,catalog)
  if c['mode']:
   assert f.read(0x6000,8000)==bits,(tag,'independentbitmap',next((i,a,b)for i,(a,b)in enumerate(zip(f.read(0x6000,8000),bits))if a!=b))
   assert f.read(0x4000,1000)==attrs,(tag,'independentattrs')
  w,h,pixels=read_png(out/('native-'+tag+'.png'));assert(w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    at=(y//8)*40+x//8;ink=bits[(y//8)*320+x//8*8+y%8]&(128>>(x%8));role=attrs[at]>>4 if ink else attrs[at]&15;pixel=pixels[(35+y)*w+32+x];assert pixel==palette.setdefault(role,pixel),(tag,'actualVIC',x,y)
  if c['group']:
   group=c['group'];state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],w)for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
   assert state==states.setdefault(group,state),(tag,'wholecanonical/history')
   h=f.get('se_gc_handle',1);b=ram[s['se_reu_map']+h];masked=bytearray(reu)
   if h:
    assert b and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+b]==0xfe
    masked[b*65536:b*65536+0x1600]=bytes(0x1600)
   digest=hashlib.sha256(masked).hexdigest();assert digest==groups.setdefault(group,digest),(tag,'whole16MiB outside exactnarrowFE0..1600')
  observed.append(dict(id=tag,mode=c['mode'],fast=bool(c.get('fast')),caret=c['caret'],loads=f.get('se_overlay_loads',2),png_sha256=hashlib.sha256((out/('native-'+tag+'.png')).read_bytes()).hexdigest()));print('PASS',tag,flush=True)
 assert len(set(palette.values()))==len(palette)
 for a,b in [('40-base','40-right'),('40-right','40-left')]:
  x=next(x for x in observed if x['id']==a);y=next(x for x in observed if x['id']==b);assert x['loads']==y['loads'],('source40zeroloads',a,b)
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-only scenario changedactualmedia'
 result=dict(status='passed',identity=identity,frames=observed,pixels=64000*len(cases),attributes=1000*len(cases),actual_fast_frames=sum(x['fast']for x in observed),source40_caret_zero_loads=True,whole16MiB_exact_groups=list(groups),limits='RealIRQnative events and nativepixels; no physicalmatrix, timing or lifecycleclaim. FileSTOP is actual modalcancel; precise mid-C11STOP is separately CPUproved. No source edits in this readonly gallery.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def execute(e,smoke=False):
 ports_free();n=scenario(e,smoke);p=n.plan();assert len({x['id']for x in n.steps})==len(n.steps)
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
 with zipfile.ZipFile(e/'verifier-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for q in sorted((ROOT/folder).glob('*.py')):z.write(q,q.relative_to(ROOT))
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
 print('NATIVE',e,'8300/8400','steps',len(n.steps),'IRQbytes',n.keys,'frames',len(n.cases),flush=True)
 try:engine.capacity.run_owned_plan(p,n.out,timeout=1800)
 finally:ports_free()
 return evaluate(e)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--base',type=Path,default=DEFAULT);p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:print(evaluate(a.verify.resolve()))
 elif a.run:print(execute(a.fixture.resolve()if a.fixture else freeze(a.base.resolve()),a.smoke))
 else:print('Prepared private48/currentC14/C333914 actualIRQ/native32 on8300/8400; --run')
