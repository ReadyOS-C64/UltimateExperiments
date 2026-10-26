"""Cold-Plain PAL caret comparison on sealed canonical D81 builds.

Boot default must be Plain, set by validated host configuration before building.
Setup uses actual ROM File/Open and typed IRQ commands; timing retains the
explicit PC/SP/public-input stopwatch seam. No physical-key latency claim.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,socket,subprocess,tempfile,zipfile
import test_presentation_vice as presentation
from test_presentation_vice import timing,capacity,ROOT,Captured,vice_plan


class Plan(presentation.Plan):
    pass


def free_ports():
    for port in (8100,*range(8200,8240)):
        with socket.socket() as sock:
            # A closed owned VICE can leave TIME_WAIT sockets. Reuse does not
            # permit binding over a live listening monitor on these ports.
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',port))


def scenario(e):
    report=json.loads((e/'editor-report.json').read_text())
    assert report['symbols']['se_presentation_default']==0,'cold Plain host default required'
    n=Plan(e,report,1,0);n.cost_profile=True
    data=timing.native.live.grid.fixture();n.boot();n.memory('cold_plain_default','se_render_caps',0)
    n.open('open_diverse',b'DIVERSE')
    names=json.loads((e/'freeze.json').read_text())['catalog']
    # Assert the actual managed dependency state; never manufacture it.
    for name,slot in (('styler',1),('viewsource',0)):
        n.memory('unverified_'+name,n.s['image_slot']+names.index(name),slot)
    for preset,caps in (('plain',0),('full',3)):
        if caps:n.typed('enable_'+preset,'syntax '+preset)
        n.memory('caps_'+preset,'se_render_caps',caps)
        for mode,width in ((1,60),(2,80)):
            tag=preset+str(width);n.mode_to(mode);n.typed(tag+'_goto','goto 2')
            n.send(tag+'_interior',b'\x1d'*6)
            for action,key in (('right',0x1d),('left',0x9d),('down',0x11),('up',0x91)):
                n.measure(tag+'-'+action,data,mode,key=key,category='local-caret-'+action)
                n.measurements[-1].update(caps=caps,preset=preset,action=action)
    return n


def evaluate(n,require_fast=False):
    result=timing.evaluate(n)
    images=timing.native.live.grid.reu_images(n.out/'run');s=n.s
    invariant=None;outside=None;frames=[];fontsettings=(n.e/'editor-defaults.bin').read_bytes()
    for item in result['measurements']:
        ident=item['id'];cap=n.out/'captures';ram=(cap/(ident+'-ram.bin')).read_bytes()
        colors=(cap/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e)
        assert f.get('se_render_caps',1)==item['caps'] and f.get('se_sel_mark',1)==0
        assert f.read(s['se_editor_settings'],64)==fontsettings
        current=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w)for k,w in (
            ('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),
            ('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),
            ('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)))
        if invariant is None:invariant=current
        assert current==invariant,(ident,'source/history/clipboard state')
        assert not f.get('se_hot_pending',1) and not f.get('se_h_dirty',1)
        reu=images[ident];handle=f.get('se_gc_handle',1);bank=ram[s['se_reu_map']+handle]
        assert len(reu)==16*1024*1024 and handle and bank
        assert ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfe
        assert [i for i in range(256)if ram[s['se_reu_physical_owner']+i]==0xfe]==[bank]
        masked=bytearray(reu)
        # Full's real C14 publisher also builds its independently checked SP2
        # paragraph authority. Plain never executes or manufactures that work.
        if item['caps']:
            import binascii
            sc=reu[bank*65536+0x1600:bank*65536+0x1680]
            assert sc[:4]==b'SP\x02\xa5'
            assert binascii.crc_hqx(sc[:126],65535)==int.from_bytes(sc[126:128],'little')
            assert sc[4:37]==f.read(s['se_st_descriptor'],33)
            assert sc[37:39]==f.read(s['se_doc_epoch'],2)
            assert sc[39:41]==f.read(s['se_st_descriptor']+33,2)
            assert sc[41]==f.get('se_v_columns',1)
            assert sc[42:111]==f.read(s['se_v_rows'],66)+f.read(s['se_v_bottom'],3)
        for lo,hi in ((0,22*240),(0x1500,0x1680)):
            masked[bank*65536+lo:bank*65536+hi]=bytes(hi-lo)
        digest=hashlib.sha256(masked).hexdigest()
        if outside is None:outside=digest
        assert digest==outside,(ident,'whole16MiB outside exact grid packets/NC header/SP2')
        if item['caps']==0:
            names=result['identity']['catalog']
            assert ram[s['image_slot']+names.index('styler')]==1
            assert ram[s['image_slot']+names.index('viewsource')]==0
            assert not f.get('se_st_valid',1) and not f.get('se_st_request',1)
            assert not any(g['id']in(14,15,24,25,26,34,35,37,39)and g['slot']==1 for g in item['cost_profile']['groups']),(ident,'Plain semantic worker entered')
        if require_fast and item['action']in('right','left'):
            assert ram[0x89c0]==1,(ident,'actual C33 TRY rather than full render CAPTURE')
            assert not any(g['id']==16 and g['slot']==1 for g in item['cost_profile']['groups']),(ident,'C16 repaint')
        frames.append(dict(id=ident,cycles=item['emulated_cycles'],first_publish=item['first_publish_cycles'],loads=item['counter_deltas']['se_overlay_loads'],C33_operation=ram[0x89c0],caps=item['caps'],png_sha256=hashlib.sha256((n.out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
    assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
    free_ports()
    summary=dict(status='PASS',scope=__doc__,identity=result['identity'],frames=frames,native_pixels=result['native_pixels'],whole16MiB_outside_grid_exact=True,require_fast=require_fast,ports_released=True,visual_review='pending')
    (n.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
    return summary


def execute(source=None,existing=None,verify=False,require_fast=False):
    free_ports()
    if existing:e=existing.resolve()
    else:
        assert source,'immutable cold-Plain product fixture required'
        e=timing.freeze(source.resolve(),'pal');target=e.with_name(e.name.replace('display-timing-pal','grid-plain-caret-native'));e.rename(target);e=target
    if verify:
        # Reconstruct only the read-only evaluator context, never an execution
        # plan in the completed capture directory or another emulator run.
        with tempfile.TemporaryDirectory(prefix='supereditor-caret-evaluator-') as tmp:
            context=Path(tmp);shutil.copy2(e/'editor.prg',context/'editor.prg')
            n=Plan(context,json.loads((e/'editor-report.json').read_text()),1,0)
            n.e=e;n.out=e/'timing';n.cost_profile=True
            n.measurements=json.loads((n.out/'measurements.json').read_text())
            return evaluate(n,require_fast)
    n=scenario(e)
    p=n.plan();assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
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
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--existing',type=Path);p.add_argument('--verify',action='store_true');p.add_argument('--require-fast',action='store_true');a=p.parse_args()
    execute(a.source,a.existing,a.verify,a.require_fast)
