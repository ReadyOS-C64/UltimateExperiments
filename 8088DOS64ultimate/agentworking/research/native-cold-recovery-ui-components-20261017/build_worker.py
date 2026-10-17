from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;W=P/'worker';sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-worker-build');assert not Path(sys.pycache_prefix).exists()
import subprocess,json
L={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P/'work/controller.labels').read_text().splitlines()if l.startswith('al ')}
G={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P/'gate/gate.labels').read_text().splitlines()if l.startswith('al ')}
L.update({n:G[n]for n in ['_jg_recovery_copy']})
(W/'imports.s').write_text('\n'.join(('.exportzp 'if v<256 else '.export ')+n+'\n'+n+' = $%04x'%v for n,v in L.items()if not n.startswith('__') and not n.startswith('@'))+'\n')
commands=[['cc65','-t','none','-Oirs','--add-source','-D','D64_START_OPTIONS=1','-I',str(P/'work'),'-I',str(P/'gate'),'rollforward.c','-o','rollforward.s']]+[['ca65','-g',n+'.s','-o',n+'.o']for n in ['entry','rollforward','imports']]+[['ld65','-C','worker.cfg','-o','ROLL.PRG','-Ln','worker.labels','-m','worker.map','entry.o','rollforward.o','imports.o','/opt/homebrew/share/cc65/lib/none.lib']]
for i,c in enumerate(commands):
 r=subprocess.run(c,cwd=W,capture_output=True);(P/f'WORKER{i}.stdout').write_bytes(r.stdout);(P/f'WORKER{i}.stderr').write_bytes(r.stderr);assert r.returncode==0,(c,r.stderr.decode())
 if i==0:(W/'rollforward.s').write_text((W/'rollforward.s').read_text()+'\n.export _stage,_phase,_raw,_waiting,_position,_state,_error,_cleanup,_rename_start\n')
print((W/'worker.map').read_text().split('Segment list:')[1].split('Exports list')[0])

# Test-only bounded native polling fixture, outside release phase and loader.
Q={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(W/'worker.labels').read_text().splitlines()if l.startswith('al ')}
assert Q['__RF_BSS_RUN__']==0x9800 and Q['__RF_BSS_SIZE__']<=0x800
assert G['__RECOVER_BSS_RUN__']+G['__RECOVER_BSS_SIZE__']<=0x9800
assert len((W/'ROLL.PRG').read_bytes())<=8194
(W/'test_calls.inc').write_text('RF_POLL=$%04x\nRF_STATE=$%04x\n'%(Q['_rf_poll'],Q['_rf_state']))
subprocess.run(['ca65','-g','test_batch.s','-o','test_batch.o'],cwd=W,check=True)
subprocess.run(['ld65','-C','test_batch.cfg','-o','test_batch.bin','test_batch.o'],cwd=W,check=True)
