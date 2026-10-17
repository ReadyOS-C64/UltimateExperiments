"""Offline admissions only; no network or hardware activation."""
from pathlib import Path
import hashlib,json,re,struct
HELPER_SHA='4977b66b5595c7e7eb88b92b161f04eb5507b26c75ddaf6aef7d6505f7d28992'
MAIN_SHA='c7a14a3a119e18ea4949efb8f37493df7afeeb1dc97d421561544cf7f79a8f93'
LABELS_SHA='33543080df6e4296aed14d4284890309cb4ff51db54ada035f830ff9c8493364'
MAP_SHA='d957159ec0467c122dacb5b9841ac78f77f05dc76436e13aa638ebec8fd41f9c'
HELPER_LABELS={'close_config':0x14ba,'close_config_end':0x14d0,'close_entry':0x080d,'close_idle':0x093a,'close_nmi':0x09de,'entered':0x14d0,'dos64_uci_upload_operand':0x0dee,'dos64_uci_drain_operand':0x0e94}
sha=lambda b:hashlib.sha256(b).hexdigest()
class Contract:
 def __init__(self,prg,labels_blob,maptext,path):
  if sha(prg)!=MAIN_SHA:raise ValueError('Exact source-boundc7 runtime required')
  if type(labels_blob)is not str or sha(labels_blob.encode())!=LABELS_SHA or type(maptext)is not str or sha(maptext.encode())!=MAP_SHA:raise ValueError('Exact current source-bound labels/map required')
  labels={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in labels_blob.splitlines()if l.startswith('al ')}
  if not isinstance(path,bytes)or not 2<=len(path)<128 or not path.startswith(b'/')or b'\0'in path:raise ValueError('Explicit current C path required')
  self.prg=prg;self.labels=labels;self.path=path
  self.spans=[]
  for line in maptext.split('Segment list:',1)[1].split('Exports list',1)[0].splitlines():
   match=re.fullmatch(r'([A-Z]+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]+',line)
   if match and match[1]in ['BASIC','CODE','DEVICECODE']:
    a,b=int(match[2],16),int(match[3],16);self.spans.append((a,b+1))
  if len(self.spans)!=3:raise ValueError('Exact source map ranges required')
 def admit(self,ram):
  if len(ram)!=65536 or ram[0]&7!=7 or ram[1]&7!=5:raise ValueError('Coherent native35 RAM required')
  def get(n,k=1):a=self.labels[n];return ram[a:a+k]
  # Exact public executable spans, not serialized startup assets or current
  # overlays; HDBIOS copied resident source is bound separately.
  ignored=set()
  for name,window in [('dos64_uci_upload_operand',(0xc100,0xc47f)),('dos64_uci_drain_operand',(0xc480,0xc7ff))]:
   a=self.labels[name];value=int.from_bytes(ram[a:a+2],'little')
   if not window[0]<=value<=window[1]:raise ValueError('MAIN UCI operand outside bounded queue')
   ignored.update([a,a+1])
  for a,b in self.spans:
   for address in range(a,b):
    if address not in ignored and ram[address]!=self.prg[address-0x801+2]:raise ValueError('Runtime executable source differs '+hex(address))
  if ram[0xf000:0xfe00]!=self.prg[0xa000-0x801+2:0xae00-0x801+2]:raise ValueError('Resident HDBIOS source differs')
  d=get('dos64_native_diag',19)
  if d[0]!=5 or d[1:4]!=bytes(3)or d[4]!=0xa5:raise ValueError('Successful actual snapshot/cacheflush ACK required')
  for name in ['dos64_overlay_busy','dos64_overlay_error','dos64_pit_poll_error','hd_uncertain','dos64_files_error','dos64_uci_error','dos64_uci_recovery_failed']:
   if get(name)!=b'\0':raise ValueError('Unsafe pending/error '+name)
  if get('hdb_active')not in [b'\0',b'\2']or get('hdc_phase')!=b'\2':raise ValueError('HD native owner not quiescent')
  if get('dos64_files_state')!=b'\2'or get('dos64_uci_state')not in [b'\0',b'\x09']:raise ValueError('FILES/UCI not terminal quiet')
  if get('dos64_files_handle')!=b'\1'or get('dos64_files_target')!=b'\2'or get('dos64_files_owned_target')!=b'\2'or get('hdc_target')!=b'\2':raise ValueError('Exact still-open C target2 authority required')
  if get('hdc_path_len')[0]!=len(self.path)+1 or get('hdc_path',len(self.path)+1)!=self.path+b'\0':raise ValueError('C source path identity mismatch')
  # All32 guest cache frames must have no dirty bit after real cacheflush.
  flags=get('dos64_cache_flags',32) if 'dos64_cache_flags'in self.labels else ram[0xe940:0xe960]
  if any(v&2 for v in flags):raise ValueError('Dirty guest cache after snapshot')
  return {'schema':1,'purpose':'CURRENTC7_C_TARGET2_CLOSE_ONLY','MAIN_sha256':MAIN_SHA,'C_path':self.path.decode('ascii'),'paused_stage5':True,'cacheflush_ACK':True,'known_C_handle_open':True,'known_C_closed':False,'FILES_target':2,'RAM_sha256':sha(ram),'runtime_executable_and_resident_source_exact':True,'host_fields_are_receipt_not_activation_capability':True}

