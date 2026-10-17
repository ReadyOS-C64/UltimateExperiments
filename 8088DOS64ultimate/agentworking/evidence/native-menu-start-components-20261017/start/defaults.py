from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;R=P.parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-default-cache');assert not Path(sys.pycache_prefix).exists()
import importlib.util,shutil,subprocess,json,hashlib
s=importlib.util.spec_from_file_location('start',R/'build_support/start_launcher.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);t=m.tools();records=[]
for profile in ['undefined','explicit0']:
 W=P/('default-fixed-'+profile);W.mkdir();m.sources(W,{},options=True);shutil.copyfile(P/'work/controller.c',W/'controller.c')
 with (P/('default-'+profile+'.stdout')).open('wb')as out,(P/('default-'+profile+'.stderr')).open('wb')as err:
  def command(argv,cwd):
   argv=list(map(str,argv))
   if profile=='explicit0'and argv[0]in [t['cc65'],t['ca65']]:argv[1:1]=['-D','D64_START_MODAL=0']
   env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
   for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
   subprocess.run(argv,cwd=cwd,env=env,stdout=out,stderr=err,check=True)
  m.command=command;m.build(W,t,options=True)
 got={n:hashlib.sha256((W/n).read_bytes()).hexdigest()for n in ['controller.prg','START.INO']}
 assert got=={'controller.prg':'79bb0470e830b9012eac1b87beddb14a5a005542f332c53b68ec7b4d3ddb34e8','START.INO':'eebb43aca1e12a67279b4b41d4b57d9b18d407f3e98dfeaadd9e5dc5f697459e'},got
 records.append({'profile':profile,'hashes':got,'exact':True})
(P/'DEFAULTS.json').write_text(json.dumps(records,indent=2)+'\n');print('Both default profiles reproduce public options START/INO')
