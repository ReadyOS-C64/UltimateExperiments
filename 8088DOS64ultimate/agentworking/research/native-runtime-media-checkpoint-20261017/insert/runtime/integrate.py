from pathlib import Path
import json,hashlib,shutil
P=Path(__file__).resolve().parent;O=P.parent/'live-media-ui-saveas-root-20261017'
added={}
for n in ['build_support','assets','tests','third_party']:
 for q in (O/'work'/n).rglob('*'):
  if q.is_file() and not any(x in q.parts for x in ['__pycache__','.zig-cache','zig-out']):
   r=q.relative_to(O/'work');dst=P/'work'/r;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(q.read_bytes());added[str(r)]={'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
(P/'SUPPLEMENTAL_PRIVATE_BUILD_INPUTS.json').write_text(json.dumps(added,indent=2)+'\n')
p=P/'controller/action_shell.c';s=p.read_text().replace('extern char tw_home[128];','extern unsigned int tw_take_sequence(void);\nextern char tw_home[128];');s=s.replace(' if(service_cause)return failure(service_cause,0u,tw_closed());\n return 1u;',''' if(service_cause)return failure(service_cause,0u,tw_closed());
 if(mode==2u){
  /* Only private WIRE DONE/known-C+freshbroker authority selects a sequence.
   * The request value is an advisory nonzero search hint, never CUI identity. */
  job.sequence=tw_take_sequence();
  if(!job.sequence)return failure(3u,tw_error(),tw_closed());
  ac_result.sequence=job.sequence;
 }
 return 1u;''',1);s=s.replace('ac_result.phase=WIRE;if(!wire(0u))','ac_result.phase=WIRE;if(!wire(2u))');p.write_text(s)
p=P/'bridge/bridge.s';s=p.read_text();a=' lda br_intent\n sta _ac_request+2\n lda br_intent+1\n sta _ac_request+3';b=''' ; CUI ticket belongs only to the private WAIT/reply protocol. Start readonly
 ; archive search at1; WIRE returns the private transaction sequence separately.
 lda #1
 sta _ac_request+2
 lda #0
 sta _ac_request+3''';assert a in s;s=s.replace(a,b);p.write_text(s)
p=P/'controller/action_shell.h';s=p.read_text().replace('struct ac_request_t {','/* sequence is advisory allocation search hint; result.sequence is selected. */\nstruct ac_request_t {',1);p.write_text(s)
p=P/'build_controller.py';s=p.read_text().replace("'tw_begin','tw_poll'","'tw_take_sequence','tw_begin','tw_poll'",1);p.write_text(s)
p=P/'build_ui_bridge.py';s=p.read_text();needle="run([sys.executable,'-B','build_controller.py'])";replacement='''# WIRE mode2 is linked only after exact UNIT/broker role aliases are known.
(P/'phase/sequence_broker.inc').write_text(''.join('alloc_broker_'+n+'=$%04x\\n'%B[n]for n in ['native_owner','saved_files','saved_hd','saved_hdb']))
run([tools['ca65'],'-g','-D','DOS64_MEDIA_BINDING=1','-D','DOS64_MEDIA_SEQUENCE=1','transaction_wire.s','-o','transaction_wire.o'],P/'phase')
run([tools['ld65'],'-C','plan.cfg','-o','transaction-wire.prg','-m','transaction-wire.map','-Ln','transaction-wire.labels','transaction_wire.o'],P/'phase')
'''+needle;assert needle in s;s=s.replace(needle,replacement);s=s.replace("'broker-runtime','bridge','controller','ui'","'broker-runtime','bridge','controller','ui','phase','binding'");s=s.replace('sequence allocation/coldSTART/public/physical pending','private sequence allocation enabled; coldSTART/runtime/public/physical pending');s=s.replace('commands=[];sdk=',"env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPYCACHEPREFIX']=str(P/'.absent-ui-build-cache');assert not Path(env['PYTHONPYCACHEPREFIX']).exists()\ncommands=[];sdk=",1);p.write_text(s)
p=P/'model/tests/floppy_export/bulk_model.h';s=p.read_text();old='if(!files.contains(path)){error();break;}';assert old in s;s=s.replace(old,'if(!files.contains(path)){const char *msg="FILE DOESN\\\'T EXIST";s.assign(msg,msg+18);break;}');p.write_text(s)
shutil.copy2(P.parent/'native-media-unused-sequence-20261017/build_model.py',P/'build_model.py')
