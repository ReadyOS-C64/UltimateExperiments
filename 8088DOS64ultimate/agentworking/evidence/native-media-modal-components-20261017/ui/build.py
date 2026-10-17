from pathlib import Path
import os,shutil,subprocess,json,hashlib,sys
r=Path(__file__).resolve().parent;os.chdir(r)
tools={n:Path(shutil.which(n)).resolve()for n in ['cc65','ca65','ld65']};tools['library']=Path('/opt/homebrew/share/cc65/lib/none.lib')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');[env.pop(k,None)for k in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH']]
commands=[]
def run(args):
 commands.append([str(x)for x in args]);p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE);Path('build-'+str(len(commands))+'.stdout').write_bytes(p.stdout);Path('build-'+str(len(commands))+'.stderr').write_bytes(p.stderr)
 if p.returncode:raise RuntimeError((commands[-1],p.stderr.decode(errors='replace')))
for n in ['panel','platform']:
 run([tools['cc65'],'-t','none','-Oirs','-I.',n+'.c','-o',n+'.s']);run([tools['ca65'],'-g',n+'.s','-o',n+'.o'])
for n in ['scan','header']:run([tools['ca65'],'-g',n+'.s','-o',n+'.o'])
run([tools['ld65'],'-C','panel.cfg','-o','panel.prg','-m','panel.map','-Ln','panel.labels','panel.o','platform.o','scan.o','header.o',tools['library']])
Path('COMMANDS.json').write_text(json.dumps({'tools':{n:{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for n,f in tools.items()},'commands':commands},indent=2)+'\n')
print(hashlib.sha256(Path('panel.prg').read_bytes()).hexdigest())
