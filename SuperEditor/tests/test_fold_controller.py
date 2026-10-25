"""Actual resident dispatch+C19/C17/C18/R18 fold coordinator CPU gate.

Only private frozen build/evidence. No product build or VICE. Fixtures initialize
source through actual objects; C19 allocates/binds/builds/actions/cleans up itself.
Root F7 regressions additionally exercise real source40 recovery publication;
modal tests stop before directory I/O, which requires the separate native lane.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,ctypes as C,hashlib,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from peddle import Machine
from bindings import verify
from test_fold_leaves import runner
from supermark_probe import petscii
from redraw_model import native_text,source40
spec=importlib.util.spec_from_file_location('controller_oracle',ROOT/'tests/test_fold_builder.py');model=importlib.util.module_from_spec(spec);sys.modules[spec.name]=model;spec.loader.exec_module(model)

def freeze(out):
 base=out/'fixture';(base/'build/overlays').mkdir(parents=True);r=json.loads((ROOT/'build/editor-report.json').read_text());seal=verify(ROOT/'build/editor.prg',ROOT/'build/editor.lbl');assert seal['resident_sha256']==r['sha256'];names=list(cpu_editor.NAMES);assert all(n in names for n in ['foldparse','foldfinish','foldcore','foldctl','rangeio'])
 for n in ['editor.prg','editor-report.json','editor.lbl','editor.map','editor-bindings.json']:shutil.copy2(ROOT/'build'/n,base/'build'/n)
 for n in names:
  p=ROOT/'build/overlays'/(n+'.seo');raw=p.read_bytes();assert raw[20:36]==raw[36:52]==bytes.fromhex(seal['digest']);shutil.copy2(p,base/'build/overlays'/p.name)
 (base/'freeze.json').write_text(json.dumps(dict(names=names,prg_sha256=r['sha256'],binding=seal['digest'],assets={n:hashlib.sha256((base/'build/overlays'/(n+'.seo')).read_bytes()).hexdigest() for n in names}),indent=2)+'\n');return base,r,names

class Fixture(editor_fixture.EditorFixture):
 def __init__(self,out):
  self.runner=runner(out);self.calls=0;self.peak=0;self.phases=set();self.leafcalls=0
  def fast(m,address,a=0,x=0,y=0,limit=3_000_000):
   for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',y)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
   m.write(0x1FE,0xFE);m.write(0x1FF,2);used=self.runner.fl_run(m.handle,limit);assert used,('nonreturn',hex(m.regs().pc));self.peak=max(self.peak,used);return m.regs(),used
  old=Machine.call;Machine.call=fast
  try:super().__init__()
  finally:Machine.call=old
  self.m.call=lambda address,a=0,x=0,y=0,limit=3_000_000:fast(self.m,address,a,x,y,limit)
 def read(self,a,n):
  b=C.create_string_buffer(n);self.runner.fl_ram(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(16777216);self.runner.fl_reu(self.m.handle,len(b),b);return b.raw
 def render(self):
  error=self.get('se_e_error',1)
  for _ in range(16):
   reg=self.call('se_editor_render');assert not reg.p&1,('render',hex(reg.a))
   if not self.get('se_e_job',1):return reg
   assert self.get('se_e_job',1) in (7,10)
   self.settle(error)
  raise AssertionError('render did not converge')
 def canonical(self):
  return self.read(self.s['se_doc_roots'],512)+b''.join(self.read(self.s[n],w) for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_hot_ready',1),('se_hot_pending',1),('se_hot_base',3),('se_hot_caret',3),('se_hot_left',2),('se_hot_right',2),('se_h_token',5),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_sel_mark',13)])+self.read(0x9200,2048)+self.read(0xC600,1024)
 def dispatch(self,op=1,action=0):
  if op==0:self.m.write(self.s['se_overlay_frame']+1,action)
  r=self.call('se_ef_dispatch',op);self.calls+=1
  if self.get('se_f_owner',1)==3:self.phases.add(self.get('se_ec_phase',1))
  return r
 def finish(self,r):
  for _ in range(25000):
   if r.p&1 or r.a==0:return r
   assert r.a==1,(r.a,r.p);r=self.dispatch()
  raise AssertionError('unbounded fold controller')
 def action(self,action=0,error=0):
  before=self.canonical();r=self.finish(self.dispatch(0,action));assert bool(r.p&1)==bool(error) and r.a==error,(action,error,r.a,self.get('se_ec_error',1));assert self.canonical()==before;assert self.get('se_f_owner',1)==self.get('se_ef_active',1)==self.get('se_fs_owned',1)==0
  return r
 def bank(self,token=None):
  token=token or self.read(self.s['se_ef_token'],5);logical=self.m.read(self.s['object_extents']+token[0]*16);return self.m.read(self.s['se_reu_map']+logical)
 def records(self):
  reu=self.reu();at=self.bank()*65536;return [reu[at+i*32:at+(i+1)*32] for i in range(self.get('se_ef_count',2))]
 def suppress(self,name):
  raw=self.assets[name];slot,id_=raw[5],raw[6];which=next(i for i in range(self.s['se_overlay_capacity']) if self.m.read(self.s['se_overlay_ids']+i)==id_ and self.m.read(self.s['image_slot']+i)==slot);self.m.write(self.s['se_overlay_ids']+which,0);return which,id_
 def restore(self,token):self.m.write(self.s['se_overlay_ids']+token[0],token[1])

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path);a=p.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/fold-controller'/stamp;out.mkdir(parents=True)
 if a.base:base=a.base;r=json.loads((base/'build/editor-report.json').read_text());names=json.loads((base/'freeze.json').read_text())['names']
 else:base,r,names=freeze(out)
 cpu_editor.ROOT=editor_fixture.ROOT=base;cpu_editor.NAMES=editor_fixture.NAMES=names;f=Fixture(out);cases=[];data=petscii('# Main\nintro\n## Inner\ninside body\n:::region Details\nregion body\n:::basic\n10 PRINT "TEST"\n:::\n:::end\n# Tail\nend\n');caret=data.index(petscii('body'))+2
 try:
  f.source(data,banks=1);f.position(caret);before=f.canonical();reu=f.reu();f.action();tree,_,_,err=model.oracle(data);assert not err and f.get('se_ef_count',2)==len(tree);records=f.records();target=max((i for i,x in enumerate(tree) if x.start<=caret<x.end),key=lambda i:tree[i].start);assert records[target][13]==3 and int.from_bytes(records[target][14:17],'little')==caret and f.get('se_e_target')==tree[target].start
  bank=f.bank();after=f.reu();assert all(after[i*65536:(i+1)*65536]==reu[i*65536:(i+1)*65536] for i in range(256) if i!=bank);assert f.get('se_ef_valid',1)==1 and f.get('se_l_valid',1)==f.get('se_r_valid',1)==f.get('se_st_valid',1)==f.get('se_st_request',1)==f.get('se_st_cp_valid',1)==0 and f.get('se_l_need_wrap',1)==1;cases.append('actualC19allocate-builder-innermosttoggle/sourceandforeignREU/derivedinvalidations')
  token=f.read(f.s['se_ef_token'],5);f.position(f.get('se_e_target'));f.action();assert f.read(f.s['se_ef_token'],5)==token and f.get('se_e_target')==caret and not(f.records()[target][13]&1);cases.append('publishedmapreuse/controlledreload/keymatch/innermostexpandrestorescaret')
  f.position(caret);f.action(3);assert all(x[13]&1 for x in f.records());f.position(f.get('se_e_target'));f.action(4);assert all(not x[13]&1 for x in f.records());cases.append('collapseall-andexpandall')
  # Published map cannot be freed even if a corrupted candidateflag names it.
  f.put('se_f_owner',3,1);f.m.load(f.s['se_ec_candidate'],token);f.put('se_ec_allocated',1,1);f.put('se_fs_owned',0,1);regs=f.call('se_ef_emergency',0x17);assert regs.p&1 and regs.a==0x17 and f.m.read(f.s['object_owner']+token[0])==0x46 and not f.get('se_f_owner',1);f.call('se_ef_emergency',0x17);cases.append('emergency-idempotent-neverfreespublishedmap')
  # Missing each image is a catalog admission fault, not modeled service I/O.
  for missing in ['foldctl','foldparse','foldfinish','foldcore','viewsource']:
   f.source(data,banks=1);assert not f.call('se_doc_read_acquire').p&1;foreign=1;before=f.canonical();guard=f.reu()
   if missing in ['foldctl','foldparse','foldcore','viewsource']:
    suppressed=f.suppress(missing);reg=f.finish(f.dispatch(0,3))
   else:
    reg=f.dispatch(0,3)
    for _ in range(10000):
     if f.get('se_fb_phase',1)>=4:break
     reg=f.dispatch();assert not reg.p&1
    suppressed=f.suppress(missing);reg=f.finish(f.dispatch())
   assert reg.p&1 and reg.a==0x17,(missing,reg.a);assert f.get('se_f_owner',1)==f.get('se_ef_valid',1)==f.get('se_ef_active',1)==f.get('se_ec_allocated',1)==0 and f.get('se_doc_read_locks',1)==foreign;assert f.canonical()==before and not any(f.m.read(f.s['object_owner']+i)==0x46 for i in range(8));after=f.reu();candidate=f.read(f.s['se_ec_candidate'],5);allowed=f.bank(candidate) if missing!='foldctl' else None;assert all(after[i*65536:(i+1)*65536]==guard[i*65536:(i+1)*65536] for i in range(256) if i!=allowed),(missing,'foreignREUchanged');f.restore(suppressed);f.call('se_doc_read_release');cases.append('missing-'+missing+'-actualadmission/foreignlease/candidatecleanup')
  # MissingC19 after BEGIN owns a real builderlease and fresh candidate.
  f.source(data,banks=1);f.call('se_doc_read_acquire');before=f.canonical();reg=f.dispatch(0,3);assert reg.a==1 and f.get('se_fs_owned',1)==1 and f.get('se_doc_read_locks',1)==2;which=f.suppress('foldctl');reg=f.dispatch();assert reg.p&1 and reg.a==0x17 and f.get('se_doc_read_locks',1)==1 and f.get('se_f_owner',1)==0 and not any(f.m.read(f.s['object_owner']+i)==0x46 for i in range(8)) and f.canonical()==before;f.restore(which);f.call('se_doc_read_release');cases.append('missingC19-inflight-residentlease-andcandidatecleanup')
  f.source(data,banks=1);f.call('se_doc_read_acquire');before=f.canonical();f.dispatch(0,3);reg=f.dispatch(2);assert not reg.p&1 and reg.a==0 and f.get('se_doc_read_locks',1)==1 and f.get('se_f_owner',1)==f.get('se_ef_valid',1)==0 and f.canonical()==before;f.dispatch(2);f.call('se_doc_read_release');cases.append('actualSTOPcancel-builder/candidatefree/foreignlease')
  # Actual object-table exhaustion: unrelated allocations remain owned.
  f.source(data,banks=1);allocated=[]
  while True:
   reg,_=f.m.call(f.s['se_object_create'],a=99,x=1)
   if reg.p&1:break
   allocated.append(f.read(f.s['se_object_id'],5))
  before=f.canonical();f.action(3,error=0x35);assert f.canonical()==before
  for t in allocated:assert f.m.read(f.s['object_owner']+t[0])==99
  cases.append('actualobjecttable-exhaustion-expandedfallback/sourcepreserved')
  # Other union owners are opaque on BEGIN/STEP/CANCEL, including doublecleanup.
  f.source(data,banks=1)
  for owner in [1,2,255]:
   f.put('se_f_owner',owner,1);opaque=bytes((i*37+owner)&255 for i in range(1152));f.m.load(0x8D00,opaque);descriptor=f.read(f.s['se_ef_state'],114)
   for op in [0,1,2]:reg=f.dispatch(op,3);assert reg.p&1 and reg.a==0xB2 and f.read(0x8D00,1152)==opaque and f.read(f.s['se_ef_state'],114)==descriptor and f.get('se_f_owner',1)==owner
  f.put('se_f_owner',0,1);cases.append('foreignphase1-2-255-noinspection-orcleanup')
  # Exact user-visible regression: warm canonical index, fold claim/projection,
  # selected hidden source copy/cut, then actual journal undo. No fake source or
  # index flags: F7commands and actual source navigation do every transition.
  clipdata=native_text('# First\rOne hidden line.\rAnother hidden line.\r# Second\rVisible last line.\r')
  f.source(clipdata,banks=1);f.put('se_status',1,1);f.position(12);f.render()
  f.typed(native_text('fold'));f.render();assert f.get('se_hot_caret')==0
  f.typed(native_text('fold'));f.render();assert f.get('se_hot_caret')==12
  f.typed(native_text('fold'));f.render();assert f.get('se_hot_caret')==0
  f.command(68);f.typed(native_text('goto 4'));f.render();assert f.get('se_hot_caret')==46 and f.get('se_ef_fold_rows',1)&1
  # Also close the unrelated second section. CUT must drop the deleted first
  # heading while retaining the shifted second heading; Undo creates a fresh
  # expanded first heading and keeps that unaffected second section closed.
  f.typed(native_text('fold'));f.render();assert all(x[13]&1 for x in f.records())
  f.typed(native_text('copy'));f.render();assert f.get('se_clip_length')==46 and f.document()==clipdata
  cliptoken=f.read(f.s['se_clip_token'],5);handle=f.m.read(f.s['object_extents']+cliptoken[0]*16);physical=f.m.read(f.s['se_reu_map']+handle);assert f.reu()[physical*65536:physical*65536+46]==clipdata[:46]
  f.typed(native_text('cut'));f.render();assert f.document()==clipdata[46:] and f.get('se_ef_valid',1)==1
  fresh_cut,_,_,err=model.oracle(clipdata[46:]);assert not err and len(fresh_cut)==1
  expected_cut=[replace(x,flags=1,saved=0,motion=0) for x in fresh_cut]
  assert b''.join(f.records())==b''.join(x.bytes() for x in expected_cut),('cut-freshparse/unrelated-second-retained',f.records(),expected_cut)
  f.typed(native_text('undo'));f.render();assert f.document()==clipdata and f.get('se_e_error',1)==f.get('se_doc_read_locks',1)==f.get('se_fs_owned',1)==f.get('se_f_owner',1)==0
  fresh_undo,_,_,err=model.oracle(clipdata);assert not err and len(fresh_undo)==2
  expected_undo=[replace(x,flags=int(index==1),saved=0,motion=0) for index,x in enumerate(fresh_undo)]
  assert f.get('se_ef_valid',1)==1 and b''.join(f.records())==b''.join(x.bytes() for x in expected_undo),('undo-freshparse/new-first-expanded-second-retained',f.records(),expected_undo)
  assert f.get('se_h_current',4)==f.get('se_h_saved',4)
  cases.append('actualF7fold/savedcaret/indexwarm/markgoto4/copy46includinghidden/cut28/undo74clean/freshparsed-unrelated-second-collapse-retained')
  # Recovery must invalidate the published projection as well as the map. An
  # unchanged source/key/caret must not allow the old folded R1 cache to hit.
  f.source(clipdata,banks=1);f.put('se_status',1,1);f.typed(native_text('fold'));f.render()
  assert f.get('se_ef_valid',1) and f.get('se_ef_fold_rows',1)&1
  collapsed=f.read(0x4050,880);before=f.canonical();suppressed=f.suppress('foldcore')
  f.typed(native_text('fold'),error=0x17)
  assert f.get('se_ef_valid',1)==0 and f.get('se_f_owner',1)==0
  f.render();wanted=source40(clipdata,0,0,error=0x17)
  matrix=f.read(0x4000,1000);colors=bytes(x&15 for x in f.read(0xD800,1000))
  anchors=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
  (out/'recovery-expanded-screen.bin').write_bytes(matrix)
  (out/'recovery-expanded-colors.bin').write_bytes(colors)
  (out/'recovery-expanded-anchors.json').write_text(json.dumps(dict(actual=anchors,expected=wanted.anchors))+'\n')
  assert matrix[80:960]!=collapsed
  assert matrix[80:960]==wanted.matrix[80:960],('emergency-expanded-body',[(i,a,b) for i,(a,b) in enumerate(zip(matrix[80:960],wanted.matrix[80:960])) if a!=b][:16])
  assert colors[80:960]==wanted.colors[80:960] and anchors==wanted.anchors,('emergency-expanded-colors/anchors',anchors,wanted.anchors)
  # Each of the independently expected 880 glyphs defines eight native bitmap
  # scanlines. The font itself is immutable across this code path.
  font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
  raster=lambda cells:b''.join(bytes(v^(255 if c&128 else 0) for v in font[(c&127)*8:(c&127)*8+8]) for c in cells)
  assert raster(matrix[80:960])==raster(wanted.matrix[80:960])
  assert f.canonical()==before and f.get('se_doc_read_locks',1)==f.get('se_fs_owned',1)==0
  f.restore(suppressed);cases.append('publishedcollapsed/emergency-missingR18/nextpublicrender-expanded880cells7040glyphscanlines23anchors')
  # Resident modal helper is phase-independent even under FileUI/foreign work.
  # The descriptor is an actually built/published map, not a synthetic token.
  f.source(clipdata,banks=1);f.typed(native_text('fold'));f.render()
  token=f.read(f.s['se_ef_token'],5);key=f.read(f.s['se_ef_key'],28);records=f.records();reu=f.reu()
  assert not f.call('se_doc_read_acquire').p&1
  for owner in [0,2,3,255]:
   f.put('se_f_owner',1,1);phase=bytes((i*29+owner)&255 for i in range(1152));f.m.load(0x8D00,phase)
   reg=f.call('se_ef_modal');assert not reg.p&1 and reg.a==0 and f.get('se_ef_suspended',1)==1 and f.get('se_ef_valid',1)==0
   assert f.read(0x8D00,1152)==phase and f.get('se_doc_read_locks',1)==1
   reg=f.call('se_ef_modal');assert not reg.p&1 and f.read(0x8D00,1152)==phase
   f.put('se_f_owner',owner,1);reg=f.call('se_ef_modal')
   assert not reg.p&1 and reg.a==0 and f.get('se_ef_valid',1)==1 and f.get('se_ef_suspended',1)==0
   assert f.read(0x8D00,1152)==phase and f.get('se_doc_read_locks',1)==1
   assert f.get('se_l_valid',1)==f.get('se_r_valid',1)==f.get('se_st_valid',1)==f.get('se_st_request',1)==f.get('se_st_cp_valid',1)==0 and f.get('se_l_need_wrap',1)==1
  assert f.reu()==reu and f.read(f.s['se_ef_token'],5)==token and f.records()==records
  # Explicit key mismatch and actual invalid-token provider fault take distinct
  # return paths; a CMP must not accidentally clear the provider error carry.
  f.put('se_f_owner',1,1);f.call('se_ef_modal');f.m.write(f.s['se_ef_key']+17,key[17]^1);f.put('se_f_owner',0,1);reg=f.call('se_ef_modal')
  assert not reg.p&1 and reg.a==0 and f.get('se_ef_valid',1)==f.get('se_ef_suspended',1)==0
  f.m.load(f.s['se_ef_key'],key);f.put('se_ef_valid',1,1);f.put('se_f_owner',1,1);f.call('se_ef_modal');meta=f.read(f.s['se_doc_meta'],5);bad=bytearray(meta);bad[1]^=1;f.m.load(f.s['se_doc_meta'],bad);f.put('se_f_owner',0,1);reg=f.call('se_ef_modal')
  assert reg.p&1 and reg.a==0x31 and f.get('se_ef_valid',1)==f.get('se_ef_suspended',1)==0
  f.m.load(f.s['se_doc_meta'],meta);f.call('se_doc_read_release');assert f.reu()==reu
  cases.append('modalactualpublishedmap/owner1suspend/owners0-2-3-255resume/phase-andforeignlease-andREUopaque/keychange-normal/provider31carry')
  # Real queued STOP while C11 owns an incomplete fold projection. Cancelling
  # drops incomplete derived rows; FileUI suspends the map while owner1 holds
  # its opaque phase. No directory-I/O completion claim in this CPU fixture.
  f.source(clipdata,banks=1);f.typed(native_text('fold'));f.render();before=f.canonical()
  f.call('se_editor_command',98);f.call('se_editor_render')
  assert f.get('se_e_job',1)==7 and f.get('se_l_valid',1)==0 and f.get('se_f_owner',1)==3
  tail=f.get('se_input_tail',1);f.m.write(f.s['se_input_chars']+tail,3);f.m.write(f.s['se_input_mods']+tail,0);f.put('se_input_head',(tail+1)%32,1)
  f.call('se_editor_service')
  assert f.get('se_e_job',1)==f.get('se_f_owner',1)==f.get('se_doc_read_locks',1)==0
  f.key(0x85);f.key(native_text('f')[0]);f.put('se_e_key',native_text('o')[0],1);f.call('se_editor_input')
  assert f.get('se_e_ui',1)==3 and f.get('se_f_owner',1)==1 and f.get('se_e_job',1)==9
  phase=f.read(0x8D00,1152);f.call('se_editor_render')
  for steps in range(100):
   if f.get('se_e_job',1)!=7:break
   f.call('se_editor_service')
  assert f.get('se_e_job',1)==0 and f.get('se_f_owner',1)==1 and f.get('se_l_valid',1)==1 and f.get('se_ef_valid',1)==0,('STOPmodal-layout-did-not-converge',steps)
  assert f.read(0x8D00,1152)==phase and f.document()==clipdata and f.get('se_doc_read_locks',1)==0
  cases.append('actualqueuedSTOP-C11/mode80/F1FileOpen/owner1-render-converges-phaseopaque-directorypending')
  assert f.read(0xC600,1024)==f.shim
  result=dict(status='passed',resident_sha256=r['sha256'],catalog=names,controller_calls=f.calls,peak_instructions=f.peak,coordinator_phases=sorted(f.phases),folds=len(tree),cases=cases,shim_bytes=1024,whole_REU_guard_bytes=16777216,source_bytes=len(data),limits='Actual frozen residentdispatch/C19/C17/C18/R18/R14/object/hot code, actualF7clipboard and source40recovery body/anchor oracle. Glyph scanlines derived from verified nativefont and exact screen codes; not a VIC/native screenshot claim. Modal FileOpen render is explicitly before directory I/O; separate native acceptance must prove completed directory/save/cancel restoration. Catalogremoval and object-table exhaustion are explicit actualresource faults.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 evidence=ROOT/'agentsworking/evidence/M5'/(stamp+'-fold-controller');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 for name in ['tests/test_fold_controller.py','src/editor_fold/coordinator.s','src/editor_fold/controller.inc','src/editor_fold/emergency.s','src/editor_fold/phase-state.s','src/editor_fold/modal.s','src/editor_fold/modal-state.s','src/overlays/fold-editor.s']:
  target=evidence/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()
