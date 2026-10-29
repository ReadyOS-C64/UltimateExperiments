"""Private actual lexical page -> COWCR -> VALID-last alternate root transaction."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,zipfile,hashlib,binascii
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_lexical as lexical
geos=lexical.geos;F=lexical.F;IO=lexical.IO;command=lexical.command;labels=lexical.labels
from overlays import wrap
BASE=ROOT/'build/cache-editor-product/20261026T045019460982Z/fixture';D=ROOT/'src/cache/lexical-link-probe'

def build(out,base):
 out.mkdir(parents=True);report=json.load(open(base/'build/editor-report.json'));binding=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in ('core','page','open'):(out/(name+'.s')).write_bytes(z.read('src/cache/arena/'+name+'.s'))
 objs=[]
 for name,source in [('entry',D/'entry.s'),('core',out/'core.s'),('page',out/'page.s'),('open',out/'open.s')]:
  obj=out/(name+'.o');command(['ca65','-g','-D','BCA_READONLY_OPEN=1','-I',out,'-I',ROOT/'src','-o',obj,source]);objs.append(obj)
 command(['python3','tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs]);command(['ca65','-o',out/'aliases.o',out/'aliases.s'])
 (out/'link.cfg').write_text('MEMORY {C:file=%O,start=$B000,size=$1000;} SEGMENTS {CODE:load=C,type=ro;RODATA:load=C,type=ro;}')
 command(['ld65','-C',out/'link.cfg','-o',out/'link.bin','-Ln',out/'link.lbl','-m',out/'link.map',*objs,out/'aliases.o']);raw=(out/'link.bin').read_bytes()
 result=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());print('LINK_BUDGET',result,flush=True);return raw,labels(out/'link.lbl'),result

class Fixture(lexical.Fixture):
 def ll(self,op):
  self.put('se_overlay_frame',op,1);r,n=self.fast_call(self.s['se_overlay_call'],a=5,x=1);self.total_instructions+=n;assert self.read(0xc600,1024)==self.shim;return r,n

def run(out,base,build_only=False):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base);worker,linked,wb=lexical.build(out/'worker',frozen);page,pl,pb=lexical.build_page(out/'page',frozen);link,ll,lb=build(out/'link',frozen)
 if build_only:return
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True)
 binding=bytes.fromhex(json.load(open(frozen/'build/editor-report.json'))['resident_binding']['digest']);api=f.s['se_overlay_call'],f.s['se_overlay_frame']
 for name,raw,slot,id_ in [('lifectrl',worker,1,29),('lifecopy',page,0,26),('eplay',link,1,5)]:f.assets[name]=wrap(raw,slot,id_,api=api,binding_digest=binding)
 def drive(fn,op=1,limit=20000):
  for i in range(limit):
   r,n=fn(op)
   if r.p&1 or r.a!=1:return r,i+1
  raise AssertionError('boundedsteps')
 def produce(data):
  target=data.index(geos.native_text('10 PRINT'));f.source(data);f.command(99);f.render();assert f.get('se_bc_flags',1)&15==1
  for n in ('se_i_ready','se_i_count','se_n_cache_count'):f.put(n,0,1)
  f.put('se_f_owner',4,1);f.m.write(0x8b40+21,0);f.m.load(0x8b40,target.to_bytes(3,'little'));f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  while r.a==1 and not r.p&1:
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  assert not r.p&1 and r.a==0
  r,n=f.lx(0);assert not r.p&1 and r.a==1;r,n=f.lp(0);assert not r.p&1;r,_=drive(f.lp);assert not r.p&1 and r.a==0
  while True:
   r,n=f.lx(1);assert not r.p&1
   ready=f.m.read(F+4)
   if ready==1:
    r,n=f.lp(3);assert not r.p&1 and not r.a;f.lx(3)
   elif ready==2:
    f.lp(5);r,_=drive(f.lp);assert not r.p&1 and not r.a;f.lx(3);break
  token=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+token[0]*16);bank=f.m.read(f.s['se_reu_map']+logical);lo=bank*65536
  return target,lo
 def root_valid(raw):
  return raw[:6]==b'BCA1\1\1' and int.from_bytes(raw[119:121],'little')==binascii.crc_hqx(raw[:5]+raw[6:119]+raw[121:],65535)
 def exact_interval(before,after,lo,free=0,alternate=None):
  wanted=bytearray(before)
  if free:
   at=lo+free*4096;wanted[at:at+4096]=after[at:at+4096];at=lo+0x100+free*8;wanted[at:at+8]=after[at:at+8]
  if alternate is not None:wanted[lo+alternate:lo+alternate+128]=after[lo+alternate:lo+alternate+128]
  assert after==wanted,'whole16MiB outside actualCOWpage/directory8/alternateRoot128'
 try:
  data=geos.native_text('Intro\r:::basic\r10 PRINT "Hello":REM tail\r:::\rTail.');target,lo=produce(data)
  # ABI0 roots/NIL refs remain an explicit safe lexical miss.
  f.m.load(F+37,target.to_bytes(3,'little'));r,n=f.ll(3);assert not r.p&1 and r.a==1;r,_=drive(f.ll);assert not r.p&1 and r.a==2 and not f.get('se_doc_read_locks',1)
  target,lo=produce(data);before=f.reu();canonical=f.canonical();catalog=f.catalog();roots=[before[lo+i:lo+i+128]for i in (0,128)];selected=max((i for i in (0,128)if root_valid(before[lo+i:lo+i+128])),key=lambda i:int.from_bytes(before[lo+i+18:lo+i+22],'little'));oldroot=before[lo+selected:lo+selected+128];oldpage=oldroot[104];lexref=f.read(F+80,3);count=int.from_bytes(f.read(F+83,2),'little')
  r,n=f.ll(0);assert not r.p&1 and r.a==1,('linkbegin',r.a,r.p)
  r,steps=drive(f.ll);assert not r.p&1 and r.a==0,('linkstep',r.a,r.p,f.read(F,94).hex())
  after=f.reu();free=f.m.read(F+9);alternate=selected^128;exact_interval(before,after,lo,free,alternate)
  root=after[lo+alternate:lo+alternate+128];assert root_valid(root) and after[lo+selected:lo+selected+128]==oldroot
  assert root[31]==5 and root[98:100]==b'\1\0' and root[104]==root[108]==free and int.from_bytes(root[18:22],'little')==int.from_bytes(oldroot[18:22],'little')+1
  old=before[lo+oldpage*4096:lo+(oldpage+1)*4096];new=after[lo+free*4096:lo+(free+1)*4096];slots=old[23];matched=0
  for slot in range(slots):
   at=64+slot*96;wanted=bytearray(old[at:at+96]);record=new[at:at+96]
   if int.from_bytes(wanted[16:19],'little')==target:
    matched+=1;wanted[2]|=16;wanted[47:51]=bytes([lexref[0],0])+lexref[1:];wanted[51:54]=count.to_bytes(3,'little');wanted[74:76]=binascii.crc_hqx(wanted[1:74]+wanted[76:],65535).to_bytes(2,'little')
   assert record==wanted
  assert matched==1 and not f.get('se_doc_read_locks',1) and f.canonical()==canonical and f.catalog()==catalog
  print('LINKED',steps,'records',slots,'COWpage',free,flush=True)
  # Erase all page receipt fields before resolving. Only realroot/CR may
  # reconstruct them; no host-provided lexicalpage reference survives.
  f.m.load(F+80,bytes(7));f.m.load(F+37,target.to_bytes(3,'little'));readonly=f.reu();r,n=f.ll(3);assert not r.p&1 and r.a==1
  r,resolve_steps=drive(f.ll);assert not r.p&1 and not r.a,('resolve',r.a,r.p,f.read(F,94).hex());assert f.m.read(F+79)==3 and f.read(F+80,3)==lexref
  f.m.load(F+94,target.to_bytes(3,'little')+bytes([10]));r,n=f.lp(4);assert not r.p&1;r,window_steps=drive(f.lp);assert not r.p&1 and not r.a
  from supermark_model import lex
  roles=bytearray([4])*10;body=int.from_bytes(f.read(F+21,3),'little');end=int.from_bytes(f.read(F+24,3),'little')
  for a,b,role in lex(data[body:end],1,start=body):
   for x in range(max(a,target),min(b,target+10)):roles[x-target]=role
  assert f.read(0x8200,10)==roles and f.reu()==readonly
  f.ll(2);assert not f.get('se_doc_read_locks',1)
  # Rootcapability is partial: an untouched proseCR stillhasNIL and misses.
  f.m.load(F+37,bytes(3));r,n=f.ll(3);assert not r.p&1;r,_=drive(f.ll);assert not r.p&1 and r.a==2 and not f.get('se_doc_read_locks',1) and f.reu()==readonly
  # Original supportedABI0 query safely refuses the newpartiallex capability.
  f.m.load(0x8b40,target.to_bytes(3,'little'));f.m.write(0x8b40+21,0);f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  for _ in range(100):
   if r.p&1 or r.a!=1:break
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  assert r.p&1 and r.a==0xc2 and not f.get('se_doc_read_locks',1) and f.reu()==readonly
  faults=['ABI0/NILlexicalmiss','originalC35rejectsflags5/lexABI1','linkedroot-uncompleted-proseCR-NILmiss','returnedref-erased-before-realrootCRresolve']
  # Every precommitphase is cancellable without touching oldreachabledata.
  for phase in range(1,14):
   target,lo=produce(data);before=f.reu();canonical=f.canonical();r,n=f.ll(0);assert not r.p&1
   for _ in range(200):
    if f.m.read(F)==phase:break
    r,n=f.ll(1);assert not r.p&1 and r.a==1
   assert f.m.read(F)==phase
   free=f.m.read(F+9)if phase>=5 else 0;selected=f.m.read(F+13)if phase>=2 else 128;alternate=(selected^128)if phase==13 else None
   r,n=f.ll(2);assert not r.p&1 and not r.a;f.ll(2)
   exact_interval(before,f.reu(),lo,free,alternate);assert not f.get('se_doc_read_locks',1) and f.canonical()==canonical
   if phase==13:assert not f.m.read(F) and not f.reu()[lo+alternate+5]
  faults.append('all13precommitphases-idempotentcancel/oldselectedroot+referencedpages+sourceexact')
  target,lo=produce(data)
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);opaque=f.read(F,576);reu=f.reu()
   for op in range(4):
    r,n=f.ll(op);assert r.p&1 and r.a==0xb2 and f.read(F,576)==opaque and f.reu()==reu
  f.put('se_f_owner',4,1);faults.append('sixforeignowners/all4ops-opaque576+wholeREU')
  for caps in (0,1):
   f.put('se_render_caps',caps,1);opaque=f.read(F,576);reu=f.reu();r,n=f.ll(0);assert not r.p&1 and r.a==2 and f.read(F,576)==opaque and f.reu()==reu
  f.put('se_render_caps',3,1);faults.append('Plain+Markdown-bypass')
  for name in ('se_bc_ticket','se_bc_incarnation','se_doc_generation','se_r_revision'):
   target,lo=produce(data);r,n=f.ll(0);assert not r.p&1;at=f.s[name];old=f.m.read(at);f.m.write(at,old^1);reu=f.reu();r,n=f.ll(1);assert r.p&1 and f.reu()==reu;f.m.write(at,old);f.ll(2);assert not f.get('se_doc_read_locks',1)
  faults.append('ticket/incarnation/generation/revision-faults-before-newDMA')
  target,lo=produce(data);before=f.reu();token=f.read(f.s['se_bc_arena'],5);assert f.m.read(f.s['object_banks']+token[0])==1
  # Explicit pressurefixture: retire only currentlyallzero directoryentries
  # using checked typed writes. Nonzero INVALID entries cannot be reused.
  for page_ in range(1,16):
   at=lo+0x100+page_*8
   if before[at:at+8]!=bytes(8):continue
   f.m.load(f.s['se_object_id'],token);f.put('se_object_offset',0x100+page_*8);f.put('se_object_length',8,2);f.put('se_object_c64',IO,2);f.m.load(IO,bytes([0,0,0,0,0,0,0xa5,0]));assert not f.call('se_object_copy',a=0).p&1
  before=f.reu();canonical=f.canonical();r,n=f.ll(0);assert not r.p&1;r,_=drive(f.ll);assert not r.p&1 and r.a==3 and f.reu()==before and f.canonical()==canonical and not f.get('se_doc_read_locks',1)
  faults.append('no-allzero-directoryentry-STREAM/no-writes/no-oldroot-loss')
  target,lo=produce(data+geos.native_text('More.\r')*45);before=f.reu();canonical=f.canonical();r,n=f.ll(0);assert not r.p&1;r,_=drive(f.ll);assert r.p&1 and r.a==0xc0 and f.reu()==before;f.ll(2);assert not f.get('se_doc_read_locks',1) and f.canonical()==canonical
  faults.append('multiCRpage-topology-declines-before-any-write')
  result=dict(status='passed-narrow',worker=wb,page=pb,link=lb,source_bytes=len(data),linked_steps=steps,resolve_steps=resolve_steps,window_steps=window_steps,records=slots,faults=faults,scope='Private actualproducer LEXpage→oneCRpageCOW→alternateVALIDlastroot→rootCRresolver→actualR26consumer; not productionregistration.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result,flush=True)

 except BaseException:
  (out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());raise
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--build-only',action='store_true');a=p.parse_args();out=ROOT/'build/cache-lexical-link'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.build_only)
