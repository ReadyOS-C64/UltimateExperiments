#!/usr/bin/env python3
"""Human-paced, read-only ReadyFS tour with actual physical VIC UDP video.

Mounts only the local test image in an empty drive. All write/copy commands
are previews. Preserves evidence and restores drive/CPU settings on exit.
"""
from pathlib import Path
import json, os, re, subprocess, time, urllib.request, urllib.error, urllib.parse
import socket, struct, threading, select, random, hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(os.environ['READYFS_DEMO_OUT']); OUT.mkdir(parents=True,exist_ok=True)
API='http://'+os.environ.get('C64U_HOST','10.0.0.79')+'/v1'
log=(OUT/'events.jsonl').open('a',buffering=1)
random.seed(64)
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
    if isinstance(data,str):data=bytes(0xBF if char=='\\' else ord(char) for char in data.upper())
    for key in data:
        deadline=time.monotonic()+12
        while read(0xC6,1)!=b'\0':
            if time.monotonic()>deadline:raise RuntimeError('keyboard did not drain')
            time.sleep(.03)
        write(0xC5,b'\0\0');write(0x277,bytes([key]));write(0xC6,b'\1')
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
def command(text,needle=None,pause=4):
    event(command=text);keys(text);time.sleep(.65);keys([13]);time.sleep(pause)
    if needle:check('case-'+str(len(list(OUT.glob('case-*')))).zfill(2),needle)
