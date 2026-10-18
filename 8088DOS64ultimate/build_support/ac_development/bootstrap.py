"""Source-only isolated A+C host support imports."""
from pathlib import Path
import sys,hashlib,json
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
HELPER=PROJECT/'tools/hd_close_reopen'
HELPER_BUILD=PROJECT/'build/hd_close_reopen'
SUPPORT=HERE/'support'
CACHE_DISABLED=HERE/'.source-import-cache-disabled'
if CACHE_DISABLED.exists():raise RuntimeError('Source-only cache path must remain absent')
sys.dont_write_bytecode=True;sys.pycache_prefix=str(CACHE_DISABLED)
for m in tuple(sys.modules.values()):
 f=getattr(m,'__file__',None)
 if f and Path(f).resolve().is_relative_to(PROJECT/'build_support') and not Path(f).resolve().is_relative_to(HERE):raise RuntimeError('Fresh process required; ROOT support loaded')
dependency_path=HERE/'DEPENDENCIES.json'
if hashlib.sha256(dependency_path.read_bytes()).hexdigest()!='cf5241ac19607dc51c0b48985bccf5ce04669c0a0bf070c32f75b6fad9f99841':raise RuntimeError('Reviewed dependency manifest differs')
for name,want in json.loads(dependency_path.read_text())['files'].items():
 q=HERE/name
 if not q.is_file() or q.stat().st_size!=want['bytes'] or hashlib.sha256(q.read_bytes()).hexdigest()!=want['sha256']:raise RuntimeError('Reviewed dependency source differs: '+name)
sys.path.insert(0,str(SUPPORT))
