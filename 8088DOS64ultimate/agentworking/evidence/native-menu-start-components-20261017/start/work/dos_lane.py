import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-handoff-cache-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,hashlib,unittest,time
from test_controller import Controller,L,HOME,A,B,ROOT,cfg,release_fixture
from test_actual import bind,ptr,u8,u16,u32,u64,Regs,Result
bind('dos64_get_regs',Regs,[ptr]);bind('dos64_cia_clock_enable',None,[ptr]);bind('dos64_cia_clock_step',None,[ptr,u32]);bind('dos64_cia_clock_advance',None,[ptr,u32]);bind('dos64_native_display_enable',None,[ptr]);bind('dos64_host_input_model_enable',None,[ptr]);bind('native_runtime_control_enable',None,[ptr])
bind('bulk_model_open',u8,[ptr,u8]);bind('lc_final_dma_nmi_arm',None,[ptr])
for n in ['lc_nmi_count','lc_final_dma_seen','lc_final_dma_address']:bind(n,u32,[ptr])
for n in ['lc_final_dma_host','lc_final_dma_count']:bind(n,u16,[ptr])
bind('lc_nmi_opcode',u8,[ptr]);bind('lc_entry_interrupt_seed',None,[ptr]);bind('lc_entry_interrupt_checked',u8,[ptr])
MAIN={l.split()[2].lstrip("."):int(l.split()[1],16) for l in (ROOT/"build/dos64.labels").read_text().splitlines() if l.startswith("al ")}
def sha(b):return hashlib.sha256(b).hexdigest()
class Lane:
 def __init__(self,f,a):
  self.f=f;self.m=f.m;self.a=a;self.stage='date';self.version=False;self.initial=False;self.header=False;self.summary=False;self.pagination=0;self.ticks=0;self.cycles=0;self.remainder=0;self.commands=0;self.observations=[];self.keys=[];self.last=None
  ss=struct.unpack_from('<H',a,11)[0];reserved=struct.unpack_from('<H',a,14)[0];fats=a[16];roots=struct.unpack_from('<H',a,17)[0];fatsecs=struct.unpack_from('<H',a,22)[0];rootlba=reserved+fats*fatsecs;rootsecs=(roots*32+ss-1)//ss
  self.entries={}
  for i in range(roots):
   e=a[rootlba*ss+i*32:rootlba*ss+(i+1)*32]
   if not e[0]:break
   if e[0]==0xe5 or e[11]&0x1e:continue
   self.entries[(e[:8]+b' '+e[8:11]).decode('ascii')]=[struct.unpack_from('<I',e,28)[0],False]
  fat=a[reserved*ss:(reserved+fatsecs)*ss];clusters=(struct.unpack_from('<H',a,19)[0]-rootlba-rootsecs)//a[13];self.free=0
  for cluster in range(2,clusters+2):
   i=cluster+cluster//2;v=fat[i]|fat[i+1]<<8;v=(v&0xfff) if cluster%2==0 else v>>4
   if not v:self.free+=a[13]*ss
  assert len(self.entries)==35 and self.free==9216
 def at(self,n):return MAIN[n]
 def get(self,n,nbytes=1):return bytes(L.dos64_peek(self.m,self.at(n)+i) for i in range(nbytes))
 def put(self,n,b):L.dos64_load(self.m,self.at(n),b,len(b))
 def state(self):return self.get('dos64_native_diag')[0]
 def count(self):return int.from_bytes(self.get('dos64_cpu_instructions',4),'little')
 def call(self,n,budget=5_000_000):
  # Actual resident function call; only the native hardware return frame is set.
  ret=0x0300-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255)
  before=L.dos64_get_regs(self.m).cycles
  L.dos64_set_regs(self.m,Regs(self.at(n),0xfd,0x71,0x82,0x93,0x24,0,0))
  r=L.dos64_run(self.m,0x0300,budget);elapsed=r.regs.cycles-before
  self.cycles+=elapsed;self.remainder+=elapsed;L.dos64_cia_clock_advance(self.m,self.remainder//64);self.remainder%=64
  assert not r.status,(n,r.status,hex(r.regs.pc),self.state(),self.count())
  assert not(r.regs.p&1) and self.state()!=0xe1,(n,self.state(),self.get('dos64_native_diag',19).hex())
  assert self.cycles<6_000_000_000 and self.count()<1_200_000
 def command(self,c):
  d=self.at('dos64_native_diag');assert L.dos64_peek(self.m,d+3)==0
  L.dos64_poke(self.m,d+4,0);L.dos64_poke(self.m,d+3,c);self.commands+=1
  for _ in range(256):
   self.call('dos64_native_tick',3_000_000 if c==2 else 5_000_000)
   if L.dos64_peek(self.m,d+3)==0:break
  assert L.dos64_peek(self.m,d+3)==0 and L.dos64_peek(self.m,d+4)==0xa5
 def read(self,a,n):
  assert self.state()==5;out=bytearray()
  while len(out)<n:
   far=a+len(out);count=min(n-len(out),2048,65536-(far&65535));d=self.at('dos64_native_diag')
   L.dos64_load(self.m,d+14,struct.pack('<I',far)[:3]+struct.pack('<H',count),5);self.command(4)
   out.extend(L.dos64_peek(self.m,0xc100+i) for i in range(count))
  return bytes(out)
 def observe(self):
  # The legacy lane only exercised floppy media. Command2 deliberately
  # rejects an active C request; observe only after its native completion.
  for _ in range(4096):
   if self.get('hdb_active')!=b'\1':break
   self.call('dos64_native_tick')
  assert self.get('hdb_active')!=b'\1'
  before=self.count();self.command(2);assert self.count()==before and self.state()==5
  bda=self.read(0x400,256);cols=struct.unpack_from('<H',bda,0x4a)[0];page=bda[0x62];size,offset=struct.unpack_from('<HH',bda,0x4c);cur=struct.unpack_from('<H',bda,0x50+page*2)[0];row,col=cur>>8,cur&255
  assert bda[0x49]<=3 and cols in [40,80] and size==(4096 if cols==80 else 2048) and offset==page*size and row<25 and col<cols
  v=self.read(0xb8000+offset,cols*50);lines=[''.join(chr(v[(r*cols+c)*2]) if 32<=v[(r*cols+c)*2]<127 else '?' for c in range(cols)) for r in range(25)];text='\n'.join(lines);prompt=col==2 and lines[row].strip()=='A>'
  self.observations.append({'stage':self.stage,'instructions':before,'screen':text,'cursor':[row,col],'columns':cols,'bitmap_sha256':sha(bytes(L.dos64_peek(self.m,0x6000+i) for i in range(8000)))})
  keys=''
  if self.stage=='date' and 'Enter new date (mm-dd-yy):' in text:keys='\r';self.stage='time'
  elif self.stage=='time' and 'Enter new time:' in text:keys='\r';self.stage='prompt'
  elif self.stage=='prompt' and prompt:self.initial=True;keys='VER\r';self.stage='ver'
  elif self.stage=='ver':
   if 'MS-DOS Version 3.30' in text:self.version=True
   if self.version and prompt:keys='DIR /P\r';self.stage='dir'
  elif self.stage=='dir':
   if 'Directory of  A:' in text:self.header=True
   if self.header:
    for line in lines:
     for name,e in self.entries.items():
      if line.startswith(name):
       fields=line[12:].split()
       if fields and fields[0].isdigit() and int(fields[0])==e[0]:e[1]=True
     fields=line.split()
     if len(fields)>=5 and fields[1]=='File(s)' and fields[3:5]==['bytes','free'] and fields[0].isdigit() and fields[2].isdigit() and int(fields[0])==len(self.entries) and int(fields[2])==self.free:self.summary=True
   if all(e[1] for e in self.entries.values()) and self.summary and prompt:self.stage='done'
   elif 'Strike a key when ready . . .' in lines[row][:col]:
    assert self.pagination<4;keys=' ';self.pagination+=1
  if self.stage!='done':
   self.command(3)
   scans={'V':0x2f,'E':0x12,'R':0x13,'D':0x20,'I':0x17,'P':0x19,' ':0x39,'/':0x35,'\r':0x1c}
   for k in keys:
    d=self.at('dos64_native_diag');L.dos64_load(self.m,d+5,bytes([ord(k),scans[k]]),2);self.command(1);self.keys.append(scans[k]<<8|ord(k))
 def run(self):
  L.dos64_cia_clock_step(self.m,0)
  while self.stage!='done':
   assert self.ticks<80000,(self.stage,self.count());self.ticks+=1;self.call('dos64_native_tick');count=self.count()
   if count!=self.last and (self.get('dos64_bios_waiting')==b'\x01' or self.last is None or ((count-self.last)&0xffffffff)>=4096):self.last=count;self.observe()
  assert self.initial and self.version and self.header and self.summary and self.pagination>0
  guest=self.read(0,640*1024);video=self.read(0xb8000,16384)
  assert int.from_bytes(self.get('dos64_pit_total',4),'little')>0 and int.from_bytes(guest[0x46c:0x470],'little')>0
  return {'status':'PASS_ACTUAL_C_CONTROLLER_DMA_NMI_REAL_MAIN_GENUINE_DOS','guest_instructions':self.count(),'native_cycles_after_start':self.cycles,'ticks':self.ticks,'pagination':self.pagination,'directory_entries':self.entries,'free_bytes':self.free,'guest_sha256':sha(guest),'video_sha256':sha(video),'inputs':self.keys,'observations':self.observations,'clock':'functional64:1 afterstartup, DMA stalls excluded; not physical throughput'}
