from pathlib import Path
import json,hashlib,subprocess,shutil,os,sys,zlib,argparse
ap=argparse.ArgumentParser();ap.add_argument('--role',choices=['unit','runtime'],default='unit');role=ap.parse_args().role
P=Path(__file__).resolve().parent;W=P/'work';tools={n:str(Path(shutil.which(n)).resolve())for n in ['cc65','ca65','ld65','make']};env=dict(os.environ)
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPYCACHEPREFIX']=str(P/'.absent-ui-build-cache');assert not Path(env['PYTHONPYCACHEPREFIX']).exists()
commands=[];sdk=Path(tools['cc65']).parents[1]/'share/cc65'
def run(a,d=P):
 a=list(map(str,a));i=len(commands);r=subprocess.run(a,cwd=d,env=env,capture_output=True);(P/f'UIBUILD{i:02d}.stdout').write_bytes(r.stdout);(P/f'UIBUILD{i:02d}.stderr').write_bytes(r.stderr);commands.append({'argv':a,'cwd':str(d),'exit':r.returncode});(P/'UI_BUILD_COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,(i,a,r.stderr.decode())
def labels(p):return{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
def info(p):b=p.read_bytes();return{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
flags=['DOS64_MODAL_MENU=1','DOS64_SAVE_HD_CONTEXT=1','DOS64_EXPORT_CRC=1','DOS64_SAVE_MODAL=1','DOS64_MEDIA_BINDING=1']
# First native link establishes role-specific addresses; header retagging below
# changes only fixed bytes. No foreign aliases may survive final verification.
run([tools['make'],'build/dos64.prg','build/dos64-tests.prg','build/dos64-tests.prg.unit-extra.bin','build/dos64-tests.bin','verify-memory',*flags],W)
for n in ['panel','platform']:run([tools['cc65'],'-t','none','-O',n+'.c','-o',n+'.s'],P/'ui')
for n in ['header','panel','platform','scan']:run([tools['ca65'],'-g',n+'.s','-o',n+'.o'],P/'ui')
run([tools['ld65'],'-C','panel.cfg','-o','panel.prg','-m','panel.map','-Ln','panel.labels','header.o','panel.o','platform.o','scan.o',sdk/'lib/none.lib'],P/'ui');U=labels(P/'ui/panel.labels');ui=(P/'ui/panel.prg').read_bytes()[2:];assert len(ui)<=8192
ui_names=['_mu_fixture_init','_mu_capture','_mu_poll','_mu_take','_mu_reply','_mu_block','_mu_refresh','_mu_view','_mu_event','_mu_reply_ticket','_mu_reply_error','_mu_reply_safe','_mu_block_error']
for folder,nativefile in [('broker','dos64.labels'if role=='runtime'else'dos64-tests.labels'),('broker-runtime','dos64.labels')]:
 (P/folder/'bridge_products.inc').write_text('BRIDGE_BYTES=1\nBRIDGE_CRC=0\nBRIDGE_REU=$3df300\nUI_BYTES=%d\nUI_CRC=$%08x\n'%(len(ui),zlib.crc32(ui)))
 N=labels(W/'build'/nativefile);old=(P/folder/'symbols.inc').read_text();names=[l.split('=',1)[0].strip()for l in old.splitlines()if '='in l];(P/folder/'symbols.inc').write_text(''.join(n+'=$%04x\n'%N[n]for n in names));(P/folder/'ui_symbols.inc').write_text(''.join(n+'=$%04x\n'%U[n]for n in ui_names))
 run([tools['ca65'],'-g','broker.s','-o','broker.o'],P/folder);run([tools['ld65'],'-C','broker.cfg','-o','broker.prg','-m','broker.map','-Ln','broker.labels','broker.o'],P/folder)
N=labels(W/'build'/('dos64.labels'if role=='runtime'else'dos64-tests.labels'));B=labels(P/'broker/broker.labels');oldaliases=(P/'binding/runtime.inc').read_text()if(P/'binding/runtime.inc').exists()else(P/'phase/runtime.inc').read_text()
(P/'phase/runtime.inc').write_text(''.join(n+'=$%04x\n'%v for n,v in N.items()if n.startswith(('dos64_','hdb_','hd_','hdc_','sav_'))))
# BIND native aliases live in its copied runtime include; regenerate any file
# actually named by source instead of assuming a previous role's addresses.
print('bindinginclude',[(p.name,p.read_text().splitlines()[:4])for p in(P/'binding').glob('*.s')if p.name=='glue.s'])
(P/'binding/runtime.inc').write_text((P/'phase/runtime.inc').read_text())
# Every executable phase is rebuilt against selected native aliases. The
# runtime SAVER is explicit and never loaded through a UNIT-named alias.
saver='dos64-resident.prg.saver.bin'if role=='runtime'else'dos64-tests-resident.prg.saver.bin'
(P/'phase/selected_saver.inc').write_text('.incbin "../work/build/'+saver+'"\n')
run([tools['ca65'],'-g','modal_save.s','-o','modal_save.o'],P/'phase')
run([tools['ld65'],'-C','modal-save.cfg','-o','modal-save.prg','-m','modal-save.map','-Ln','modal-save.labels','modal_save.o'],P/'phase')
run([tools['cc65'],'-t','none','-Oirs','-D','MP_RUNTIME_RECEIPT=1','-D','MP_BUILD_ONLY=1','media_plan.c','-o','media_plan.s'],P/'phase')
for n in ['media_plan','glue','crc']:run([tools['ca65'],'-g',n+'.s','-o',n+'.o'],P/'phase')
run([tools['ld65'],'-C','plan.cfg','-o','runtime-plan.prg','-m','runtime-plan.map','-Ln','runtime-plan.labels','media_plan.o','glue.o','crc.o',sdk/'lib/none.lib'],P/'phase')
Q=labels(P/'phase/runtime-plan.labels');(P/'phase/plan-entry.inc').write_text('plan_init=$%04x\nplan_build=$%04x\n'%(Q['_mp_fixture_init'],Q['_mp_build']))
run([tools['ca65'],'-g','worker_calls.s','-o','worker_calls.o'],P/'phase')
run([tools['ld65'],'-C','worker-calls.cfg','-o','worker-calls.prg','-m','worker-calls.map','-Ln','worker-calls.labels','worker_calls.o'],P/'phase')


(P/'binding/broker.inc').write_text(''.join('broker_'+a+'=$%04x\n'%B[b]for a,b in [('owned','modal_owned'),('context','modal_context'),('files','saved_files'),('hd','saved_hd'),('hdb','saved_hdb'),('online','saved_online'),('target','saved_target')]))
run([tools['cc65'],'-t','none','-O','media_bind.c','-o','media_bind.s'],P/'binding')
for n in ['media_bind','glue']:run([tools['ca65'],'-g',n+'.s','-o',n+'.o'],P/'binding')
run([tools['ca65'],'-g','../phase/crc.s','-o','crc.o'],P/'binding');run([tools['ld65'],'-C','../phase/plan.cfg','-o','binding.prg','-m','binding.map','-Ln','binding.labels','media_bind.o','glue.o','crc.o',sdk/'lib/none.lib'],P/'binding')
Q=labels(P/'binding/binding.labels');(P/'binding/plan-entry.inc').write_text('plan_init=$%04x\nplan_build=$%04x\n'%(Q['_mb_fixture_init'],Q['_mb_bind']))
run([tools['ca65'],'-g','worker_calls.s','-o','worker_calls.o'],P/'binding');run([tools['ld65'],'-C','../phase/worker-calls.cfg','-o','binding-calls.prg','-m','binding-calls.map','-Ln','binding-calls.labels','worker_calls.o'],P/'binding')
# WIRE mode2 is linked only after exact selected native/broker role aliases are known.
(P/'phase/sequence_broker.inc').write_text(''.join('alloc_broker_'+n+'=$%04x\n'%B[n]for n in ['native_owner','saved_files','saved_hd','saved_hdb']))
run([tools['ca65'],'-g','-D','DOS64_MEDIA_BINDING=1','-D','DOS64_MEDIA_SEQUENCE=1','transaction_wire.s','-o','transaction_wire.o'],P/'phase')
run([tools['ld65'],'-C','plan.cfg','-o','transaction-wire.prg','-m','transaction-wire.map','-Ln','transaction-wire.labels','transaction_wire.o'],P/'phase')
run([sys.executable,'-B','build_controller.py','--role',role])
run([sys.executable,'-B','build_finish.py','--role',role])
F=labels(P/'finish/finish.labels');finish=(P/'finish/finish.prg').read_bytes()[2:]
A=labels(P/'controller/controller.labels');controller=(P/'controller/controller.prg').read_bytes()[2:]
(P/'bridge/symbols.inc').write_text(''.join(n+'=$%04x\n'%v for table in [N,B,U,A,F]for n,v in table.items()if (table is F and n.startswith('fn_'))or n in ['modal_owned','modal_context','modal_error','modal_verify','verify_expected','ui_ready','modal_poll','modal_ui_on','modal_ui_off','modal_view_refresh','dos64_native_diag','dos64_cache_limit','dos64_reu_request','dos64_reu_transfer','_mu_event','_mu_capture','_mu_view','_mu_refresh','_mu_block_error','_mu_block','_mu_reply_ticket','_mu_reply_error','_mu_reply_safe','_mu_reply','ac_entry','_ac_request','_ac_result']))
(P/'bridge/products.inc').write_text('CONTROLLER_BYTES=%d\nCONTROLLER_CRC=$%08x\nUI_BYTES=%d\nUI_CRC=$%08x\n'%(len(controller),zlib.crc32(controller),len(ui),zlib.crc32(ui))+('FINISH_BYTES=%d\nFINISH_CRC=$%08x\n'%(len(finish),zlib.crc32(finish))))
run([tools['ca65'],'-g','bridge.s','-o','bridge.o'],P/'bridge');run([tools['ld65'],'-C','bridge.cfg','-o','bridge.prg','-m','bridge.map','-Ln','bridge.labels','bridge.o'],P/'bridge');bridge=(P/'bridge/bridge.prg').read_bytes()[2:];assert len(bridge)<=0xd00
bridge_offset=json.loads((P/'CONTROLLER_BUILD.json').read_text())['core_end'];assert bridge_offset+len(bridge)<=0x6000
for folder in ['broker','broker-runtime']:
 (P/folder/'bridge_products.inc').write_text('BRIDGE_BYTES=%d\nBRIDGE_CRC=$%08x\nBRIDGE_REU=$%06x\nUI_BYTES=%d\nUI_CRC=$%08x\n'%(len(bridge),zlib.crc32(bridge),0x3da000+bridge_offset,len(ui),zlib.crc32(ui)))
 run([tools['ca65'],'-g','broker.s','-o','broker.o'],P/folder);run([tools['ld65'],'-C','broker.cfg','-o','broker.prg','-m','broker.map','-Ln','broker.labels','broker.o'],P/folder)
 final=labels(P/folder/'broker.labels');prior=B if folder=='broker'else None
 if prior:
  for n in ['modal_owned','modal_context','modal_error','modal_verify','verify_expected','ui_ready','modal_poll','modal_ui_on','modal_ui_off','modal_view_refresh','saved_files','saved_hd','saved_hdb','saved_online','saved_target']:assert prior[n]==final[n],n
broker=(P/'broker/broker.prg').read_bytes()[2:];assert len(broker)<=2048
# Native common cohort includes every actual new source/product identity.
sources={str(f.relative_to(P)):info(f)for root in ['work/src','work/include','work/cfg','broker','broker-runtime','bridge','controller','ui','phase','binding','finish']for f in(P/root).rglob('*')if f.is_file()and f.suffix in ['.c','.h','.s','.inc','.cfg']and f.name!='modal_assets.inc'}
sources['build_ui_bridge.py']=info(P/'build_ui_bridge.py');sources['build_controller.py']=info(P/'build_controller.py');sources['build_finish.py']=info(P/'build_finish.py');sources['work/Makefile']=info(W/'Makefile')
tag=hashlib.sha256(json.dumps({'source':sources,'flags':flags,'role':role},sort_keys=True,separators=(',',':')).encode()).digest()[:16]
header=bytearray(64);header[:8]=b'D64M\1\1\x40\0';header[8:24]=tag;header[24:26]=len(broker).to_bytes(2,'little');header[26:28]=b'\0p';header[28:31]=(0x3da200).to_bytes(3,'little');header[31:33]=len(ui).to_bytes(2,'little');header[33:36]=(0x3daa00).to_bytes(3,'little');(P/'HEADER.bin').write_bytes(header)
(W/'include/modal_assets.inc').write_text('MM_BROKER_BYTES='+str(len(broker))+'\nMM_HEADER_REU=$3da000\nMM_BROKER_REU=$3da200\n.macro MM_EXPECTED_HEADER\n.byte '+','.join(map(str,header))+'\n.endmacro\n')
# Whole-second Make mtimes cannot authorize a stale cohort.
for name in ['modal_entry.o','unit-modal_entry.o','dos64.prg','dos64-tests.prg','dos64-tests.prg.unit-extra.bin','dos64-tests.bin']:(W/'build'/name).unlink(missing_ok=True)
run([tools['make'],'build/dos64.prg','build/dos64-tests.prg','build/dos64-tests.prg.unit-extra.bin','build/dos64-tests.bin','verify-memory',*flags],W)
assert (W/'build'/('dos64.prg'if role=='runtime'else'dos64-tests.prg')).read_bytes().count(header[8:24])==1
finalN=labels(W/'build'/('dos64.labels'if role=='runtime'else'dos64-tests.labels'));assert all(N[n]==finalN[n]for n in N if n.startswith(('dos64_','hdb_','hd_','hdc_','sav_')))
body=bytearray((P/'WORKERS.MNU').read_bytes());body[:64]=header;body[0x200:0x200+len(broker)]=broker;body[0xa00:0xa00+len(ui)]=ui;assert 0xa00+len(ui)<=0x2800;body[bridge_offset:bridge_offset+len(bridge)]=bridge;assert 0x9800+len(finish)<=len(body);body[0x9800:0x9800+len(finish)]=finish;(P/'MODAL.MNU').write_bytes(body)
result={'scope':'selected-role fullCUI sequence SaveAs; coldSTART/public/physical unqualified','role':role,'native':info(W/'build'/('dos64.prg'if role=='runtime'else'dos64-tests.prg')),'broker':info(P/'broker/broker.prg'),'ui':info(P/'ui/panel.prg'),'bridge':info(P/'bridge/bridge.prg'),'controller':info(P/'controller/controller.prg'),'finish':info(P/'finish/finish.prg'),'MNU':info(P/'MODAL.MNU'),'tag':tag.hex(),'inputs':sources};(P/'UI_BUILD_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='inputs'}))
