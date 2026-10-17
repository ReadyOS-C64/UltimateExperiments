from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-iw-defaults');assert not Path(sys.pycache_prefix).exists()
import shutil,json,hashlib,subprocess
D=P/'default-controls';assert not D.exists();D.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(P/'.absent-iw-default-cache'))
for n in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH']:env.pop(n,None)
expected=(P/'default-expected/dos64.prg').read_bytes();records=[]
for role in ['old','undefined','zero']:
 W=D/role;shutil.copytree(P/'work',W,ignore=shutil.ignore_patterns('build','third_party','tests','__pycache__','.zig-cache','zig-out'))
 if role=='old':
  shutil.copyfile(P/'default-expected/src/floppy_control.s',W/'src/floppy_control.s');shutil.copyfile(P/'default-expected/src/disk.inc',W/'include/disk.inc')
 flags=['DOS64_MODAL_MENU=0','DOS64_SAVE_HD_CONTEXT=0','DOS64_EXPORT_CRC=0','DOS64_SAVE_MODAL=0']
 if role!='undefined':flags+=['DOS64_MEDIA_BINDING=0']
 a=[shutil.which('make'),'build/dos64.prg',*flags];r=subprocess.run(a,cwd=W,env=env,capture_output=True);(D/(role+'.stdout')).write_bytes(r.stdout);(D/(role+'.stderr')).write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode();actual=(W/'build/dos64.prg').read_bytes();assert actual==expected,role
 records.append({'profile':role,'argv':a,'bytes':len(actual),'sha256':hashlib.sha256(actual).hexdigest(),'exact_parent_default':True})
(D/'RESULT.json').write_text(json.dumps({'passed':True,'records':records,'worker_is_standalone_not_in_default_graph':True},indent=2)+'\n');print((D/'RESULT.json').read_text())