def configure(base,labels,nonce,contract,ram):
 if any(labels.get(k)!=v for k,v in HELPER_LABELS.items()):raise ValueError('Exact helper ABI required')
 if type(contract)is not Contract or len(nonce)!=16 or not any(nonce)or sha(base)!=HELPER_SHA:raise ValueError('Exact native source and fresh RAM admission/nonce required')
 contract.admit(ram) # Recompute raw-source/owner predicates; no positive observation flag.
 a=labels['close_config']-0x801+2;b=labels['close_config_end']-0x801+2
 if b-a!=22 or base[a:b]!=b'DCC1\0\2'+bytes(16):raise ValueError('Exact disabled helper configuration required')
 out=bytearray(base);out[a+4]=0xa5;out[a+6:b]=nonce;return bytes(out)

def result(ram,configured,labels,nonce):
 if any(labels.get(k)!=v for k,v in HELPER_LABELS.items()):raise ValueError('Exact helper ABI required')
 if len(ram)!=65536:raise ValueError('Full terminal RAM required')
 # UCI operand self-modification remains bounded and source-bound.
 ignored=set()
 for name in ['dos64_uci_upload_operand','dos64_uci_drain_operand']:
  a=labels[name];value=int.from_bytes(ram[a:a+2],'little');window=(0xc101,0xc101)if 'upload'in name else(0xffff,0xffff)
  if not window[0]<=value<=window[1]:raise ValueError('UCI operand outside private queue')
  ignored.update([a,a+1])
 ignored.add(labels['entered'])
 for i,v in enumerate(configured[2:]):
  a=0x801+i
  if a not in ignored and ram[a]!=v:raise ValueError('Close helper native source differs')
 d=ram[0x6000:0x6030]
 if d[:5]!=b'DCC1\xa5'or d[5]!=0 or d[8:12]!=b'\0\1\1\2'or d[16:32]!=nonce or d[33]!=0:raise ValueError('Native close lacks exact knownclosed/quiet/one-attempt')
 if d[6]not in [0,3]or d[7]!=0 or d[32]not in [0,9,10]or d[35]&7!=5 or d[36]&12!=4:raise ValueError('Native terminal close error/bank/IRQ contract')
 return {'state':'KNOWN_CLOSED_QUIET','target':2,'CLOSE_attempts':1,'native_FILES_error':d[6],'UCI_error':d[7],'native_poll_count':int.from_bytes(d[14:16],'little'),'nonce':nonce.hex(),'helper_source_and_SMC_verified':True,'REU_reads_writes':0,'OPEN_READ_WRITE_SEEK_commands':0,'original_main_resumable':False}
