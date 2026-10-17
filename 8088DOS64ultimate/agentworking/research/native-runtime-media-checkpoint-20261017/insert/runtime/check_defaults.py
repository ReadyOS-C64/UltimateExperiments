from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-default-check');assert not Path(sys.pycache_prefix).exists()
import shutil,hashlib,json,subprocess
O=P/'upstream-default';D=P/'default-controls';assert not D.exists();D.mkdir();records=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(P/'.absent-default-native-cache'))
for n in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH']:env.pop(n,None)
def info(p):return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
# Compare actual old/new code using the SAME selected runtime aliases.
# Absolute UNIT WIRE bytes are not a relocation-invariant oracle.
old=[['ca65','-g','-I',str(P/'phase'),'-D','DOS64_MEDIA_BINDING=1',str(O/'phase/old_transaction_wire.s'),'-o',str(D/'old-runtime.o')],['ld65','-C','plan.cfg','-o',str(D/'old-runtime.prg'),str(D/'old-runtime.o')]]
for a in old:
 r=subprocess.run(a,cwd=P/'phase',env=env,capture_output=True);assert r.returncode==0,r.stderr.decode()
expected=(D/'old-runtime.prg').read_bytes();(D/'expected-wire.prg').write_bytes(expected)
for mode,defs in [('undefined',[]),('zero',['-D','DOS64_MEDIA_SEQUENCE=0'])]:
 commands=[['ca65','-g','-D','DOS64_MEDIA_BINDING=1',*defs,'transaction_wire.s','-o',str(D/(mode+'.o'))],['ld65','-C','plan.cfg','-o',str(D/(mode+'.prg')),str(D/(mode+'.o'))]]
 for a in commands:
  r=subprocess.run(a,cwd=P/'phase',env=env,capture_output=True);assert r.returncode==0,r.stderr.decode()
 assert (D/(mode+'.prg')).read_bytes()==expected,mode
 records.append({'profile':mode,'WIRE_exact':True,**info(D/(mode+'.prg'))})
for role in ['old-header','new-header']:
 W=D/role;shutil.copytree(P/'work',W,ignore=shutil.ignore_patterns('build','third_party','tests','__pycache__','.zig-cache','zig-out'))
 if role=='old-header':shutil.copyfile(O/'work/include/modal_assets.inc',W/'include/modal_assets.inc')
 a=['make','build/dos64.prg','DOS64_MODAL_MENU=0','DOS64_SAVE_HD_CONTEXT=0','DOS64_EXPORT_CRC=0','DOS64_SAVE_MODAL=0','DOS64_MEDIA_BINDING=0'];r=subprocess.run(a,cwd=W,env=env,capture_output=True);(D/(role+'.stdout')).write_bytes(r.stdout);(D/(role+'.stderr')).write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode();records.append({'profile':role,**info(W/'build/dos64.prg')})
assert(D/'old-header/build/dos64.prg').read_bytes()==(D/'new-header/build/dos64.prg').read_bytes()
(D/'RESULT.json').write_text(json.dumps({'passed':True,'WIRE_undefined_zero_exact_parent':True,'native_default_unchanged_by_new_tag':True,'records':records},indent=2)+'\n');print((D/'RESULT.json').read_text())
