"""Offline predicate only: never reads/writes device, ACK, resume or reset.
Live use requires a separately reviewed coherent-pause/no-retry controller.
"""
from pathlib import Path
import hashlib,json
from copy_reader_host import Source
W=Path(__file__).resolve().parent
class Admission:
 def __init__(self):
  m=json.loads((W/'PREDECESSOR_LAUNCH.json').read_text());self.m=m
  self.source=Source((W/'copy-reader.prg').read_bytes(),(W/'copy-reader.labels').read_text(),m['files'][m['reader']],m['files'][m['reader_labels']],m['home'].encode(),bytes.fromhex(m['purpose_nonce']))
  self.l={}
  for line in (W/'copy-reader.labels').read_text().splitlines():
   if line.startswith('al '):
    _,a,n=line.split();n=n.lstrip('.');a=int(a,16)
    if not(n.startswith(('_cr_p_','_files_','_uci_'))or n in ['sp','_np_mapping']):continue
    if n in self.l and self.l[n]!=a:raise ValueError('Ambiguous exact linker label')
    self.l[n]=a
  self.reference=(W/'WAIT76-reference.bin').read_bytes();self.wait(self.reference)
 def at(self,n):return self.l[n]
 def wait(self,raw):
  self.source.frame(raw,76)
  # The old GO75 consumed/cleared SEQ. Ambiguous LE16 SEQ76 writes4C,00;
  # its only permitted fresh values are0000 or4C00, never75/otherframe.
  if raw[0x260:0x264]not in[b'\0\0\0\0',b'\x4c\0\0\0']:raise ValueError('Only ambiguous SEQ76 with CANCEL/GOzero')
  for n,v in {'_cr_p_fill':32768,'_files_count':512,'_files_actual':512}.items():
   if int.from_bytes(raw[self.at(n):self.at(n)+2],'little')!=v:raise ValueError('Exact WAIT completed read count '+n)
  for n,v in {'_cr_p_frame_live':1,'_cr_p_eof':0,'_cr_p_copy_attempts':1,'_cr_p_aborted':0,'_files_state':2,'_files_error':0,'_files_transport_error':0,'_files_count_known':1,'_files_mode':1,'_files_target':2,'_files_owned_target':2,'_files_op':4,'_uci_error':0,'_uci_recovery_failed':0}.items():
   if raw[self.at(n)]!=v:raise ValueError('Exact completed readonly WAIT '+n)
  return {'frame':76,'offset':2490368,'readonly_handle':1,'COPY_uncertain':False,'CWD_restored':True,'GO_zero':True,'cancel_one_byte_only':0x262,'mapping_epoch':76,'mapping_receipt':raw[self.at('_np_mapping'):self.at('_np_mapping')+8].hex(),'native_clock_revalidated_on_resume':True,'Cstack_bounded_not_hardware_frames_retired':True}
 def fresh_wait(self,raw):
  fact=self.wait(raw)
  # Exact retained payload, header, controls and private transport ledger,
  # except the single ambiguous two-byte SEQ write. Never authorize from it alone.
  for lo,hi in [(0x200,0x230),(0x270,0x28d),(0x300,0x30b),(0x4000,0xc000),(self.at('_cr_p_previous_cwd'),self.at('_cr_p_cwd_changed')+1),(self.at('_cr_p_used'),self.at('_cr_p_mismatch')+4),(self.at('_files_state'),self.at('_files_state')+25)]:
   if raw[lo:hi]!=self.reference[lo:hi]:raise ValueError('Retained WAIT76/private ledger changed')
  return fact
 def failed_closed(self,raw):
  s=self.source;s.verify(raw)
  if raw[self.at('_cr_p_phase')]!=12 or raw[self.at('_cr_p_first')]not in[7,8]or raw[self.at('_cr_p_cleanup')]!=0:raise ValueError('Only cancel/elapsed terminal with clean closure')
  for n,v in {'_cr_p_copy_uncertain':0,'_cr_p_cwd_changed':0,'_cr_p_initialclosed':1,'_cr_p_raw':0,'_files_handle':0,'_uci_recovery_failed':0}.items():
   if raw[self.at(n)]!=v:raise ValueError('Private knownclosed '+n)
  if raw[self.at('_uci_state')]not in[9,10]or raw[self.at('_uci_state')]==10 and raw[self.at('_uci_error')]<3:raise ValueError('Private engine not quiet')
  if raw[self.at('sp'):self.at('sp')+2]!=b'\xff\xcf':raise ValueError('cc65 return stack required, not hardware-frame retirement')
  if int.from_bytes(raw[self.at('_cr_p_frame'):self.at('_cr_p_frame')+2],'little')!=76 or int.from_bytes(raw[self.at('_cr_p_offset'):self.at('_cr_p_offset')+4],'little')!=2490368:raise ValueError('No advancement beyond owned frame76')
  return {'known_closed':True,'frame':76,'read':2490368,'native_first':raw[self.at('_cr_p_first')],'mapping_epoch':0,'permitted_next':'one documented coldreset after durable fresh fullRAM; no source replacement before reset','original_campaign_stays_failed':True}
