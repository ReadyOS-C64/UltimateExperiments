"""M2 selected-range immutable source capture for delta history."""
from datetime import datetime,timezone
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

report=json.loads((ROOT/'build/range-probe-report.json').read_text())
s=report['symbols']
tail_text='Beyond 64 KiB: PETSCII source survives'
tail=bytes(ord(c)+128 if 'A'<=c<='Z' else ord(c)-32 if 'a'<=c<='z' else ord(c) for c in tail_text)
cross=bytearray(((i+128)&255)^0xA5 for i in range(1024))
cross[128:128+len(tail)]=tail
build=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert build.returncode==0,build.stdout+build.stderr
for banks in [256,8]:
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=ROOT/'agentsworking/evidence/M2'/f'{stamp}-range-{banks}'
    evidence.mkdir(parents=True)
    shutil.copyfile(ROOT/'build/range-probe-report.json',evidence/'build-report.json')
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
              step('disk_boot','input.sequence',keys=list(b'LOAD"RANGEPROBE",8,1\rRUN\r'),inter_key_delay_s=0.04)]
    ready=step('memory_passed','assert.memory',start=s['se_range_result'],end=s['se_range_cases'],equals_hex='01 05')
    ready['retry']=dict(max_attempts=12,backoff_ms=40,jitter=False)
    packed_orig=bytes([1,1,0])+bytes(3)+(1).to_bytes(3,'little')
    packed_app=bytes([2,1,0])+bytes(3)+(1).to_bytes(3,'little')
    expected_roots=b''.join(bytes([slot,count])+count.to_bytes(3,'little')+b'\xff'*3 for slot,count in [(1,64),(0,64),(3,16)])
    steps += [ready,step('dma_count','assert.memory',start=s['se_reu_dma_calls'],end=s['se_reu_dma_bytes']+2,
                        equals_hex=(234).to_bytes(2,'little').hex(' ')+' '+(92394).to_bytes(3,'little').hex(' ')),
              step('published_length','assert.memory',start=s['se_doc_length'],end=s['se_doc_length']+2,equals_hex=(144).to_bytes(3,'little').hex(' ')),
              step('published_generation','assert.memory',start=s['se_doc_generation'],end=s['se_doc_generation']+1,equals_hex='06 00'),
              step('idle','assert.memory',start=s['se_doc_busy'],end=s['se_doc_busy'],equals_hex='00'),
              step('source_unlocked','assert.memory',start=s['se_doc_read_locks'],end=s['se_doc_read_locks'],equals_hex='00'),
              step('reused_roots','assert.memory',start=s['se_doc_reused_roots'],end=s['se_doc_reused_roots'],equals_hex='02'),
              step('active_roots','assert.memory',start=s['se_doc_roots'],end=s['se_doc_roots']+23,equals_hex=expected_roots.hex(' ')),
              step('captured_packet','assert.memory',start=0x8000,end=0x80B3,equals_hex=(packed_orig*10+packed_app+packed_orig*9).hex(' ')),
              step('captured_counts','assert.memory',start=s['se_range_pieces'],end=s['se_range_bytes']+1,equals_hex='14 00 b4 00'),
              step('capture_idle','assert.memory',start=s['se_snapshot_busy'],end=s['se_snapshot_busy'],equals_hex='00'),
              step('crossing_bytes','assert.memory',start=0x9000,end=0x93FF,equals_hex=cross.hex(' ')),
              step('shim_intact','assert.memory',start=0xC600,end=0xC9FF,equals_hex=canary.hex(' ')),
              step('native_capture','monitor.command',command=f'raw: screenshot "{evidence}/native-range.png" 2'),
              step('screen','dump.memory_ranges',ranges=[dict(label='screen',start=0x4000,end=0x43E7)]),
              step('reu_after','dump.reu',mode='full',stage_tag='reu_after')]
    plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-range-{banks}-{stamp}',run_mode='gui_vice',
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
    # Compare exact initialized and COW regions, not whole allocated banks.
    first=bytes((i&255)^0xA5 for i in range(65536))
    second=bytearray((i&255)^0xA5 for i in range(4096));second[:len(tail)]=tail
    packed_orig=bytes([1,1,0])+bytes(3)+(1).to_bytes(3,'little')
    packed_app=bytes([2,1,0])+bytes(3)+(1).to_bytes(3,'little')
    orig_record=packed_orig+b'\xff'*3+bytes(4)
    app_record=packed_app+b'\xff'*3+bytes(4)
    plain_leaf=orig_record*64
    changed_leaf=orig_record*6+app_record+orig_record*57
    tail_leaf=orig_record*16+bytes(768)
    metadata=changed_leaf+plain_leaf+plain_leaf+tail_leaf
    allowed=[(65536,packed_orig*144),(65536+1536,packed_app),(2*65536,metadata),
             (3*65536,first),(4*65536+0xFF4C,packed_orig*10+packed_app+packed_orig*9),(5*65536,bytes(second)),(6*65536,bytes([0xD8]))]
    cursor=0
    for offset,payload in allowed:
        assert after[cursor:offset]==before[cursor:offset],f'unowned REU data changed before {offset:x}'
        assert after[offset:offset+len(payload)]==payload,f'unexpected private content at {offset:x}'
        cursor=offset+len(payload)
    assert after[cursor:]==before[cursor:],'unowned REU tail changed'
    actual=bytearray()
    for slot,count in [(1,64),(0,64),(3,16)]:
        for index in range(count):
            at=2*65536+slot*1024+index*16
            identity=after[at];offset=int.from_bytes(after[at+3:at+6],'little');length=int.from_bytes(after[at+6:at+9],'little')
            physical=3 if identity==1 else 6 if identity==2 else None
            assert physical is not None and length==1 and offset==0
            actual.extend(after[physical*65536+offset:physical*65536+offset+length])
    expected=bytes([0xA5])*70+bytes([0xD8])+bytes([0xA5])*73
    assert bytes(actual)==expected
    decoded=native_screen_text((artifacts/'stages/screen/screen.bin').read_bytes())
    (evidence/'screen-decoded.txt').write_text(decoded+'\n')
    assert 'Range capture result:' in decoded and '01' in decoded
    assert '20 refs / 180 bytes / source unchanged' in decoded
    width,height,pixels=read_png(evidence/'native-range.png')
    assert (width,height)==(384,272) and len(set(pixels))>1
    result=dict(status='passed',evidence=str(evidence),harness_manifest=str(manifest),
                reu_banks=banks,probe_cases=5,prerequisite_cases=10,dma_calls=234,dma_bytes=92394,
                document_bytes=144,reference_pieces=144,captured_range_bytes=20,captured_references=20,packed_range_bytes=180,retained_roots_per_local_edit=2,bounded_read_piece_limit=8,
                physical_source_banks=[3,5],physical_metadata_bank=2,shim_bytes_verified=1024,
                untouched_reu_bytes_verified=len(after)-sum(len(payload) for _,payload in allowed),
                reconstructed_source_bytes=len(actual),append_bytes=1,screenshot=str(evidence/'native-range.png'))
    (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
