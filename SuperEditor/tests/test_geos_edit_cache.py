"""Private R28 transaction using actual C6 witness and real full-render rows.

Only the missing C21 row-transport leg is an explicit seam: a second actual
editor builds the candidate row, copied with checkedFE writes. No host-designed
maps/pixels. C21/C22 incremental glue is not claimed by this component proof.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
import test_geos_fold_editor as fold
from overlays import wrap,HEADER
ROOT=fold.ROOT;BASE=ROOT/'build/geos-semantic-editor/20261025T071324227584Z/fixture'
STATE=0x9149;GEC=0xCFE8


def cmd(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 assert not p.returncode,p.stdout+p.stderr


def build(out,frozen):
 out.mkdir();report=frozen/'build/editor-report.json';r=json.loads(report.read_text());s=r['symbols'];seal=r['resident_binding']['digest']
 minimal=out/'minimal';minimal.mkdir();full=out/'full';full.mkdir()
 (minimal/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 cmd(sys.executable,'tools/overlay_api.py','--report',report,'--output',full/'editor-api.inc','--all-public','--symbols','object_owner','object_banks','object_size_lo','object_size_mid','object_size_hi','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry','text_ptr','screen_ptr')
 images={};symbols={}
 for tag,slot,identity,names in [
  ('editcache',0,28,[('edit','src/render/geos/edit-cache.s',[]),('cache','src/render/geos/cache.s',['-D','SE_GP_CACHE_WARM_ONLY=1'])]),
  ('geoscaret',0,27,[('caret','src/render/geos/caret-cache.s',[]),('cache','src/render/geos/cache.s',['-D','SE_GP_CACHE_WARM_ONLY=1']),('ui','src/render/geos/caret-ui.s',[]),('chrome','src/tui/editor-chrome40.s',[]),('header','src/tui/header40.s',[])])]:
  objs=[]
  for name,source,flags in names:
   obj=out/(tag+'-'+name+'.o');cmd('ca65','-g',*flags,'-I',minimal,'-I','src','-o',obj,source);objs.append(obj)
  cmd(sys.executable,'tools/module_bindings.py','--report',report,'--output',out/(tag+'-aliases.s'),*objs);cmd('ca65','-o',out/(tag+'-aliases.o'),out/(tag+'-aliases.s'))
  cmd('ld65','-C','cfg/overlay-r.cfg','-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objs,out/(tag+'-aliases.o'))
  payload=(out/(tag+'.bin')).read_bytes();images[tag]=wrap(payload,slot,identity,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/(tag+'.seo')).write_bytes(images[tag]);symbols[tag]={x[2].lstrip('.'):int(x[1],16)for line in(out/(tag+'.lbl')).read_text().splitlines()if len(x:=line.split())==3 and x[0]=='al'}
 cmd('ca65','-g','-D','EDITOR_BINDINGS=1','-I',full,'-I','src','-o',out/'window.o','src/overlays/hot-window.s');cmd('ld65','-C','cfg/overlay-c.cfg','-o',out/'window.bin',out/'window.o')
 images['window']=wrap((out/'window.bin').read_bytes(),1,6,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal))
 return images,symbols


class Fixture(fold.Fixture):
 def import_extra(self,image):
  self.m.write(0xCBD5,0);self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:]);assert not self.call('se_overlay_import').p&1
 def transfer(self,offset,data=None,count=None):
  if data is not None and len(data)>128:
   for at in range(0,len(data),128):self.transfer(offset+at,data[at:at+128])
   return bytes(data)
  if data is None and count>128:return b''.join(self.transfer(offset+at,count=min(128,count-at))for at in range(0,count,128))
  if data is not None:self.m.load(0x9000,data);count=len(data)
  self.m.load(0x9178,offset.to_bytes(2,'little'));self.m.load(0x917A,(0x9000).to_bytes(2,'little'));self.m.load(0x917C,count.to_bytes(2,'little'))
  r,n=self.fast_call(self.edit_symbols['se_gp_cache_write'if data is not None else'se_gp_cache_read']);assert not r.p&1,(offset,r.a)
  return self.read(0x9000,count)
 def invoke(self,op):
  self.put('se_overlay_frame',op,1);before=self.read(0,65536);reu=self.reu();canonical=self.canonical();r,n=self.fast_call(self.s['se_overlay_call'],a=28,x=0)
  after=self.read(0,65536);want=bytearray(before)
  # WholeRAM permission is limited to ordinarycheckedreader/cache/overlay
  # bookkeeping, currentviewderivedreadfields, this47Bphase and192Bscratch.
  pairs=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2),('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_v_cache_base',3),('se_v_cache_end',3),('se_v_phys',3),('se_v_pos',3),('se_object_id',12),('validate_index',1),('validate_extent',1),('validate_type',1),('doc_cache_slot',1),('screen_ptr',2),('text_ptr',2)]
  ranges=[(self.s[k],self.s[k]+w)for k,w in pairs]+[(0x100,0x200),(0x8000,0x8400),(0x8400,0x8800),(0x9000,0x90C0),(STATE,0x917E),(GEC,GEC+1),(0xCF90,0xCF91),(0xCBD5,0xCBD6),(0x5000,0x6000),(0xA000,0xB000),(self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_overlay_header'],self.s['se_overlay_header']+36),(0xDF00,0xDF0B)]
  for a,b in ranges:want[a:b]=after[a:b]
  assert after==want,('wholeRAM',op,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
  assert self.canonical()==canonical and self.read(0xC600,1024)==self.shim
  handle=self.get('se_gc_handle',1);bank=self.m.read(self.s['se_reu_map']+handle);actual=self.reu();base=bank*65536;want=bytearray(reu)
  for a,b in [(0,64),(0xD528,0xE568)]+[(0x200+i*2048,0x200+(i+1)*2048)for i in range(22)]:want[base+a:base+b]=actual[base+a:base+b]
  assert actual==want,('whole16MiB',op,next(hex(i)for i,(a,b)in enumerate(zip(actual,want))if a!=b))
  return r,n


def run(out,previous,smoke=False):
 inputs=['src/render/geos/edit-cache.s','src/render/geos/edit-cache.inc','src/render/geos/edit-certificate.inc','src/render/geos/edit-certificate-body.inc','src/render/geos/cache.s','src/render/geos/caret-cache.s','tests/test_geos_edit_cache.py']
 source_hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in inputs}
 with zipfile.ZipFile(out/'candidate-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
  for n in inputs:archive.write(ROOT/n,n)
 frozen,identity=fold.geos.freeze(out,previous);images,syms=build(out/'leaf',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
 dll=fold.retention.runner(out);f=Fixture(out,frozen,dll,True);g=Fixture(out,frozen,dll,True);f.edit_symbols=syms['editcache'];g.edit_symbols=syms['editcache'];cases=[]
 for x in(f,g):x.assets.update({k:v for k,v in images.items()if k!='editcache'})
 def setup(x,data,at,top=None):
  x.source(data);x.command(99)
  if top is not None:
   x.position(at);x.put('se_v_top',top) #actual W_LOAD; explicit far-viewport setup
  else:
   for _ in range(at):assert not x.call('se_hot_call',7).p&1
  x.render()
 def case(data,at,delete=False,tag='insert',top=None):
  setup(f,data,at,top);setup(g,data,at,top);f.import_extra(images['editcache']);q=fold.geos.native_text('Q')[0]
  for x in(f,g):x.key(0x14 if delete else q)
  assert f.m.read(GEC)==1
  f.put('se_f_owner',4,1);old,bank=f.raw_cache();pixels=f.read(0x6000,8000)+f.read(0x4000,1000)
  r,n=f.invoke(0);assert not r.p&1 and r.a==1,(tag,'ADMIT',r.a,r.p,f.read(STATE,47).hex());row=f.m.read(STATE+1)
  assert f.read(0x6000,8000)+f.read(0x4000,1000)==pixels
  print('FIRST EDITCACHE ADMIT PASS',tag,row,n,flush=True)
  # Actualsecondeditor fullproducer owns sourceparse/mapgeneration. Theonly
  # seam transportsitsrowpacket/headercaretfields, not source orhostmodels.
  g.render();new,newbank=g.raw_cache();packet=new[0x200+row*2048:0x200+(row+1)*2048]
  f.transfer(0x200+row*2048,packet)
  assert not f.fast_call(syms['editcache']['se_gp_cache_guard'])[0].p&1
  hdr=bytearray(f.read(0x8500,64));hdr[41:46]=new[41:46];f.transfer(0,hdr)
  r,v=f.invoke(1);assert not r.p&1 and r.a==1,(tag,'VERIFY',r.a,r.p,f.read(STATE,47).hex())
  ticks=0;used=n+v
  while True:
   r,n=f.invoke(2);ticks+=1;used+=n;assert not r.p&1,(tag,'REBASE',r.a,r.p,ticks)
   if r.a==0:break
   assert r.a==1 and ticks<200,(tag,r.a,ticks)
  actual,_=f.raw_cache();assert actual[:64]==new[:64],(tag,'header',actual[:64].hex(),new[:64].hex())
  for i in range(new[1]):
   a=0x200+i*2048;assert actual[a:a+1814]==new[a:a+1814],(tag,'rowpacket',i,next((j,a,b)for j,(a,b)in enumerate(zip(actual[a:a+1814],new[a:a+1814]))if a!=b))
  f.put('se_f_owner',0,1);f.render();assert(f.read(0x6000,8000),f.read(0x4000,1000))==(g.read(0x6000,8000),g.read(0x4000,1000)),(tag,'actualC22consumerpixels')
  cases.append(dict(tag=tag,row=row,rebase_steps=ticks,instructions=used,source_bytes=len(f.merged())))
 def prepare(tag):
  data=fold.geos.native_text('Ordinary text here.\rSecond source line.\rThird line.\r')
  setup(f,data,5);f.import_extra(images['editcache']);f.key(fold.geos.native_text('Q')[0]);assert f.m.read(GEC)==1
  f.put('se_f_owner',4,1)
 def admit(tag):
  prepare(tag);r,n=f.invoke(0);assert not r.p&1 and r.a==1,(tag,'admit',r.a,r.p)
 def invalid(tag):
  cache,_=f.raw_cache();assert cache[0]==0,(tag,'page should remain invalid')
 def faults():
  # Every operation rejects foreign phase ownership before touching phase or FE.
  prepare('foreign')
  for owner in(0,1,2,3,5,255):
   f.put('se_f_owner',owner,1)
   for op in range(4):
    phase=f.read(STATE,47);reu=f.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000)
    r,n=f.invoke(op);assert r.p&1 and r.a==0xB2,('foreign',owner,op,r.a,r.p)
    assert f.read(STATE,47)==phase and f.reu()==reu and pixels==f.read(0x6000,8000)+f.read(0x4000,1000)
  f.put('se_f_owner',4,1);cases.append(dict(tag='foreign-owner-opaque',calls=24))
  # Exact witness failures cannot publish a new key or page. Mutate a single
  # certificate field after a real producer, never invent a positive witness.
  for name,offset in [('revision',7),('old-length',11),('sequence',14),('doc-epoch',16),('provider-epoch',18)]:
   prepare(name);f.m.write(GEC+offset,f.m.read(GEC+offset)^1);reu=f.reu()
   r,n=f.invoke(0);assert not r.p&1 and r.a==2,(name,r.a,r.p)
   assert f.reu()==reu and f.m.read(STATE)==0 and f.m.read(GEC)==0
   cases.append(dict(tag='stale-'+name))
  # User cancellation after ADMIT is a derived-cache discard, not source undo.
  admit('cancel');r,n=f.invoke(3);assert not r.p&1 and r.a==0;invalid('cancel');assert f.m.read(STATE)==0
  cases.append(dict(tag='cancel-admitted'))
  # A source revision change during any bounded phase is a strict source fault.
  admit('sourcechange');f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
  r,n=f.invoke(1);assert r.p&1 and r.a==0x74,('sourcechange',r.a,r.p);invalid('sourcechange')
  cases.append(dict(tag='source-change-after-admit'))
  # VERIFY sees the actual old row here, whose next/end fail the required delta.
  admit('unrebuilt');r,n=f.invoke(1);assert not r.p&1 and r.a==2,('unrebuilt',r.a,r.p);invalid('unrebuilt')
  cases.append(dict(tag='verify-unrebuilt-row'))
  # Wrong geometry and active styling on a full-rendered candidate are rejected.
  for name,offset,value in [('reason',17,3),('height',14,8),('style',194,1),('role',356,1)]:
   admit(name);setup(g,fold.geos.native_text('Ordinary text here.\rSecond source line.\rThird line.\r'),5);g.key(fold.geos.native_text('Q')[0]);g.render();cache,_=g.raw_cache();row=f.m.read(STATE+1)
   packet=bytearray(cache[0x200+row*2048:0x200+(row+1)*2048]);packet[offset]=value;f.transfer(0x200+row*2048,packet)
   r,n=f.invoke(1);assert not r.p&1 and r.a==2,(name,r.a,r.p);invalid(name)
   cases.append(dict(tag='verify-bad-'+name))
 try:
  case(fold.geos.native_text('Ordinary text here.\rSecond source line.\rThird line.\r'),5)
  if not smoke:
   case(fold.geos.native_text('Ordinary text here.\rSecond source line.\rThird line.\r'),5,True,'backspace')
   case(fold.geos.native_text('First source.\rOrdinary second line.\rThird source.'),20,False,'secondrow-insert')
   faults()
   for start in(0x100,0x10000):
    data=b'x'*(start-1)+b'\r'+fold.geos.native_text('Ordinary text here.\rSecond source line.\rThird line.\r')
    case(data,start+5,False,'row0-at-'+hex(start),top=start)
  result=dict(status='passed',identity=identity,payload_bytes=len(images['editcache'])-HEADER,cases=cases,source_sha256=source_hashes,seam='Newrowprovidedbyasecondactualfullrenderer+checkedFEtransport; no C21incrementalglue/dirtypaintclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,len(cases));return result
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-edit-cache'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.smoke)
