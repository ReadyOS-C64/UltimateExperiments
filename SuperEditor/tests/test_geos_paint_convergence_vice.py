"""Offline-first paired cold62/cold63 native paint-convergence qualification.

ROM File/Open and IRQ setup; timing uses the existing disclosed public-input
PC/SP seam. First-publication and settled PAL/NTSC costs remain separate. No
runtime substitution, forged certificate, main build, or physical-key claim.
Owned binary8900/text9000..9039. Preparation/compile never launches VICE.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ast,binascii,hashlib,json,os,re,shutil,socket,subprocess,sys,threading,zipfile
import test_geos_edit_profile as profile
import test_presentation_vice as presentation
import test_reu_capacity_vice as capacity
from test_lifecycle_cache_current import cache_frame
from closed_runtime_copy import run_with_closed_links
from d81_image import D81Image
from png_pixels import read_png
from vice_config import step
from test_cache_rebase_registered import metadata
import vice_plan
ROOT=profile.ROOT;timing=profile.timing
CONTROL=ROOT/'build/rebase-refusal-committed/20261026T235419243481Z/fixture'
CANDIDATE=ROOT/'build/paint-registration-private/cold63/fixture'
PORT=8900
native=timing.native.live.grid.native_text
DOCS={'prose':native('Ordinary words make a continuing paragraph with enough text to wrap. '*6+'\rTail remains.\r'),'styled':native('Alpha **bold words inside the continuing styled paragraph '*6+'** omega.\rTail remains.\r')}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verifier_dependencies():
 """Pin relevant imports, including lazy imports, without unrelated agent work."""
 local={p.stem:p for folder in('tests','tools')for p in(ROOT/folder).glob('*.py')}
 pending=[Path(__file__).resolve()]
 for module in list(sys.modules.values()):
  name=getattr(module,'__file__',None)
  if name and Path(name).resolve().parent in(ROOT/'tests',ROOT/'tools'):pending.append(Path(name).resolve())
 found={}
 while pending:
  p=pending.pop();name=str(p.relative_to(ROOT))
  if name in found:continue
  found[name]=sha(p)
  for node in ast.walk(ast.parse(p.read_text())):
   imports=[a.name for a in node.names]if isinstance(node,ast.Import)else[node.module]if isinstance(node,ast.ImportFrom)and node.module else[]
   pending.extend(local[n.split('.')[0]]for n in imports if n.split('.')[0]in local)
 return found

class Plan(profile.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1;p['global_defaults']['timeouts']['step_s']=180
  assert not p['global_defaults'].get('kill_stale',False)and not p['steps'][0]['params']['kill_stale'];return p
 def raw_state(self,ident):
  caps=self.out/'captures';caps.mkdir(exist_ok=True)
  self.raw(ident+'_coherent',['delete',f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',f'bsave "{caps}/{ident}-ram.bin" 0 $0000 $cfff',f'bsave "{caps}/{ident}-colors.bin" 0 $d800 $dbe7'])
  self.steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))

def freeze(base,e,variant):
 e.mkdir(parents=True);d=json.loads((base/'freeze.json').read_text());assert len(d['names'])==(62 if variant=='control'else 63)
 for name in('editor.prg','editor.lbl','editor.map','editor-report.json','editor-bindings.json','disk-manifest.json','supereditor.d81'):os.link(base/'build'/name,e/name)
 for name in d['names']:os.link(base/f'build/overlays/{name}.seo',e/(name+'.seo'))
 for name in timing.native.live.geos.GEOS_FONTS+('native8.bin','chargen.bin'):os.link(base/'fonts'/name,e/name)
 os.link(base/'product-sources.zip',e/'product-sources.zip')
 disk=D81Image((e/'supereditor.d81').read_bytes());prg=(e/'editor.prg').read_bytes();report=json.loads((e/'editor-report.json').read_text());s=report['symbols'];digest=report['resident_binding']['digest'];assert sha(e/'editor.prg')==d['prg_sha256']and sha(e/'supereditor.d81')==d['disk_sha256'];assert disk.read(b'SUPEREDITOR',kind=2).data==prg
 for name in d['names']:
  image=(e/(name+'.seo')).read_bytes();assert sha(e/(name+'.seo'))==d['assets'][name]and image[20:36]==image[36:52]==bytes.fromhex(digest)and disk.read(name.upper().encode(),kind=1).data==image
 pack=disk.read(b'GEOSFONTS',kind=1).data;(e/'font-pack.bin').write_bytes(pack);load=int.from_bytes(prg[:2],'little');at=2+s['session_defaults']-load;(e/'editor-defaults.bin').write_bytes(prg[at:at+64]);assert(e/'editor-defaults.bin').read_bytes()[:8]==b'SEST\1\x40\10\7'
 assert {'se_bc_arena','se_bc_incarnation','se_doc_roots','se_doc_meta','se_doc_generation','se_doc_length','se_h_current','se_h_saved','se_h_counter','se_clip_token','se_clip_length','se_gc_handle','se_gc_epoch','se_gf_state','se_render_caps'}<=s.keys()
 identity=dict(prg_sha256=d['prg_sha256'],disk_sha256=d['disk_sha256'],resident_binding=digest,catalog=d['names'],asset_sha256=d['assets'],font_pack_sha256=hashlib.sha256(pack).hexdigest(),product_sources_sha256=sha(e/'product-sources.zip'),cpu_fixture=str(base),variant=variant,input_freeze_sha256=sha(base/'freeze.json'))
 (e/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');shutil.copy2(e/'supereditor.d81',e/'working.d81')
 for name,data in DOCS.items():
  path=e/(name+'.seq');path.write_bytes(data);r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(path),name+',s'],capture_output=True);(e/(name+'-package.log')).write_bytes(r.stdout+r.stderr);assert not r.returncode
 work=D81Image((e/'working.d81').read_bytes())
 for name,data in DOCS.items():assert work.read(name.upper().encode(),kind=1).data==data
 for ent in disk.entries():assert work.read(ent.name).data==disk.read(ent.name).data
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');return e

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.boot()
 for doc,data in DOCS.items():
  for preset,caps in(('full',3),('markdown',1)):
   for action,key in(('insert',native('Q')[0]),('BACK',0x14),('CR',13)):
    ident=doc+'-'+preset+'-'+action
    # A real reopen resets canonical history; no host source/window seeding.
    n.open('open_'+ident,doc.upper().encode());n.typed(ident+'_caps','syntax '+preset);n.typed(ident+'_geos','mode hires');n.typed(ident+'_top','top');n.typed(ident+'_goto','goto 1');n.send(ident+'_column',b'\x1d'*85);n.memory(ident+'_caret_before','se_hot_caret',85,3)
    # Match the CPU proof's current-source publication through public commands.
    n.typed(ident+'_fresh_plain','syntax plain');n.typed(ident+'_fresh_preset','syntax '+preset);n.memory(ident+'_caps_before','se_render_caps',caps);n.memory(ident+'_pending_before','se_hot_pending',0)
    n.steps.append(step(ident+'-before_reu','dump.reu',mode='full',stage_tag=ident+'-before_reu'))
    after=data[:84]+data[85:]if action=='BACK'else data[:85]+bytes((key,))+data[85:]
    n.literal_return=key==13;n.measure(ident,after,3,key=key,category='wrapped-'+action);n.literal_return=False
    n.measurements[-1].update(caps=caps,document=doc,operation=action,before_source=data.hex(),expected_caret=84 if action=='BACK'else 86)
    n.memory(ident+'_pending_after','se_hot_pending',1)
    n.send(ident+'_actual_Undo',b'\x1a');n.memory(ident+'_Undo_length','se_v_length',len(data),3);n.memory(ident+'_Undo_pending','se_hot_pending',0);n.memory(ident+'_Undo_clean','se_h_dirty',0);n.raw_state(ident+'-undo')
 return n

def prepare(control,candidate,out,compile_only=False):
 assert not out.exists();out.mkdir(parents=True)
 # Admit either the original corrected62 control or the independently native-
 # qualified current scatter package. Never silently mix a changed control.
 cold=json.loads((ROOT/'build/paint-registration-private/cold63/release.json').read_text());c=json.loads((control/'freeze.json').read_text());old=json.loads((Path(cold['control']['base'])/'freeze.json').read_text())
 identity=lambda d:(d['prg_sha256'],d['assets'],d['disk_sha256'])
 admission='original corrected62'
 if identity(c)!=identity(old):
  qualified=ROOT/'build/vic-stride-probe/native-ready3/candidate-package/fixture'
  current=json.loads((qualified/'freeze.json').read_text())
  assert identity(c)==identity(current), 'control is not either qualified cohort'
  assert c['git_commit']=='ac7b2705f4d00c6cf99aee7ded46a16ac3b79409'
  assert {n for n,h in c['assets'].items()if h!=old['assets'][n]}=={'gtype','type'}
  assert json.loads((ROOT/'build/vic-stride-probe/native-ready3/comparison.json').read_text())['status']=='PASS'
  assert json.loads((ROOT/'build/vic-stride-probe/root-native-review/visual-review.json').read_text())['frames']==48
  admission='native-qualified ac7 current62'
 (out/'control-admission.json').write_text(json.dumps(dict(cohort=admission,PRG=c['prg_sha256'],D81=c['disk_sha256'],assets=c['assets']),indent=2)+'\n')
 info={}
 for variant,base in(('control',control),('candidate',candidate)):
  e=freeze(base,out/variant,variant);n=scenario(e);plan=n.plan();assert len(n.measurements)==12 and len({s['id']for s in plan['steps']})==len(plan['steps'])
  assert sum(v['type']=='dump.reu' for v in plan['steps'])==36
  (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n');(n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
  dependencies=verifier_dependencies()
  with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
   for folder in('tests','tools'):
    for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
  (e/'qualification.json').write_text(json.dumps(dict(status='PREPARED_NOT_EXECUTED',variant=variant,source=str(base),port=PORT,dependencies=dependencies,script_sha256=sha(Path(__file__)),scope=__doc__),indent=2)+'\n')
  if compile_only:
   project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;r=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(r.stdout+r.stderr);assert not r.returncode
   command=['dotnet','run','--no-build','--project',str(project),'--','compile-plan','--plan',str(n.out/'plan.yaml')]
   r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120);(n.out/'compile-plan.stdout.txt').write_text(r.stdout);(n.out/'compile-plan.stderr.txt').write_text(r.stderr);assert not r.returncode,(variant,r.stdout[-1200:],r.stderr[-1200:])
  info[variant]=dict(path=str(e),steps=len(n.steps),frames=12,IRQbytes=n.keys,REU_snapshots=36,expected_raw_REU_bytes=36*16777216,plan_sha256=sha(n.out/'plan.yaml'),compile_only=compile_only)
 receipt=dict(status='PREPARED_NOT_NATIVE',variants=info,port=PORT,text_ports=[9000,9039],script_sha256=sha(Path(__file__)),scope=__doc__,limits='Native timing/pixels/wholeREU verdict pending execution. CPU percentages not PAL predictions; CR regression is explicit. Before/post snapshots bracket each pending edit; Undo is separately source/pixel/history verified.')
 (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True);return receipt

def loaded(e):
 n=presentation.scenario_loaded(e);n.__class__=Plan;n.cost_profile=True;return n

def outgoing_record(record,row,header,data,start,writer_verified):
 """Validate a newly permitted R19 checkpoint, never its surrounding spare."""
 assert writer_verified and 0<=row<22 and len(record)==len(header)==64
 assert record[:4]==b'C\2\x40\1' and record[44:62]==bytes(18)
 assert int.from_bytes(record[62:64],'little')==binascii.crc_hqx(record[:62],65535)
 assert record[7:35]==header[4:32] and record[41:44]==header[32:35]
 # These two independently modeled fixtures have no fence/region carry.
 assert b':::' not in data and record[35:41]==bytes(6)
 assert 0<=start<=len(data)
 cr=data.find(b'\r',start);next_source=cr+1 if cr>=0 else len(data)
 assert int.from_bytes(record[4:7],'little')==next_source
 return dict(row=row,offset=0x700+row*0x800,bytes=64,next_source=next_source)

def outgoing_negative_vectors():
 header=bytes(range(64));data=b'abc\rdef';record=bytearray(64)
 record[:4]=b'C\2\x40\1';record[4:7]=(4).to_bytes(3,'little');record[7:35]=header[4:32];record[41:44]=header[32:35]
 def seal(r):r[62:64]=binascii.crc_hqx(r[:62],65535).to_bytes(2,'little');return bytes(r)
 record=seal(record);outgoing_record(record,0,header,data,0,True);passed=['valid-control']
 for name,at in [('magic',0),('schema',1),('length',2),('VALID',3),('NEXT',4),('key',7),('carry',35),('TOP',41),('reserved',44),('CRC',62)]:
  bad=bytearray(record);bad[at]^=1
  if name!='CRC':bad=seal(bad)
  try:outgoing_record(bytes(bad),0,header,data,0,True)
  except AssertionError:passed.append(name)
  else:raise AssertionError(('bad outgoing record accepted',name))
 for name,row,writer in [('row22',22,True),('negative-row',-1,True),('missing-writer',0,False)]:
  try:outgoing_record(record,row,header,data,0,writer)
  except AssertionError:passed.append(name)
  else:raise AssertionError(('bad outgoing authority accepted',name))
 for at in (31,96):
  before=bytearray(128);after=bytearray(before);after[32:96]=record;after[at]^=1
  allowed=bytearray(before);allowed[32:96]=after[32:96]
  assert allowed!=after;passed.append('adjacent-'+str(at))
 return dict(status='PASS',vectors=passed,scope='Offline verifier negatives; recomputed CRC cannot excuse wrong schema/key/TOP/NEXT/carry/reserved fields. Exact64B permission excludes adjacent bytes.')

def outgoing_updates(e,f,pre,oldreu,newreu,bank,data,fonts,measurement,spans):
 """Authenticate the frozen OP7 producer before adding exact changed records."""
 identity=json.loads((e/'freeze.json').read_text());base=Path(identity['cpu_fixture'])
 assert sha(base/'freeze.json')==identity['input_freeze_sha256']
 image=(e/'rangeio.seo').read_bytes();raw=image[36:];idx=identity['catalog'].index('rangeio');s=f.s
 assert image[5:7]==bytes((0,19)) and image[20:36]==raw[:16]==bytes.fromhex(identity['resident_binding'])
 assert len(raw)==int.from_bytes(image[8:10],'little') and binascii.crc_hqx(raw,65535)==int.from_bytes(image[12:14],'little')
 def emitted(name,label):
  path=metadata(base,name);payload=(e/(name+'.seo')).read_bytes()[36:]
  assert path.with_suffix('.bin').read_bytes()==payload
  labels={name:int(pc,16)for pc,name in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',path.with_suffix('.lbl').read_text())}
  origin=0xb000 if (e/(name+'.seo')).read_bytes()[5] else 0xa000
  return payload[labels[label]-origin:],labels
 selector,_=emitted('geospage','gsc_publish');entry,labels=emitted('rangeio','entry')
 word=lambda n:bytes((n&255,n>>8))
 assert selector[:12]==b'\xa9\7\x8d'+word(s['se_overlay_frame'])+b'\xa9\x13\xa2\0\x4c'+word(s['se_overlay_call'])
 assert entry[:10]==b'\xad'+word(s['se_overlay_frame'])+b'\xc9\7\xd0\3\x4c'+word(labels['se_gcl_publish'])
 writer=[q for q in measurement['cost_profile']['groups']if(q['slot'],q['id'])==(0,19)]
 assert len(writer)==1 and writer[0]['calls']>0
 for view,reu in((pre,oldreu),(f,newreu)):
  assert view.ram[s['se_overlay_ids']+idx]==19 and view.ram[s['image_slot']+idx]&1==0
  assert view.ram[s['image_size_lo']+idx]|view.ram[s['image_size_hi']+idx]<<8==len(raw)
  assert view.ram[s['image_crc_lo']+idx]|view.ram[s['image_crc_hi']+idx]<<8==binascii.crc_hqx(raw,65535)
  h=view.ram[s['se_overlay_asset']+(idx>>4)];p=view.ram[s['se_reu_map']+h]
  assert h and p and view.ram[s['se_reu_logical_owner']+h]==view.ram[s['se_reu_physical_owner']+p]==2
  at=p*65536+(idx&15)*4096;assert reu[at:at+len(raw)]==raw
 _,_,rows,_=presentation.expected_geos(f,data,fonts);offset=bank*65536;header=bytes(newreu[offset:offset+64]);records=[]
 for row in range(22):
  at=0x700+row*0x800;old=oldreu[offset+at:offset+at+64];new=bytes(newreu[offset+at:offset+at+64])
  # Candidate snapshots already have a separate qualified, phase-limited scope.
  # They can reuse this spare. They gain no additional permission here.
  if old==new or any(lo<=at and at+64<=hi for lo,hi in spans):continue
  assert row<len(rows)
  records.append(outgoing_record(new,row,header,data,rows[row].start,True))
 return records

def arena_pages(f,reu):
 s=f.s;token=f.read(s['se_bc_arena'],5);assert any(token)
 proof,raw=cache_frame(s,f.ram,reu,f.e);assert proof['banks']==1 and proof['bytes']==65536
 oid=token[0];logical=f.ram[s['object_extents']+oid*16];physical=f.ram[s['se_reu_map']+logical]
 assert proof['token']==token.hex()and f.read(s['se_bc_incarnation'],4)!=bytes(4)
 spans=[(0,256),(0x100,0x180),(0x900,0xf00),(0xf00,0x1000)];pages=[]
 for page in range(1,16):
  d=raw[0x100+page*8:0x108+page*8]
  if d[3]!=1:continue
  assert d[2]in range(1,8)and d[6:]==bytes(2)and int.from_bytes(d[4:6],'little')==binascii.crc_hqx(d[:4]+d[6:],65535)
  h=raw[page*4096:page*4096+64];used=int.from_bytes(h[21:23],'little')
  assert h[:4]==b'BP\1\1'and h[4]==page and h[5]==d[2]and h[6:8]==d[:2]and h[8:12]==f.read(s['se_bc_incarnation'],4)and h[12:17]==token and used<=4032 and not any(h[42:])
  assert int.from_bytes(h[37:39],'little')==binascii.crc_hqx(h[:3]+h[4:37]+h[39:],65535)
  payload=raw[page*4096+64:page*4096+64+used];assert int.from_bytes(h[39:41],'little')==binascii.crc_hqx(payload,65535)
  pages.append(page);spans.append((page*4096,(page+1)*4096))
 return proof,physical,spans,pages

def packet_geometry(f,reu,data,fonts):
 s=f.s;handle=f.get('se_gc_handle',1);bank=f.ram[s['se_reu_map']+handle];assert handle and bank
 raw=reu[bank*65536:(bank+1)*65536];_,_,rows,_=presentation.expected_geos(f,data,fonts)
 assert raw[:4]==bytes((1,len(rows),0x47,3)) and int.from_bytes(raw[32:35],'little')==f.get('se_v_top')
 for i,row in enumerate(rows):
  p=raw[0x200+i*0x800:0x220+i*0x800]
  assert tuple(int.from_bytes(p[j:j+3],'little')for j in(0,3,6))==(row.start,row.end,row.next) and(p[14],p[15])==(row.height,row.top),('packet geometry',i)
 assert f.read(s['se_v_rows'],len(rows)*3)==b''.join(row.start.to_bytes(3,'little')for row in rows) and f.get('se_v_bottom')==rows[-1].next
 return len(rows)

def evaluate(e):
 n=loaded(e);old_expected,old_catalog=timing.semantic.expected,timing.FontCatalog;timing.semantic.expected=presentation.expected_geos
 from test_geos_preview_vice import pack_catalog
 timing.FontCatalog=lambda p,native:pack_catalog((e/'font-pack.bin').read_bytes(),native)
 try:result=timing.evaluate(n)
 finally:timing.semantic.expected,timing.FontCatalog=old_expected,old_catalog
 reus=timing.native.live.grid.reu_images(n.out/'run');s=n.s;frozen=json.loads((e/'freeze.json').read_text());pack=(e/'font-pack.bin').read_bytes();fonts={name:(e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)};scopes=[]
 measured={q['id']:q for q in result['measurements']}
 def captured(ram,colors):
  f=presentation.Captured(s,ram,colors,e);f.e=e;return f
 def full_assets(f,reu):
  assert f.read(0xc600,1024)==n.canary and f.read(s['se_editor_settings'],64)==(e/'editor-defaults.bin').read_bytes()
  for i,name in enumerate(frozen['catalog']):
   logical=f.ram[s['se_overlay_asset']+(i>>4)];bank=f.ram[s['se_reu_map']+logical];assert logical and bank and f.ram[s['se_reu_logical_owner']+logical]==f.ram[s['se_reu_physical_owner']+bank]==2
   data=(e/(name+'.seo')).read_bytes()[36:];at=bank*65536+(i&15)*4096;assert reu[at:at+len(data)]==data
  assert f.read(s['se_gf_state'],1)==b'\xa5'and f.read(s['se_gf_state']+3,2)==f.read(s['se_reu_epoch'],2)
  for i,h in enumerate(f.read(s['se_gf_state']+1,2)):
   bank=f.ram[s['se_reu_map']+h];assert h and bank and f.ram[s['se_reu_logical_owner']+h]==f.ram[s['se_reu_physical_owner']+bank]==0xfd;data=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(data)]==data
 for item in n.measurements:
  ident=item['id'];caps=n.out/'captures';before=(caps/(ident+'-before-ram.bin')).read_bytes();after=(caps/(ident+'-ram.bin')).read_bytes();colors=(caps/(ident+'-colors.bin')).read_bytes();f=captured(after,colors);pre=captured(before,bytes(1000));oldreu=bytearray(reus[ident+'-before']);newreu=bytearray(reus[ident]);assert len(oldreu)==len(newreu)==16777216
  assert f.get('se_render_caps',1)==item['caps']and f.get('se_hot_caret')==item['expected_caret']and f.get('se_hot_pending',1)==1 and f.get('se_sel_mark',1)==0
  fields=[('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)]
  assert pre.read(s['se_doc_roots'],512)==f.read(s['se_doc_roots'],512)and all(pre.read(s[k],w)==f.read(s[k],w)for k,w in fields),(ident,'pending source/history/clipboard')
  assert f.get('se_clip_length')==0;full_assets(f,bytes(newreu));row_count=packet_geometry(f,bytes(newreu),bytes.fromhex(item['source']),fonts)
  FE=[]
  for view in(pre,f):
   handle=view.get('se_gc_handle',1);bank=view.ram[s['se_reu_map']+handle];assert handle and bank and view.get('se_gc_epoch',2)==view.get('se_reu_epoch',2)and view.ram[s['se_reu_logical_owner']+handle]==view.ram[s['se_reu_physical_owner']+bank]==0xfe;FE.append(bank)
  assert FE[0]==FE[1]
  if frozen['variant']=='candidate':
   assert bytes(reus[ident+'-before'])[FE[0]*65536+0xdd68:FE[0]*65536+0xdd6a]==b'\xa5\5',('fresh genuine convergence certificate',ident)
   assert(f.read(0x914a,1)==b'\xa7')==(item['operation']!='CR'),('actual convergence admission/structural refusal',ident)
  spans=[(0,64),(0x600,0x680),(0xb200,0xe568)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]
  if frozen['variant']=='candidate':spans +=[(0x200+i*0x800+0x480,0x200+i*0x800+0x480+842)for i in range(22)if i!=2]
  outgoing=outgoing_updates(e,f,pre,oldreu,newreu,FE[0],bytes.fromhex(item['source']),fonts,measured[ident],spans)
  spans +=[(q['offset'],q['offset']+q['bytes'])for q in outgoing]
  for lo,hi in spans:oldreu[FE[0]*65536+lo:FE[0]*65536+hi]=newreu[FE[0]*65536+lo:FE[0]*65536+hi]
  a,p0,allowed0,pages0=arena_pages(pre,bytes(reus[ident+'-before']));b,p1,allowed1,pages1=arena_pages(f,bytes(reus[ident]));assert p0==p1 and a['token']==b['token']and a['banks']==b['banks']
  for lo,hi in set(allowed0+allowed1):oldreu[p0*65536+lo:p0*65536+hi]=newreu[p0*65536+lo:p0*65536+hi]
  assert oldreu==newreu,(ident,'whole16MiB outside explicit FE and authenticated53 page union')
  undo_ram=(caps/(ident+'-undo-ram.bin')).read_bytes();undo_colors=(caps/(ident+'-undo-colors.bin')).read_bytes();u=captured(undo_ram,undo_colors);ur=reus[ident+'-undo'];original=bytes.fromhex(item['before_source']);assert timing.native.live.merged(u,ur)==original and u.get('se_hot_pending',1)==0 and u.get('se_h_dirty',1)==0 and u.get('se_h_current',4)==u.get('se_h_saved',4)and u.get('se_hot_caret')==85
  assert all(u.get(k,1)==0 for k in('se_e_job','se_e_error','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks'));bits,attrs,_,_=presentation.expected_geos(u,original,fonts);assert u.read(0x6000,8000)==bits and u.read(0x4000,1000)==attrs;full_assets(u,ur);packet_geometry(u,ur,original,fonts)
  scopes.append(dict(id=ident,independent_packet_rows=row_count,FE_bank=FE[0],FE_spans=spans,outgoing_checked_records=outgoing,arena_bank=p0,arena_before=a,arena_after=b,arena_page_union=sorted(set(pages0+pages1)),whole16MiB_guard=True,Undo_source_pixels_history=True))
 assert(e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes();result.update(variant=frozen['variant'],scoped_REU=scopes,limits='Pending edit intervals are whole16MiB exact outside documented FE ranges, individually authenticated changed outgoing64B checkpoints, and CRC/authenticated53 root/directory/journal/committed-page unions. Undo performs legitimate canonical/history writes and is checked by independent source/pixels plus restored history/current/font/catalog/shim, not claimed REU-readonly. Service timing is not physical keyboard latency.');(n.out/'paint-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def compare(out):
 runs={v:json.loads((out/v/'timing/paint-result.json').read_text())for v in('control','candidate')};rows=[]
 assert len(runs['control']['measurements'])==len(runs['candidate']['measurements'])==12
 for a,b in zip(runs['control']['measurements'],runs['candidate']['measurements']):
  assert a['id']==b['id']and a['source']==b['source'];crops=[]
  for v,r in runs.items():
   w,h,pixels=read_png(out/v/'timing'/('native-'+a['id']+'.png'));x,y=r['native_viewport'];crops.append(tuple(pixel for j in range(200) for pixel in pixels[(y+j)*w+x:(y+j)*w+x+320]))
  assert crops[0]==crops[1],(a['id'],'paired native active pixels')
  rows.append(dict(id=a['id'],control_first=a['first_publish_cycles'],candidate_first=b['first_publish_cycles'],control_settled=a['emulated_cycles'],candidate_settled=b['emulated_cycles'],change=100*(b['emulated_cycles']/a['emulated_cycles']-1),control_loads=a['counter_deltas']['se_overlay_loads'],candidate_loads=b['counter_deltas']['se_overlay_loads'],paired_pixels=True))
 result=dict(status='PASS paired native',cases=rows,scope=__doc__);(out/'paired-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def execute(e):
 q=json.loads((e/'qualification.json').read_text());assert q['script_sha256']==sha(Path(__file__))
 for p,h in q['dependencies'].items():assert sha(ROOT/p)==h,('prepared verifier changed; reprepare',p)
 for port in(PORT,*range(9000,9040)):
  with socket.socket()as s:s.bind(('127.0.0.1',port))
 n=loaded(e);plan=json.loads((n.out/'plan.yaml').read_text());project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 r=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(r.stdout+r.stderr);assert not r.returncode
 stop=threading.Event()
 def watch():
  while not stop.wait(.1):
   p=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for line in p.stdout.splitlines():
    if '/x64sc 'in line and f'-binarymonitoraddress 127.0.0.1:{PORT}'in line and str(e/'working.d81')in line:
     fields=line.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(PID=int(fields[0]),parent=int(fields[1]),command=fields[2],binary_port=PORT,text_ports=[9000,9039],match='Both exact owned disk and binary monitor port'),indent=2)+'\n');return
 thread=threading.Thread(target=watch,daemon=True);thread.start()
 try:
  manifest=run_with_closed_links(capacity.run_owned_plan,plan,n.out,timeout=1800)
 except BaseException as error:
  outcome=n.out/'run-plan.stdout.txt'
  (e/'execution-error.json').write_text(json.dumps(dict(error=repr(error),owned_runner_output=outcome.read_text()if outcome.exists()else None,note='Inspect original RunDir manifest for product failure; failed closed-link copy may raise its own assertion.'),indent=2)+'\n');raise
 finally:
  stop.set();thread.join(timeout=3);closed=dict(PID_witness=(e/'owned-process.json').exists())
  if closed['PID_witness']:
   owned=json.loads((e/'owned-process.json').read_text());p=subprocess.run(['ps','-p',str(owned['PID']),'-o','command='],capture_output=True,text=True);closed.update(PID=owned['PID'],exact_command_absent=str(e/'working.d81')not in p.stdout)
  ports=[]
  for port in(PORT,*range(9000,9040)):
   with socket.socket()as sock:
    try:sock.bind(('127.0.0.1',port))
    except OSError:ports.append(port)
  closed['occupied_ports']=ports;(e/'owned-closure.json').write_text(json.dumps(closed,indent=2)+'\n')
 assert closed['PID_witness']and closed['exact_command_absent']and not closed['occupied_ports'],closed
 (n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return evaluate(e)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--control',type=Path,default=CONTROL);p.add_argument('--candidate',type=Path,default=CANDIDATE);p.add_argument('--out',type=Path);p.add_argument('--compile-only',action='store_true');p.add_argument('--verify',type=Path);p.add_argument('--run-prepared',type=Path);p.add_argument('--compare',type=Path);p.add_argument('--oracle-negatives',action='store_true');a=p.parse_args()
 if a.oracle_negatives:print(json.dumps(outgoing_negative_vectors(),indent=2))
 elif a.compare:compare(a.compare.resolve())
 elif a.verify:evaluate(a.verify.resolve())
 elif a.run_prepared:execute(a.run_prepared.resolve())
 else:
  out=a.out or ROOT/'build/paint-convergence-native-adapter'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prepare(a.control.resolve(),a.candidate.resolve(),out.resolve(),a.compile_only)
