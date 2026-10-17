from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-runtime-couple-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import argparse,json,hashlib,zlib,shutil,subprocess,importlib.util
ap=argparse.ArgumentParser();ap.add_argument('--runtime-cohort',type=Path,required=True);ap.add_argument('--runtime-project',default='project');ap.add_argument('--rebuild-runtime',action='store_true');a=ap.parse_args();R=a.runtime_cohort.resolve();W=P/'work';D=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not(P/'COUPLED_RUNTIME_RESULT.json').exists(),'one-shot output; use a fresh coupling workspace'
m=json.loads((R/'MANIFEST.json').read_text());entries=m['files']
for n,v in entries.items():assert D(R/n)==v['sha256'],n
src=(R/a.runtime_project).resolve();assert src.is_dir()and src.is_relative_to(R),'runtime source must be inside its sealed cohort'
prefix=str(src.relative_to(R))+'/'
expected={n[len(prefix):]for n in entries if n.startswith(prefix)}
actual={str(f.relative_to(src))for f in src.rglob('*')if f.is_file()and'__pycache__'not in f.parts}
assert expected==actual,'runtime source filename set differs from sealed manifest'
T=P/'runtime';assert not T.exists();shutil.copytree(src,T,ignore=shutil.ignore_patterns('__pycache__'))
env=dict(os.environ)
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
env['PYTHONDONTWRITEBYTECODE']='1'
def run(name,cmd,cwd=P):
 with(P/(name+'.stdout')).open('wb')as out,(P/(name+'.stderr')).open('wb')as err:r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=out,stderr=err)
 assert r.returncode==0,(name,r.returncode)
if a.rebuild_runtime:run('RUNTIME_SOURCE_BUILD',[sys.executable,'-B','build_ui_bridge.py','--role','runtime'],T)
# The selected runtime image is an actual independently linked role, never a UNIT alias.
for n in ['work/build/dos64.prg','work/build/dos64.labels','work/build/dos64.map','MODAL.MNU','HEADER.bin']:
 assert n in {str(Path(x).relative_to(a.runtime_project)) for x in entries if x.startswith(a.runtime_project+'/')}
 assert D(T/n)==D(src/n),(n,'runtime rebuild changed bound product')
s=importlib.util.spec_from_file_location('runtime_oracle',T/'role_oracle.py');mo=importlib.util.module_from_spec(s);s.loader.exec_module(mo);role=mo.verify('runtime')
main=(T/'work/build/dos64.prg').read_bytes();menu=(T/'MODAL.MNU').read_bytes();header=(T/'HEADER.bin').read_bytes();assert len(menu)==40960 and menu[:64]==header and len(header)==64 and menu[5]==1
assert main.count(header[8:24])==1
# Replacing inherited cold model source image, labels, map and exact sidecars is explicit.
old={}
for f in sorted((P/'inputs/build').glob('dos64*')):
 if f.is_file():old[f.name]=D(f)
shutil.copytree(P/'inputs/build',P/'old-runtime-inputs')
for f in(T/'work/build').glob('dos64*'):
 if f.is_file()and not f.name.startswith('dos64-tests'):shutil.copyfile(f,P/'inputs/build'/f.name)
(W/'DOS64.MNU').write_bytes(menu);(W/'modal-header.bin').write_bytes(header)
(W/'modal_capsule.s').write_text('.export _sm_modal_spec,_sm_modal_header\n.segment "DATA"\n_sm_modal_spec:\n.byte "D64M",1,16\n.word %d\n.dword %d\n.dword $3da000\n_sm_modal_header:\n.incbin "modal-header.bin"\n'%(len(menu),zlib.crc32(menu)))
run('COLD_COUPLE',[sys.executable,'-B',P/'couple.py'])
labels={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(W/'controller.labels').read_text().splitlines()if l.startswith('al ')}
start=(W/'controller.prg').read_bytes();ino=(W/'START.INO').read_bytes();assert len(start)==20480 and 0x801+len(start)-3==0x57fe and labels['_lc_control']-0x801+2==19555
at=labels['_sm_modal_spec']-0x801+2;assert start[at:at+16]==b'D64M\1\20'+len(menu).to_bytes(2,'little')+zlib.crc32(menu).to_bytes(4,'little')+(0x3da000).to_bytes(4,'little');assert start[at+16:at+80]==header
for sym,magic,count,file in [('_sj_gate_spec',b'D64G\1\30',24,'START.RCV'),('_sr_worker_spec',b'D64F\1\20',16,'START.RFW')]:
 q=labels[sym]-0x801+2;cap=start[q:q+count];b=(W/file).read_bytes();assert cap[:6]==magic and int.from_bytes(cap[6:8],'little')==len(b)and int.from_bytes(cap[8:12],'little')==zlib.crc32(b)
record={'passed':True,'runtime_parent_manifest':D(R/'MANIFEST.json'),'runtime_role':role,'old_runtime_inputs':old,'new_runtime_source_rebuilt':a.rebuild_runtime,'runtime':{'sha256':D(T/'work/build/dos64.prg'),'MNU':D(W/'DOS64.MNU'),'header':header.hex(),'menu_crc':zlib.crc32(menu)},'cold':{n:{'sha256':D(W/n),'bytes':(W/n).stat().st_size}for n in ['controller.prg','controller.labels','controller.map','START.INO','START.REL','START.RCV','START.RFW','DOS64.REL']},'last_source_byte':0x57fe,'control_file_offset':19555,'scope':'source-bound runtime role/header/wholefile coupling and fresh RCV prefix/RFW imports. No execution acceptance from this builder alone.'}
(P/'COUPLED_RUNTIME_RESULT.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
