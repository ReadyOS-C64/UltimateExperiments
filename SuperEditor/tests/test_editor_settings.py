"""Host compiler/session-reference/actual ca65 ABI tests; no editor integration.

Run with Python3.11+ for TOML tests (available host: /opt/homebrew/bin/python3).
The default systemPython3.9 can run binary/session tests; TOML cases skip rather
than installing a global dependency or silently parsing a different dialect.
"""
from pathlib import Path
import copy
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import editor_settings as settings

DEFAULT=ROOT/'config/editor-defaults.toml'
OUT=ROOT/'build/editor-settings-tests'
PROOF={'binary_mutations':0,'invalid_candidates_preserved_active':0}


def defaults():
    profiles=tuple(settings.Profile(0,1 if name=='code' else 0,
        8 if name=='code' else 9,14 if name=='code' else 7 if name.startswith('heading') else 1,
        6,0) for name in settings.PROFILES)
    return settings.encode(settings.Settings(profiles))


class RuntimeTests(unittest.TestCase):
    def test_exact64_roundtrip(self):
        raw=defaults();self.assertEqual(len(raw),64)
        self.assertEqual(raw[:8],b'SEST\x01\x40\x08\x07')
        self.assertEqual(settings.encode(settings.decode(raw)),raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '3b1eba8b891d253e56cbbe563a4205045f6b35a7ee490dadf81315c08d4586e3')

    def test_actual_font_catalog(self):
        fonts=settings.supported_fonts()
        self.assertEqual(len(fonts),44)
        self.assertEqual([(f.name,f.origin,f.family,f.size) for f in fonts[:2]],
                         [('bsw',0,0,9),('native',0,1,8)])
        self.assertEqual(sum(f.origin==1 for f in fonts),42)
        mono=[(f.name,f.size) for f in fonts if f.monospaced]
        self.assertEqual(mono,[('native',8),('commodore',10)])
        self.assertFalse(fonts[0].monospaced);self.assertTrue(fonts[1].monospaced)
        self.assertEqual(set(fonts[1].advances),{8})
        self.assertTrue(all(f.sources for f in fonts))

    def test_code_measured_mono_not_name(self):
        fonts=settings.supported_fonts()
        fake_native=settings.FontFace('native',0,1,8,(8,)*127+(7,))
        with self.assertRaises(settings.SettingsError):
            settings.decode(defaults(),(fonts[0],fake_native))
        session=settings.SessionSettings(defaults())
        with self.assertRaises(settings.SettingsError):
            session.update('code',family=0,size=9)
        self.assertEqual(session.active,defaults())

    def test_atomic_reject_every_byte_mutations(self):
        session=settings.SessionSettings(defaults());original=session.active
        rng=random.Random(0x53455354)
        for at in range(64):
            for value in (0,1,7,15,16,255,rng.randrange(256)):
                candidate=bytearray(original);candidate[at]=value
                previous=session.active
                try:session.apply(candidate)
                except settings.SettingsError:
                    self.assertEqual(session.active,previous)
                    PROOF['invalid_candidates_preserved_active']+=1
                else:
                    self.assertEqual(settings.encode(settings.decode(session.active)),session.active)
                PROOF['binary_mutations']+=1
                session.apply(original)
        for candidate in (b'',original[:-1],original+b'\0'):
            with self.assertRaises(settings.SettingsError):session.apply(candidate)
            self.assertEqual(session.active,original)

    def test_styles_update_reset_no_disk_writes(self):
        catalog=settings.supported_fonts()
        session=settings.SessionSettings(defaults(),catalog)
        file_before=DEFAULT.read_bytes()
        def no_write(*a,**k):raise AssertionError('runtime session attempted disk write')
        with patch.object(settings,'write_outputs',no_write),patch.object(Path,'write_bytes',no_write),patch.object(Path,'write_text',no_write),patch.object(settings.os,'replace',no_write):
            for styles in range(8):
                session.update('body',foreground=styles,background=15-styles,styles=styles)
                p=settings.decode(session.active,catalog).profiles[0]
                self.assertEqual((p.foreground,p.background,p.styles),(styles,15-styles,styles))
            # All profiles, not only the edited one, are validated before publish.
            broken=bytearray(session.active);broken[57+6]=8
            old=session.active
            with self.assertRaises(settings.SettingsError):session.apply(broken)
            self.assertEqual(session.active,old)
            self.assertEqual(session.reset_defaults(),defaults())
        self.assertEqual(DEFAULT.read_bytes(),file_before)

    def test_invalid_style_color_and_unknown_font(self):
        session=settings.SessionSettings(defaults());old=session.active
        for changes in ({'styles':8},{'styles':-1},{'foreground':16},
                        {'background':True},{'size':10},{'family':27},{'origin':1}):
            with self.subTest(changes=changes),self.assertRaises(settings.SettingsError):
                session.update('body',**changes)
            self.assertEqual(session.active,old)
        with self.assertRaises(settings.SettingsError):session.update('body',invented=True)
        with self.assertRaises(settings.SettingsError):session.update('heading7',styles=1)

    def test_genuine_geos_namespace_extensible_not_builtin_collision(self):
        # A future renderer must explicitly admit the measured face first.
        fonts=settings.supported_fonts()
        university=settings.FontFace('University',1,1,12,(9,)*128)
        session=settings.SessionSettings(defaults(),fonts[:2]+(university,))
        session.update('body',origin=1,family=1,size=12)
        self.assertEqual(settings.decode(session.active,fonts[:2]+(university,)).profiles[0].origin,1)
        with self.assertRaises(settings.SettingsError):settings.decode(session.active,fonts[:2])

    def test_all_genuine_family_size_selections(self):
        catalog=settings.supported_fonts();base=settings.decode(defaults(),catalog)
        for face in catalog:
            profiles=list(base.profiles)
            p=profiles[0]
            profiles[0]=settings.Profile(face.origin,face.family,face.size,p.foreground,p.background,p.styles)
            raw=settings.encode(settings.Settings(tuple(profiles)),catalog)
            self.assertEqual(settings.decode(raw,catalog).profiles[0].family,face.family)
            profiles[-1]=profiles[0]
            if face.monospaced:
                settings.encode(settings.Settings(tuple(profiles)),catalog)
            else:
                with self.assertRaises(settings.SettingsError):settings.encode(settings.Settings(tuple(profiles)),catalog)

    def test_generated_abi_allocates_no_state(self):
        source=settings.abi_include().decode()
        self.assertNotIn('.res',source);self.assertNotIn('.segment',source)
        self.assertEqual((ROOT/'src/render/geos/settings.inc').read_bytes(),settings.abi_include())
        self.assertIn('SES_CODE=57',source);self.assertIn('SES_POINT_SIZE=3',source)


