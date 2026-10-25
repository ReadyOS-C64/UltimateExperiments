"""Actual C19 journal-retention ownership/recovery gate; no sharedbuild/VICE."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,sys,zipfile
import test_fold_controller as t
from redraw_model import native_text
ROOT=t.ROOT
DATA=native_text('plain start\r:::region A\ralpha\r:::end\routside middle\r:::region B\rbeta\r:::end\rplain end\r')

def main():
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/fold-retention-faults'/stamp;out.mkdir(parents=True);base,r,names=t.freeze(out);t.cpu_editor.ROOT=t.editor_fixture.ROOT=base;t.cpu_editor.NAMES=t.editor_fixture.NAMES=names;f=t.Fixture(out);cases=[]
 def oldmap():return f.read(f.s['se_ef_token'],5),b''.join(f.records())
 def unchanged(old):
  token,raw=old;assert f.read(f.s['se_ef_token'],5)==token and b''.join(f.records())==raw and f.m.read(f.s['object_owner']+token[0])==0x46
 def owned():return [i for i in range(8) if f.m.read(f.s['object_owner']+i)==0x46]
 def merged():
  data=f.document();base=f.get('se_hot_base');old=f.get('se_hot_old_length',2);left=f.get('se_hot_left',2);right=f.get('se_hot_right',2);return data[:base]+f.read(0x9200,left)+f.read(0x9200+right,2048-right)+data[base+old:]
 def setup():
  f.source(DATA,banks=1);f.command(115);f.render();assert len(f.records())==2 and all(x[13]&1 for x in f.records()) and f.get('se_ej_status',1)==1 and f.get('se_ej_count',1)==0
  f.key(native_text('Q')[0]);assert f.get('se_hot_pending',1) and f.get('se_ej_status',1)==2 and f.get('se_ej_count',1)==1
  return oldmap()
 def clean(error=0):
  assert f.get('se_f_owner',1)==f.get('se_ef_active',1)==f.get('se_doc_read_locks',1)==f.get('se_fs_owned',1)==f.get('se_ec_allocated',1)==0 and not f.get('se_ec_reuse',1)&1
  assert f.read(0xC600,1024)==f.shim
 def foreign_guard(before,allowed=()):
  after=f.reu();allowed=set(allowed);assert all(before[i*65536:(i+1)*65536]==after[i*65536:(i+1)*65536] for i in range(256) if i not in allowed)
 try:
  old=setup();canonical=f.canonical();before=f.reu();hidden=f.suppress('foldxform');reg=f.finish(f.dispatch(0,6));assert reg.p&1 and reg.a==0x17;f.restore(hidden);unchanged(old);clean();assert owned()==[old[0][0]] and f.get('se_ej_status',1)==0x80 and not f.get('se_ef_valid',1) and f.canonical()==canonical and f.reu()==before;cases.append('missingR20-BEGIN/oldpublishedmapretained/hintcleanup/source-all16MiB-exact')
  old=setup();canonical=f.canonical();before=f.reu();reg=f.dispatch(0,6);assert not reg.p&1 and f.get('se_ec_phase',1)==4 and f.get('se_ec_reuse',1)&1;hint=f.read(f.s['se_fb_old_token'],5);bank=f.bank(hint)
  for _ in range(3):reg=f.dispatch();assert not reg.p&1
  hidden=f.suppress('foldxform');reg=f.finish(f.dispatch());assert reg.p&1 and reg.a==0x17;f.restore(hidden);unchanged(old);clean();assert owned()==[old[0][0]] and f.canonical()==canonical;foreign_guard(before,[bank]);cases.append('missingR20-midSTEP/partialhintretired/oldpublishedmapandforeignREUretained')
  old=setup();canonical=f.canonical();before=f.reu();reg=f.call('se_editor_render');assert not reg.p&1 and f.get('se_e_job',1)==10 and f.get('se_ec_phase',1)==4;hint=f.read(f.s['se_fb_old_token'],5);bank=f.bank(hint)
  f.call('se_editor_service');f.call('se_editor_service');tail=f.get('se_input_tail',1);f.m.write(f.s['se_input_chars']+tail,3);f.m.write(f.s['se_input_mods']+tail,0);f.put('se_input_head',(tail+1)%32,1);f.call('se_editor_service');assert f.get('se_e_job',1)==0
  unchanged(old);clean();assert owned()==[old[0][0]] and f.get('se_ej_status',1)==0x80 and f.canonical()==canonical;foreign_guard(before,[bank]);cases.append('actualqueuedSTOP-job10-phase4/hintreleased/oldmap-kept/source-andforeignREUexact')
  old=setup();foreign=[]
  while sum(f.m.read(f.s['object_owner']+i)==0 for i in range(8))>1:
   reg,_=f.m.call(f.s['se_object_create'],a=99,x=1);assert not reg.p&1;foreign.append(f.read(f.s['se_object_id'],5))
  canonical=f.canonical();before=f.reu();reg=f.dispatch(0,6);assert not reg.p&1;hint=f.read(f.s['se_fb_old_token'],5);bank=f.bank(hint);reg=f.finish(reg);assert reg.p&1 and reg.a==0x35;unchanged(old);clean();assert owned()==[old[0][0]] and f.canonical()==canonical
  for token in foreign:assert f.m.read(f.s['object_owner']+token[0])==99
  foreign_guard(before,[bank]);cases.append('actualobjecttable-exhausted-after-hint/candidate-create35/hintretired/oldmap-andforeignowners-kept')
  # Suppress journal only after transformation, so failure occurs at BASELINE
  # admission after a newly parsed map was fully published, with old DIRTY1.
  old=setup();canonical=f.canonical();reg=f.dispatch(0,6)
  for _ in range(10000):
   if f.get('se_ec_phase',1)==1:break
   reg=f.dispatch();assert not reg.p&1
  else:raise AssertionError('transform never reached parser')
  assert f.get('se_ej_status',1)==2 and f.get('se_ej_count',1)==1
  hidden=f.suppress('rangeio');reg=f.finish(reg);assert not reg.p&1 and reg.a==0 and f.get('se_ef_valid',1)==1 and f.get('se_ej_status',1)==0x80 and f.get('se_ej_count',1)==1 and f.canonical()==canonical;clean();assert len(owned())==1 and all(x[13]&1 for x in f.records())
  f.render();assert f.get('se_e_job',1)==0 and f.get('se_ej_status',1)==0x80;f.restore(hidden);cases.append('missingR19-BASELINE-afterfreshpublish/disarms-oldDIRTY1/mapvalid/noautorebuildloop')
  # Fresh map built from a pending view; public LEFT flush changes generation
  # but no visible edit remains in the freshly reset zero-event journal.
  setup();f.render();old=oldmap();assert f.get('se_hot_pending',1) and f.get('se_ej_count',1)==0 and f.get('se_ej_status',1)==1;data=merged();f.command(1);assert not f.get('se_hot_pending',1) and f.document()==data and f.get('se_ej_count',1)==0
  before=f.reu();f.render();unchanged(old);clean();assert f.read(f.s['se_ef_key']+15,2)==f.read(f.s['se_doc_generation'],2) and f.get('se_ej_status',1)==1 and f.get('se_ej_count',1)==0 and f.reu()==before;cases.append('actualpublicLEFT-hotflush/ARMEDzeroevent/READLOGwitness-rekeys-samepublishedmap')
  # Actual original-adoption publication primitive with a fresh allocator token.
  # Setup the fresh root input frame as FileIO does; this is not a FileUI test.
  f.source(DATA,banks=1);f.command(115);f.render();old=oldmap();assert f.get('se_ej_status',1)==1
  original=f.read(f.s['se_doc_original'],5);reg,_=f.m.call(f.s['se_object_create'],a=4,x=1);assert not reg.p&1;replacement=f.read(f.s['se_object_id'],5);newdata=native_text('# New\rnew source body\r# Tail\rend\r');f.m.load(0x8000,newdata);f.put('se_object_offset',0);f.put('se_object_length',len(newdata),2);f.put('se_object_c64',0x8000,2);assert not f.call('se_object_copy').p&1
  assert not f.call('se_hot_call',10).p&1;f.m.load(f.s['se_doc_original'],replacement);f.put('se_doc_root_count',0,1);f.put('se_doc_length',0);f.put('se_doc_generation',1,2);f.put('se_doc_source_length',len(newdata));assert not f.call('se_doc_adopt_original').p&1
  assert not f.call('se_history_call',1).p&1;assert not f.call('se_hot_cold').p&1;f.put('se_hot_group',1,1);f.position(0);f.m.load(f.s['se_object_id'],original);assert not f.call('se_object_release').p&1
  # First fold must discard stale journal graph and build normally, no error.
  f.command(115);f.render();assert f.document()==newdata and f.get('se_ef_valid',1)==1 and f.get('se_ej_status',1)==1 and f.get('se_ej_count',1)==0 and f.read(f.s['se_ef_key']+5,5)==replacement and all(x[13]&1 for x in f.records());clean();cases.append('actualfreshoriginal-token/adoptpublication/stalejournal-discard/firstnewdocfold-succeeds')
  result=dict(status='passed',resident_sha256=r['sha256'],catalog=names,cases=cases,controller_calls=f.calls,peak_instructions=f.peak,whole_REU_guard_bytes=16777216,scope='Actual C19/R19/R20/catalog/provider/hot/history/queuedSTOP code. Explicit catalog resource faults and real allocator exhaustion; no native/pixel/FileUI OPEN claim. Lifecycle uses actual original-adoption publication with explicit fresh-frame setup.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e),cases=cases),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 evidence=ROOT/'agentsworking/evidence/M5'/(stamp+'-fold-retention-faults');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 with zipfile.ZipFile(evidence/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in ['src/editor_fold/coordinator.s','src/editor_fold/retain.s','src/fold/transform.s','src/fold/transform.inc','tests/test_fold_retention_ownership.py','tests/test_fold_controller.py']:z.write(ROOT/name,name)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()
