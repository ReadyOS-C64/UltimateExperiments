from pathlib import Path
import sys,os,subprocess,shutil,json,hashlib
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
sys.pycache_prefix=str(P/('.absent-codec-build-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists() and Path.cwd()==P
D=P/'codec-fixtures';D.mkdir(exist_ok=True)
old=P/'baseline-codecs'
cfg='''MEMORY {
 HEADER:start=$0000,size=$0002,file=%O,type=ro;
 MAIN:start=$0801,size=$47ff,file=%O,type=rw;
 ZP:start=$0020,size=$0060,file="",type=rw;
 STATE:start=$8000,size=$2000,file="",type=rw;
 TABLES:start=$c900,size=$0400,file="",type=rw;
}
SEGMENTS {
 LOADADDR:load=HEADER,type=ro;
 CODE:load=MAIN,type=rw;
 RODATA:load=MAIN,type=ro;
 DATA:load=MAIN,type=rw,optional=yes;
 ZEROPAGE:load=ZP,type=zp,define=yes;
 BSS:load=STATE,type=bss,define=yes;
 CRC_TABLES:load=TABLES,type=bss,optional=yes;
}
'''
(D/'fixture.cfg').write_text(cfg)
for name,src,fast in [('old-default',old,0),('new-default',P,0),('full-fast',P,1)]:
 w=D/name;w.mkdir(exist_ok=True)
 for n in ['install_config.c','install_config.h','release.c','release.h']:shutil.copyfile(src/n,w/n)
 for n in ['validator_crc.c','validator_crc.h','crc32.s','crc32.h','sc_probe_entry.s']:shutil.copyfile(P/n,w/n)
 names=['sc_probe_entry','install_config','release']+(['validator_crc','crc32'] if fast else [])
 for n in ['install_config','release']+(['validator_crc'] if fast else []):subprocess.run([os.environ.get('DOS64_CC65','cc65'),'-t','none','-O','--add-source','-D','D64_VALIDATOR_FAST_CRC='+str(fast),'-D','D64_CONFIG_VALIDATE_ONLY=0','-I',str(w),str(w/(n+'.c')),'-o',str(w/(n+'.s'))],check=True)
 for n in names:subprocess.run([os.environ.get('DOS64_CA65','ca65'),'-g',str(w/(n+'.s')),'-o',str(w/(n+'.o'))],check=True)
 subprocess.run([os.environ.get('DOS64_LD65','ld65'),'-C',str(D/'fixture.cfg'),'-o',str(w/'codec.prg'),'-Ln',str(w/'codec.labels'),'-m',str(w/'codec.map'),*[str(w/(n+'.o')) for n in names],os.environ.get('DOS64_CC65_LIB','/opt/homebrew/share/cc65/lib/none.lib')],check=True)
oldbytes=(D/'old-default/codec.prg').read_bytes();newbytes=(D/'new-default/codec.prg').read_bytes();assert oldbytes==newbytes,'default validators changed native bytes'
# Product mode exports decoder/path helpers but deliberately omits maker.
labels=(P/'controller.labels').read_text();assert '._d64_config_make' not in labels
out={'status':'PASS_DEFAULT_NATIVE_BINARY_IDENTITY_AND_FULL_FAST_FIXTURE_BUILD','default_completeprg_sha256':hashlib.sha256(oldbytes).hexdigest(),'default_bytes':len(oldbytes),'full_fast_sha256':hashlib.sha256((D/'full-fast/codec.prg').read_bytes()).hexdigest(),'full_fast_bytes':(D/'full-fast/codec.prg').stat().st_size,'START_make_export_absent':True,'defaultflags':'FAST0/VALIDATEONLY0 retains complete existing ABI','fastfixtureflags':'FAST1/VALIDATEONLY0 retains maker for behavioral tests','productflags':'FAST1/VALIDATEONLY1 decoder/path consumer only'}
(P.parent/'CODEC_BUILD.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
