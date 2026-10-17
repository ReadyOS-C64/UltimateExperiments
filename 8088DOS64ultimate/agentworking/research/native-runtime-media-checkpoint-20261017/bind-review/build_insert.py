from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-build-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import subprocess,json,hashlib
p=P/'project';out=P/(sys.argv[1]if len(sys.argv)>1 else'build-insert');out.mkdir();env=dict(os.environ)
for k in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH','PYTHONPYCACHEPREFIX']:env.pop(k,None)
cmds=[('phase',['ca65','-g','-D','DOS64_MEDIA_BINDING=1','-D','DOS64_MEDIA_SEQUENCE=1','-D','DOS64_MEDIA_INSERT=1','transaction_wire.s','-o','transaction_wire.o']),('phase',['ld65','-C','plan.cfg','-o','transaction-wire.prg','-m','transaction-wire.map','-Ln','transaction-wire.labels','transaction_wire.o']),('binding',['cc65','-t','none','-O','-D','MB_INSERT=1','media_bind.c','-o','media_bind.s']),('binding',['ca65','-g','-D','MB_INSERT=1','glue.s','-o','glue.o']),('binding',['ca65','-g','media_bind.s','-o','media_bind.o']),('binding',['ld65','-C','insert.cfg','-o','binding.prg','-m','binding.map','-Ln','binding.labels','media_bind.o','glue.o','crc.o','/opt/homebrew/share/cc65/lib/none.lib'])]
# Match private native stage/broker labels from the selected runtime role.
N={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(p/'work/build/dos64.labels').read_text().splitlines()if x.startswith('al ')}
assert 'fixture_return'not in N,'runtime native product required'
(p/'phase/insert_native.inc').write_text(''.join('insert_'+n+'=$%04x\n'%N[n]for n in ['stage_drive','stage_flags','stage_mount','stage_content','stage_binding']))
B={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(p/'broker/broker.labels').read_text().splitlines()if x.startswith('al ')}
(p/'phase/insert_broker.inc').write_text('insert_broker_owner=$%04x\n'%B['native_owner'])
src={str(q.relative_to(p)):hashlib.sha256(q.read_bytes()).hexdigest()for root in ['phase','binding']for q in(p/root).glob('*')if q.suffix in ['.c','.s','.inc','.cfg','.h']};(out/'SOURCE.json').write_text(json.dumps(src,indent=2)+'\n')
for i,(root,c)in enumerate(cmds):
 r=subprocess.run(c,cwd=p/root,env=env,capture_output=True);(out/f'{i}.stdout').write_bytes(r.stdout);(out/f'{i}.stderr').write_bytes(r.stderr);print(i,r.returncode,r.stderr.decode());
 if r.returncode:raise SystemExit(r.returncode)
(out/'COMMANDS.json').write_text(json.dumps(cmds,indent=2)+'\n')
Q={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(p/'binding/binding.labels').read_text().splitlines()if x.startswith('al ')}
(p/'binding/insert-entry.inc').write_text('plan_init=$%04x\nplan_build=$%04x\n'%(Q['_mb_fixture_init'],Q['_mb_bind']))
for cmd in [['ca65','-g','insert_calls.s','-o','insert_calls.o'],['ld65','-C','../phase/worker-calls.cfg','-o','insert-calls.prg','-Ln','insert-calls.labels','-m','insert-calls.map','insert_calls.o']]:
 r=subprocess.run(cmd,cwd=p/'binding',env=env,capture_output=True);assert not r.returncode,r.stderr.decode()
for n in ['phase/transaction-wire.map','binding/binding.map']:
 print(n,(p/n).read_text().split('Segment list:',1)[1].split('Exports list',1)[0])
