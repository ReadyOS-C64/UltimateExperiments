#!/usr/bin/env python3
"""Terminal-owned runner for the native read-only diagnostic."""
from pathlib import Path
import json, os, subprocess, time, urllib.request, urllib.parse

root = Path(__file__).resolve().parent.parent
out = Path(os.environ['READYFS_SD2IEC_OUT']); out.mkdir(parents=True, exist_ok=True)
api = 'http://' + os.environ.get('C64U_HOST', '10.0.0.79') + '/v1'
def request(path, method='GET', data=None, content_type=None):
    headers = {'Content-Type': content_type} if content_type else {}
    with urllib.request.urlopen(urllib.request.Request(api + path, data=data, method=method, headers=headers), timeout=30) as response:
        return response.read()
def save(name, data):
    (out/name).write_text(json.dumps(data, indent=2)+'\n')

(out/'status.txt').write_text('running\n')
prg = out/'sd2iec-readonly.prg'
subprocess.run(['cl65','-t','c64','-Os','-o',str(prg),str(root/'build_support/sd2iec_readonly_probe.c')], check=True)
original = json.loads(request('/configs/U64%20Specific%20Settings'))['U64 Specific Settings']
restore = {key: original[key] for key in ('Turbo Control', 'CPU Speed')}
save('original-speed.json', restore)
save('original-drives.json', json.loads(request('/drives')))
try:
    request('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual','PUT')
    request('/configs/U64%20Specific%20Settings/CPU%20Speed?value=%201','PUT')
    request('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off','PUT')
    request('/machine:writemem?address=C1F0&data=00','PUT')
    request('/runners:run_prg','POST',prg.read_bytes(),'application/octet-stream')
    deadline = time.monotonic()+90
    while request('/machine:readmem?address=C1F0&length=1') != b'\xA5':
        if time.monotonic()>deadline: raise TimeoutError('Native diagnostic did not complete')
        time.sleep(1)
    data = request('/machine:readmem?address=C100&length=768')
    (out/'native-mailbox.bin').write_bytes(data)
    screen = request('/machine:readmem?address=0400&length=1000')
    (out/'screen_0400.bin').write_bytes(screen)
    subprocess.run(['python3',str(root/'build_support/decode_c64_screen.py'),str(out/'screen_0400.bin'),'--output',str(out/'screen.txt')],check=True)
    assert data[:4] == b'RFS\x01' and data[0xF0] == 0xA5
    result = {'listen_status':dict(zip(('8','9','10','11'),data[8:12])),
              'ui_open_result':data[0x10], 'ui_count':data[0x11],
              'ui_raw_hex':data[0x20:0x20+min(data[0x11],63)].hex(),
              'partition_current_raw_hex':data[0x80:0x9F].hex(),
              'partition_1_raw_hex':data[0xA0:0xBF].hex()}
    result['scan_8_to_15']=[{'device':data[i], 'count':data[i+1], 'status_hex':data[i+2:i+2+min(data[i+1],45)].hex()} for i in range(256,640,48)]
    save('results.json',result);print(json.dumps(result),flush=True)
except Exception as error:
    (out/'status.txt').write_text('failed\n');save('error.json',{'error':repr(error)});raise
finally:
    request('/configs','POST',json.dumps({'U64 Specific Settings':restore}).encode(),'application/json')
    after = json.loads(request('/configs/U64%20Specific%20Settings'))['U64 Specific Settings']
    assert all(after[key] == value for key,value in restore.items()),'CPU settings not restored'
    drives = json.loads(request('/drives'));save('restored-drives.json',drives)
    before = json.loads((out/'original-drives.json').read_text())
    for state in (before, drives):
        for entry in state['drives']:
            for drive in entry.values(): drive.pop('last_error', None)
    assert drives == before,'Drive configuration, media or cwd changed during read-only diagnostic'

(out/'status.txt').write_text('success\n')
