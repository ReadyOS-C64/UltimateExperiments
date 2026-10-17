from pathlib import Path
import sys
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/'.absent-purpose-launch-cache')
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache required')
import argparse,json,hashlib,socket
p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--sha',required=True);p.add_argument('--offline',action='store_true');a=p.parse_args();mf=Path(a.manifest);blob=mf.read_bytes()
if hashlib.sha256(blob).hexdigest()!=a.sha:raise ValueError('Exact reviewed physical purpose manifest')
m=json.loads(blob)
for n,h in m['files'].items():
 if hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h:raise ValueError('Changed preimport source '+n)
if a.offline:socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Offline network forbidden'))
for name in ['purpose','copy_session','copy_transport','copy_reader_host','directory_host','process_context','cold_session','cold_transport','cold_entry','basic_ready','driver','host_stream','transport','put_transport','fast_transport','numeric_transport','native_file','hybrid','hybrid_transport','bulk_program']:
 if name in sys.modules:raise RuntimeError('Preloaded project source refused '+name)
from purpose import preflight,physical_context,live
for module in tuple(sys.modules.values()):
 n=getattr(module,'__file__',None)
 if n and '/8088DOS64ultimate/'in str(Path(n).resolve()):
  n=str(Path(n).resolve())
  if m['files'].get(n)!=hashlib.sha256(Path(n).read_bytes()).hexdigest():raise ValueError('Unpinned project import '+n)
contract=preflight(m)
if a.offline:print(json.dumps({'status':'OFFLINE_CONSTRUCTOR_PASS_NO_DEVICE_CALLS','pins':len(m['files']),'contract':contract,'dispatch_requires_ROOT_review':True}))
else:
 context=physical_context(m,a.sha)
 print(json.dumps(live(m,context)))
