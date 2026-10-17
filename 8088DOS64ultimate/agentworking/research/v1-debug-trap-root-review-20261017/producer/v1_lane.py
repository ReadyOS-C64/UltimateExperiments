from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-v1-run-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
sys.path.insert(0,str(P/'start'))
import re
import argparse,ctypes as C,hashlib,json,struct,time,zlib,shutil
from test_start import Start,SYMS,L,MAIN
from test_actual import bind,ptr,u8,u16,u32,u64,Regs,Result
from importlib.util import spec_from_file_location,module_from_spec
for n,r,a in [('v1_call',Result,[ptr,u16,u16,u64]),('v1_ticks',Result,[ptr,u16,u16,u64,u32,C.POINTER(u64)]),('v1_ram',None,[ptr,ptr]),('dos64_get_regs',Regs,[ptr]),('dos64_cia_clock_advance',None,[ptr,u32])]:bind(n,r,a)
HOME=b'/usb1/V1 Test';PATHS=[b'/usb1/V1 Media/A.IMG',b'/usb1/V1 Media/B.IMG',b'/usb1/V1 Media/C.IMG']
TOTAL_NATIVE_CYCLES=0
RUN_STARTED=time.monotonic()
TEXT='DOS64 V1 EDIT 1'
SOURCE=['program V1Edit;','{$G-}','begin',"Writeln('"+TEXT+"');",'end.']
def sha(b):return hashlib.sha256(b).hexdigest()
def ident(q):b=q.read_bytes();return {'sha256':sha(b),'bytes':len(b)}
def verify(rec):
 for n,v in rec.items():assert ident(Path(n))==v,n
def labels(q):return {l.split()[2].lstrip('.'):int(l.split()[1],16)for l in q.read_text().splitlines()if l.startswith('al ')}
def module(n,q):s=spec_from_file_location(n,q);m=module_from_spec(s);s.loader.exec_module(m);return m
DISK=module('v1_independent_fat',P/'project/build_support/dos_disk_inspect.py')
CURSOR=module('v1_captured_cursor_oracle',P/'project/build_support/cga_cursor_oracle.py')
class Fixture(Start):
 def __init__(self,hd,columns):
  super().__init__(0xa5,HOME);self.columns=columns;self.a=(P/'media/A.IMG').read_bytes();self.b=(P/'media/B.IMG').read_bytes();self.hd=hd
  config=bytearray(576);config[:8]=b'D64C\1\x40\2\0';config[8:136]=HOME.ljust(128,b'\0')
  for o,v in zip([136,264,392],PATHS):config[o:o+128]=v.ljust(128,b'\0')
  config[522]=1;config[524:526]=bytes([3,7]);struct.pack_into('<IIHI',config,528,zlib.crc32(self.a),zlib.crc32(self.b),1,0x400000);struct.pack_into('<I',config,572,zlib.crc32(config[:572]));self.config=bytes(config)
  bundle=json.loads((P/'BUNDLE.json').read_text());self.main=(P/'inputs/build/dos64.prg').read_bytes();self.rel=Path(bundle['products']['DOS64.REL']['path']).read_bytes();self.asset=(P/'start/START.INO').read_bytes()
  ini=b'[emulator]\r\ninitial_columns='+str(columns).encode()+b'\r\n';self.seeds=[(HOME+b'/'+n,d)for n,d in [(b'DOS64.PRG',self.main),(b'DOS64.REL',self.rel),(b'START.INO',self.asset),(b'DOS64.CFG',self.config),(b'DOS64.INI',ini)]]+list(zip(PATHS,[self.a,self.b,hd]))
  for name in ['DOS64.MNU','START.RCV','START.RFW']:
   body=Path(bundle['products'][name]['path']).read_bytes();self.seeds.append((HOME+b'/'+name.encode(),body))
  for path,data in self.seeds:L.bulk_model_seed(self.m,path,data,len(data))
 def file(self,path):
  count=L.bulk_model_size(self.m,path);b=C.create_string_buffer(count);assert L.bulk_model_read(self.m,path,b,count);return b.raw
