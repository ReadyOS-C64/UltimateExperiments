from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-diskcopy-cache');assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,struct,zlib,time,hashlib,shutil,re
from test_journal_start import Journal as Menu,SYMS,L
from test_actual import ptr,Regs
from dos_lane import Lane
from dos_disk_inspect import Volume,inspect
REPORT=ROOT/'run';REPORT.mkdir(exist_ok=False)
MAIN={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(P.parent/'inputs/build/dos64.labels').read_text().splitlines()if l.startswith('al ')}
def labels(p):return{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
UI=labels(P.parent/'runtime/ui/panel.labels');BR=labels(P.parent/'runtime/bridge/bridge.labels');BO=labels(P.parent/'runtime/broker/broker.labels')
for n,ret,args in [('format_watch',None,[ptr,C.c_uint16,C.c_uint16]),('format_count',C.c_uint32,[ptr]),('format_word',C.c_uint16,[ptr,C.c_uint32,C.c_uint8]),('format_id',C.c_uint8,[ptr,C.c_uint32,C.c_uint8]),('dos64_step',None,[ptr]),('coupled_fault_bits',C.c_uint32,[ptr])]:fn=getattr(L,n);fn.restype=ret;fn.argtypes=args
scans={'A':30,'B':48,'C':46,'D':32,'E':18,'F':33,'G':34,'H':35,'I':23,'J':36,'K':37,'L':38,'M':50,'N':49,'O':24,'P':25,'Q':16,'R':19,'S':31,'T':20,'U':22,'V':47,'W':17,'X':45,'Y':21,'Z':44,':':39,'\\':43,'.':52,' ':57,'/':53,'\r':28}
for s in ['DISKCOPY A: B:\r','DISKCOMP A: B:\r','CLS\r','TYPE C:\\DOS\\CONFIG.SYS\r','N\r','\r']:assert all(c in scans for c in s)
assert 'Compare OK' in Volume((ROOT/'initial/A.IMG').read_bytes()).payloads['DISKCOMP.COM'].decode('latin1')
ci=(ROOT/'initial/C.IMG').read_bytes();cj=inspect(ci,(128,2,16));cv=Volume(ci[cj['partition']['start_lba']*512:]);c_text=cv.payloads['DOS/CONFIG.SYS'];assert c_text==b'c:\r\ndevice=c:\\dos\\ansi.sys\r\nfiles=25\r\nbuffers=25\r\n';C_LINES=c_text.decode('ascii').splitlines();assert len(C_LINES)==4
start=time.monotonic();events=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,j):(REPORT/n).write_text(json.dumps(j,indent=2)+'\n')
def get(m,n,size=1):return bytes(L.dos64_peek(m,MAIN[n]+i)for i in range(size))
def call(m,n,stop=0x300,budget=40000000):
 L.dos64_poke(m,0x1ff,2);L.dos64_poke(m,0x1fe,255);L.dos64_set_regs(m,Regs(MAIN[n],253,113,130,147,36,0,0));return L.dos64_run(m,stop,budget)
