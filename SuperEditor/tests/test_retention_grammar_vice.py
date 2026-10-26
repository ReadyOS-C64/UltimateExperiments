"""Native private C19 incomplete-region recovery; owned8100/text8200..8239.
Real D81 File/Open and IRQ bytes, no document/frame/PC/status substitutions.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,socket,subprocess,zipfile
import test_standalone_acceptance_vice as engine
import test_retention_grammar as grammar
from test_fold_retention_vice import Captured
from test_geos_navigation_vice import object_bytes
from overlay_catalog_policy import catalog_identity
from png_pixels import read_png
from d81_image import D81Image
from closed_runtime_copy import run_with_closed_links
import vice_plan
ROOT=engine.ROOT;live=engine.live
BASE=ROOT/'build/retention-grammar/20261026T200015684677Z/link/fixture'
SOURCE=grammar.SOURCE;NAME=b'REGION';C19='53884af91475602c11020180c519e10f36fc59df83d0489286f6c21fa92a318b'

class Plan(engine.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1;assert not p['global_defaults'].get('kill_stale',False);return p
 def shot(self,ident,data,mode,*,pending=0,caret=0,node=1,group=None,end=0,cursor=0,after_failure=False):
  super().shot(ident,data,mode,pending=pending,caret=caret,node=node,current=NAME,group=group)
  self.memory(ident+'_history_end','se_h_end',end,2);self.memory(ident+'_history_cursor','se_h_cursor',cursor,2)
  self.cases[-1].update(history_end=end,history_cursor=cursor,after_failure=after_failure)

def free_ports():
 for port in (8100,*range(8200,8240)):
  with socket.socket()as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',port))

def freeze(base):
 ident=json.loads((base/'freeze.json').read_text());original=json.loads((grammar.BASE/'freeze.json').read_text())
 assert len(ident['names'])==59 and ident['names']==original['names'] and ident['prg_sha256']==original['prg_sha256']
 assert {n for n in ident['assets']if ident['assets'][n]!=original['assets'][n]}=={'foldctl'} and ident['assets']['foldctl']==C19
 e=engine.folds.freeze(base,ident['prg_sha256'],ident['disk_sha256']);target=ROOT/'agentsworking/evidence/M8'/e.name.replace('geos-fold-native','retention-grammar-native');target.parent.mkdir(exist_ok=True);shutil.move(e,target);e=target
 # Original freeze packages DIVERSE; this owned run uses only its valid48B file.
 shutil.copy2(e/'supereditor.d81',e/'working.d81');(e/'region.bin').write_bytes(SOURCE)
 p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'region.bin'),'region,s'],capture_output=True,text=True);(e/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
 assert D81Image((e/'working.d81').read_bytes()).read(NAME,kind=1).data==SOURCE and len(SOURCE)==48
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');return e

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');q=live.grid.native_text('Q');z=live.grid.native_text('Z');at=SOURCE.index(b':::END')+2;data=SOURCE[:at]+q+SOURCE[at:];assert len(data)==49 and at==37
 n.boot();n.memory('cold_fontpack_ready',0xcbc0,0xa5);n.open('open_valid_region',NAME)
 # Real sourceGEOS publication establishes genuine optional semantic baseline
 # before editing. No analysis token/flag is fabricated by the verifier.
 n.switch('prime_geos',3);n.memory('actual_initial_baseline_armed','se_bc_flags',17)
 n.switch('initial40',0);n.shot('initial-valid40',SOURCE,0)
 n.typed('real_fold_all','fold all');n.typed('real_unfold_all','unfold all');n.memory('trusted_map_before_edit','se_ef_valid',1)
 n.typed('real_goto_closer','goto 3');n.send('real_right_twice',b'\x1d\x1d');n.memory('closer_interior37','se_hot_caret',at,3)
 n.send('break_closer_Q',q);n.shot('pending-broken40',data,0,pending=1,caret=at+1,after_failure=True)
 n.send('real_left',b'\x9d');n.send('real_undo',b'\x1a');n.memory('undo_restores48','se_doc_length',48,3)
 n.send('real_redo',b'\x19');n.shot('repaired40',data,0,caret=at+1,node=2,group='repaired49',end=75,cursor=75,after_failure=True)
 for mode in (1,2,3):
  n.switch('repair_mode'+str(mode),mode);n.shot('repaired'+('60','80','geos')[mode-1],data,mode,caret=at+1,node=2,group='repaired49',end=75,cursor=75,after_failure=True)
 n.send('continued_Z',z);n.send('continued_right',b'\x1d');nextdata=data[:at+1]+z+data[at+1:]
 n.send('continued_undo',b'\x1a');n.shot('continued-undo-geos',data,3,caret=at+1,node=2,end=150,cursor=75,after_failure=True)
 n.send('continued_redo',b'\x19');n.shot('continued-redo-geos',nextdata,3,caret=at+2,node=3,group='continued50',end=150,cursor=150,after_failure=True)
 n.switch('continued_mode40',0);n.shot('continued40',nextdata,0,caret=at+2,node=3,group='continued50',end=150,cursor=150,after_failure=True)
 return n

def exact_history(f,reu,end,cursor):
 assert f.get('se_h_end',2)==end and f.get('se_h_cursor',2)==cursor
 if not end:return
 raw=object_bytes(f,reu,f.read(f.s['se_h_token'],5),end);assert len(raw)==end
 for i in range(end//75):
  r=raw[i*75:(i+1)*75];assert r[:5]==b'SEH1\1' and int.from_bytes(r[6:8],'little')==75 and int.from_bytes(r[-2:],'little')==75
  assert binascii.crc_hqx(r[:58]+r[60:64],65535)==int.from_bytes(r[58:60],'little') and binascii.crc_hqx(r[64:],65535)==int.from_bytes(r[56:58],'little')
  assert [int.from_bytes(r[a:a+3],'little')for a in (26,29,32,39,42)]==[37+i,0,1,37+i,38+i]
  assert int.from_bytes(r[8:12],'little')==1+i and int.from_bytes(r[12:16],'little')==2+i
  ref=r[64:73];token=ref[:3]+f.read(f.s['se_object_epoch'],2);offset=int.from_bytes(ref[3:6],'little');count=int.from_bytes(ref[6:9],'little');assert count==1
  assert object_bytes(f,reu,token,offset+1)[offset:offset+1]==live.grid.native_text('Q'if i==0 else'Z')

def arena(f,reu):
 s=f.s;token=f.read(s['se_bc_arena'],5);oid=token[0];assert oid<8 and token!=bytes(5) and f.read(s['object_owner']+oid,1)==b'\x53'
 assert token[1:3]==f.read(s['object_gen_lo']+oid,1)+f.read(s['object_gen_hi']+oid,1) and token[3:]==f.read(s['se_object_epoch'],2)==f.read(s['se_reu_epoch'],2)
 count=f.read(s['object_banks']+oid,1)[0];assert 1<=count<=16;logical=list(f.read(s['object_extents']+oid*16,count));physical=[f.read(s['se_reu_map']+x,1)[0]for x in logical]
 assert all(logical)and len(set(logical))==len(set(physical))==count and all(physical)
 for l,p in zip(logical,physical):assert f.read(s['se_reu_logical_owner']+l,1)==f.read(s['se_reu_physical_owner']+p,1)==b'\x53'
 payload=b''.join(reu[p*65536:(p+1)*65536]for p in physical);return dict(token=token.hex(),logical=logical,physical=physical,sha256=hashlib.sha256(payload).hexdigest())

def evaluate(e):
 out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];ident=json.loads((e/'freeze.json').read_text());cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');fonts={n:(e/n).read_bytes()for n in live.geos.GEOS_FONTS+('native8.bin',)};pack=(e/'font-pack.bin').read_bytes();fontcatalog=engine.folds.previous.pack_catalog(pack,fonts['native8.bin'])
 palette={};catalog0=None;clip0=None;arena0=None;groups={};states={};frames=[];intervals=0
 # These exact contracts are explicit; no wholeFEbank exception is used.
 with zipfile.ZipFile(e/'product-sources.zip')as z:
  grid_contract=z.read('src/render/grid/cache.inc').decode();assert 'GRID_CACHE_ROWS=22'in grid_contract and 'GRID_CACHE_PACKET=240'in grid_contract
  for name,values in [('src/render/geos/edit-cache.inc',('GEX_OLD_HEADER=$D528','GEX_TAIL_END=$E568')),('src/render/geos/typing-font-cache.inc',('GTF_DATA=$E568','GTF_META=$EA68')),('src/render/geos/preview-cache.inc',('PPC_META_REU=$EA88','PPC_SIZE=225')),('src/render/geos/preview-glyph-cache.inc',('PGC_BASE=$EB69','PGC_END=$FBA9','PGC_BYTES=4160'))]:
   text=z.read(name).decode();assert all(v in text for v in values)
 for c in cases:
  tag=c['id'];ram=(out/'captures'/(tag+'-ram.bin')).read_bytes();colors=(out/'captures'/(tag+'-colors.bin')).read_bytes();reu=images[tag];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert len(ram)==0xd000 and len(reu)==16777216 and f.get('se_reu_banks',2)==256
  assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'] and f.get('se_mode',1)==c['mode']
  assert (f.get('se_h_current',4),f.get('se_h_saved',4),f.get('se_h_dirty',1),f.get('se_hot_pending',1))==(c['node'],1,int(c['node']!=1),c['pending'])
  assert not any(f.get(k,1)for k in ['se_e_error','se_e_job','se_e_draw_busy','se_e_redraw','se_f_owner','se_doc_read_locks','se_sel_mark','se_ef_active'])
  assert f.get('se_render_caps',1)==3 and f.get('se_e_ui',1)==0
  if c['after_failure']:assert f.get('se_ef_valid',1)==0 and f.get('se_ej_status',1)==128
  assert f.read(0xc600,1024)==bytes((i*73+29)&255 for i in range(1024)) and f.read(s['se_editor_settings'],64)==(e/'editor-defaults.bin').read_bytes()
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==NAME and f.get('se_f_current_device',1)==8
  current=catalog_identity(f.read(s['se_overlay_ids'],384),s);catalog0=current if catalog0 is None else catalog0;assert current==catalog0
  clip=f.read(s['se_clip_token'],5)+f.read(s['se_clip_length'],3);clip0=clip if clip0 is None else clip0;assert clip==clip0 and f.get('se_clip_length')==0
  exact_history(f,reu,c['history_end'],c['history_cursor'])
  a=arena(f,reu);arena0=a if arena0 is None else arena0;assert a==arena0,(tag,'whole authenticated53 arena immutable across edit and modes')
  assert f.read(0xcbc0,1)==b'\xa5' and f.read(0xcbc3,2)==f.read(s['se_reu_epoch'],2) and f.read(0xcbc6,1)==f.read(0xcbc8,1)==b'\0'
  for i,h in enumerate(f.read(0xcbc1,2)):
   p=ram[s['se_reu_map']+h];assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfd;part=pack[i*65536:(i+1)*65536];assert reu[p*65536:p*65536+len(part)]==part
  for slot,name in enumerate(ident['catalog']):
   h=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);p=ram[s['se_reu_map']+h];assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==2;payload=(e/(name+'.seo')).read_bytes()[36:];start=p*65536+(slot&15)*4096;assert reu[start:start+len(payload)]==payload
  if c['group']:
   state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],w)for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_counter',4),('se_h_end',2),('se_h_cursor',2)])
   assert state==states.setdefault(c['group'],state),(tag,'read-only canonical/history')
   h=f.get('se_gc_handle',1);p=ram[s['se_reu_map']+h];assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfe
   masked=bytearray(reu)
   # Cross-mode read-only groups must include both real packet layouts: grid
   #22 contiguous240-byte records and GEOS64Bheader+22x2048Brecord slots.
   for lo,hi in [(0,22*240),(0,64),(0x200,0xb200),(0xb200,0xd528),(0xd528,0xe568),(0xe568,0xea88),(0xea88,0xeb69),(0xeb69,0xfba9)]:masked[p*65536+lo:p*65536+hi]=bytes(hi-lo)
   digest=hashlib.sha256(masked).hexdigest();intervals+=int(c['group']in groups);assert digest==groups.setdefault(c['group'],digest),(tag,'whole16MiB outside exactFEspans; type53/46/source/history/foreign/unallocatedtails exact')
  bits,attrs=engine.capacity.raster(e,c,f,fonts,fontcatalog)
  if c['mode']:assert ram[0x6000:0x7f40]==bits and ram[0x4000:0x43e8]==attrs,(tag,'independent full bitmap/attrs')
  w,h,pixels=read_png(out/('native-'+tag+'.png'));assert(w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attr>>4 if ink else attr&15;pixel=pixels[(35+y)*w+32+x];assert pixel==palette.setdefault(color,pixel),(tag,'actualVICpixel',x,y,color)
  frames.append(dict(id=tag,mode=c['mode'],source_bytes=len(data),pending=c['pending'],node=c['node'],history_end=c['history_end'],sha256=hashlib.sha256((out/('native-'+tag+'.png')).read_bytes()).hexdigest()))
 assert len(set(palette.values()))==len(palette) and (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
 result=dict(status='PASS',identity=ident,frames=frames,pixels=len(cases)*64000,attributes=len(cases)*1000,whole16MiB_readonly_intervals=intervals,analysis53_immutable=arena0,scope=__doc__,visual_review='pending',negative_control='Explicit malformedFoldAll B5 and missingR14 are qualified in CPU regression, not injected in this native run.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('RETENTION_GRAMMAR_NATIVE_PASS',out,len(cases),'frames',flush=True);return result

def execute(e):
 n=scenario(e);plan=n.plan();assert len({x['id']for x in plan['steps']})==len(plan['steps']);(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for p in (ROOT/folder).glob('*.py'):z.write(p,p.relative_to(ROOT))
 print('NATIVE',e,'steps',len(n.steps),'IRQbytes',n.keys,'frames',len(n.cases),flush=True);free_ports();manifest=run_with_closed_links(engine.capacity.run_owned_plan,plan,n.out,timeout=1200);free_ports();(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return evaluate(e)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--run',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(a.verify.resolve())
 elif a.run:free_ports();execute(freeze(a.fixture.resolve()))
 else:print(__doc__)