class Native:
 def __init__(self,f,out):self.f=f;self.m=f.m;self.out=out;self.remainder=C.c_uint64();self.cycles=0;self.ticks=0;self.calls=0;self.samples=0;self.keys=[];self.observations=[];self.started=time.monotonic();self.expected_head=None;self.previous_head=None;self.watch_stage='cold';self.watch_cycles=0
 def at(self,n):return MAIN[n]
 def get(self,n,k=1):return bytes(L.dos64_peek(self.m,self.at(n)+i)for i in range(k))
 def put(self,n,b):L.dos64_load(self.m,self.at(n),b,len(b))
 def stage(self):return self.get('dos64_native_diag')[0]
 def guest(self):return int.from_bytes(self.get('dos64_cpu_instructions',4),'little')
 def ram(self):b=C.create_string_buffer(65536);L.v1_ram(self.m,b);return b.raw
 def call(self,n,budget=8_000_000,allow_clock_sample=False):
  global TOTAL_NATIVE_CYCLES
  before=L.dos64_get_regs(self.m).cycles;r=L.v1_call(self.m,self.at(n),0x300,budget);elapsed=r.regs.cycles-before;self.cycles+=elapsed;TOTAL_NATIVE_CYCLES+=elapsed;total=elapsed+self.remainder.value;L.dos64_cia_clock_advance(self.m,total//64);self.remainder.value=total%64;self.calls+=1
  assert not r.status and(not(r.regs.p&1)or(allow_clock_sample and n=='dos64_elapsed_poll'and self.get('dos64_host_clock_status')==b'\4')),(n,r.status,hex(r.regs.pc),hex(r.regs.p),self.get('dos64_native_diag',34).hex())
  assert self.stage()!=0xe1,('native failure',self.get('dos64_native_diag',34).hex());self.budget();return r
 def budget(self):assert self.guest()<12_000_000 and self.ticks<1_000_000 and TOTAL_NATIVE_CYCLES<80_000_000_000 and self.cycles-self.watch_cycles<20_000_000_000 and time.monotonic()-RUN_STARTED<1200,('budget',self.watch_stage,self.guest(),self.ticks,self.cycles,TOTAL_NATIVE_CYCLES,self.cycles-self.watch_cycles)
 def tick(self,n=32):
  global TOTAL_NATIVE_CYCLES
  assert self.stage()==4,self.stage();before=L.dos64_get_regs(self.m).cycles;r=L.v1_ticks(self.m,self.at('dos64_native_tick'),0x300,8_000_000,n,C.byref(self.remainder));self.cycles+=r.regs.cycles-before;TOTAL_NATIVE_CYCLES+=r.regs.cycles-before;self.calls+=n;self.ticks+=n
  assert not r.status and not(r.regs.p&1)and self.stage()!=0xe1,('native tick',r.status,hex(r.regs.pc),hex(r.regs.p),self.get('dos64_native_diag',34).hex());self.budget()
 def command(self,op,key=None):
  at=self.at('dos64_native_diag');assert L.dos64_peek(self.m,at+3)==0
  if key is not None:L.dos64_load(self.m,at+5,struct.pack('<H',key),2)
  L.dos64_poke(self.m,at+4,0);L.dos64_poke(self.m,at+3,op)
  for _ in range(256):
   self.call('dos64_native_tick')
   if L.dos64_peek(self.m,at+3)==0:break
  assert L.dos64_peek(self.m,at+3)==0 and L.dos64_peek(self.m,at+4)==0xa5,('command',op,self.get('dos64_native_diag',34).hex())
 def read(self,a,n):
  assert self.stage()==5;out=bytearray()
  while len(out)<n:
   far=a+len(out);count=min(n-len(out),2048,65536-(far&65535));self.put('dos64_native_diag',self.get('dos64_native_diag',14)+struct.pack('<I',far)[:3]+struct.pack('<H',count));self.command(4);out.extend(L.dos64_peek(self.m,0xc100+i)for i in range(count))
  return bytes(out)
 def observe(self,tag,checkpoint=False):
  # Caller waits for completed HD transactions; never borrows an active FILE frame.
  assert self.get('hdb_active')==b'\0'
  before=self.guest();self.command(2);assert self.stage()==5 and self.guest()==before
  ram_before=self.ram();bda=self.read(0x400,256);cols=int.from_bytes(bda[0x4a:0x4c],'little');page=bda[0x62];offset=int.from_bytes(bda[0x4e:0x50],'little');cur=int.from_bytes(bda[0x50+2*page:0x52+2*page],'little');row,col=cur>>8,cur&255
  assert cols in [40,80] and bda[0x49] in [1,3] and offset==page*(4096 if cols==80 else 2048)and row<25 and col<cols
  video=self.read(0xb8000+offset,cols*50);lines=[''.join(chr(video[2*(r*cols+c)]) if 32<=video[2*(r*cols+c)]<127 else' 'for c in range(cols))for r in range(25)];text='\n'.join(lines);ram_after=self.ram();assert self.guest()==before
  # Native READ may alter request/transport scratch but not paused guest/display/keyboard authority.
  for n,count in [('dos64_guest',28),('dos64_cga_registers',18),('dos64_cga_control',1),('dos64_cga_control_valid',1),('dos64_cursor_phase_valid',1),('dos64_cursor_field_phase',1),('dos64_render_text_request',2)]:
   if n in MAIN:
    at=self.at(n);assert ram_before[at:at+count]==ram_after[at:at+count],('capture changed',n)
  assert ram_before[0x4000:0x5000]==ram_after[0x4000:0x5000] and ram_before[0x6000:0x7f40]==ram_after[0x6000:0x7f40],'paused frame changed during READ'
  head=int.from_bytes(bda[0x1a:0x1c],'little');tail=int.from_bytes(bda[0x1c:0x1e],'little');assert head in range(0x1e,0x3e,2)and tail in range(0x1e,0x3e,2)
  self.samples+=1;s={'id':self.samples,'stage':tag,'guest':before,'cols':cols,'mode':bda[0x49],'cursor':[row,col],'guest_regs_hex':self.get('dos64_guest',28).hex(),'head':head,'tail':tail,'text':text,'prompt':lines[row].strip()=='C>'and col==2}
  self.observations.append(s)
  if checkpoint:
   stem=self.out/(str(self.samples).zfill(4)+'-'+tag)
   stem.with_suffix('.txt').write_text(text+'\n');stem.with_suffix('.RAM.bin').write_bytes(ram_after);stem.with_suffix('.BDA.bin').write_bytes(bda);stem.with_suffix('.CGA.bin').write_bytes(video);stem.with_suffix('.json').write_text(json.dumps(s,indent=2)+'\n')
   cga=self.read(0xb8000,16384);narrow=(P/'project/assets/native-text/cp437-narrow4x8.bin').read_bytes();wide=(P/'project/assets/native-text/cp437-unscii8.bin').read_bytes()
   frame=CURSOR.render_text_capture(bda,cga,narrow,wide,registers=self.get('dos64_cga_registers',18),control=self.get('dos64_cga_control')[0],control_valid=self.get('dos64_cga_control_valid')[0],phase_valid=self.get('dos64_cursor_phase_valid')[0],field_phase=self.get('dos64_cursor_field_phase')[0],blink_visible=self.get('dos64_render_text_request',2)[1],native_sha256=sha(self.f.main),expected_native_sha256=sha((P/'inputs/build/dos64.prg').read_bytes()))
   assert ram_after[0x4400:0x4800]==narrow and ram_after[0x4800:0x5000]==wide and ram_after[0x6000:0x7f40]==frame['bitmap']and ram_after[0x4000:0x43e8]==frame['matrix'],'full native bitmap/matrix/cursor oracle mismatch'
   png(stem.with_suffix('.png'),frame['bitmap'],frame['matrix']);stem.with_suffix('.frame.json').write_text(json.dumps({'status':'actualRAM fullbitmap/matrix/cursor verified; illustrative palette; not physicalHDMI','columns':cols,**frame['metadata']},indent=2)+'\n')
  return s
 def resume(self):
  if self.stage()==5:self.command(3)
 def key(self,s,word):
  assert s['head']==s['tail']and self.expected_head is None,('foreign queue',s['head'],s['tail'])
  self.previous_head=s['head'];self.expected_head=0x1e if s['tail']==0x3c else s['tail']+2;self.resume();self.command(1,word);self.keys.append({'word':word,'sample':s['id'],'guest':s['guest'],'expected_head':self.expected_head})
 def consumed(self,s):
  if self.expected_head is None:return s['head']==s['tail']
  assert s['tail']==self.expected_head and s['head']in[self.previous_head,self.expected_head],('unexpected keyboard queue mutation',s)
  if s['head']!=self.expected_head:return False
  assert s['head']==s['tail'];self.expected_head=None;return True
 def wait(self,stage,predicate,stable=True):
  if stage!=self.watch_stage:self.watch_stage=stage;self.watch_cycles=self.cycles
  accepted=False
  for _ in range(3000):
   self.resume();self.tick(512)
   if self.get('hdb_active')!=b'\0':continue
   s=self.observe(stage)
   if self.samples%32==0:
    (self.out/'PROGRESS.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({'phase':'wait','stage':stage,'samples':self.samples,'guest':self.guest(),'cycles':self.cycles,'cursor':s['cursor'],'head':s['head'],'tail':s['tail']}),flush=True)
   if not self.consumed(s):continue
   yes=bool(predicate(s))
   if yes and(accepted or not stable):
    self.observe(stage,True);return s
   accepted=yes
  raise TimeoutError(('UI stage',stage,self.guest(),self.observations[-1]))
 def type(self,text,stage):
  # Observed empty ring, capacity15; each group14 cannot FULL under exclusive input.
  for start in range(0,len(text),14):
   self.wait(stage+'-batch-'+str(start//14),lambda s:s['head']==s['tail'],False);self.resume();at=self.at('dos64_native_diag')
   for ch in text[start:start+14]:
    word=key(ch);assert self.stage()==4 and L.dos64_peek(self.m,at+3)==0
    L.dos64_load(self.m,at+5,struct.pack('<H',word),2);L.dos64_poke(self.m,at+4,0);L.dos64_poke(self.m,at+3,1);self.call('dos64_native_tick')
    ack=L.dos64_peek(self.m,at+4);assert L.dos64_peek(self.m,at+3)==0 and ack==0xa5,('unexpected enqueue refusal in capacity-bounded group',ack,self.get('dos64_keyboard_status'))
    self.keys.append({'word':word,'stage':stage,'guest':self.guest(),'group':start//14,'group_limit':14})
  print(json.dumps({'phase':'keyboard_batch_accepted','stage':stage,'words':len(text),'guest':self.guest(),'cycles':self.cycles}),flush=True)
 def wire_summary(self,expect_writes):
  hist={};writes=[]
  for i in range(L.bulk_model_commands(self.m)):
   target=L.bulk_model_command(self.m,i,0);op=L.bulk_model_command(self.m,i,1);k=str(target)+':'+str(op);hist[k]=hist.get(k,0)+1
   if op==5:
    count=L.bulk_model_command(self.m,i,2)|(L.bulk_model_command(self.m,i,3)<<8);assert target==2 and count==256,(i,target,count);writes.append(i)
  assert bool(writes)==expect_writes and len(writes)%2==0,(expect_writes,len(writes))
  return {'wire_histogram_target_opcode':hist,'WRITE05_commands':len(writes),'WRITE05_count_each':256,'native512sector_split_into2x256':True,'native_model_checks_exact_wire_payload_length':True}
 def close_readback(self):
  self.readback_started=True;self.watch_stage='native-closed-full-readback';self.watch_cycles=self.cycles
  assert self.stage()==5 and self.get('hdb_active')==b'\0'and self.get('dos64_files_handle')==b'\1'
  def clock():
   for attempt in range(256):
    r=self.call('dos64_elapsed_poll',100000,allow_clock_sample=True)
    if not(r.regs.p&1):self.put('dos64_files_now',self.get('dos64_elapsed_now',2));return
    self.clock_sample_retries=getattr(self,'clock_sample_retries',0)+1
   raise TimeoutError('256 transient HC_ERR_SAMPLE clock attempts')
  def op(code,**kw):
   clock();self.put('dos64_files_op',bytes([code]))
   for name,b in kw.items():self.put(name,b)
   self.call('dos64_overlay_files_start',100000)
   for _ in range(4096):
    if self.get('dos64_files_state')!=b'\1':break
    clock();self.call('dos64_overlay_files_poll',100000)
   assert self.get('dos64_files_state')==b'\2',('native fileop',code,self.get('dos64_files_state_start',25).hex())
   return int.from_bytes(self.get('dos64_files_actual',2),'little')
  op(3);assert self.get('dos64_files_handle')==b'\0'and [L.bulk_model_open(self.m,i)for i in[1,2]]==[0,0]
  path=PATHS[2]+b'\0';L.dos64_load(self.m,self.at('dos64_uci_command')+3,path,len(path));op(2,dos64_files_mode=b'\1',dos64_files_path_len=bytes([len(path)]));op(7);size=int.from_bytes(self.get('dos64_uci_data',4),'little');assert size==len(self.f.hd)
  data=bytearray()
  while len(data)<size:
   n=op(4,dos64_files_count=struct.pack('<H',512));assert n==512 and self.get('dos64_files_count_known')==b'\1'and self.get('dos64_files_short')==b'\0';data.extend(self.get('dos64_uci_data',n))
   if len(data)%(2*1024*1024)==0:print(json.dumps({'phase':'native_C_readback','bytes':len(data),'guest':self.guest()}),flush=True)
  assert op(4,dos64_files_count=struct.pack('<H',512))==0 and self.get('dos64_files_short')==b'\1';op(3);assert self.get('dos64_files_handle')==b'\0'and L.bulk_model_open(self.m,2)==0
  assert bytes(data)==self.f.file(PATHS[2]);return bytes(data)
def png(path,bitmap,matrix):
 palette=[(0,0,0),(255,255,255),(136,0,0),(170,255,238),(204,68,204),(0,204,85),(0,0,170),(238,238,119),(221,136,85),(102,68,0),(255,119,119),(51,51,51),(119,119,119),(170,255,102),(0,136,255),(187,187,187)]
 raw=bytearray()
 for y in range(200):
  raw.append(0)
  for x in range(320):
   cell=(y//8)*40+x//8;bits=bitmap[(y//8)*320+(x//8)*8+y%8];colors=matrix[cell];rgb=palette[(colors>>4)if bits&(1<<(7-x%8))else(colors&15)];raw.extend(rgb)
 def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,200,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b''))
def key(ch):
 scans={**{v:i+2 for i,v in enumerate('1234567890')},**dict(zip('qwertyuiop',[0x10+i for i in range(10)])),**dict(zip('asdfghjkl',[0x1e+i for i in range(9)])),**dict(zip('zxcvbnm',[0x2c+i for i in range(7)])), '\r':0x1c,' ':0x39,'\\':0x2b,':':0x27,';':0x27,"'":0x28,'.':0x34,'>':0x34,'{':0x1a,'}':0x1b,'$':5,'-':0x0c,'(':0x0a,')':0x0b}
 return(scans[ch.lower()]<<8)|ord(ch)
def menu(s):return all(x in s['text'].split('\n')[0]for x in['File','Edit','Run','Compile','Help'])
def editor(s):return menu(s)and all(x not in s['text']for x in['Compiling','Save File As','Save file as','Destination','Compile successful:'])
def launch(f,out):
 L.lc_final_dma_nmi_arm(f.m);r=f.run(SYMS['trampoline_start'],1_300_000_000);assert r.status in[0,2]and r.regs.pc==0x200,(r.status,hex(r.regs.pc));f.startup_guard();assert f.byte('_sf_status')==2 and f.read('_lc_result',2)==b'\5\0'
 options=f.reu(0x3ff500,32);assert options[:8]==b'D64O\1\xa5\x20\0'and options[16]==f.columns
 staged=f.reu(0x3e0000,len(f.main));r=f.run(SYMS['trampoline_loaded'],20000);assert not r.status;assert bytes(L.dos64_peek(f.m,0x0801+i)for i in range(len(f.main)-2))==staged[2:]
 r=f.run(MAIN['dos64_native_loop']);assert not r.status and L.dos64_peek(f.m,MAIN['dos64_native_diag'])==6;assert f.reu(0x3ff005,1)==f.reu(0x3ff505,1)==b'\0';assert L.lc_nmi_count(f.m)==2
 L.lc_clock_model_ratio(f.m,0);n=Native(f,out);polls=0
 while n.stage()==6:
  assert polls<30000;n.call('dos64_native_cold_poll');polls+=1
 assert n.stage()==4;print(json.dumps({'phase':'cold_started','polls':polls,'columns':f.columns}),flush=True)
 s=n.wait('DOS-initial',lambda s:s['prompt']);assert s['cols']==f.columns;return n
def workflow(n):
 n.type('TURBO\r','launch-TURBO');s=n.wait('IDE-menu',lambda s:menu(s)and'NONAME00.PAS'in s['text']);
 n.type("program V1Edit;\r{$G-}\rbegin\rWriteln('DOS64 V1 EDIT 0",'type-source')
 s=n.wait('IDE-edit-old',lambda s:editor(s)and'V1 EDIT 0'in s['text']);n.key(s,0x0e08);s=n.wait('IDE-edit-deleted',lambda s:editor(s)and'V1 EDIT 0'not in s['text']);n.key(s,key('1'));n.type("');\rend.\r",'finish-source');s=n.wait('IDE-source-new',lambda s:editor(s)and all(x in s['text']for x in SOURCE));n.key(s,0x3c00)
 s=n.wait('IDE-SaveAs-dialog',lambda s:'Save File As'in s['text']);n.type('C:\\V1EDIT.PAS\r','save-filename');s=n.wait('IDE-saved',lambda s:editor(s)and'V1EDIT.PAS'in s['text']and all(x in s['text']for x in SOURCE));n.key(s,0x2e00)
 s=n.wait('IDE-Compile-menu',lambda s:'Destination'in s['text']and'Memory'in s['text']);n.key(s,key('d'));s=n.wait('IDE-after-destination-toggle',editor);n.key(s,0x2e00);s=n.wait('IDE-Destination-Disk',lambda s:'Destination'in s['text']and'Disk'in s['text']);n.key(s,0x011b);s=n.wait('IDE-editor-beforecompile',editor);n.key(s,0x7000)
 s=n.wait('IDE-diskcompile-success',lambda s:'Compile successful: Press any key'in s['text']and re.search(r'Destination:[ \t]+Disk[ \t]+Line number:',s['text'])and'Main file: \\V1EDIT.PAS'in s['text']and re.search(r'Total lines:[ \t]+5(?:[ \t]|$)',s['text']));n.key(s,0x011b);s=n.wait('IDE-editor-aftercompile',editor);n.key(s,0x6600);s=n.wait('IDE-return-from-run',editor);n.resume();before=n.guest();n.tick(50000);print(json.dumps({'phase':'bounded_actual_run_settle','native_ticks':50000,'guest_before':before,'guest_after':n.guest(),'cycles':n.cycles}),flush=True);s=n.wait('IDE-after-run-settle',editor);n.key(s,0x6c00)
 s=n.wait('IDE-program-output',lambda s:TEXT in s['text']and'Writeln('not in s['text']and not menu(s));n.key(s,0x1c0d);s=n.wait('IDE-after-output',editor);n.key(s,0x2d00);s=n.wait('DOS-after-AltX',lambda s:s['prompt']);n.type('ECHO V1 IDE EXIT\r','DOS-exit-marker');n.wait('DOS-owned-exit-marker',lambda s:s['prompt']and'V1 IDE EXIT'in s['text']);n.type('C:\\V1EDIT.EXE > C:\\V1OUT.TXT\r','DOS-redirect-output');n.wait('DOS-output-file-created',lambda s:s['prompt']);n.type('TYPE C:\\V1OUT.TXT\r','DOS-TYPE-output-file');n.wait('DOS-output-file-read',lambda s:s['prompt']and TEXT in s['text'])
def inspect(before,after,out):
 report=DISK.inspect(after,(640,4,16));start=report['partition']['start_lba']*512;size=report['bpb']['total_sectors']*512;original=DISK.Volume(before[start:start+size]);new=DISK.Volume(after[start:start+size]);
 for name,data in original.payloads.items():assert new.payloads.get(name)==data,('original payload changed',name)
 assert new.payloads['V1EDIT.PAS'].decode('ascii').splitlines()==SOURCE,repr(new.payloads['V1EDIT.PAS'])
 assert new.payloads['V1OUT.TXT']==(TEXT+'\r\n').encode('ascii'),repr(new.payloads['V1OUT.TXT'])
 assert new.payloads['V1EDIT.EXE'][:2]==b'MZ'and len(new.payloads['V1EDIT.EXE'])>1000
 for name in ['V1EDIT.PAS','V1EDIT.EXE','V1OUT.TXT']:(out/name).write_bytes(new.payloads[name])
 (out/'FAT.json').write_text(json.dumps(report,indent=2)+'\n');return {'original_payloads_preserved':len(original.payloads),'new_source_sha256':sha(new.payloads['V1EDIT.PAS']),'new_EXE_sha256':sha(new.payloads['V1EDIT.EXE']),'new_files':sorted(set(new.payloads)-set(original.payloads)),'full_image_sha256':sha(after)}
def fresh(n):
 n.type('TYPE C:\\V1OUT.TXT\r','fresh-TYPE-output');n.wait('fresh-output-file',lambda s:s['prompt']and any(line.strip()==TEXT for line in s['text'].splitlines()));n.type('TYPE C:\\V1EDIT.PAS\r','fresh-TYPE');n.wait('fresh-source',lambda s:s['prompt']and all(x in s['text']for x in SOURCE));n.type('CLS\r','fresh-clear');n.wait('fresh-cleared',lambda s:s['prompt']and all(not line.strip()or line.strip()=='C>'for line in s['text'].splitlines()));n.type('C:\\V1EDIT.EXE\r','fresh-EXE');n.wait('fresh-program-output',lambda s:s['prompt']and'C>C:\\V1EDIT.EXE'in s['text']and any(line.strip()==TEXT for line in s['text'].rsplit('C>C:\\V1EDIT.EXE',1)[1].splitlines()));n.type('ECHO V1 FRESH DONE\r','fresh-marker');n.wait('fresh-DONE',lambda s:s['prompt']and'V1 FRESH DONE'in s['text'])
def validate_keyboard_vectors():
 import ast
 vectors=[]
 for node in ast.walk(ast.parse(Path(__file__).read_text())):
  if isinstance(node,ast.Call) and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
   if (isinstance(node.func,ast.Attribute) and node.func.attr=='type') or (isinstance(node.func,ast.Name) and node.func.id=='key'):vectors.append(node.args[0].value)
 for text in vectors:
  for ch in text:assert key(ch)&255==ord(ch)
 assert key('>')==0x343e
 return {'literal_vectors':len(vectors),'literal_characters':sum(map(len,vectors)),'redirection_word':key('>')}
def main():
 keyboard_preflight=validate_keyboard_vectors()
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--only-menu',action='store_true');ap.add_argument('--keyboard-control',action='store_true');args=ap.parse_args();out=args.out.resolve();assert out.is_relative_to(P)and not out.exists();out.mkdir();pins=json.loads((P/'PREPARED_INPUTS.json').read_text());products=json.loads((P/'PREPARED_PRODUCTS.json').read_text());pins[str(Path(__file__).resolve())]=ident(Path(__file__).resolve());pins[str(P/'project/build_support/dos_disk_inspect.py')]=ident(P/'project/build_support/dos_disk_inspect.py');pins[str(P/'project/build_support/cga_cursor_oracle.py')]=ident(P/'project/build_support/cga_cursor_oracle.py');verify(pins);verify(products);(out/'INPUTS_BEFORE.json').write_text(json.dumps(pins,indent=2)+'\n');(out/'PRODUCTS_BEFORE.json').write_text(json.dumps(products,indent=2)+'\n');shutil.copyfile(Path(__file__),out/'EXECUTED_DRIVER.py');hd=(P/'media/C-original.IMG').read_bytes();f=n=None;error=None;result={'keyboard_preflight':keyboard_preflight,'status':'FAILED','physical':False,'keyboard_input':'actual nativeXTword endpoint; physicalC64matrix/human bypassed','host_guest_code_or_disk_save_injection':False,'start_config_fixture':'host-prepared canonical CFG/persistenthome/INI vectors, not installer-output proof'}
 try:
  f=Fixture(hd,80);n=launch(f,out);result['first_start_sha256']=sha(f.prg)
  if args.keyboard_control:
   n.type('ECHO BATCH0123456789BATCH0123456789BATCH0123456789BATCH0123456789 > C:\\PREKEY.TXT\r','control-long-redirection');n.wait('control-created',lambda s:s['prompt']);n.type('TYPE C:\\PREKEY.TXT\r','control-TYPE');n.wait('control-output',lambda s:s['prompt']and'BATCH0123456789BATCH0123456789BATCH0123456789BATCH0123456789'in s['text']);saved=n.close_readback();(out/'C-control-native-readback.IMG').write_bytes(saved)
   report=DISK.inspect(saved,(640,4,16));at=report['partition']['start_lba']*512;size=report['bpb']['total_sectors']*512;old=DISK.Volume(hd[at:at+size]);new=DISK.Volume(saved[at:at+size]);assert all(new.payloads.get(k)==d for k,d in old.payloads.items());assert new.payloads['PREKEY.TXT']==b'BATCH0123456789BATCH0123456789BATCH0123456789BATCH0123456789 \r\n';assert f.file(PATHS[0])==f.a and f.file(PATHS[1])==f.b;result['wire']=n.wire_summary(True);result['status']='PASS_ACTUAL_NATIVE_GROUP14_DOS_REDIR_FULL_NATIVE_CLOSE_READBACK_CONTROL_NOT_IDE';return
  if args.only_menu:

   n.type('TURBO\r','launch-TURBO');n.wait('IDE-menu',lambda s:menu(s)and'NONAME00.PAS'in s['text']);result['status']='MENU_PROBE_ONLY_NOT_V1_ACCEPTANCE';return
  workflow(n);saved=n.close_readback();(out/'C-after-native-readback.IMG').write_bytes(saved);result['files']=inspect(hd,saved,out);result['first_wire']=n.wire_summary(True);result['first_guest']=n.guest();result['first_ticks']=n.ticks;result['first_keys']=n.keys;result['first_observations']=n.observations;assert f.file(PATHS[0])==f.a and f.file(PATHS[1])==f.b
  f.close();f=None;n=None;second=out/'fresh40';second.mkdir();f=Fixture(saved,40);n=launch(f,second);assert sha(f.prg)==result['first_start_sha256'];fresh(n);n.close_readback();assert f.file(PATHS[2])==saved and f.file(PATHS[0])==f.a and f.file(PATHS[1])==f.b;result['fresh_wire']=n.wire_summary(False);result['fresh_guest']=n.guest();result['fresh_ticks']=n.ticks;result['fresh_keys']=n.keys;result['fresh_observations']=n.observations;result['status']='PASS_ACTUAL_START_TURBO_EDIT_SAVE_DISKCOMPILE_RUN_EXIT_NATIVE_READBACK_FRESH40_TYPE_RUN'
 except BaseException as caught:
  error=caught;result['error']=repr(caught)
  # Ordinary host oracle failures may retain a reusable native-closed image.
  # Never retry a started readback, native fatal state or interrupt/accounting gap.
  if isinstance(caught,Exception)and n is not None and f is not None and n.stage()in[4,5]and not getattr(n,'readback_started',False):
   try:
    for _ in range(4096):
     if n.get('hdb_active')==b'\0':break
     n.resume();n.tick(1)
    assert n.get('hdb_active')==b'\0';n.observe('first-failure-diagnostic-pause',True);diagnostic=n.close_readback();(out/'C-first-failure-diagnostic-knownclose.IMG').write_bytes(diagnostic);result['first_failure_diagnostic']={'status':'NATIVE_KNOWN_CLOSE_FULL_READBACK_ONLY_ORIGINAL_FAILURE_RETAINED','sha256':sha(diagnostic),'bytes':len(diagnostic)}
   except BaseException as secondary:result['first_failure_diagnostic']={'status':'FAILED_NO_RETRY','error':repr(secondary)}
  raise

 finally:
  # Independent reporting/diagnosis/close phases preserve the first exact exception.
  actions=[]
  if n is not None:
   actions.append(lambda:result.update(native_diag=n.get('dos64_native_diag',34).hex(),guest=n.guest(),ticks=n.ticks,cycles=n.cycles,clock_sample_retries=getattr(n,'clock_sample_retries',0),total_native_cycles=TOTAL_NATIVE_CYCLES,keys=n.keys,observations=n.observations));actions.append(lambda:(out/'failure-or-final-RAM.bin').write_bytes(n.ram()))
  if f is not None:
   actions.append(lambda:(out/'C-model-current.IMG').write_bytes(f.file(PATHS[2])));actions.append(f.close)
  for action in actions:
   try:action()
   except BaseException as secondary:
    result.setdefault('secondary_errors',[]).append(repr(secondary))
    if error is None:error=secondary
  try:
   verify(pins);verify(products);(out/'INPUTS_AFTER.json').write_text(json.dumps(pins,indent=2)+'\n');(out/'PRODUCTS_AFTER.json').write_text(json.dumps(products,indent=2)+'\n')
  except BaseException as secondary:
   result.setdefault('secondary_errors',[]).append(repr(secondary))
   if error is None:error=secondary
  try:(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
  except BaseException as secondary:
   if error is None:error=secondary
  if error is not None and sys.exc_info()[0]is None:raise error
if __name__=='__main__':main()
