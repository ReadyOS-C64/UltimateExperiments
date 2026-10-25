"""Native frozen GEOS mixed-metric selection/history/save/reopen acceptance.

Own7900/text8000. Source enters through real ROM File/Open. Canonical clipboard,
journal records, saved raw1581 chains and all native VIC pixels are independent
oracles; there are no debugger document/register writes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,subprocess,zipfile
import test_geos_semantic_editor as semantic
import test_geos_semantic_vice as previous
import test_geos_navigation_vice as native
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan
live=previous.live;ROOT=live.ROOT
FINAL=ROOT/'agentsworking/evidence/M7/20261025T032222941206Z-geos-semantic-io-native'
START=15;STOP=77;CLIP=semantic.FIXTURE[START:STOP]
PASTED=semantic.FIXTURE+CLIP


class Plan(native.Plan):
    def __init__(self,e,report,phase):
        live.grid.NativePlan.__init__(self,e,phase,report)
        self.mode=0;self.mode_serial=0;self.wide_colors=True;self.row_cache=True
        prg=(e/'editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');le=lambda n:self.s[n].to_bytes(2,'little')
        pattern=b'\xAD'+le('se_e_redraw')+b'\xF0\x06\x20'+le('se_editor_render')+b'\x4C'+le('se_idle')+b'\xAD'+le('se_e_ui')
        at=prg.find(pattern);assert at>=2 and prg.find(pattern,at+1)<0
        self.idle_pc=load+at-2+11
    def plan(self):
        plan=super().plan();plan['global_defaults']['monitor_port_start']=7900;plan['global_defaults']['monitor_port_span']=1;return plan


def freeze(source=FINAL):
    source=Path(source).resolve();font_source=source/'fonts/chargen.bin'
    if (source/'build/editor.prg').exists():source=previous.freeze(source)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M7'/(stamp+'-geos-semantic-io-native');e.mkdir(parents=True)
    for p in source.iterdir():
        if p.is_file() and p.name not in ('final-verifier-sources.zip','cpu-result.json','verification-sources.zip'):shutil.copy2(p,e/p.name)
    if font_source.exists():shutil.copy2(font_source,e/'chargen.bin')
    shutil.copy2(source/'initial-fixtures.d81',e/'working.d81');shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    identity=json.loads((e/'freeze.json').read_text());assert 31<=len(identity['catalog'])<=32 and {'geossema','geoslex','geosnav'}<=set(identity['catalog']);assert hashlib.sha256((e/'editor.prg').read_bytes()).hexdigest()==identity['prg_sha256']
    disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
    for name,h in identity['asset_sha256'].items():assert hashlib.sha256((e/(name+'.seo')).read_bytes()).hexdigest()==h and disk.read(name.upper().encode(),kind=1).data==(e/(name+'.seo')).read_bytes()
    assert D81Image((e/'working.d81').read_bytes()).read(b'STYLED',kind=1).data==semantic.FIXTURE
    print('FROZEN '+str(e),flush=True);return e


def scenario(e,phase):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),phase)
    def capture(ident,data,caret,*,mode=3,marked=False,anchor=0,current=b'STYLED',node=1,saved=1,clipboard=None,group=None):
        for name,value,width in [('se_hot_caret',caret,3),('se_sel_mark',int(marked),1),('se_h_current',node,4),('se_h_saved',saved,4),('se_h_dirty',int(node!=saved),1)]:n.memory(ident+'_expected_'+name,name,value,width)
        if marked:n.memory(ident+'_expected_anchor','se_sel_anchor',anchor,3)
        if mode==3:n.memory(ident+'_visible_canonical_caret','se_v_seen',1)
        if mode<3:n.memory(ident+'_stylevalid','se_st_valid',1);n.memory(ident+'_styledone','se_st_request',0)
        n.snapshot(ident,data,mode)
        n.cases[-1].update(caret=caret,mark=marked,anchor=anchor,current=current.decode(),node=node,saved=saved,clipboard=clipboard.hex() if clipboard is not None else None,readonly_group=group)
    n.boot()
    if phase=='restart':
        n.open('reopen_saved',b'STYLEDIO');n.typed('reopen_geos','mode hires');capture('restarted-geos',PASTED,0,current=b'STYLEDIO')
        for mode in (0,1,2):n.mode_to(mode);capture('restarted-'+str((40,60,80)[mode]),PASTED,0,mode=mode,current=b'STYLEDIO',group='restart-modes')
        n.typed('restarted_return','mode hires');capture('restarted-return',PASTED,0,current=b'STYLEDIO',group='restart-modes');return n
    n.open('open_original',b'STYLED');n.typed('initial_geos','mode hires');capture('initial',semantic.FIXTURE,0)
    n.typed('select_start','goto 2');n.memory('start15','se_hot_caret',START,3)
    n.send('mark_key',bytes([0x89]));n.send('select_cross_metrics',bytes([0x1D])*(STOP-START))
    capture('marked-prose-through-code',semantic.FIXTURE,STOP,marked=True,anchor=START)
    n.send('copy_native0B',bytes([0x0B]));n.memory('exact_clip_length','se_clip_length',len(CLIP),3)
    capture('copied',semantic.FIXTURE,STOP,marked=True,anchor=START,clipboard=CLIP)
    n.send('unmark_key',bytes([3]));n.typed('paste_end','bottom');n.memory('end328','se_hot_caret',len(semantic.FIXTURE),3)
    n.send('paste_native16',bytes([0x16]));capture('pasted',PASTED,len(PASTED),node=2,clipboard=CLIP)
    n.send('undo_native1A',bytes([0x1A]));capture('undo',semantic.FIXTURE,len(semantic.FIXTURE),clipboard=CLIP,group='undo-modes')
    for mode in (0,1,2):n.mode_to(mode);capture('undo-mode'+str((40,60,80)[mode]),semantic.FIXTURE,len(semantic.FIXTURE),mode=mode,clipboard=CLIP,group='undo-modes')
    n.typed('return_geos','mode hires');capture('undo-return-geos',semantic.FIXTURE,len(semantic.FIXTURE),clipboard=CLIP,group='undo-modes')
    n.send('redo_native19',bytes([0x19]));capture('redo',PASTED,len(PASTED),node=2,clipboard=CLIP)
    n.save_as('save_raw_petscii',b'STYLEDIO');capture('saved',PASTED,len(PASTED),node=2,saved=2,current=b'STYLEDIO',clipboard=CLIP)
    n.open('open_original_again',b'STYLED');capture('opened-original',semantic.FIXTURE,0,clipboard=CLIP)
    n.open('reopen_saved_same_process',b'STYLEDIO');capture('reopened',PASTED,0,current=b'STYLEDIO',clipboard=CLIP)
    return n


def exact_journal(f,reu):
    size=f.get('se_h_end',2);raw=native.object_bytes(f,reu,f.read(f.s['se_h_token'],5),size)
    assert len(raw)>=66 and raw[:5]==b'SEH1\x01';head=raw[:64];length=int.from_bytes(head[6:8],'little');assert length==len(raw)==75
    assert binascii.crc_hqx(head[:58]+head[60:],0xFFFF)==int.from_bytes(head[58:60],'little')
    assert binascii.crc_hqx(raw[64:],0xFFFF)==int.from_bytes(head[56:58],'little') and int.from_bytes(raw[-2:],'little')==length
    assert tuple(int.from_bytes(head[a:a+3],'little') for a in (26,29,32,39,42))==(328,0,len(CLIP),328,len(PASTED))
    assert int.from_bytes(head[8:12],'little')==1 and int.from_bytes(head[12:16],'little')==2
    assert head[35:39]==b'\0\0\1\0' and head[5]==head[45]==0
    ref=raw[64:73];token=ref[:3]+f.read(f.s['se_object_epoch'],2);offset=int.from_bytes(ref[3:6],'little');count=int.from_bytes(ref[6:9],'little');assert count==len(CLIP)
    assert native.object_bytes(f,reu,token,offset+count)[offset:]==CLIP,'journal canonical inserted reference bytes'
    return raw


def evaluate(e,phase):
    out=e/phase;s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS};fonts['native8.bin']=(e/'grid80.seo').read_bytes()[36+0xC00:36+0x1000]
    font40=(e/'chargen.bin').read_bytes()[0x800:0x1000];assert len(font40)==2048
    frozen=json.loads((e/'freeze.json').read_text());catalog_names=frozen['catalog']
    palette={};observations=[];catalog=None;groups={};journal=None;readonly=0
    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
        assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'] and bool(f.get('se_sel_mark',1))==c['mark'],(ident,'canonical source/caret/selection')
        if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
        assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==c['current'].encode() and f.get('se_f_current_device',1)==8
        assert (f.get('se_h_current',4),f.get('se_h_saved',4),f.get('se_h_dirty',1))==(c['node'],c['saved'],int(c['node']!=c['saved']))
        assert all(f.get(k,1)==0 for k in ('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_f_owner','se_e_error','se_hot_pending'))
        assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
        got_catalog=f.read(s['se_overlay_ids'],192)
        if catalog is None:catalog=got_catalog
        assert got_catalog==catalog
        assert len(reu)==16*1024*1024
        for slot,name in enumerate(catalog_names):
            handle=f.get('se_overlay_asset' if slot<16 else 'se_overlay_asset_second',1);physical=ram[s['se_reu_map']+handle]
            assert handle and physical and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+physical],(ident,'catalog allocation ownership',slot)
            payload=(e/(name+'.seo')).read_bytes()[36:];offset=physical*65536+(slot%16)*4096
            assert reu[offset:offset+len(payload)]==payload,(ident,'complete frozen catalog payload',slot,name)
        if c['clipboard'] is not None:
            wanted=bytes.fromhex(c['clipboard']);assert f.get('se_clip_length')==len(wanted)
            assert native.object_bytes(f,reu,f.read(s['se_clip_token'],5),len(wanted))==wanted,(ident,'complete canonical clipboard')
        if phase=='editing' and ident not in ('initial','marked-prose-through-code','copied','opened-original','reopened'):
            got=exact_journal(f,reu)
            if journal is None:journal=got
            assert got==journal,(ident,'single unchanged authoritative paste record through undo/redo/save')
        if c['mode']==3:
            assert f.get('se_v_seen',1)==1,(ident,'canonical caret must remain visible')
            bits,attrs,_,_=semantic.expected(f,data,fonts)
        else:
            (a,b),_,_,_=live.geos.grid.expected(f,data)
            if c['mode']==0:
                assert f.read(0x4000,1000)==a and bytes(v&15 for v in colors)==b,(ident,'source40 glyphs/colors')
                assert f.read(0x4800,2048)==font40,(ident,'full256glyphsource40fontvsfrozenROM')
                bits=bytearray(8000);attrs=bytearray(1000)
                for row in range(25):
                    for col in range(40):
                        at=row*40+col;code=a[at];bits[row*320+col*8:row*320+col*8+8]=font40[code*8:code*8+8];attrs[at]=(b[at]<<4)|6
            else:bits,attrs=a,b
        if c['mode']:
            assert ram[0x6000:0x7F40]==bits,(ident,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7F40],bits)) if a!=b))
            assert ram[0x4000:0x43E8]==attrs,(ident,'attrs',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x4000:0x43E8],attrs)) if a!=b))
        w,h,pixels=read_png(out/('native-'+ident+'.png'));assert(w,h)==(384,272)
        for y in range(200):
            for x in range(320):
                attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));role=attr>>4 if ink else attr&15;actual=pixels[(35+y)*w+32+x]
                assert actual==palette.setdefault(role,actual),(ident,'nativeVICpixel',x,y)
        if c['readonly_group']:
            handle=f.get('se_gc_handle',1);physical=f.ram[s['se_reu_map']+handle]
            assert handle and physical and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2) and f.ram[s['se_reu_logical_owner']+handle]==f.ram[s['se_reu_physical_owner']+physical]==0xFE
            assert len(reu)==16*1024*1024;masked=reu[:physical*65536]+bytes(65536)+reu[(physical+1)*65536:]
            state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],n) for k,n in (('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)))
            value=(state,hashlib.sha256(masked).hexdigest())
            if c['readonly_group'] in groups:readonly+=1
            assert value==groups.setdefault(c['readonly_group'],value),(ident,'modecycle canonical/history/whole16MiB outside activeFE cachebank')
        observations.append(dict(id=ident,mode=c['mode'],bytes=len(data),caret=c['caret'],node=c['node'],saved=c['saved']))
    assert len(set(palette.values()))==len(palette)
    if journal is not None:(out/'exact-paste-journal.bin').write_bytes(journal)
    result=dict(status='passed',phase=phase,identity=json.loads((e/'freeze.json').read_text()),cases=observations,catalog_assets_checked=len(catalog_names),catalog_frames_checked=len(cases),screenshots=len(cases),native_pixels=64000*len(cases),native_attributes=1000*len(cases),whole16MiB_readonly_intervals=readonly,clipboard_bytes=len(CLIP),journal_bytes=len(journal) if journal else 0,scope='ActualROMFileOpen/IRQnative mixedfont canonicalselection/copy/paste/undo/redo/saveas/reopen; all4modes nativeVICpixels, no physicalkeyboard/timing claim.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def disk_oracle(e):
    before=D81Image((e/'initial-fixtures.d81').read_bytes());after=D81Image((e/'working.d81').read_bytes());original={x.name for x in before.entries()}
    assert {x.name for x in after.entries()}==original|{b'STYLEDIO'},'unexpected temp/backup/orphan'
    assert after.read(b'STYLEDIO',kind=1).data==PASTED,'byteexact native saved canonicalPETSCII'
    for name in original:
        a,b=before.read(name),after.read(name)
        assert a.data==b.data and a.sectors==b.sectors,(name,'unrelatedfile/sectorchain')
        assert (a.entry.kind,a.entry.closed,a.entry.locked,a.entry.first,a.entry.blocks)==(b.entry.kind,b.entry.closed,b.entry.locked,b.entry.first,b.entry.blocks)
    result=dict(status='passed',saved_bytes=len(PASTED),saved_sha256=hashlib.sha256(PASTED).hexdigest(),unrelated_files_unchanged=len(original),disk_sha256=hashlib.sha256((e/'working.d81').read_bytes()).hexdigest(),oracle='Independent raw1581 sector chains; no c1541 sequential read')
    (e/'disk-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def execute(e,phase):
    n=scenario(e,phase);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
    with zipfile.ZipFile(e/('verification-'+phase+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for module in (__file__,semantic.__file__,live.__file__,native.__file__,live.geos.__file__,ROOT/'tools/supermark_model.py',ROOT/'tools/d81_image.py',ROOT/'tests/geos_packet.py',Path(previous.__file__),ROOT/'tests/test_fold_retention_vice.py'):
            p=Path(module);z.write(p,p.relative_to(ROOT))
    project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0
    print('NATIVE '+str(e)+' phase='+phase+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' screenshots='+str(len(n.cases)),flush=True)
    vice_plan.run_plan(plan,n.out);return evaluate(e,phase)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--source-freeze',type=Path,default=FINAL);p.add_argument('--phase',choices=['editing','restart','both'],default='both');p.add_argument('--verify',type=Path);args=p.parse_args()
    if args.verify:
        for phase in ('editing','restart'):
            if (args.verify/phase/'cases.json').exists():evaluate(args.verify.resolve(),phase)
        return disk_oracle(args.verify.resolve())
    if args.run:
        e=(args.fixture or freeze(args.source_freeze)).resolve()
        for phase in (('editing','restart') if args.phase=='both' else (args.phase,)):execute(e,phase)
        disk_oracle(e);return
    print('Prepared actual native IO; --run uses frozenfinal private7900/text8000 only.')


if __name__=='__main__':main()
