"""Fresh dual-media FTP staging; no device activity until explicitly called."""
import bootstrap
from pathlib import Path
import io,json,re,time,uuid,zlib,ftplib
from ac_contract import sha,HD_SHA,A_SHA,PURPOSE,verify_media
from c64u_bulk_reu_recovery import dump

def stage_media(connect,floppy_path,hd_path,run_id,output,clock=time.monotonic,seconds=180):
 if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',run_id) or isinstance(seconds,bool) or not 1<=seconds<=180:raise ValueError('Fresh run id/bounded FTP phase required')
 floppy=Path(floppy_path).read_bytes();hd=Path(hd_path).read_bytes()
 if len(floppy)!=368640 or sha(floppy)!=A_SHA or len(hd)!=20*1024*1024 or sha(hd)!=HD_SHA:raise ValueError('Exact source media required before any FTP')
 out=Path(output);out.mkdir(parents=True,exist_ok=False);deadline=clock()+seconds;remote='/usb1/DOS64_TEST/'+run_id
 r={'schema':1,'purpose':PURPOSE,'status':'running','created_directory':False,'original_sources_unchanged':False,'run_id':run_id,'remote_directory':remote,'files':{}}
 def bound():
  left=deadline-clock()
  if left<=0:raise TimeoutError('Complete dual-media staging deadline')
  return min(5,left)
 def readback(ftp,path,expected):
  b=bytearray()
  def chunk(block):
   bound()
   if len(b)+len(block)>len(expected):raise ValueError('FTP readback exceeds exact expected length')
   b.extend(block)
   if getattr(ftp,'sock',None):ftp.sock.settimeout(bound())
  ftp.retrbinary('RETR '+path,chunk);bound()
  if bytes(b)!=expected:raise ValueError('Complete FTP media readback differs')
 try:
  with connect(bound()) as ftp:
   try:ftp.mkd('/usb1/DOS64_TEST')
   except ftplib.error_perm:ftp.cwd('/usb1/DOS64_TEST')
   ftp.mkd(remote);r['created_directory']=True
   marker=json.dumps({'project':'8088DOS64ultimate','purpose':PURPOSE,'run_id':run_id,'nonce':uuid.uuid4().hex,'files':{'DOS33A.IMG':sha(floppy),'DOSHD.IMG':sha(hd)}},sort_keys=True).encode()
   ftp.storbinary('STOR '+remote+'/OWNER.JSON',io.BytesIO(marker));readback(ftp,remote+'/OWNER.JSON',marker);r['marker_sha256']=sha(marker);(out/'OWNER.JSON').write_bytes(marker)
   for role,body,path,leaf in [('floppy',floppy,floppy_path,'DOS33A.IMG'),('hd',hd,hd_path,'DOSHD.IMG')]:
    bound();native=remote+'/'+leaf;ftp.storbinary('STOR '+native,io.BytesIO(body),callback=lambda b:bound());readback(ftp,native,body)
    r['files'][role]={'source_path':str(Path(path).resolve()),'source_bytes':len(body),'source_sha256':sha(body),'remote_readback_bytes':len(body),'remote_readback_sha256':sha(body),'native_path':native}
  if Path(floppy_path).read_bytes()!=floppy or Path(hd_path).read_bytes()!=hd:raise ValueError('Local source changed during staging')
  r['original_sources_unchanged']=True;r['status']='verified';verify_media(r,floppy,hd)
 except BaseException as error:r['status']='failed';r['error']=repr(error);raise
 finally:dump(out/'ac-media-staging.json',r)
 return r
