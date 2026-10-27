"""Actual standalone reduced-REU acceptance; own8100/text8200.

Frozen907b product only. Resource requests, actual provider capacity and every
REU image length are independently checked. Positive profiles use public edits,
history, hidden canonical copy, folds, preview/settings and real save/reopen.
512KiB/missingREU are expected startup diagnostics, never support claims.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,subprocess,zipfile
import test_geos_fold_native as folds
from test_geos_preview_vice import settings_ui
from test_fold_retention_vice import Captured
from test_geos_navigation_vice import object_bytes
from png_pixels import read_png
from d81_image import D81Image
from vice_config import step
import vice_plan
from cache_job_build import editor_pair_index

ROOT=folds.ROOT;live=folds.live
SOURCE=ROOT/'build/geos-semantic-editor/20261025T060655745558Z/fixture'
PRG='8fd8a96c27052ee14ce59070981e863b53b3afc7cb4a4e3ced4728975747f232'
DISK='907b3aa134cf296f05dd7c23971358d5174de00598cdc06d8edc25c5700f8847'
CURRENT_KB=1024


class Plan(folds.Plan):
    def __init__(self,*args):super().__init__(*args);self.capacity_cases=[];self.capture_error=0
    def idle(self,ident,ui=0,error=0,owner=None):
        return super().idle(ident,ui,self.capture_error or error,owner)
    def boot(self):
        super().boot();p=self.out/'resources.mon'
        text=p.read_text().replace('"REUsize" "16384"',f'"REUsize" "{CURRENT_KB or 512}"')
        text+='resourceget "REUsize"\nresourceget "REU"\n'
        if not CURRENT_KB:text=text.replace('resourceset "REU" "1"','resourceset "REU" "0"')
        p.write_text(text)
        if CURRENT_KB in (0,512):
            index=next(i for i,v in enumerate(self.steps) if v['id']=='boot')
            self.steps=self.steps[:index+1]
            self.memory('expected_cold_failure','se_status',3)
            self.memory('expected_cold_error','se_e_error',0x78 if not CURRENT_KB else 1)
    def extra(self,ident,data,caret,*,pending=0,ui=0,kind='literal',settings=None,current=b'DIVERSE',clip=None,mode=None,error=0,node=None):
        if mode is None:mode=0 if ident in ('pending-Q','undo-Q','redo-Q','undo-Q-final') else 3
        self.memory(ident+'_caret','se_hot_caret',caret,3);self.memory(ident+'_pending','se_hot_pending',pending)
        self.capture_error=error
        self.capture(ident,data,mode,ui,kind=kind,caret=caret,mark=False,anchor=None,folds=[],
            clipboard=clip.hex() if clip is not None else None,capacity_case=True,pending=pending,
            settings=settings.hex() if settings else None,current=current.decode(),error=error,node=node)
        self.capture_error=0
        self.capacity_cases.append(self.cases.pop())
    def open(self,ident,name,*args,**kwargs):
        super().open(ident,name,*args,**kwargs)
        if ident!='open_diverse':return
        data=live.grid.fixture();q=live.grid.native_text('Q')
        self.send('pending_insert_Q',q);self.extra('pending-Q',q+data,1,pending=1)
        self.send('undo_actual_Q',b'\x1A');self.extra('undo-Q',data,0)
        self.send('redo_actual_Q',b'\x19');self.extra('redo-Q',q+data,1)
        self.send('undo_actual_Q_final',b'\x1A');self.extra('undo-Q-final',data,0)


def freeze(kb,source=SOURCE):
    e=folds.freeze(source,PRG if source==SOURCE else None,DISK if source==SOURCE else None)
    target=e.with_name(e.name.replace('-geos-fold-native',f'-reu-{kb or "missing"}-native'));shutil.move(e,target)
    return target


def scenario(e,kb):
    global CURRENT_KB
    CURRENT_KB=kb
    if kb in (0,512):
        n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');n.boot()
        captures=n.out/'captures';captures.mkdir(exist_ok=True)
        n.raw('failure_capture',[f'until ${n.s["se_idle"]:04x}','step $10000',
            f'screenshot "{n.out}/native-cold-failure.png" 2',
            f'bsave "{captures}/cold-failure-ram.bin" 0 $0000 $cfff',
            f'bsave "{captures}/cold-failure-colors.bin" 0 $d800 $dbe7'])
        if kb:n.steps.append(step('cold-failure_reu','dump.reu',mode='full',stage_tag='cold-failure_reu'))
        return n
    old=folds.Plan;folds.Plan=Plan
    try:n=folds.scenario(e)
    finally:folds.Plan=old
    # The original18 immutable-source fold cases remain an independent group.
    for c in n.cases:c.update(capacity_case=False,pending=0,settings=None,current='DIVERSE')
    data=live.grid.fixture();clip=data[data.index(live.grid.native_text(':::basic')):data.index(live.grid.native_text(':::asm'))-1]
    assert len(clip)==76
    defaults=(e/'editor-defaults.bin').read_bytes();changed=bytearray(defaults);changed[8+4]=(changed[8+4]+1)&15;changed[8+6]^=1
    n.typed('settings_public','settings',ui=1);n.send('settings_B_C',b'BC',ui=1)
    n.extra('settings-session',data,227,ui=1,kind='settings',settings=bytes(changed),clip=clip)
    n.send('settings_close',b'\r');n.typed('custom_preview','preview',ui=4)
    n.extra('settings-preview',data,227,ui=4,kind='preview',settings=bytes(changed),clip=clip)
    n.send('preview_back_to_edit',b'\r');n.typed('settings_reset_open','settings',ui=1);n.send('settings_reset_key',b'R',ui=1);n.send('settings_reset_close',b'\r')
    n.save_as('save_reduced_reu',b'CAPOUT');n.extra('saved-reduced',data,227,current=b'CAPOUT',clip=clip)
    n.open('reopen_saved',b'CAPOUT');n.extra('reopened-reduced',data,0,current=b'CAPOUT',clip=clip)
    n.cases+=n.capacity_cases
    return n


def legacy_boundary_scenario(e,kb):
    global CURRENT_KB
    CURRENT_KB=kb
    line=live.grid.native_text('Capacity 0123456789 abcdefghijk\r')
    data=(line*((65535//len(line))+1))[:65535]+b'\r'
    assert len(data)==65536
    (e/'source64.bin').write_bytes(data)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'source64.bin'),'large64,s'],capture_output=True,text=True)
    (e/'boundary-package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');n.boot();n.open('open_large64',b'LARGE64')
    n.extra('large64-opened',data,0,current=b'LARGE64',mode=0)
    n.typed('large64_bottom','bottom');n.send('large64_insert_Q',live.grid.native_text('Q'))
    n.extra('large64-pending',data+live.grid.native_text('Q'),65537,pending=1,current=b'LARGE64',mode=0)
    n.send('large64_actual_undo',b'\x1A');n.extra('large64-undo',data,65536,current=b'LARGE64',mode=0)
    n.save_as('save_large64',b'CAP64');n.extra('large64-saved',data,65536,current=b'CAP64',mode=0)
    n.open('reopen_large64',b'CAP64');n.extra('large64-reopened',data,0,current=b'CAP64',mode=0)
    n.cases=n.capacity_cases
    return n


def boundary_scenario(e,kb):
    """Corrected quota acceptance: refusal before mutation, usable history/save.

    Historical907b late-flush failure remains immutable in063145 evidence;
    this new expected behavior must pass only a parent-released fixed build.
    """
    global CURRENT_KB
    CURRENT_KB=kb
    line=live.grid.native_text('Capacity 0123456789 abcdefghijk\r')
    data=(line*((65535//len(line))+1))[:65535]+b'\r'
    (e/'source64.bin').write_bytes(data)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'source64.bin'),'large64,s'],capture_output=True,text=True)
    (e/'boundary-package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');n.boot();n.open('open_large64',b'LARGE64')
    def snap(ident,source,caret,**opts):n.extra(ident,source,caret,current=b'LARGE64',mode=0,**opts)
    q=live.grid.native_text('Q');replaced=data[:-1]+q
    snap('large64-opened',data,0,node=1)
    n.typed('large64_bottom','bottom');n.send('large64_refuse_Q',q,error=0x32)
    snap('large64-refused',data,65536,error=0x32,node=1)
    n.send('large64_backspace',b'\x14');snap('large64-pending-delete',data[:-1],65535,pending=1,node=1)
    n.send('large64_replace_Q',q);snap('large64-pending-replacement',replaced,65536,pending=1,node=1)
    n.send('large64_refuse_second_Q',q,error=0x32)
    snap('large64-refused-pending',replaced,65536,pending=1,error=0x32,node=1)
    n.send('large64_actual_undo',b'\x1A');snap('large64-undo',data,65536,node=1)
    n.send('large64_actual_redo',b'\x19');snap('large64-redo',replaced,65536,node=2)
    n.send('large64_actual_undo_final',b'\x1A');snap('large64-undo-final',data,65536,node=1)
    n.save_as('save_large64',b'CAP64');n.extra('large64-saved',data,65536,current=b'CAP64',mode=0,node=1)
    n.open('reopen_large64',b'CAP64');n.extra('large64-reopened',data,0,current=b'CAP64',mode=0,node=1)
    n.cases=n.capacity_cases;return n


def raster(e,c,f,fonts,catalog):
    data=bytes.fromhex(c['source']);tree=[folds.decoded_fold(bytes.fromhex(x)) for x in c['folds']]
    settings=bytes.fromhex(c['settings']) if c.get('settings') else (e/'editor-defaults.bin').read_bytes()
    if c['mode']==0:
        (matrix,colors),_,_,_=live.geos.grid.expected(f,data)
        rom=(e/'chargen.bin').read_bytes()[0x800:0x1000];assert f.read(0x4800,2048)==rom
        bits=bytearray(8000);attrs=bytearray(1000)
        for r in range(25):
            for x in range(40):
                at=r*40+x;bits[r*320+x*8:r*320+x*8+8]=rom[matrix[at]*8:matrix[at]*8+8];attrs[at]=colors[at]*16+6
        assert f.read(0x4000,1000)==matrix and bytes(v&15 for v in f.colors)==colors
        return bytes(bits),bytes(attrs)
    if c['kind']=='preview':
        result=folds.preview(data,settings,tree,catalog=catalog,top=f.get('se_v_top'));bits,attrs=result.bitmap,result.attrs
        assert f.get('se_v_bottom')==result.bottom
    elif c['mode']==3:
        bits,attrs,_,_=folds.raster(data,fonts,tree,top=f.get('se_v_top'),caret=c['caret'],anchor=c['anchor'] if c['mark'] else None,
            nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
    else:(bits,attrs),_,_,_,_=folds.grid_fold.expected(f,data,tree,f.get('se_v_top'))
    matrix,colors,popup=live.geos.grid.logical_ui(f,data)
    bits,attrs=live.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
    if c['kind']=='settings':
        ui=settings_ui(f,data,settings,0,named_fonts=True);bits,attrs=bytearray(bits),bytearray(attrs)
        live.grid.paint_native(bits,attrs,ui,fonts['native8.bin'])
    return bytes(bits),bytes(attrs)


def evaluate(e,kb):
    out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run')
    if kb in (0,512):
        ram=(out/'captures/cold-failure-ram.bin').read_bytes();colors=(out/'captures/cold-failure-colors.bin').read_bytes();f=Captured(s,ram,colors,e)
        assert f.get('se_status',1)==3 and f.get('se_e_error',1)==(1 if kb else 0x78)
        assert f.get('se_reu_banks',2)==(8 if kb else 0)
        assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
        matrix=bytearray([32])*1000
        for row,text in [(10,'Cannot start editor.'),(12,'Check disk assets and REU capacity.')]:
            expected=bytes(map(live.grid.screen_code,live.grid.native_text(text)));assert f.read(0x4000+row*40+2,len(expected))==expected
            matrix[row*40+2:row*40+2+len(expected)]=expected
        assert f.read(0x4000,1000)==matrix and bytes(v&15 for v in colors)==bytes([1])*1000
        rom=(e/'chargen.bin').read_bytes()[0x800:0x1000];assert f.read(0x4800,2048)==rom
        w,h,pixels=read_png(out/'native-cold-failure.png');assert (w,h)==(384,272);palette={}
        for y in range(200):
            for x in range(320):
                glyph=matrix[(y//8)*40+x//8];ink=rom[glyph*8+y%8]&(128>>(x%8));color=1 if ink else 6;pixel=pixels[(35+y)*w+32+x]
                assert pixel==palette.setdefault(color,pixel),(kb,'failure native VIC pixel',x,y)
        assert len(set(palette.values()))==2
        if kb:
            image=images['cold-failure'];assert len(image)==kb*1024
            assert not any(v==0xFD for v in f.read(s['se_reu_logical_owner'],256)),'font firstallocation rollback'
        result=dict(status='expected_failure',capacity_kb=kb,reported_banks=f.get('se_reu_banks',2),error=f.get('se_e_error',1),shim_preserved=True,font_partial_allocation_rolled_back=bool(kb),pixels=64000,attributes=1000,scope='Actual cold failure diagnostic; no supported editor session.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result
    fonts={n:(e/n).read_bytes() for n in live.geos.GEOS_FONTS+('native8.bin',)}
    catalog=folds.previous.pack_catalog((e/'font-pack.bin').read_bytes(),fonts['native8.bin']);pack=(e/'font-pack.bin').read_bytes()
    palette={};observed=[];canonical=None;groups={};intervals=0;max_banks=max_objects=0;journal=None
    # Include only banks authenticated as derived during this readonly group.
    # A first fold can allocate a previously free bank with old retired bytes;
    # use that same precise union on both sides of the comparison.
    derived=set()
    for c in cases:
        if c['capacity_case']:continue
        ram=(out/'captures'/(c['id']+'-ram.bin')).read_bytes()
        derived.update(i for i in range(kb//64) if ram[s['se_reu_physical_owner']+i] in (0xFE,0x46))
    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident]
        assert len(reu)==kb*1024,(ident,'actual native REU image size',len(reu),kb)
        f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
        assert f.get('se_reu_banks',2)==kb//64
        if (e/'source64.bin').exists():
            assert f.get('se_doc_length')==65536
            for token_name in ('se_doc_original','se_doc_append'):
                assert ram[s['object_banks']+f.get(token_name,1)]==1,(ident,'declared one-bank quota')
        assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret']
        assert bool(f.get('se_hot_pending',1))==bool(c.get('pending')) and bool(f.get('se_sel_mark',1))==c['mark']
        if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
        assert not any(f.get(k,1) for k in ('se_e_job','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks'))
        assert f.get('se_e_error',1)==c.get('error',0)
        if c.get('node') is not None:assert f.get('se_h_current',4)==c['node'] and f.get('se_h_saved',4)==1
        assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
        assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==c['current'].encode()
        wanted_settings=bytes.fromhex(c['settings']) if c.get('settings') else (e/'editor-defaults.bin').read_bytes()
        assert f.read(0xCB80,64)==wanted_settings
        physical=f.read(s['se_reu_physical_owner'],256);logical=f.read(s['se_reu_logical_owner'],256)
        assert all(v==255 for v in physical[kb//64:])
        allocated=[i for i,v in enumerate(physical[:kb//64]) if v];max_banks=max(max_banks,len(allocated))
        for handle,owner in enumerate(logical):
            if owner not in (0,255):
                bank=ram[s['se_reu_map']+handle];assert bank<kb//64 and physical[bank]==owner
        objects=sum(bool(v) for v in f.read(s['object_owner'],8));max_objects=max(max_objects,objects)
        for i,handle in enumerate(f.read(0xCBC1,2)):
            bank=ram[s['se_reu_map']+handle];assert handle and physical[bank]==logical[handle]==0xFD
            chunk=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(chunk)]==chunk
        for order,name in enumerate(json.loads((e/'freeze.json').read_text())['catalog']):
            image=(e/(name+'.seo')).read_bytes();slot=editor_pair_index(image[5],image[6]) if 'catalog_index' in s else order
            handle=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);bank=ram[s['se_reu_map']+handle]
            assert physical[bank]==logical[handle]==2;payload=image[36:];start=bank*65536+(slot&15)*4096
            assert reu[start:start+len(payload)]==payload
        if c['clipboard'] is not None:
            clip=bytes.fromhex(c['clipboard']);assert f.get('se_clip_length')==len(clip)
            assert object_bytes(f,reu,f.read(s['se_clip_token'],5),len(clip))==clip
        if not c['capacity_case']:
            tree=[folds.decoded_fold(bytes.fromhex(x)) for x in c['folds']]
            if f.get('se_ef_valid',1):assert object_bytes(f,reu,f.read(s['se_ef_token'],5),len(tree)*32)==b''.join(x.bytes() for x in tree)
            state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],n) for k,n in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
            if canonical is None:canonical=state
            assert state==canonical
            group=bool(c['clipboard']);masked=bytearray(reu)
            for bank in derived:masked[bank*65536:(bank+1)*65536]=bytes(65536)
            digest=hashlib.sha256(masked).hexdigest()
            if group in groups:intervals+=1
            assert digest==groups.setdefault(group,digest),(ident,'whole actual REU outside declared derived banks')
        if ident in ('undo-Q','redo-Q','undo-Q-final','large64-undo','large64-redo','large64-undo-final'):
            raw=object_bytes(f,reu,f.read(s['se_h_token'],5),f.get('se_h_end',2));assert len(raw)==(84 if ident.startswith('large64') else 75) and raw[:5]==b'SEH1\1'
            assert binascii.crc_hqx(raw[:58]+raw[60:64],0xFFFF)==int.from_bytes(raw[58:60],'little')
            assert binascii.crc_hqx(raw[64:],0xFFFF)==int.from_bytes(raw[56:58],'little')
            assert [int.from_bytes(raw[a:a+3],'little') for a in (26,29,32,39,42)]==([65535,1,1,65536,65536] if ident.startswith('large64') else [0,0,1,0,1])
            if ident.startswith('large64'):
                assert raw[64:67]==raw[16:19] and raw[67:73]==bytes.fromhex('ffff00010000')
                assert raw[73:76]==raw[21:24] and raw[76:82]==bytes.fromhex('000000010000')
                assert object_bytes(f,reu,raw[16:21],65536)[-1:]==b'\r'
                assert object_bytes(f,reu,raw[21:26],1)==live.grid.native_text('Q')
                assert int.from_bytes(raw[82:84],'little')==84
            if journal is None:journal=raw
            assert raw==journal
        bits,attrs=raster(e,c,f,fonts,catalog)
        if c['mode']:
            assert ram[0x6000:0x7F40]==bits,(ident,'pixels',[(i,a,b)for i,(a,b)in enumerate(zip(ram[0x6000:0x7F40],bits))if a!=b][:8])
            assert ram[0x4000:0x43E8]==attrs,(ident,'attributes')
        w,h,pixels=read_png(out/('native-'+ident+'.png'));assert (w,h)==(384,272)
        for y in range(200):
            for x in range(320):
                at=(y//8)*40+x//8;ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attrs[at]>>4 if ink else attrs[at]&15;pixel=pixels[(35+y)*w+32+x]
                assert pixel==palette.setdefault(color,pixel),(ident,'VIC pixel',x,y)
        observed.append(dict(id=ident,source_bytes=len(data),pending=c.get('pending',0),allocated_banks=len(allocated),object_slots=objects))
    before=D81Image((e/'initial-fixtures.d81').read_bytes());after=D81Image((e/'working.d81').read_bytes())
    boundary=(e/'source64.bin').exists();saved=b'CAP64' if boundary else b'CAPOUT';wanted=(e/'source64.bin').read_bytes() if boundary else live.grid.fixture()
    assert {v.name for v in after.entries()}=={v.name for v in before.entries()}|{saved}
    assert after.read(saved,kind=1).data==wanted
    for entry in before.entries():
        a,b=before.read(entry.name),after.read(entry.name);assert a.data==b.data and a.sectors==b.sectors
    assert len(set(palette.values()))==len(palette)
    result=dict(status='passed',capacity_kb=kb,actual_REU_bytes=kb*1024,frames=observed,pixels=len(cases)*64000,attributes=len(cases)*1000,
        observed_checkpoint_max_allocated_banks=max_banks,observed_checkpoint_max_object_slots=max_objects,
        whole_actual_REU_derived_only_intervals=intervals,journal_bytes=len(journal or b''),saved_source_bytes=len(wanted),
        limits='Observed checkpoint maxima are not a trace of every transient allocation. Verified source sizes only, not maximum document capacity. NativeIRQbytes, not physical keys/timing.')
    if boundary:
        assert images['large64-undo-final']==images['large64-saved'],'large64 SaveAs must preserve whole actual REU'
        assert images['large64-opened']==images['large64-refused'],'quota refusal must preserve whole actual REU'
        assert images['large64-pending-replacement']==images['large64-refused-pending'],'pending quota refusal must preserve whole actual REU'
        intervals+=3;result['whole_actual_REU_derived_only_intervals']=intervals
        result['pending_source_bytes']=65536
        result['refused_above_quota_bytes']=65537
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def run_owned_plan(plan,out,timeout=900):
    """Same .NET protocol/assertions, longer lifetime for genuine largeIEC I/O.

    No second monitor client is used during an active run. Partial historical
    180s timeout remains preserved; this changes only the host runner lifetime.
    """
    path=out/'plan.yaml';path.write_text(json.dumps(plan,indent=2)+'\n')
    command=['dotnet','run','--no-build','--project',str(vice_plan.PROJECT),'--']
    for mode,extra in [('compile-plan',[]),('run-plan',['--close-vice','--no-tui'])]:
        p=subprocess.run(command+[mode,'--plan',str(path)]+extra,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        (out/(mode+'.stdout.txt')).write_text(p.stdout);(out/(mode+'.stderr.txt')).write_text(p.stderr)
        if mode=='run-plan' and p.stdout.strip().startswith('{'):
            outcome=json.loads(p.stdout)
            if 'RunDir' in outcome and Path(outcome['RunDir']).exists():shutil.copytree(outcome['RunDir'],out/'run')
        assert not p.returncode,(mode,p.stdout[-1800:],p.stderr[-1000:])
    manifest=json.loads(Path(outcome['Manifest']).read_text(encoding='utf-8-sig'));assert manifest['status']=='success',manifest
    for p in (out/'run/stages').glob('*/monitor_command.txt'):assert 'ERROR' not in p.read_text(encoding='utf-8-sig'),p
    return manifest


def execute(e,kb,boundary=False):
    n=boundary_scenario(e,kb) if boundary else scenario(e,kb);p=n.plan();assert len({x['id'] for x in p['steps']})==len(p['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests','tools'):
            for x in sorted((ROOT/folder).glob('*.py')):z.write(x,x.relative_to(ROOT))
    project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('NATIVE',e,'capacityKB',kb,'steps',len(n.steps),'IRQbytes',n.keys,'screens',len(n.cases) or 1,flush=True)
    run_owned_plan(p,n.out);return evaluate(e,kb)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--kb',type=int,choices=[0,512,1024,2048],default=1024);p.add_argument('--fixture',type=Path);p.add_argument('--cpu-fixture',type=Path,default=SOURCE);p.add_argument('--verify',type=Path);p.add_argument('--boundary',action='store_true');a=p.parse_args()
    if a.verify:evaluate(a.verify,a.kb)
    elif a.run:execute(a.fixture.resolve() if a.fixture else freeze(a.kb,a.cpu_fixture.resolve()),a.kb,a.boundary)
    else:print('Prepared actual907b REU capacity gate; --run --kb 1024|2048|512|0. Own8100/text8200.')
