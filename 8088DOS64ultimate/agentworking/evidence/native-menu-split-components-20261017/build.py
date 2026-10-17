from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;W=P/'work';R=P.parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-build-cache');assert not Path(sys.pycache_prefix).exists()
import importlib.util,subprocess,json,zlib,hashlib
s=importlib.util.spec_from_file_location('start',R/'build_support/start_launcher.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
t=m.tools();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
commands=[]
with(P/'BUILD.stdout').open('wb')as out,(P/'BUILD.stderr').open('wb')as err:
 def command(argv,cwd):
  argv=list(map(str,argv));commands.append(argv)
  # Additional fixed cold asset capsule participates in the normal START link.
  if argv[0]==t['ld65']:
   subprocess.run([t['ca65'],'-g','modal_capsule.s','-o','modal_capsule.o'],cwd=W,env=env,stdout=out,stderr=err,check=True)
   argv.insert(-1,'modal_capsule.o')
  if argv[0]in [t['cc65'],t['ca65']]:argv[1:1]=['-D','D64_START_MODAL=1']
  subprocess.run(argv,cwd=cwd,env=env,stdout=out,stderr=err,check=True)
  if argv[0]==t['cc65']and 'controller.c'in argv:
   q=W/'controller.s';q.write_text(q.read_text()+'\n.export _modal_copy,_modal_ready\n')
 m.command=command;m.build(W,t,options=True)
for name,file in [('descriptor','setup_release_descriptor.py'),('template','start_template_descriptor.py')]:
 s=importlib.util.spec_from_file_location(name,R/'build_support'/file);mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)
 if name=='descriptor':(W/'DOS64.REL').write_bytes(mod.descriptor((P/'inputs/build/dos64.prg').read_bytes(),(P/'inputs/build/dos64.labels').read_text(),options=True))
 else:(W/'START.REL').write_bytes(mod.make((W/'controller.prg').read_bytes(),(W/'controller.labels').read_text(),(W/'controller.map').read_text()))
(P/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n')
print('START bytes',len((W/'controller.prg').read_bytes()),'INO',len((W/'START.INO').read_bytes()))
