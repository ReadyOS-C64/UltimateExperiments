"""Extended immutable-editor callable lifecycle admission/state witnesses.

Actual C29/R26 sidecars are byte-identical to the frozen package. Real editor
commands create history/selection and bind File/Open on modeled KERNAL/DOS only.
Session settings initialization and fresh cold descriptor/R26/prelude are explicit
host seams. No product/shared build or native/host-handoff claim.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,binascii,hashlib,json,shutil,sys,zipfile
import test_lifecycle_editor as component
import test_editor_file_integration as filemodel
import test_geos_semantic_editor as semantic
import editor_settings
from geos_preview_model import render as preview_render
from test_geos_preview_vice import pack_catalog
from overlays import HEADER
from d81_image import D81Image
ROOT=component.ROOT;BASE=ROOT/'build/geos-incremental-editor/20261025T081538083121Z/fixture'
DATA=semantic.geos.native_text('# Custom\rOrdinary text for selection.\r:::basic\r10 PRINT "Hi"\r:::\rTail.')
NAME=b'BOUND@NATIVE'


class Fixture(component.Fixture,filemodel.IntegratedFiles):
 def __init__(self,*a):
  self.fs={NAME:DATA};self.channels={};self.trace=[];self.inject={};self.selected_in=self.selected_out=None;self.st=0;self.dos=b'00, OK,00,00\r';self.directory=b'';self.actions=[];self.opens=[];self.dos_commands=[];self.service_steps=0
  super().__init__(*a)
 call=filemodel.IntegratedFiles.call
 command=filemodel.IntegratedFiles.command
 rom=filemodel.IntegratedFiles.rom
 raw_sectors=filemodel.IntegratedFiles.raw_sectors
 directory_stream=filemodel.IntegratedFiles.directory_stream
 start=filemodel.IntegratedFiles.start
 enter_name=filemodel.IntegratedFiles.enter_name
 object_bytes=filemodel.IntegratedFiles.object_bytes
 def key(self,byte,error=None,mods=0):
  return filemodel.IntegratedFiles.key(self,byte,error=error,mods=mods)


def run(out,previous,smoke=False):
 frozen,identity=semantic.geos.freeze(out,previous);images=component.build(out/'leaf',frozen)
 for n,b in images.items():assert b==(frozen/'build/overlays'/(n+'.seo')).read_bytes(),(n,'not packaged byte identity')
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=frozen;semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=identity['names']
 dll=component.fold.retention.runner(out);f=None;cases=[]
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in semantic.geos.GEOS_FONTS+('native8.bin',)}
 disk=D81Image((frozen/'build/supereditor.d81').read_bytes());pack=disk.read(b'GEOSFONTS',kind=1).data;catalog=pack_catalog(pack,fonts['native8.bin'])
 labels={x[2].lstrip('.'):int(x[1],16)for line in(out/'leaf/lifecopy.lbl').read_text().splitlines()if len(x:=line.split())==3 and x[0]=='al'}
 def setup():
  nonlocal f
  if f:f.close()
  f=Fixture(out,frozen,dll,True);f.source(semantic.geos.native_text('Initial source.'));assert not f.call('se_clip_init').p&1 #host source reset requires real clipboard init
  f.start('menu','O');f.key(0x86);assert f.get('se_f_device',1)==9;f.enter_name(NAME,True);f.settle()
  assert f.merged()==DATA and f.get('se_f_current_device',1)==9 and f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==NAME
  f.command(99);f.render()
  settings=bytearray(f.read(0xCB80,64));settings[8:15]=bytes((1,1,0,10,6,7,7));settings[15:22]=bytes((1,1,0,24,2,0,4));settings[57:64]=bytes((1,26,0,10,13,6,4))
  validated=editor_settings.decode(settings)
  for profile in validated.profiles:assert(profile.origin,profile.family,profile.size)in catalog.faces
  f.m.load(0xCB80,settings);f.m.write(0xCBD5,0) #explicit validated session-init seam
  f.m.load(0x800,bytes.fromhex(json.loads((frozen/'build/editor-report.json').read_text())['resident_binding']['digest'])+bytes(0x40));f.m.load(0xA00,(out/'leaf/resume.bin').read_bytes())
  return bytes(settings)
 def journal():return f.object_bytes(f.read(f.s['se_h_token'],5),f.get('se_h_end',2))
 def preserved():
  names=[('se_f_current_name',18),('se_editor_settings',64),('se_l_pan',3),('se_v_top',3),('se_l_preferred',3),('se_l_manual',1),('se_mode',1),('se_e_ui',1),('se_r_presentation',1),('se_h_end',2),('se_h_cursor',2),('se_h_current',4),('se_h_saved',4)]
  return f.canonical()+b''.join(f.read(f.s[n],w)for n,w in names)+journal()
 def source_proof():
  data=f.merged();before=f.canonical();f.render();bits,attrs,_,_=semantic.expected(f,data,fonts)
  assert(f.read(0x6000,8000),f.read(0x4000,1000))==(bits,attrs) and f.canonical()==before and f.read(0xC600,1024)==f.shim
 def capture(before_begin=None):
  f.render()
  if before_begin:before_begin()
  f.put('se_e_redraw',0,1);f.put('se_status',1,1);stable=preserved();before=f.reu();r,n=f.lc(0);assert not r.p&1 and r.a==1,('BEGIN',r.a,r.p,f.debug())
  steps=0
  while True:
   r,n=f.lc(1);steps+=1;assert not r.p&1,(steps,r.a,r.p)
   if not r.a:break
   assert r.a==1 and steps<500
  assert steps==381 and preserved()==stable
  saved=f.reu();bank=f.m.read(0x811);at=bank*65536;payload=saved[at:at+0xBC18];header=saved[at+0xBC20:at+0xBC60]
  want=bytearray(before);want[at:at+0xBC18]=payload;want[at+0xBC20:at+0xBC60]=header;assert saved==want and binascii.crc_hqx(payload,0xffff)==int.from_bytes(header[51:53],'little')
  return stable,saved,payload
 def restore(stable,saved,payload):
  preserve={n:f.read(f.s[n],w)for n,w in [('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256),('se_reu_epoch',2),('se_reu_retired',1)]}
  for at,length,offset in component.EXTENTS:f.m.load(at,bytes((i*37+19)&255 for i in range(length)))
  for n,data in preserve.items():f.m.load(f.s[n],data)
  f.m.load(0xA000,images['lifecopy'][HEADER:]);f.m.load(0xA00,(out/'leaf/resume.bin').read_bytes())
  r,n=f.fast_call(labels['se_lc_restore_begin']);assert not r.p&1 and r.a==1
  for count in range(200):
   if f.m.read(0x820)==4 and f.m.read(0x827)==2:
    for n,v in [('pc',labels['se_lc_copy_step']),('sp',0xFD),('p',0x24)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
    assert dll.gm_idle(f.m.handle,0xA00,100000) and f.m.regs().sp==255
    for at,length,offset in component.EXTENTS:assert f.read(at,length)==payload[offset:offset+length]
    assert f.reu()==saved and f.read(0xC600,1024)==f.shim
    assert dll.gm_idle(f.m.handle,f.s['se_idle'],300000),('prelude stalled',hex(f.m.regs().pc));break
   r,n=f.fast_call(labels['se_lc_copy_step']);assert not r.p&1 and r.a==1
  else:raise AssertionError('restore did not converge')
  assert preserved()==stable and f.reu()==saved and not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_job','se_e_draw_busy'))
 def position(column):
  f.typed(semantic.geos.native_text('goto 2'))
  for _ in range(column):f.command(2)
 def save_bound(wanted):
  f.command(81);assert f.get('se_e_error',1)==0 and bytes(f.fs[NAME])==wanted
  assert f.get('se_f_current_device',1)==9 and f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==NAME
  assert any(device==9 for name,device,sa in f.opens)
 def remove(ident,slot):
  index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)==slot)
  f.m.write(f.s['se_overlay_ids']+index,0);f.m.write(f.s['se_overlay_active']+slot,0)
 def reu_derived_only(before):
  after=f.reu();want=bytearray(before)
  for h in range(1,256):
   if f.m.read(f.s['se_reu_logical_owner']+h)==0xFE:
    p=f.m.read(f.s['se_reu_map']+h);want[p*65536:(p+1)*65536]=after[p*65536:(p+1)*65536]
  assert after==want,'changed REU outside authenticated disposable FE page'
 try:
  settings=setup();allocated=[]
  while True:
   r,n=f.fast_call(f.s['se_reu_alloc'],a=0xA5)
   if r.p&1:assert r.a==1;break
   h=r.a;p=f.m.read(f.s['se_reu_map']+h);assert f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+p)==0xA5;allocated.append((h,p))
  assert allocated and not any(v==0 for v in f.read(f.s['se_reu_logical_owner']+1,255)) and not any(v==0 for v in f.read(f.s['se_reu_physical_owner']+1,255))
  stable=preserved();before=f.reu();owners=f.read(f.s['se_reu_map'],768);r,n=f.lc(0)
  assert r.p&1 and r.a==1 and f.m.read(0x810)==f.m.read(0x820)==0 and f.reu()==before and preserved()==stable and f.read(f.s['se_reu_map'],768)==owners,('allocation refusal',r.a,r.p)
  for h,p in allocated:
   assert f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+p)==0xA5
   r,n=f.fast_call(f.s['se_reu_free'],x=h);assert not r.p&1
  r,n=f.lc(0);assert not r.p&1 and r.a==1 and f.m.read(0x820)==1
  h=f.m.read(0x810);p=f.m.read(0x811);assert f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+p)==0xFC
  r,n=f.lc(2);assert not r.p&1 and r.a==0 and f.m.read(0x820)==0 and preserved()==stable
  cases.append(dict(tag='actual-allocation-exhaustion-recovery',owned_A5_allocations=len(allocated),error=1));print('PASS',cases[-1],flush=True)
  if not smoke:
   settings=setup();position(8);at=f.get('se_hot_caret');q=semantic.geos.native_text('Q');f.key(q[0]);f.command(68)
   for _ in range(4):f.command(1)
   assert f.get('se_sel_mark',1)==1 and f.get('se_hot_caret')<f.get('se_sel_anchor'),('reversed selection',f.get('se_sel_mark',1),f.get('se_hot_caret'),f.get('se_sel_anchor'),f.get('se_hot_pending',1))
   wanted=DATA[:at]+q+DATA[at:];lo,hi=f.get('se_hot_caret'),f.get('se_sel_anchor');clip=wanted[lo:hi]
   stable,saved,payload=capture();restore(stable,saved,payload);source_proof();f.command(69)
   assert f.object_bytes(f.read(f.s['se_clip_token'],5),f.get('se_clip_length'))==clip
   f.command(50);f.command(16);assert f.merged()==DATA;f.command(17);assert f.merged()==wanted;f.key(semantic.geos.native_text('R')[0]);source_proof();save_bound(f.merged())
   cases.append(dict(tag='reversed-selection-custom-settings-binding',selected_bytes=len(clip),settings=settings.hex(),bound=NAME.decode(),device=9));print('PASS',cases[-1],flush=True)
   settings=setup();position(8);at=f.get('se_hot_caret');f.key(q[0]);f.command(16);assert f.merged()==DATA and f.get('se_hot_pending',1)==0 and f.get('se_h_cursor',2)<f.get('se_h_end',2)
   # No new edit between actual Undo and snapshot: this is a redo-only journal.
   stable,saved,payload=capture();restore(stable,saved,payload);source_proof();f.command(17);assert f.merged()==DATA[:at]+q+DATA[at:];f.command(16);assert f.merged()==DATA;f.key(semantic.geos.native_text('R')[0]);source_proof();save_bound(f.merged())
   cases.append(dict(tag='redo-only-history-custom-settings-binding',settings=settings.hex(),bound=NAME.decode(),device=9));print('PASS',cases[-1],flush=True)
   settings=setup();position(8);f.key(q[0]);assert f.get('se_hot_pending',1)==1
   stable,saved,payload=capture();assert f.get('se_hot_pending',1)==1;restore(stable,saved,payload);source_proof()
   assert f.get('se_hot_pending',1)==1
   # Demonstrate that preserved genuine nondefault profiles are executable,
   # not merely byte-equal session state. This preview is still read-only.
   f.command(102);f.render();model=preview_render(f.merged(),settings,catalog=catalog,top=f.get('se_v_top'))
   assert f.read(0x6280,7040)==model.bitmap[640:7680] and f.read(0x4050,880)==model.attrs[80:960]
   f.key(13);f.render();source_proof()
   cases.append(dict(tag='pending-merged-source-and-custom-font-preview',pending=1,preview_pixels=320*176));print('PASS',cases[-1],flush=True)
   for ident,slot,name,stage in [(21,0,'geosrow','hardware'),(22,1,'geospaint','render')]:
    setup();stable,saved,payload=capture(lambda:remove(ident,slot));restore(stable,saved,payload)
    if stage=='render':
     # The success-only render helper waits for draw publication, which an
     # intentionally missing painter cannot produce. Drive one real root job
     # to its actual clean error termination instead of retrying it 16 times.
     r=f.call('se_editor_render');assert not r.p&1
     f.settle()
    assert f.get('se_e_error',1)==0x17,(stage,'missing overlay did not fail',f.debug())
    assert preserved()==stable and f.read(0xC600,1024)==f.shim
    assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_job','se_e_draw_busy'))
    reu_derived_only(saved);(out/(stage+'-refusal-ram.bin')).write_bytes(f.read(0,65536))
    image=next(image for image in f.assets.values()if image[5]==slot and image[6]==ident)
    f.import_image(image);f.put('se_e_error',0,1);source_proof();reu_derived_only(saved)
    cases.append(dict(tag='first-resumed-'+stage+'-missing-asset-recovery',asset=ident,slot=slot,error=0x17));print('PASS',cases[-1],flush=True)
  result=dict(status='passed',identity=identity,cases=cases,packaged_byteidentity=True,scope='Actual CPU editor C29/R26/exhausted real provider and public selection/history/File controls; only KERNAL ROM filesystem, validated settings init and fresh cold bootstrap are explicit seams. No native/host handoff claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:
  if f:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/lifecycle-extended'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.smoke)
