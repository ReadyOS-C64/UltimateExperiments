from pathlib import Path
import sys,os,subprocess,json,hashlib,shutil
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True
def labels(p):return{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
N=labels(P/'work/build/dos64.labels');B=labels(P/'broker/broker.labels')
assert 'fixture_return'not in N,'Insert component requires actual runtime aliases'
(P/'phase/insert_native.inc').write_text(''.join('insert_'+n+'=$%04x\n'%N[n]for n in ['stage_drive','stage_flags','stage_mount','stage_content','stage_binding']))
(P/'phase/insert_broker.inc').write_text('insert_broker_owner=$%04x\n'%B['native_owner'])
D=P/'insert-binding';D.mkdir(exist_ok=True)
for n in ['media_bind.c','media_bind.h','semantic.inc','glue.s','insert.cfg','insert_calls.s','broker.inc']:shutil.copyfile(P/'binding'/n,D/n)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for k in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH','PYTHONPYCACHEPREFIX']:env.pop(k,None)
commands=[]
def run(root,a):
 a=list(map(str,a));r=subprocess.run(a,cwd=P/root,env=env,capture_output=True);i=len(commands);(P/f'INSERT_BUILD{i:02}.stdout').write_bytes(r.stdout);(P/f'INSERT_BUILD{i:02}.stderr').write_bytes(r.stderr);commands.append({'cwd':root,'argv':a,'exit':r.returncode});(P/'INSERT_BUILD_COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,(a,r.stderr.decode())
run('phase',['ca65','-g','-D','DOS64_MEDIA_BINDING=1','-D','DOS64_MEDIA_SEQUENCE=1','-D','DOS64_MEDIA_INSERT=1','transaction_wire.s','-o','transaction_wire.o'])
run('phase',['ld65','-C','plan.cfg','-o','transaction-wire.prg','-m','transaction-wire.map','-Ln','transaction-wire.labels','transaction_wire.o'])
run('insert-binding',['cc65','-t','none','-O','-D','MB_INSERT=1','media_bind.c','-o','media_bind.s'])
for n in ['media_bind','glue']:run('insert-binding',['ca65','-g','-D','MB_INSERT=1',n+'.s','-o',n+'.o'])
run('insert-binding',['ca65','-g','../phase/crc.s','-o','crc.o'])
run('insert-binding',['ld65','-C','insert.cfg','-o','binding.prg','-m','binding.map','-Ln','binding.labels','media_bind.o','glue.o','crc.o',os.environ['DOS64_CC65_LIB']])
Q=labels(D/'binding.labels');(D/'insert-entry.inc').write_text('plan_init=$%04x\nplan_build=$%04x\n'%(Q['_mb_fixture_init'],Q['_mb_bind']))
run('insert-binding',['ca65','-g','insert_calls.s','-o','insert_calls.o'])
run('insert-binding',['ld65','-C','../phase/worker-calls.cfg','-o','insert-calls.prg','-m','insert-calls.map','-Ln','insert-calls.labels','insert_calls.o'])
result={n:{'sha256':hashlib.sha256((P/n).read_bytes()).hexdigest(),'bytes':(P/n).stat().st_size}for n in ['phase/transaction-wire.prg','binding/binding.prg','insert-binding/binding.prg','insert-binding/insert-support.prg','insert-binding/insert-calls.prg']}
(P/'INSERT_BUILD_RESULT.json').write_text(json.dumps({'products':result,'scope':'runtime Insert-enabled WIRE plus distinct Save and Insert BIND/support/wrappers'},indent=2)+'\n')
print(json.dumps(result,indent=2))
