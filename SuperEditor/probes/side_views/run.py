"""Isolated actual80/GEOS preview. No editor build or shared disk is changed."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,zipfile,struct
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan
from d81_image import D81Image
from png_pixels import read_png
OUT=ROOT/'build/side-views';OUT.mkdir(exist_ok=True)
SOURCES=['probes/side_views/main.s','probes/side_views/render.s','src/tui/charset.s','src/tui/petscii.s','src/tui/box40.s','src/tui/cell40.s']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def codes(text):return [ord(c)-96 if c.islower() else ord(c) for c in text]
def verify(e):
    result=json.loads((e/'result.json').read_text());checks=header_checks=glyph_checks=0
    header=[0x5D if c=='|' else codes(c)[0] for c in '|File |Edit |View |Navigate|Block |Help|'];assert len(header)==40
    rule=[0x6D if i==0 else 0x7D if i==39 else 0x71 if i in [6,12,18,27,34] else 0x40 for i in range(40)]
    font4=(ROOT/'assets/fonts/generated/narrow4.bin').read_bytes();bsw=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes()
    for name in ['80-column','geos','geos-help']:
        folder=e/'run/stages'/(name+'_ram');bitmap=(folder/'bitmap.bin').read_bytes();attributes=(folder/'attributes.bin').read_bytes();font=(folder/'font.bin').read_bytes();w,h,pixels=read_png(e/f'native-{name}.png');assert (w,h)==(384,272)
        raw=(e/f'native-{name}.png').read_bytes();cursor=8;palette=None
        while cursor<len(raw):
            n=struct.unpack_from('>I',raw,cursor)[0];kind=raw[cursor+4:cursor+8];data=raw[cursor+8:cursor+8+n];cursor+=n+12
            if kind==b'PLTE':palette=[tuple(data[i:i+3]) for i in range(0,len(data),3)]
        # VICE may emit trueRGB PNGs without PLTE. Recover a single RGB per
        # actual VIC color code, then require all64000 pixels agree with it;
        # logical header attributes and blue/white/yellow identities are also
        # checked independently below. This does not assume a particular gamma.
        rgb_by_color={}
        def bit(x,y):return bool(bitmap[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8)))
        for y in range(200):
            for x in range(320):
                color=attributes[(y//8)*40+x//8];code=(color>>4) if bit(x,y) else color&15;actual=pixels[(35+y)*w+32+x];expected=rgb_by_color.setdefault(code,actual)
                assert actual==expected,(name,x,y,'capturedVICcolor');checks+=1
        assert rgb_by_color[6]==pixels[0] and rgb_by_color[6][2]>max(rgb_by_color[6][:2])
        assert min(rgb_by_color[1])>220 and min(rgb_by_color[7][:2])>220 and rgb_by_color[7][2]<128
        assert len(set(rgb_by_color.values()))==len(rgb_by_color)
        for row,line in enumerate([header,rule]):
            for col,code in enumerate(line):
                for gy in range(8):
                    assert bitmap[row*320+col*8+gy]==font[code*8+gy],(name,row,col,gy,'frozenheaderglyph');header_checks+=8
                expected_fg=7 if row or col in [0,6,12,18,27,34,39] else 1
                assert attributes[row*40+col]==(expected_fg<<4)|6,(name,row,col,'headerpalette')
        if name=='geos-help':continue
        for text,x,y,flags in [('A PETSCII notebook',8,16,1),('Italic: gjpqy / Abc XYZ / native PETSCII.',8,42,2)]:
            for code in codes(text):
                advance=4 if name=='80-column' else widths[code]+(1 if flags==1 else 2)
                for gy in range(8 if name=='80-column' else 9):
                    word=font4[code*8+gy]<<8 if name=='80-column' else int.from_bytes(bsw[code*18+gy*2:code*18+gy*2+2],'big')
                    if name=='geos' and flags==1:word|=word>>1
                    if name=='geos' and flags==2:word>>=2 if gy<3 else 1 if gy<6 else 0
                    for gx in range(advance):assert bit(x+gx,y+gy)==bool(word&(0x8000>>gx)),(name,text,code,gx,gy,'actualfont');glyph_checks+=1
                x+=advance
        for col,code in enumerate(codes('1234567890'*8)):
            for gy in range(8):
                for gx in range(4):assert bit(col*4+gx,180+gy)==bool(font4[code*8+gy]&(128>>gx));glyph_checks+=1
    result.update(status='passed',captured_VIC_color_pixels_checked=checks,header_pixels_checked=header_checks,font_style_and_ruler_pixels_checked=glyph_checks,header='Exact titlecase physical40tile ABI, glyphs/attributes verified across all320pixels; Help and both final verticals included.',visual_review='Three native screenshots must be reviewed; no readability claim inferred solely from pixel oracle.')
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
def build():
    objects=[]
    for name in SOURCES:
        obj=OUT/(Path(name).stem+'.o');objects.append(str(obj));subprocess.run(['ca65','-I',str(ROOT/'src'),'-I',str(ROOT/'probes/side_views'),'-g','-o',str(obj),str(ROOT/name)],cwd=ROOT,check=True)
    subprocess.run(['ld65','-C',str(ROOT/'probes/side_views/probe.cfg'),'-o',str(OUT/'side-preview.prg'),'-m',str(OUT/'side-preview.map'),'-Ln',str(OUT/'side-preview.lbl'),*objects],cwd=ROOT,check=True)
    symbols={x[2].lstrip('.'):int(x[1],16) for line in (OUT/'side-preview.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}
    return symbols
def main():
    s=build();e=ROOT/'agentsworking/evidence/M6'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-side-previews');e.mkdir(parents=True)
    for p in OUT.glob('side-preview.*'):shutil.copyfile(p,e/p.name)
    disk=e/'working.d81';r=subprocess.run(['c1541','-format','side previews,sp','d81',str(disk),'-attach',str(disk),'-write',str(e/'side-preview.prg'),'sidepreview,p','-list'],capture_output=True,text=True);(e/'package.log').write_text(r.stdout+r.stderr);assert r.returncode==0
    assert D81Image(disk.read_bytes()).read(b'SIDEPREVIEW',kind=2).data==(e/'side-preview.prg').read_bytes()
    with zipfile.ZipFile(e/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in SOURCES+['src/probe_display.s','src/probe_panel.s','src/platform.inc','src/tui/theme.inc','probes/side_views/probe.cfg','probes/side_views/run.py','assets/fonts/generated/manifest.json']:
            z.write(ROOT/name,name)
    canary=bytes((i*73+29)&255 for i in range(1024));steps=[step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('seed_shim','memory.write',start=0xC600,bytes_hex=canary.hex(' ')),step('boot','input.sequence',keys=list(b'LOAD"SIDEPREVIEW",8,1\rRUN\r'),inter_key_delay_s=0.04)]
    def memory(name,symbol,value,width=1):
        data=value if isinstance(value,bytes) else value.to_bytes(width,'little');at=s[symbol] if isinstance(symbol,str) else symbol;v=step(name,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '));v['retry']=dict(max_attempts=1000,backoff_ms=50,jitter=False);steps.append(v)
    captures=[]
    def capture(name,sequence,mode):
        memory(name+'_ready','sv_ready',1);memory(name+'_sequence','sv_render_seq',sequence,2);memory(name+'_mode','se_mode',mode)
        steps.append(step(name+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{name}.png" 2'))
        steps.append(step(name+'_ram','dump.memory_ranges',ranges=[dict(label='bitmap',start=0x6000,end=0x7F3F),dict(label='attributes',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='source',start=s['sv_source'],end=s['sv_source_end']-1)]));captures.append(name)
    capture('80-column',1,2)
    steps.append(step('switch_GEOS','input.sequence',keys=[0x32],post_delay_s=0.12));capture('geos',2,3)
    steps.append(step('GEOS_help','input.sequence',keys=[0x8B],post_delay_s=0.12));capture('geos-help',3,3)
    memory('shim_intact',0xC600,canary)
    plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-side-previews-'+e.name,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6800,monitor_port_span=1,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
    r=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True);(e/'harness-build.log').write_text(r.stdout+r.stderr);assert r.returncode==0
    artifacts,manifest=run_plan(plan,e)
    sources=[(artifacts/'stages'/(n+'_ram')/'source.bin').read_bytes() for n in captures];assert len(set(sources))==1
    result=dict(status='captured-awaiting-visual-review',evidence=str(e),manifest=str(manifest),prg_sha256=sha(e/'side-preview.prg'),prg_bytes=(e/'side-preview.prg').stat().st_size,source_bytes=len(sources[0]),source_sha256=hashlib.sha256(sources[0]).hexdigest(),headless_requested=True,headless_mechanism='Existing .NET harness passes VICE -console +sound; actual process/resource evidence retained in manifest.',binary_port=6800,screenshots=[str(e/f'native-{n}.png') for n in captures],shim_bytes=1024,limits='Standalone scripted display probe; no editor integration, input editing, parser/fold/selection implementation or four-mode completion claim. Reuses existing M1 renderer and generated narrow4/English GEOS BSW9 fonts, with its prototype rank-only tile color conflict shortcut.')
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');result=verify(e);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
