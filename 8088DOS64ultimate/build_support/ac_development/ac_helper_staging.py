"""Fresh exact helper staging separate from unchanged two-role FTP transport."""
import bootstrap,io,json,re,time,uuid,ftplib
from pathlib import Path
from ac_contract import sha
from c64u_bulk_reu_recovery import dump
PURPOSE='owned-ac-HDC1-helper'
def validate_helper_stage(r,body):
 if r.get('schema')!=1 or r.get('purpose')!=PURPOSE or r.get('status')!='verified' or r.get('created_directory') is not True or r.get('source_files_unchanged') is not True or set(r.get('files',{}))!={'helper'}:raise ValueError('Fresh actual HDC1 staging registry required')
 run=r.get('run_id','');directory='/usb1/DOS64_TEST/'+run
 if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',run) or r.get('remote_directory')!=directory or not re.fullmatch(r'[0-9a-f]{64}',r.get('marker_sha256','')):raise ValueError('Fresh helper marker/directory required')
 item=r['files']['helper'];expected={'sha256':sha(body),'bytes':len(body),'remote_readback_sha256':sha(body),'remote_readback_bytes':len(body),'remote_path':directory+'/HD-CLOSE.PRG'}
 if any(item.get(k)!=v for k,v in expected.items()):raise ValueError('Exact configured helper complete staging differs')
 return item['remote_path']
def stage_helper(connect,source,expected,run_id,output,clock=time.monotonic,seconds=120):
 body=Path(source).read_bytes()
 if sha(body)!=expected or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',run_id) or isinstance(seconds,bool) or not 1<=seconds<=180:raise ValueError('Exact helper/freshid/bound required')
 out=Path(output);out.mkdir(parents=True,exist_ok=False);directory='/usb1/DOS64_TEST/'+run_id;deadline=clock()+seconds
 r={'schema':1,'purpose':PURPOSE,'status':'running','created_directory':False,'source_files_unchanged':False,'run_id':run_id,'remote_directory':directory,'files':{'helper':{'source_path':str(Path(source).resolve()),'remote_path':directory+'/HD-CLOSE.PRG','bytes':len(body),'sha256':sha(body)}}}
 def bound(*a):
  if clock()>=deadline:raise TimeoutError('Helper staging deadline')
 def readback(ftp,path,expected_body):
  b=bytearray()
  def chunk(block):
   bound()
   if len(b)+len(block)>len(expected_body):raise ValueError('Helper readback excess')
   b.extend(block)
  ftp.retrbinary('RETR '+path,chunk);bound()
  if bytes(b)!=expected_body:raise ValueError('Helper complete readback differs')
 try:
  with connect(5) as ftp:
   try:ftp.mkd('/usb1/DOS64_TEST')
   except ftplib.error_perm:ftp.cwd('/usb1/DOS64_TEST')
   ftp.mkd(directory);r['created_directory']=True
   marker=json.dumps({'project':'8088DOS64ultimate','purpose':PURPOSE,'run_id':run_id,'nonce':uuid.uuid4().hex,'helper_sha256':sha(body)},sort_keys=True).encode();ftp.storbinary('STOR '+directory+'/OWNER.JSON',io.BytesIO(marker),callback=bound);readback(ftp,directory+'/OWNER.JSON',marker);r['marker_sha256']=sha(marker)
   ftp.storbinary('STOR '+directory+'/HD-CLOSE.PRG',io.BytesIO(body),callback=bound);readback(ftp,directory+'/HD-CLOSE.PRG',body);r['files']['helper'].update(remote_readback_bytes=len(body),remote_readback_sha256=sha(body))
  if Path(source).read_bytes()!=body:raise ValueError('Helper source changed during staging')
  r['source_files_unchanged']=True;r['status']='verified';validate_helper_stage(r,body)
 except BaseException as error:r['status']='failed';r['error']=repr(error);raise
 finally:dump(out/'helper-staging.json',r)
 return r
