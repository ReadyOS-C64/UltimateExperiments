"""Persistent45B fold descriptor/key against immutable actual0659 editor.

Private capsule only: real view_init/object validation/hot edits/flush/replay.
Map publication in this test is a fixture marker, not a built/validated fold UI.
The28-byte key excludes caret/gap representation; query clients must require
valid separately. Revision/generation wrap requires explicit root invalidation.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from peddle import Machine,VENDOR
from test_bitmap_cells import labels
BASE=ROOT/'build/editor-fold-key/frozen'
SOURCES=['src/editor_fold/api.inc','src/editor_fold/state.s','src/editor_fold/key.s']

def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,capture_output=True)
def build(out):
 r=json.loads((BASE/'build/editor-report.json').read_text());assert r['sha256']=='06596474ad133423ff5555c33695fcc4f1352fe98c649251d6c6d1cf3b4e25f8';s=r['symbols']
 names=['se_view_init','se_v_length','se_doc_meta','se_doc_original','se_doc_append','se_doc_generation','se_r_revision','se_reu_epoch','se_doc_epoch','se_object_id','se_object_validate']
 (out/'aliases.s').write_text('\n'.join(f'.export {n}\n{n} = ${s[n]:04X}' for n in names)+'\n')
 (out/'key.cfg').write_text('MEMORY { C:file=%O,start=$5000,size=$1000; B:file="",start=$C57D,size=$83; } SEGMENTS { CODE:load=C,type=ro; BSS:load=B,type=bss,define=yes; }')
 for n,p in [('key','src/editor_fold/key.s'),('state','src/editor_fold/state.s'),('aliases',out/'aliases.s')]:run('ca65','-g','-I','src','-o',out/f'{n}.o',p)
 run('ld65','-C',out/'key.cfg','-o',out/'key.bin','-m',out/'key.map','-Ln',out/'key.lbl',*(out/f'{n}.o' for n in ['key','state','aliases']))
 cs=labels(out/'key.lbl');assert cs['se_ef_state']==0xC57D and cs['se_ef_state_end']==0xC5EF and cs['se_ef_valid']-cs['se_ef_state']==35
 fields=[n for n in cs if n.startswith('se_ef_') and n not in ['se_ef_key_capture','se_ef_key_match','se_ef_invalidate','se_ef_motion_tick']]
 (out/'editor-api.inc').write_text('\n'.join(f'{n} = ${v:04X}' for n,v in {**{n:s[n] for n in names},**{n:cs[n] for n in fields}}.items())+'\n')
 run('ca65','-g','-D','EDITOR_OVERLAY=1','-I',out,'-I','src','-o',out/'overlay.o','src/editor_fold/key.s')
 (out/'overlay.cfg').write_text('MEMORY { C:file=%O,start=$5000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; }')
 run('ld65','-C',out/'overlay.cfg','-o',out/'overlay.bin',out/'overlay.o');assert (out/'overlay.bin').read_bytes()==(out/'key.bin').read_bytes()
 return r,cs

def runner(out):
 cpp=out/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t fk_run(ZeroPagePeddle*m,uint64_t limit){auto b=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-b;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void fk_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void fk_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
 ext='.dylib' if sys.platform=='darwin' else '.so';p=out/('runner'+ext);run('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',p);lib=C.CDLL(str(p));lib.fk_run.argtypes=[C.c_void_p,C.c_uint64];lib.fk_run.restype=C.c_uint64;lib.fk_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];lib.fk_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return lib

class Fixture(editor_fixture.EditorFixture):
 def __init__(self,out,r,cs):
  self.out=out;self.cs=cs;self.lib=runner(out);self.calls=0;self.peak=0
  def fast(m,address,a=0,x=0,y=0,limit=2_000_000):
   for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',y)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
   m.write(0x1FE,0xFE);m.write(0x1FF,2);used=self.lib.fk_run(m.handle,limit);assert used,('nonreturn',hex(m.regs().pc));return m.regs(),used
  self.fast=fast;old=Machine.call;Machine.call=fast
  try:super().__init__()
  finally:Machine.call=old
  self.m.call=lambda address,a=0,x=0,y=0,limit=2_000_000:fast(self.m,address,a,x,y,limit)
 def read(self,a,n):
  b=C.create_string_buffer(n);self.lib.fk_read(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(16777216);self.lib.fk_reu(self.m.handle,len(b),b);return b.raw
 def efget(self,n,w=1):return int.from_bytes(self.read(self.cs[n],w),'little')
 def efput(self,n,v,w=1):self.m.load(self.cs[n],v if isinstance(v,(bytes,bytearray)) else v.to_bytes(w,'little'))
 def install(self):self.m.load(0x5000,(self.out/'key.bin').read_bytes())
 def key(self,*args,**kwargs):self.install();return super().key(*args,**kwargs)
 def marker(self):
  self.m.load(self.cs['se_ef_state'],bytes((i*37+11)&255 for i in range(114)))
  self.efput('se_ef_active',1);self.efput('se_ef_valid',1);self.efput('se_ef_fold_rows',0x3FFFFF,3)
 def expected_key(self):
  length=self.get('se_doc_length')-self.get('se_hot_old_length',2)+self.get('se_hot_length',2)
  return self.read(self.s['se_doc_meta'],15)+self.read(self.s['se_doc_generation'],2)+self.read(self.s['se_r_revision'],4)+length.to_bytes(3,'little')+self.read(self.s['se_reu_epoch'],2)+self.read(self.s['se_doc_epoch'],2)
 def ef(self,name,error=0):
  self.install();before=self.read(0,65536);state=before[self.cs['se_ef_state']:self.cs['se_ef_state_end']];r,n=self.m.call(self.cs[name]);self.calls+=1;self.peak=max(self.peak,n);after=self.read(0,65536);want=bytearray(before)
  allowed=[(0x100,0x200),(self.cs['se_ef_state'],self.cs['se_ef_state_end'])]
  if name in ['se_ef_key_capture','se_ef_key_match']:
   allowed += [(self.s[k],self.s[k]+w) for k,w in [('se_v_length',3),('se_v_hot_end',3),('se_v_span',3),('se_v_old_span',3),('se_v_cache_count',2),('se_object_id',5),('validate_index',3)]]
  for lo,hi in allowed:want[lo:hi]=after[lo:hi]
  assert after==want,(name,'RAM/source/shim/phase/foreignlease guard',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  now=after[self.cs['se_ef_state']:self.cs['se_ef_state_end']];permitted=bytearray(state)
  if name=='se_ef_key_capture' and not error:permitted[7:35]=self.expected_key()
  invalid=bool(error) or name in ['se_ef_invalidate','se_ef_key_capture'] or name=='se_ef_motion_tick' and int.from_bytes(state[36:40],'little')==0xFFFFFFFF
  if invalid:permitted[35]=0;permitted[111:114]=bytes(3)
  if name=='se_ef_motion_tick':permitted[36:40]=((int.from_bytes(state[36:40],'little')+1)&0xFFFFFFFF).to_bytes(4,'little')
  assert now==permitted,(name,'descriptor/token/count/active/paintends changed',state.hex(),now.hex(),permitted.hex())
  assert bool(r.p&1)==bool(error) and r.a==error,(name,error,r.a,r.p)
  if name in ['se_ef_key_capture','se_ef_key_match'] and not error:assert self.read(self.cs['se_ef_key'],28)==self.expected_key()
  return r
 def capture(self):self.ef('se_ef_key_capture');self.efput('se_ef_valid',1);self.efput('se_ef_fold_rows',0x3FFFFF,3)
 def flush(self):
  assert not self.call('se_hot_call',8).p&1
  for _ in range(10000):
   if not self.get('se_hot_phase',1):return
   assert not self.call('se_hot_call',2).p&1
  raise AssertionError('flush didnot finish')


def main():
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/editor-fold-key'/stamp;out.mkdir(parents=True);r,cs=build(out);freeze=json.loads((BASE/'freeze.json').read_text());cpu_editor.ROOT=editor_fixture.ROOT=BASE;cpu_editor.NAMES=editor_fixture.NAMES=freeze['names'];f=Fixture(out,r,cs);cases=[];mutants=motions=0
 data=b'# Heading\r'+b'A'*180+b'\r:::region Details\rcontent\r:::end\r';assert len(data)<2048
 try:
  f.source(data,banks=1);f.marker();f.capture();f.ef('se_ef_key_match');cases.append('realview-and3fulltokens/compact28Bkey')
  # Every persisted key byte is compared, not just token IDs or a16bit revision.
  key=f.read(cs['se_ef_key'],28);reu=f.reu()
  for i in range(28):
   q=bytearray(key);q[i]^=1;f.efput('se_ef_key',q);f.efput('se_ef_valid',1);f.ef('se_ef_key_match',0xB7);mutants+=1;f.efput('se_ef_key',key)
  assert f.reu()==reu;cases.append('every28keybyte-mismatch-failclosed')
  # Actual pending insertion: merged length differs from committed length.
  f.position(70);f.key(0xD8);assert f.get('se_hot_pending',1) and f.get('se_doc_length')==len(data);f.capture();pending_key=f.read(cs['se_ef_key'],28);assert pending_key[21:24]==(len(data)+1).to_bytes(3,'little')
  revision=f.get('se_r_revision',4);geometry=f.read(f.s['se_hot_left'],4);reu=f.reu()
  for keycode in [0x9D]*30+[0x1D]*50+[0x9D]*20:
   assert not f.call('se_hot_call',6 if keycode==0x9D else 7).p&1;f.ef('se_ef_key_match');assert f.get('se_r_revision',4)==revision and f.read(cs['se_ef_key'],28)==pending_key and f.efget('se_ef_valid')==1;motions+=1
  assert f.read(f.s['se_hot_left'],4)==geometry and f.reu()==reu;cases.append('100actual-hot-W_LEFT-W_RIGHT-pending-gap-motions-retain-key')
  f.key(0xD9);f.ef('se_ef_key_match',0xB7);f.capture();cases.append('actual-pending-content-edit-invalidates')
  old=f.read(cs['se_ef_key'],28);f.flush();assert f.document()==data[:70]+bytes([0xD8,0xD9])+data[70:];f.ef('se_ef_key_match',0xB7);assert f.read(cs['se_ef_key'],28)==old;cases.append('actual-committed-flush-invalidates')
  f.capture();f.command(16);f.ef('se_ef_key_match',0xB7);f.capture();f.command(17);f.ef('se_ef_key_match',0xB7);cases.append('actual-undo-and-redo-publication-invalidates')
  # Key helpers never inspect the1152Bunion, even when other clients own it.
  f.capture();assert not f.call('se_doc_read_acquire').p&1;assert not f.call('se_doc_read_acquire').p&1;leases=f.get('se_doc_read_locks',1);reu=f.reu()
  for owner in [0,1,2,3]:
   f.put('se_f_owner',owner,1);opaque=bytes((i*29+owner*47)&255 for i in range(1152));f.m.load(0x8D00,opaque);f.ef('se_ef_key_match');f.capture();assert f.read(0x8D00,1152)==opaque and f.get('se_doc_read_locks',1)==leases
  f.put('se_f_owner',0,1);assert f.reu()==reu;assert not f.call('se_doc_read_release').p&1;assert not f.call('se_doc_read_release').p&1;cases.append('phaseowners0-1-2-3-and2foreignleases-opaque')
  # Actual allocator-issued replacement token, with valid same-lifetime context.
  for field,type_ in [('se_doc_meta',3),('se_doc_original',4),('se_doc_append',4)]:
   f.capture();original=f.read(f.s[field],5);r_,_=f.m.call(f.s['se_object_create'],a=type_,x=1);assert not r_.p&1;token=f.read(f.s['se_object_id'],5);f.m.load(f.s[field],token)
   hot='se_hot_original' if field=='se_doc_original' else 'se_hot_append' if field=='se_doc_append' else None
   saved=f.read(f.s[hot],5) if hot else None
   if hot:f.m.load(f.s[hot],token)
   f.ef('se_ef_key_match',0xB7);f.m.load(f.s[field],original)
   if hot:f.m.load(f.s[hot],saved)
   f.m.load(f.s['se_object_id'],token);assert not f.call('se_object_release').p&1
  cases.append('actualallocated-canonical-token-replacements-invalidated')
  # A stale metadata generation must fail actual token validation, even when
  # the persisted key is forged to agree with the bad source frame.
  f.capture();meta=f.read(f.s['se_doc_meta'],5);bad=bytearray(meta);bad[1]^=1;f.m.load(f.s['se_doc_meta'],bad);fake=bytearray(f.read(cs['se_ef_key'],28));fake[:5]=bad;f.efput('se_ef_key',fake);f.ef('se_ef_key_match',0x31);f.m.load(f.s['se_doc_meta'],meta);cases.append('stale-metatoken-refused-even-ifkey-forged')
  # Re-adopt is the real canonical-open publication primitive; it changes doc
  # generation/context before another source client can use an old map.
  f.capture();assert not f.call('se_hot_call',10).p&1;f.put('se_doc_root_count',0,1);f.put('se_doc_length',0);f.put('se_doc_generation',1,2);f.put('se_doc_source_length',0);assert not f.call('se_doc_adopt_original').p&1;f.ef('se_ef_key_match',0x70);f.position(0);f.capture();cases.append('freshcandidate-frame/actual-adopt-open-publication-invalidates')
  # Explicit invalidation covers counter alias boundaries. MATCH is deliberately
  # allowed for a pending build, so VALID remains the query admission gate.
  for name,w in [('se_r_revision',4),('se_doc_generation',2)]:
   f.capture();before=f.read(f.s[name],w);f.m.load(f.s[name],bytes([255])*w);f.ef('se_ef_invalidate');f.m.load(f.s[name],before);assert f.efget('se_ef_valid')==0;cases.append(name+'-explicit-wrap-alias-invalidation')
  for serial in [0,0xFF,0xFFFF,0xFFFFFF,0xFFFFFFFF]:
   f.efput('se_ef_motion',serial,4);f.efput('se_ef_valid',1);f.efput('se_ef_fold_rows',0x3FFFFF,3);f.ef('se_ef_motion_tick');assert f.efget('se_ef_motion',4)==(serial+1)&0xFFFFFFFF;assert f.efget('se_ef_valid')==int(serial!=0xFFFFFFFF)
  cases.append('motionserial-carry-and32bitwrap-invalidates-onlyonwrap')
  # View/token/epoch failures preserve another service's leases and map token.
  f.capture();saved=f.get('se_doc_epoch',2);f.put('se_doc_epoch',saved^1,2);f.put('se_doc_read_locks',7,1);f.ef('se_ef_key_match',0x40);assert f.get('se_doc_read_locks',1)==7;f.put('se_doc_epoch',saved,2);f.put('se_doc_read_locks',0,1)
  f.capture();f.call('se_reu_provider_init');f.put('se_doc_read_locks',7,1);reu=f.reu();f.ef('se_ef_key_match',0x30);f.ef('se_ef_key_capture',0x30);assert f.get('se_doc_read_locks',1)==7 and f.reu()==reu;cases.append('provider-reset-anddocument-epoch-refuse-with7foreignleases')
  assert f.read(0xC600,1024)==f.shim
  result=dict(status='passed',resident_sha256=r['sha256'],code_bytes=len((out/'key.bin').read_bytes()),descriptor_bytes=45,key_bytes=28,projection_bytes=69,total_persistent_bytes=114,private_state_start=cs['se_ef_state'],private_state_end_exclusive=cs['se_ef_state_end'],remaining_before_shim=0xC600-cs['se_ef_state_end'],new_ZP=0,helper_CPU_calls=f.calls,peak_instructions=f.peak,every_keybyte_mutants=mutants,actual_pending_cursor_motions=motions,whole_REU_preservation_bytes=16777216,full_RAM_guards=65536,cases=cases,limits='Private capsule against actual frozen resident view/object/hot/history APIs. Fixture mapvalid is a marker; no builder/allocation/projection/UI/native or edited-fold-retention claim. KEY_MATCH is a source guard only; query clients separately require VALID1. Root must explicitly invalidate known revision/generation reset/wrap.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 evidence=ROOT/'agentsworking/evidence/M5'/(stamp+'-editor-fold-key');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build');shutil.copytree(BASE,evidence/'fixture')
 for name in SOURCES+['tests/test_editor_fold_key.py','tools/editor_fixture.py','tools/cpu_editor.py','tools/peddle.py']:
  target=evidence/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()
