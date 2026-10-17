"""Pure source/private receipt admission, no IO or directory authority from public state."""
import hashlib,re,struct
EXPECTED_SHA=bytes.fromhex('78b941711081e5ee8b1e2855b1ca4d4876160f97a5dfdb1e475fa65a699d102c')
class DirectorySource:
 def __init__(self,prg,labels,prg_sha,labels_sha,root,nonce):
  if hashlib.sha256(prg).hexdigest()!=prg_sha or hashlib.sha256(labels.encode()).hexdigest()!=labels_sha:raise ValueError('Exact source cohort')
  if not re.fullmatch(rb'/usb1/DOS64_TEST/copy20m-[a-z0-9_-]{1,56}',root)or len(root)>81 or len(nonce)!=16 or not any(nonce):raise ValueError('Fixed fresh owned namespace/nonce')
  wanted=['_dp_control','_br_config','sp','ps_rti','runtime_init','fixture_return','owner_prelude_entry','_ps_init','_dp_init','_dp_step','_dp_result','_dp_cancel','_dp_p_first','_dp_p_phase','_dp_p_cleanup','_dp_p_initialclosed','_dp_p_mkdir_attempts','_dp_p_created','_dp_p_uncertain','_dp_p_verified','_dp_p_cwd_changed','_dp_p_raw','_dp_p_marker','_dp_p_readback','_files_handle','_uci_state','_uci_error','_uci_recovery_failed','uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store','_uci_command','_uci_data']
  self.labels={}
  for line in labels.splitlines():
   if line.startswith('al '):
    _,a,n=line.split();n=n.lstrip('.')
    if n in wanted:
     a=int(a,16)
     if n in self.labels and self.labels[n]!=a:raise ValueError('Ambiguous exact symbol')
     self.labels[n]=a
  self.low=int.from_bytes(prg[:2],'little');self.high=self.low+len(prg)-2
  if self.low!=0x801 or self.high>0x4000 or self.at('_dp_result')!=0x200 or self.at('_dp_cancel')!=0x260 or self.at('owner_prelude_entry')!=0x80d:raise ValueError('Exact native ABI')
  self.root=root;self.nonce=nonce;self.marker=b'DCR1'+nonce+EXPECTED_SHA;b=bytearray(prg[2:])
  for n,v in [('_dp_control',b'\xa5'+nonce+root.ljust(128,b'\0')),('_br_config',b'\xa5\2'+struct.pack('<I',0x400000)+root.ljust(128,b'\0'))]:
   a=self.at(n)-self.low;b[a:a+len(v)]=v
  self.body=bytes(b);self.configured=prg[:2]+self.body
  self.ports={self.at(n)+1:0xdf1c+o for n,o in [('uci_status_read',0),('uci_control_write',0),('uci_id_read',1),('uci_command_write',1),('uci_data_read',2),('uci_stat_read',3)]};self.dynamic={self.at('read')+1:(self.at('_uci_command'),896),self.at('store')+1:(self.at('_uci_data'),896)};self.mutable={a+i for a in [*self.ports,*self.dynamic]for i in [0,1]}
  if len(self.mutable)!=16:raise ValueError('Exact allowed SMC spans')
 def at(self,n):return self.labels[n]
 def verify(self,ram):
  if type(ram)is not bytes or len(ram)!=65536 or ram[0]&7!=7 or ram[1]&7!=5:raise ValueError('Coherent mapped35 fullRAM')
  for i,b in enumerate(self.body):
   if self.low+i not in self.mutable and ram[self.low+i]!=b:raise ValueError('Immutable native source')
  for a,v in self.ports.items():
   if int.from_bytes(ram[a:a+2],'little')!=v:raise ValueError('UCI source port')
  for a,(lo,n)in self.dynamic.items():
   v=int.from_bytes(ram[a:a+2],'little')
   if v!=0xffff and not lo<=v<lo+n:raise ValueError('UCI buffer span')
  if ram[0xfffa:0xfffc]!=self.at('ps_rti').to_bytes(2,'little')or ram[self.at('ps_rti')]!=0x40:raise ValueError('Safe source NMI')
 def receipt(self,ram):
  self.verify(ram);r=ram[0x200:0x254]
  if r!=b'DPR1\4\0\0\1\x10\1\1\1\0\0\0\0'+self.nonce+self.marker:raise ValueError('Exact directory OWNER terminal receipt')
  for n,v in {'first':0,'phase':16,'cleanup':0,'initialclosed':1,'mkdir_attempts':1,'created':1,'uncertain':0,'verified':1,'cwd_changed':0,'raw':0}.items():
   if ram[self.at('_dp_p_'+n)]!=v:raise ValueError('Private directory ledger '+n)
  for n in ['_dp_p_marker','_dp_p_readback']:
   if ram[self.at(n):self.at(n)+52]!=self.marker:raise ValueError('Private exact owner readback')
  if ram[self.at('_files_handle')]!=0 or ram[self.at('_uci_state')]!=9 or ram[self.at('sp'):self.at('sp')+2]!=b'\xff\xcf':raise ValueError('Known native quiet/allframes returned')
  return {'home':self.root.decode('ascii'),'nonce':self.nonce.hex(),'OWNER_sha256':hashlib.sha256(self.marker).hexdigest(),'native_source_sha256':hashlib.sha256(self.configured).hexdigest(),'mkdir_once':True,'OWNER_create_new':True,'OWNER_readback_exact':True,'EOF_zero':True,'known_closed':True,'CWD_CD_restore_ack':True,'REU_writes':0}
