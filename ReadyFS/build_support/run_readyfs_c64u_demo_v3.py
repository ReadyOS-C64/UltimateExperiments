#!/usr/bin/env python3
"""Human-paced ReadyFS tour with marker-gated nested filesystem operations.

Uses empty drive B as device 9; preserves occupied drive A. Mutations stay in a fresh owned USB1
run root. Preserves that root and source fixtures; restores CPU and drive state.
"""
from pathlib import Path
import json, os, re, subprocess, time, urllib.request, urllib.error, urllib.parse
import socket, struct, threading, select, random, hashlib, shutil
import ftplib, io, posixpath
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
ARTIFACTS=Path(os.environ.get('READYFS_DEMO_ARTIFACTS', str(ROOT/'artifacts/readyfs')))
OUT=Path(os.environ['READYFS_DEMO_OUT']); OUT.mkdir(parents=True,exist_ok=True)
API='http://'+os.environ.get('C64U_HOST','10.0.0.79')+'/v1'
log=(OUT/'events.jsonl').open('a',buffering=1)
random.seed(64)
steps=[]
FAST=os.environ.get('READYFS_DEMO_PREFLIGHT')=='1'
def event(**data):
    data['time']=time.time(); log.write(json.dumps(data)+'\n'); print(json.dumps(data),flush=True)
def api(path,method='GET',data=None,ctype=None,timeout=20):
    headers={} if ctype is None else {'Content-Type':ctype}
    with urllib.request.urlopen(urllib.request.Request(API+path,data=data,headers=headers,method=method),timeout=timeout) as r:return r.read()
