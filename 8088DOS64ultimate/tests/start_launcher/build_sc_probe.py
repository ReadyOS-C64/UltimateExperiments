from pathlib import Path
import subprocess,os,sys,hashlib,json
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.pycache_prefix=str(P/('.absent-sc-build-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists() and Path.cwd()==P
subprocess.run([os.environ.get('DOS64_CC65','cc65'),'-t','none','-O','--add-source','sc_abi_probe.c','-o','sc_abi_probe.s'],check=True)
for n in ['sc_probe_entry','sc_abi_probe']:subprocess.run([os.environ.get('DOS64_CA65','ca65'),'-g',n+'.s','-o',n+'.o'],check=True)
names=['sc_probe_entry','bulk_reu','bindings','uci','files','install_config','release','controller','dma','crc32','validator_crc','startup_close','sc_abi_probe']
subprocess.run([os.environ.get('DOS64_LD65','ld65'),'-C','controller.cfg','-o','sc-abi.prg','-Ln','sc-abi.labels','-m','sc-abi.map',*[n+'.o' for n in names],os.environ.get('DOS64_CC65_LIB','/opt/homebrew/share/cc65/lib/none.lib')],check=True)
b=(P/'sc-abi.prg').read_bytes();assert 0x0801+len(b)-2<=0x5000
print(json.dumps({n:{'sha256':hashlib.sha256((P/n).read_bytes()).hexdigest(),'bytes':(P/n).stat().st_size} for n in ['sc-abi.prg','sc-abi.labels','sc-abi.map']},indent=2))
