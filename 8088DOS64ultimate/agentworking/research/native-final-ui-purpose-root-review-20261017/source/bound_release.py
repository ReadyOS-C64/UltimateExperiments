"""Purpose-pinned successor inventory; never carries an older release's identity.
No network/default release discovery. Caller must source-pin expected_record_sha.
"""
import json,re
from protocol import Protocol,LEAVES,sha
NAMES=('SETUP.PRG','SETUP.FAT','SETUP.PUB','CONFIG.PRG','START.TPL','START.REL','START.INO','DOS64.PRG','DOS64.REL','DOS64.MNU','START.RCV','START.RFW','DOS1.IMG','DOS2.IMG','DOS3.IMG')
class BoundRelease:
 def __init__(self,record,expected_record_sha,assets):
  if type(record)is not bytes or type(expected_record_sha)is not str or not re.fullmatch('[0-9a-f]{64}',expected_record_sha)or sha(record)!=expected_record_sha:raise ValueError('Purpose-pinned exact release record required')
  j=json.loads(record)
  if j.get('schema')!=1 or type(j.get('schema'))is not int or j.get('purpose')!='V1_RELEASE16_MATCHED_DISTRIBUTION'or j.get('stage16_chunks')!=94 or set(j.get('files',{}))!=set(NAMES)or set(assets)!=set(NAMES):raise ValueError('Exact15 source files / release16 profile')
  rows=[]
  for n in NAMES:
   b=assets[n];r=j['files'][n]
   if type(b)is not bytes or type(r)is not dict or set(r)!={'sha256','bytes'}or type(r['bytes'])is not int or not 1<=len(b)<=1048576 or r!={'sha256':sha(b),'bytes':len(b)}:raise ValueError('Exact successor source identity '+n)
   rows.append((n,b))
  # OWNER adds one chunk; exact unchanged native16/94/380 profile.
  if 1+sum((len(b)+16383)//16384 for n,b in rows)!=94:raise ValueError('Profile requires94 chunks including OWNER')
  self._rows=tuple(rows);self.record_sha=expected_record_sha
 def assets(self,home,nonce):
  if type(home)is not bytes or not re.fullmatch(rb'/usb1/DOS64_TEST/[a-z0-9_-]{1,64}',home)or type(nonce)is not bytes or len(nonce)!=16 or not any(nonce):raise ValueError('Exact owned root and nonzero nonce')
  owner={'purpose':'release16-purpose-pinned-successor','nonce':nonce.hex(),'home':home.decode(),'inventory_sha256':self.record_sha}
  return {'OWNER.JSON':(json.dumps(owner,sort_keys=True)+'\n').encode(),**dict(self._rows)}
 def verify(self,assets,home):
  if type(assets)is not dict or set(assets)!=set(NAMES)|{'OWNER.JSON'}or any(type(v)is not bytes for v in assets.values()):raise ValueError('Exact16 immutable byte payloads')
  owner=json.loads(assets['OWNER.JSON']);nonce=bytes.fromhex(owner['nonce'])
  if self.assets(home,nonce)!=assets:raise ValueError('Successor inventory/owner differs before CREATE')
  if len(assets['OWNER.JSON'])>16384:raise ValueError('Single bounded owner chunk')
  return dict(assets)
class Release16Protocol(Protocol):
 def file(self,leaf,body):
  if leaf not in LEAVES or type(body)is not bytes:raise ValueError('Exact release16 asset')
  self.job(2,leaf=leaf)
  for off in range(0,len(body),16384):
   data=body[off:off+16384];self.job(3,offset=off,data=data);self.job(4,offset=off,data=data)
  self.job(5);self.job(6,leaf=leaf);self.job(7,offset=len(body));actual=bytearray()
  for off in range(0,len(body),16384):
   data=body[off:off+16384];self.job(8,offset=off,data=data);actual.extend(self.last_payload)
  self.job(9,offset=len(body));self.job(5)
  return {'bytes':len(body),'sha256':sha(bytes(actual)),'native_EOF':True,'known_closed':True},bytes(actual)
def publish(p,release,assets,retain):
 try:
  if type(p)is not Release16Protocol or type(release)is not BoundRelease or not callable(retain):raise ValueError('Typed release16/source-pinned successor')
  immutable=release.verify(assets,p.source.home);p.job(1);done={}
  for n,b in immutable.items():
   facts,actual=p.file(n,b)
   if actual!=b:raise ValueError('Every retained native file byte required '+n)
   retain(n,actual);done[n]=facts
  p.job(10)
  if p.sequence!=380 or len(p.records)!=380:raise ValueError('Exact380 native completion receipts')
  return {'status':'NATIVE_RELEASE16_SOURCE_STAGING_PASSED','record_sha256':release.record_sha,'files':done,'native_jobs':380,'chunks16K':94,'native_known_closed_stopped':True,'product_programs_executed':False,'physical':False}
 except BaseException as e:
  if isinstance(p,Protocol)and p.first is None:p.first=e
  raise
