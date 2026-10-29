"""M1 display probe: real D81 boot, four modes, menus/atlases and pixel oracle."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from run_vice import step, PROJECT
from vice_plan import run_plan
from png_pixels import read_png

report = json.loads((ROOT/'build/display-probe-report.json').read_text())
symbols = report['symbols']
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
evidence = ROOT/'agentsworking/evidence/M1'/f'{stamp}-display'
evidence.mkdir(parents=True)
disk = evidence/'working.d81'
shutil.copyfile(ROOT/'build/supereditor.d81', disk)
shutil.copyfile(ROOT/'build/display-probe-report.json',evidence/'build-report.json')
shutil.copyfile(ROOT/'assets/fonts/generated/manifest.json',evidence/'font-manifest.json')
canary = bytes((i*73+29)&255 for i in range(1024))


def wait_render(ident, sequence):
    item = step(ident, 'assert.memory', start=symbols['p_render_seq'], end=symbols['p_render_seq']+1,
                equals_hex=sequence.to_bytes(2,'little').hex(' '))
    item['retry'] = dict(max_attempts=15, backoff_ms=30, jitter=False)
    return item


def capture(ident):
    return [step(ident, 'screen.capture', label=ident),
            step(ident+'_native','monitor.command',
                 command=f'raw: screenshot "{evidence}/native-{ident}.png" 2'),
            step(ident+'_ram', 'dump.memory_ranges', ranges=[
                dict(label='bitmap',start=0x6000,end=0x7F3F),
                dict(label='matrix',start=0x4000,end=0x43E7),
                dict(label='font40',start=0x4800,end=0x4BFF)])]


steps = [step('launch','vice.launch',kill_stale=False),
         step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),
         step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' ')),
         step('disk_boot','input.sequence',keys=list(b'LOAD"DISPLAYPROBE",8,1\rRUN\r'),
              inter_key_delay_s=0.04), wait_render('render_initial',1)]
seq = 1
for mode in range(4):
    if mode:
        steps.append(step(f'mode_{mode}','input.sequence',keys=[0x31+mode],inter_key_delay_s=0.04))
        seq += 1
        steps.append(wait_render(f'render_{mode}',seq))
    steps += capture(f'view-{mode}')
    for suffix, key in [('menu',0x85),('menu-close',0x85),('atlas',0x41),('atlas-close',0x41)]:
        steps.append(step(f'{suffix}_{mode}','input.sequence',keys=[key],inter_key_delay_s=0.04))
        seq += 1
        steps.append(wait_render(f'render_{suffix}_{mode}',seq))
        if not suffix.endswith('close'):
            steps += capture(f'{suffix}-{mode}')
steps.append(step('shim_intact','assert.memory',start=0xC600,end=0xC9FF,equals_hex=canary.hex(' ')))
plan = dict(version=1,kind='vice_task_plan',plan_id='supereditor-display-'+stamp,run_mode='gui_vice',
            global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,
                retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),
                timeouts=dict(launch_s=30,step_s=60,read_s=2),
                artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),
                vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,
                          true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
build = subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert build.returncode==0,build.stdout+build.stderr
artifacts,manifest = run_plan(plan,evidence)

# Independent bit-address oracle for the title. It checks glyph boundaries,
# inter-character advances and complete pixels (including zeros) in each view.
text = 'SuperEditor display probe'
screen_codes = [ord(c) if c.isupper() or not c.isalpha() else ord(c)-96 for c in text]
fonts = ROOT/'assets/fonts/generated'
pixel_checks = 0
for mode in range(4):
    directory = artifacts/f'stages/view-{mode}_ram'
    matrix = (directory/'matrix.bin').read_bytes()
    bitmap = (directory/'bitmap.bin').read_bytes()
    font40 = (directory/'font40.bin').read_bytes()
    glyphs = (fonts/('narrow5.bin' if mode==1 else 'narrow4.bin')).read_bytes()
    bsw = (fonts/'bsw9.bin').read_bytes()
    widths = (fonts/'bsw9-widths.bin').read_bytes()
    x, y = 8,16
    for code in screen_codes:
        advance = (8 if mode==0 else 5 if mode==1 else 4 if mode==2 else widths[code])
        height = 9 if mode==3 else 8
        for gy in range(height):
            word = int.from_bytes(bsw[code*18+gy*2:code*18+gy*2+2],'big') if mode==3 else None
            row = glyphs[code*8+gy] if mode in (1,2) else font40[code*8+gy] if mode==0 else 0
            for gx in range(advance):
                px,py=x+gx,y+gy
                expected = bool(word & (0x8000>>gx)) if mode==3 else bool(row & (0x80>>gx))
                if mode==0:
                    actual_code=matrix[(py//8)*40+px//8]
                    actual=bool(font40[(actual_code&127)*8+py%8] & (0x80>>(px%8)))
                else:
                    offset=(py//8)*320+(px//8)*8+py%8
                    actual=bool(bitmap[offset] & (0x80>>(px%8)))
                assert actual==expected,(mode,chr(code),px,py,expected,actual)
                pixel_checks+=1
        x+=advance
# Verify actual captured VIC pixels as well, so a stale or partly drawn frame
# cannot pass solely because its RAM dump contains the right glyphs.
captured_checks=0
for mode in range(4):
    for scenario,text,origin,flags in [('view','SuperEditor display probe',(8,16),0),
                                     ('menu','View / display probe',(32,40),0),
                                     ('view','Bold glyphs: Abc XYZ 0123',(8,80),1),
                                     ('view','Italic glyphs: gjpqy Abc',(8,96),2),
                                     ('view','X',((312 if mode==0 else 303 if mode==1 else 316),176),0)]:
        png=evidence/f'native-{scenario}-{mode}.png'
        width,height,pixels=read_png(png)
        assert (width,height)==(384,272)
        # Native PAL normal-border viewport, verified against both full screen
        # glyph rows and VICE's raster geometry. Keep full source screenshots.
        offset_x,offset_y=32,35
        background=pixels[0]
        codes=[ord(c) if c.isupper() or not c.isalpha() else ord(c)-96 for c in text]
        font40=(artifacts/f'stages/{scenario}-{mode}_ram/font40.bin').read_bytes()
        narrow=(fonts/('narrow5.bin' if mode==1 else 'narrow4.bin')).read_bytes()
        bsw=(fonts/'bsw9.bin').read_bytes()
        widths=(fonts/'bsw9-widths.bin').read_bytes()
        x,y=origin
        proportional=(mode==3 and scenario=='view' and origin[1]!=176)
        for code in codes:
            advance=widths[code]+(1 if flags&1 else 0)+(2 if flags&2 else 0) if proportional else 8 if mode==0 else 5 if mode==1 else 4
            for gy in range(9 if proportional else 8):
                word=int.from_bytes(bsw[code*18+gy*2:code*18+gy*2+2],'big') if proportional else 0
                if proportional and flags&1:
                    word|=word>>1
                if proportional and flags&2:
                    word>>=(2 if gy<3 else 1 if gy<6 else 0)
                row=font40[code*8+gy] if mode==0 else narrow[code*8+gy] if not proportional else 0
                for gx in range(advance):
                    expected=bool(word&(0x8000>>gx)) if proportional else bool(row&(0x80>>gx))
                    actual=pixels[(offset_y+y+gy)*width+offset_x+x+gx]!=background
                    assert actual==expected,(scenario,mode,code,x+gx,y+gy,'captured VIC frame')
                    captured_checks+=1
            x+=advance
result=dict(status='passed',evidence=str(evidence),harness_manifest=str(manifest),
            modes=4, screenshots=12, title_pixels_checked=pixel_checks,
            captured_vic_pixels_checked=captured_checks,
            native_screenshots=[str(p) for p in sorted(evidence.glob('native-*.png'))],
            native_viewport=dict(x=32,y=35,width=320,height=200),
            input='KERNAL PETSCII queue, not physical chord proof',shim_bytes_verified=1024)
(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
