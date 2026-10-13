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
if os.environ.get('READYFS_PROBE_SOURCE') == 'capture':
    for name, address, length in [('zero-stack-vectors',0,1024),('overlay',0xB600,4096),('native-trace',0xC600,16),('screen',0x400,1000)]:
        (out/(name+'.bin')).write_bytes(request(f'/machine:readmem?address={address:X}&length={length}'))
    (out/'status.txt').write_text('success\n')
    raise SystemExit(0)
prg = out/'sd2iec-readonly.prg'
subprocess.run(['cl65','-t','c64','-Os','-o',str(prg),str(root/'build_support'/os.environ.get('READYFS_PROBE_SOURCE', 'sd2iec_readonly_probe.c'))], check=True)
original = json.loads(request('/configs/U64%20Specific%20Settings'))['U64 Specific Settings']
restore = {key: original[key] for key in ('Turbo Control', 'CPU Speed')}
save('original-speed.json', restore)
save('original-drives.json', json.loads(request('/drives')))
try:
    (out/'before-screen.bin').write_bytes(request('/machine:readmem?address=0400&length=1000'))
    request('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual','PUT')
    request('/configs/U64%20Specific%20Settings/CPU%20Speed?value=%201','PUT')
    request('/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off','PUT')
    request('/machine:writemem?address=C1F0&data=00','PUT')
    request('/runners:run_prg','POST',prg.read_bytes(),'application/octet-stream')
    deadline = time.monotonic()+90
    while request('/machine:readmem?address=C1F0&length=1') != b'\xA5':
        if time.monotonic()>deadline: raise TimeoutError('Native diagnostic did not complete')
        time.sleep(1)
    data = request('/machine:readmem?address=C100&length=1024')
    (out/'native-mailbox.bin').write_bytes(data)
    screen = request('/machine:readmem?address=0400&length=1000')
    (out/'screen_0400.bin').write_bytes(screen)
    subprocess.run(['python3',str(root/'build_support/decode_c64_screen.py'),str(out/'screen_0400.bin'),'--output',str(out/'screen.txt')],check=True)
    assert data[:3] == b'RFS' and data[0xF0] == 0xA5
    if data[3] == 5:
        assert data[4]==5 and data[5]==1 and data[6]==0 and data[9]==1, 'Native preparation failed'
        assert data[7] in (1,2) and 1<=data[8]<=254, 'Invalid pinned native partition'
        assert data[10]==1 and data[11] in (0,1) and data[12]==0, 'Qualified native root lookup failed'
        result = {'stage':data[4], 'prepare_ok':data[5], 'explicit_prepare_ok':data[9],
                  'native_mode':data[7], 'pinned_partition':data[8], 'lookup':data[11], 'dos':data[12],
                  'partition_reply_hex':data[512:543].hex(),
                  'directory_request_hex':data[384:504].split(b'\0')[0].hex(),
                  'status_reply_hex':data[256:336].split(b'\0')[0].hex()}
    elif data[3] == 4:
        after = int.from_bytes(data[9:11], 'little', signed=True)
        assert data[4]==6 and data[5]==0 and data[6]==6 and after>0, 'Live directory did not survive status read'
        assert data[32:35]==b'00,' and data[7]==0x40, 'Native status query failed'
        result = {'stage':data[4], 'open_result':data[5], 'before_count':data[6], 'status_st':data[7], 'status_hex':data[32:32+data[8]].hex(), 'after_count':after, 'after_st':data[11], 'raw_hex':data[256:256+data[6]+max(after,0)].hex()}
    elif data[3] == 3:
        assert data[4]==4 and data[5]==1 and data[6]==0, 'Production partition parser failed'
        result = {'stage':data[4], 'execute_ok':data[5], 'result_code':data[6]}
    elif data[3] == 2:
        count = int.from_bytes(data[8:10], 'little')
        assert data[4]==4 and data[5]==0 and data[7]==0x40 and count>=2, 'Partition byte stream incomplete'
        result = {'stage':data[4], 'open_result':data[5], 'last_count':data[6], 'status':data[7], 'count':count, 'raw_hex':data[256:256+count].hex()}
    else:
        result = {'probe_source':os.environ.get('READYFS_PROBE_SOURCE', 'sd2iec_readonly_probe.c'), 'listen_status':dict(zip(('8','9','10','11'),data[8:12])),
                  'ui_open_result':data[0x10], 'ui_count':data[0x11],
                  'ui_raw_hex':data[0x20:0x20+min(data[0x11],63)].hex(),
                  'partition_current_raw_hex':data[0x80:0x9F].hex(),
                  'partition_1_raw_hex':data[0xA0:0xBF].hex()}
        result['scan_8_to_15']=[{'device':data[i], 'count':data[i+1], 'status_hex':data[i+2:i+2+min(data[i+1],45)].hex()} for i in range(256,640,48)]
    save('results.json',result);print(json.dumps(result),flush=True)
except Exception as error:
    (out/'timeout-mailbox.bin').write_bytes(request('/machine:readmem?address=C100&length=1024'))
    (out/'timeout-screen.bin').write_bytes(request('/machine:readmem?address=0400&length=1000'))
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
