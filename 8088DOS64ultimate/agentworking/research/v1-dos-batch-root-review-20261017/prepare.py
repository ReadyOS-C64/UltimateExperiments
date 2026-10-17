from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-prepare');assert not Path(sys.pycache_prefix).exists()
import shutil,json,hashlib,struct,importlib.util
ROOT=P.parents[2];Q=P.parent/'v1-final-public-producer-consumer-20261017';T=P.parent/'v1-turbo-current-cold-20261017'
def ident(p):d=p.read_bytes();return {'sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d)}
origins={}
def cp(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b);assert ident(a)==ident(b);origins[str(b.resolve())]={'origin':str(a.resolve()),**ident(a)}
for folder in ['start','project']:
 for p in(T/folder).rglob('*'):
  if p.is_file()and'__pycache__'not in p.parts:cp(p,P/folder/p.relative_to(T/folder))
for p in(Q/'work').iterdir():
 if p.is_file()and(p.suffix in['.py','.prg','.labels','.map','.INO','.RCV','.RFW','.REL']):cp(p,P/'start'/p.name)
# Keep source-built450 model with v1_call/ticks/ram wrappers; never substitute an old native product.
cp(T/'start/journal-peddle.dylib',P/'start/journal-peddle.dylib')
for p in(Q/'inputs/build').iterdir():cp(p,P/'inputs/build'/p.name)
for p in(Q/'gate').iterdir():cp(p,P/'gate'/p.name)
for a,b in [('broker-runtime','broker'),('ui','ui'),('bridge','bridge')]:
 for p in(Q/'runtime'/a).rglob('*'):
  if p.is_file():cp(p,P/'runtime'/b/p.relative_to(Q/'runtime'/a))
for p in(Q/'setup/full-output').iterdir():cp(p,P/'published'/p.name)
for p in(Q/'config-real/published-40').iterdir():cp(p,P/'published40'/p.name)
for n in['A.IMG','B.IMG','C.IMG']:cp(Q/'setup/full-output'/n,P/'media'/n)
cp(T/'v1_lane.py',P/'v1_lane.py');cp(T/'run_current.py',P/'finish_helpers.py')
# Independent input fixture: only these host-supplied batch programs are added.
# All files under test must be created by their genuine DOS execution.
main=r'''@ECHO OFF
C:
CD \
DATE 10-17-1988
TIME 12:34:56
ECHO BEGIN>C:\V1.LOG
VOL >>C:\V1.LOG
MD V1WORK
CD V1WORK
ECHO ALPHA>ORIG.TXT
ECHO BETA>>ORIG.TXT
COPY /B C:\DOS\COMMAND.COM BIN.DAT >COPYBIN.LOG
TYPE NUL>EMPTY.DAT
COPY ORIG.TXT T1.TXT >COPY1.LOG
COPY ORIG.TXT T2.TXT >COPY2.LOG
REN T1.TXT KEEP.TXT
IF EXIST KEEP.TXT ECHO REN_OK>>C:\V1.LOG
COPY T?.TXT WCOPY.TXT >COPYWILD.LOG
DEL T?.TXT
IF NOT EXIST T2.TXT ECHO WILD_OK>>C:\V1.LOG
COPY KEEP.TXT TD1.TXT >NUL
COPY KEEP.TXT TD2.TXT >NUL
DEL TD?.TXT
IF NOT EXIST TD1.TXT IF NOT EXIST TD2.TXT ECHO WILD2_OK>>C:\V1.LOG
ATTRIB +R KEEP.TXT
ATTRIB KEEP.TXT >ATRO.LOG
DEL KEEP.TXT >RO.LOG
IF EXIST KEEP.TXT ECHO RO_OK>>C:\V1.LOG
ATTRIB -R KEEP.TXT
ATTRIB KEEP.TXT >ATWR.LOG
SET V1VAR=BATCHVALUE
ECHO %V1VAR%>ENV.TXT
PROMPT V1$N$G
ECHO %PROMPT%>PROMPT.TXT
FOR %%F IN (ONE TWO THREE) DO ECHO %%F>>FOR.TXT
GOTO SKIP
ECHO BAD>BAD.TXT
:SKIP
CALL C:\V1SUB.BAT FIRST SECOND
ECHO CALL_BACK>>C:\V1.LOG
C:\DOS\COMMAND.COM /C ECHO CHILD_OK>CMD.TXT
C:\DOS\COMMAND.COM /C C:\V1EXIT.BAT
C:\DOS\FIND.EXE "ALPHA" ORIG.TXT >FIND.LOG
IF ERRORLEVEL 1 GOTO FAIL
ECHO ERRORLEVEL0_OK>>C:\V1.LOG
C:\DOS\FIND.EXE "ABSENT" ORIG.TXT >NOMATCH.LOG
ECHO N RET1.COM>DEBUG.INP
ECHO E 100 B8 01 4C CD 21>>DEBUG.INP
ECHO RCX>>DEBUG.INP
ECHO 5>>DEBUG.INP
ECHO W>>DEBUG.INP
ECHO Q>>DEBUG.INP
C:\DOS\DEBUG.COM <DEBUG.INP >DEBUG.LOG
RET1.COM
IF ERRORLEVEL 1 ECHO ERRORLEVEL1_OK>>C:\V1.LOG
MD SUB
CD SUB
ECHO NESTED>DEEP.TXT
CD ..
CD \
MD EMPTY
RD EMPTY
IF NOT EXIST EMPTY ECHO RD_OK>>C:\V1.LOG
ECHO COMPLETE>C:\V1DONE.TXT
ECHO V1_BATCH_COMPLETE
PROMPT $N$G
GOTO END
:FAIL
ECHO BAD_ERRORLEVEL>C:\V1FAIL.TXT
PROMPT $N$G
:END
'''
sub=r'''@ECHO OFF
ECHO %1>C:\V1WORK\ARGS.TXT
SHIFT
ECHO %1>>C:\V1WORK\ARGS.TXT
REM The following marker requires return to the parent batch.
ECHO SUB_OK>>C:\V1.LOG
'''
ex=r'''@ECHO OFF
ECHO EXIT_OK>C:\V1WORK\EXIT.TXT
EXIT
ECHO BAD>C:\V1WORK\EXITBAD.TXT
'''
batches={n:s.replace('\n','\r\n').encode('ascii')for n,s in[('V1TEST.BAT',main),('V1SUB.BAT',sub),('V1EXIT.BAT',ex)]}
for n,b in batches.items():(P/n).write_bytes(b)
spec=importlib.util.spec_from_file_location('independent_fat',P/'project/build_support/dos_disk_inspect.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
raw=(P/'media/C.IMG').read_bytes();data=bytearray(raw);offset=8192;v=mod.Volume(raw[offset:]);root=offset+v.root_sector*512;free=[c for c in range(2,v.clusters+2)if v.entry(c)==0];slots=[a for a in range(root,root+v.bpb['root_entries']*32,32)if data[a]in[0,0xe5]];cb=v.spc*512
assert v.width==12 and len(slots)>=len(batches)
for (name,b),at in zip(batches.items(),slots):
 chain=free[:(len(b)+cb-1)//cb];del free[:len(chain)]
 for i,c in enumerate(chain):
  val=chain[i+1]if i+1<len(chain)else 0xfff
  for mirror in range(2):
   base=offset+(v.bpb['reserved_sectors']+mirror*v.bpb['sectors_per_fat'])*512;pos=base+c*3//2;old=int.from_bytes(data[pos:pos+2],'little');word=(old&15)|(val<<4)if c&1 else(old&0xf000)|val;struct.pack_into('<H',data,pos,word)
  begin=offset+(v.data_sector+(c-2)*v.spc)*512;chunk=b[i*cb:(i+1)*cb];data[begin:begin+cb]=chunk.ljust(cb,b'\0')
 entry=bytearray(32);stem,ext=name.split('.');entry[:11]=(stem.ljust(8)+ext.ljust(3)).encode();entry[11]=0x20;struct.pack_into('<HI',entry,26,chain[0],len(b));data[at:at+32]=entry
new=mod.Volume(bytes(data[offset:]));assert all(new.payloads.get(n)==b for n,b in v.payloads.items());assert {n:new.payloads[n]for n in batches}==batches;assert set(new.payloads)-set(v.payloads)==set(batches)
(P/'media/C-input.IMG').write_bytes(data)
(P/'FIXTURE_PROVENANCE.json').write_text(json.dumps({'scope':'owned copy of actual SETUP C; only three input batch programs appended by host, not operation output proof','original':ident(P/'media/C.IMG'),'input':ident(P/'media/C-input.IMG'),'input_batches':{n:ident(P/n)for n in batches},'all_original_payloads_preserved':len(v.payloads),'independent_FAT_valid':True,'free_bytes':new.report()['free_bytes']},indent=2)+'\n')
(P/'ORIGINS.json').write_text(json.dumps(origins,indent=2)+'\n');print(len(origins),len(v.payloads))
