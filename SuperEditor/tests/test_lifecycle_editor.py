"""Private actual-editor callable PREPARE/RESUME component, no shared build.

Same process, unchanged live provider/REU backing. Fresh trusted R26/prelude are
explicit host bootstrap seams; no old overlay/stack continuation is resumed.
CPU ROM glyph reads use the existing labeled fixture seam; no native IRQ claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,json,subprocess,sys,shutil,ctypes as C
from dataclasses import replace
import test_geos_fold_editor as fold
from overlays import HEADER,wrap
ROOT=fold.ROOT
BASE=ROOT/'build/geos-fold-editor/20261025T060733594632Z/fixture'
EXTENTS=((0x1000,0xB600,0),(0xCA00,0x600,0xB600),(2,24,0xBC00))
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise AssertionError(p.stdout+p.stderr)
def build(out,base):
 out.mkdir();shutil.copy2(ROOT/'cfg/lifecycle-controller.cfg',out/'canonical-controller.cfg');r=json.loads((base/'build/editor-report.json').read_text());binding=r['resident_binding']['digest']
 assert next(s for s in r['segments'] if s['name']=='ZEROPAGE')==dict(name='ZEROPAGE',start=2,end=25,size=24),'version1 snapshots requireexact24B ZP'
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 (out/'source/lifecycle').mkdir(parents=True)
 for name in ('adapter.s','adapter.inc','resume.s','resume.inc','copy-entry.s','copy-entry.inc','preflight.s','preflight.inc'):shutil.copy2(ROOT/'src/lifecycle'/name,out/'source/lifecycle'/name)
 obj={}
 for name in ('adapter','resume','copy-entry','preflight'):
  obj[name]=out/(name+'.o');command('ca65','-g','-I',out,'-I',out/'source','-I','src',*(['-D','LC_PREFLIGHT_IN_C29=1'] if name=='preflight' else []),'-o',obj[name],out/'source/lifecycle'/(name+'.s'))
 images={}
 for tag,slot,ident,names in [('lifecopy',0,26,['copy-entry']),('lifectrl',1,29,['adapter','preflight','resume'])]:
  oo=[obj[n] for n in names];command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(tag+'-aliases.s'),*oo)
  command('ca65','-o',out/(tag+'-aliases.o'),out/(tag+'-aliases.s'))
  cfg=out/(tag+'.cfg');cfg.write_text('MEMORY {O:file=%O,start=$'+('B000,size=$800,fill=yes;T:file=%O,start=$B800,size=$100,fill=yes;R:file="",start=$0A00,size=$100;' if slot else 'A000,size=$1000;')+'} SEGMENTS {CODE:load=O,type=ro;RODATA:load=O,type=ro;'+('RESUME:load=T,run=R,type=ro;' if slot else '')+'}')
  if slot:shutil.copy2(ROOT/'cfg/lifecycle-controller.cfg',cfg)
  command('ld65','-C',cfg,'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*oo,out/(tag+'-aliases.o'))
  raw=(out/(tag+'.bin')).read_bytes();
  if slot:
   assert len(raw)==2304
   (out/'resume.bin').write_bytes(raw[0x800:0x900])
  image=wrap(raw,slot,ident,api=(r['symbols']['se_overlay_call'],r['symbols']['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(out/(tag+'.seo')).write_bytes(image);images[tag]=image
 return images
class Fixture(fold.Fixture):
 def import_image(self,image):
  self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:]);assert not self.call('se_overlay_import').p&1
 def lc(self,op):
  return self.fast_call(0xAE0,a=op)

def run(out,base,mode=0,skip_faults=False,preview=False):
 frozen,identity=fold.geos.freeze(out,base);images=build(out/'leaf',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
 dll=fold.retention.runner(out);f=Fixture(out,frozen,dll,True);calls=[]
 try:
  data=fold.geos.native_text('# Main\rPending editor survives.\r:::region A\rhidden\r:::end\r# Tail\rEnd.')
  f.source(data);assert not f.call('se_clip_init').p&1;f.command(68)
  for _ in range(5):f.command(2)
  f.command(69);f.key(3);assert f.get('se_clip_length')==5
  f.command(115);f.position(12)
  f.command((96,97,98,99)[mode]);f.key(0xD1);f.render()
  if preview:f.command(102);f.render();assert f.get('se_e_ui',1)==4
  expected_source=data[:12]+bytes([0xD1])+data[12:]
  assert f.merged()==expected_source
  captured_fast_valid=f.m.read(0xCF90)
  if mode==3 and not preview and 'geoscaret' in identity['names']:assert captured_fast_valid==1,'test must capture an actually valid root fast path'
  f.m.write(0xCFE8,1) #explicit stale-derived-certificate fault seam
  assert f.get('se_hot_pending',1)==1
  semantic=lambda:{**{name:f.read(f.s[name],width) for name,width in [('se_ef_state',45),('se_editor_settings',64),('se_l_pan',3),('se_v_top',3),('se_l_preferred',3),('se_l_manual',1),('se_mode',1),('se_e_ui',1),('se_r_presentation',1),('se_h_saved',4),('se_h_current',4),('se_clip_token',5),('se_clip_length',3),('se_f_current_name',18)]},'preview_history':f.read(0xCE00,97)}
  packaged=all(name in identity['names'] for name in images)
  if packaged:
   for name,image in images.items():assert image==f.assets[name],('private/source output differs from packaged asset',name)
  else:
   for image in images.values():f.import_image(image)
  # Trusted freshly emitted descriptor/prelude. No old BOOT instruction is
  # required after these bytes overwrite cold initialization below1000.
  f.m.load(0x800,bytes.fromhex(json.loads((frozen/'build/editor-report.json').read_text())['resident_binding']['digest'])+bytes(0x40))
  f.m.load(0xA00,(out/'leaf/resume.bin').read_bytes())
  f.put('se_e_redraw',0,1);f.put('se_status',1,1)
  canonical=f.canonical();semantics=semantic();before=f.read(0,65536);reu=f.reu();r,n=f.lc(0);calls.append(n);assert not r.p&1 and r.a==1,(r.a,r.p)
  # Re-entry refuses without erasing the admitted work or touching REU.
  guard=f.reu();r,n=f.lc(0);calls.append(n);assert r.p&1 and r.a==0xDA and f.reu()==guard and f.m.read(0x820)==1
  # These are explicit between-slice event/source/admission injections; actual
  # IRQ/RESTORE electronics and scheduler handoff remain native follow-up.
  f.put('se_input_nmi_pending',1,1);guard=f.reu();r,n=f.lc(1);calls.append(n);assert r.p&1 and r.a==0xD5 and f.m.read(0x820)==0 and f.reu()==guard;f.put('se_input_nmi_pending',0,1)
  r,n=f.lc(0);calls.append(n);assert not r.p&1 and r.a==1
  revision=f.get('se_r_revision',4);f.put('se_r_revision',revision^1,4);guard=f.reu();r,n=f.lc(1);calls.append(n);assert r.p&1 and r.a==0xDF and f.m.read(0x820)==0 and f.reu()==guard;f.put('se_r_revision',revision,4)
  r,n=f.lc(0);calls.append(n);assert not r.p&1 and r.a==1
  candidate=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==26 and f.m.read(f.s['image_slot']+i)==0)
  f.m.write(f.s['se_overlay_ids']+candidate,0);guard=f.reu();r,n=f.lc(1);calls.append(n);assert r.p&1 and r.a==0x17 and f.m.read(0x820)==0 and f.reu()==guard;f.m.write(f.s['se_overlay_ids']+candidate,26)
  r,n=f.lc(0);calls.append(n);assert not r.p&1 and r.a==1
  guard=f.reu();r,n=f.lc(2);calls.append(n);assert not r.p&1 and r.a==0 and f.m.read(0x820)==0 and f.reu()==guard
  r,n=f.lc(0);calls.append(n);assert not r.p&1 and r.a==1
  handle=f.m.read(0x810);bank=f.m.read(0x811);assert f.m.read(f.s['se_reu_logical_owner']+handle)==f.m.read(f.s['se_reu_physical_owner']+bank)==0xFC
  prepare_counts=[]
  for count in range(500):
   r,n=f.lc(1);calls.append(n);prepare_counts.append(n);assert not r.p&1,(count,r.a,r.p)
   assert f.canonical()==canonical and f.read(0xC600,1024)==f.shim
   if r.a==0:break
   assert r.a==1
  else:raise AssertionError('unbounded prepare')
  captured=f.reu();at=bank*65536;payload=captured[at:at+0xBC18];header=captured[at+0xBC20:at+0xBC60]
  assert header[:8]==b'LCA1'+bytes([1,0xA5,3,0xFC])
  assert int.from_bytes(header[51:53],'little')==binascii.crc_hqx(payload,0xFFFF)
  assert int.from_bytes(header[62:64],'little')==binascii.crc_hqx(header[:62],0xFFFF)
  want=bytearray(reu);want[at:at+0xBC18]=payload;want[at+0xBC20:at+0xBC60]=header;assert captured==want,'capture changed foreign REU/padding'
  labels={x[2].lstrip('.'):int(x[1],16) for line in (out/'leaf/lifecopy.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}
  def inject(offset,raw):
   # Explicit corruption seam through the real general DMA API. No wholebank
   # host replacement or general DMA whitelist weakening is used.
   f.m.load(0x8000,raw);f.put('se_reu_c64',0x8000,2);f.put('se_reu_offset',offset,2);f.put('se_reu_length',len(raw),2);f.put('se_reu_logical',handle,1)
   assert not f.call('se_reu_copy',0).p&1
  def rawcall(name):
   prior=f.read(0,65536);r,n=f.fast_call(labels[name]);calls.append(n);after=f.read(0,65536);wanted=bytearray(prior)
   for lo,hi in [(0x100,0x200),(0x700,0x800),(0x820,0x82E),(0x880,0x8C0),(0xDF00,0xDF0B)]:wanted[lo:hi]=after[lo:hi]
   assert after==wanted,('validation wrote outside cold scratch',name,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
   return r
  f.m.load(0xA000,images['lifecopy'][HEADER:])
  for i in range(0 if skip_faults else 16):
   byte=f.m.read(0x800+i);f.m.write(0x800+i,byte^1);guard=f.reu();r=rawcall('se_lc_restore_begin');assert r.p&1 and r.a==0xDC and f.reu()==guard
   f.m.write(0x800+i,byte)
  for off in (() if skip_faults else (0x810,0x811,0x812,0x813)):
   byte=f.m.read(off);f.m.write(off,byte^0x80);guard=f.reu();r=rawcall('se_lc_restore_begin');assert r.p&1 and r.a==0xDB and f.reu()==guard
   f.m.write(off,byte)
  for i in range(0 if skip_faults else 64):
   inject(0xBC20+i,bytes([header[i]^1]));guard=f.reu();r=rawcall('se_lc_restore_begin');assert r.p&1 and r.a==0xDC and f.reu()==guard
   inject(0xBC20+i,header[i:i+1])
  for i in (() if skip_faults else (0,4,28,30,33,53,61)):
   mutant=bytearray(header);mutant[i]^=1;mutant[62:64]=binascii.crc_hqx(mutant[:62],0xFFFF).to_bytes(2,'little');inject(0xBC20,mutant)
   guard=f.reu();r=rawcall('se_lc_restore_begin');assert r.p&1 and r.a==0xDC and f.reu()==guard
  inject(0xBC20,header)
  for i in (() if skip_faults else (0,0xB5FF,0xB600,0xBBFF,0xBC00,0xBC17)):
   inject(i,bytes([payload[i]^1]));guard=f.reu();r=rawcall('se_lc_restore_begin');assert not r.p&1 and r.a==1
   for _ in range(189):
    r=rawcall('se_lc_copy_step')
    if r.p&1:break
    assert r.a==1
   assert r.p&1 and r.a==0xDD and f.reu()==guard,'payload corruption was not refused before warm writes'
   inject(i,payload[i:i+1])
  # Changes to any live provider entry, including a foreign allocation unrelated
  # to FC, must refuse after CRC but before the fresh restore thunk.
  for name,index in ([] if skip_faults else [('se_reu_map',250),('se_reu_logical_owner',250),('se_reu_physical_owner',250)]):
   original=f.m.read(f.s[name]+index);f.m.write(f.s[name]+index,original^1);guard=f.reu();r=rawcall('se_lc_restore_begin');assert not r.p&1
   for _ in range(192):
    r=rawcall('se_lc_copy_step')
    if r.p&1:break
   assert r.p&1 and r.a==0xDE and f.reu()==guard;f.m.write(f.s[name]+index,original)
  assert f.canonical()==canonical and semantic()==semantics
  captured=f.reu()
  if not skip_faults:print('LIFECYCLE FAULT PASS:64 header/7 recomputed semantic/6 payload/3 foreign provider faults; every validation STEP cold-only, all16MiB exact',flush=True)
  # Arbitrary warm bytes including both old executable slots are perturbed.
  # LIVE provider tables/epoch remain authoritative; they may not be replaced
  # by a saved image unless they compare exact before any restore write.
  preserve={n:f.read(f.s[n],w) for n,w in [('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256),('se_reu_epoch',2),('se_reu_retired',1)]}
  for cpu,length,off in EXTENTS:f.m.load(cpu,bytes((i*37+19)&255 for i in range(length)))
  for n,raw in preserve.items():f.m.load(f.s[n],raw)
  fresh=images['lifecopy'][HEADER:];f.m.load(0xA000,fresh)
  f.m.load(0xA00,(out/'leaf/resume.bin').read_bytes());before_restore=f.read(0,65536)
  r,n=f.fast_call(labels['se_lc_restore_begin']);calls.append(n);assert not r.p&1 and r.a==1,(r.a,r.p)
  for count in range(200):
   if f.m.read(0x820)==4 and f.m.read(0x827)==2:
    # The final step cannot return through the overwrittenRslot/stack. Stop
    # at the actual new prelude boundary, then execute it to actual se_idle.
    for k,v in [('pc',labels['se_lc_copy_step']),('sp',0xFD),('p',0x24)]:getattr(f.m.lib,'zeropage_peddle_set_'+k)(f.m.handle,v)
    used=dll.gm_idle(f.m.handle,0xA00,100000);assert used and f.m.regs().sp==255,'freshthunk transfer failed';calls.append(used)
    for cpu,length,off in EXTENTS:assert f.read(cpu,length)==payload[off:off+length],('exactrestore',hex(cpu))
    assert f.read(0xC600,1024)==f.shim and f.reu()==captured
    used=dll.gm_idle(f.m.handle,f.s['se_idle'],300000);assert used,('prelude stalled',hex(f.m.regs().pc));calls.append(used);break
   r,n=f.fast_call(labels['se_lc_copy_step']);calls.append(n);assert not r.p&1 and r.a==1,(count,r.a,r.p)
  else:raise AssertionError('unbounded restore')
  assert f.canonical()==canonical and f.get('se_hot_pending',1)==1 and semantic()==semantics and f.reu()==captured
  assert f.m.read(0xCF90)==f.m.read(0xCFE8)==0,'warm hardware reset retained a derived fast path'
  assert f.read(0xD011,1)==bytes([0x3B if mode else 0x1B]) and f.read(0xD018,1)==bytes([8 if mode else 2])
  f.render()
  if mode==3:
   assert f.merged()==expected_source
   fonts={n:(frozen/'fonts'/n).read_bytes() for n in fold.geos.GEOS_FONTS+('native8.bin',)}
   folds=[replace(t,flags=1) for t in fold.tree(data)]
   _,folds=fold.retention.retained(folds,data,12,0,bytes([0xD1]));folds,_=fold.action_model(folds,5,0,13,0,13)
   if preview:
    from geos_preview_model import FontCatalog
    if not (frozen/'genuine').exists():shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
    model=fold.preview(expected_source,f.read(f.s['se_editor_settings'],64),folds,catalog=FontCatalog(frozen/'genuine/catalog.json',native=fonts['native8.bin']),top=f.get('se_v_top'));bits,attrs=model.bitmap,model.attrs
   else:
    bits,attrs,_,_=fold.raster(expected_source,fonts,folds,top=f.get('se_v_top'),caret=13,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
   matrix,colors,popup=fold.geos.grid.logical_ui(f,expected_source);bits,attrs=fold.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
   (out/'resume-actual.bin').write_bytes(f.read(0x6000,8000)+f.read(0x4000,1000));(out/'resume-expected.bin').write_bytes(bits+attrs)
   fold.geos.png(f.read(0x6000,8000),f.read(0x4000,1000),out/'resume-actual.png')
   assert (f.read(0x6000,8000),f.read(0x4000,1000))==(bits,attrs),'independent resumed GEOS allpixels/attributes'
  if preview:f.key(13);f.render()
  f.key(0xD2);f.render();assert f.get('se_hot_pending',1)==1
  f.command(16);f.render();assert f.canonical()!=canonical and f.merged()==data,'undo must restore exact original source'
  assert f.read(0xC600,1024)==f.shim
  result=dict(status='passed',scope='standalone actual editor pending prepare/fresh-trusted-R26 restore/newprelude/real edit+undo; no native IRQ or ReadyOS claim',resident_sha256=identity['prg_sha256'],packaged_pair_byteidentical=packaged,mode=mode,preview=preview,resumed_pixels_checked=64000 if mode==3 else 0,captured_fast_valid=captured_fast_valid,controller_bytes=len(images['lifectrl'])-HEADER,copy_bytes=len(images['lifecopy'])-HEADER,prelude_bytes=len((out/'leaf/resume.bin').read_bytes()),prepare_steps=381,restore_steps=192,capture_abort_groups=4,header_corruptions=0 if skip_faults else 64,recomputed_header_faults=0 if skip_faults else 7,payload_faults=0 if skip_faults else 6,foreign_provider_faults=0 if skip_faults else 3,max_prepare_step_instructions=max(prepare_counts),max_call_instructions=max(calls),calls=len(calls))
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--out',type=Path);p.add_argument('--mode',type=int,choices=range(4),default=0);p.add_argument('--skip-faults',action='store_true');p.add_argument('--preview',action='store_true');a=p.parse_args();out=a.out or ROOT/'build/lifecycle-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);run(out,a.base,a.mode,a.skip_faults,a.preview)
