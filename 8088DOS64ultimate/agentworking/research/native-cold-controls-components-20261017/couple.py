from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;W=P/'work';sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/'.absent-coupled-build');assert not Path(sys.pycache_prefix).exists()
import subprocess,hashlib,json,zlib,importlib.util
D=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,args):
 with(P/(name+'.stdout')).open('wb')as out,(P/(name+'.stderr')).open('wb')as err:subprocess.run([sys.executable,'-B']+list(map(str,args)),cwd=P,stdout=out,stderr=err,check=True)
run('COUPLED_BUILD',[P/'build.py'])
old=(W/'controller.prg').read_bytes();ino=(W/'START.INO').read_bytes()
run('GATE_LINK',[P/'build_gate.py','--start-work',W,'--start-sha256',D(W/'controller.prg'),'--ino-sha256',D(W/'START.INO')])
asset=(P/'gate/START.RCV').read_bytes();assert asset[:2]==b'\0\x60';payload=asset[2:];assert 0<len(payload)<=8192
labels={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(W/'controller.labels').read_text().splitlines()if l.startswith('al ')}
gate={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P/'gate/gate.labels').read_text().splitlines()if l.startswith('al ')}
assert gate['_jg_dispatch']==labels['_d64_release_validate']and gate['_jg_home']==0x9000
capsule=bytearray(b'D64G\1\30')+len(payload).to_bytes(2,'little')+zlib.crc32(payload).to_bytes(4,'little')+(0x6000).to_bytes(2,'little')+gate['_jg_dispatch'].to_bytes(2,'little')+gate['_jg_home'].to_bytes(2,'little')+bytes(6)
assert len(capsule)==24
at=labels['_sj_gate_spec']-0x801+2;new=bytearray(old);new[at:at+24]=capsule
(W/'controller.prg').write_bytes(new);(W/'START.RCV').write_bytes(payload)
# Refresh matched binding against the final DATA-patched START; the relink must remain byte-exact.
run('GATE_FINAL_LINK',[P/'build_gate.py','--start-work',W,'--start-sha256',D(W/'controller.prg'),'--ino-sha256',D(W/'START.INO')])
assert(P/'gate/START.RCV').read_bytes()==asset and(W/'START.INO').read_bytes()==ino
s=importlib.util.spec_from_file_location('template',P/'dependencies/build_support/start_template_descriptor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
run('RECOVERY_WORKER',[P/'build_worker.py'])
rf=(P/'worker/ROLL.PRG').read_bytes();assert rf[:2]==b'\0\xa0' and len(rf)-2<=8192
rfbody=rf[2:];rfcap=b'D64F\1\20'+len(rfbody).to_bytes(2,'little')+zlib.crc32(rfbody).to_bytes(4,'little')+b'\0\xa0\0\xa0'
rfat=labels['_sr_worker_spec']-0x801+2;new[rfat:rfat+16]=rfcap
(W/'controller.prg').write_bytes(new);(W/'START.RFW').write_bytes(rfbody)
(W/'START.REL').write_bytes(m.make(bytes(new),(W/'controller.labels').read_text(),(W/'controller.map').read_text()))
(P/'COUPLED_RESULT.json').write_text(json.dumps({'status':'passed','START':D(W/'controller.prg'),'INO':D(W/'START.INO'),'RCV_payload':D(W/'START.RCV'),'RCV_disk_bytes':len(payload),'RCV_entry':gate['_jg_dispatch'],'patched_DATA_only':[at,at+24],'unpatched_START':hashlib.sha256(old).hexdigest(),'second_RCV_link_exact':True,'shared_prefix':gate['_jg_dispatch']-0x6000},indent=2)+'\n');print('Coupled native START/RCV',D(W/'controller.prg')[:8],len(payload))
