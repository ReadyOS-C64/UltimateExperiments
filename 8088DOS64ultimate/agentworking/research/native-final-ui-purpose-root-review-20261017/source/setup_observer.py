"""Read-only source/private-admission observer. No network, entry or input writes.
Caller pins the binding-record digest in its independently reviewed purpose.
"""
import hashlib,json,re
sha=lambda b:hashlib.sha256(b).hexdigest()
def labels(blob):
 d={}
 for a,n in re.findall(rb'^al ([0-9A-Fa-f]+) \.(\S+)',blob,re.M):d.setdefault(n.decode(),set()).add(int(a,16))
 return d
class SetupObserver:
 def __init__(self,record,expected_sha,files):
  if type(record)is not bytes or type(expected_sha)is not str or not re.fullmatch('[a-f0-9]{64}',expected_sha)or sha(record)!=expected_sha:raise ValueError('Exact purpose-pinned observer binding')
  j=json.loads(record)
  if j.get('schema')!=1 or j.get('role')!='SETUP_78E_BANKGUARD_POSTENTRY'or set(j['files'])!=set(files):raise ValueError('Exact SETUP observer source inventory')
  for n,b in files.items():
   if type(b)is not bytes or j['files'][n]!={'sha256':sha(b),'bytes':len(b)}:raise ValueError('Bound source differs '+n)
  self.record_sha=expected_sha;self.files=dict(files);self.prg=files['setup.prg'];self.l=labels(files['setup.labels']);self.map=files['setup.map'].decode();self.modules={};current=None
  for row in self.map.split('Segment list:',1)[0].splitlines():
   m=re.fullmatch(r'([^\s:]+)\.o:',row)
   if m:current=m[1];self.modules[current]={}
   m=re.fullmatch(r'\s+(\w+)\s+Offs=([0-9A-F]+)\s+Size=([0-9A-F]+).*',row)
   if m and current:self.modules[current][m[1]]=(int(m[2],16),int(m[3],16))
  self.segments={}
  for row in self.map.split('Segment list:',1)[1].split('Exports list',1)[0].splitlines():
   m=re.fullmatch(r'([A-Z][A-Z0-9_]*)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]+',row.strip())
   if m:self.segments[m[1]]=(int(m[2],16),int(m[3],16)+1,int(m[4],16))
  if self.prg[:2]!=b'\x01\x08'or self.at('setup_boot')!=0x80d or self.at('__HIGH_CODE_RUN__')!=0xf700 or self.at('__AUX_CODE_RUN__')!=0xc3a0 or self.at('__BOOT_DIAG_LOAD__')!=0xb000 or self.at('__BOOT_DIAG_RUN__')!=0xc843 or self.at('__FILE_DIAG_RUN__')!=0xbfa0 or self.segments['UCIBUFFER']!=(0xc000,0xc3a0,928):raise ValueError('Qualified bankguard/compact SETUP map required')
  self.private={}
  self.resolve('coordinator','source/coordinator.s','BSS');self.resolve('startup_close','source/startup_close.s','BSS');self.resolve('source_load','source_load.s','HIGHBSS');self.resolve('setup_overlay','setup_overlay.s','BSS');self.resolve('bulk_context','bulk_context.s','BSS')
  # Compiler output locates installed field, not an assumed C struct offset.
  install=files['source_load.s'].decode().split('.proc\t_sl_install:',1)[1].split('.endproc',1)[0]
  m=re.search(r'lda\s+#\$A5\s+sta\s+_q\+(\d+)',install)
  if not m or 'jsr     _sl_copy_code'not in install:raise ValueError('Exact native installed-last copy/readback gate')
  self.installed=self.p('source_load','_q')+int(m[1]);size=self.private['source_load'][1]['_q'][1]
  if not 0<=int(m[1])<size:raise ValueError('Installed private member range')
  self.bc_handle_offsets=tuple(map(int,re.findall(r'lda\s+_saved\+(\d+)',files['bulk_context.s'].decode().split('.proc\t_bc_files_closed:',1)[1].split('.endproc',1)[0])))
  if self.bc_handle_offsets!=(167,345)or self.private['bulk_context'][1]['_saved'][1]!=356:raise ValueError('Actual two-context private FILES snapshot ABI')
  self.smc={}
  for n,o in [('uci_status_read',0),('uci_control_write',0),('uci_id_read',1),('uci_command_write',1),('uci_data_read',2),('uci_stat_read',3)]:self.smc[self.at(n)+1]=(0xdf1c+o,0xdf1c+o)
  self.smc[self.at('read')+1]=(self.at('_uci_command'),self.at('_uci_command')+159)
  self.smc[self.at('store')+1]=(self.at('_uci_data'),self.at('_uci_data')+511)
  if len(self.smc)!=8:raise ValueError('Exact eight UCI instruction operands')
  self.ranges=[]
  for n in ['BASIC','BOOT','DEVICECODE','FILECODE','CODE','RODATA','UI_CODE','UI_RO']:
   a,b,size=self.segments[n]
   if b-a!=size:raise ValueError('Contiguous immutable segment '+n)
   self.add_range(n,a,a,size)
  self.add_range('HIGH_CODE',self.at('__HIGH_CODE_LOAD__'),self.at('__HIGH_CODE_RUN__'),self.at('__HIGH_CODE_SIZE__'))
  self.add_range('AUX',self.at('__AUX_CODE_LOAD__'),self.at('__AUX_CODE_RUN__'),self.at('__AUX_CODE_SIZE__')+self.at('__AUX_RO_SIZE__'))
  for n in ['BOOT_DIAG','FILE_DIAG']:self.add_range(n,self.at('__'+n+'_LOAD__'),self.at('__'+n+'_RUN__'),self.at('__'+n+'_SIZE__'))
 def at(self,n):
  v=self.l.get(n,set())
  if len(v)!=1:raise ValueError('Missing/ambiguous linker export '+n)
  return next(iter(v))
 def resolve(self,module,file,segment):
  off=0;current=None;found={}
  for row in self.files[file].decode().splitlines():
   row=row.split(';',1)[0].strip();m=re.match(r'\.segment\s+"([A-Z_]+)"',row)
   if m:current=m[1];continue
   if current!=segment:continue
   m=re.match(r'([A-Za-z_]\w*):\s*(.*)',row)
   if m:found[m[1]]=[off,0];last=m[1];row=m[2]
   m=re.match(r'\.res\s+(\$[0-9A-Fa-f]+|\d+)(?:\s*,.*)?$',row)
   if m:
    n=int(m[1][1:],16)if m[1].startswith('$')else int(m[1]);off+=n
    if 'last'in locals():found[last][1]+=n;del last
  module_off,module_size=self.modules[module][segment]
  if off!=module_size:raise ValueError('Full private '+module+' '+segment+' size mismatch '+str((off,module_size)))
  run=self.segments[segment][0]+module_off
  # Every visible exported BSS anchor must agree with module/asm reconstruction.
  for n,(a,size)in found.items():
   if n in self.l and len(self.l[n])==1 and self.at(n)!=run+a:raise ValueError('Exported private-layout anchor differs '+n)
  self.private[module]=(run,found)
 def p(self,module,name):return self.private[module][0]+self.private[module][1][name][0]
 def add_range(self,name,load,run,n):
  data=self.prg[load-0x801+2:load-0x801+2+n]
  if n<=0 or len(data)!=n or run<0x801 or run+n>0xfffa or not(run+n<=0xd000 or run>=0xe000):raise ValueError('Complete readable immutable source range '+name)
  self.ranges.append((name,run,data))
 def source(self,ram,live_ui=True,terminal=False):
  if type(ram)is not bytes or len(ram)!=65536 or ram[0]&7!=7 or ram[1]&7!=5:raise ValueError('Whole coherently paused mapped35 RAM')
  ignored={x for a in self.smc for x in [a,a+1]}
  for name,a,b in self.ranges:
   if not live_ui and name in['UI_CODE','UI_RO']:continue
   for i,v in enumerate(b):
    if a+i not in ignored and ram[a+i]!=v:raise ValueError('Immutable '+name+' byte differs at%04X'%(a+i))
  for a,(lo,hi)in self.smc.items():
   v=int.from_bytes(ram[a:a+2],'little')
   if not lo<=v<=hi and not(a in[self.at('read')+1,self.at('store')+1]and v==0xffff):raise ValueError('Bounded UCI operand differs')
  if int.from_bytes(ram[0xfffa:0xfffc],'little')!=self.at('ps_rti')or ram[self.at('ps_rti')]!=0x40:raise ValueError('Owned RAM NMI RTI/vector')
  sp=int.from_bytes(ram[self.at('sp'):self.at('sp')+2],'little')
  if not 0xcd00<=sp<=0xcfff or(terminal and sp!=0xcfff):raise ValueError('Bounded UI stack / terminal allframes returned required')
 def observe(self,ram):
  self.source(ram)
  def byte(module,n):return ram[self.p(module,n)]
  if byte('coordinator','state')!=2 or byte('coordinator','error')or byte('coordinator','cancelled')or byte('coordinator','phase_verified')!=1:raise ValueError('Private coordinator authentic UI phase not admitted')
  sc=self.p('startup_close','sc_private')
  if ram[sc:sc+6]!=b'\2\0\0\2\3\0':raise ValueError('Private startup CLOSE1/2 not known successful')
  if ram[self.installed]!=0xa5:raise ValueError('Private installed-last HIGH/AUX proof absent')
  so=self.p('setup_overlay','_ledger');v=ram[so:so+10];ticket=int.from_bytes(v[8:10],'little');rc=self.p('coordinator','ticket');expected=self.at('_rc_expected_ticket')
  if v[:8]!=b'\2\1\0\0\0\0\0\1'or not ticket or ram[rc:rc+2]!=v[8:10]or ram[expected:expected+2]!=v[8:10]:raise ValueError('Private SO admitted UI ticket/first-cause differs')
  owned=self.p('setup_overlay','_owned')
  if ram[owned:owned+7]!=b'\xa5\0\0\x40\0\x10\x27'or any(ram[owned+7:owned+135]):raise ValueError('Private original owner/4MiB/10000tick admission differs')
  if byte('setup_overlay','_started')!=1 or any(byte('setup_overlay',n)for n in ['_waiting','_leased','_handle']):raise ValueError('SO source operation still owns/awaits transport')
  bc=self.p('bulk_context','_saved');active=byte('bulk_context','_active');uilease=byte('bulk_context','_ui')
  if byte('bulk_context','_initialized')!=1 or active not in[0,1]or any(ram[bc+n]for n in self.bc_handle_offsets)or ram[self.at('dos64_files_handle')]:raise ValueError('Private actual FILES/context handles not closed')
  return {'status':'SOURCE_AND_AUTHENTIC_INITIAL_UI_ADMISSION_OBSERVED','binding_sha256':self.record_sha,'immutable_ranges':[(n,a,len(b),sha(b))for n,a,b in self.ranges],'private_installed_last_A5':True,'private_startup_CLOSE_mask':3,'private_phase':'UI','private_ticket':ticket,'native_human_input_verified':False,'public_positive_observations_used':False,'browser_directory_lease':uilease,'current_UCI_state':ram[self.at('dos64_uci_state')],'takeover_or_reset_authorized':False,'CPU_P_register_observed':False,'observation_context':'source/private admission only; physical context supplied by validated purpose'}

 def terminal(self,ram):
  self.source(ram,live_ui=False,terminal=True)
  def byte(m,n):return ram[self.p(m,n)]
  state=byte('coordinator','state');error=byte('coordinator','error')
  if state not in[5,7]:raise ValueError('Native SETUP terminal not reached')
  sc=self.p('startup_close','sc_private')
  if ram[sc:sc+6]!=b'\2\0\0\2\3\0':raise ValueError('Original startup close authority absent')
  if state==5 and byte('coordinator','failure_closed')!=1:raise ValueError('Native failure explicitly unknown closure')
  bc=self.p('bulk_context','_saved');active=byte('bulk_context','_active');saved_size=self.private['bulk_context'][1]['_ledger'][1]//2;ledger=self.p('bulk_context','_ledger')
  if byte('bulk_context','_initialized')!=1 or active not in[0,1]or byte('bulk_context','_ui')or any(ram[bc+n]for n in self.bc_handle_offsets)or ram[self.at('dos64_files_handle')]or ram[ledger+active*saved_size]==1:raise ValueError('Current private FILES/lease pending or uncertain')
  u=ram[self.at('dos64_uci_state')];ue=ram[self.at('dos64_uci_error')];rf=ram[self.at('dos64_uci_recovery_failed')]
  if not(u in[0,9]or(u==10 and not rf and ue>=3)):raise ValueError('UCI not terminal quiet')
  if state==7:
   a=self.at('_rc_retained');so=self.p('setup_overlay','_ledger');layout=self.at('_rc_record_layout')
   if self.prg[layout-0x801+2:layout-0x801+10]!=b'\xb7\0\x86\0\x9a\0\xb5\0':raise ValueError('Native private record ABI differs')
   if error or ram[a+180]!=31 or ram[a+181]!=1 or ram[so:so+8]!=b'\2\3\0\0\0\0\0\0':raise ValueError('Private all-output/nativePUB retirement facts absent')
  return {'outcome':'COMPLETED_NATIVE_INSTALL'if state==7 else'STOPPED_NATIVE_UI'if error==0x13 else'NATIVE_FAILED_KNOWN_QUIET','native_state':state,'native_first_error':error,'known_closed_quiet':True,'all_frames_returned':True,'original_CPU_RAM_application_restore':False,'human_key_origin_not_provable_from_RAM_alone':True,'final_V1_acceptance':False}
