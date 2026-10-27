"""Bounded1MiB source-engine capacity on committed1612523, CPU modeled ROM.

Actual import/object/hot/history/selection/clipboard/public edit services; Plain
is selected through its real command before the initial paint. Far positions use
the documented hot-window load API, not a claim of global user navigation speed.
No1MiB D81/native/cold512KiB/Full performance claim. No capsule substitution/build.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,json,zipfile
import test_cache_rebase_registered as identity
import test_capacity_lifecycle as capacity
import test_geos_fold_editor as fold
import test_plain_geos as plain
geos=fold.geos;ROOT=identity.ROOT
BASE=ROOT/'build/warm-shift-committed/20261027T002602997186Z/fixture'
QUOTA=16*65536
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Fixture(fold.Fixture):
 def render(self):
  if self.get('se_render_caps',1)!=0:
   self.typed(geos.native_text('syntax plain'));assert self.get('se_render_caps',1)==0
  return super().render()
 def source(self,data,banks=16,physical=256):return geos.Fixture.source(self,data,banks,physical)


def source_view(out,base):
 out.mkdir(parents=True);p=out/'project';p.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():q=p/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(name))
 (p/'build').symlink_to(base/'build',target_is_directory=True);seal=identity.authenticate(base,p)
 (out/'authentication.json').write_text(json.dumps(seal,indent=2)+'\n');return seal


def run(out,base):
 out.mkdir(parents=True);seal=source_view(out/'source-view',base);ident=json.loads((base/'freeze.json').read_text());assert ident['git_commit']=='16125239094435223a0d6e355e8ee98204fbc330'
 import font_fixture
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=font_fixture.ROOT=base;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=ident['names']
 dll=capacity.runner(out);f=Fixture(out,base,dll,True);events=[];checks=[];intervals=[];frames=[];active_tag='initial'
 prefix=geos.native_text('Capacity source\r');tail=geos.native_text('\rEnd.')
 body=(geos.native_text('abcdefghijklmnopqrstuvwxyz0123456789')*((QUOTA//36)+1))[:QUOTA-16-len(prefix)-len(tail)]
 original=prefix+body+tail;assert len(original)==QUOTA-16;data=original
 foreign_bank=None;original_banks=[];held_original=[];settings=None;catalog=None
 def clean():
  assert not any(f.get(n,1)for n in ['se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_h_owned_lease','se_hot_owned','se_s_owned','se_n_owned','se_b_phase','se_h_phase','se_doc_busy','se_clip_busy']),f.debug()
  assert f.read(0xc600,1024)==f.shim
  # FS8EE0..8F35 is a dead phase alias atowner0, often live LINEINDEX.
  # Resident lockcounts/owned flags above prove leases, not stale FS bytes.
 def measured(tag,fn):
  nonlocal active_tag
  active_tag=tag;start=f.total_instructions;result=fn();events.append(dict(tag=tag,instructions=f.total_instructions-start,max_service=f.max_service));print('EVENT',events[-1],flush=True);return result
 def observer():return f.read(f.s['se_bc_arena'],17)+f.read(f.s['se_bc_ring'],96)
 def check(tag):
  start=f.total_instructions;assert f.merged()==data,(tag,'independent source',len(data),len(f.merged()))
  assert f.get('se_hot_caret')<=len(data)and f.get('se_h_cursor',2)<=f.get('se_h_end',2)
  assert f.get('se_h_dirty',1)==int(f.get('se_h_current',4)!=f.get('se_h_saved',4))
  assert f.catalog()==catalog and f.read(f.s['se_editor_settings'],64)==settings
  clean();s=observer();assert s[16]<=3
  for i in range(s[16]):
   at=17+((s[15]+i)%3)*32;r=s[at:at+32];assert r[0]==0xa5 and int.from_bytes(r[29:31],'little')==binascii.crc_hqx(r[1:29]+r[31:],65535)
  checks.append(dict(tag=tag,source_bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),caret=f.get('se_hot_caret'),pending=f.get('se_hot_pending',1),document_generation=f.get('se_doc_generation',2),history_current=f.get('se_h_current',4),history_end=f.get('se_h_end',2),observer17=s[:17].hex(),source_verification_instructions=f.total_instructions-start,pieces=sum(f.read(f.s['se_doc_roots']+i*8,8)[1]for i in range(f.get('se_doc_root_count',1)))))
  (out/'progress.json').write_text(json.dumps(dict(events=events,checks=checks),indent=2)+'\n')
 def interval(tag,fn):
  before=f.reu();assert len(before)==16777216;f.audit_begin();fn();writes=f.audit_end(before,tag);after=f.reu()
  for bank,held in zip(original_banks,held_original):assert after[bank*65536:(bank+1)*65536]==held,(tag,'immutable original bank',bank)
  if foreign_bank is not None:assert before[foreign_bank*65536:(foreign_bank+1)*65536]==after[foreign_bank*65536:(foreign_bank+1)*65536],(tag,'foreign bank')
  intervals.append(dict(tag=tag,actual_REU_bytes=len(before),checked_typed_stashes=writes,foreign_bank=foreign_bank,all_original16_banks_unchanged=True))
 def position(at):
  measured('hotAPI-position-'+str(at),lambda:f.position(at));assert f.get('se_hot_caret')==at
 def mutation_group(label,at):
  nonlocal data
  position(at);before=data;q=geos.native_text('Q')
  measured(label+'-INSERT',lambda:f.key(q[0]));data=before[:at]+q+before[at:];check(label+'-insert')
  measured(label+'-Undo',lambda:f.command(16));data=before;check(label+'-undo')
  measured(label+'-Redo',lambda:f.command(17));data=before[:at]+q+before[at:];check(label+'-redo')
  measured(label+'-Undo-return',lambda:f.command(16));data=before;check(label+'-return')
 def clip_bytes():
  token=f.read(f.s['se_clip_token'],5);n=f.get('se_clip_length');assert n<=1024;f.m.load(f.s['se_object_id'],token);f.put('se_object_offset',0);f.put('se_object_length',n,2);f.put('se_object_c64',0x8800,2);assert not f.call('se_object_copy',1).p&1;return f.read(0x8800,n)
 def refusal(tag,key=True):
  before=f.reu();canonical=f.canonical();state=observer();revision=f.get('se_r_revision',4)
  if key:measured(tag,lambda:f.key(geos.native_text('Q')[0],error=0x32))
  else:
   f.put('se_doc_edit_position',len(data));f.put('se_doc_edit_delete',0);f.put('se_doc_edit_insert',1);r=measured(tag,lambda:f.call('se_doc_splice_begin'));assert r.p&1 and r.a==0x32
  assert f.canonical()==canonical and f.reu()==before and observer()==state and f.get('se_r_revision',4)==revision,(tag,'non-atomic capacity refusal')
  assert f.merged()==data and not f.get('se_doc_busy',1)and not f.get('se_doc_read_locks',1)and not f.get('se_f_owner',1)
  f.put('se_e_error',0,1);check(tag+'-unchanged')
 def frame(tag):
  before=f.reu();canon=f.canonical();f.audit_begin();measured(tag,lambda:f.render());f.audit_end(before,tag);after=f.reu();wanted=bytearray(before);h=f.get('se_gc_handle',1);spans=[];mode=f.get('se_mode',1)
  if h:
   bank=f.m.read(f.s['se_reu_map']+h);assert bank and f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+bank)==0xfe
   spans=([(0,64),(0x600,0x680),(0xb200,0xd8b2),(0xe568,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)])if mode==3 else[(0,22*240)]
   for a,b in spans:wanted[bank*65536+a:bank*65536+b]=after[bank*65536+a:bank*65536+b]
  assert after==wanted and f.canonical()==canon,(tag,'readonly exactFE/source guard');check(tag+'-source')
  if mode==3:
   fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};bits,attrs,rows=plain.expected(f,data,fonts,0);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs;geos.png(bits,attrs,out/(tag+'.png'))
  else:
   (bits,attrs),_,_,_=geos.grid.expected(f,data);assert f.read(0x4000,len(bits))==bits and bytes(v&15 for v in f.read(0xd800,1000))==attrs
  frames.append(dict(tag=tag,mode=mode,source_bytes=len(data),TOP=f.get('se_v_top'),bottom=f.get('se_v_bottom'),bitmap_or_screen_sha256=hashlib.sha256(bits+attrs).hexdigest(),precise_FE_ranges=spans))
 try:
  measured('source-import-Plain-BOF',lambda:f.source(data,banks=16,physical=256));assert f.get('se_reu_banks',2)==256 and f.get('se_render_caps',1)==0 and f.get('se_doc_length')==len(data)
  for name in ['se_doc_original','se_doc_append']:
   token=f.read(f.s[name],5);f.m.load(f.s['se_object_id'],token);r=f.call('se_object_validate');assert not r.p&1 and f.m.read(f.s['object_banks']+r.x)==16
  token=f.read(f.s['se_doc_original'],5);oid=token[0]
  for i in range(16):
   logical=f.m.read(f.s['object_extents']+oid*16+i);bank=f.m.read(f.s['se_reu_map']+logical);assert f.m.read(f.s['se_reu_logical_owner']+logical)==f.m.read(f.s['se_reu_physical_owner']+bank)==4;original_banks.append(bank)
  image=f.reu();held_original=[image[b*65536:(b+1)*65536]for b in original_banks]
  r,_=f.fast_call(f.s['se_reu_alloc'],a=0xa5);assert not r.p&1;foreign_handle=r.a;foreign_bank=f.m.read(f.s['se_reu_map']+foreign_handle)
  pattern=bytes((i*73+29)&255 for i in range(256));f.m.load(0x8800,pattern)
  for offset in [0,0xff00]:
   for name,v,w in [('se_reu_logical',foreign_handle,1),('se_reu_offset',offset,2),('se_reu_c64',0x8800,2),('se_reu_length',256,2)]:f.put(name,v,w)
   assert not f.call('se_reu_copy',0).p&1
  settings=f.read(f.s['se_editor_settings'],64);catalog=f.catalog();check('imported-near1MiB');frame('BOF40-near1MiB')
  for label,at in [('BOF',0),('middle',len(data)//2),('EOF',len(data))]:interval(label,lambda l=label,p=at:mutation_group(l,p))
  def copying():
   nonlocal data
   position(0);f.command(68)
   for _ in range(5):f.command(2)
   measured('public-COPY5',lambda:f.command(69));assert clip_bytes()==data[:5];f.command(50);at=len(data)//2;position(at);before=data;clip=data[:5]
   measured('public-PASTE5',lambda:f.command(71));data=before[:at]+clip+before[at:];check('paste-middle')
   measured('paste-Undo',lambda:f.command(16));data=before;check('paste-undo');measured('paste-Redo',lambda:f.command(17));data=before[:at]+clip+before[at:];check('paste-redo');measured('paste-Undo-return',lambda:f.command(16));data=before;check('paste-return')
  interval('COPY-PASTE-UndoRedo',copying)
  def exact():
   nonlocal data
   position(len(data));before=data;raw=geos.native_text('Q'*16)
   for i,c in enumerate(raw):measured('exact-byte-'+str(i),lambda v=c:f.key(v))
   data=before+raw;assert len(data)==QUOTA;check('pending-exact1MiB')
   measured('exact-Undo',lambda:f.command(16));data=before;check('exact-undo');measured('exact-Redo',lambda:f.command(17));data=before+raw;check('committed-exact1MiB')
  interval('below-to-exact1MiB',exact)
  for label,at in [('BOF',0),('middle',QUOTA//2),('EOF',QUOTA)]:position(at);refusal('quota-key-'+label)
  refusal('quota-splice-BEGIN-above',False)
  def selected():
   nonlocal data
   at=QUOTA//2;position(at);f.command(68);f.command(2);before=data;r=geos.native_text('R');measured('selected-equal-at-quota',lambda:f.key(r[0]));data=before[:at]+r+before[at+1:];check('selected-equal')
   measured('selected-Undo',lambda:f.command(16));data=before;check('selected-undo');measured('selected-Redo',lambda:f.command(17));data=before[:at]+r+before[at+1:];check('selected-redo');measured('selected-Undo-return',lambda:f.command(16));data=before;check('selected-return')
  interval('selected-equal-1MiB',selected)
  position(0);f.command(50);frame('BOF40-exact1MiB');measured('mode-GEOS',lambda:f.command(99));frame('BOFGEOS-Plain-exact1MiB')
  result=dict(status='PASS',identity=seal,commit=ident['git_commit'],provider_banks=256,declared_quota_bytes=QUOTA,source_bytes=len(data),source_sha256=hashlib.sha256(data).hexdigest(),initial_source_bytes=len(original),longest_initial_logical_body=len(body),events=events,checks=checks,typed_intervals=intervals,frames=frames,source_original_physical_banks=original_banks,foreign_bank=foreign_bank,peak_single_call_instructions=f.peak,scope=__doc__,verifier_sha256=sha(__file__),remaining='No1MiB D81/native/Full performance/global far navigation proof; no512KiB fullfont support or exhaustive2048-piece/history exhaustion proof.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('CAPACITY_LIMITS_PASS',out,flush=True);return result
 except BaseException as exc:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(exc),active=active_tag,events=events,checks=checks,debug=f.debug(),caret=f.get('se_hot_caret'),job=f.get('se_e_job',1)),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:dll.fr_end();f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/capacity-limits-current'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out.resolve(),a.fixture.resolve())
