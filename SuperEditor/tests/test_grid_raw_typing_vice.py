"""Native cold-Plain short/wrapped typing and structural fallback qualification.

Actual sealed D81, ROM File/Open, IRQ setup commands and real scheduler. The
stopwatch uses the disclosed PC/SP/public-input seam, not physical key latency.
Source, all VIC pixels, attributes, catalog, stack guards and shim are checked by
the existing independent native evaluator. Input edits legitimately mutate REU;
this test does not claim the whole REU is read-only across an edit.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,shutil,subprocess,tempfile,zipfile
import test_grid_plain_caret_vice as caret
from test_grid_plain_caret_vice import timing,capacity,ROOT,Captured,vice_plan
from d81_image import D81Image


class Plan(caret.Plan):
    pass


def fixture(width):
    native=timing.native.live.grid.native_text
    return native('Plain editable words.\r'+'Alpha words '*18+'\r'+
                  'A'*(width-1)+'\rUntouched tail.\r')


def package(e):
    for width in (60,80):
        path=e/('raw'+str(width)+'.seq');path.write_bytes(fixture(width))
        p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',
                          str(path),'raw'+str(width)+',s'],capture_output=True)
        (e/('package-raw'+str(width)+'.log')).write_bytes(p.stdout+p.stderr)
        assert not p.returncode
        assert D81Image((e/'working.d81').read_bytes()).read(
            ('RAW'+str(width)).encode(),kind=1).data==fixture(width)
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')


def scenario(e):
    report=json.loads((e/'editor-report.json').read_text())
    assert report['symbols']['se_presentation_default']==0,'cold Plain build required'
    # The established stopwatch treats Return as command acceptance (UI2).
    # Here Return is a real body edit (UI0). Change that precondition alone;
    # retain the actual input instruction, scheduler and every capture guard.
    source=inspect.getsource(timing.Plan.measure)
    assert source.count('ui if key!=13 else 2')==1
    source=source.replace('ui if key!=13 else 2','ui')
    import textwrap
    (e/'body-return-measure.py').write_text(textwrap.dedent(source))
    ns=dict(vars(timing));exec(compile(textwrap.dedent(source),str(e/'body-return-measure.py'),'exec'),ns)
    Plan.measure=ns['measure']
    n=Plan(e,report,1,0);n.cost_profile=True;n.boot()
    n.memory('cold_plain','se_render_caps',0)
    for width,mode in ((60,1),(80,2)):
        data=fixture(width);short=0;wrapped=data.index(b'\r')+1
        edge=data.index(b'\r',wrapped)+1
        # Each insertion is immediately deleted. The editor coalesces this
        # actual no-op group back to its saved state; no dirty dialog exists.
        n.open('open_raw'+str(width),('RAW'+str(width)).encode())
        n.mode_to(mode)
        for tag,at,key,branch in (
                ('short-space',short+5,32,1),
                ('wrapped-quote',wrapped+width+5,34,2),
                ('wrapped-column0',wrapped+width,81,2),
                ('new-wrap',edge+5,81,None),
                ('insert-CR',short+5,13,None)):
            ident=str(width)+'-'+tag
            line=data[:at].count(b'\r')+1
            column=at-(data.rfind(b'\r',0,at)+1)
            n.typed(ident+'-goto','goto '+str(line))
            if column:n.send(ident+'-column',b'\x1d'*column)
            n.memory(ident+'-at','se_hot_caret',at,3)
            changed=data[:at]+bytes((key,))+data[at:]
            n.measure(ident+'-insert',changed,mode,key=key,category='raw-'+tag)
            n.measurements[-1].update(caps=0,branch=branch,expected_caret=at+1)
            n.measure(ident+'-back',data,mode,key=20,category='raw-delete-'+tag)
            n.measurements[-1].update(caps=0,branch=branch,expected_caret=at)
    return n


def evaluate(n,require_fast=False):
    result=timing.evaluate(n);frames=[];clipboard=None
    for item in result['measurements']:
        ident=item['id'];cap=n.out/'captures'
        ram=(cap/(ident+'-ram.bin')).read_bytes()
        f=Captured(n.s,ram,(cap/(ident+'-colors.bin')).read_bytes(),n.e)
        assert f.get('se_render_caps',1)==0 and f.get('se_st_valid',1)==0
        assert not f.get('se_st_request',1) and not f.get('se_sel_mark',1)
        assert f.get('se_hot_caret')==item['expected_caret']
        assert f.read(n.s['se_editor_settings'],64)==(n.e/'editor-defaults.bin').read_bytes()
        current=f.read(n.s['se_clip_token'],5)+f.read(n.s['se_clip_length'],3)
        if clipboard is None:clipboard=current
        assert current==clipboard,(ident,'unrelated clipboard')
        groups=item['cost_profile']['groups']
        assert not any(g['slot']==1 and g['id']in(14,15,24,25,26,34,35,37,39)for g in groups),(ident,'Plain parser work')
        if require_fast and item['branch'] is not None:
            assert ram[0x89ff]==item['branch'],(ident,'actual short/wrapped branch',ram[0x89ff])
            assert not any(g['slot']==1 and g['id']==16 for g in groups),(ident,'fallback C16 repaint')
        frames.append(dict(id=ident,cycles=item['emulated_cycles'],first_publish=item['first_publish_cycles'],loads=item['counter_deltas']['se_overlay_loads'],branch=ram[0x89ff],png_sha256=hashlib.sha256((n.out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
    assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
    caret.free_ports()
    result=dict(status='PASS',scope=__doc__,identity=result['identity'],frames=frames,
                native_pixels=result['native_pixels'],require_fast=require_fast,
                visual_review='pending',ports_released=True)
    (n.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True);return result


def execute(source=None,existing=None,verify=False,require_fast=False):
    caret.free_ports()
    if existing:e=existing.resolve()
    else:
        assert source,'immutable cold Plain product fixture required'
        e=timing.freeze(source.resolve(),'pal')
        target=e.with_name(e.name.replace('display-timing-pal','grid-raw-typing-native'))
        e.rename(target);e=target;package(e)
    if verify:
        with tempfile.TemporaryDirectory(prefix='supereditor-raw-typing-evaluator-')as tmp:
            context=Path(tmp);shutil.copy2(e/'editor.prg',context/'editor.prg')
            n=Plan(context,json.loads((e/'editor-report.json').read_text()),1,0)
            n.e=e;n.out=e/'timing';n.cost_profile=True
            n.measurements=json.loads((n.out/'measurements.json').read_text())
            return evaluate(n,require_fast)
    n=scenario(e);p=n.plan()
    assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
    (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('NATIVE',e,'steps',len(n.steps),'frames',len(n.measurements),flush=True)
    capacity.run_owned_plan(p,n.out,timeout=900)
    return evaluate(n,require_fast)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path)
    p.add_argument('--existing',type=Path);p.add_argument('--verify',action='store_true')
    p.add_argument('--require-fast',action='store_true');a=p.parse_args()
    execute(a.source,a.existing,a.verify,a.require_fast)
