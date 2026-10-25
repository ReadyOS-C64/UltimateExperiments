"""M2 journalled groups/checkpoints/undo/redo/branch through D81 overlays."""
from datetime import datetime,timezone
import binascii
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan
from run_vice import native_screen_text
from png_pixels import read_png

report=json.loads((ROOT/'build/history-probe-report.json').read_text())
s=report['symbols']
assets={name:(ROOT/f'build/overlays/{name}.seo').read_bytes() for name in ['hedit','hplay']}
from overlays import HEADER
from cpu_history_probe import run_probe
predicted=run_probe(8)
assert (predicted['probe_cases'],predicted['dma_calls'],predicted['dma_bytes'])==(15,119,129618)
tail_text='Beyond 64 KiB: PETSCII source survives'
tail=bytes(ord(c)+128 if 'A'<=c<='Z' else ord(c)-32 if 'a'<=c<='z' else ord(c) for c in tail_text)
cross=bytearray(((i+128)&255)^0xA5 for i in range(1024))
cross[128:128+len(tail)]=tail
build=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert build.returncode==0,build.stdout+build.stderr
for banks in [256,8]:
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=ROOT/'agentsworking/evidence/M2'/f'{stamp}-history-{banks}'
    evidence.mkdir(parents=True)
    shutil.copyfile(ROOT/'build/history-probe-report.json',evidence/'build-report.json')
    shutil.copyfile(ROOT/'build/history-probe.prg',evidence/'history-probe.prg')
    for name,payload in assets.items():(evidence/f'{name}.seo').write_bytes(payload)
    disk=evidence/'working.d81'
    shutil.copyfile(ROOT/'build/supereditor.d81',disk)
    canary=bytes((i*73+29)&255 for i in range(1024))
    steps=[step('launch','vice.launch',kill_stale=False),
           step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),
           step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
    if banks==8:
        for name,command in [('off','resourceset "REU" "0"'),('size','resourceset "REUsize" "512"'),('on','resourceset "REU" "1"')]:
            steps.append(step(name,'monitor.command',command='raw: '+command))
    steps += [step('reu_before','dump.reu',mode='full',stage_tag='reu_before'),
              step('disk_boot','input.sequence',keys=list(b'LOAD"HISTORYPROBE",8,1\rRUN\r'),inter_key_delay_s=0.04)]
    ready=step('memory_passed','assert.memory',start=s['se_h_probe_result'],end=s['se_h_probe_cases'],equals_hex='01 0f')
    ready['retry']=dict(max_attempts=12,backoff_ms=40,jitter=False)
    expected_root=bytes([1,3])+(69635).to_bytes(3,'little')+b'\xff'*3
    steps += [ready,step('dma_count','assert.memory',start=s['se_reu_dma_calls'],end=s['se_reu_dma_bytes']+2,
                        equals_hex=(119).to_bytes(2,'little').hex(' ')+' '+(129618).to_bytes(3,'little').hex(' ')),
              step('published_length','assert.memory',start=s['se_doc_length'],end=s['se_doc_length']+2,equals_hex=(69635).to_bytes(3,'little').hex(' ')),
              step('published_generation','assert.memory',start=s['se_doc_generation'],end=s['se_doc_generation']+1,equals_hex='0b 00'),
              step('nodes','assert.memory',start=s['se_h_current'],end=s['se_h_counter']+3,equals_hex=(5).to_bytes(4,'little').hex(' ')+' '+(3).to_bytes(4,'little').hex(' ')+' '+(5).to_bytes(4,'little').hex(' ')),
              step('log_cursor','assert.memory',start=s['se_h_end'],end=s['se_h_cursor']+1,equals_hex='96 00 96 00'),
              step('history_idle','assert.memory',start=s['se_h_phase'],end=s['se_h_fault'],equals_hex='00 01 00'),
              step('dirty','assert.memory',start=s['se_h_dirty'],end=s['se_h_dirty'],equals_hex='01'),
              step('owned_states_clear','assert.memory',start=s['se_h_owned_lease'],end=s['se_h_owned_splice'],equals_hex='00 00 00'),
              step('idle','assert.memory',start=s['se_doc_busy'],end=s['se_snapshot_busy'],equals_hex='00 00 00'),
              step('active_root','assert.memory',start=s['se_doc_roots'],end=s['se_doc_roots']+7,equals_hex=expected_root.hex(' ')),
              step('actual_source','assert.memory',start=0x8000,end=0x8003,equals_hex='d8 d9 d1 00'),
              step('active_overlay','assert.memory',start=s['se_overlay_active'],end=s['se_overlay_busy']+1,equals_hex='00 02 00 00'),
              step('module_counts','assert.memory',start=s['se_overlay_loads'],end=s['se_overlay_calls']+1,equals_hex='06 00 34 00 3a 00'),
              step('channels_closed','assert.memory',start=0x98,end=0x98,equals_hex='00'),
              step('profile','assert.memory',start=s['se_reu_banks'],end=s['se_reu_banks']+1,equals_hex=banks.to_bytes(2,'little').hex(' ')),
              step('crossing_bytes','assert.memory',start=0x9000,end=0x93FF,equals_hex=cross.hex(' ')),
              step('shim_intact','assert.memory',start=0xC600,end=0xC9FF,equals_hex=canary.hex(' ')),
              step('native_capture','monitor.command',command=f'raw: screenshot "{evidence}/native-history.png" 2'),
              step('screen','dump.memory_ranges',ranges=[dict(label='screen',start=0x4000,end=0x43E7)]),
              step('reu_after','dump.reu',mode='full',stage_tag='reu_after')]
    plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-history-{banks}-{stamp}',run_mode='gui_vice',
        global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,
            retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),
            timeouts=dict(launch_s=30,step_s=60,read_s=2),
            artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),
            vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,
                      true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
    artifacts,manifest=run_plan(plan,evidence)
    images={}
    for index in (artifacts/'dumps').glob('*.json'):
        data=json.loads(index.read_text(encoding='utf-8-sig'))
        for item in data.get('chunks',[]):
            if item.get('source')=='vice_native_reu_image':
                key='before' if 'before' in index.name else 'after' if 'after' in index.name else None
                if key:
                    images[key]=(index.parent/Path(item['file']).name).read_bytes()
    assert set(images)=={'before','after'}
    before,after=images['before'],images['after']
    assert len(before)==len(after)==banks*65536
    # Independent binary records, including CRCs, source context and source
    # references. The original logical baseline is the imported69632 bytes.
    def packed(identity,offset,length):
        return bytes([identity,1,0])+offset.to_bytes(3,'little')+length.to_bytes(3,'little')
    def leaf_record(identity,offset,length):return packed(identity,offset,length)+b'\xff'*3+bytes(4)
    def history_record(before_node,after_node,position,source_offset,length):
        head=bytearray(64);head[:4]=b'SEH1';head[4]=1;head[5]=1;head[6:8]=(75).to_bytes(2,'little')
        head[8:12]=before_node.to_bytes(4,'little');head[12:16]=after_node.to_bytes(4,'little')
        head[16:21]=bytes([1,1,0,1,0]);head[21:26]=bytes([2,1,0,1,0]);head[26:29]=position.to_bytes(3,'little')
        head[32:35]=length.to_bytes(3,'little');head[37]=1
        head[39:42]=position.to_bytes(3,'little');head[42:45]=(position+length).to_bytes(3,'little');head[45]=1
        body=packed(2,source_offset,length)+(75).to_bytes(2,'little')
        head[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little')
        head[58:60]=binascii.crc_hqx(head[:58]+head[60:],0xFFFF).to_bytes(2,'little')
        return bytes(head)+body
    group=history_record(1,3,0,0,2);branch=history_record(3,5,2,3,1)
    # A canceled84-byte replacement left9 exact private bytes after later
    #75-byte stage replays. Check the bytes; do not mask/erase the whole bank.
    canceled_tail=bytes([0,3,0,0,1,0,0,84,0])
    first=bytes((i&255)^0xA5 for i in range(65536))
    second=bytearray((i&255)^0xA5 for i in range(4096));second[:len(tail)]=tail
    undo_leaf=leaf_record(2,0,2)+leaf_record(1,0,69632)+bytes(992)
    final_leaf=leaf_record(2,0,2)+leaf_record(2,3,1)+leaf_record(1,0,69632)+bytes(976)
    allowed=[(65536,assets['hedit'][HEADER:]),(65536+4096,assets['hplay'][HEADER:]),
             (2*65536,undo_leaf+final_leaf),(3*65536,first),(4*65536,group+branch),
             (4*65536+0xB000,branch+canceled_tail),(5*65536,bytes(second)),(6*65536,bytes([0xD8,0xD9,0xDA,0xD1]))]
    cursor=0
    for offset,payload in allowed:
        assert after[cursor:offset]==before[cursor:offset],f'unowned REU data changed before {offset:x}'
        actual_part=after[offset:offset+len(payload)]
        assert actual_part==payload,f'unexpected private content at {offset:x}: first difference '+str(next((i for i,(a,b) in enumerate(zip(actual_part,payload)) if a!=b),None))
        cursor=offset+len(payload)
    assert after[cursor:]==before[cursor:],'unowned REU tail changed'
    actual=bytearray()
    for index in range(3):
        at=2*65536+1024+index*16;identity=after[at];offset=int.from_bytes(after[at+3:at+6],'little');length=int.from_bytes(after[at+6:at+9],'little')
        sources=[3,5] if identity==1 else [6,7] if identity==2 else None
        assert sources is not None
        while length:
            count=min(length,65536-(offset&65535));physical=sources[offset>>16]*65536+(offset&65535)
            actual.extend(after[physical:physical+count]);offset+=count;length-=count
    expected=bytes([0xD8,0xD9,0xD1])+first+bytes(second)
    assert bytes(actual)==expected and len(actual)==69635
    decoded=native_screen_text((artifacts/'stages/screen/screen.bin').read_bytes())
    (evidence/'screen-decoded.txt').write_text(decoded+'\n')
    assert 'Journal model result:' in decoded and '01' in decoded
    assert 'Group XY / undo+redo / branch XYQ' in decoded and 'XYQ' in decoded
    width,height,pixels=read_png(evidence/'native-history.png')
    assert (width,height)==(384,272) and len(set(pixels))>1
    result=dict(status='passed',evidence=str(evidence),harness_manifest=str(manifest),
                prg_sha256=report['sha256'],resident_binding=report['resident_binding']['digest'],
                overlay_sha256={name:hashlib.sha256(image).hexdigest() for name,image in assets.items()},
                reu_banks=banks,probe_cases=15,dma_calls=119,dma_bytes=129618,
                document_bytes=69635,document_generation=11,journal_records=2,journal_bytes=150,
                current_node=5,saved_node=3,dirty=True,canceled_staging_tail_bytes=9,
                module_loads=6,module_calls=58,actual_rom_disk_transport=True,channels_closed=True,
                physical_source_banks=[3,5],physical_metadata_bank=2,physical_journal_bank=4,
                shim_bytes_verified=1024,untouched_reu_bytes_verified=len(after)-sum(len(payload) for _,payload in allowed),
                reconstructed_source_bytes=len(actual),append_bytes=4,screenshot=str(evidence/'native-history.png'))
    (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
