"""Fixed source-gated stream→one native-file restore→stream capability.
No FTP, arbitrary files/REU/descriptor writes, native retry, or deadline reset.
"""
from hybrid_transport import HybridREST
from numeric_transport import RepairREST
from cold_transport import ColdREST
from transport import INVENTORY
from host_stream import SIZE
from native_file import sha
PROFILE='configs/U64%20Specific%20Settings/Turbo%20Control?value='
TEMP=PROFILE+'Manual'
RESTORE=PROFILE+'C64U%20Turbo%20Registers'
CONFIGURED='5c709f00cf2a359856eb2866ffb0c3f4f5a8af35d2024992e97573ad423d23cc'
class FastREST(HybridREST):
 def __init__(self,host,streams,service,baseline,**kw):
  # Do not acquire the predecessor's scratch command capability.
  if set(streams)!={'initial','final'}or sha(service)!=CONFIGURED or streams['initial'][1]==streams['final'][1]:raise ValueError('Exact two streams/historical native file source')
  self.streams=streams;self.service=service;self._baseline=baseline
  ColdREST.__init__(self,host,streams['initial'][0],**kw)
  self.mode='activate';self.role=None;self._permit=None;self.stream_done=set();self._last_full=None;self.reset_uncertain=False;self.global_full=0;self.global_acks=0;self.response_meta={};self.restore_done=False;self.restore_start_attempted=False
 _exchange=RepairREST._exchange
 _retain_write=RepairREST._retain_write
 _retain_failure=RepairREST._retain_failure
 def _allowed(self,m,r,body):
  reads={(0,65536),(0x801,len(self.source)-2)}
  if self.role in self.streams:reads|={(0x3e00,52),(0x801,SIZE)}
  if self.role=='restore':reads|={(0x6000,32)}
  readonly=m=='GET'and body is None and r in INVENTORY
  if m=='GET'and body is None and r.startswith('machine:readmem?'):
   try:
    q=dict(v.split('=')for v in r.split('?')[1].split('&'));readonly=set(q)=={'address','length'}and(int(q['address'],16),int(q['length']))in reads
   except (ValueError,KeyError):readonly=False
  control=m=='PUT'and r in {'machine:pause','machine:resume','machine:reset'}and body is None
  profile=m=='PUT'and body is None and getattr(self,'_profile_permit',None)==r
  write=self._permit is not None and(m,r,body)==self._permit
  if write and self.cleanup_mode:raise ValueError('Cleanup cannot load/source/queue/ACK or restart native')
  if(write or profile or control)and self.archive_write is None:raise ValueError('Durable raw response required before mutation')
  if not(readonly or control or profile or write):raise ValueError('Outside exact one-shot native-file/stream capability')
 def configure_turbo(self,role,deadline):
  if role not in ['temporary','restore']or self._turbo_original!=('C64U Turbo Registers','64')or (role=='restore')!=self.cleanup_mode:raise ValueError('Only captured original one-field PUT policy')
  if role=='restore'and'turbo_temporary'not in self.calls:raise ValueError('No restore without owned attempt')
  self._once('turbo_'+role);route=RESTORE if role=='restore'else TEMP;self._profile_permit=route
  try:return self._exchange('PUT',route,deadline)
  finally:self._profile_permit=None
 def cold_begin(self,role):
  allowed=(role=='initial'and self.mode=='activate')or(role=='restore'and self.mode=='initial_done'and self.stream_done=={'initial'})or(role=='final'and self.mode=='restore_native'and self.restore_done)
  if not allowed:raise ValueError('Monotone single native-file restoration phases')
  self._once('cold_'+role);self.role=role;self.mode=role+'_cold';self.source=self.streams[role][0]if role in self.streams else self.service
  if role in self.streams:self.ack_next=1;self.ack_attempted=set();self.cancel_attempted=False;self.full_count=0;self._last_full=None
 def write(self,*args):
  if len(args)!=2:raise ValueError('No host REU command/descriptor capability')
  return HybridREST.write(self,*args)
 def control(self,kind,key,deadline):
  if key=='restore_start_resume':
   if self.restore_start_attempted:raise ValueError('No second autonomous restore start')
   self.restore_start_attempted=True
  return super().control(kind,key,deadline)
 def begin(self,*args):raise ValueError('No scratch/native block commands')
 def finish_stream(self,path):return HybridREST.finish_stream(self,path)