@unittest.skipIf(settings.tomllib is None,'TOML requires Python3.11+; use /opt/homebrew/bin/python3')
class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.data=DEFAULT.read_bytes();self.mapping=settings.tomllib.loads(self.data.decode())

    def test_current_appearance_defaults(self):
        result=settings.compile_defaults(self.data)
        self.assertEqual(result['editor-defaults.bin'],defaults())
        manifest=json.loads(result['editor-defaults.json'])
        self.assertEqual(len(result['editor-font-catalog.bin']),220)
        self.assertEqual(len(manifest['fonts']),44)
        self.assertEqual(result['editor-font-catalog.bin'][:10],bytes((0,0,0,9,0,0,1,0,8,1)))
        self.assertEqual(manifest['bytes'],64)
        self.assertEqual(manifest['profile_values']['body']['foreground'],1)
        self.assertEqual(manifest['profile_values']['heading6']['foreground'],7)
        self.assertEqual(manifest['profile_values']['code']['foreground'],14)
        self.assertTrue(all(p['background']==6 and p['styles']==0 for p in manifest['profile_values'].values()))
        self.assertIn('8x8',manifest['limits'][1])

    def test_deterministic_generation_and_real_ca65_bytes(self):
        first=settings.compile_defaults(self.data);second=settings.compile_defaults(self.data)
        self.assertEqual(first,second)
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            folder=Path(directory);settings.write_outputs(first,folder)
            self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},first)
            (folder/'test.s').write_text('.include "editor-defaults.inc"\n.segment "RODATA"\nstart: SE_SETTINGS_EMIT_DEFAULTS\nend:\n.assert end-start=SES_SIZE,error,"settings size"\n')
            (folder/'test.cfg').write_text('MEMORY { DATA:start=$8000,size=$100,file="defaults.bin",type=ro; }\nSEGMENTS { RODATA:load=DATA,type=ro; }\n')
            subprocess.run(['ca65','-I',str(folder),'test.s','-o','test.o'],cwd=folder,check=True,capture_output=True)
            subprocess.run(['ld65','-C','test.cfg','test.o'],cwd=folder,check=True,capture_output=True)
            self.assertEqual((folder/'defaults.bin').read_bytes(),first['editor-defaults.bin'])
            PROOF['ca65_bytes']=64

    def test_unknown_missing_and_wrong_types(self):
        mutants=[]
        for change in ('unknown-root','missing-profile','unknown-profile-key','missing-field','unsupported-font','unsupported-size','bool-color','numeric-style','mono-code'):
            data=copy.deepcopy(self.mapping)
            if change=='unknown-root':data['runtime_write']=True
            elif change=='missing-profile':del data['heading6']
            elif change=='unknown-profile-key':data['body']['itallic']=True
            elif change=='missing-field':del data['body']['underline']
            elif change=='unsupported-font':data['body']['font']='University'
            elif change=='unsupported-size':data['body']['size']=12
            elif change=='bool-color':data['body']['foreground']=True
            elif change=='numeric-style':data['body']['bold']=1
            elif change=='mono-code':data['code']['font']='bsw';data['code']['size']=9
            with self.subTest(change=change),self.assertRaises(settings.SettingsError):
                settings.from_mapping(data)
        for raw in (b'schema = 1\nschema = 1\n',b'body = [',b'\xff'):
            with self.assertRaises(settings.SettingsError):settings.read_toml(raw)

    def test_invalid_cli_does_not_publish_or_touch_existing_defaults(self):
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            folder=Path(directory);target=folder/'outputs';settings.write_outputs(settings.compile_defaults(self.data),target)
            before={p.name:p.read_bytes() for p in target.iterdir()}
            invalid=folder/'invalid.toml';invalid.write_bytes(self.data.replace(b'foreground = 1',b'foreground = 99',1))
            command=[sys.executable,str(ROOT/'tools/editor_settings.py'),str(invalid),'--out-dir',str(target)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},before)
            self.assertEqual(DEFAULT.read_bytes(),self.data)
            absent=folder/'absent'
            result=subprocess.run(command[:-1]+[str(absent)],capture_output=True)
            self.assertEqual(result.returncode,2);self.assertFalse(absent.exists())


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    run=unittest.main(exit=False,verbosity=2)
    PROOF.update(status='passed' if run.result.wasSuccessful() else 'failed',tests=run.result.testsRun,
        skipped=len(run.result.skipped),toml_available=settings.tomllib is not None,
        table_sha256=hashlib.sha256(defaults()).hexdigest(),
        scope='Host defaults/session atomicity and actualca65 ABI only; no runtime editor wiring/native.')
    (OUT/'result.json').write_text(json.dumps(PROOF,sort_keys=True,indent=2)+'\n')
    print(json.dumps(PROOF,sort_keys=True))
    sys.exit(0 if run.result.wasSuccessful() else 1)
