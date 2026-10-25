"""Stage-level native hot-flush attribution without changing product source."""
from datetime import datetime, timezone
import hashlib
import binascii
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from cpu_editor import NAMES
from flush_profile_cpu import WIDTHS
from overlays import HEADER
from png_pixels import read_png
from redraw_model import source40,verify_screen
from vice_config import PROJECT,step
from vice_plan import run_plan


def main():
    report=json.loads((ROOT/'build/editor-report.json').read_text());s=report['symbols']
    cpu=json.loads((ROOT/'build/flush-profile-cpu.json').read_text())
    assert cpu['prg_sha256']==report['sha256']
    for name in NAMES:
        assert hashlib.sha256((ROOT/f'build/overlays/{name}.seo').read_bytes()).hexdigest()==cpu['overlay_sha256'][name],('CPU/native asset identity mismatch',name)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    e=ROOT/'agentsworking/evidence/M3'/f'{stamp}-flush-profile';e.mkdir(parents=True)
    for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','flush-profile-cpu.json']:
        shutil.copyfile(ROOT/'build'/name,e/name)
    for name in NAMES:shutil.copyfile(ROOT/f'build/overlays/{name}.seo',e/(name+'.seo'))
    for name in ['tests/test_flush_profile_vice.py','tools/flush_profile_cpu.py','tools/redraw_model.py']:
        dest=e/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for folder in ['src','cfg']:
            for path in (ROOT/folder).rglob('*'):
                if path.is_file():archive.write(path,path.relative_to(ROOT))
        archive.write(ROOT/'Makefile','Makefile')
    disk=e/'working.d81';shutil.copyfile(ROOT/'build/supereditor.d81',disk)
    steps=[];cases=[];canary=bytes((i*73+29)&255 for i in range(1024))
    def raw(ident,commands):
        script=e/f'{ident}.mon';script.write_text('\n'.join(commands)+'\n')
        steps.append(step(ident,'monitor.command',command=f'raw: playback "{script}"'))
    def memory(ident,name,value,width=1):
        address=s[name] if isinstance(name,str) else name
        data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
        item=step(ident,'assert.memory',start=address,end=address+len(data)-1,equals_hex=data.hex(' '))
        item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
    def dump(ident,full=False):
        ranges=[dict(label='state',start=0xC000,end=0xC5FF),dict(label='metadata',start=0x9A00,end=0x9FFF),dict(label='view',start=s['se_editor_state_start'],end=s['se_editor_state_end']-1)]
        if full:ranges += [dict(label='hot',start=0x9200,end=0x99FF),dict(label='matrix',start=0x4000,end=0x43E7),dict(label='colors',start=0xD800,end=0xDBE7),dict(label='font',start=0x4800,end=0x4FFF)]
        steps.append(step(ident,'dump.memory_ranges',ranges=ranges))
    def measure(ident,function=None):
        dump(ident+'_before')
        code=bytes([0xEA]*8) if function is None else bytes([0x20])+s[function].to_bytes(2,'little')
        stop=0x0E00+len(code)
        # After the breakpoint resumes, hold at its NOP/JMP loop. IRQs run but
        # the editor cannot silently advance the next service between stages.
        code += bytes([0xEA,0x4C])+stop.to_bytes(2,'little')
        commands=[f'logname "{e}/{ident}.log"','log on',f'> 0e00 {code.hex(" ")}']
        if function=='se_editor_input':commands += [f'> {s["se_e_key"]:04x} 9d',f'> {s["se_e_mods"]:04x} 00']
        flags=0x24 if function is None else 0x20
        commands += [f'registers PC=$0e00, SP=$ff, FL=${flags:02x}','registers','stopwatch reset',f'until ${stop:04x}','stopwatch','registers','log off']
        raw(ident,commands);dump(ident+'_after')
        cases.append(dict(id=ident,function=function,stop_pc=stop,irq_enabled=function is not None))
        memory(ident+'_no_error','se_e_error',0)
    steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30)]
    raw('resources',['resourceset "MachineVideoStandard" "1"','resourceset "VICIIModel" "0"','resourceset "MachinePowerFrequency" "50"','resourceset "REU" "0"','resourceset "REUsize" "512"','resourceset "REU" "1"','resourceget "MachineVideoStandard"','resourceget "VICIIModel"','warp','resourceget "Drive8TrueEmulation"'])
    steps += [step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' ')),step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15)]
    memory('ready','se_status',1);memory('boot_drawn','se_e_draw_sequence',1,2)
    steps.append(step('typing','input.sequence',keys=[0xD8]*5,inter_key_delay_s=0.04,post_delay_s=0.08))
    memory('keys_consumed','se_key_sequence',5,2);memory('typed_pending','se_hot_pending',1)
    memory('initial_idle','se_e_job',0);memory('initial_rendered','se_e_redraw',bytes([0,0]))
    measure('calibration')
    for i,stage in enumerate(cpu['stages']):measure(f'phase_{i:02d}',stage['function'])
    memory('final_idle','se_e_job',0);memory('final_pending','se_hot_pending',0)
    memory('final_caret','se_hot_caret',4,3);memory('shim_intact',0xC600,canary);memory('channels_closed',0x98,0)
    for name in ['se_doc_read_locks','se_h_owned_lease','se_h_owned_capture','se_h_owned_splice','se_hot_owned','se_clip_busy','se_b_phase']:
        memory('released_'+name,name,0)
    dump('final',True)
    raw('screenshot',[f'screenshot "{e}/native-final.png" 2'])
    steps.append(step('final_reu','dump.reu',mode='full',stage_tag='final_reu'))
    plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-flush-{stamp}',run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
    (e/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    build=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert build.returncode==0,build.stdout+build.stderr
    print(f'Prepared {e}',flush=True)
    artifacts,manifest=run_plan(plan,e)
    def read_state(folder):
        def get(name,width):
            address=s[name]
            if 0xC000<=address<0xC600:label,base='state',0xC000
            elif 0x9A00<=address<0xA000:label,base='metadata',0x9A00
            elif s['se_editor_state_start']<=address<s['se_editor_state_end']:label,base='view',s['se_editor_state_start']
            else:raise AssertionError(('uncaptured address',name,hex(address)))
            data=(folder/(label+'.bin')).read_bytes()[address-base:address-base+width];assert len(data)==width
            return int.from_bytes(data,'little')
        out={name:get(name,width) for name,width in WIDTHS.items()}
        out['active_catalog_indices']=[get('se_overlay_active',2)&255,get('se_overlay_active',2)>>8]
        out['paint_path']=get('se_r_path',1);out['paint_rows']=get('se_r_rows',1);out['paint_cells']=get('se_r_cells',2)
        return out
    rows=[]
    for case in cases:
        text=(e/(case['id']+'.log')).read_text(encoding='utf-8-sig')
        values=re.findall(r'Stopwatch:\s*([0-9]+)',text);assert len(values)==1,text
        cycles=int(values[0]);assert re.search(r'\.C:'+f'{case["stop_pc"]:04x}',text,flags=re.I)
        before=read_state(artifacts/f'stages/{case["id"]}_before');after=read_state(artifacts/f'stages/{case["id"]}_after')
        if case['function'] is None:assert cycles==16
        item=dict(case,cycles=cycles,before=before,after=after,delta={n:after[n]-before[n] for n in ['se_overlay_calls','se_overlay_loads','se_overlay_hits','se_reu_dma_calls','se_reu_dma_bytes']})
        if case['function']:
            expected=cpu['stages'][len(rows)-1]
            for field in ['se_e_job','se_hot_phase','se_h_phase','se_doc_busy','se_hot_pending','se_hot_caret','se_doc_length','se_doc_generation']:
                assert before[field]==expected['before'][field] and after[field]==expected['after'][field],(case['id'],field,before[field],after[field],expected)
            item['cpu_attribution']=expected
        rows.append(item)
    final=artifacts/'stages/final';state=read_state(final)
    prg=(e/'editor.prg').read_bytes();sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
    source=bytes([0xD8])*5+sample
    meta=(final/'metadata.bin').read_bytes()
    def field(name,width=1):
        address=s[name];data=meta[address-0x9A00:address-0x9A00+width];assert len(data)==width;return int.from_bytes(data,'little')
    hot=(final/'hot.bin').read_bytes();assert hot[:field('se_hot_left',2)]+hot[field('se_hot_right',2):]==source
    view=(final/'view.bin').read_bytes();top=int.from_bytes(view[s['se_v_top']-s['se_editor_state_start']:s['se_v_top']-s['se_editor_state_start']+3],'little')
    matrix=(final/'matrix.bin').read_bytes();colors=(final/'colors.bin').read_bytes()
    verify_screen(matrix,colors,source40(source,top,4,dirty=True),tag='native profiled flush final')
    image=None
    for index in (artifacts/'dumps').glob('*.json'):
        for chunk in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks',[]):
            if chunk.get('source')=='vice_native_reu_image':image=(index.parent/Path(chunk['file']).name).read_bytes()
    assert image is not None and len(image)==8*65536
    rebuilt=bytearray();root=s['se_doc_roots']-0x9A00
    for i in range(field('se_doc_root_count')):
        record=meta[root+i*8:root+(i+1)*8];leaf=2*65536+record[0]*1024
        for j in range(record[1]):
            piece=image[leaf+j*16:leaf+(j+1)*16];assert piece[0] in [1,2]
            offset=int.from_bytes(piece[3:6],'little');length=int.from_bytes(piece[6:9],'little');bank=3 if piece[0]==1 else 4
            rebuilt += image[bank*65536+offset:bank*65536+offset+length]
    assert rebuilt==source
    body=bytes([2,1,0])+bytes(3)+(5).to_bytes(3,'little')+(75).to_bytes(2,'little')
    header=bytearray(64);header[:6]=b'SEH1\x01\x01';header[6:8]=(75).to_bytes(2,'little')
    header[8:12]=(1).to_bytes(4,'little');header[12:16]=(2).to_bytes(4,'little')
    header[16:21]=bytes([1,1,0,1,0]);header[21:26]=bytes([2,1,0,1,0])
    header[32:35]=(5).to_bytes(3,'little');header[37:39]=(1).to_bytes(2,'little')
    header[42:45]=(5).to_bytes(3,'little');header[45]=1
    header[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little')
    header[58:60]=binascii.crc_hqx(header[:58]+header[60:],0xFFFF).to_bytes(2,'little')
    journal=bytes(header)+body
    assert image[5*65536:5*65536+75]==journal,'exact published journal/header/body CRC'
    assert image[5*65536+0xB000:5*65536+0xB000+75]==journal,'exact staged journal'
    assert field('se_h_end',2)==75 and field('se_h_current',4)==2 and field('se_h_saved',4)==1
    for i,name in enumerate(NAMES):
        payload=(e/(name+'.seo')).read_bytes()[HEADER:]
        assert image[65536+i*4096:65536+i*4096+len(payload)]==payload
    w,h,pixels=read_png(e/'native-final.png');assert (w,h)==(384,272)
    font=(final/'font.bin').read_bytes();background=pixels[0]
    for row in range(25):
        for col in range(40):
            for y in range(8):
                pattern=font[matrix[row*40+col]*8+y]
                for x in range(8):assert (pixels[(35+row*8+y)*w+32+col*8+x]!=background)==bool(pattern&(128>>x))
    result=dict(status='passed',evidence=str(e),harness_manifest=str(manifest),prg_sha256=report['sha256'],resident_binding=report['resident_binding']['digest'],overlay_sha256=cpu['overlay_sha256'],measurements=rows,total_segmented_cycles=sum(x['cycles'] for x in rows if x['function']),cpu_total_instructions=cpu['total_instructions'],crc_byte_calls=cpu['crc_byte_calls'],source_bytes_reconstructed=len(source),source_sha256=hashlib.sha256(source).hexdigest(),exact_journal_and_stage_bytes=75,journal_header_and_body_crc_verified=True,full_screen_cells_verified=1000,native_vic_pixels_verified=64000,shim_bytes_verified=1024,configured=dict(video='PAL6569',reu_kib=512,warp=True,drive_traps=True,true_drive=False),limitations='Segmented IRQ-enabled service-entry costs; hold loop prevents automatic progress between stages and changes IRQ/raster phase. Sum is not continuous key latency. ProbeJSR/RTS12cycles included perstage. CPUcounts are supplemental and exclude native stalls/IRQs.')
    baseline_path=ROOT/'agentsworking/evidence/M3/20261024T191141186811Z-flush-profile/result.json'
    if baseline_path.exists():
        baseline=json.loads(baseline_path.read_text());cycles=result['total_segmented_cycles']
        result['baseline_comparison']=dict(evidence=str(baseline_path),baseline_segmented_cycles=baseline['total_segmented_cycles'],optimized_segmented_cycles=cycles,saved_segmented_cycles=baseline['total_segmented_cycles']-cycles,percent_reduction=(1-cycles/baseline['total_segmented_cycles'])*100,baseline_cpu_instructions=baseline['cpu_total_instructions'],optimized_cpu_instructions=cpu['total_instructions'],baseline_cold_loads=sum(x['delta']['se_overlay_loads'] for x in baseline['measurements']),optimized_cold_loads=sum(x['delta']['se_overlay_loads'] for x in rows),baseline_admission_crc_bytes=baseline['crc_byte_calls']['overlay_admission'],optimized_admission_crc_bytes=cpu['crc_byte_calls']['overlay_admission'])
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='measurements'},indent=2))
    print('STAGES',[(x['id'],x['cycles'],x['delta']) for x in rows],flush=True)


if __name__=='__main__':main()
