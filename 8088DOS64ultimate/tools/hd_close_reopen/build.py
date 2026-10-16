#!/usr/bin/env python3
"""Build default-disabled standalone target2 CLOSE/reopen helper from actual native sources."""
from pathlib import Path
import subprocess,json,hashlib,sys
H=Path(__file__).resolve().parent;W=H.parents[1];B=W/'build/hd_close_reopen'
if H!=W/'tools/hd_close_reopen' or not (W/'src/files.s').is_file():raise RuntimeError('Expected project helper layout')
B.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
items=[('helper',H/'close_reopen.s',[]),*[(n,W/'src'/(n+'.s'),['-D','DOS64_FILES_INFO=1'] if n=='files' else []) for n in ['files','uci','host_clock','elapsed']]]
files=[Path(__file__).resolve(),H/'link.cfg',*[src for _,src,_ in items],*sorted((W/'include').glob('*.inc'))]
pins={str(f):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in files}
commands=[]
for n,src,flags in items:
 cmd=['ca65','-g',*flags,'-I',str(W/'include'),'-o',str(B/(n+'.o')),str(src)];commands.append(cmd);subprocess.run(cmd,cwd=W,check=True)
cmd=['ld65','-C',str(H/'link.cfg'),'-o',str(B/'close-reopen.prg'),'-m',str(B/'close-reopen.map'),'-Ln',str(B/'close-reopen.labels'),*[str(B/(n+'.o')) for n,_,_ in items]];commands.append(cmd);subprocess.run(cmd,cwd=W,check=True)
for f in files:
 if sha(f)!=pins[str(f)]['sha256']:raise RuntimeError('Helper build input changed: '+str(f))
r={'schema':1,'hardware_executed':False,'default_disabled':True,'target':2,'readonly_reopen':True,'never_writes_disk_or_REU':True,'inputs':pins,'commands':commands,'cwd':str(W),'prg_sha256':sha(B/'close-reopen.prg'),'labels_sha256':sha(B/'close-reopen.labels')}
(B/'source-manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'prg_sha256':r['prg_sha256'],'labels_sha256':r['labels_sha256']}))
