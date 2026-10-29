"""PAL queued-input check through real IRQ and foreground; no PC/job seeds.

Explicit immutable fixture; private owned10100/text10200, actual D81/FileOpen.
KERNAL keyboard bytes are injected, not physical matrix events. One final
independent source/raster/native screenshot; stopwatch includes IRQ/VIC stalls.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
import test_display_timing_vice as timing
import test_supereditor_current_2mib_vice as owned
import test_plain_geos as plain
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan

ROOT=timing.ROOT
DATA=plain.SOURCE+timing.native.live.grid.native_text(
    'Long continuing words make several real viewports. '*32+'\rLast.\r')


class Plan(timing.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=10100
        p['global_defaults']['monitor_port_span']=1
        return p
    def boot(self):
        super().boot();p=self.out/'resources.mon'
        p.write_text(p.read_text().replace('"REUsize" "16384"','"REUsize" "2048"'))


def execute(base,out,inflight=False):
    assert not out.exists(),'fresh output required'
    e=timing.freeze(base,'pal');out.mkdir(parents=True)
    (out/'fixture.txt').write_text(str(e)+'\n')
    doc=e/'longdoc.bin';doc.write_bytes(DATA)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(doc),'longdoc,s'],capture_output=True,text=True)
    assert not p.returncode,p.stdout+p.stderr
    assert D81Image((e/'working.d81').read_bytes()).read(b'LONGDOC',kind=1).data==DATA
    (out/'verifier.py').write_bytes(Path(__file__).read_bytes())
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0)
    n.boot();n.open('longdoc',b'LONGDOC');n.typed('plain','syntax plain')
    n.typed('hires','mode hires');n.typed('bottom','bottom')
    s=n.s;captures=n.out/'captures';captures.mkdir(exist_ok=True)
    # Issue TOP through the real keyboard path, then stop at an actual pending
    # required paint. Neither parser/cache validity nor scheduler state is set.
    top=bytes([0x88])+timing.native.live.grid.native_text('top')+b'\r'
    pending=f'(@cpu:${s["se_e_ui"]:04x} == $00) && (@cpu:${s["se_input_head"]:04x} == @cpu:${s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00) && (@cpu:${s["se_e_job"]:04x} == $0b) && (@cpu:$9135 == $16) && ((@cpu:${s["se_bc_flags"]:04x} & $08) == $00)'
    pending_pc=queued_pc=s['se_idle']
    if inflight:
        labels={name:int(address,16)for address,name in re.findall(
            r'al ([0-9a-fA-F]+) \.(\w+)',(base/'build/overlays/geosrow.lbl').read_text())}
        pending_pc=labels['raster_continue']
        image=(base/'build/overlays/geosrow.seo').read_bytes()
        tag=(timing.editor_pair_index(image[5],image[6])
             if 'catalog_index' in s else
             json.loads((base/'freeze.json').read_text())['names'].index('geosrow'))+1
        pending+=f' && (@cpu:${s["se_overlay_active"]:04x} == ${tag:02x}) && (@cpu:${s["se_overlay_busy"]:04x} == $01) && (@cpu:$9040 > $14)'
        # Stop immediately after the real IRQ publishes the event. Reconstruct
        # the interrupted PC from the ROM dispatcher stack to prove mid-R21.
        prg=(e/'editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little')
        first,last=(s[k]-load+2 for k in ('se_input_irq','se_input_nmi'))
        needle=bytes((0x8d,s['se_input_head']&255,s['se_input_head']>>8))
        offsets=[i for i in range(first,last-2)if prg[i:i+3]==needle]
        assert len(offsets)==1
        queued_pc=load+offsets[0]-2+3
    queued=f'(@cpu:${s["se_input_head"]:04x} != @cpu:${s["se_input_tail"]:04x})'
    applied=f'(@cpu:${s["se_hot_pending"]:04x} == $01) && (@cpu:${s["se_hot_caret"]:04x} == $01) && (@cpu:${s["se_input_head"]:04x} == @cpu:${s["se_input_tail"]:04x})'
    log=n.out/'queued-stopwatch.log'
    n.raw('required_paint_pending_coherent',[
        'delete',f'> 0277 {top.hex(" ")}',f'> 00c6 {len(top):02x}',
        f'logname "{n.out / "pending-stop.log"}"','log on',
        f'break exec ${pending_pc:04x} if {pending}','x','delete',
        f'bsave "{captures}/pending.bin" 0 $0000 $cfff',
        f'bsave "{captures}/pending-colors.bin" 0 $d800 $dbe7','log off']
    )
    applied_capture=[
        'stopwatch','registers','delete',
        f'bsave "{captures}/applied.bin" 0 $0000 $cfff',
        f'bsave "{captures}/apply-colors.bin" 0 $d800 $dbe7','log off']
    hit=n.out/'IRQ_key_applied_timed-hit.mon'
    hit.write_text('\n'.join(applied_capture)+'\n')
    n.raw('IRQ_key_queued_applied_coherent',[
        f'> 0277 {timing.native.live.grid.native_text("Q").hex(" ")}','> 00c6 01',
        f'logname "{n.out / "queued-stop.log"}"','log on',
        f'break exec ${queued_pc:04x} if {queued}','x','delete',
        f'bsave "{captures}/queued.bin" 0 $0000 $cfff',
        f'bsave "{captures}/queued-colors.bin" 0 $d800 $dbe7','log off',
        f'logname "{log}"','log on','registers','stopwatch reset',
        f'break exec ${s["se_idle"]:04x} if {applied}',
        f'command 1 "playback \\"{hit}\\""','x',*applied_capture])
    wanted=timing.native.live.grid.native_text('Q')+DATA
    n.snapshot('queued-final',wanted,3)
    plan=n.plan();(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
    project=owned.private_project(n);vice_plan.PROJECT=project
    p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert not p.returncode
    planpath=n.out/'plan.yaml';planpath.write_text(json.dumps(plan,indent=2)+'\n')
    owned.free_ports();env=dict(os.environ,**{owned.ENV:str(n.out/'owned-process.json')})
    cmd=['dotnet','run','--no-build','--project',str(project),'--','run-plan','--plan',str(planpath),'--close-vice','--no-tui']
    print('NATIVE',e,flush=True)
    try:
        with(n.out/'stdout.txt').open('w')as so,(n.out/'stderr.txt').open('w')as se:
            p=subprocess.Popen(cmd,cwd=ROOT,stdout=so,stderr=se,env=env)
            try:assert p.wait(timeout=600)==0
            finally:
                if p.poll()is None:p.terminate();p.wait(timeout=10)
    finally:owned.close_owned(n.out,e)
    result=json.loads((n.out/'stdout.txt').read_text());assert result['Status']=='success',result
    shutil.copytree(result['RunDir'],n.out/'run',copy_function=os.link)
    images=timing.native.live.grid.reu_images(n.out/'run')
    ram=(captures/'queued-final-ram.bin').read_bytes();colors=(captures/'queued-final-colors.bin').read_bytes()
    f=Captured(s,ram,colors,e)
    assert timing.native.live.merged(f,images['queued-final'])==wanted
    assert ram[0xc600:0xca00]==n.canary
    fonts={name:(e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)}
    bits,attrs,_=plain.expected(f,wanted,fonts,0)
    assert ram[0x6000:0x7f40]==bits and ram[0x4000:0x43e8]==attrs
    w,h,pixels=read_png(n.out/'native-queued-final.png');assert(w,h)==(384,272)
    palette={}
    for y in range(200):
        for x in range(320):
            a=(y//8)*40+x//8;ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8))
            c=attrs[a]>>4 if ink else attrs[a]&15;pixel=pixels[(y+35)*w+x+32]
            assert pixel==palette.setdefault(c,pixel)
    for phase in ('pending','queued','applied'):
        b=(captures/(phase+'.bin')).read_bytes()
        assert b[s['se_e_ui']]==0
        assert b[198]==(1 if inflight and phase=='queued' else 0)
        if phase!='applied':
            assert b[s['se_e_job']]==11 and b[0x9135]==22
            assert int.from_bytes(b[s['se_hot_caret']:s['se_hot_caret']+3],'little')==0
        else:
            assert b[s['se_hot_pending']]==1 and b[s['se_hot_caret']]==1
        assert (b[s['se_input_head']]!=b[s['se_input_tail']])==(phase=='queued')
    values=re.findall(r'Stopwatch:\s*(\d+)',log.read_text(encoding='utf-8-sig'));assert len(values)==1
    interrupted=None
    if inflight:
        registers=re.findall(r'(?m)^\.;([0-9a-f]{4}) (?:[0-9a-f]{2} ){3}([0-9a-f]{2}) ',log.read_text(encoding='utf-8-sig'),re.I)
        assert len(registers)==2 and int(registers[0][0],16)==queued_pc,registers
        sp=int(registers[0][1],16);b=(captures/'queued.bin').read_bytes()
        interrupted=b[0x100+((sp+5)&255)]|(b[0x100+((sp+6)&255)]<<8)
        assert 0xa000<=interrupted<0xb000,('IRQ did not interrupt R21',hex(interrupted))
        assert b[s['se_overlay_active']]==tag and b[s['se_overlay_busy']]==1
    receipt=dict(status='PASS',fixture=str(base),native=str(e),queued_apply_PAL_cycles=int(values[0]),
        independent_pixels=64000,source_bytes=len(wanted),inflight=inflight,
        interrupted_PC=hex(interrupted)if interrupted is not None else None,
        timing_boundary='IRQ event publication inside R21 to applied'if inflight else'queued safe foreground boundary to applied',scope=__doc__)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--inflight',action='store_true')
    a=p.parse_args();execute(a.fixture.resolve(),a.out.resolve(),a.inflight)
