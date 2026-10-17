from pathlib import Path
import subprocess,sys,json,hashlib
P=Path.cwd();assert P.name=='native-media-live-binding-clock-successor-20261017';D=P/'binding';B=P/'broker';cmds=[]
S={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(B/'broker.labels').read_text().splitlines()if x.startswith('al ')}
(D/'broker.inc').write_text(''.join('broker_'+a+'=$%04x\n'%S[b]for a,b in [('owned','modal_owned'),('context','modal_context'),('files','saved_files'),('hd','saved_hd'),('hdb','saved_hdb'),('online','saved_online'),('target','saved_target')]))
def run(a):
 r=subprocess.run(a,cwd=D,capture_output=True);i=len(cmds);(D/f'{i}.stdout').write_bytes(r.stdout);(D/f'{i}.stderr').write_bytes(r.stderr);cmds.append({'argv':a,'exit':r.returncode});(P/'BIND_BUILD.json').write_text(json.dumps(cmds,indent=2));assert not r.returncode,(a,r.stderr.decode())
run(['cc65','-t','none','-O','media_bind.c','-o','media_bind.s'])
for n in ['media_bind','glue']:run(['ca65','-g',n+'.s','-o',n+'.o'])
run(['ca65','-g','../phase/crc.s','-o','crc.o'])
run(['ld65','-C','../phase/plan.cfg','-o','binding.prg','-m','binding.map','-Ln','binding.labels','media_bind.o','glue.o','crc.o','/opt/homebrew/share/cc65/lib/none.lib'])
L={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(D/'binding.labels').read_text().splitlines()if x.startswith('al ')}
(D/'plan-entry.inc').write_text('plan_init=$%04x\nplan_build=$%04x\n'%(L['_mb_fixture_init'],L['_mb_bind']))
(D/'worker_calls.s').write_text((P/'phase/worker_calls.s').read_text())
run(['ca65','-g','worker_calls.s','-o','worker_calls.o']);run(['ld65','-C','../phase/worker-calls.cfg','-o','binding-calls.prg','-m','binding-calls.map','-Ln','binding-calls.labels','worker_calls.o'])
print((D/'binding.map').read_text().split('Segment list:')[1].split('Exports list')[0])
print(hashlib.sha256((D/'binding.prg').read_bytes()).hexdigest())
