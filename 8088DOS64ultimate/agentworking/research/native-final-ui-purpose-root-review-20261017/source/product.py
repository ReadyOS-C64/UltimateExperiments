"""One registered SETUP load/SYS and bounded physical-human CIA observation.
No host synthetic native key, private state write, main launch or retry.
"""
import time
from bound_release import BoundRelease
from large_load_only import RegisteredLoadOnly
class Product:
 def __init__(self,wire,protocol,release,assets,observer,*,save,clock=time.monotonic,sleep=time.sleep,cancel=lambda:False):
  self.wire=wire;self.protocol=protocol;self.release=release;self.assets=assets;self.observer=observer;self.save=save;self.clock=clock;self.sleep=sleep;self.cancel=cancel;self.started=False;self.resume_attempted=False;self.count_attempted=False;self.first=None;self.terminal_raw=None;self.report={'status':'pending','SYS_resume_attempted':False,'human_CIA_input_synthesized':False};self.index=0
 def record(self,v):self.index+=1;self.save('product-event-%04d.json'%self.index,(__import__('json').dumps(v,indent=2)+'\n').encode())
 def api(self,m,r,end):return self.wire.product_exchange(self,m,r,end)
 def ram(self,end):return self.wire.product_exchange(self,'GET','machine:readmem?address=0&length=65536',end,65536)
 def control(self,route,end):
  v=self.api('PUT',route,end)
  if type(v)is not dict or v.get('errors')!=[]:raise ValueError('Exact product control ACK')
  return v
 def run(self,stager_terminal,parent_end):
  if self.started:raise ValueError('Single product instance')
  self.started=True;self.wire.begin_product(self,stager_terminal);end=min(parent_end,self.clock()+60);load=RegisteredLoadOnly(self.protocol,self.release,self.assets,stager_terminal,'SETUP.PRG',api=self.api,read_ram=self.ram,record=self.record,clock=self.clock,sleep=self.sleep)
  try:
   self.report['registered_LOAD']=load.run(end,30);raw=self.ram(end);self.save('product-loaded-visible-RAM.bin',raw)
   if raw[0xc6]!=0:raise ValueError('Empty BASIC keyboard before exact SYS')
   for a,b,key in [(0x277,b'SYS2061\r','body'),(0xc6,b'\x08','count')]:
    if key=='count':self.count_attempted=True
    self.wire.product_field(self,a,b,end,key);raw=self.ram(end)
    if raw[0x277:0x27f]!=b'SYS2061\r'or raw[0xc6]!=(8 if key=='count'else 0):raise ValueError('Exact owned SYS count-last readback')
    if raw[0x801:0xa000]!=self.assets['SETUP.PRG'][2:0xa000-0x801+2]:raise ValueError('Visible entrysource before resume')
    self.save('product-SYS-'+key+'.bin',raw)
   self.resume_attempted=True;self.report['SYS_resume_attempted']=True;self.control('machine:resume',end)
   # Observe native admission only; pending startup is not a failure nor a ready bit.
   admitted=False
   for i in range(128):
    if self.clock()>=end:raise TimeoutError('Native startup original60s endpoint')
    self.control('machine:pause',end);raw=self.ram(end);a=self.observer.p('coordinator','state');state=raw[a]
    if state==2:
     self.report['postentry']=self.observer.observe(raw);self.save('product-admitted-RAM.bin',raw);self.save('product-admitted-screen.bin',raw[0x400:0x7e8]);admitted=True;break
    if state==5:raise ValueError('Native SETUP failed before UI admission')
    self.control('machine:resume',end);self.sleep(min(.05,max(0,end-self.clock())))
   if not admitted:raise TimeoutError('Bounded128 native startup observations')
   hold_end=min(parent_end-180,self.clock()+120)
   if hold_end<=self.clock():raise TimeoutError('Reserve original180s for retention/restore')
   self.record({'event':'NATIVE_UI_ADMITTED_HUMAN_CIA_ONLY','home':self.protocol.source.home.decode(),'deadline':hold_end,'instructions':'Use physical C64 keyboard. Choose owned home and three DOS sources; RunStop cancels safely. Host emits no native keys.','remaining_core_restore_reserve':parent_end-hold_end})
   self.control('machine:resume',hold_end)
   for i in range(256):
    if self.clock()>=hold_end:raise TimeoutError('Bounded human CIA window; no synthetic STOP/reset')
    if self.cancel():raise KeyboardInterrupt('Host cancelled; native ownership still requires terminal proof')
    self.control('machine:pause',hold_end);a=self.observer.p('coordinator','state');header=self.wire.product_exchange(self,'GET',f'machine:readmem?address={a:X}&length=12',hold_end,12)
    self.record({'event':'native_header','observation':i,'bytes':header.hex()})
    if header[0]in[5,7]:
     raw=self.ram(hold_end);proof=self.observer.terminal(raw);self.save('product-native-terminal-RAM.bin',raw);self.save('product-native-terminal-screen.bin',raw[0x400:0x7e8]);self.terminal_raw=raw;self.report.update(status='passed',terminal=proof)
     if proof['outcome']=='NATIVE_FAILED_KNOWN_QUIET':raise RuntimeError('Native firsterror%d'%proof['native_first_error'])
     return self.report
    self.control('machine:resume',hold_end);self.sleep(min(.5,max(0,hold_end-self.clock())))
   raise TimeoutError('Bounded256 human observations')
  except BaseException as e:
   if self.first is None:self.first=e
   self.report.update(status='failed',first_error=repr(self.first));raise self.first
