#!/usr/bin/env python3
"""Build the native START template and replay its actual 6510 behavior locally."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
NATIVE = {
    **{n: 'tools/native/' + n for n in ['bulk_reu.c','bulk_reu.h','bulk_uci.h','bindings.s','crc32.s','crc32.h','platform.c','platform.s','platform.h','startup_close.s','startup_close.h','validator_crc.c','validator_crc.h']},
    **{n: 'tools/start/' + n for n in ['controller.c','controller.h','dma.s','frontend.s','handoff.s']},
    **{n: 'tools/setup/' + n for n in ['install_config.c','install_config.h','release.c','release.h']},
    'codec_test_entry.s': 'tools/start/entry.s', 'controller.cfg': 'tools/start/start.cfg',
    'uci.s':'src/uci.s', 'files.s':'src/files.s', 'uci.inc':'include/uci.inc', 'files.inc':'include/files.inc',
}
OPTIONS_NATIVE = {n:'tools/start/'+n for n in ['ini_parser.c','ini_parser.h','ini_io.c','ini_io.h','overlay_capsule.s']}
OPTIONS_NATIVE['controller.cfg']='tools/start/start-options.cfg'

NAMES = ['codec_test_entry','bulk_reu','bindings','uci','files','install_config','release','controller','dma','crc32','platform_c','platform','frontend','handoff','validator_crc','startup_close']

def digest(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def tools(test=False):
    result = {name: shutil.which(os.environ.get('DOS64_' + name.upper(), name)) for name in (['cc65','ca65','ld65','clang++'] if test else ['cc65','ca65','ld65'])}
    if not all(result.values()):
        raise RuntimeError('cc65, ca65, ld65 and clang++ are required')
    result = {name: str(Path(value).resolve()) for name,value in result.items()}
    supplied = os.environ.get('DOS64_CC65_LIB')
    candidates = [Path(supplied)] if supplied else [Path(result['cc65']).resolve().parent.parent/'share/cc65/lib/none.lib', Path('/opt/homebrew/share/cc65/lib/none.lib'), Path('/usr/share/cc65/lib/none.lib')]
    result['library'] = next((p for p in candidates if p.is_file()), None)
    if result['library'] is None:
        raise RuntimeError('Set DOS64_CC65_LIB to the cc65 none.lib path')
    result['library'] = result['library'].resolve()
    return result

def command(argv, work):
    subprocess.run([str(x) for x in argv], cwd=work, check=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

def sources(work, record, options=False):
    selected = dict(NATIVE, **OPTIONS_NATIVE) if options else NATIVE
    for destination, source in selected.items():
        p = ROOT/source
        record[str(p)] = digest(p)
        shutil.copyfile(p, work/destination)

def build(work, t, options=False, cold=False):
    extra = ['-D','D64_START_OPTIONS=1'] if options else []
    if cold:
        if not options: raise RuntimeError('Cold profile requires options')
        extra += ['-D','D64_START_MODAL=1','-D','D64_START_JOURNAL=1']
    names = NAMES + ['ini_parser','ini_io','overlay_capsule'] if options else NAMES
    if cold: names += ['journal_capsule','modal_capsule']
    for name in (['bulk_reu','install_config','release','controller','validator_crc'] + (['ini_parser','ini_io'] if options else [])):
        command([t['cc65'],'-t','none','-O','--add-source','-D','D64_VALIDATOR_FAST_CRC=1','-D','D64_CONFIG_VALIDATE_ONLY=1',*extra,name+'.c','-o',name+'.s'], work)
    command([t['cc65'],'-t','none','-O','--add-source','platform.c','-o','platform_c.s'], work)
    for name in names:
        command([t['ca65'],'-g',*extra,'-D','DOS64_FILES_INFO=1','-I','.',name+'.s','-o',name+'.o'], work)
    command([t['ld65'],'-C','controller.cfg','-o','controller.prg','-Ln','controller.labels','-m','controller.map',*[n+'.o' for n in names],t['library']], work)
    data=(work/'controller.prg').read_bytes()
    if data[:2] != b'\x01\x08' or len(data) > (0x5001 if cold else 0x4801):
        raise RuntimeError('START must load at0801 and finish below5000')
    products = ['controller.prg','controller.labels','controller.map']
    if options:
        symbols = {line.split()[2].lstrip('.'):int(line.split()[1],16) for line in (work/'controller.labels').read_text().splitlines() if line.startswith('al ')}
        asset=(work/'START.INO').read_bytes();at=symbols['_so_overlay_spec']-0x0801+2
        if not 2<=at<=len(data)-16 or data[at:at+6]!=b'D64I\x01\x10' or data[at+8:at+12]!=b'CRC?' or int.from_bytes(data[at+6:at+8],'little')!=len(asset) or data[at+12:at+16]!=b'\0\x60\0\0':
            raise RuntimeError('Unbound prelaunch capsule')
        if len(data)!=(20480 if cold else 18432) or symbols['__PRELAUNCH_RUN__']!=0x6000 or symbols['__PRELAUNCH_RO_RUN__']+symbols['__PRELAUNCH_RO_SIZE__']!=0x6000+len(asset) or len(asset)>8192:
            raise RuntimeError('Prelaunch layout changed')
        bound=bytearray(data);bound[at+8:at+12]=zlib.crc32(asset).to_bytes(4,'little')
        (work/'controller.prg').write_bytes(bound)
        products.append('START.INO')
    return {n:digest(work/n) for n in products}

def verify(record):
    for name, expected in record.items():
        if digest(Path(name)) != expected:
            raise RuntimeError('Build/test input changed: ' + name)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--test',action='store_true',help='Fresh source-only native/Peddle replay, including locally supplied DOS images')
    args=p.parse_args();t=tools(args.test);base=ROOT/'build';base.mkdir(exist_ok=True)
    os.environ.update({'DOS64_' + name.upper():str(value) for name,value in t.items() if name!='library'})
    os.environ['DOS64_CC65_LIB']=str(t['library'])
    if args.test:
        parent=Path(tempfile.mkdtemp(prefix='start-tests-',dir=base));work=parent/'work';work.mkdir()
    else:
        parent=base/'start';parent.mkdir(exist_ok=True);work=parent/'work';work.mkdir(exist_ok=True)
    record={str(Path(x).resolve()):digest(Path(x).resolve()) for x in [*t.values(),sys.executable]}
    record[str(Path(__file__))]=digest(Path(__file__));sources(work,record)
    native=build(work,t)
    if args.test:
        testroot=ROOT/'tests/start_launcher'
        for f in sorted(testroot.rglob('*')):
            if not f.is_file() or f.suffix not in ['.py','.s','.c','.h']:continue
            rel=f.relative_to(testroot)
            if rel.parts[0]=='support':continue
            dest=work/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);record[str(f)]=digest(f)
        for folder in ['tests/host','tests/floppy_export','third_party/peddle/Peddle']:
            for f in sorted((ROOT/folder).glob('*')):
                if f.is_file() and f.suffix in ['.cpp','.h']:
                    dest=work/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);record[str(f)]=digest(f)
        for f in (testroot/'support').glob('*'):
            target=work/('tests/host'if f.name=='peddle_bridge.h'else'tests/floppy_export')/f.name
            shutil.copyfile(f,target);record[str(f)]=digest(f)
        for f in [ROOT/'build/dos64.prg',ROOT/'build/dos64.labels',*sorted((ROOT/'reference').glob('*.img'))]:
            dest=parent/'inputs'/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);record[str(f)]=digest(f)
        if not list((parent/'inputs/reference').glob('*.img')):
            raise RuntimeError('Place locally supplied DOS images in reference/ before the opt-in DOS replay')
        (parent/'SOURCE_BEFORE.json').write_text(json.dumps(record,indent=2)+'\n')
        for script in ['build_sc_probe.py','build_codec_fixtures.py']:
            command([sys.executable,'-B',script],work)
        command([t['clang++'],'-std=c++20','-O2','-dynamiclib','-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle','tests/floppy_export/bridge.cpp',*[str(Path('third_party/peddle/Peddle')/n) for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','bulk-peddle.dylib'],work)
        names=list(native)+['sc-abi.prg','sc-abi.labels','sc-abi.map','bulk-peddle.dylib']+[f'codec-fixtures/{kind}/codec.{suffix}' for kind in ['old-default','new-default','full-fast'] for suffix in ['prg','labels','map']]
        products_before={name:digest(work/name) for name in names}
        for script in ['test_controller.py','test_peer.py','test_startup_close.py','test_codec_fast.py','test_start_controls.py','test_start.py']:
            command([sys.executable,'-B',script],work)
        if products_before != {name:digest(work/name) for name in names}:
            raise RuntimeError('START or native test product changed during replay')
        native=products_before
    verify(record)
    for name, source in [('START.PRG','controller.prg'),('START.labels','controller.labels'),('START.map','controller.map')]:
        shutil.copyfile(work/source,parent/name)
    result={'status':'passed','actual_native_groups':46 if args.test else None,'native':native,'source_inputs':record,'physical':False,'template':'disabled ownerFF/homeFF; SETUP publication required'}
    (parent/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(str(parent))

if __name__=='__main__':main()
