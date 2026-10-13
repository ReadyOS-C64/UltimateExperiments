#!/usr/bin/env python3
"""Serialize after baseline; expose external8, repair address, restore Ultimate8."""
from pathlib import Path
import json,os,subprocess,time,urllib.request
root=Path(__file__).resolve().parent.parent
out=Path(os.environ['READYFS_SD2IEC_OUT']);out.mkdir(parents=True,exist_ok=True)
api='http://'+os.environ.get('C64U_HOST','10.0.0.79')+'/v1'
def request(path,method='GET',data=None,ctype=None):
    with urllib.request.urlopen(urllib.request.Request(api+path,data=data,method=method,headers={'Content-Type':ctype} if ctype else {}),timeout=30) as response:return response.read()
def js(path):return json.loads(request(path))
def save(name,data):(out/name).write_text(json.dumps(data,indent=2)+'\n')
(out/'status.txt').write_text('waiting-for-baseline\n')
wait=Path(os.environ['READYFS_WAIT_FOR_BASELINE'])
scope=json.loads((wait/'owned-scope.json').read_text())
pid=int(scope['run_id'].rsplit('-',1)[1]);deadline=time.monotonic()+900
while (wait/'status.txt').read_text().strip()=='running':
    command=subprocess.check_output(['ps','-p',str(pid),'-o','command=']).decode()
    assert 'run_readyfs_c64u_demo_v3.py' in command,'Baseline process handle is no longer live'
    assert time.monotonic()<deadline,'Baseline observation timeout; do not overlap hardware jobs'
    time.sleep(5)
events=[json.loads(line) for line in (wait/'events.jsonl').read_text().splitlines()]
assert events[-1].get('complete') and events[-1].get('restored'),'Baseline did not restore hardware'
(out/'status.txt').write_text('running\n')
prg=out/'sd2iec-readdress.prg'
subprocess.run(['cl65','-t','c64','-Os','-o',str(prg),str(root/'build_support/sd2iec_readdress_probe.c')],check=True)
original=js('/drives');save('original-drives.json',original)
drive=next(d['a'] for d in original['drives'] if 'a' in d)
speed=js('/configs/U64%20Specific%20Settings')['U64 Specific Settings']
restore_speed={key:speed[key] for key in ('Turbo Control','CPU Speed')};save('original-speed.json',restore_speed)
stage=None
try:
    request('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual','PUT')
    request('/configs/U64%20Specific%20Settings/CPU%20Speed?value=%201','PUT')
    request('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off','PUT')
    request('/configs/Drive%20A%20Settings/Drive?value=Disabled','PUT')
    disabled=js('/drives');save('drive-a-disabled.json',disabled)
    assert not next(d['a'] for d in disabled['drives'] if 'a' in d)['enabled']
    request('/machine:writemem?address=C1F0&data=00','PUT')
    request('/runners:run_prg','POST',prg.read_bytes(),'application/octet-stream')
    deadline=time.monotonic()+120
    while request('/machine:readmem?address=C1F0&length=1')!=b'\xA5':
        assert time.monotonic()<deadline,'Address diagnostic did not complete'
        time.sleep(1)
    data=request('/machine:readmem?address=C100&length=256');(out/'mailbox.bin').write_bytes(data)
    assert data[:4]==b'RFA\x01';stage=data[4]
    save('result.json',{'stage':stage,'sd2iec_at_8':data[0x20:0x60].split(b'\0',1)[0].hex(),
                        'sd2iec_at_10':data[0x60:0xA0].split(b'\0',1)[0].hex(),
                        'save_status':data[0xA0:0xE0].split(b'\0',1)[0].hex()})
    (out/'screen_0400.bin').write_bytes(request('/machine:readmem?address=0400&length=1000'))
    subprocess.run(['python3',str(root/'build_support/decode_c64_screen.py'),str(out/'screen_0400.bin'),'--output',str(out/'screen.txt')],check=True)
finally:
    request('/configs/Drive%20A%20Settings/Drive?value='+('Enabled' if drive['enabled'] else 'Disabled'),'PUT')
    request('/configs','POST',json.dumps({'U64 Specific Settings':restore_speed}).encode(),'application/json')
    restored=js('/drives');save('restored-drives.json',restored)
    assert next(d['a'] for d in restored['drives'] if 'a' in d)==drive,'Drive A media/settings differ after restoration'
    settings=js('/configs/U64%20Specific%20Settings')['U64 Specific Settings']
    assert all(settings[key]==value for key,value in restore_speed.items()),'CPU settings differ after restoration'
(out/'status.txt').write_text('success\n' if stage==4 else 'not-identified\n' if stage==0 else 'partial\n')
print(json.dumps({'stage':stage,'restored':True}),flush=True)