def js(path):return json.loads(api(path))
def save_json(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def read(address,size):return api(f'/machine:readmem?address={address:X}&length={size}')
def write(address,data):return api(f'/machine:writemem?address={address:X}&data={data.hex()}','PUT')
def keys(data,human=True):
    if FAST:human=False
    if isinstance(data,str):data=bytes(0xBF if char=='\\' else ord(char) for char in data.upper())
    for key in data:
        deadline=time.monotonic()+12
        while read(0xC6,1)!=b'\0':
            if time.monotonic()>deadline:raise RuntimeError('keyboard did not drain')
            time.sleep(.03)
        write(0xC5,b'\0\0');write(0x277,bytes([key]));write(0xC6,b'\1')
        if key != 13:
            while read(0xC6,1)!=b'\0':
                if time.monotonic()>deadline:raise RuntimeError('key was not consumed')
                time.sleep(.03)
        if human:time.sleep(random.uniform(.085,.165)+(random.uniform(.09,.18) if key==32 else 0))
    time.sleep(.2)
def capture(label):
    dest=OUT/label;dest.mkdir(exist_ok=True)
    data=read(0x400,1000);(dest/'screen_0400.bin').write_bytes(data)
    subprocess.run(['python3',str(ROOT/'build_support/decode_c64_screen.py'),str(dest/'screen_0400.bin'),'--output',str(dest/'screen.txt')],check=True)
    return (dest/'screen.txt').read_text()
def check(label,needle):
    text=capture(label)
    assert needle.upper() in text.upper(),f'{label}: missing {needle}: {text}'
    event(case=label,result='PASS');return text
def verify_more_color(label):
    text=capture(label);color=read(0xD800,1000)
    row,line=next((row,line[4:]) for row,line in enumerate(text.splitlines()) if '-- MORE --' in line.upper())
    col=line.upper().index('-- MORE --')
    assert all((v&15)==7 for v in color[row*40+col:row*40+col+10]),'Pager prompt is not yellow'
    event(case='yellow-more-prompt',result='PASS')

def command(text,needle=None,pause=4):
    started=time.time()
    event(command=text);keys(text);time.sleep(.65);keys([13]);wait_ready(min(pause,4))
    if needle:check('case-'+str(len(list(OUT.glob('case-*')))).zfill(2),needle)
    if not FAST:record_step(text,started=started)
def speed(mhz):
    api('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual','PUT')
    api('/configs/U64%20Specific%20Settings/CPU%20Speed?value='+urllib.parse.quote(f'{mhz:2d}'),'PUT')
    if mhz==1:api('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off','PUT')
    time.sleep(1)
    state=js('/configs/U64%20Specific%20Settings')['U64 Specific Settings']
    assert int(str(state['CPU Speed']).strip())==mhz

class OwnedDemo:
    def __init__(self):
        self.host=os.environ.get('C64U_HOST','10.0.0.79')
        self.run='readyfs-'+time.strftime('%Y%m%d-%H%M%S',time.gmtime())+'-'+str(os.getpid())
        assert re.fullmatch(r'readyfs-[0-9]{8}-[0-9]{6}-[0-9]+',self.run)
        self.root='/USB1/READYFS_TEST/'+self.run
        self.marker='.readyfs-owner-'+self.run
        self.marker_bytes=('READYFS-OWNED-ROOT\nrun_id='+self.run+'\npolicy=preserve-by-default\n').encode()
        self.seed={'readme.seq':b'READYFS NESTED DEMO\rSOURCE STAYS SAFE\r',
                   'alpha/one.seq':b'ALPHA ONE\r','alpha/two.seq':b'ALPHA TWO\r',
                   'beta/deep/three.seq':b'THREE LEVELS\r','beta/four.seq':b'BETA FOUR\r'}
        with self.ftp() as ftp:
            ftp.cwd('/USB1/READYFS_TEST')
            existing={posixpath.basename(n).lower() for n in ftp.nlst()}
            assert self.run.lower() not in existing,'Refuse existing root'
            ftp.mkd(self.root)
            ftp.storbinary('STOR '+self.root+'/'+self.marker,io.BytesIO(self.marker_bytes))
        (OUT/'ownership-marker.txt').write_bytes(self.marker_bytes)
        save_json('owned-scope.json',{'run_id':self.run,'root':self.root,'marker':self.marker,'policy':'delete only copied demo descendants; preserve root, marker, and source'})
        self.guard(self.root+'/source')
        for folder in ['source','source/alpha','source/beta','source/beta/deep']:
            self.guard(self.root+'/'+folder)
            with self.ftp() as ftp:ftp.mkd(self.root+'/'+folder)
        for leaf,data in self.seed.items():
            target=self.root+'/source/'+leaf;self.guard(target)
            with self.ftp() as ftp:ftp.storbinary('STOR '+target,io.BytesIO(data))
        self.original=self.snapshot()
        save_json('seed-snapshot.json',self.original)
    def ftp(self):
        ftp=ftplib.FTP();ftp.connect(self.host,21,timeout=20);ftp.login('anonymous','anonymous@');return ftp
    def guard(self,*paths):
        for path in paths:
            assert path.startswith(self.root+'/') and path!=self.root+'/',path
            assert posixpath.normpath(path)==path and all(x not in path for x in ['..','!','@',':']),path
            assert path!=self.root+'/'+self.marker,'Marker cannot be a mutation target'
        buf=io.BytesIO()
        with self.ftp() as ftp:ftp.retrbinary('RETR '+self.root+'/'+self.marker,buf.write)
        assert buf.getvalue()==self.marker_bytes,'Ownership marker mismatch'
        event(ownership='PASS',paths=paths)
    def snapshot(self):
        self.guard(self.root+'/source')
        result={}
        with self.ftp() as ftp:
            def walk(path):
                # LIST has stable Unix-like output on Ultimate; no MLSD assumption.
                lines=[];ftp.retrlines('LIST '+path,lines.append)
                for line in lines:
                    parts=line.split(None,8);assert len(parts)==9,line
                    name=parts[8]
                    if name in ('.','..'):continue
                    assert '/' not in name and name not in ('','..'),name
                    child=path+'/'+name;rel=child[len(self.root)+1:].lower()
                    if line[0]=='d':result[rel]={'kind':'dir'};walk(child)
                    else:
                        data=io.BytesIO();ftp.retrbinary('RETR '+child,data.write)
                        result[rel]={'kind':'file','bytes':len(data.getvalue()),'sha256':hashlib.sha256(data.getvalue()).hexdigest()}
            walk(self.root)
        return result
    def expand(self,path):
        assert path.lower().startswith('@lab:/'),path
        return self.root+'/'+path[6:].lower().rstrip('/')
    def mutate(self,text,paths,needle,pause=8):
        self.guard(*(self.expand(p) for p in paths))
        command(text,needle,pause)
    def preview(self,text,paths):
        self.guard(*(self.expand(p) for p in paths));before=self.snapshot()
        command(text,'DONE W0 D0 M0',8)
        after=self.snapshot();assert before==after,'What-if changed the test tree'
        event(case='whatif-'+text.split()[0].lower()+'-unchanged',result='PASS')
    def subtree(self,snapshot,prefix):return {k[len(prefix)+1:]:v for k,v in snapshot.items() if k.startswith(prefix+'/')}
    def verify(self,phase):
        snap=self.snapshot();save_json(phase+'-snapshot.json',snap)
        src=self.subtree(snap,'source');assert src==self.subtree(self.original,'source'),'Source fixture changed'
        if phase=='copied':assert self.subtree(snap,'copy')==src,'Copy differs'
        if phase=='moved':
            assert self.subtree(snap,'moved')==src,'Move differs'
            assert not self.subtree(snap,'copy'),'Move source descendants remain'
        if phase=='deleted':assert not any(k=='moved' or k.startswith('moved/') or k=='copy' or k.startswith('copy/') for k in snap),'Deleted demo descendants remain'
        event(case='nested-'+phase+'-byte-oracle',result='PASS')

PAL=[(0,0,0),(255,255,255),(136,57,50),(103,182,189),(139,63,150),(85,160,73),(64,49,141),(191,206,114),(139,84,41),(87,66,0),(184,105,98),(80,80,80),(120,120,120),(148,224,137),(120,105,196),(159,159,159)]
frames={};frame_times={};first=None;capture_epoch=None;height=272;stop=threading.Event();receive_errors=[];chapters=[];streaming=False
# Ultimate's packed VIC bytes contain the LEFT pixel in the low nibble.
lut=[bytes(PAL[i&15]+PAL[i>>4]) for i in range(256)]
def receive():
    global first,height,capture_epoch
    try:
        while not stop.is_set():
            if not select.select([vid],[],[],.05)[0]:continue
            data=vid.recv(4096);now=time.monotonic()
            if len(data)!=780:continue
            q,f,l,w,n,b,e=struct.unpack_from('<HHHHBBH',data)
            if (w,n,b,e)!=(384,4,4,0):continue
            if first is None:first=f;capture_epoch=time.time()
            index=(f-first)&65535;line=l&32767
            if l&32768:height=line+n
            if line==0:frame_times[index]=now
            buf,rows=frames.setdefault(index,(bytearray(384*272//2),set()))
            buf[line*192:(line+n)*192]=data[12:];rows.update(range(line,line+n))
    except BaseException as error:receive_errors.append(repr(error))
# Match the page prompt directly in passive VIC pixels; never poll C64 RAM
# during directory I/O. Both standard C64 character sets are accepted.
chargen=Path('/opt/homebrew/Cellar/vice/3.10/share/vice/C64/chargen-901225-01.bin').read_bytes()
more_patterns=[]
for bank in (0,2048):
    for letters in (0,64):
        codes=[ord(c)-64+letters if c.isalpha() else ord(c) for c in '-- MORE --']
        more_patterns.append(bytes(1 if chargen[bank+code*8+row] & (128>>bit) else 0 for row in range(8) for code in codes for bit in range(8)))
def is_more(buf):
    def pixel(x,y):
        byte=buf[y*192+x//2];return (byte>>(4 if x&1 else 0))&15
    for top in range(28,min(height-8,245)):
        first=bytes(pixel(32+x,top+y) in (1,7) for y in range(8) for x in range(8))
        for pattern in more_patterns:
            if first!=b''.join(pattern[y*80:y*80+8] for y in range(8)):continue
            actual=bytes(pixel(32+x,top+y) in (1,7) for y in range(8) for x in range(80))
            if actual==pattern:return True
    return False

def wait_ready(minimum=3,timeout=180):
    # Passive VIC observation: no REST DMA while a filesystem command runs.
    started=time.monotonic();time.sleep(minimum)
    while time.monotonic()-started<timeout:
        items=list(frames.items())
        complete=[i for i,(_,rows) in items if len(rows)==height]
        if complete:
            buf=frames[max(complete)][0]
            region=buf[220*192:240*192]
            gray=sum((v&15)==11 for v in region)+sum((v>>4)==11 for v in region)
            if gray>100 or is_more(buf):return
        time.sleep(.2)
    raise RuntimeError('ReadyFS did not return to its gray live-input footer')

def snapshot_png(filename):
    complete=[i for i,(_,rows) in frames.items() if len(rows)==height]
    if complete:
        rgb=b''.join(lut[v] for v in frames[max(complete)][0][:height*192])
        Image.frombytes('RGB',(384,height),rgb).resize((768,height*2),Image.Resampling.NEAREST).save(OUT/filename)
def record_step(text,explanation=None,started=None):
    verb=text.split()[0].upper()
    reasons={'AL':'Give an absolute location a short, reusable name.', 'ALIAS':'An alias names a location without changing its capabilities.',
    'DRIVES':'List responding devices. Only mounts made by ReadyFS have a remembered host path.', 'DV':'The short form of DRIVES shows the same last-mount hints.',
    'MOUNT':'Mount our disposable image through native UCI and remember its resolved path for this session.', 'MO':'An alias resolves to the full image path before the native mount request.',
    'DIR':'List the current directory; disk files use classic names, types and block counts.', 'LS':'The short listing command accepts the same endpoint paths.',
    'STAT':'Inspect file metadata with a last-mount hint for an IEC file.', 'VOLUME':'Show volume details with the same clearly marked historical mount hint.',
    'COPY':'Copy an ordinary byte stream or a selected recursive tree.', 'CP':'The short form of COPY works with aliases and endpoint paths.',
    'COMPARE':'Read both files and check their contents.', 'CM':'Compare contents after a cross-endpoint transfer.',
    'TREE':'Show the folder structure and nested files.', 'MOVE':'Move the copied tree, keeping the original source safe.', 'MV':'Move nested folders with the short command and option forms.',
    'DELETE':'Preview removal of the copied test data.', 'RM':'Delete only the owned demonstration descendants.', 'MD':'Create an empty destination inside the test root.', 'MKDIR':'Create a destination with the full command name.', 'RD':'Remove an empty test directory.', 'RMDIR':'Remove the remaining empty copy root.',
    'HELP':'Read command-specific help and varied examples.', 'H':'Command help also accepts short command names.', 'CD':'Change the current location so relative paths have a clear base.'}
    description=explanation or reasons.get(verb,'Run the command and read its actual result.')
    if ' --whatif' in text.lower() or ' -w' in text.lower():description+=' What-if previews the plan without changing storage.'
    number=len(steps)+1; filename=f'step-{number:02d}.png';snapshot_png(filename)
    screen=capture(f'script-step-{number:02d}');colors=read(0xD800,1000)
    steps.append({'time':time.time(),'group':len(chapters)-1,'input':text,'explanation':description,'screenshot':filename,'screen':'\n'.join(line[4:] for line in screen.splitlines()[:25]),'start_time':started or chapters[-1]['time'],'screen_rows':[{'text':line.rstrip(),'color':next((colors[row*40+i]&15 for i,c in enumerate(line[:40]) if c!=' '),1)} for row,line in enumerate([line[4:] for line in screen.splitlines()[:25]])]})

def chapter(title,description):
    chapters.append({'time':time.time(),'title':title,'description':description})
    event(chapter=title);time.sleep(2)
    complete=[i for i,(buf,rows) in frames.items() if len(rows)==height]
    if complete:
        rgb=b''.join(lut[v] for v in frames[max(complete)][0][:height*192])
        Image.frombytes('RGB',(384,height),rgb).resize((768,height*2),Image.Resampling.NEAREST).save(OUT/f'chapter-{len(chapters):02d}.png')
def encode():
    assert not receive_errors,receive_errors
    complete=[i for i,(buf,rows) in frames.items() if len(rows)==height];assert complete,'No complete VIC frames'
    lo=min(complete);hi=max(complete);fps=985248/19656
    ff=subprocess.Popen(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'384x{height}','-framerate',str(fps),'-i','-','-vf','scale=768:-2:flags=neighbor,setsar=1','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'readyfs-demo.mp4')],stdin=subprocess.PIPE)
    prev=frames[lo][0];missing=0
    for i in range(lo,hi+1):
        if i in frames and len(frames[i][1])==height:prev=frames[i][0]
        else:missing+=1
        rgb=b''.join(lut[v] for v in prev[:height*192]);ff.stdin.write(rgb)
        if i==lo:Image.frombytes('RGB',(384,height),rgb).resize((768,height*2),Image.Resampling.NEAREST).save(OUT/'poster.png')
    ff.stdin.close();assert ff.wait()==0
    duration=(hi-lo+1)/fps
    save_json('capture-timing.json',{'first_packet_epoch':capture_epoch,'chapters':chapters,'first_frame':lo})
    for item in chapters:item['seconds']=max(0,item.pop('time')-capture_epoch-lo/fps)
    save_json('chapters.json',chapters)
    for item in steps:
        item['seconds']=max(0,item.pop('time')-capture_epoch-lo/fps)
        item['start_seconds']=max(0,item.pop('start_time')-capture_epoch-lo/fps)
    save_json('script.json',steps)
    def stamp(seconds):
        ms=round(seconds*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
    vtt='WEBVTT\n\n'
    for i,item in enumerate(chapters):
        end=chapters[i+1]['seconds'] if i+1<len(chapters) else duration
        vtt+=f"{i+1}\n{stamp(item['seconds'])} --> {stamp(end)}\n{item['title']}\n{item['description']}\n\n"
    (OUT/'captions.vtt').write_text(vtt)
    report={'source':'physical C64 Ultimate VIC UDP stream','cpu_mhz':1,'frames':hi-lo+1,'complete_frames':len(complete),'duplicated_missing_frames':missing,'fps':fps,'seconds':duration,'dimensions':[768,height*2],'audio':'silent; ReadyFS produces no music','sha256':hashlib.sha256((OUT/'readyfs-demo.mp4').read_bytes()).hexdigest(),'checks':sum('"result": "PASS"' in line and '"case"' in line for line in (OUT/'events.jsonl').read_text().splitlines())}
    save_json('video-report.json',report);event(video=report)

labels=(ARTIFACTS/'readyfs-overlay.lbl').read_text()
line_address=int(re.search(r'^al ([0-9A-F]{6}) \._line_buf$',labels,re.M)[1],16)
snapshot=OUT/'build-snapshot';snapshot.mkdir(exist_ok=True)
build_files=list(ARTIFACTS.glob('*.prg'))+[
    ARTIFACTS/'readyfs-overlay-lab.d81',
    ARTIFACTS/'readyfs-overlay.lbl',
    ARTIFACTS/'readyfs-build-report.json',
    (ARTIFACTS/'readyfs-overlay.map' if (ARTIFACTS/'readyfs-overlay.map').exists() else ROOT/'obj/readyfs-overlay.map')]
for file in build_files:shutil.copy2(file,snapshot/file.name)
save_json('build-hashes.json',{file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in build_files})
mounted=False;saved=None;b_saved=None;rc=1;vid=None;thread=None;extra_baseline=None
(OUT/'status.txt').write_text('running\n')
try:
    original=js('/drives');save_json('original-drives.json',original)
    drive=next(d['a'] for d in original['drives'] if 'a' in d)
    drive_b=next(d['b'] for d in original['drives'] if 'b' in d)
    assert not drive_b.get('image_file') and not drive_b.get('image_path'),'Drive B occupied; refuse to replace it'
    assert not any(v.get('enabled') and v.get('bus_id')==9 for d in original['drives'] for v in d.values()),'Device 9 already occupied'
    b_config=js('/configs/Drive%20B%20Settings')['Drive B Settings'];save_json('original-drive-b-config.json',b_config)
    b_saved={k:b_config[k] for k in ('Drive','Drive Type','Drive Bus ID')}
    config=js('/configs/U64%20Specific%20Settings');save_json('original-u64-config.json',config)
    saved={k:config['U64 Specific Settings'][k] for k in ('Turbo Control','CPU Speed')}
    save_json('restore-speed.json',{'U64 Specific Settings':saved})
    owned=OwnedDemo()
    owned_image=owned.root+'/media.d81';owned.guard(owned_image)
    with owned.ftp() as ftp:ftp.storbinary('STOR '+owned_image,io.BytesIO((ARTIFACTS/'readyfs-overlay-lab.d81').read_bytes()))
    owned.original=owned.snapshot();save_json('seed-snapshot.json',owned.original)
    payload={'Drive B Settings':{'Drive':'Enabled','Drive Type':'1581','Drive Bus ID':9}}
    api('/configs','POST',json.dumps(payload).encode(),'application/json');mounted=True
    owned.guard(owned_image)
    api('/drives/b:mount?image='+urllib.parse.quote(owned_image,safe='')+'&mode=readwrite&type=d81','PUT')
    time.sleep(2)
    now=js('/drives');assert next(d['a'] for d in now['drives'] if 'a' in d)==drive,'Drive A changed'
    def guard_disk():
        owned.guard(owned_image)
        current=js('/drives');assert next(d['a'] for d in current['drives'] if 'a' in d)==drive,'Drive A changed'
        b=next(d['b'] for d in current['drives'] if 'b' in d)
        assert b['bus_id']==9 and b['enabled'] and posixpath.normpath(b['image_file'] if b['image_file'].startswith('/') else b['image_path'].rstrip('/')+'/'+b['image_file']).lower()==owned_image.lower(),b
    binary=bytearray((ARTIFACTS/'readyfs-overlay.prg').read_bytes())
    load=int.from_bytes(binary[:2],'little');boot=int(re.search(r'^al ([0-9A-F]{6}) \._readyfs_boot_device$',labels,re.M)[1],16)
    assert binary[boot-load+2]==8;binary[boot-load+2]=9
    (OUT/'boot-device-9.prg').write_bytes(binary);save_json('boot-patch.json',{'address':boot,'original':8,'demo':9,'reason':'preserve occupied user device 8'})
    speed(64)
    event(phase='launch-overlay-from-owned-device-9')
    response=api('/runners:run_prg','POST',bytes(binary),'application/octet-stream',45)
    (OUT/'launch-response.json').write_bytes(response)
    event(phase='sidecar-load-quiet-wait',wait_seconds=180);time.sleep(180)
    check('boot','UP/DN HIST');speed(1)
    route=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);route.connect((os.environ.get('C64U_HOST','10.0.0.79'),80));local_ip=route.getsockname()[0];route.close()
    vid=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);vid.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8*1024*1024);vid.bind(('',11000))
    thread=threading.Thread(target=receive);thread.start()
    api('/streams/video:start?ip='+local_ip+':11000','PUT');streaming=True;time.sleep(3)
    assert frames,'Video stream not received'
    if FAST:
        keys('AL LAB u:/usb1/READYFS_TEST/'+owned.run,False);keys([13],False);wait_ready(3)
        if os.environ.get('READYFS_SD2IEC_BASELINE') == '1':
            command('PROBE IEC 10:','STATUS:',4)
            command('PROFILE IEC 10:','PROFILE:',4)
            command('DIR 10:/',pause=4)
            page=0
            while '-- MORE --' in capture(f'sd2iec-initial-directory-{page:02d}').upper():
                page+=1
                assert page<=32,'SD2IEC initial listing exceeds bounded inventory'
                keys(' ',False);time.sleep(2)
            event(case='sd2iec-present-readonly-inventory',result='PASS')
        for mhz in (1,16,64):
            speed(mhz);guard_disk()
            command('MOUNT @LAB:/MEDIA.D81 9: --force','LAST MOUNTED BY READYFS')
            check(f'mount-path-{mhz}mhz','MAY HAVE CHANGED ELSEWHERE')
            command('DIR 9:/',pause=3)
            while '-- MORE --' in capture('preflight-dir-page').upper():keys(' ',False);time.sleep(2)
            guard_disk();owned.guard(owned.root+f'/disk-{mhz}.seq')
            command(f'CP 9:/RFVIEW @LAB:/DISK-{mhz}.SEQ','COPIED',5)
            command(f'COMPARE 9:/RFVIEW @LAB:/DISK-{mhz}.SEQ','VERIFY: IDENTICAL',5)
            event(case=f'native-mount-cross-copy-{mhz}mhz',result='PASS')
        speed(1)
        guard_disk();owned.guard(owned_image)
        command('CP @LAB:/SOURCE/README.SEQ 9:/HOSTSEQ','COPIED',5)
        command('COMPARE 9:/HOSTSEQ @LAB:/SOURCE/README.SEQ','VERIFY: IDENTICAL',5)
        command('DISMOUNT 9: --force','MEDIA DISMOUNTED')
        command('DRIVES','9: IMAGE PATH UNKNOWN')
        event(case='dismount-invalidates-path',result='PASS')
        snap=owned.snapshot()
        fixture=(ROOT/'build_support/readyfs_content_view.seq').read_bytes()
        expected={'kind':'file','bytes':len(fixture),'sha256':hashlib.sha256(fixture).hexdigest()}
        for mhz in (1,16,64):assert snap[f'disk-{mhz}.seq']==expected
        event(case='disk-to-host-independent-byte-oracle',result='PASS')
        if os.environ.get('READYFS_SD2IEC_BASELINE') == '3':
            from readyfs_iec_config_hardware import run as config_acceptance
            config_acceptance(globals())
        if os.environ.get('READYFS_SD2IEC_BASELINE') in ('2', '3'):
            from readyfs_sd2iec_baseline import Baseline
            extra_baseline=Baseline(globals())
            extra_baseline.run()
        rc=0
    else:
        # Unfilmed admission checks on the exact build being recorded.
        # Native UCI is state-driven at each CPU speed; only human typing is paced.
        for mhz in (1,16,64):
            speed(mhz);guard_disk()
            keys('MOUNT u:'+owned_image+' 9: --force',False);keys([13],False);wait_ready(3)
            check(f'exact-build-native-mount-{mhz}mhz','MAY HAVE CHANGED ELSEWHERE')
        speed(1);guard_disk()
        keys('DISMOUNT 9: --force',False);keys([13],False);wait_ready(3)
        keys('DRIVES',False);keys([13],False);wait_ready(3);check('exact-build-dismount-invalidates','9: IMAGE PATH UNKNOWN')
        owned.guard(owned_image)
        current=js('/drives');assert next(d['a'] for d in current['drives'] if 'a' in d)==drive
        b=next(d['b'] for d in current['drives'] if 'b' in d);assert not b.get('image_file')
        api('/drives/b:mount?image='+urllib.parse.quote(owned_image,safe='')+'&mode=readwrite&type=d81','PUT')
        guard_disk();keys('CLEAR',False);keys([13],False);wait_ready(3)
        if int(os.environ.get('READYFS_DEMO_FROM','1')) <= 1:
            chapter('01 · Help and classic directories','Cyan commands, white results. HELP accepts full command names and shortcuts.')
            command('HELP DIR','QUOTED NAMES, TYPES',5)
            color=read(0xD800,1000);lines=capture('color-oracle').splitlines()
            row=next(i for i,line in enumerate(lines) if 'RF> HELP DIR' in line.upper())
            assert all((c&15)==3 for c in color[row*40:row*40+12])
            row=next(i for i,line in enumerate(lines) if 'QUOTED NAMES, TYPES' in line.upper())
            assert all((c&15)==1 for c in color[row*40:row*40+20])
            event(case='command-output-colors',result='PASS')
            command('DIR 9:/',pause=6)
            if '-- MORE --' in capture('directory-first-page').upper():verify_more_color('yellow-pager-oracle');keys(' ');time.sleep(6)
            check('classic-directory','BLOCKS FREE.')
            command('HELP CP','CP @LAB:/SRC @LAB:/COPY -R -W',5)
            command('AL LAB u:/usb1/READYFS_TEST/'+owned.run,'ALIAS SET',4)
            command('TREE @LAB:/SOURCE','TREE DONE',6)
            chapter('02 · Native mounts and endpoint boundaries','ReadyFS uses its native interface. Mount paths are session hints and can become stale after changes elsewhere.')
            command('DRIVES','9: IMAGE PATH UNKNOWN',5)
            command('DIR 8:/',pause=5)
            while '-- MORE --' in capture('external-drive-directory-page').upper():keys(' ');time.sleep(5)
            guard_disk();command('MOUNT @LAB:/MEDIA.D81 9: --force','LAST MOUNTED BY READYFS',6)
            command('DV','MAY HAVE CHANGED ELSEWHERE',5)
            command('DIR 9:/',pause=5)
            while '-- MORE --' in capture('mounted-directory-page').upper():keys(' ');time.sleep(5)
            check('mounted-directory-context','BLOCKS FREE.')
            command('STAT 9:/RFVIEW','LAST MOUNTED BY READYFS',5)
            command('VOLUME 9:/','MAY HAVE CHANGED ELSEWHERE',5)
            command('AL DISK 9:/','ALIAS SET',4)
            chapter('03 · Disk files and host files','Copy a disk file out through an alias, then copy a host file into our disposable mounted disk. Compare both directions.')
            guard_disk();owned.mutate('COPY @DISK:/RFVIEW @LAB:/FROM-DISK.SEQ',['@LAB:/FROM-DISK.SEQ'],'COPIED',8)
            command('COMPARE @DISK:/RFVIEW @LAB:/FROM-DISK.SEQ','VERIFY: IDENTICAL',5)
            guard_disk();command('CP @LAB:/SOURCE/README.SEQ @DISK:/HOSTSEQ','COPIED',8)
            command('COMPARE @DISK:/HOSTSEQ @LAB:/SOURCE/README.SEQ','VERIFY: IDENTICAL',5)
            command('DIR 9:/FOLDER','UNSUPPORTED',5)
            text=capture('red-error-text');color=read(0xD800,1000)
            row=next(i for i,line in enumerate(text.splitlines()) if line[4:].strip()=='UNSUPPORTED')
            assert all((v&15)==2 for v in color[row*40:row*40+11]);event(case='red-unsupported-error',result='PASS')
            event(case='alias-cross-endpoint-both-directions',result='PASS')
            chapter('04 · Edit once, then use the command','Insert a missing letter in HEAD; edit and navigate a long quoted command.')
            keys('HED @LAB:/SOURCE/README.SEQ 2');time.sleep(2);keys([19,29,29]);keys('A');time.sleep(2);keys([147,13]);time.sleep(6)
            check('insert-middle','SOURCE STAYS SAFE');record_step('HEAD @LAB:/SOURCE/README.SEQ 2','Insert the missing A in HED using Home and cursor movement, then execute HEAD.')
            long_started=time.time()
            prefix='WRITE "@LAB:/field notes.seq" "';suffix='" --whatif'
            body=('LONG INPUT, SMALL REDRAWS. USE HOME AND END TO NAVIGATE THE FOUR ROW EDITOR. '*4)[:255-len(prefix)-len(suffix)]
            longline=prefix+body+suffix;assert len(longline)==255
            owned.guard(owned.root+'/field notes.seq');before=owned.snapshot()
            keys(longline);time.sleep(3);assert read(line_address,256)==longline.upper().encode()+b'\0';event(case='255-byte-input',result='PASS');snapshot_png('editor-255-byte.png')
            keys([19]);time.sleep(2);keys([147]);time.sleep(2);keys([157]*12);keys([148]);keys('X');keys([148]);time.sleep(2)
            check('overwrite-prompt','RF>')
            executed=read(line_address,256).split(b'\0',1)[0].decode('ascii')
            keys([13]);time.sleep(6);check('long-preview','DONE W0 D0 M0');assert before==owned.snapshot();record_step(executed,'Edit a 255-byte quoted command using Home, End and overwrite mode. Execute only its preview.',started=long_started);steps[-1]['editor_screenshot']='editor-255-byte.png'
            chapter('05 · Command history and output pages','Up/down recall commands and restore a draft. F1/F3 page older/newer output at a readable pace.')
            keys('HD @LAB:/SOURCE/README.SEQ 1');draft=read(line_address,256);time.sleep(2)
            keys([145]);time.sleep(3);keys([145]);time.sleep(3);keys([17]);time.sleep(3);keys([17]);time.sleep(3)
            assert read(line_address,256)==draft;event(case='history-draft-restored',result='PASS')
            keys([133]);time.sleep(4);check('page-up','OUTPUT:')
            keys([133]);time.sleep(4);capture('older-page')
            keys([134]);time.sleep(4);capture('newer-page')
            keys([3]);time.sleep(2);assert read(line_address,256)==draft;event(case='paging-draft-unchanged',result='PASS')
            keys([13]);time.sleep(5);check('draft-executed-after-paging','READYFS NESTED DEMO');record_step('HD @LAB:/SOURCE/README.SEQ 1','Recall older commands, restore an unsent draft, page output with F1/F3, then execute the preserved draft.')
        chapter('06 · Preview and copy a nested tree','Five files in alpha and beta/deep. What-if leaves storage unchanged; the real copy preserves every byte.')
        if int(os.environ.get('READYFS_DEMO_FROM','1')) > 1:
            command('AL LAB u:/usb1/READYFS_TEST/'+owned.run,'ALIAS SET',4)
            command('TREE @LAB:/SOURCE','TREE DONE',6)
        owned.preview('CP @LAB:/SOURCE @LAB:/COPY -R -W',['@LAB:/SOURCE','@LAB:/COPY'])
        owned.mutate('MD @LAB:/COPY',['@LAB:/COPY'],'DIRECTORY CREATED')
        owned.mutate('COPY @LAB:/SOURCE @LAB:/COPY --recursive',['@LAB:/SOURCE','@LAB:/COPY'],'FAIL 0',16)
        owned.verify('copied');command('TREE @LAB:/COPY','TREE DONE',6)
        chapter('07 · Move the copied folders','Preview first, then move both folders and their nested files. The original source stays intact.')
        owned.mutate('MKDIR @LAB:/MOVED',['@LAB:/MOVED'],'DIRECTORY CREATED')
        owned.preview('MOVE @LAB:/COPY @LAB:/MOVED --recursive --whatif',['@LAB:/COPY','@LAB:/MOVED'])
        owned.mutate('MV @LAB:/COPY @LAB:/MOVED -R',['@LAB:/COPY','@LAB:/MOVED'],'FAIL 0',18)
        owned.verify('moved');command('TREE @LAB:/MOVED','TREE DONE',6)
        chapter('08 · Preview, delete, and check the survivors','Only this run’s copied fixtures are deleted. Empty roots are removed separately; source and ownership marker remain.')
        command('H RM','DELETE PATH',5)
        owned.preview('DELETE @LAB:/MOVED --recursive --whatif',['@LAB:/MOVED'])
        owned.mutate('RM @LAB:/MOVED -R -Y',['@LAB:/MOVED'],'FAIL 0',16)
        owned.mutate('RD @LAB:/MOVED -Y',['@LAB:/MOVED'],'DIRECTORY REMOVED')
        owned.mutate('RMDIR @LAB:/COPY --yes',['@LAB:/COPY'],'DIRECTORY REMOVED')
        owned.verify('deleted')
        command('CD @LAB:/SOURCE');command('DIR','DIR',6)
        command('TREE .','TREE DONE',6)
        chapter('09 · Checked on real hardware','Nested copy, move and delete verified independently. What-if snapshots match; the original source is preserved.')
        time.sleep(7);rc=0
except Exception as error:
    event(result='FAIL',error=repr(error));raise
finally:
    if streaming:
        try:api('/streams/video:stop','PUT')
        except Exception as error:event(restore='stream',error=repr(error))
    stop.set()
    if thread:thread.join()
    if vid:vid.close()
    restored=True
    if extra_baseline is not None:
        try:extra_baseline.restore()
        except Exception as error:restored=False;event(restore='SoftwareIEC cwd',error=repr(error))
    if saved is not None:
        try:subprocess.run(['/bin/bash',str(ROOT/'build_support/run_readyfs_c64u_restore_speed.sh'),str(OUT),os.environ.get('C64U_HOST','10.0.0.79')],check=True)
        except Exception as error:restored=False;event(restore='CPU settings',error=repr(error))
    if mounted:
        try:
            current=js('/drives');b=next(d['b'] for d in current['drives'] if 'b' in d)
            if b.get('image_file'):
                guard_disk();api('/drives/b:remove','PUT')
                image=io.BytesIO()
                with owned.ftp() as ftp:ftp.retrbinary('RETR '+owned_image,image.write)
                (OUT/'owned-media-after.d81').write_bytes(image.getvalue())
            api('/configs','POST',json.dumps({'Drive B Settings':b_saved}).encode(),'application/json')
            time.sleep(1);final=js('/drives');save_json('restored-drives.json',final)
            assert next(d['a'] for d in final['drives'] if 'a' in d)==drive
            now=next(d['b'] for d in final['drives'] if 'b' in d)
            assert all(now.get(k)==drive_b.get(k) for k in ('enabled','bus_id','type','image_file','image_path'))
        except Exception as error:restored=False;event(restore='Drive B',error=repr(error))
    if frames and not FAST:
        event(phase='encoding');encode()
    (OUT/'status.txt').write_text('success\n' if rc==0 and restored else 'failed\n')
    event(complete=True,restored=restored,result='PASS' if rc==0 and restored else 'FAIL')
