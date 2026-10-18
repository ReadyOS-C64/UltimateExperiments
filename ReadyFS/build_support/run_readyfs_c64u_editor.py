#!/usr/bin/env python3
"""Terminal-owned, read-only editor/REU integration proof on C64 Ultimate.

Only mounts the freshly built local fixture in an empty drive A. No storage
files are created or modified. Restores the original CPU settings and unmounts
its fixture in finally, including on failed assertions.
"""
from pathlib import Path
import json, os, re, subprocess, time, urllib.request, urllib.error, urllib.parse
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(os.environ['READYFS_UI_OUT']);OUT.mkdir(parents=True,exist_ok=True)
API='http://'+os.environ.get('C64U_HOST','10.0.0.79')+'/v1'
log=(OUT/'events.jsonl').open('a',buffering=1)
def event(**data):
    data['time']=time.time();log.write(json.dumps(data)+'\n');print(json.dumps(data),flush=True)
def api(path,method='GET',data=None,ctype=None,timeout=20):
    headers={} if ctype is None else {'Content-Type':ctype}
    with urllib.request.urlopen(urllib.request.Request(API+path,data=data,headers=headers,method=method),timeout=timeout) as r:return r.read()
def js(path):return json.loads(api(path))
def save_json(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def read(address,size):return api(f'/machine:readmem?address={address:X}&length={size}')
def write(address,data):return api(f'/machine:writemem?address={address:X}&data={data.hex()}','PUT')
def keys(data):
    if isinstance(data,str):data=bytes(0xBF if char=='\\' else ord(char) for char in data.upper())
    for key in data:
        deadline=time.monotonic()+10
        while read(0xC6,1)!=b'\0':
            if time.monotonic()>deadline:raise RuntimeError('keyboard did not drain')
            time.sleep(.02)
        write(0xC5,b'\0\0');write(0x277,bytes([key]));write(0xC6,b'\1')
        while read(0xC6,1)!=b'\0':
            if time.monotonic()>deadline:raise RuntimeError('key was not consumed')
            time.sleep(.02)
    time.sleep(.15)
def capture(label):
    dest=OUT/label;dest.mkdir(exist_ok=True)
    data=read(0x400,1000);(dest/'screen_0400.bin').write_bytes(data)
    subprocess.run(['python3',str(ROOT/'build_support/decode_c64_screen.py'),str(dest/'screen_0400.bin'),'--output',str(dest/'screen.txt')],check=True)
    return (dest/'screen.txt').read_text()
def check(label,needle):
    for attempt in range(90):
        text=capture(label)
        ready=('UP/DN HIST' in text and 'F7 JOIN' in text) or ('JOIN:' in text and 'F7 JOINS' in text) or 'STOP LIVE' in text
        if needle.upper() in text.upper() and ready:
            event(case=label,result='PASS');return text
        time.sleep(.1)
    raise AssertionError(f'{label}: missing {needle} or unfinished screen')
def speed(mhz):
    api('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual','PUT')
    api('/configs/U64%20Specific%20Settings/CPU%20Speed?value='+urllib.parse.quote(f'{mhz:2d}'),'PUT')
    if mhz==1:api('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off','PUT')
    time.sleep(1)
    state=js('/configs/U64%20Specific%20Settings')['U64 Specific Settings']
    assert int(str(state['CPU Speed']).strip())==mhz
    save_json(f'speed-{mhz}.json',state)
labels=(ROOT/'artifacts/readyfs/readyfs-overlay.lbl').read_text()
line_address=int(re.search(r'^al ([0-9A-F]{6}) \._line_buf$',labels,re.M)[1],16)
mounted=False;saved=None;rc=1
(OUT/'status.txt').write_text('running\n')
try:
    original=js('/drives');save_json('original-drives.json',original)
    drive=next(d['a'] for d in original['drives'] if 'a' in d)
    assert not drive.get('image_file') and not drive.get('image_path'),'Drive A occupied'
    assert drive['enabled'] and drive['bus_id']==8 and drive['type']=='1581','Drive A must be enabled 1581 on bus 8'
    config=js('/configs/U64%20Specific%20Settings');save_json('original-u64-config.json',config)
    saved={k:config['U64 Specific Settings'][k] for k in ('Turbo Control','CPU Speed')}
    save_json('restore-speed.json',{'U64 Specific Settings':saved})
    event(phase='mount-build-fixture')
    mounted=True
    response=subprocess.check_output(['curl','--fail','--silent','--show-error','--max-time','60','-X','POST','-F',f"file=@{ROOT/'artifacts/readyfs/readyfs-overlay-lab.d81'}",'-F','mode=readwrite','-F','type=d81',API+'/drives/a:mount'])
    (OUT/'mount-response.json').write_bytes(response)
    time.sleep(2)
    if os.environ.get('READYFS_UI_ATTACH_LIVE')=='1':
        # Reuse the known live build after an earlier suite restored settings.
        # Compare every immutable resident byte; refuse a different program.
        from readyfs_build_report import segments, OVERLAY_MAP
        binary=(ROOT/'artifacts/readyfs/readyfs-overlay.prg').read_bytes()
        load=int.from_bytes(binary[:2],'little')
        for name,segment in segments(OVERLAY_MAP).items():
            if name not in ('CODE','RODATA'):continue
            for addr in range(segment['start'],segment['end']+1,1024):
                size=min(1024,segment['end']+1-addr)
                assert read(addr,size)==binary[2+addr-load:2+addr-load+size],f'Live {name} differs from build'
        event(phase='attached-to-verified-resident')
    else:
        event(phase='launch-overlay')
        try:
            response=api('/runners:run_prg','POST',(ROOT/'artifacts/readyfs/readyfs-overlay.prg').read_bytes(),'application/octet-stream',45)
            (OUT/'launch-response.json').write_bytes(response)
        except urllib.error.HTTPError as err:
            if err.code!=404:raise
            event(phase='IEC-load-fallback',wait_seconds=240)
            api('/machine:reset','PUT');time.sleep(3);api('/machine:resume','PUT');time.sleep(7)
            keys('LOAD"READYFS-OVERLAY",8,1\r')
            time.sleep(240) # No DMA reads during KERNAL LOAD.
            keys('SYS2061\r')
        event(phase='sidecar-load-quiet-wait',wait_seconds=180)
        time.sleep(180) # Keep REST DMA away from sidecar IEC loading as well.
    check('boot','UP/DN HIST')
    keys('AL UI 8:/\r');check('alias-set','ALIAS SET')
    keys('AL\r');check('alias-list','@UI:')
    keys('CD @UI:/\r');keys('PW\r');check('alias-resolve','8:/')
    keys('UA UI\r');check('alias-remove','REMOVED')
    for mhz in (1,16,64):
        speed(mhz);prefix=f'{mhz}mhz-';event(phase='editor-suite',mhz=mhz)
        keys('PW\r');check(prefix+'short-command','8:/')
        keys('WR \"\" TEXT -W\r');check(prefix+'short-preview','PLAN W1 D0 M0; DONE W0 D0 M0')
        keys('PW\r');check(prefix+'pwd-after-preview','8:/')
        line='UNKNOWN '+'A'*234+'READYFS255END'
        keys(line);assert read(line_address,256)==line.encode()+b'\0'
        check(prefix+'wrapped-255','READYFS255')
        keys([157,157,20,148,88]);capture(prefix+'edit-tail')
        keys([3]);keys('DRAFT');keys([145]);check(prefix+'history-up','PW')
        keys([17]);check(prefix+'draft-return','DRAFT');assert read(line_address,6)==b'DRAFT\0'
        keys([3]);keys('UNKNOWN\\\r');check(prefix+'continuation','JOIN:')
        keys('JOINED\r');check(prefix+'continuation-executed','UNKNOWN; TYPE HELP')
        keys('FI 8:/ -I RFVIEW\r');time.sleep(5);check(prefix+'short-option','FIND DONE')
        keys('PB UCI\r');check(prefix+'uci-probe','UCI: BASE')
        keys('H\r');check(prefix+'help','PROBE ALL')
        for seed in range(1,13):keys(f'SEED{seed:02d}\r')
        keys('CL\r');keys('PW\r');keys('DRAFT')
        check(prefix+'draft-before-output','DRAFT')
        live=read(0x400,1000);color=read(0xD800,1000)
        keys([133]);check(prefix+'page-up','OUTPUT:')
        keys([133]);capture(prefix+'older-output')
        keys([134,134]);check(prefix+'page-down-live','DRAFT')
        restored_screen=read(0x400,1000)
        # Normalize only the live cursor's reverse-video bit (blink phase).
        assert all((a&127)==(b&127) if index==809 else a==b for index,(a,b) in enumerate(zip(restored_screen,live)))
        assert bytes(b&15 for b in read(0xD800,1000))==bytes(b&15 for b in color)
        assert read(line_address,6)==b'DRAFT\0';event(case=prefix+'output-live-restored',result='PASS')
        keys([3])
    keys('RU 8:/RFRING\r')
    for attempt in range(120):
        text=capture('output-ring-wrap')
        if 'COMMANDS 900' in text and 'UP/DN HIST' in text:break
        time.sleep(1)
    assert 'COMMANDS 900' in text and 'RC 0' in text
    used_address=int(re.search(r'^al ([0-9A-F]{6}) \._readyfs_console_used$',labels,re.M)[1],16)
    assert int.from_bytes(read(used_address,2),'little')==800
    event(case='800-row-ring-wrap',result='PASS')
    keys([133]);check('ring-newest-page','OUTPUT:')
    for page in range(34):keys([133])
    check('ring-oldest-page','BATCH> PW')
    keys([3]);check('ring-return-live','UP/DN HIST')
    keys([134,135]);assert read(line_address,1)==b'\0';event(case='function-keys-not-text',result='PASS')
    rc=0
except Exception as error:
    event(result='FAIL',error=repr(error));raise
finally:
    restored=True
    if saved is not None:
        try:
            subprocess.run(['/bin/bash',str(ROOT/'build_support/run_readyfs_c64u_restore_speed.sh'),str(OUT),os.environ.get('C64U_HOST','10.0.0.79')],check=True)
        except Exception as error:restored=False;event(restore='CPU settings',error=repr(error))
    if mounted:
        try:
            api('/drives/a:remove','PUT');time.sleep(1)
            final=js('/drives');save_json('restored-drives.json',final)
            now=next(d['a'] for d in final['drives'] if 'a' in d)
            assert all(now.get(k)==drive.get(k) for k in ('enabled','bus_id','type','image_file','image_path'))
        except Exception as error:restored=False;event(restore='Drive A',error=repr(error))
    (OUT/'status.txt').write_text('success\n' if rc==0 and restored else 'failed\n')
    event(complete=True,restored=restored,result='PASS' if rc==0 and restored else 'FAIL')
