"""Exact private target2 CLOSE/reopen/read-only helper and load/SYS authority."""
import bootstrap,re,time
from pathlib import Path
from ac_contract import sha
from load_then_sys import LoadThenSysClient
from c64u_native_application import labels_from
# Helper labels intentionally have a different ABI from the native runtime.
def parse_labels(body):return {n.lstrip('.'):int(a,16) for a,n in re.findall(r'^al ([0-9a-fA-F]+) (\S+)',body.decode('ascii'),re.M)}
def configure_helper(base,labels_blob,path):
 labels=parse_labels(labels_blob);at=labels['helper_config']-0x801+2;end=labels['helper_config_end']-0x801+2
 if base[:14]!=b'\x01\x08\x0b\x08\x0a\x00\x9e2061\x00\x00\x00' or len(base)-2+0x801>0x4000 or end-at!=134 or base[at:at+6]!=b'DHC1\0\0':raise ValueError('Exact disabled HDC1 BASIC2061 source required')
 if not re.fullmatch(r'/usb1/DOS64_TEST/[a-z0-9][a-z0-9_-]{0,63}/DOSHD\.IMG',path):raise ValueError('Exact owned HD helper path required')
 raw=path.encode('ascii')+b'\0'
 if len(raw)>128:raise ValueError('HD helper path too long')
 out=bytearray(base);out[at+4:at+134]=bytes([0xa5,len(raw)])+raw+bytes(128-len(raw));out=bytes(out)
 if any(x!=y and not at+4<=i<at+134 for i,(x,y) in enumerate(zip(base,out))):raise ValueError('Helper config patch escaped')
 return out,labels,{'base_sha256':sha(base),'configured_sha256':sha(out),'labels_sha256':sha(labels_blob),'config_address':labels['helper_config'],'path':path,'source_helper_default_disabled':True}
class HelperLoadThenSys(LoadThenSysClient):
 def __init__(self,delegate,configured,path,patch,base=None,labels_blob=None,clock=time.monotonic,sleep=time.sleep):
  from ac_contract import read_json
  manifest=read_json(bootstrap.HELPER_BUILD/'source-manifest.json')
  if not isinstance(base,bytes) or not isinstance(labels_blob,bytes) or sha(base)!=manifest['prg_sha256'] or sha(labels_blob)!=manifest['labels_sha256']:raise ValueError('Exact source-built HDC1 helper authority required')
  expected,labels,expected_patch=configure_helper(base,labels_blob,patch['path'])
  if configured!=expected or patch!=expected_patch:raise ValueError('Helper configured bytes escape constructor authority')
  if sha(configured)!=patch['configured_sha256'] or not re.fullmatch(r'/usb1/DOS64_TEST/[a-z0-9][a-z0-9_-]{0,63}/HD-CLOSE\.PRG',path):raise ValueError('Exact staged helper identity required')
  self.authority={'purpose':'owned-HDC1-target2-close-reopen-readonly','configured_sha256':sha(configured),'source_sha256':patch['base_sha256'],'sys_bytes':b'SYS2061\r','labels':{}};self.delegate=delegate;self.configured=configured;self.path=path;self.clock=clock;self.sleep=sleep;self.seconds=30;self.journal=lambda *a,**k:None;self.events=[]
  self.load_attempted=False;self.load_returned=False;self.sys_body_written=False;self.sys_go_attempted=False;self.sys_go_verified=False;self.start_resume_attempted=False;self.awaiting_start_resume=False;self.cancel_attempted=False
 def verify_loaded(self,ram):
  expected=self.configured[2:];end=0x801+len(expected)
  if len(ram)!=65536 or ram[0x801:end]!=expected:raise ValueError('Entire visible helper differs before SYS')
  return {'visible_start':0x801,'visible_end_exclusive':end,'all_helper_bytes_exact':True,'hidden_PRG_verified':False,'scope':'entirehelper is below4000; no hidden ranges'}
