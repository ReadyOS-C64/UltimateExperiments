from pathlib import Path
import subprocess,hashlib,json,os,sys
P=Path.cwd();out=P/(sys.argv[1]if len(sys.argv)>1 else'default-final');out.mkdir();W=P/'project';base=P.parent/'cold-runtime-media-controls-20261017/runtime';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
for name,flag in [('undefined',[]),('zero',['-D','DOS64_MEDIA_INSERT=0'])]:
 d=out/name;d.mkdir();cmds=[(['ca65','-g','-D','DOS64_MEDIA_BINDING=1','-D','DOS64_MEDIA_SEQUENCE=1',*flag,'transaction_wire.s','-o',str(d/'wire.o')],W/'phase'),(['ld65','-C','plan.cfg','-o',str(d/'wire.prg'),str(d/'wire.o')],W/'phase'),(['cc65','-t','none','-O',*(['-D','MB_INSERT=0']if flag else[]),'media_bind.c','-o',str(d/'bind.s')],W/'binding'),(['ca65','-g',str(d/'bind.s'),'-o',str(d/'bind.o')],W/'binding'),(['ca65','-g',*(['-D','MB_INSERT=0']if flag else[]),'glue.s','-o',str(d/'glue.o')],W/'binding'),(['ld65','-C','../phase/plan.cfg','-o',str(d/'bind.prg'),str(d/'bind.o'),str(d/'glue.o'),'crc.o','/opt/homebrew/share/cc65/lib/none.lib'],W/'binding')]
 for i,(c,cwd)in enumerate(cmds):
  r=subprocess.run(c,cwd=cwd,capture_output=True);(d/f'{i}.err').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode()
 for f,old in [('wire.prg','phase/transaction-wire.prg'),('bind.prg','binding/binding.prg')]:assert(d/f).read_bytes()==(base/old).read_bytes(),(name,f,sha(d/f),sha(base/old))
 records.append({'profile':name,'WIRE':sha(d/'wire.prg'),'BIND':sha(d/'bind.prg'),'exact_c866':True})
(out/'RESULT.json').write_text(json.dumps({'passed':True,'profiles':records},indent=2)+'\n');print(records)
