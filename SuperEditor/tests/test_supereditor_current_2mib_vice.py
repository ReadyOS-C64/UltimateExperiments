"""Offline-first frozen62/63 2MiB native smoke; no emulator in default preparation.

Real D81 coldboot/FileOpen/IRQ inputs; future10100/text10200..10239 exactPID.
Only a genuine2048KiB resource,32 reported banks and2,097,152-byte dumps qualify.
No reduced-capacity support claim until that future run and image review pass.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ast,binascii,hashlib,json,os,re,signal,socket,subprocess,time,zipfile,shutil
import test_help_guide_vice as guide
from test_fold_retention_vice import Captured
from test_geos_navigation_vice import object_bytes
from overlay_catalog_policy import catalog_identity
from png_pixels import read_png
from d81_image import D81Image
from cache_job_build import editor_pair_index
ROOT=guide.ROOT;live=guide.live;inputs=guide.inputs
BASE=ROOT/'build/help-guide-committed/20261027T020054896973Z/fixture'
COMMIT='12bde7a204d26dc8df1b65553d80fbe53594122a';PORT=10100;PORTS=(PORT,*range(10200,10240));SIZE=2*1024*1024;FRAMES=5
ENV='SUPEREDITOR_2MIB_OWNED'
sha=guide.sha;digest=guide.digest;dump=guide.dump

def free_ports(ports=PORTS):
 for port in ports:
  with socket.socket()as s:
   s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   try:s.bind(('127.0.0.1',port))
   except OSError as e:raise AssertionError(f'occupied port{port}; no process stopped')from e

def cold_catalog(prg,labelpath,names):
 labels={q[2].lstrip('.'):int(q[1],16)for line in labelpath.read_text().splitlines()if len(q:=line.split())==3}
 start,end=labels['file_catalog'],labels['file_catalog_end'];assert end-start==2*len(names) and len(names)in(62,63)
 load=int.from_bytes(prg[:2],'little')
 def read(at,count):assert load<=at<0x1000 and at+count<=0x1000;return prg[2+at-load:2+at-load+count]
 entries=[]
 for i,name in enumerate(names):
  lo,packed=read(start+2*i,2);length=packed&15;at=lo|((packed>>4)<<8);assert length and read(at,length)==name.upper().encode(),(i,name,'actualpackedcoldname')
  entries.append(dict(index=i,name=name,address=at,length=length))
 return dict(count=len(names),start=start,end=end,entries=entries,table_sha256=digest(read(start,end-start)))

def validate_native(e):
 d=json.load(open(e/'freeze.json'));r=json.load(open(e/'editor-report.json'));s=r['symbols'];names=d['catalog'];assert len(names)in(62,63) and len(names)==len(set(names))
 assert sha(e/'editor.prg')==d['prg_sha256']==r['sha256']and sha(e/'supereditor.d81')==d['disk_sha256']and r['resident_binding']['digest']==d['resident_binding']
 assert s['se_presentation_default']==3 and s['se_overlay_managed_verification']==1
 cold_catalog((e/'editor.prg').read_bytes(),e/'editor.lbl',names);disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes();slots=[]
 for n in names:
  raw=(e/(n+'.seo')).read_bytes();assert sha(e/(n+'.seo'))==d['asset_sha256'][n]and raw[20:36]==raw[36:52]==bytes.fromhex(d['resident_binding'])
  assert len(raw)-36==int.from_bytes(raw[8:10],'little')<=4096 and binascii.crc_hqx(raw[36:],65535)==int.from_bytes(raw[12:14],'little')and disk.read(n.upper().encode(),kind=1).data==raw
  assert raw[5]in(0,1)and raw[6]<64;slots.append(tuple(raw[5:7]))
 assert len(slots)==len(set(slots))and slots[:62][-2:]==[(1,41),(0,34)]
 assert sha(e/'font-pack.bin')==d['font_pack_sha256']and disk.read(b'GEOSFONTS',kind=1).data==(e/'font-pack.bin').read_bytes()
 assert(e/'editor-defaults.bin').read_bytes()[:8]==b'SEST\x01\x40\x08\x07'and sha(e/'product-sources.zip')==d['product_sources_sha256']
 inputs.contracts(e);return d

def freeze(base,out):
 out.mkdir(parents=True);d=json.load(open(base/'freeze.json'))
 for n in('editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81'):os.link(base/'build'/n,out/n)
 for n in d['names']:os.link(base/f'build/overlays/{n}.seo',out/(n+'.seo'))
 for n in live.geos.GEOS_FONTS+('native8.bin','chargen.bin'):os.link(base/'fonts'/n,out/n)
 os.link(base/'product-sources.zip',out/'product-sources.zip');disk=D81Image((out/'supereditor.d81').read_bytes());(out/'font-pack.bin').write_bytes(disk.read(b'GEOSFONTS',kind=1).data)
 r=json.load(open(out/'editor-report.json'));prg=(out/'editor.prg').read_bytes();at=2+r['symbols']['session_defaults']-int.from_bytes(prg[:2],'little');(out/'editor-defaults.bin').write_bytes(prg[at:at+64])
 meta=dict(prg_sha256=d['prg_sha256'],disk_sha256=d['disk_sha256'],resident_binding=r['resident_binding']['digest'],catalog=d['names'],asset_sha256=d['assets'],cpu_fixture=str(base.resolve()),font_pack_sha256=sha(out/'font-pack.bin'),product_sources_sha256=sha(out/'product-sources.zip'),source_parent_metadata=d.get('git_commit'),source_policy=d['source_policy'],input_freeze_sha256=sha(base/'freeze.json'))
 dump(out/'freeze.json',meta);os.link(base/'freeze.json',out/'input-cpu-freeze.json');validate_native(out)
 shutil.copy2(out/'supereditor.d81',out/'working.d81');data=live.grid.fixture();(out/'diverse.bin').write_bytes(data)
 if b'DIVERSE'not in{v.name for v in disk.entries()}:
  q=subprocess.run(['c1541','-attach',str(out/'working.d81'),'-write',str(out/'diverse.bin'),'diverse,s'],capture_output=True,text=True);(out/'package.log').write_text(q.stdout+q.stderr);assert q.returncode==0
 work=D81Image((out/'working.d81').read_bytes());assert work.read(b'DIVERSE',kind=1).data==data and{v.name for v in work.entries()}=={v.name for v in disk.entries()}|{b'DIVERSE'}
 for v in disk.entries():assert work.read(v.name).data==disk.read(v.name).data
 shutil.copy2(out/'working.d81',out/'initial-fixtures.d81');return out

def authenticate(base):
 d=json.load(open(base/'freeze.json'));r=json.load(open(base/'build/editor-report.json'));assert len(d['names'])in(62,63)
 if len(d['names'])==62:assert d['git_commit']==COMMIT and len(d['sources'])==1974
 else:assert d.get('git_commit')or d.get('source_parent_commit')or d.get('private_original_fixture'),'honest frozen source provenance required'
 assert len(d['names'])==len(set(d['names'])) and d['names'][:62][-2:]==['parse','xform']
 assert sha(base/'build/editor.prg')==d['prg_sha256']==r['sha256'];assert sha(base/'build/supereditor.d81')==d['disk_sha256']
 assert r['resident_binding']['digest']==d.get('resident_binding',r['resident_binding']['digest'])
 if len(d['names'])==62:assert r['resident_binding']['digest']=='39cea9cc8e4af5b2970e1030d502d7a4'
 cold=cold_catalog((base/'build/editor.prg').read_bytes(),base/'build/editor.lbl',d['names'])
 disk=D81Image((base/'build/supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(base/'build/editor.prg').read_bytes()
 pairs={}
 for name in d['names']:
  raw=(base/f'build/overlays/{name}.seo').read_bytes();assert sha(base/f'build/overlays/{name}.seo')==d['assets'][name]
  assert raw[20:36]==raw[36:52]==bytes.fromhex(r['resident_binding']['digest'])
  assert len(raw)-36==int.from_bytes(raw[8:10],'little')<=4096 and binascii.crc_hqx(raw[36:],65535)==int.from_bytes(raw[12:14],'little')
  assert raw[36:]==(base/f'build/overlays/{name}.bin').read_bytes() and disk.read(name.upper().encode(),kind=1).data==raw
  pairs[name]={x:sha(base/f'build/overlays/{name}.{x}')for x in('seo','bin','lbl','map')}
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  assert set(z.namelist())==set(d['sources'])
  for n in z.namelist():assert digest(z.read(n))==d['sources'][n],n
  assert b'SuperMark blocks 3/3'in z.read('src/overlays/editor-ui-draw.s')
 parentproof=None
 if len(d['names'])==63 and not d.get('git_commit'):
  parent=Path(d['private_original_fixture']);pd=json.load(open(parent/'freeze.json'));assert pd['names']==d['names']and pd['prg_sha256']==d['prg_sha256']and sha(parent/'build/editor.prg')==d['prg_sha256']
  changed=[n for n in d['names']if (base/f'build/overlays/{n}.seo').read_bytes()!=(parent/f'build/overlays/{n}.seo').read_bytes()];assert changed==['menu40','popups']
  with zipfile.ZipFile(base/'product-sources.zip')as z,zipfile.ZipFile(parent/'product-sources.zip')as a:
   assert set(z.namelist())==set(a.namelist());changes=[n for n in z.namelist()if z.read(n)!=a.read(n)];assert set(changes)==set(guide.guide.CHANGES)
  parentproof=dict(fixture=str(parent),freeze_sha256=sha(parent/'freeze.json'),PRG_sha256=sha(parent/'build/editor.prg'),D81_sha256=sha(parent/'build/supereditor.d81'),changed_assets=changed,changed_sources=changes)
 return dict(private_parent_comparison=parentproof,commit=d.get('git_commit'),source_parent=d.get('source_parent_commit'),cold_catalog=cold,fixture=str(base),PRG=d['prg_sha256'],binding=r['resident_binding']['digest'],D81=d['disk_sha256'],source_count=len(d['sources']),sources_sha256=sha(base/'product-sources.zip'),all_assets_raw_label_map=pairs)

class Plan(guide.Plan):
 def boot(self):
  super().boot();p=self.out/'resources.mon';text=p.read_text();assert text.count('"REUsize" "16384"')==1
  p.write_text(text.replace('"REUsize" "16384"','"REUsize" "2048"')+'resourceget "REUsize"\nresourceget "REU"\n')
  self.memory('actual_provider32','se_reu_banks',32,2)
 def plan(self):
  p=super().plan();p['plan_id']='supereditor-current2mib-'+self.e.parent.name;p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1;return p

def scenario(e):
 n=Plan(e,json.load(open(e/'editor-report.json')),'gallery');data=live.grid.fixture();n.boot();n.open('open_diverse',b'DIVERSE')
 n.send('mark4',b'\x89'+b'\x1d'*4);n.send('copy_native0B',b'\x0b');n.send('unmark',b'\3')
 n.switch('prime_actual_semantic_baseline',3)
 for mode in(0,2,3):
  n.switch('mode'+str(mode),mode)
  if mode<3:n.memory('style_ready'+str(mode),'se_st_valid',1);n.memory('style_idle'+str(mode),'se_st_request',0)
  n.shot('source'+str(mode),data,mode,kind='literal',ui=0)
 n.send('View_P_preview',b'\x85VP',ui=4);n.shot('preview',data,3,kind='preview',ui=4,presentation=1)
 n.send('F6_current_help',b'\x8b\x87\x87',ui=1);n.shot('preview-help2',data,3,page=2,presentation=1,group='preview-help')
 n.send('F6_return_preview',b'\x8b',ui=4);n.send('return_source',b'\r');n.memory('final_source_restored','se_r_presentation',0)
 assert len(n.cases)==FRAMES;return n

def validate_plan(n,p):
 assert len(n.cases)==FRAMES and [(c['mode'],c['presentation'],c['page'])for c in n.cases]==[(0,0,None),(2,0,None),(3,0,None),(3,1,None),(3,1,2)]
 assert len(p['steps'])==len({q['id']for q in p['steps']}) and p['run_mode']=='gui_vice'
 gd=p['global_defaults'];assert gd['monitor_port_start']==PORT and gd['monitor_port_span']==1
 v=gd['vice'];assert v['disk8']==str(n.e/'working.d81')and v['drive8_type']==1581 and not v['autostart_enabled']and not v['true_drive']and v['close_vice']
 assert not p['steps'][0]['params']['kill_stale'];resource=(n.out/'resources.mon').read_text();assert '"REUsize" "2048"'in resource and '16384'not in resource and 'resourceget "REUsize"'in resource
 for q in p['steps']:
  if q['type']=='memory.write':assert q['params']['start']==0xc600 and bytes.fromhex(q['params']['bytes_hex'])==n.canary
  if q['type']=='monitor.command':
   cmd=q['params']['command'];assert cmd.startswith('raw: playback ');path=Path(cmd.split('"')[1]);assert path.is_relative_to(n.out)
   for line in path.read_text().splitlines():assert re.match(r'^(delete$|break exec \$[0-9a-f]+ if |x$|step \$10000$|screenshot |bsave |resourceset |resourceget |warp$)',line),(q['id'],line)
 return dict(frames=FRAMES,steps=len(n.steps),IRQ_bytes=n.keys,resource_KiB=2048,provider_banks=32,dump_bytes=SIZE,binary=PORT,text_block=[10200,10239],warp=True,traps=True,no_source_or_PC_seeds=True)

def paint_scopes(e,f,reu,c):
 d=json.load(open(e/'freeze.json'))
 if 'paint'not in d['catalog']:return [],None
 with zipfile.ZipFile(e/'product-sources.zip')as z:
  api=z.read('src/render/geos/paint-convergence/api.inc');code=z.read('src/render/geos/paint-convergence/transaction.s');page=z.read('src/render/geos/page.s');fs=z.read('src/fold/source.inc').decode()
  assert all(v in api for v in[b'CV_CERT=$DD68',b'CV_NEXT=$DE68',b'CV_PACKET=$D568',b'CV_SIZE=240',b'CV_SOURCE=67',b'CV_CRCS=126',b'CV_HEADER=170',b'CV_CRC=238'])
  assert b'field_lo:.byte 0,32,<194,<356,<518'in code and b'field_hi:.byte 0,0,>194,>356,>518'in code
  assert b'lda GEC_VALID\n cmp #1\n jne miss'in code and b'convergence_snapshot:\n    lda FAST_PAINT\n    cmp #3\n    bne @done'in page
 assert f.read(0xcfe8,1)==b'\0','noeditprofile mustnot claimmutation certificate'
 h=f.get('se_gc_handle',1);p=f.ram[f.s['se_reu_map']+h];base=p*65536;cert=reu[base+0xdd68:base+0xdd68+240];nxt=reu[base+0xde68:base+0xde68+240]
 assert cert[:3]==b'\xa5\5\3'and 1<=cert[3]<=22
 assert cert[4:20]==bytes.fromhex(d['resident_binding'])and cert[59:61]==f.read(f.s['se_gc_epoch'],2)and cert[61:63]==bytes((h,p))
 assert int.from_bytes(cert[238:240],'little')==binascii.crc_hqx(cert[1:238],65535)
 assert int.from_bytes(cert[234:236],'little')==binascii.crc_hqx(cert[67:126],65535)and cert[236:238]==bytes(2)and cert[63]==0
 header=cert[170:234];assert header[0]==1 and header[1]==cert[3]and header[2:4]==b'G\3'
 assert cert[20:57]==header[4:41]and cert[64:67]==header[46:49]
 assert cert[57:59]==f.read(0xcf91,2),'actualR27 sequence witness'
 expected=bytearray(cert);expected[0]=0;expected[3:67]=bytes(64);expected[170:234]=bytes(64);expected[238:240]=bytes(2)
 assert bytes(expected)==nxt,'exact uncommitted nextrecord from verifiedcurrentcert, no broad allowance'
 if c['mode']==3:
  fields=re.findall(r'^    action (se_\w+),(\d+),(\d+)$',fs,re.M);assert len(fields)==23 and sum(int(n)for _,_,n in fields)==59
  actual=b''.join(f.read(f.s[name],int(n))for name,_,n in fields);assert actual==cert[67:126],'actualcurrentcompleteFS59, no relaxedsourcekey'
  assert reu[base:base+64]==header
  for i in range(cert[3]):
   at=base+0x200+i*0x800;packet=reu[at:at+842];count=int.from_bytes(packet[12:14],'little');assert count<=161
   live=packet[:32]+b''.join(packet[a:a+count]for a in(32,194,356))+packet[518:518+2*(count+1)]
   assert binascii.crc_hqx(live,65535)==int.from_bytes(cert[126+i*2:128+i*2],'little'),('actualcomputedpacketCRC',i)
 assert cert[126+2*cert[3]:170]==bytes(44-2*cert[3])
 return[(0xdd68,0xdd68+240),(0xde68,0xde68+240)],dict(validated_source_paint_records=2,bytes=480,packet_CRC_rows=cert[3]if c['mode']==3 else 0,shadow_and_staging_bytes_still_protected=True,records_sha256=digest(cert+nxt))

def evaluate(e):
 validate_native(e);out=e/'gallery';s=json.load(open(e/'editor-report.json'))['symbols'];d=json.load(open(e/'freeze.json'));cases=json.load(open(out/'cases.json'));assert len(cases)==FRAMES
 images=live.grid.reu_images(out/'run');fonts={n:(e/n).read_bytes()for n in live.geos.GEOS_FONTS+('native8.bin',)};pack=(e/'font-pack.bin').read_bytes();catalog=guide.engine.folds.previous.pack_catalog(pack,fonts['native8.bin']);allowed=guide.spans(e)
 palette={};catalog0=arena0=outside=provider0=canonical0=observer0=FE=None;observations=[];allocations=[];paint_prior=None
 for c in cases:
  tag=c['id'];ram=(out/'captures'/(tag+'-ram.bin')).read_bytes();colors=(out/'captures'/(tag+'-colors.bin')).read_bytes();reu=images[tag];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert len(reu)==SIZE and f.get('se_reu_banks',2)==32,(tag,'actual2MiB resource/provider/dump required')
  assert ram[s['se_reu_physical_owner']+32:s['se_reu_physical_owner']+256]==bytes([255])*224,'outside physical32 unavailable'
  assert live.merged(f,reu)==data and f.get('se_hot_caret')==4 and not f.get('se_hot_pending',1)
  assert (f.get('se_mode',1),f.get('se_e_ui',1),f.get('se_r_presentation',1),f.get('se_render_caps',1))==(c['mode'],c['ui'],c['presentation'],3)
  assert not any(f.get(n,1)for n in('se_e_job','se_e_error','se_e_draw_busy','se_e_redraw','se_f_owner','se_doc_read_locks','se_sel_mark','se_clip_busy'))
  assert(f.get('se_h_current',4),f.get('se_h_saved',4),f.get('se_h_dirty',1),f.get('se_h_end',2),f.get('se_h_cursor',2))==(1,1,0,0,0)
  assert f.read(0xc600,1024)==bytes((i*73+29)&255 for i in range(1024)) and f.read(s['se_editor_settings'],64)==(e/'editor-defaults.bin').read_bytes()
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'DIVERSE'and f.get('se_f_current_device',1)==8
  cc=catalog_identity(f.read(s['se_overlay_ids'],384),s);catalog0=cc if catalog0 is None else catalog0;assert cc==catalog0
  assert f.get('se_clip_length')==4 and object_bytes(f,reu,f.read(s['se_clip_token'],5),4)==live.grid.fixture()[:4]
  a=guide.grammar.arena(f,reu);arena0=a if arena0 is None else arena0;assert a==arena0,(tag,'whole typed53 allocation immutable, no53 mask')
  assert f.get('se_bc_flags',1)&1 and not f.get('se_bc_flags',1)&14
  observer=f.read(s['se_bc_arena'],17);ring=f.read(s['se_bc_ring'],96);assert observer[16]==0 and observer[14]==observer[15]
  immutable=observer[:13]+observer[14:]+ring;observer0=immutable if observer0 is None else observer0;assert immutable==observer0
  canonical=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],w)for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
  canonical0=canonical if canonical0 is None else canonical0;assert canonical==canonical0
  owners=list(f.read(s['se_reu_physical_owner'],32));allocations.append(dict(id=tag,occupied_banks=sum(v!=0 for v in owners),owner_counts={str(v):owners.count(v)for v in sorted(set(owners))},highest_owned_physical=max(i for i,v in enumerate(owners)if v)))
  provider=f.read(s['se_reu_map'],256)+f.read(s['se_reu_logical_owner'],256)+f.read(s['se_reu_physical_owner'],256);provider0=provider if provider0 is None else provider0;assert provider==provider0
  assert f.read(0xcbc0,1)==b'\xa5'and f.read(0xcbc3,2)==f.read(s['se_reu_epoch'],2)and f.read(0xcbc6,1)==f.read(0xcbc8,1)==b'\0'
  for i,h in enumerate(f.read(0xcbc1,2)):
   p=ram[s['se_reu_map']+h];assert h and 0<p<32 and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfd;part=pack[i*65536:(i+1)*65536];assert reu[p*65536:p*65536+len(part)]==part
  for order,name in enumerate(d['catalog']):
   image=(e/(name+'.seo')).read_bytes();slot=editor_pair_index(image[5],image[6]) if 'catalog_index' in s else order
   h=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);p=ram[s['se_reu_map']+h];assert h and 0<p<32 and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==2
   raw=image[36:];at=p*65536+(slot&15)*4096;assert reu[at:at+len(raw)]==raw
  h=f.get('se_gc_handle',1);p=ram[s['se_reu_map']+h];assert h and 0<p<32 and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfe
  fe=(h,p);FE=fe if FE is None else FE;assert fe==FE
  extra,paintproof=paint_scopes(e,f,reu,c)
  if paintproof:
   if paint_prior is not None and c['id']!='source3':assert paint_prior==paintproof['records_sha256'],'noC21sourcepublication: paintrecordsreadonly'
   paint_prior=paintproof['records_sha256']
  masked=bytearray(reu)
  for lo,hi in allowed+extra:masked[p*65536+lo:p*65536+hi]=bytes(hi-lo)
  v=digest(masked);outside=v if outside is None else outside;assert v==outside,(tag,'whole actual2MiB outside exact source-authenticated FE spans, inclunused asset/font tails')
  if c['page']is not None:assert f.get('se_e_menu',1)==6 and f.get('se_e_text_length',1)==c['page']
  bits,attrs=guide.raster(e,c,f,fonts,catalog)
  if c['mode']:assert ram[0x6000:0x7f40]==bits and ram[0x4000:0x43e8]==attrs
  w,hh,pixels=read_png(out/('native-'+tag+'.png'));assert(w,hh)==(384,272)
  for y in range(200):
   for x in range(320):
    at=(y//8)*40+x//8;bit=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attrs[at]>>4 if bit else attrs[at]&15;actual=pixels[(35+y)*w+32+x];assert actual==palette.setdefault(color,actual),(tag,'native pixel',x,y,color)
  observations.append(dict(id=tag,mode=c['mode'],paint_records=paintproof,png_sha256=sha(out/('native-'+tag+'.png'))))
 assert len(set(palette.values()))==len(palette)and(e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
 result=dict(status='PASS',allocation_observations=allocations,peak_occupied_banks=max(x['occupied_banks']for x in allocations),capacity_bytes=SIZE,reported_banks=32,frames=observations,native_pixels=FRAMES*64000,attributes=FRAMES*1000,whole2MiB_precise_FE_intervals=FRAMES-1,no_53_allowance=True,analysis53=arena0,visual_review='pending',scope=__doc__);dump(out/'result.json',result);return result

def source_snapshot(out,project):
 files=set();todo=[Path(__file__).resolve(),ROOT/'tools/diagnostics_model.py']
 while todo:
  p=todo.pop()
  if p in files:continue
  files.add(p)
  for n in ast.walk(ast.parse(p.read_text())):
   names=[q.name for q in n.names]if isinstance(n,ast.Import)else[n.module]if isinstance(n,ast.ImportFrom)and n.module else[]
   for name in names:
    for root in(ROOT/'tests',ROOT/'tools'):
     q=root/(name.split('.')[0]+'.py')
     if q.exists():todo.append(q.resolve())
 records=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)for p in sorted(files)]
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for r in records:z.write(ROOT/r['path'],r['path'])
  for p in sorted(project.parent.iterdir()):
   if p.is_file()and p.suffix in('.cs','.csproj','.json'):z.write(p,'host/'+p.name)
 dump(out/'verification-sources.json',dict(local_python_imports=records,explicit_lazy_imports=['diagnostics_model'],zip_sha256=sha(out/'verification-sources.zip')));return records

def private_project(n):
 project=guide.private_project(n);p=project.parent/'Program.cs';text=p.read_text();assert text.count('SUPEREDITOR_HELP_OWNED')==1;text=text.replace('SUPEREDITOR_HELP_OWNED',ENV);launch='\"-reusize\",\n            \"16384\"';assert text.count(launch)==1;text=text.replace(launch,'\"-reusize\",\n            \"2048\"');p.write_text(text)
 dump(project.parent/'current2mib-host-adapter.json',dict(actual_program_sha256=sha(p),base_adapter=sha(Path(guide.__file__)),ownership_ENV=ENV,changes=['launch REU2048KiB as well as explicitmonitorresource2048; no16MiBbacking allocation','new unique runtime directory and REU perownedrun','persist PID/executable/args/disk/REU/ports immediatelyafterstart','recordfailure closesonlynewprocess'],no_app_changes=True));return project

def negative_controls(n,p):
 with socket.socket()as sock:
  sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  try:free_ports([port])
  except AssertionError:occupied=True
  else:raise AssertionError('occupied listener admitted')
 for mutate in [lambda q:q['global_defaults'].update(monitor_port_start=10101),lambda q:q['steps'].append(dict(id='invalid-source-write',type='memory.write',params=dict(start=0x9200,bytes_hex='00')))]:
  q=json.loads(json.dumps(p));mutate(q)
  try:validate_plan(n,q)
  except AssertionError:pass
  else:raise AssertionError('mutated plan admitted')
 assert SIZE==2097152 and SIZE!=16*1024*1024
 own=n.e.parent/'ownership-negative';own.mkdir();fake_reu=own/'runtime-logs/fake.img'
 dump(own/'owned-process.json',dict(pid=os.getpid(),binary=PORT,text=10200,disk=str(n.e/'working.d81'),reu=str(fake_reu),executable='python3'))
 try:close_owned(own,n.e)
 except AssertionError:foreign_pid_refused=True
 else:raise AssertionError('unrelatedPID admitted')
 assert not(own/'closure.json').exists()
 return dict(occupied_listener_refused=occupied,wrong_port_refused=True,source_write_refused=True,foreign_pid_refused_before_signal=foreign_pid_refused,no_native_ports_opened=True)

def prepare(base,out):
 out.mkdir(parents=True);auth=authenticate(base);e=freeze(base,out/'native');validate_native(e)
 n=scenario(e);p=n.plan();rec=validate_plan(n,p);dump(n.out/'plan.yaml',p);dump(n.out/'cases.json',n.cases);dump(out/'authentication.json',auth);dump(out/'negative-controls.json',negative_controls(n,p))
 dump(out/'FE-spans.json',dict(spans=guide.spans(e),conditional63_records=[(0xdd68,0xdd68+240),(0xde68,0xde68+240)]if 'paint'in auth['all_assets_raw_label_map']else[],condition='actual validatedrecordfields/wholeCRC/NEXTreconstruction; noedits so rowshadows/staging stayprotected',whole_REU_bytes=SIZE,no_whole_bank_mask=True,no_53_allowance=True,unused_font_asset_and_row_tails_protected=True))
 project=private_project(n)
 b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 cmd=['dotnet','run','--no-build','--project',str(project),'--','compile-plan','--plan',str(n.out/'plan.yaml'),'--output-root',str(out/'compiled')]
 c=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=120);(out/'compile-plan.stdout.txt').write_text(c.stdout);(out/'compile-plan.stderr.txt').write_text(c.stderr);assert c.returncode==0
 compiled=list((out/'compiled').rglob('compiled_plan.json'));assert len(compiled)==1
 deps=source_snapshot(out,project);host=[dict(path=str(p),sha256=sha(p))for p in sorted((project.parent/'bin/Debug/net8.0').iterdir())if p.is_file()]
 result=dict(status='OFFLINE_PREPARED_COMPILED_NOT_NATIVE',adapter_sha256=sha(Path(__file__)),fixture=str(base),native=str(e),authentication=auth,plan=rec,plan_sha256=sha(n.out/'plan.yaml'),cases_sha256=sha(n.out/'cases.json'),project=str(project),compiled_plan=str(compiled[0]),compiled_plan_sha256=sha(compiled[0]),private_program_sha256=sha(project.parent/'Program.cs'),dependencies=deps,host_files=host,ownership_receipt=str(n.out/'owned-process.json'),ports=[10100,10200,10239],storage=dict(actual_REU_bytes=SIZE,dump_count=FRAMES,dump_bytes=FRAMES*SIZE,live_REU_bytes=SIZE,RAM_color_bytes=FRAMES*(0xd000+1000),estimated_total_incremental_bytes=50*1024*1024,closed_output='successfulclosedruntimehardlinks only; failures retained'),native_run=False,limits='Only frozen source/package/plan/compiler validation. Actual2MiB boot/capacity/pixels/guards pending future authorized --run and screenshotreview. No native1MiB/512KiB,hardware/physicalchord,save/reopen,performance orReadyOS claim.')
 dump(out/'prepare-result.json',result);return result

def close_owned(out,e):
 path=out/'owned-process.json';rec=dict(receipt=str(path),actions=[])
 if not path.exists():rec['status']='no-receipt-no-process-targeted';dump(out/'closure.json',rec);return
 r=json.load(open(path));assert r['binary']==PORT and 10200<=r['text']<=10239 and Path(r['disk']).resolve()==(e/'working.d81').resolve()
 reu=Path(r['reu']).resolve();assert reu.is_relative_to(out/'runtime-logs');pid=int(r['pid']);rec.update(pid=pid,disk=r['disk'],REU=str(reu),binary=r['binary'],text=r['text'])
 def command():return subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout.strip()
 def owned(cmd):return str(reu)in cmd and str(e/'working.d81')in cmd and f'127.0.0.1:{PORT}'in cmd and Path(r['executable']).name in cmd
 cmd=command()
 if cmd:
  assert owned(cmd),('PIDidentitychanged;notstopped',pid,cmd);os.kill(pid,signal.SIGTERM);rec['actions'].append('SIGTERM exactownedPID')
  for _ in range(40):
   if not command():break
   time.sleep(.1)
  cmd=command()
  if cmd:
   assert owned(cmd);os.kill(pid,signal.SIGKILL);rec['actions'].append('SIGKILL exactstillownedPID')
   for _ in range(40):
    if not command():break
    time.sleep(.1)
 assert not command();rec['status']='ownedPID-command-absent';dump(out/'closure.json',rec)

def execute(prepared):
 meta=json.load(open(prepared/'prepare-result.json'));assert meta['status']=='OFFLINE_PREPARED_COMPILED_NOT_NATIVE'and meta['adapter_sha256']==sha(Path(__file__))
 for r in meta['dependencies']:assert sha(ROOT/r['path'])==r['sha256'],('sealed dependency changed',r['path'])
 for r in meta['host_files']:assert sha(r['path'])==r['sha256']
 project=Path(meta['project']);assert sha(project.parent/'Program.cs')==meta['private_program_sha256'];e=Path(meta['native']);out=e/'gallery';validate_native(e)
 assert sha(out/'plan.yaml')==meta['plan_sha256']and sha(out/'cases.json')==meta['cases_sha256']and sha(meta['compiled_plan'])==meta['compiled_plan_sha256']
 assert not(out/'owned-process.json').exists()and not(out/'run').exists(),'never overwrite ownedrun'
 free_ports();proc=None;cmd=['dotnet','run','--no-build','--project',str(project),'--','run-compiled','--compiled',meta['compiled_plan'],'--close-vice','--no-tui'];env=dict(os.environ,**{ENV:str(out/'owned-process.json')})
 dump(out/'launch-command.json',dict(command=cmd,ports=PORTS,disk=str(e/'working.d81'),working_directory=str(ROOT)))
 try:
  with(out/'run-plan.stdout.txt').open('w')as so,(out/'run-plan.stderr.txt').open('w')as se:
   proc=subprocess.Popen(cmd,cwd=ROOT,stdout=so,stderr=se,env=env,start_new_session=True);dump(out/'owned-cli.json',dict(pid=proc.pid,command=cmd));rc=proc.wait(timeout=1800)
  assert rc==0,('runnerfailed;originalruntimepreserved',rc)
 finally:
  try:close_owned(out,e)
  finally:
   if proc is not None and proc.poll()is None:
    proc.terminate()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
  free_ports()
 outcome=json.loads((out/'run-plan.stdout.txt').read_text());assert outcome['Status']=='success';runtime=Path(outcome['RunDir']).resolve();assert runtime.is_relative_to(out/'runtime-logs')
 manifest=json.load(open(outcome['Manifest'],encoding='utf-8-sig'));assert manifest['status']=='success';receipts=[]
 def link(a,b):
  a,b=Path(a),Path(b);h=sha(a);os.link(a,b);assert a.stat().st_ino==b.stat().st_ino and sha(b)==h;receipts.append(dict(source=str(a),target=str(b.relative_to(out)),bytes=a.stat().st_size,sha256=h));return str(b)
 shutil.copytree(runtime,out/'run',copy_function=link);dump(out/'closed-hardlinks.json',dict(files=receipts,terminal_closed_success=True));dump(out/'owned-manifest.json',manifest)
 return evaluate(e)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--output',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args();assert not(a.run and a.verify)
 if a.run:assert a.prepared;print(json.dumps(execute(a.prepared.resolve()),indent=2))
 elif a.verify:assert a.prepared;print(json.dumps(evaluate(a.prepared.resolve()/'native'),indent=2))
 else:
  out=(a.output or ROOT/'build/current-2mib-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve();print('PREPARE',out,flush=True);r=prepare(a.fixture.resolve(),out);print('OFFLINE_COMPILED',r['plan'],flush=True)
