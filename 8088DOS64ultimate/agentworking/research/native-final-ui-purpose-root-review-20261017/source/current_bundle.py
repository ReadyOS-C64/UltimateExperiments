import hashlib,zlib,json
from pathlib import Path
from protocol import Protocol,LEAVES,sha
NAMES=('SETUP.PRG','SETUP.FAT','SETUP.PUB','CONFIG.PRG','START.TPL','START.REL','START.INO','DOS64.PRG','DOS64.REL')
# Explicit immutable candidate authority, not the mutable build pointer.
CANDIDATE_RESULT_SHA='1720fe5cf96bbaecbfef62f34917852a98f266b94c85796d23bf66fa7f4d00e6'
IDENTITIES={'SETUP.PRG': {'sha256': '7901183a628406fe555e6940a0c568bcea38c05ed1da56e3b5e9c5d1c26d2da8', 'bytes': 42627}, 'SETUP.FAT': {'sha256': '305e596807b94fbc4e49936b741e81760d6d4f5059c830ad587bd3d7388def13', 'bytes': 20541}, 'SETUP.PUB': {'sha256': '39a0803f38ae79fd97e2ebd71942fc526a016292c80718c6e11a3b5937299445', 'bytes': 20544}, 'CONFIG.PRG': {'sha256': '508d1943fe021f956b62a6ac7b8be1a6b9e7725736e364f05be70839a6f4486a', 'bytes': 42892}, 'START.TPL': {'sha256': '79bb0470e830b9012eac1b87beddb14a5a005542f332c53b68ec7b4d3ddb34e8', 'bytes': 18432}, 'START.REL': {'sha256': '45b68eafff7913f47d8d2884167e48d00ba91e23a0fdf4b485d375d8eb705697', 'bytes': 64}, 'START.INO': {'sha256': 'eebb43aca1e12a67279b4b41d4b57d9b18d407f3e98dfeaadd9e5dc5f697459e', 'bytes': 6798}, 'DOS64.PRG': {'sha256': '666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064', 'bytes': 47105}, 'DOS64.REL': {'sha256': '9eb1cd3a16afe31277fa7fb76911011aad26248f40341b3435a21dee854abbe4', 'bytes': 64}}
class CurrentProtocol(Protocol):
 def file(self,leaf,body):
  if leaf not in LEAVES or not isinstance(body,bytes):raise ValueError('Exact current asset')
  self.job(2,leaf=leaf)
  for off in range(0,len(body),16384):
   data=body[off:off+16384];self.job(3,offset=off,data=data);self.job(4,offset=off,data=data)
  self.job(5);self.job(6,leaf=leaf);self.job(7,offset=len(body));actual=bytearray()
  for off in range(0,len(body),16384):
   data=body[off:off+16384];self.job(8,offset=off,data=data);actual.extend(self.last_payload)
  self.job(9,offset=len(body));self.job(5)
  return {'bytes':len(body),'sha256':sha(bytes(actual)),'native_EOF':True,'known_closed':True},bytes(actual)
def prepare(home,folder,result_bytes,nonce):
 if sha(result_bytes)!=CANDIDATE_RESULT_SHA or not isinstance(nonce,bytes)or len(nonce)!=16 or not any(nonce):raise ValueError('Exact candidate/nonzero owner nonce required')
 result=json.loads(result_bytes);assets={n:(folder/n).read_bytes()for n in NAMES}
 for n,b in assets.items():
  if result['files'][n]!={'sha256':sha(b),'bytes':len(b)}:raise ValueError('Candidate asset differs '+n)
 owner=json.dumps({'purpose':'current9-native-PUT-staging-only','nonce':nonce.hex(),'home':home.decode(),'candidate_result_sha256':CANDIDATE_RESULT_SHA},sort_keys=True).encode()+b'\n';assets={'OWNER.JSON':owner,**assets}
 return assets

def _publish(p,assets,retain):
 if type(p)is not CurrentProtocol or set(assets)!=set(NAMES)|{'OWNER.JSON'}or not callable(retain):raise ValueError('Exact10 source assets and durable actual readback sink required')
 # Pin whole immutable snapshot before any MKDIR/CREATE.
 immutable={n:bytes(b)for n,b in assets.items()}
 for n,v in IDENTITIES.items():
  if {'sha256':sha(immutable[n]),'bytes':len(immutable[n])}!=v:raise ValueError('Exact immutable candidate asset required '+n)
 owner=json.loads(immutable['OWNER.JSON']);nonce=bytes.fromhex(owner['nonce'])
 if set(owner)!={'purpose','nonce','home','candidate_result_sha256'}or owner['purpose']!='current9-native-PUT-staging-only'or owner['home'].encode()!=p.source.home or owner['candidate_result_sha256']!=CANDIDATE_RESULT_SHA or len(nonce)!=16 or not any(nonce):raise ValueError('Exact current owner/purpose/root required')
 expected={n:sha(b)for n,b in immutable.items()};p.job(1);done={}
 for name,body in immutable.items():
  facts,actual=p.file(name,body)
  if actual!=body or sha(actual)!=expected[name]:raise ValueError('Native fullbytes differ '+name)
  retain(name,actual);done[name]=facts
 p.job(10)
 return {'status':'NATIVE_CURRENT9_PUT_STAGING_PASSED','files':done,'native_known_closed_stopped':True,'START_executed':False,'SETUP_CONFIG_UI_executed':False,'physical':False}

def publish(p,assets,retain):
 try:return _publish(p,assets,retain)
 except BaseException as e:
  if isinstance(p,Protocol)and p.first is None:p.first=e
  raise
