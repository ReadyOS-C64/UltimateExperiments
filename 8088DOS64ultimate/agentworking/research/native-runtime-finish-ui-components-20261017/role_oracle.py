from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent
def labels(f):return{x.split()[2].lstrip('.'):int(x.split()[1],16)for x in f.read_text().splitlines()if x.startswith('al ')}
def constants(f):return{m.group(1):int(m.group(2),16)for m in re.finditer(r'^([A-Za-z0-9_]+)\s*=\s*\$([0-9a-fA-F]+)\s*$',f.read_text(),re.M)}
def verify(role):
 assert role in ['unit','runtime'];n=labels(P/'work/build'/('dos64.labels'if role=='runtime'else'dos64-tests.labels'));b=labels(P/'broker/broker.labels');u=labels(P/'ui/panel.labels');a=labels(P/'controller/controller.labels');t=labels(P/'phase/transaction-wire.labels');m=labels(P/'phase/modal-save.labels');q=labels(P/'phase/runtime-plan.labels');checks={}
 for f in ['phase/runtime.inc','binding/runtime.inc','broker/symbols.inc']:
  c=constants(P/f);assert c and all(k in n and n[k]==v for k,v in c.items()),f;checks[f]=len(c)
 c=constants(P/'controller/native.inc');table=dict(n,**b);assert c and all(k in table and table[k]==v for k,v in c.items());checks['controller/native.inc']=len(c)
 c=constants(P/'bridge/symbols.inc');table={**n,**b,**u,**a,**labels(P/'finish/finish.labels')};assert c and all(k in table and table[k]==v for k,v in c.items());checks['bridge/symbols.inc']=len(c)
 c=constants(P/'phase/sequence_broker.inc')
 for name in ['native_owner','saved_files','saved_hd','saved_hdb']:assert c['alloc_broker_'+name]==b[name]
 c=constants(P/'binding/broker.inc')
 for k,z in [('owned','modal_owned'),('context','modal_context'),('files','saved_files'),('hd','saved_hd'),('hdb','saved_hdb'),('online','saved_online'),('target','saved_target')]:assert c['broker_'+k]==b[z]
 c=constants(P/'controller/worker.inc')
 for table,names in [(t,['tw_take_sequence','tw_begin','tw_poll','tw_state','tw_error','tw_closed','tw_committing','tw_home','tw_sequence','tw_limit','tw_mode','tw_cancel']),(m,['ms_begin','ms_poll','ms_state','ms_error','ms_drive','ms_path','ms_cancel'])]:
  for name in names:assert c[name]==table[name],name
 for name in ['mp_drive','mp_readonly','mp_sequence','mp_capacity','mp_image_path','mp_snapshot','mp_image_crc']:assert c[name]==q['_'+name]
 for f,table,init,build in [('phase/plan-entry.inc',q,'_mp_fixture_init','_mp_build'),('binding/plan-entry.inc',labels(P/'binding/binding.labels'),'_mb_fixture_init','_mb_bind')]:
  c=constants(P/f);assert c['plan_init']==table[init]and c['plan_build']==table[build],f
 saver='dos64-resident.prg.saver.bin'if role=='runtime'else'dos64-tests-resident.prg.saver.bin';assert(P/'phase/selected_saver.inc').read_text()=='.incbin "../work/build/'+saver+'"\n';raw=(P/'work/build'/saver).read_bytes();assert(P/'phase/modal-save.prg').read_bytes()[2+0x210:2+0x210+len(raw)]==raw
 image=P/'work/build'/('dos64.prg'if role=='runtime'else'dos64-tests.prg');header=(P/'HEADER.bin').read_bytes();assert header[8:24]in image.read_bytes();assert(P/'MODAL.MNU').read_bytes()[:64]==header
 return{'role':role,'alias_checks':checks,'explicit_SAVER':saver,'SAVER_bytes':len(raw),'native_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'native_bytes':image.stat().st_size,'cold_open':n['dos64_cold_open'],'tag':header[8:24].hex(),'native_labels':str(image.with_suffix('.labels'))}