def speed(mhz):
    api('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual','PUT')
    api('/configs/U64%20Specific%20Settings/CPU%20Speed?value='+urllib.parse.quote(f'{mhz:2d}'),'PUT')
    if mhz==1:api('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off','PUT')
    time.sleep(1)
    state=js('/configs/U64%20Specific%20Settings')['U64 Specific Settings']
    assert int(str(state['CPU Speed']).strip())==mhz

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
    def stamp(seconds):
        ms=round(seconds*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
    vtt='WEBVTT\n\n'
    for i,item in enumerate(chapters):
        end=chapters[i+1]['seconds'] if i+1<len(chapters) else duration
        vtt+=f"{i+1}\n{stamp(item['seconds'])} --> {stamp(end)}\n{item['title']}\n{item['description']}\n\n"
    (OUT/'captions.vtt').write_text(vtt)
    report={'source':'physical C64 Ultimate VIC UDP stream','cpu_mhz':1,'frames':hi-lo+1,'complete_frames':len(complete),'duplicated_missing_frames':missing,'fps':fps,'seconds':duration,'dimensions':[768,height*2],'audio':'silent; ReadyFS produces no music','sha256':hashlib.sha256((OUT/'readyfs-demo.mp4').read_bytes()).hexdigest(),'checks':sum('"result": "PASS"' in line and '"case"' in line for line in (OUT/'events.jsonl').read_text().splitlines())}
    save_json('video-report.json',report);event(video=report)

labels=(ROOT/'artifacts/readyfs/readyfs-overlay.lbl').read_text()
line_address=int(re.search(r'^al ([0-9A-F]{6}) \._line_buf$',labels,re.M)[1],16)
mounted=False;saved=None;rc=1;vid=None;thread=None
(OUT/'status.txt').write_text('running\n')
try:
    original=js('/drives');save_json('original-drives.json',original)
    drive=next(d['a'] for d in original['drives'] if 'a' in d)
    assert not drive.get('image_file') and not drive.get('image_path'),'Drive A occupied'
    assert drive['enabled'] and drive['bus_id']==8 and drive['type']=='1581','Drive A must be empty enabled 1581 on bus 8'
    config=js('/configs/U64%20Specific%20Settings');save_json('original-u64-config.json',config)
    saved={k:config['U64 Specific Settings'][k] for k in ('Turbo Control','CPU Speed')}
    save_json('restore-speed.json',{'U64 Specific Settings':saved})
    if os.environ.get('READYFS_DEMO_ATTACH_LIVE')=='1':speed(1)
    event(phase='mount-build-fixture');mounted=True
    response=subprocess.check_output(['curl','--fail','--silent','--show-error','--max-time','60','-X','POST','-F',f"file=@{ROOT/'artifacts/readyfs/readyfs-overlay-lab.d81'}",'-F','mode=readonly','-F','type=d81',API+'/drives/a:mount'])
    (OUT/'mount-response.json').write_bytes(response);time.sleep(2)
    if os.environ.get('READYFS_DEMO_ATTACH_LIVE')=='1':
        from readyfs_build_report import segments, OVERLAY_MAP
        binary=(ROOT/'artifacts/readyfs/readyfs-overlay.prg').read_bytes()
        load=int.from_bytes(binary[:2],'little')
        for name,segment in segments(OVERLAY_MAP).items():
            if name not in ('CODE','RODATA'):continue
            for address in range(segment['start'],segment['end']+1,1024):
                count=min(1024,segment['end']+1-address)
                assert read(address,count)==binary[2+address-load:2+address-load+count],f'Live {name} differs'
        event(phase='attached-to-verified-resident')
        keys([3],False)
    else:
        event(phase='launch-overlay')
        try:
            response=api('/runners:run_prg','POST',(ROOT/'artifacts/readyfs/readyfs-overlay.prg').read_bytes(),'application/octet-stream',45)
            (OUT/'launch-response.json').write_bytes(response)
        except urllib.error.HTTPError as error:
            if error.code!=404:raise
            event(phase='IEC-load-fallback',wait_seconds=240)
            api('/machine:reset','PUT');time.sleep(3);api('/machine:resume','PUT');time.sleep(7)
            keys('LOAD"READYFS-OVERLAY",8,1\r',False);time.sleep(240);keys('SYS2061\r',False)
        event(phase='sidecar-load-quiet-wait',wait_seconds=180);time.sleep(180)
    check('boot','UP/DN HIST');speed(1)
    if int(os.environ.get('READYFS_DEMO_FROM','1'))>1:
        keys('CD 8:/\r',False);time.sleep(1);keys('AL DISK 8:/\r',False);time.sleep(1)
    route=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);route.connect((os.environ.get('C64U_HOST','10.0.0.79'),80));local_ip=route.getsockname()[0];route.close()
    vid=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);vid.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8*1024*1024);vid.bind(('',11000))
    thread=threading.Thread(target=receive);thread.start()
    api('/streams/video:start?ip='+local_ip+':11000','PUT');streaming=True;time.sleep(3)
    assert frames,'Video stream not received'
    if int(os.environ.get('READYFS_DEMO_FROM','1'))<=1:
        chapter('01 · ReadyFS on a real C64','1 MHz. Actual VIC display; human-paced keystrokes throughout.')
        command('HELP','PROBE ALL',6);command('PROBE UCI','UCI: BASE',5)
        command('CD 8:/');command('PWD','8:/',4)
        chapter('02 · Insert, overwrite, Home and End','Correct a missing letter, replace a typo, and remove unwanted text.')
        keys('PD');time.sleep(2);keys([157]);time.sleep(1);keys('W');time.sleep(2)
        assert read(line_address,4)==b'PWD\0';event(case='insert-middle',result='PASS');keys([13]);time.sleep(4)
        keys('PXD');time.sleep(2);keys([19]);time.sleep(1);keys([29]);keys([148]);time.sleep(2);keys('W');time.sleep(2)
        assert read(line_address,4)==b'PWD\0';check('overwrite-prompt','OV>');keys([13]);time.sleep(4)
        keys('XPWDZ');time.sleep(2);keys([19]);keys([29]);time.sleep(1);keys([20]);keys([147]);time.sleep(1);keys([20]);time.sleep(2)
        assert read(line_address,4)==b'PWD\0';event(case='home-end-delete',result='PASS');keys([13]);time.sleep(4)
        chapter('03 · Files, aliases and relative paths','Read the same fixture using absolute, relative and @alias paths.')
        command('HEAD 8:/RFVIEW 3','VIEW03',6)
        command('HD RFVIEW 2','VIEW02',5)
        command('ALIAS DISK 8:/','ALIAS SET',4)
        command('CD @DISK:/');command('PW','8:/',4)
        command('TAIL @DISK:/RFVIEW 2','VIEW12',6)
        command('CR 8:/RFVIEW','CRC32',5)
        command('FIND 8:/ --include RFVIEW','FIND DONE',7)
        command('FI @DISK:/ -I RFVIEW','FIND DONE',7)
    if int(os.environ.get('READYFS_DEMO_FROM','1'))<=4:
        chapter('04 · Long lines and the moving input viewport','Type a 255-byte command. Scroll to its beginning and end; edit the tail.')
        # Preview has no filesystem side effects, including for nonexistent paths.
        prefix='WRITE u:/usb1/READYFS_TEST/DEMO/notes.seq "'
        suffix='" --whatif'
        text='LONG LINES STAY EDITABLE. CURSOR MOTION SCROLLS THE FOUR ROW VIEWPORT. '
        body=(text*5)[:255-len(prefix)-len(suffix)-10]+'FINAL MARK'
        longline=prefix+body+suffix;assert len(longline)==255
        keys(longline);time.sleep(4)
        assert read(line_address,256)==longline.upper().encode()+b'\0';event(case='255-byte-input',result='PASS')
        keys([19]);time.sleep(4)
        keys([147]);time.sleep(4)
        keys([157]*12);time.sleep(2);keys([148]);time.sleep(1);keys('K');keys([148]);time.sleep(2)
        keys([13]);time.sleep(5);check('long-preview','DONE W0 D0 M0')
        chapter('05 · Recall, edit and restore a draft','Up walks older commands. Down walks newer ones and restores the unsent draft.')
        command('HD 8:/RFVIEW 2','VIEW02',4)
        keys('PWD');time.sleep(2)
        keys([145]);time.sleep(3);keys([145]);time.sleep(3);keys([145]);time.sleep(3)
        keys([17]);time.sleep(3);keys([17]);time.sleep(3);keys([17]);time.sleep(3)
        assert read(line_address,4)==b'PWD\0';event(case='history-draft-restored',result='PASS');keys([3]);time.sleep(2)
        keys([145]);time.sleep(3);keys([147]);keys([20]);keys('4');time.sleep(2);keys([13]);time.sleep(5);check('edited-recall','VIEW04')
        chapter('06 · Full and short options; quoted paths','Dry-run write and copy commands show plans without changing storage.')
        command('WRITE u:/usb1/READYFS_TEST/DEMO/notes.seq "A quoted message" --dry-run --line','DONE W0 D0 M0',5)
        command('WR "u:/usb1/READYFS_TEST/DEMO/field notes.seq" "SHORT FLAGS" -W -L','DONE W0 D0 M0',5)
        command('COPY 8:/RFVIEW u:/usb1/READYFS_TEST/DEMO/copy.seq --whatif','DONE W0 D0 M0',5)
        command('CP @DISK:/RFVIEW u:/usb1/READYFS_TEST/DEMO/copy.seq -W','DONE W0 D0 M0',5)
        command('NATIVE OPEN 11.3:/GAMES/HELLO.PRG','NATIVE:',5)
        command('NT DIR 11.3:/GAMES/TOOLS/','NATIVE:',5)
    chapter('07 · Page Up and Page Down through output','F1 = Page Up; F3 = Page Down. Pauses let you read each page. STOP restores the draft.')
    command('H','PROBE ALL',5)
    keys('HD @DISK:/RFVIEW 5');time.sleep(3);draft=read(line_address,18)
    keys([133]);time.sleep(4);check('page-up','OUTPUT:')
    used_address=int(re.search(r'^al ([0-9A-F]{6}) \._readyfs_console_used$',labels,re.M)[1],16)
    available_moves=min(4,(int.from_bytes(read(used_address,2),'little')-1)//23)
    assert available_moves>=1,'Need older output for paging demonstration'
    event(paging_moves=available_moves)
    for i in range(available_moves):keys([133]);time.sleep(4);capture(f'page-older-{i}')
    for i in range(available_moves):keys([134]);time.sleep(4);capture(f'page-newer-{i}')
    keys([3]);time.sleep(4)
    assert read(line_address,18)==draft;check('paging-draft-restored','UP/DN HIST');event(case='paging-draft-unchanged',result='PASS')
    keys([13]);time.sleep(6);check('draft-executed-after-paging','VIEW05')
    chapter('08 · Join a command across entries','F7 joins input with a space. Finish the quoted message on the next entry.')
    keys('WR "" "FIRST PART');time.sleep(3);keys([136]);time.sleep(3);check('continuation','JOIN:')
    keys('SECOND PART" -W');time.sleep(3);keys([13]);time.sleep(5);check('continuation-preview','DONE W0 D0 M0')
    command('UNALIAS DISK','REMOVED',4);command('PW','8:/',5)
    chapter('09 · Demo complete','Editing, 255-byte input, history, paging, aliases and dry-run options checked on hardware.')
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
    if saved is not None:
        try:subprocess.run(['/bin/bash',str(ROOT/'build_support/run_readyfs_c64u_restore_speed.sh'),str(OUT),os.environ.get('C64U_HOST','10.0.0.79')],check=True)
        except Exception as error:restored=False;event(restore='CPU settings',error=repr(error))
    if mounted:
        try:
            api('/drives/a:remove','PUT');time.sleep(1);final=js('/drives');save_json('restored-drives.json',final)
            now=next(d['a'] for d in final['drives'] if 'a' in d)
            assert all(now.get(k)==drive.get(k) for k in ('enabled','bus_id','type','image_file','image_path'))
        except Exception as error:restored=False;event(restore='Drive A',error=repr(error))
    if frames:
        event(phase='encoding');encode()
    (OUT/'status.txt').write_text('success\n' if rc==0 and restored else 'failed\n')
    event(complete=True,restored=restored,result='PASS' if rc==0 and restored else 'FAIL')
