from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-iw-build');assert not Path(sys.pycache_prefix).exists()
import json,hashlib,shutil,subprocess,re
L=lambda f:{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in f.read_text().splitlines()if l.startswith('al ')}
N=L(P/'work/build/dos64.labels');B=L(P/'broker/broker.labels');w=P/'worker';names=[n for n in N if n.startswith(('dos64_','hdb_','hd_','hdc_','sav_'))]+['stage_drive','stage_flags','stage_mount','stage_content']
(w/'imports.inc').write_text(''.join(n+'=$%04x\n'%N[n]for n in names)+''.join('broker_'+n+'=$%04x\n'%B[n]for n in ['native_owner','presentation_owner','saved_files','saved_hd','saved_hdb']))
# Generate geometry directly from this exact native COMMIT validator source.
core=(P/'work/src/floppy_control.s').read_text();tables={}
for label in ['ctl_bpb_offsets','ctl_bpb_values']:
 values=[int(t.strip()[1:],16)if t.strip().startswith('$')else int(t.strip())for t in re.search(r'^'+label+r':\s*\.byte([^\n]+)',core,re.M).group(1).split(',')];assert len(values)==12;tables[label]=values
(w/'geometry.inc').write_text('iw_bpb_offsets:.byte '+','.join(map(str,tables['ctl_bpb_offsets']))+'\niw_bpb_values:.byte '+','.join(map(str,tables['ctl_bpb_values']))+'\n')
(P/'GEOMETRY_SOURCE.json').write_text(json.dumps({'core_sha256':hashlib.sha256((P/'work/src/floppy_control.s').read_bytes()).hexdigest(),'tables':tables},indent=2)+'\n')
env=dict(os.environ)
for n in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
cmds=[]
for a in [[shutil.which('ca65'),'-g','incoming.s','-o','incoming.o'],[shutil.which('ld65'),'-C','incoming.cfg','-o','incoming.prg','-m','incoming.map','-Ln','incoming.labels','incoming.o']]:
 r=subprocess.run(a,cwd=w,env=env,capture_output=True);i=len(cmds);(P/f'IW_BUILD{i}.stdout').write_bytes(r.stdout);(P/f'IW_BUILD{i}.stderr').write_bytes(r.stderr);cmds.append({'argv':a,'exit':r.returncode});assert not r.returncode,r.stderr.decode()
(P/'IW_BUILD.json').write_text(json.dumps({'commands':cmds,'native':hashlib.sha256((P/'work/build/dos64.prg').read_bytes()).hexdigest(),'worker':hashlib.sha256((w/'incoming.prg').read_bytes()).hexdigest(),'bytes':(w/'incoming.prg').stat().st_size},indent=2)+'\n');print((w/'incoming.map').read_text().split('Segment list:')[1].split('Exports list')[0])
