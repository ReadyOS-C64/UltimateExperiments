from pathlib import Path
import subprocess,shlex,tempfile,json,importlib.util,hashlib,re
P=Path(__file__).parent/'project';R=Path(__file__).parent/'package-controls';R.mkdir(exist_ok=False)
line=next(s for s in(Path(__file__).parent/'fourth-build.stdout').read_text().splitlines()if s.startswith('python3 build_support/overlay_package.py --resident-prg build/dos64-resident.prg '));base=shlex.split(line);rows=[]
def run(n,change,ok=False):
 d=R/n;d.mkdir();cmd=base[:]
 for k,file in [('--output-prg','out.prg'),('--output-assets','assets.bin'),('--manifest','package.json')]:cmd[cmd.index(k)+1]=str(d/file)
 change(cmd,d)
 q=subprocess.run(cmd,cwd=P,capture_output=True);(d/'stdout').write_bytes(q.stdout);(d/'stderr').write_bytes(q.stderr);assert(q.returncode==0)==ok,(n,q.returncode,q.stderr.decode());assert ok or not any((d/f).exists()for f in ['out.prg','assets.bin','package.json']);rows.append({'case':n,'passed':True,'exit':q.returncode,'no_rejected_outputs':not ok})
run('paired',lambda c,d:None,True)
def omit(c,d):i=c.index('--cpu-trap');del c[i:i+2]
run('missing_payload',omit)
def badpayload(data):
 def f(c,d):p=d/'trap.bin';p.write_bytes(data);c[c.index('--cpu-trap')+1]=str(p)
 return f
trap=(P/'build/dos64-resident.prg.trap.bin').read_bytes()
run('short_payload',badpayload(trap[:-1]));run('oversized_payload',badpayload(bytes(257)))
def badlabel(c,d):
 p=d/'labels';s=(P/c[c.index('--labels')+1]).read_text();s,n=re.subn(r'(?m)^al 00FE00 (\.__CPUTRAP_RUN__)$',r'al 00FF00 \1',s);assert n==1;p.write_text(s);c[c.index('--labels')+1]=str(p)
run('vector_page_target',badlabel)
spec=importlib.util.spec_from_file_location('vm',P/'build_support/verify_memory.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
b=P/'build';m=(b/'dos64.map').read_text();l=(b/'dos64.labels').read_text();prg=(b/'dos64.prg').read_bytes()
payload={n:(b/f'dos64-resident.prg.{ext}.bin').read_bytes()for n,ext in [('FILECODE','files'),('RENDERCODE','render'),('INPUTCODE','input'),('IRQMAIN','pit'),('GFXCODE','gfx'),('HDCODE','hd'),('DISKCODE','disk')]}
args=[m,l,prg,payload,(b/'dos64-resident.prg.import.bin').read_bytes(),(b/'dos64-resident.prg.hdb.bin').read_bytes(),(b/'dos64-resident.prg.saver.bin').read_bytes(),None,trap]
report=v.verify(*args);assert not report['errors'];rows.append({'case':'memory_exact','passed':True})
for n,offset in [('changed_trap_source',0xae00),('changed_zero_tail',0xaf00)]:
 a=args[:];data=bytearray(prg);data[offset-0x801+2]^=1;a[2]=bytes(data);r=v.verify(*a);assert r['errors'];(R/(n+'.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append({'case':n,'passed':True,'refused':r['errors']})
a=args[:];a[-1]=None;r=v.verify(*a);assert r['errors'];rows.append({'case':'memory_unpaired','passed':True,'refused':r['errors']})
(R/'RESULT.json').write_text(json.dumps({'passed':True,'groups':rows,'target_sha256':hashlib.sha256(prg).hexdigest()},indent=2)+'\n');print(len(rows),'groups PASS')
