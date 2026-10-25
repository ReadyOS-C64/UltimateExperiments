"""Final actual standalone gallery: four editable modes and cold save/reopen.

Own binary8100/text8200, immutable product/privateD81/PID, no shared build.
Real File/Open and IRQ-native events; no document/register/PC substitutions.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,subprocess,zipfile
import test_geos_fold_native as folds
import test_reu_capacity_vice as capacity
from test_fold_retention_vice import Captured,decoded_fold
from test_geos_navigation_vice import object_bytes
from d81_image import D81Image
from png_pixels import read_png
from overlay_catalog_policy import catalog_identity
import vice_plan
ROOT=folds.ROOT;live=folds.live
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T071324227584Z/fixture'
NAMES=(b'FINAL40',b'FINAL60',b'FINAL80',b'FINALGEOS')
OWNED_MONITOR_PORT=8100


class Plan(folds.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=OWNED_MONITOR_PORT
  p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p
 def switch(self,ident,mode):
  self.typed(ident,('mode 40','mode 60','mode 80','mode hires')[mode]);self.memory(ident+'_mode','se_mode',mode)
 def shot(self,ident,data,mode,*,ui=0,pending=0,caret=0,node=1,saved=1,current=b'DIVERSE',clip=None,mark=False,anchor=None,tree=(),kind='literal',group=None,journal=False):
  for name,value,width in [('se_hot_caret',caret,3),('se_hot_pending',pending,1),('se_h_current',node,4),('se_h_saved',saved,4),('se_h_dirty',int(node!=saved),1),('se_sel_mark',int(mark),1)]:self.memory(ident+'_'+name,name,value,width)
  if mark:self.memory(ident+'_anchor','se_sel_anchor',anchor,3)
  self.capture(ident,data,mode,ui,kind=kind,caret=caret,pending=pending,node=node,saved=saved,current=current.decode(),clipboard=clip.hex() if clip is not None else None,mark=mark,anchor=anchor,folds=[f.bytes().hex()for f in tree],group=group,journal=journal,settings=None,error=0)


def freeze(cpu):
 e=folds.freeze(cpu);target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-geos-fold-native','-standalone-native');target.parent.mkdir(exist_ok=True);shutil.move(e,target);return target


def scenario(e,phase):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),phase);data=live.grid.fixture();q=live.grid.native_text('Q');edited=q+data
 n.boot()
 if phase=='fold':
  current=NAMES[3];n.open('visible_fold_open',current);n.switch('visible_fold_geos',3);n.typed('visible_fold_top','top')
  n.shot('visible-fold-expanded',edited,3,current=current,group='visiblefold')
  tree=folds.folded.tree(edited);tree,caret=folds.action_model(tree,3,0,0,0,0)
  n.typed('visible_fold_all','fold all');n.shot('visible-fold-collapsed',edited,3,current=current,tree=tree,caret=caret,group='visiblefold');n.cases[-1]['require_summary']=True
  n.typed('visible_fold_preview','preview',ui=4);n.shot('visible-fold-preview',edited,3,ui=4,kind='preview',current=current,tree=tree,caret=caret,group='visiblefold');n.cases[-1]['require_summary']=True
  n.send('visible_fold_preview_exit',b'\r');n.typed('visible_unfold_all','unfold all');tree,caret=folds.action_model(tree,4,0,caret,0,caret)
  n.shot('visible-fold-restored',edited,3,current=current,tree=tree,caret=caret,group='visiblefold');return n
 if phase=='restart':
  for mode,name in enumerate(NAMES):
   n.open('restart_open_'+str(mode),name);n.switch('restart_mode_'+str(mode),mode)
   n.shot('restart-'+str(mode),edited,mode,current=name,group='restart'+str(mode))
  return n
 for mode,name in enumerate(NAMES):
  tag=str(mode);group='original'+tag
  n.open('open_'+tag,b'DIVERSE');n.switch('switch_'+tag,mode)
  n.shot('original-'+tag,data,mode,group=group)
  n.send('menu_'+tag,b'\x85F',ui=1);n.shot('file-menu-'+tag,data,mode,ui=1,group=group)
  n.send('menu_close_'+tag,b'\3');n.send('help_'+tag,b'\x8B',ui=1)
  n.shot('help-'+tag,data,mode,ui=1,group=group);n.send('help_close_'+tag,b'\x8B')
  if mode==3:
   n.typed('original_preview','preview',ui=4);n.shot('formatted-preview',data,3,ui=4,kind='preview',group=group)
   n.send('preview_readonly_probe',b'Q\x14',ui=4);n.memory('preview_unchanged_history','se_h_end',0,2)
   n.send('preview_exit',b'\r')
  n.send('type_Q_'+tag,q);n.shot('pending-Q-'+tag,edited,mode,pending=1,caret=1)
  n.send('undo_'+tag,b'\x1A');n.shot('undo-'+tag,data,mode,journal=True)
  n.send('redo_'+tag,b'\x19');n.shot('redo-'+tag,edited,mode,caret=1,node=2,journal=True)
  n.save_as('save_'+tag,name);n.shot('saved-'+tag,edited,mode,caret=1,node=2,saved=2,current=name,journal=True)
 # The finalGEOS document remains saved. Exercise canonical selection and
 # paste, then Undo back to those exact saved bytes before a read-only fold.
 name=NAMES[3];n.typed('clip_top','top');n.send('mark_three',b'\x89'+b'\x1D'*3)
 n.send('copy_native_0B',b'\x0B');clip=edited[:3]
 n.shot('geos-selected-copy',edited,3,caret=3,node=2,saved=2,current=name,clip=clip,mark=True,anchor=0)
 n.send('unmark',b'\3');n.typed('paste_bottom','bottom');n.send('paste_native_16',b'\x16')
 n.shot('geos-pasted',edited+clip,3,caret=len(edited)+3,node=3,saved=2,current=name,clip=clip)
 n.send('paste_undo',b'\x1A');n.shot('geos-paste-undone',edited,3,caret=len(edited),node=2,saved=2,current=name,clip=clip,group='finalGEOS')
 tree=folds.folded.tree(edited);tree,caret=folds.action_model(tree,3,0,len(edited),0,len(edited))
 n.typed('collapse_all','fold all');n.shot('geos-collapsed',edited,3,caret=caret,node=2,saved=2,current=name,clip=clip,tree=tree,group='finalGEOS')
 n.typed('folded_preview','preview',ui=4);n.shot('folded-formatted-preview',edited,3,ui=4,kind='preview',caret=caret,node=2,saved=2,current=name,clip=clip,tree=tree,group='finalGEOS')
 n.send('fold_preview_exit',b'\r');n.typed('expand_all','unfold all');tree,caret=folds.action_model(tree,4,0,caret,0,caret)
 n.shot('geos-expanded',edited,3,caret=caret,node=2,saved=2,current=name,clip=clip,tree=tree,group='finalGEOS')
 return n


def evaluate(e,phase):
 out=e/phase;s=json.loads((e/'editor-report.json').read_text())['symbols'];identity=json.loads((e/'freeze.json').read_text());cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run')
 fonts={n:(e/n).read_bytes()for n in live.geos.GEOS_FONTS+('native8.bin',)};catalog=folds.previous.pack_catalog((e/'font-pack.bin').read_bytes(),fonts['native8.bin'])
 palette={};groups={};states={};intervals=0;observed=[];actual_catalog=None;derived={}
 narrow_witness=False;preview_spans=[]
 with zipfile.ZipFile(e/'product-sources.zip')as z:
  if 'grid' in identity['catalog']:
   abi=z.read('src/render/grid/caret/api.inc')
   assert b'NC_REU=$1500' in abi and b'NC_SIZE=256' in abi
   narrow_witness=True
  if 'src/render/geos/preview-cache.inc' in z.namelist():
   abi=z.read('src/render/geos/preview-cache.inc')
   assert b'PPC_META_REU=$EA88' in abi and b'PPC_SIZE=225' in abi
   preview_spans.append((0xea88,0xeb69))
  if 'src/render/geos/preview-glyph-cache.inc' in z.namelist():
   abi=z.read('src/render/geos/preview-glyph-cache.inc')
   assert b'PGC_BASE=$EB69' in abi and b'PGC_END=$FBA9' in abi
   preview_spans.append((0xeb69,0xfba9))
 # Authenticate only provider-owned derived banks; retain source/history/
 # clipboard/object data and unallocated tails in every read-only comparison.
 for c in cases:
  ram=(out/'captures'/(c['id']+'-ram.bin')).read_bytes()
  if c['group']:
   for i in range(256):
    owner=ram[s['se_reu_physical_owner']+i]
    if owner in (0xfe,0x46):derived.setdefault(c['group'],{}).setdefault(owner,set()).add(i)
 for c in cases:
  ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert len(reu)==16*1024*1024 and f.get('se_reu_banks',2)==256
  assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'],(ident,'source/caret')
  assert f.get('se_hot_pending',1)==c['pending'] and f.get('se_mode',1)==c['mode'] and f.get('se_e_ui',1)==c['ui']
  assert f.get('se_h_current',4)==c['node'] and f.get('se_h_saved',4)==c['saved'] and f.get('se_h_dirty',1)==int(c['node']!=c['saved'])
  assert f.get('se_sel_mark',1)==c['mark']
  if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
  assert not any(f.get(k,1)for k in ('se_e_job','se_e_error','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks'))
  assert f.read(0xc600,1024)==bytes((i*73+29)&255 for i in range(1024))
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==c['current'].encode()
  assert f.read(0xcb80,64)==(e/'editor-defaults.bin').read_bytes()
  # Published managed slot bit7 records verification progress, not a change
  # of image identity. Validate its declared policy; preserve every other
  # catalog bit and the separate complete payload checks below.
  current=catalog_identity(f.read(s['se_overlay_ids'],6*64),s)
  if actual_catalog is None:actual_catalog=current
  assert current==actual_catalog,(ident,'catalog384B')
  pack=(e/'font-pack.bin').read_bytes()
  for i,handle in enumerate(f.read(0xcbc1,2)):
   bank=ram[s['se_reu_map']+handle];assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfd
   part=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(part)]==part
  for slot,name in enumerate(identity['catalog']):
   handle=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);bank=ram[s['se_reu_map']+handle]
   assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==2
   payload=(e/(name+'.seo')).read_bytes()[36:];at=bank*65536+(slot&15)*4096;assert reu[at:at+len(payload)]==payload
  if c['clipboard'] is not None:assert object_bytes(f,reu,f.read(s['se_clip_token'],5),f.get('se_clip_length'))==bytes.fromhex(c['clipboard'])
  if c['journal']:
   raw=object_bytes(f,reu,f.read(s['se_h_token'],5),f.get('se_h_end',2));assert len(raw)==75 and raw[:5]==b'SEH1\1'
   assert binascii.crc_hqx(raw[:58]+raw[60:64],0xffff)==int.from_bytes(raw[58:60],'little') and binascii.crc_hqx(raw[64:],0xffff)==int.from_bytes(raw[56:58],'little')
   assert [int.from_bytes(raw[a:a+3],'little')for a in (26,29,32,39,42)]==[0,0,1,0,1]
  if ident.startswith('restart-'):assert f.get('se_h_end',2)==0
  tree=[decoded_fold(bytes.fromhex(x))for x in c['folds']]
  if f.get('se_ef_valid',1):
   assert f.get('se_ef_count',2)==len(tree) and object_bytes(f,reu,f.read(s['se_ef_token'],5),len(tree)*32)==b''.join(v.bytes()for v in tree)
  else:assert not any(v.flags&1 for v in tree)
  if c['group']:
   state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],w)for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
   assert state==states.setdefault(c['group'],state),(ident,'readonly canonical/history')
   masked=bytearray(reu)
   for owner,banks in derived.get(c['group'],{}).items():
    for bank in banks:
     assert ram[s['se_reu_physical_owner']+bank] in (0,owner),(ident,'derivedbank replaced canonical data')
     if owner==0x46:masked[bank*65536:(bank+1)*65536]=bytes(65536)
     else:
      spans=[(0,22*240)] if c['mode'] in (1,2) else [(0,64),(0x200,0xb200),(0xb200,0xd528)]
      if narrow_witness and c['mode'] in (1,2):spans.append((0x1500,0x1600))
      if c['mode']==3:spans+=preview_spans
      for a,b in spans:masked[bank*65536+a:bank*65536+b]=bytes(b-a)
   digest=hashlib.sha256(masked).hexdigest()
   if c['group'] in groups:intervals+=1
   assert digest==groups.setdefault(c['group'],digest),(ident,'whole16MiB outside declared derived spans')
  bits,attrs=capacity.raster(e,c,f,fonts,catalog)
  summary_count=0
  if c.get('require_summary'):
   if c['kind']=='preview':
    rendered=folds.preview(data,f.read(0xcb80,64),tree,catalog=catalog,top=f.get('se_v_top'))
    summary_count=sum(any(v.flags&1 and r.end==v.hidden-1 and r.next>=v.end for v in tree)for r in rendered.rows)
   else:
    _,_,rows,_=folds.raster(data,fonts,tree,top=f.get('se_v_top'),caret=c['caret'],anchor=c['anchor']if c['mark']else None,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
    summary_count=sum(r.marker for r in rows)
   assert summary_count>=1,(ident,'required actualvisible summary')
  if c['mode']:
   assert ram[0x6000:0x7f40]==bits,(ident,'bitmap',next((i,a,b)for i,(a,b)in enumerate(zip(ram[0x6000:0x7f40],bits))if a!=b))
   assert ram[0x4000:0x43e8]==attrs,(ident,'attrs')
  w,h,pixels=read_png(out/('native-'+ident+'.png'));assert(w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    at=(y//8)*40+x//8;ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attrs[at]>>4 if ink else attrs[at]&15;pixel=pixels[(35+y)*w+32+x]
    assert pixel==palette.setdefault(color,pixel),(ident,'actualVIC',x,y,color)
  observed.append(dict(id=ident,mode=c['mode'],source_bytes=len(data),pending=c['pending'],current=c['current'],visible_summaries=summary_count,png_sha256=hashlib.sha256((out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
 assert len(set(palette.values()))==len(palette)
 baseline=D81Image((e/'initial-fixtures.d81').read_bytes());disk=D81Image((e/'working.d81').read_bytes());wanted=live.grid.native_text('Q')+live.grid.fixture()
 for name in NAMES:assert disk.read(name,kind=1).data==wanted
 for old in baseline.entries():
  a,b=baseline.read(old.name),disk.read(old.name);assert a.data==b.data and a.sectors==b.sectors
 assert {v.name for v in disk.entries()}=={v.name for v in baseline.entries()}|set(NAMES)
 if phase=='fold':assert (e/'working.d81').read_bytes()==(e/'fold-initial.d81').read_bytes(),'read-onlyfoldD81 changed'
 result=dict(status='passed',phase=phase,identity=identity,frames=observed,pixels=len(cases)*64000,attributes=len(cases)*1000,whole16MiB_readonly_intervals=intervals,saved_files={n.decode():len(wanted)for n in NAMES},scope={'editing':'ActualcoldD81/FileOpen/Q/Undo/Redo/SaveAs inall4editablemodes,pluspreview/menu/help/canonicalcopy/paste; EOFfoldcapturesdo notrequirevisiblemarkers.','restart':'Freshownedcoldboot/sameD81/actualFileOpen offoursaved423Bfiles inmatchingdisplaymodes; freshhistory.','fold':'Freshownedcoldboot/canonicalTOP/foldall/preview/unfold withrequiredvisibleliteral+formattedsummary andbyteexactread-onlyD81.'}[phase]+' IRQnativeevents, notphysicalchords; no timing/lifecycleclaim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e,phase):
 if phase=='fold':shutil.copyfile(e/'working.d81',e/'fold-initial.d81')
 n=scenario(e,phase);p=n.plan();(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
 assert len({v['id']for v in n.steps})==len(n.steps)
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
 with zipfile.ZipFile(e/(phase+'-verification-sources.zip'),'w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for x in sorted((ROOT/folder).glob('*.py')):z.write(x,x.relative_to(ROOT))
 print('NATIVE',e,phase,'steps',len(n.steps),'IRQ',n.keys,'frames',len(n.cases),flush=True);capacity.run_owned_plan(p,n.out);return evaluate(e,phase)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--cpu-fixture',type=Path,default=DEFAULT);p.add_argument('--fixture',type=Path);p.add_argument('--phase',choices=['editing','restart','fold','both'],default='both');p.add_argument('--verify',type=Path);p.add_argument('--monitor-port',type=int,default=8100);a=p.parse_args()
 OWNED_MONITOR_PORT=a.monitor_port;assert 1024<=OWNED_MONITOR_PORT<=65395
 if a.verify:
  for phase in (('editing','restart','fold')if a.phase=='both'else(a.phase,)):evaluate(a.verify,phase)
 elif a.run:
  e=a.fixture.resolve()if a.fixture else freeze(a.cpu_fixture.resolve())
  for phase in (('editing','restart','fold')if a.phase=='both'else(a.phase,)):execute(e,phase)
 else:print('Prepared finalactual39asset four-mode acceptance; --run freezes then owns8100/text8200.')