class CompositeClient:
 def __init__(self,native,helper):self.native=native;self.helper=helper;self.client=native.client;self.helper_active=False;self.helper_descriptor=None;self.helper_ack_cleared=False
 def __getattr__(self,name):return getattr(self.native,name)
 @property
 def journal(self):return self.native.journal
 @journal.setter
 def journal(self,value):self.native.journal=value;self.helper.journal=value
 def request(self,method,route,data=None,content_type=None):
  if method=='POST' and route=='runners:run_prg':
   if data==self.helper.configured:
    self.helper_active=True;self.helper_descriptor=None;self.helper_ack_cleared=False
    return self.helper.request(method,route,data,content_type)
   self.helper_active=False;self.helper_descriptor=None;self.helper_ack_cleared=False
  match=re.fullmatch(r'machine:writemem\?address=([0-9a-fA-F]{1,4})',route)
  if self.helper_active and method=='POST' and match:
   if content_type!='application/octet-stream' or not isinstance(data,bytes):raise ValueError('Exact helper immutable write payload required')
   address=int(match[1],16)
   if address==0x6004 and data==b'\0':self.helper_ack_cleared=True;self.helper_descriptor=None
   elif address==0x6009 and len(data)==8 and self.helper_ack_cleared:
    op=data[1];count=int.from_bytes(data[2:4],'little');offset=int.from_bytes(data[4:8],'little')
    if not (op==1 and 1<=count<=512 and offset<=20*1024*1024 or op==2 and count==0 and offset==0):raise ValueError('Helper descriptor is not bounded readonly READ or CLOSE')
    self.helper_descriptor=data
   elif address==0x6004 and data==b'G' and self.helper_descriptor is not None:self.helper_ack_cleared=False
   else:raise ValueError('Write escapes exact HDC1 descriptor/GO envelope')
   return self.client.put('machine:writemem?address='+format(address,'X')+'&data='+data.hex().upper())
  return self.native.request(method,route,data,content_type)
 def put(self,route):
  if route=='machine:resume' and self.helper.awaiting_start_resume:return self.helper.put(route)
  return self.native.put(route)
 def read(self,*a,**k):return self.native.read(*a,**k)
class HelperSession:
 def __init__(self,client,configured,labels,clock=time.monotonic,sleep=time.sleep):self.client=client;self.configured=configured;self.labels=labels;self.clock=clock;self.sleep=sleep;self.sequence=0
 def write(self,at,b):self.client.request('POST','machine:writemem?address='+format(at,'X'),b,'application/octet-stream')
 def mailbox(self):
  b=self.client.read(0x6000,32)
  if len(b)!=32 or b[:4]!=b'DHC1':raise ValueError('Helper mailbox identity missing')
  return b
 def await_state(self,initial=False):
  end=self.clock()+12
  while self.clock()<end:
   b=self.mailbox()
   if b[4]==0xe1:raise RuntimeError('HDC1 firstfailure/cleanup: '+b.hex())
   if b[4]==(0x11 if initial else 0xa5):return b
   self.sleep(.02)
  raise TimeoutError('HDC1 operation deadline; no command retry')
 def verify_code(self):
  actual=bytearray(self.client.read(0x801,len(self.configured)-2));expected=self.configured[2:]
  if len(actual)!=len(expected):raise ValueError('Helper executable capture incomplete')
  for name,buffer in [('dos64_uci_upload_operand','dos64_uci_command'),('dos64_uci_drain_operand','dos64_uci_data')]:
   at=self.labels[name]-0x801;value=int.from_bytes(actual[at:at+2],'little');start=self.labels[buffer]
   if value!=0xffff and not start<=value<start+896:raise ValueError('Helper mutable operand escapes reviewed buffer')
   actual[at:at+2]=expected[at:at+2]
  if bytes(actual)!=expected:raise ValueError('Helper executable differs outside validated operands')
 def load(self):
  self.client.put('machine:pause');self.client.request('POST','runners:run_prg',self.configured,'application/octet-stream');self.client.put('machine:resume');b=self.await_state(True);self.client.put('machine:pause');self.verify_code()
  if b[19:21]!=b'\xa5\xa5' or b[5:7]!=b'\0\0' or b[8]!=1 or b[23]&7!=7 or b[24]&7!=5 or b[25]&0x0c!=4:raise ValueError('Initial target2 CLOSE/reopen did not settle')
  info=self.client.read(0x6100,b[28])
  if not 13<=len(info)<=75 or info[:4]!=(20*1024*1024).to_bytes(4,'little'):raise ValueError('Reopened INFO extent differs')
  return {'initial_close_A5':True,'reopened_readonly_A5':True,'INFO_hex':info.hex(),'native_handle':b[8]}
 def command(self,op,offset=0,count=0):
  self.client.put('machine:pause');before=self.mailbox()
  if before[4] not in (0x11,0xa5) or before[5] or before[31]:raise ValueError('Helper cannot accept new operation')
  if op not in (1,2) or op==1 and not(0<=offset<=20*1024*1024 and 1<=count<=512):raise ValueError('Exact bounded readonly helper operation required')
  self.sequence=(self.sequence+1)&255;body=bytes([self.sequence,op])+count.to_bytes(2,'little')+offset.to_bytes(4,'little')
  self.write(0x6004,b'\0');self.write(0x6009,body)
  if self.client.read(0x6009,len(body))!=body:raise ValueError('Helper descriptor readback differs beforeGO')
  self.write(0x6004,b'G');self.client.put('machine:resume');b=self.await_state();self.client.put('machine:pause')
  if b[9:17]!=body:raise ValueError('Helper acknowledged another descriptor')
  self.verify_code()
  if op==2:
   if b[8]!=0 or b[31]!=0xa5:raise ValueError('Final native target2 CLOSE not proven')
   return b''
  n=int.from_bytes(b[17:19],'little')
  if n>count:raise ValueError('Helper returned excess bytes')
  data=self.client.read(0x6200,n) if n else b''
  if len(data)!=n:raise ValueError('Helper data capture incomplete')
  return data
