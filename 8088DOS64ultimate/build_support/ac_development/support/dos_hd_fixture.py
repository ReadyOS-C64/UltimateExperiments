"""Create fresh disposable genuine DOS 3.3 HD fixtures in project agentworking/runs.

The original images are never edited. FDISK/FORMAT/SYS/CHKDSK execute in
DOSBox-X, a functional reference only. No boot/FAT/partition fields are patched.
"""
from pathlib import Path
import argparse,json,os,re,shutil,struct,subprocess,sys,time
BASE=Path(__file__).resolve().parent
from dos_disk_inspect import inspect, sha, read_volume_file

def read_file(raw, name):
 return read_volume_file(raw, name)
PROFILES={'small':(128,2,16),'large':(640,4,16)}
EXPECTED=['bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb','91a624fc448c1c423d159ae21f51cc416393d8e19a73d3858afc3af92af041c2','c69238c738bab18db840b5ae72b2470c0d594832d91103573a6d8273dce300e9']

def config(run,geometry,commands,cycles=30000):
 c,h,s=geometry
 p=run/'dosbox-x.conf'
 p.write_text(f'''[sdl]
output=surface
fullscreen=false
autolock=false
[dosbox]
machine=cga
memsize=1
fastbioslogo=true
[cpu]
core=normal
cputype=8086
cycles=fixed {cycles}
[mixer]
nosound=true
[autoexec]
mount d "{run}"
'''+commands)
 return p

