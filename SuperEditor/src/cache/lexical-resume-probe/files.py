"""Actual File SaveAs/Open with established modeled KERNAL/DOS boundary only."""
from pathlib import Path
import json,hashlib
import test_editor_file_integration as filemodel
import test_cache_lexical_registered as reg

class Fixture(filemodel.IntegratedFiles,reg.automatic.Fixture):
 catalog=reg.automatic.Fixture.catalog
 def __init__(self,*args):
  self.fs={};self.channels={};self.trace=[];self.inject={};self.selected_in=self.selected_out=None
  self.st=0;self.dos=b'00, OK,00,00\r';self.directory=b'';self.actions=[];self.opens=[];self.dos_commands=[];self.service_steps=0
  reg.automatic.Fixture.__init__(self,*args)
 def key(self,byte,error=None,mods=0):
  return filemodel.IntegratedFiles.key(self,byte,error=error,mods=mods)

def save_reopen(f,data,tag,out):
 out.mkdir();canon=f.canonical();before=f.reu();cat=f.catalog();token=f.read(f.s['se_bc_arena'],5);ticket=f.get('se_bc_ticket',4);inc=f.get('se_bc_incarnation',4)
 name=('RETURN-'+tag).upper().encode();assert len(name)<=16
 f.start('f7','A');f.enter_name(name,True);f.settle();assert not f.get('se_e_error',1)and not f.get('se_f_owner',1)
 assert f.fs[name]==data and f.merged()==data and f.document()==data
 assert f.get('se_h_saved',4)==f.get('se_h_current',4)and f.get('se_f_current_device',1)==8
 assert f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==name
 assert f.read(f.s['se_bc_arena'],5)==token and f.get('se_bc_ticket',4)==ticket and f.get('se_bc_incarnation',4)==inc
 # The unchanged source is already committed/clean, so SaveAs neither alters
 # source/history/clip nor writes any REU payload. Filename/savepoint are RAM.
 assert f.canonical()==canon,'cleanSaveAs changed source/history/group/clip'
 assert f.reu()==before and f.catalog()==cat and f.read(0xc600,1024)==f.shim
 before=f.reu();old_flags=f.get('se_bc_flags',1)
 f.start('f7','O');f.enter_name(name,True);f.settle()
 assert not f.get('se_e_error',1)and not f.get('se_f_owner',1)and f.merged()==data and f.document()==data
 assert f.get('se_bc_incarnation',4)==(inc+1)&0xffffffff and f.get('se_bc_ticket',4)==0
 assert f.get('se_bc_flags',1)==2 and not any(f.get(n,1)for n in('se_bc_head','se_bc_tail','se_bc_count'))
 assert f.get('se_h_saved',4)==f.get('se_h_current',4)==f.get('se_h_counter',4)==1 and f.get('se_h_end',2)==f.get('se_h_cursor',2)==0
 assert f.read(f.s['se_bc_arena'],5)==bytes(5),'actualOPENmustretireold53descriptor'
 assert f.catalog()==cat and f.read(0xc600,1024)==f.shim
 # Successful OPEN may write exactly the new original bytes and the initialized
 # 1024-byte metadata leaf. The borrowed append, history, clip, FC, FD, code,
 # old/unreferenced data, and all remaining16MiB must be unchanged.
 after=f.reu();wanted=bytearray(before);spans=[]
 def allow_object(symbol,kind,count):
  cap=f.read(f.s[symbol],5);ident=cap[0];assert f.m.read(f.s['object_owner']+ident)==kind
  at=0
  while at<count:
   logical=f.m.read(f.s['object_extents']+ident*16+(at>>16));bank=f.m.read(f.s['se_reu_map']+logical)
   assert f.m.read(f.s['se_reu_logical_owner']+logical)==f.m.read(f.s['se_reu_physical_owner']+bank)==kind
   n=min(count-at,65536-(at&65535));lo=bank*65536+(at&65535);wanted[lo:lo+n]=after[lo:lo+n];spans.append(dict(owner=kind,start=lo,bytes=n));at+=n
 allow_object('se_doc_original',4,len(data));allow_object('se_doc_meta',3,1024)
 assert after==wanted,'FileOpen outside exact newsource+initialmeta spans'
 result=dict(name=name.decode(),saved_bytes=len(data),saved_sha256=hashlib.sha256(data).hexdigest(),model_file_bytes_equal=True,save_REU_exact=True,reopen_authorized_REU=spans,incarnation_before=inc,incarnation_after=f.get('se_bc_incarnation',4),flags_before=old_flags,flags_after=2,ticket_after=0,queue_after=0,source_history_savedpoint_valid=True,scope='Real packagedFilejobs; only existing KERNAL/DOS model, no nativeIEC or actualdiskwrite claim')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
