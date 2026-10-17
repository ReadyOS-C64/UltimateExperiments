from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-finish-builder');assert not Path(sys.pycache_prefix).exists()
import subprocess,json,shutil,hashlib,argparse
ap=argparse.ArgumentParser();ap.add_argument("--role",choices=["unit","runtime"],default="unit");role=ap.parse_args().role
native="dos64"if role=="runtime"else"dos64-tests"
S=lambda p:{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
N=S(P/'work/build'/(native+'.labels'));B=S(P/'broker/broker.labels');D=P/'finish';text=''.join(n+'=$%04x\n'%v for n,v in N.items()if n.startswith(('dos64_','hd_','hdb_','hdc_','sav_')))
text+=''.join('broker_'+n+'=$%04x\n'%B[n]for n in ['native_owner','presentation_owner','saved_files','saved_hd','saved_hdb','saved_online','saved_target']);(D/'imports.inc').write_text(text)
commands=[];env=dict(os.environ)
for n in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
for a in [['ca65','-g','finish.s','-o','finish.o'],['ld65','-C','finish.cfg','-o','finish.prg','-m','finish.map','-Ln','finish.labels','finish.o']]:
 r=subprocess.run(a,cwd=D,env=env,capture_output=True);i=len(commands);(P/f'FINISH_BUILD{i}.stdout').write_bytes(r.stdout);(P/f'FINISH_BUILD{i}.stderr').write_bytes(r.stderr);commands.append({'argv':a,'exit':r.returncode});assert r.returncode==0,r.stderr.decode()
print((D/'finish.map').read_text().split('Segment list:')[1].split('Exports list')[0]);(P/'FINISH_BUILD.json').write_text(json.dumps({'commands':commands,'role':role,'native':hashlib.sha256((P/'work/build'/(native+'.prg')).read_bytes()).hexdigest(),'broker':hashlib.sha256((P/'broker/broker.prg').read_bytes()).hexdigest()},indent=2)+'\n')