def execute(run,geometry,commands,done,timeout=90):
 cfg=config(run,geometry,commands)
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 cmd=[DOSBOX,'-conf',str(cfg),'-noconsole']
 started=time.monotonic();completed=False
 with (run/'process.log').open('wb') as log:
  p=subprocess.Popen(cmd,cwd=run,env=env,stdout=log,stderr=log)
  try:
   while time.monotonic()-started<timeout and p.poll() is None:
    time.sleep(.1)
    try:completed=done()
    except (ValueError,FileNotFoundError,struct.error):continue
    if completed:break
  finally:
   if p.poll() is None:
    p.terminate()
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:p.kill();p.wait()
 report={'command':cmd,'configuration_sha256':sha(cfg.read_bytes()),'completed':completed,'returncode':p.returncode,'host_seconds':time.monotonic()-started,'termination':'Stopped after closed guest evidence files or bounded failure; not a power-loss durability test.'}
 (run/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
 if not completed:raise RuntimeError(f'guest stage incomplete: {run}')
 return report

def mount(geometry):
 c,h,s=geometry
 return f'imgmount 2 D:\\HD.IMG -size 512,{s},{h},{c} -fs none > D:\\MOUNT.TXT\nmount -u d\n'
def prep_floppy(run,source,auto):
 shutil.copyfile(source,run/'floppy.img')
 (run/'CONFIG.SYS').write_bytes(b'FILES=25\r\nBUFFERS=25\r\n')
 (run/'AUTOEXEC.BAT').write_bytes(auto)
 return 'imgmount a D:\\FLOPPY.IMG -t floppy\ndel a:\\*.CPI\ndel a:\\*.EXE\ncopy d:\\CONFIG.SYS a:\\CONFIG.SYS\ncopy d:\\AUTOEXEC.BAT a:\\AUTOEXEC.BAT\n'
def extract_floppy(run,names):
 disk=(run/'floppy.img').read_bytes()
 for name in names:
  data=read_file(disk,name)
  if data is not None:(run/name).write_bytes(data)

def main():
 global DOSBOX
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--profile',choices=PROFILES,required=True)
 p.add_argument('--project',type=Path,default=BASE.parent)
 p.add_argument('--output',type=Path,help='New run directory inside project agentworking/runs; must not exist')
 p.add_argument('--dosbox',default=os.environ.get('DOS64_DOSBOX','dosbox-x'))
 p.add_argument('--nasm',default=os.environ.get('DOS64_NASM','nasm'))
 p.add_argument('--timeout',type=float,default=90,help='Finite per guest stage deadline, seconds (1..180)')
 p.add_argument('--cross16',action='store_true',help='Large only: real DOS writes/reads a file spanning raw 16 MiB')
 a=p.parse_args()
 project=a.project.resolve()
 if not (project/'AGENTS.md').is_file() or not (project/'reference').is_dir():p.error('--project must identify the 8088DOS64ultimate project')
 if a.cross16 and a.profile!='large':p.error('--cross16 requires --profile large')
 if not 1<=a.timeout<=180:p.error('--timeout must be within 1..180 seconds')
 DOSBOX=shutil.which(a.dosbox)
 nasm=shutil.which(a.nasm)
 if not DOSBOX or not nasm:p.error('Optional fixture tools missing: install DOSBox-X and NASM or supply --dosbox/--nasm; read-only inspection and unit tests do not require them')
 runs=(project/'agentworking/runs').resolve()
 run=(a.output or runs/(a.profile+'-hd-fixture-'+time.strftime('%Y%m%d-%H%M%S'))).resolve()
 if run==runs or not run.is_relative_to(runs):p.error('--output must be a NEW child of project agentworking/runs')
 if run.exists():p.error('--output already exists; choose a fresh owned directory')
 if any(c in str(run) for c in '"\r\n'):p.error('--output path cannot contain quotes or line breaks')
 geometry=PROFILES[a.profile];size=geometry[0]*geometry[1]*geometry[2]*512
 sources=sorted((project/'reference').glob('*.img'));before=[sha(x.read_bytes()) for x in sources]
 if before!=EXPECTED:raise ValueError('source image identity changed')
 run.mkdir(parents=True,exist_ok=False)
 (run/'OWNER.txt').write_text('DOS64 genuine disposable HD fixture; this directory was created exclusively by dos_hd_fixture.py\n')
 report={'schema_version':1,'kind':'dos64-genuine-dos-hd-fixture','profile':a.profile,'geometry':geometry,'logical_bytes':size,'run':str(run),'source_hashes_before':before,'stages':{},'complete':False}
 try:
  dosbox=Path(DOSBOX);report['dosbox_binary_sha256']=sha(dosbox.read_bytes())
  report['tool_sources']={str(f.relative_to(BASE)):sha(f.read_bytes()) for f in [Path(__file__),BASE/'dos_disk_inspect.py',BASE/'dos_fixture_assets/keyfeed.asm',BASE/'dos_fixture_assets/cross16.asm']}
  report['nasm_binary_sha256']=sha(Path(nasm).read_bytes())
  report['nasm_version']=subprocess.run([nasm,'-v'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
  version_probe=subprocess.run([str(dosbox),'-version'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
  ver=version_probe.stdout
  report['dosbox_version_probe_returncode']=version_probe.returncode
  if 'DOSBox-X version' not in ver:raise ValueError('DOSBox-X version probe did not identify DOSBox-X')
  (run/'dosbox-version.txt').write_text(ver)
  report['dosbox_version']=ver.strip()
  stage=run/'00-partition';stage.mkdir()
  # Work around pinned DOSBox-X MountImageNone classification/geometry bug.
  backing=max(size,3*1024*1024);(stage/'hd.img').write_bytes(bytes(backing));report['transport_bytes']=backing
  src=BASE/'dos_fixture_assets/keyfeed.asm'
  subprocess.run([nasm,'-f','bin',str(src),'-o',str(stage/'KEYFEED.COM')],check=True,timeout=10)
  report['keyboard_feeder']={'source':str(src),'source_sha256':sha(src.read_bytes()),'binary_sha256':sha((stage/'KEYFEED.COM').read_bytes()),'scope':'Only reference FDISK console reads AH=0Ch/AH=08h are supplied; it does not intercept disk, filesystem, boot or INT 13h calls. SCREEN files capture each prompt.'}
  commands=prep_floppy(stage,sources[0],b'@ECHO OFF\r\nVER > A:\\VER.TXT\r\nKEYFEED\r\nFDISK\r\n')+'copy d:\\KEYFEED.COM a:\\KEYFEED.COM\n'+mount(geometry)+'boot a:\n'
  def partitioned():
   b=(stage/'hd.img').read_bytes()
   return b[510:512]==b'\x55\xaa' and b[446]==0x80 and read_file((stage/'floppy.img').read_bytes(),'S6.BIN') is not None
  report['stages']['partition']=execute(stage,geometry,commands,partitioned,timeout=a.timeout)
  extract_floppy(stage,['VER.TXT']+[f'S{i}.BIN' for i in range(8)])
  for f in stage.glob('S?.BIN'):
   b=f.read_bytes();f.with_suffix('.TXT').write_text('\n'.join(b[i*160:(i+1)*160:2].decode('cp437').rstrip() for i in range(25))+'\n')
  stage2=run/'01-format';stage2.mkdir();shutil.copyfile(stage/'hd.img',stage2/'hd.img')
  (stage2/'ANSWERS.TXT').write_bytes(b'Y\r\n\r\n')
  (stage2/'AUTOHD.BAT').write_bytes(b'@ECHO OFF\r\nVER > C:\\BOOTVER.TXT\r\nDIR C: > C:\\BOOTDIR.TXT\r\nECHO DOS64_HD_BOOT_OK > C:\\BOOTOK.TXT\r\n')
  auto=b'@ECHO OFF\r\nVER > A:\\VER.TXT\r\nFORMAT C: /S < A:\\ANSWERS.TXT > A:\\FORMAT.OUT\r\nSYS C: > A:\\SYS.OUT\r\nCOPY A:\\AUTOHD.BAT C:\\AUTOEXEC.BAT > A:\\COPY.OUT\r\nVER > C:\\VER.TXT\r\nDIR C: > C:\\DIR.TXT\r\nCHKDSK C: > C:\\CHECK.TXT\r\nECHO DOS64_HD_FORMAT_OK > A:\\DONE.TXT\r\n'
  commands=prep_floppy(stage2,sources[0],auto)+'copy d:\\ANSWERS.TXT a:\\ANSWERS.TXT\ncopy d:\\AUTOHD.BAT a:\\AUTOHD.BAT\n'+mount(geometry)+'boot a:\n'
  report['stages']['format_sys']=execute(stage2,geometry,commands,lambda:read_file((stage2/'floppy.img').read_bytes(),'DONE.TXT')==b'DOS64_HD_FORMAT_OK \r\n',timeout=a.timeout)
  extract_floppy(stage2,['VER.TXT','FORMAT.OUT','SYS.OUT','COPY.OUT','DONE.TXT'])
  if b'System transferred' not in (stage2/'FORMAT.OUT').read_bytes() or (stage2/'SYS.OUT').read_bytes()!=b'System transferred\r\n':raise ValueError('FORMAT/SYS transcript')
  stage3=run/'02-boot';stage3.mkdir();shutil.copyfile(stage2/'hd.img',stage3/'hd.img')
  start=struct.unpack_from('<I',(stage3/'hd.img').read_bytes(),454)[0]
  report['stages']['hard_disk_boot']=execute(stage3,geometry,mount(geometry)+'boot c:\n',lambda:read_volume_file((stage3/'hd.img').read_bytes()[start*512:size],'BOOTOK.TXT')==b'DOS64_HD_BOOT_OK \r\n',timeout=a.timeout)
  padded=(stage3/'hd.img').read_bytes()
  if padded[size:]!=bytes(backing-size):raise ValueError('write outside advertised logical disk')
  raw=padded[:size];(run/'disk.raw.img').write_bytes(raw)
  report['inspection']=inspect(raw,geometry)
  for name in ['BOOTVER.TXT','BOOTDIR.TXT','BOOTOK.TXT','VER.TXT','DIR.TXT','CHECK.TXT']:
   data=read_volume_file(raw[start*512:],name)
   if data is not None:(run/name).write_bytes(data)
  for filename in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:
   if read_volume_file(raw[start*512:],filename)!=read_file(sources[0].read_bytes(),filename):raise ValueError(f'system file changed: {filename}')
  if b'MS-DOS Version 3.30' not in (run/'BOOTVER.TXT').read_bytes():raise ValueError('genuine hard-disk-only guest VER evidence')
  verify_chkdsk((run/'CHECK.TXT').read_bytes(),report['inspection'])
  report['source_system_files_identical']=True
  if a.cross16:
   report['cross16']=create_cross16(run,geometry,sources[0],nasm,a.timeout)
   raw=(run/'03-cross16/hd.img').read_bytes()
   (run/'disk.raw.img').write_bytes(raw)
   report['inspection']=inspect(raw,geometry)
  for filename in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:
   if read_volume_file(raw[start*512:],filename)!=read_file(sources[0].read_bytes(),filename):raise ValueError(f'final system file changed: {filename}')
  report['raw_image']={'path':'disk.raw.img','bytes':len(raw),'sha256':sha(raw)}
  report['geometry']={'cylinders':geometry[0],'heads':geometry[1],'sectors_per_track':geometry[2],'bytes_per_sector':512}
  report['sources']=[{'path':str(x.relative_to(project)),'sha256':h,'bytes':x.stat().st_size} for x,h in zip(sources,before)]
  report['complete']=True
 except BaseException as error:
  report['error']=f'{type(error).__name__}: {error}'
  raise
 finally:
  after=[sha(x.read_bytes()) for x in sources];report['source_hashes_after']=after;report['original_images_unchanged']=before==after
  report['limitations']=['Functional PC reference only, not the 6510 runtime, target BIOS, native cache/persistence or XT timing.','FDISK input uses a private console-input TSR; FORMAT/SYS/CHKDSK are unmodified supplied binaries and real DOS owns all filesystem operations.','Temporary padded small-image transport is required by DOSBox-X; final raw payload has no invented partition, boot-sector or FAT fields.','All stages stop after evidence files close; no claim about filesystem power-failure durability.']
  (run/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(run)
 if not(report['complete'] and report['original_images_unchanged']):raise SystemExit(1)


def verify_chkdsk(transcript, inspection):
 total=re.search(rb'(?m)^ *([0-9]+) bytes total disk space\r?$',transcript)
 free=re.search(rb'(?m)^ *([0-9]+) bytes available on disk\r?$',transcript)
 cluster_bytes=inspection['bpb']['sectors_per_cluster']*512
 if not total or not free or int(total[1])!=inspection['data_clusters']*cluster_bytes or not 0<=int(free[1])<=int(total[1]) or int(free[1])%cluster_bytes:
  raise ValueError('genuine CHKDSK transcript/capacity evidence')


def create_cross16(run, geometry, source, nasm, timeout):
 stage=run/'03-cross16';stage.mkdir()
 shutil.copyfile(run/'disk.raw.img',stage/'hd.img')
 generator=BASE/'dos_fixture_assets/cross16.asm'
 subprocess.run([nasm,'-f','bin',str(generator),'-o',str(stage/'CROSS.COM')],check=True,timeout=10)
 auto=b'@ECHO OFF\r\nCROSS\r\nIF ERRORLEVEL 1 GOTO FAIL\r\nCHKDSK C: > A:\\CHECK.TXT\r\nECHO DOS64_CROSS16_DONE > A:\\DONE.TXT\r\n:FAIL\r\n'
 commands=prep_floppy(stage,source,auto)+'copy d:\\CROSS.COM a:\\CROSS.COM\n'+mount(geometry)+'boot a:\n'
 execution=execute(stage,geometry,commands,lambda:read_file((stage/'floppy.img').read_bytes(),'DONE.TXT')==b'DOS64_CROSS16_DONE \r\n',timeout=timeout)
 extract_floppy(stage,['CROSS.OK','CHECK.TXT','DONE.TXT'])
 if (stage/'CROSS.OK').read_bytes()!=b'DOS64_CROSS16_OK\r\n':raise ValueError('cross16 guest write/reopen/read/EOF marker')
 raw=(stage/'hd.img').read_bytes();report=inspect(raw,geometry)
 verify_chkdsk((stage/'CHECK.TXT').read_bytes(),report)
 start=report['partition']['start_lba']*512
 data=read_volume_file(raw[start:],'CROSS16.BIN')
 if data is None or len(data)!=4097*4096:raise ValueError('cross16 length')
 for i in range(4097):
  expected=struct.pack('<2048H',*[0xa55a^i^j for j in range(2048)])
  if data[i*4096:(i+1)*4096]!=expected:raise ValueError(f'cross16 pattern block {i}')
 entry=next(x for x in report['files'] if x['name']=='CROSS16.BIN')
 spc=report['bpb']['sectors_per_cluster']
 first=(report['partition']['start_lba']+report['data_sector_in_volume']+(entry['first_cluster']-2)*spc)*512
 if entry['clusters']!=list(range(entry['first_cluster'],entry['first_cluster']+len(entry['clusters']))):raise ValueError('cross16 fixture must be contiguous')
 if not first<0x1000000<first+len(data) or raw[first:first+len(data)]!=data:raise ValueError('cross16 raw mapping')
 return {'name':'CROSS16.BIN','file_bytes':len(data),'sha256':sha(data),'raw_start':first,'raw_end_exclusive':first+len(data),'contiguous':True,
         'guest_write_close_reopen_read_compare_eof_close':True,'host_compared_all_generated_bytes':True,
         'generator_source_sha256':sha(generator.read_bytes()),'generator_binary_sha256':sha((stage/'CROSS.COM').read_bytes()),
         'execution':execution,'seams':{hex(x):{'offset_le32':struct.pack('<I',x).hex(),'sha256':sha(raw[x:x+512])} for x in [0xfffe00,0x1000000,0x1000200,0x13ffe00]}}

if __name__=='__main__':main()
