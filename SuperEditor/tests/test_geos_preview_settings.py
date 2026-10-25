"""Actual packaged frontend settings/readonly-preview CPU acceptance.

Uses public F7/keys/rootcommands and unchanged packaged SEOs, never replacement
modules or a host font reader in the editor. Existing fixture IEC seams install
exact sealed overlays/immutable font pack via real provider/DMA; native IEC and
preview glyph appearance are separate gates. Default prepares only.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,hashlib,json,shutil,zipfile
import test_geos_editor as geos
import test_geos_preview_editor as preview
import editor_settings as settings
import font_fixture
from redraw_model import screen_code,native_text

ROOT=geos.ROOT
DATA=native_text('Settings preserve this source.\r# **Heading**\rPlain *italic* and @@code@@.\r:::basic\r10 PRINT "HELLO":REM note\r:::\rTail.\r')
FAMILY_NAMES={1:'University',2:'California',3:'Roma',4:'Dwinelle',5:'Cory',
    26:'Commodore',27:'LW Roma',28:'LW Cal',29:'LW Greek',30:'LW Barrows'}


def freeze(out,previous=None):
    frozen,identity=geos.freeze(out,previous)
    if not previous:
        for name in ('editor-settings','geos-font-catalog'):
            shutil.copytree(ROOT/'build'/name,frozen/'build'/name)
        (frozen/'config').mkdir();shutil.copy2(ROOT/'config/editor-defaults.toml',frozen/'config/editor-defaults.toml')
    assert (frozen/'build/editor-settings/editor-font-catalog.bin').stat().st_size==220
    return frozen,identity


def cycle(table,profile,which,catalog):
    model=settings.decode(table,catalog);p=model.profiles[profile]
    start=next(i for i,f in enumerate(catalog) if f.key==(p.origin,p.family,p.size))
    for delta in range(1,len(catalog)+1):
        face=catalog[(start+delta)%len(catalog)]
        if delta!=len(catalog):
            same=(face.origin,face.family)==(p.origin,p.family)
            if same!=(which=='size'):continue
            if profile==7 and not face.monospaced:continue
        profiles=list(model.profiles)
        profiles[profile]=replace(p,origin=face.origin,family=face.family,size=face.size)
        return settings.encode(settings.Settings(tuple(profiles)),catalog)
    raise AssertionError('catalog cycle could not preserve a valid face')


class CheckedFixture(preview.Fixture):
    def document(self):
        result=bytearray()
        for offset in range(0,self.get('se_doc_length'),1024):
            count=min(1024,self.get('se_doc_length')-offset)
            self.put('se_doc_offset',offset);self.put('se_doc_count',count,2);self.put('se_doc_c64',0x8000,2)
            regs=self.call('se_doc_read')
            assert not regs.p&1,('actual se_doc_read error',hex(regs.a),offset,count,
                self.read(self.s['doc_cache_slot'],3).hex(),self.read(0x8400,32).hex())
            result.extend(self.read(0x8000,count))
        return bytes(result)


class Bare:
    def __init__(self,fixture):self.fixture=fixture
    def get(self,name,width=3):
        return 0 if name in ('se_e_ui','se_e_menu') else self.fixture.get(name,width)
    def __getattr__(self,name):return getattr(self.fixture,name)


def popup_model(f,data,table,catalog):
    """Independent all1000logicalcells/colors for source40+menu8."""
    (matrix,colors),_,_,_=geos.grid.expected(Bare(f),data)
    matrix,colors=bytearray(matrix),bytearray(colors)
    def text(value,row,col):
        raw=bytes(map(screen_code,native_text(value)))
        matrix[row*40+col:row*40+col+len(raw)]=raw
    for y in range(20):
        for x in range(38):
            at=(y+3)*40+x+1;border=x in (0,37) or y in (0,19)
            glyph=32
            if y==0:glyph=0x70 if x==0 else 0x6E if x==37 else 0x40
            elif y==19:glyph=0x6D if x==0 else 0x7D if x==37 else 0x40
            elif x in (0,37):glyph=0x5D
            matrix[at]=glyph;colors[at]=14 if border else 1
    for value,row,col in [('Session text settings',4,3),('1 Body',6,3),('2 H1',7,3),('3 H2',8,3),('4 H3',9,3),('5 H4',10,3),('6 H5',11,3),('7 H6',12,3),('8 Code',13,3),('Font',6,16),('Size $',8,16),('Ink  $',9,16),('Paper$',10,16),('B / I / U',12,16),('F font  S size  C ink  G paper',15,3),('B/I/U toggle; arrows/1-8 profile',17,3),('R reset defaults; Return closes',19,3),('Session only / no disk writes',21,3)]:text(value,row,col)
    if 'se_render_caps' in f.s:
        text('H source mode:',20,3)
        text({0:'Plain',1:'Markdown',3:'Full'}.get(f.get('se_render_caps',1),'Invalid'),20,17)
    selected=f.get('se_e_item',1)&7
    for col in range(3,11):
        at=(selected+6)*40+col;matrix[at]^=128;colors[at]=3
    p=settings.decode(table,catalog).profiles[selected]
    if p.origin==0:text('BSW / 9' if p.family==0 else 'Native / 8',7,16)
    else:text(FAMILY_NAMES[p.family],7,16)
    for row,value in [(8,p.size),(9,p.foreground),(10,p.background)]:
        matrix[row*40+22:row*40+24]=f'{value:02X}'.encode()
        colors[row*40+22:row*40+24]=bytes([7])*2
    for code,col,bit in [(2,16,1),(9,20,2),(21,24,4)]:
        on=bool(p.styles&bit);matrix[13*40+col]=code^(128 if on else 0);colors[13*40+col]=3 if on else 1
    return bytes(matrix),bytes(colors)


def run(out,previous,smoke=False):
    frozen,identity=freeze(out,previous)
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=font_fixture.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    catalog=settings.supported_fonts(frozen/'build/geos-font-catalog/catalog.json')
    defaults=(frozen/'build/editor-settings/editor-defaults.bin').read_bytes()
    dll=geos.grid.runner(out);f=CheckedFixture(out,frozen,dll,True)
    frames=[];intervals=0;mode_intervals=0;preview_intervals=0;data=DATA;expected=defaults
    def FE():
        handle=f.get('se_gc_handle',1)
        if not handle:return set()
        assert f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
        assert f.m.read(f.s['se_reu_logical_owner']+handle)==0xFE
        bank=f.m.read(f.s['se_reu_map']+handle)
        assert bank and f.m.read(f.s['se_reu_physical_owner']+bank)==0xFE
        return {bank}
    def readonly_reu(before,after,banks=()):
        cursor=0
        for bank in sorted(banks):
            start=bank*65536;assert before[cursor:start]==after[cursor:start],('otherREUchanged',cursor,start)
            cursor=start+65536
        assert before[cursor:]==after[cursor:],'otherREUtailchanged'
    def actual():return f.read(f.s['se_editor_settings'],64)
    def source_guard(canonical,reu,catalog_bytes,tag):
        nonlocal intervals
        assert f.canonical()==canonical,(tag,'canonical/history/caret/gap changed')
        assert f.merged()==data and f.catalog()==catalog_bytes,(tag,'source/catalog changed')
        assert f.reu()==reu,(tag,'whole16MiB changed')
        assert f.read(0xC600,1024)==f.shim and not f.get('se_f_owner',1)
        intervals+=1
    def ui_frame(tag):
        before=(f.canonical(),f.reu(),f.catalog());f.render()
        assert (f.get('se_e_ui',1),f.get('se_e_menu',1))==(1,8)
        assert actual()==expected,(tag,'validated session table')
        matrix,colors=popup_model(f,data,expected,catalog)
        am,ac=f.read(0x4000,1000),f.read(0xD800,1000)
        for suffix,value in [('matrix',am),('colors',ac)]: (out/(tag+'-'+suffix+'.bin')).write_bytes(value)
        assert am==matrix,(tag,'1000logicalcells',next((i,a,b) for i,(a,b) in enumerate(zip(am,matrix)) if a!=b))
        assert ac==colors,(tag,'1000colors',next((i,a,b) for i,(a,b) in enumerate(zip(ac,colors)) if a!=b))
        source_guard(*before,tag)
        frames.append(dict(tag=tag,item=f.get('se_e_item',1),settings=expected.hex()))
        (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
    def key(value):f.key(native_text(value)[0] if isinstance(value,str) else value)
    def action(value,tag,draw=True):
        nonlocal expected
        selected=f.get('se_e_item',1);model=settings.decode(expected,catalog)
        if value in ('f','s'):expected=cycle(expected,selected,'font' if value=='f' else 'size',catalog)
        elif value=='r':expected=defaults
        else:
            rows=list(model.profiles);p=rows[selected]
            if value=='c':rows[selected]=replace(p,foreground=(p.foreground+1)&15)
            elif value=='g':rows[selected]=replace(p,background=(p.background+1)&15)
            elif value in ('b','i','u'):rows[selected]=replace(p,styles=p.styles^{'b':1,'i':2,'u':4}[value])
            expected=settings.encode(settings.Settings(tuple(rows)),catalog)
        before=(f.canonical(),f.reu(),f.catalog());key(value);source_guard(*before,tag+'-key')
        assert actual()==expected,(tag,'key did not publish expected whole table')
        if draw:ui_frame(tag)
    try:
        assert actual()==defaults,'actual startup must copy64compiled default bytes'
        f.source(data);assert actual()==defaults
        before=(f.canonical(),f.reu(),f.catalog());f.typed(native_text('settings'));source_guard(*before,'F7-settings')
        assert (f.get('se_e_ui',1),f.get('se_e_menu',1),f.get('se_e_item',1))==(1,8,0)
        ui_frame('initial');action('c','first-ink');action('r','first-reset')
        print('FIRST_ACTUAL_PUBLIC_F7_C16_C7_R22_SETTINGS_PASS',flush=True)
        if not smoke:
            # Actual F/S routes visit all44 admitted faces and wrap every family.
            groups=[]
            for face in catalog:
                group=(face.origin,face.family)
                if group not in groups:groups.append(group)
            visited=[]
            for group in groups:
                members=[face for face in catalog if (face.origin,face.family)==group]
                for face in members:
                    p=settings.decode(expected,catalog).profiles[0]
                    assert (p.origin,p.family,p.size)==face.key
                    ui_frame('face-'+face.name+'-'+str(face.size));visited.append(face.key)
                    action('s','size-'+face.name+'-'+str(face.size),draw=False)
                action('f','family-next-'+str(group),draw=False)
            assert len(visited)==len(set(visited))==44
            for profile in range(8):
                key(str(profile+1));assert f.get('se_e_item',1)==profile
                for value in ('b','i','u','c','g'):action(value,'profile'+str(profile)+'-'+value,draw=False)
                ui_frame('profile'+str(profile)+'-styles-colors')
            key('8')
            for face_key in [(1,26,10),(0,1,8)]:
                action('f','code-'+str(face_key),draw=False)
                p=settings.decode(expected,catalog).profiles[7];assert (p.origin,p.family,p.size)==face_key
                action('s','code-size-'+str(face_key),draw=False)
            action('r','reset-all')
        key('1')
        for value in ('f','b','u','c'):action(value,'nondefault-'+value,draw=False)
        ui_frame('nondefault-before-modes')
        assert expected!=defaults
        key(13);assert f.get('se_e_ui',1)==0
        # Session table persists through real mode changes and preview/reedit.
        before=f.canonical()
        for command,mode in [(98,2),(99,3)]:
            reu_before=f.reu();banks=FE();f.command(command);f.render();
            readonly_reu(reu_before,f.reu(),banks|FE());mode_intervals+=1;
            assert f.get('se_mode',1)==mode and actual()==expected
            assert f.canonical()==before and f.merged()==data
        reu_before=f.reu();f.typed(native_text('preview'));f.render()
        preview.guard_preview_reu(f,reu_before,f.reu(),'frontend-preview');preview_intervals+=1
        assert f.get('se_r_presentation',1)==1 and f.get('se_e_ui',1)==4 and actual()==expected
        assert f.canonical()==before and f.merged()==data
        for word in ('paste','undo','delete'):
            reu_before=f.reu();f.typed(native_text(word));f.render()
            preview.guard_preview_reu(f,reu_before,f.reu(),'frontend-preview');preview_intervals+=1
            assert f.canonical()==before and f.merged()==data and f.get('se_e_ui',1)==4,('preview readonly F7',word)
        reu_before=f.reu();f.key(0x85);key('e');key('d');f.render()
        preview.guard_preview_reu(f,reu_before,f.reu(),'frontend-preview');preview_intervals+=1
        assert f.canonical()==before and f.merged()==data and f.get('se_e_ui',1)==4,'preview Edit/Delete must not mutate'
        key(13);f.render();assert f.get('se_r_presentation',1)==0 and f.get('se_e_ui',1)==0
        assert f.canonical()==before and actual()==expected
        print('PUBLIC_PREVIEW_READONLY_AND_REEDIT_PASS',flush=True)
        # Actual pending source remains pending through preview and blocked edits.
        caret=f.get('se_hot_caret');value=native_text('Q');f.key(value[0]);data=data[:caret]+value+data[caret:]
        assert f.get('se_hot_pending',1)==1
        pending_before=f.canonical();pending_reu=f.reu()
        f.typed(native_text('preview'));f.render()
        for word in ('paste','undo','delete'):
            f.typed(native_text(word));f.render()
            assert f.canonical()==pending_before and f.merged()==data
            assert f.get('se_hot_pending',1)==1 and f.get('se_e_ui',1)==4
        f.key(0x85);key('e');key('d');f.render()
        assert f.canonical()==pending_before and f.get('se_hot_pending',1)==1 and f.merged()==data
        preview.guard_preview_reu(f,pending_reu,f.reu(),'frontend-pending-preview');preview_intervals+=1
        source_before=f.reu()
        f.typed(native_text('source'));f.render()
        assert f.canonical()==pending_before and f.merged()==data and actual()==expected
        assert f.get('se_hot_pending',1)==1 and f.get('se_e_ui',1)==0
        import test_geos_convergent_line as source_gate
        source_gate.outside(f,source_before,'frontend-reedit-source')
        print('PENDING_PREVIEW_READONLY_HISTORY_GAP_PASS',flush=True)
        result=dict(status='passed',identity=identity,UI_frames=len(frames),UI_cells=len(frames)*1000,UI_colors=len(frames)*1000,whole16MiB_intervals=intervals,mode_FEonly_intervals=mode_intervals,preview_exact_cache_intervals=preview_intervals,pending_preserved=True,nondefault_session_preserved=True,admitted_fonts=44,table_bytes=64,actual_public_F7_C16_C7_R22=True,preview_readonly_aliases=True,mode80_GE0S_session_preserved=True,frames=frames,scope='Actual packaged frontend/settings and readonlypreview CPU; no preview glyph pixel/native/timing claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
    except BaseException as exc:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(exc),debug=f.debug()),indent=2)+'\n')
        (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
    finally:f.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');parser.add_argument('--fixture',type=Path);parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    if not args.run:return print('Prepared; wait for root stable build before --run [--fixture immutable].')
    out=ROOT/'build/geos-preview-settings'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
    result=run(out,args.fixture,args.smoke);print(json.dumps({k:v for k,v in result.items() if k not in ('identity','frames')},indent=2));print(out)


if __name__=='__main__':main()
