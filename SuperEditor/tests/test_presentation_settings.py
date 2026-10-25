"""Host defaults and actual C7/R22 preset UI; no Plain renderer claim.

--cpu privately links only the changed UI images against an immutable resident.
A baseline without se_render_caps loans its proven free C5FD byte explicitly;
this tests the UI transaction, not integrated startup/bypass/native behavior.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,copy,hashlib,json,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import editor_settings as settings
import presentation_defaults as presentation

CATALOG=(settings.FontFace('bsw',0,0,9,(4,)*128),settings.FontFace('native',0,1,8,(8,)*128))
DATA=(ROOT/'config/editor-defaults.toml').read_bytes()


class HostDefaults(unittest.TestCase):
    def test_presets_preserve_every_font_byte(self):
        original=settings.compile_defaults(DATA,CATALOG)['editor-defaults.bin']
        self.assertEqual(len(original),64)
        for name,value in presentation.PRESETS.items():
            data=DATA.replace(b'source_preset = "full"',('source_preset = "'+name+'"').encode())
            outputs=presentation.compile_defaults(data,CATALOG)
            self.assertIn(('SE_PRESENTATION_DEFAULT='+str(value)).encode(),outputs['presentation-defaults.inc'])
            self.assertEqual(json.loads(outputs['presentation-defaults.json'])['capabilities'],value)
            self.assertEqual(settings.compile_defaults(data,CATALOG)['editor-defaults.bin'],original)
            self.assertEqual(outputs,presentation.compile_defaults(data,CATALOG))

    def test_legacy_full(self):
        data=DATA[:DATA.index(b'[editor]')]+DATA[DATA.index(b'[body]'):]
        self.assertEqual(json.loads(presentation.compile_defaults(data,CATALOG)['presentation-defaults.json'])['capabilities'],3)
        self.assertEqual(settings.compile_defaults(data,CATALOG)['editor-defaults.bin'],settings.compile_defaults(DATA,CATALOG)['editor-defaults.bin'])

    def test_invalid_editor_candidates(self):
        m=settings.tomllib.loads(DATA.decode())
        for editor in ({},{'source_preset':'off'},{'source_preset':'FULL'},{'source_preset':False},{'source_preset':2},{'source_preset':'full','unknown':1},'full',None):
            bad=copy.deepcopy(m);bad['editor']=editor
            with self.assertRaises(settings.SettingsError):settings.from_mapping(bad,CATALOG)
            with self.assertRaises(ValueError):presentation.validate_editor(editor)

    def test_same_whole_input_validation(self):
        for data in (DATA.replace(b'foreground = 1',b'foreground = 17',1),DATA.replace(b'schema = 1',b'schema = 2'),DATA+b'\nunknown = true\n',b'not TOML !'):
            with self.assertRaises(settings.SettingsError):presentation.compile_defaults(data,CATALOG)


def cpu(out,fixture):
    from peddle import Machine
    import test_grid_modes as grid
    from overlays import wrap
    from redraw_model import screen_code,native_text
    out.mkdir(parents=True,exist_ok=True)
    report=json.loads((fixture/'build/editor-report.json').read_text());s=report['symbols'].copy()
    seam='se_render_caps' not in s
    if seam:
        assert s['__BSS_RUN__']+s['__BSS_SIZE__']==0xC5FD
        s['se_render_caps']=0xC5FD
    extras=('object_owner','object_banks','object_size_lo','object_size_mid','object_size_hi','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry','text_ptr','screen_ptr')
    names=[n for n,v in s.items()if n.startswith('se_') and not 0x800<=v<0x1000]+list(extras)
    include=''.join('%s=$%04X\n'%(n,s[n]) for n in sorted(set(names)))
    include+='\n.macro OVL_BINDING\n.byte '+','.join('$%02X'%b for b in bytes.fromhex(report['resident_binding']['digest']))+'\n.endmacro\n'
    (out/'editor-api.inc').write_text(include)
    (out/'presentation-defaults.inc').write_bytes(presentation.compile_defaults(DATA)['presentation-defaults.inc'])
    def run(*args):subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True)
    for name,source,defines in [('menu','src/overlays/editor-menu.s',()),('popups','src/overlays/editor-popups.s',()),('box','src/tui/box40.s',('-D','EDITOR_OVERLAY=1'))]:
        run('ca65','-g',*defines,'-I',str(out),'-I','src','-o',str(out/(name+'.o')),source)
    for name,cfg,objects in [('menu','cfg/overlay-c.cfg',('menu',)),('popups','cfg/overlay-r.cfg',('popups','box'))]:
        run('ld65','-C',cfg,'-o',str(out/(name+'.bin')),'-Ln',str(out/(name+'.lbl')),*(str(out/(n+'.o'))for n in objects))
    labels={}
    for line in (out/'menu.lbl').read_text().splitlines():
        p=line.split()
        if len(p)==3:labels[p[2].lstrip('.')]=int(p[1],16)
    m=Machine();dll=grid.runner(out)
    import ctypes as C
    def reu():
        b=C.create_string_buffer(16*1024*1024);dll.gm_reu(m.handle,len(b),b);return hashlib.sha256(b.raw).hexdigest()
    def read(a,n):return bytes(m.read(a+i) for i in range(n))
    def put(n,v,w=1):m.load(s[n],v.to_bytes(w,'little'))
    def get(n):return m.read(s[n])
    prg=(fixture/'build/editor.prg').read_bytes();m.load(int.from_bytes(prg[:2],'little'),prg[2:])
    m.call(s['se_clear_state'])
    m.load(0xC600,bytes((i*71+31)&255 for i in range(1024)))
    m.load(0x9200,bytes((i*23+17)&255 for i in range(2048)))
    font64=(ROOT/'build/editor-settings/editor-defaults.bin').read_bytes();assert len(font64)==64
    m.load(s['se_editor_settings'],font64);m.load(0xB000,(out/'menu.bin').read_bytes());put('se_render_caps',3)
    m.load(s['se_ef_token'],bytes((7,2,3,4,5)));m.load(s['se_ef_count'],b'\x02\x00');put('se_ef_valid',1)
    protected=((0x9200,2048),(0xC600,1024),(s['se_editor_settings'],64),(s['se_doc_meta'],15),(s['se_doc_generation'],2),(s['se_r_revision'],4),(s['se_h_current'],4),(s['se_h_saved'],4),(s['se_clip_token'],5),(s['se_ef_token'],5),(s['se_ef_count'],2),(s['se_ef_valid'],1))
    def stable():return b''.join(read(a,n)for a,n in protected)
    original=stable();before_reu=reu();cases=[]
    flags=('se_l_valid','se_r_valid','se_st_valid','se_st_request','se_st_cp_valid','se_gc_width')
    def poison():
        for n in flags:put(n,1)
        m.load(s['se_gc_valid'],b'\xff'*3);m.load(s['se_ef_fold_rows'],b'\xff'*3)
        for a in (0xCF90,0xCFE8,0x9149):m.write(a,1)
    def assert_invalidated():
        assert all(get(n)==0 for n in flags)
        assert read(s['se_gc_valid'],3)==b'\0'*3
        assert read(s['se_ef_fold_rows'],3)==b'\0'*3
        assert all(m.read(a)==0 for a in (0xCF90,0xCFE8,0x9149))
        assert get('se_l_need_wrap')==get('se_e_redraw')==1
        assert stable()==original and reu()==before_reu
    def call_ui(key,ui=2,menu=0,text=b''):
        put('se_e_key',key);put('se_e_ui',ui);put('se_e_menu',menu);put('se_e_error',0);put('se_overlay_frame',0)
        put('se_e_text_length',len(text));m.load(s['se_e_text'],text+b'\0')
        r,used=m.call(0xB010);assert not r.p&1
        return used
    try:
        for text,caps in [('syntax plain',0),('syntax off',0),('syntax markdown',1),('syntax full',3),('syntax on',3)]:
            poison();used=call_ui(13,text=native_text(text));assert get('se_render_caps')==caps and get('se_e_command')==0 and get('se_e_ui')==0,(text,get('se_render_caps'),get('se_e_command'),get('se_e_ui'),get('se_e_error'));assert_invalidated();cases.append(dict(case=text,instructions=used))
        put('se_render_caps',0)
        for expected in (1,3,0):
            poison();used=call_ui(native_text('h')[0],ui=1,menu=8);assert get('se_render_caps')==expected;assert_invalidated();cases.append(dict(case='H cycle '+str(expected),instructions=used))
        for value in (2,4,255):
            old=get('se_render_caps');phase=read(0x8D00,1152);r,used=m.call(labels['settings_presentation'],a=value);assert get('se_render_caps')==old and get('se_e_error')==0x7C and read(0x8D00,1152)==phase;cases.append(dict(case='invalid cap '+str(value),instructions=used))
        for owner in (1,2,3,4,255):
            put('se_f_owner',owner);phase=read(0x8800,2432);old=get('se_render_caps');r,used=m.call(labels['settings_presentation'],a=3);assert get('se_render_caps')==old and get('se_f_owner')==owner and read(0x8800,2432)==phase;cases.append(dict(case='foreign owner '+str(owner),instructions=used))
        put('se_f_owner',0)
        for text in (b'syntax ',b'syntax json',b'syntax plain extra'):
            old=get('se_render_caps');call_ui(13,text=native_text(text.decode()));assert get('se_render_caps')==old and get('se_e_error')==0x76;cases.append(dict(case='refuse '+text.decode()))
        # Reset restores both independently compiled defaults after complete
        # candidate validation; UI64 keeps its original ABI and exact bytes.
        put('se_render_caps',0);m.write(s['se_editor_settings']+12,7);call_ui(native_text('r')[0],ui=1,menu=8)
        assert get('se_render_caps')==3 and read(s['se_editor_settings'],64)==font64 and stable()==original
        cases.append(dict(case='reset both defaults'))
        # A malformed immutable-default candidate must not partially restore
        # the separate preset before the existing64B validator refuses it.
        default_at=labels['settings_defaults'];old_default=m.read(default_at+12)
        m.write(default_at+12,17);put('se_render_caps',1)
        call_ui(native_text('r')[0],ui=1,menu=8)
        assert get('se_render_caps')==1 and read(s['se_editor_settings'],64)==font64 and get('se_e_error')==0x7C
        m.write(default_at+12,old_default);cases.append(dict(case='malformed reset atomic refusal'))
        m.load(0xA000,(out/'popups.bin').read_bytes())
        for caps,name in [(0,'Plain'),(1,'Markdown'),(3,'Full'),(2,'Invalid')]:
            put('se_render_caps',caps);put('se_e_menu',8);put('se_e_ui',1);put('se_e_item',0)
            m.load(0x4000,bytes([32])*1000);m.load(0xD800,bytes([1])*1000)
            r,used=m.call(0xA010);assert not r.p&1
            row=read(0x4000+40*20,40);assert row[3:17]==bytes(screen_code(v)for v in native_text('H source mode:'));assert row[17:17+len(name)]==bytes(screen_code(v)for v in native_text(name));assert read(0xD800+40*20+3,14+len(name))==bytes([1])*(14+len(name))
            assert stable()==original and reu()==before_reu;cases.append(dict(case='R22 '+name,instructions=used))
        result=dict(status='PASS',scope='Actual private C7/R22 UI; not integrated Plain renderer/startup/native',base_resident_sha256=report['sha256'],capability_free_byte_seam=seam,caps_address=s['se_render_caps'],menu_bytes=(out/'menu.bin').stat().st_size,popups_bytes=(out/'popups.bin').stat().st_size,cases=cases,whole_reu_sha256=before_reu,font64_sha256=hashlib.sha256(font64).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
    finally:m.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cpu',action='store_true');p.add_argument('--fixture',type=Path,default=ROOT/'build/geos-convergent-line-editor/20261025T211148922415Z/fixture');p.add_argument('--out',type=Path);a=p.parse_args()
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HostDefaults));assert r.wasSuccessful()
    if a.cpu:
        out=a.out or ROOT/'build/presentation-settings'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        result=cpu(out.resolve(),a.fixture.resolve());print(json.dumps(dict(status=result['status'],cases=len(result['cases']),out=str(out),menu_bytes=result['menu_bytes'],popups_bytes=result['popups_bytes'])))


if __name__=='__main__':main()