class UtilityLane(Lane):
 def call(self,n,budget=5000000):
  L.dos64_poke(self.m,0x1ff,2);L.dos64_poke(self.m,0x1fe,255);before=L.dos64_get_regs(self.m).cycles;L.dos64_set_regs(self.m,Regs(self.at(n),253,113,130,147,36,0,0));r=L.dos64_run(self.m,0x300,budget);elapsed=r.regs.cycles-before;self.cycles+=elapsed;self.remainder+=elapsed;L.dos64_cia_clock_advance(self.m,self.remainder//64);self.remainder%=64
  assert not r.status and not(r.regs.p&1)and self.state()!=225,(n,r.status,hex(r.regs.pc),self.get('dos64_native_diag',19).hex());assert self.cycles<80_000_000_000 and self.count()<20_000_000 and time.monotonic()-start<900,('bounded utility budget',self.cycles,self.count())
 def pause(self):
  for _ in range(4096):
   if self.get('hdb_active')!=b'\1':break
   self.call('dos64_native_tick')
  else:raise AssertionError('bounded C request completion')
  if self.state()!=5:self.command(2)
 def send(self,s):
  if self.state()==5:self.command(3)
  for off in range(0,len(s),8):
   for ch in s[off:off+8]:L.dos64_load(self.m,self.at('dos64_native_diag')+5,bytes([ord(ch),scans[ch]]),2);self.command(1)
   for tick in range(16000):
    self.call('dos64_native_tick')
    if tick%64!=63:continue
    self.pause();ring=self.read(0x41a,4);self.command(3)
    if ring[:2]==ring[2:]:break
   else:raise AssertionError('bounded BIOS ring drain')
 def snap(self,phase):
  waiting=self.get('dos64_bios_waiting')[0];self.pause();b=self.read(0x400,256);cols=int.from_bytes(b[74:76],'little');page=b[98];row,col=b[81+2*page],b[80+2*page];v=self.read(0xb8000+int.from_bytes(b[78:80],'little'),cols*50);lines=[''.join(chr(v[(r*cols+c)*2])if 32<=v[(r*cols+c)*2]<127 else'?'for c in range(cols))for r in range(25)];j={'phase':phase,'native_blocking_wait_before_pause':waiting,'screen':'\n'.join(lines),'cursor':[row,col],'guest_instructions':self.count(),'cycles':self.cycles,'BIOS_requests':L.format_count(self.m)};save('PROGRESS.json',j);return j,lines,row,col
 def clear_prompt(self,nextphase):
  self.send('CLS\r');stable=None
  for tick in range(10000):
   if self.state()==5:self.command(3)
   self.call('dos64_native_tick')
   if tick%64:continue
   o,lines,row,col=self.snap('CLS-before-'+nextphase)
   if col==2 and lines[row].strip()=='A>' and all(not line.strip() for i,line in enumerate(lines)if i!=row) and self.read(0x41a,4)[:2]==self.read(0x41a,4)[2:]:
    if stable is None:stable=self.count()
    elif self.count()-stable>=128:
     events.append({'phase':'CLS','before':nextphase,'empty_prompt_proved':True,'guest_instructions':self.count()});save('INPUT_EVENTS.json',events);return
  raise AssertionError(('bounded empty CLS prompt',nextphase,o))
 def format_B(self):
  self.clear_prompt('FORMAT');self.send('FORMAT B:\r');ready=False;answered=False;stable={};observed=[]
  for tick in range(60000):
   if self.state()==5:self.command(3)
   self.call('dos64_native_tick')
   if tick%128:continue
   o,lines,row,col=self.snap('FORMAT');s=o['screen'];tail=lines[row][:col].strip();observed.append(o);assert 'Format failure'not in s,o
   tag=None;key=None
   if not ready and 'Insert new diskette for drive B:'in s and 'and strike ENTER when ready'in s:tag='ready';key='\r'
   elif not answered and 'Format complete'in s and tail=='Format another (Y/N)?':tag='another';key='N\r'
   if key:
    if tag not in stable:stable[tag]=self.count()
    elif self.count()-stable[tag]>=128:
     if tag=='ready':ready=True
     else:answered=True
     events.append({'phase':'FORMAT','prompt':tail,'keys':repr(key)});save('INPUT_EVENTS.json',events);self.send(key);continue
   if answered and col==2 and lines[row].strip()=='A>':save('FORMAT.json',{'passed':True,'observations':observed});return
  raise AssertionError(('bounded FORMAT',observed[-1]))
 def utility(self,name):
  self.clear_prompt(name);self.send(name+' A: B:\r');ready=False;answered=False;stable={};observed=[];compare=False
  for tick in range(100000):
   if self.state()==5:self.command(3)
   self.call('dos64_native_tick')
   if tick%128:continue
   o,lines,row,col=self.snap(name);s=o['screen'];tail=lines[row][:col].strip();observed.append(o)
   assert not any(q in s for q in ['Unrecoverable','Compare error on','Target diskette unusable','bad or incompatible','Invalid drive']),o
   key=None
   if not ready and 'Press any key when ready . . .'in s and all(q in s for q in (['Insert SOURCE diskette in drive A:','Insert TARGET diskette in drive B:']if name=='DISKCOPY'else['Insert FIRST diskette in drive A:','Insert SECOND diskette in drive B:'])) and self.read(0x41a,4)[:2]==self.read(0x41a,4)[2:]:key='\r';tag='ready'
   elif not answered and (('Copy another diskette (Y/N)?'in tail)or('Compare another diskette (Y/N) ?'in tail)):key='N\r';tag='another'
   if key:
    if tag not in stable:stable[tag]=self.count()
    elif self.count()-stable[tag]>=128:
     if tag=='ready':ready=True
     else:answered=True
     events.append({'phase':name,'observed_prompt':tail,'keys':repr(key),'guest_instructions':self.count()});save('INPUT_EVENTS.json',events);self.send(key);continue
   compare=compare or 'Compare OK'in s
   if answered and col==2 and lines[row].strip()=='A>':
    assert ready and (name!='DISKCOMP'or compare);save(name+'.json',{'passed':True,'observations':observed,'formatting_while_copying':any('Formatting while copying'in x['screen']for x in observed),'Compare_OK':compare,'guest_instructions':self.count(),'cycles':self.cycles});return
  raise AssertionError(('bounded utility completion',name,observed[-1]))
def boot(f):
 m=f.m;r=f.run(SYMS['trampoline_loaded'],1300000000);assert r.regs.pc==SYMS['trampoline_loaded'];r=f.run(MAIN['dos64_native_loop'],1300000000);assert r.regs.pc==MAIN['dos64_native_loop'],(r.status,hex(r.regs.pc))
 for _ in range(4096):
  if get(m,'dos64_native_diag')==b'\4':break
  assert get(m,'dos64_native_diag')[0]in[2,6];r=call(m,'dos64_native_cold_poll');assert not r.status
 assert get(m,'dos64_native_diag')==b'\4';L.lc_clock_model_ratio(m,0);lane=UtilityLane(f,f.a);return lane
normal=[8,13,0x83,0x96,0x90,0x92,0x94,0x81,*map(ord,'3wa4zse'),0,*map(ord,'5rd6cftx'),*map(ord,'7yg8bhuv'),*map(ord,'9ij0mkon'),*map(ord,'+pl-.:@,'),ord('\\'),ord('*'),ord(';'),0x84,0,ord('='),ord('^'),ord('/'),ord('1'),9,0,ord('2'),ord(' '),0,ord('q'),27]
def menu(f,lane):
 m=f.m;lane.pause();lane.command(3);L.lc_clock_model_ratio(m,64);L.dos64_host_input_model_keys(m,bytes(7)+b'\xa4');r=call(m,'dos64_overlay_input_poll');assert not r.status;assert get(m,'dos64_modal_pending')==b'\1';r=call(m,'dos64_native_tick',0x7000);assert r.regs.pc==0x7000;r=L.dos64_run(m,BO['modal_wait'],40000000);assert r.regs.pc==BO['modal_wait']
 def go(keys,budget=5000000):
  L.dos64_host_input_model_keys(m,bytes(keys));L.dos64_step(m);q=L.dos64_run(m,BO['modal_wait'],budget);assert(q.status,q.regs.pc)==(2,BO['modal_wait']),(q.status,hex(q.regs.pc),get(m,'dos64_native_diag',19).hex(),bytes(L.dos64_peek(m,BR['br_last']+i)for i in range(9)).hex())
 def press(c,budget=5000000):
  go(bytes(8));shift=65<=c<=90;raw=c+32 if shift else c;at=normal.index(raw);keys=bytearray(8);keys[at//8]|=1<<(at%8)
  if shift:keys[1]|=128
  go(keys,budget)
 go(bytes(8));return go,press
def model_file(f,path):
 n=L.bulk_model_size(f.m,path);assert n!=0xffffffff,path;b=C.create_string_buffer(n);assert L.bulk_model_read(f.m,path,b,n);return b.raw
def finish(f,go,press):
 m=f.m;press(ord('f'));assert L.dos64_peek(m,UI['_mu_result'])==7;go(bytes(8));commands=L.bulk_model_commands(m);L.dos64_host_input_model_keys(m,bytes([2])+bytes(7));L.dos64_step(m);r=L.dos64_run(m,BO['modal_safe_idle'],20000000);assert r.regs.pc==BO['modal_safe_idle'];assert L.dos64_peek(m,BR['br_safe'])==1 and get(m,'dos64_native_diag')==b'\xe1';assert not L.bulk_model_open(m,1)and not L.bulk_model_open(m,2);assert L.bulk_model_commands(m)-commands==1
f=None
try:
 f=Menu();m=f.m;third=bytes((i*13+(i>>7))&255 for i in range(368640));f.seed(third,0x380000);a=f.a;b=f.b;c=f.c
 lane=boot(f);save('BOOT.json',lane.run());L.format_watch(m,MAIN['dos64_disk_transfer'],MAIN['dos64_guest']);lane.format_B();format_before=L.format_count(m);lane.utility('DISKCOPY');copied=f.reu(0x180000,368640);assert copied==a,('full720sectors',[(i,copied[i],a[i])for i in range(len(a))if copied[i]!=a[i]][:8]);assert Volume(copied).payloads==Volume(a).payloads
 lane.utility('DISKCOMP');assert f.reu(0x180000,368640)==a
 trace=[[L.format_word(m,i,j)for j in range(14)]for i in range(L.format_count(m))];formats=[r for r in trace if r[0]>>8==5];assert len(formats)>=80 and{(r[1]>>8,r[2]>>8)for r in formats}=={(c,h)for c in range(40)for h in range(2)},('actual FORMAT80',len(formats));save('BIOS_TRACE.json',trace)
 assert f.reu(0x100000,368640)==a and f.reu(0x380000,368640)==third;assert model_file(f,f.a_path)==a and model_file(f,f.b_path)==b and model_file(f,f.c_path)==c
 go,press=menu(f,lane);press(ord('b'));press(ord('n'));assert L.dos64_peek(m,UI['_mu_result'])==3;path=f.home+b'/COPY0001.IMG'
 for _ in range(len(f.home)+1):press(8)
 for ch in path:press(ch)
 before=get(m,'dos64_files_state_start',25);press(13,1600000000);assert(L.dos64_peek(m,BR['br_success']),L.dos64_peek(m,BR['br_error']))==(1,0);assert model_file(f,path)==a;newcfg=model_file(f,f.home+b'/DOS64.CFG');assert newcfg[264:392]==path.ljust(128,b'\0')and f.reu(0x3ff020,576)==newcfg;assert get(m,'dos64_files_state_start',25)==before
 # Return to actual guest then verify C remains readable before Finish.
 go(bytes(8));L.dos64_host_input_model_keys(m,bytes([0,0,2])+bytes(5));r=L.dos64_run(m,0x300,40000000);assert not r.status;assert get(m,'dos64_cache_limit')==b'\x20';call(m,'dos64_native_tick');call(m,'dos64_overlay_input_poll');call(m,'dos64_native_tick');L.dos64_host_input_model_keys(m,bytes(8));L.lc_clock_model_ratio(m,0);lane.clear_prompt('TYPE-C');lane.send('TYPE C:\\DOS\\CONFIG.SYS\r')
 for tick in range(10000):
  if lane.state()==5:lane.command(3)
  lane.call('dos64_native_tick')
  if tick%64:continue
  o,lines,row,col=lane.snap('C-after-save')
  if all(any(s.strip()==expected for s in lines)for expected in C_LINES)and col==2 and lines[row].strip()=='A>':save('C_READ.json',o);break
 else:raise AssertionError('exact C TYPE after SaveAs')
 go,press=menu(f,lane);finish(f,go,press)
 out=ROOT/'persisted';out.mkdir();pub=Path(os.environ['PUBLISHED_DIRECTORY'])
 for q in pub.iterdir():
  if q.is_file():shutil.copyfile(q,out/q.name)
 (out/'DOS64.CFG').write_bytes(newcfg);(out/'COPY0001.IMG').write_bytes(model_file(f,path));assert model_file(f,f.a_path)==a and model_file(f,f.b_path)==b and model_file(f,f.c_path)==c
 save('SESSION1.json',{'passed':True,'all720sectors_exact':True,'all_payloads_exact':True,'BIOS_format_tracks':len(formats),'DISKCOPY_additional_FORMAT_tracks':len([r for r in trace[format_before:]if r[0]>>8==5]),'actual_CIA_SaveAs_Finish':True,'C_online_exact':True,'guest_instructions':lane.count(),'cycles':lane.cycles,'sources_exact':True,'saved_path':path.decode(),'saved_sha256':sha(a)})
 f.close();f=None
 # New Machine reads only actual model-produced CFG/newimage; keep old originals in fixture.
 os.environ['PUBLISHED_DIRECTORY']=str(out);os.environ['MEDIA_DIRECTORY']=str(out);f=Menu();L.bulk_model_seed(f.m,path,(out/'COPY0001.IMG').read_bytes(),368640);lane=boot(f);save('FRESH_BOOT.json',lane.run());assert f.b==a and f.reu(0x180000,368640)==a and f.c==c and model_file(f,f.c_path)==c;assert Volume(f.b).payloads==Volume(a).payloads
 go,press=menu(f,lane);finish(f,go,press);save('RESULT.json',{'passed':True,'runtime_sha256':sha(f.main),'actual_DISKCOPY_DISKCOMP_SaveAs_Finish_freshSTART':True,'complete720sectors_and_payloads':True,'C_exact_both_sessions':True,'fresh_known_C_CLOSE':True,'seconds':time.monotonic()-start,'scope':'actual6510/genuineDOS two-drive model, XTwordDOSinput+realCIAmodalinput; initial disposable CFG/media hostprepared; no same-drive swaps/hardware/physicalthroughput'})
 print('PASS',time.monotonic()-start,flush=True)
except BaseException as e:
 save('FAILURE.json',{'type':type(e).__name__,'error':repr(e),'seconds':time.monotonic()-start,'stage':get(f.m,'dos64_native_diag',19).hex()if f else None});raise
finally:
 if f:f.close()
