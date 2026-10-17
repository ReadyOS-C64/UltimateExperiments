#!/usr/bin/env python3
"""Build one coherent development package. This does not qualify a V1 release."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.pycache_prefix = str(ROOT / 'build' / ('.absent-v1-candidate-' + str(os.getpid())))
if Path(sys.pycache_prefix).exists():
    raise RuntimeError('Source-only cache prefix must be absent')
COUPLED = ('START.TPL', 'START.REL', 'START.INO', 'DOS64.PRG', 'DOS64.REL')
NATIVE = ('SETUP.PRG', 'SETUP.FAT', 'SETUP.PUB', 'CONFIG.PRG', *COUPLED)
README = """DOS64 Ultimate development candidate

This is a coherent build, not the V1 release. The final native disk menu,
durable floppy configuration transactions and matched physical acceptance
are still in development. Do not use this candidate as your only copy of work.

For a fresh installation, copy all nine program/assets into one new folder
on the Ultimate. Keep SETUP.FAT, SETUP.PUB, START.TPL, START.REL, START.INO,
DOS64.PRG and DOS64.REL beside SETUP.PRG and CONFIG.PRG.

Supply your own three DOS 3.3 360 KiB raw images separately; vendor files
are not included. Enable Ultimate DOS/UCI and at least 4 MiB REU. The current
tested profile is PAL, Turbo Control Manual, CPU Speed 64. Record your normal
settings before changing them. A setting labelled 64 alone does not establish
that Manual turbo mode is active.

Run SETUP.PRG. Browse to this home folder and the three DOS images. Choose
a 2 or 20 MiB C drive, or the supported existing-C import. SETUP creates C
directly, separate A/B images, START.PRG and DOS64.CFG. It preserves existing
output files and source images; choose a fresh home after an interrupted job.
You do not need a blank HD download, dummy D81 or emulated FORMAT/COPY.

Run the generated START.PRG. CONFIG.PRG can prepare a new configuration and
folder-aware launcher while preserving existing media. For the supported
startup option, copy DOS64.INI.example to DOS64.INI and edit 40 or 80. A
missing DOS64.INI defaults to 80 columns. Moving a folder requires regenerating
its launcher. Do not replace an existing installation with this package.

The full Turbo Pascal IDE edit/save/disk-compile/run/fresh-boot reopen chain
has model evidence. Final physical keyboard/display and installer/media
acceptance remain open. No performance target is claimed by this package.
See the project's docs/V1_ENDPOINT.md for the release gates and current scope.

SHA256SUMS checks transport/copy integrity. BUILD.json describes the matched
files; hashes are not a signature or an end-user runtime dependency.
"""


def digest(path):
    data = Path(path).read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def atomic_json(path, value):
    pending = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    pending.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(pending, path)


def verify(records):
    for name, wanted in records.items():
        if digest(name) != wanted:
            raise RuntimeError('Component input/product changed: ' + name)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def component_inputs(coupled_path, setup_path, config_path):
    paths = [Path(p).resolve() for p in (coupled_path, setup_path, config_path)]
    records = {str(p): digest(p) for p in paths}
    coupled, setup, config = [json.loads(p.read_text()) for p in paths]
    if any(r.get('status') != 'passed' for r in (coupled, setup, config)):
        raise RuntimeError('All three component builds must have passed')
    shared = {}
    for report in (coupled, setup, config):
        for name, value in report['source_inputs'].items():
            if name in shared and shared[name] != value:
                raise RuntimeError('Mixed source generations: ' + name)
            shared[name] = value
    records.update(shared)
    verify(records)
    bundle = Path(coupled['bundle']).resolve()
    run = Path(coupled['run']).resolve()
    if not bundle.is_relative_to(run):
        raise RuntimeError('Coupled assets must belong to their immutable run')
    validator_path = ROOT / 'build_support/start_ini_bundle.py'
    records[str(validator_path)] = digest(validator_path)
    validator = module('candidate_coupled_validator', validator_path)
    validator.validate_bundle(bundle, run / 'start/controller.labels',
                              run / 'start/controller.map', run / 'main/build/dos64.labels')
    # CONFIG embeds the exact five asset identities, not merely the ABI version.
    if config['release']['assets'] != coupled['assets'] or config['release']['result_identity'] != digest(paths[0]):
        raise RuntimeError('CONFIG was built for a different coupled release')
    if not setup.get('runtime_preflight') or not setup.get('release'):
        raise RuntimeError('Candidate requires release-bound SETUP runtime preflight')
    if setup['release']['assets'] != coupled['assets'] or setup['release']['result_identity'] != digest(paths[0]):
        raise RuntimeError('SETUP was built for a different coupled release')
    selected = {name: bundle / name for name in COUPLED}
    setup_build = Path(setup['work']) / 'build'
    for name, original in [('SETUP.PRG', 'setup.prg'), ('SETUP.FAT', 'SETUP.FAT'), ('SETUP.PUB', 'SETUP.PUB')]:
        path = setup_build / original
        if digest(path) != setup['products'][original]:
            raise RuntimeError('SETUP product differs from its receipt: ' + name)
        selected[name] = path
    selected['CONFIG.PRG'] = Path(config['products']['CONFIG.PRG']['path'])
    for name, path in selected.items():
        expected = coupled['assets'][name] if name in COUPLED else (
            {k: config['products'][name][k] for k in ('sha256', 'bytes')} if name == 'CONFIG.PRG' else digest(path))
        if digest(path) != expected:
            raise RuntimeError('Native product differs from its receipt: ' + name)
        records[str(path)] = expected
    # Include every native product, label/map and compiler output used by validation.
    for report, key in [(coupled, 'products'), (config, 'native_products')]:
        records.update(report[key])
    records.update({str(setup_build / name): value for name, value in setup['products'].items()})
    verify(records)
    return selected, records


def assemble(coupled_path, setup_path, config_path, destination):
    selected, records = component_inputs(coupled_path, setup_path, config_path)
    # Refuse any preexisting destination rather than replacing user media or CFG.
    destination.mkdir()
    for name in NATIVE:
        shutil.copyfile(selected[name], destination / name)
        if digest(destination / name) != records[str(selected[name])]:
            raise RuntimeError('Candidate copy mismatch: ' + name)
    inventory = {name: digest(destination / name) for name in NATIVE}
    build = {'schema': 1, 'kind': 'DOS64_DEVELOPMENT_CANDIDATE_NOT_V1_RELEASE',
             'physical_release_qualified': False, 'V1_release_gates_closed': False,
             'minimum_REU_bytes': 4194304, 'native_assets': inventory,
             'vendor_images_included': False, 'configured_home_included': False}
    atomic_json(destination / 'BUILD.json', build)
    (destination / 'README.txt').write_text(README, encoding='ascii')
    (destination / 'DOS64.INI.example').write_bytes(b'[emulator]\r\ninitial_columns=80\r\n')
    files = {p.name: digest(p) for p in sorted(destination.iterdir())}
    (destination / 'SHA256SUMS').write_text(''.join(v['sha256'] + '  ' + name + '\n' for name, v in files.items()), encoding='ascii')
    files['SHA256SUMS'] = digest(destination / 'SHA256SUMS')
    verify(records)
    return records, files


def archive(folder, path, files):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as target:
        for name in sorted(files):
            item = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            target.writestr(item, (folder / name).read_bytes())
    with zipfile.ZipFile(path) as target:
        if target.testzip() is not None or set(target.namelist()) != set(files):
            raise RuntimeError('Candidate archive inventory/CRC mismatch')
        for name, wanted in files.items():
            data = target.read(name)
            if {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} != wanted:
                raise RuntimeError('Candidate archive bytes differ: ' + name)


def build(out):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=out))
    records = {str(Path(__file__).resolve()): digest(__file__)}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for name in ('PYTHONPATH', 'PYTHONPYCACHEPREFIX', 'CC65_HOME', 'CC65_INC', 'CA65_INC', 'LD65_LIB', 'LD65_CFG'):
        env.pop(name, None)
    phase = 'build coupled release'
    commands = []
    try:
        for name, script, extra in [
            ('coupled', 'start_ini_bundle.py', []),
            ('setup', 'setup_installer.py', ['--bundle-result', str(run / 'coupled/RESULT.json')]),
            ('config', 'config_generation.py', ['--bundle-result', str(run / 'coupled/RESULT.json')]),
        ]:
            phase = 'build ' + name
            source = ROOT / 'build_support' / script
            records[str(source)] = digest(source)
            command = [sys.executable, '-B', str(source), '--out', str(run / name), *extra]
            commands.append(command)
            with (run / (name + '.stdout')).open('wb') as stdout, (run / (name + '.stderr')).open('wb') as stderr:
                subprocess.run(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr, check=True, timeout=600)
        phase = 'validate and assemble'
        inputs, files = assemble(run / 'coupled/RESULT.json', run / 'setup/RESULT.json',
                                 run / 'config/RESULT.json', run / 'package')
        records.update(inputs)
        phase = 'archive'
        zip_path = run / 'DOS64-candidate.zip'
        archive(run / 'package', zip_path, files)
        verify(records)
        result = {'status': 'passed', 'scope': 'COHERENT_SOURCE_BUILT_CANDIDATE_NOT_V1_ACCEPTANCE',
                  'run': str(run), 'package': str(run / 'package'), 'archive': str(zip_path),
                  'archive_identity': digest(zip_path), 'files': files, 'source_products': records,
                  'commands': commands, 'physical': False, 'V1_complete': False}
        atomic_json(run / 'RESULT.json', result)
        atomic_json(out / 'RESULT.json', result)
        return result
    except BaseException as first:
        try:
            atomic_json(run / 'FAILURE.json', {'phase': phase, 'exception': type(first).__name__,
                                              'error': str(first), 'prior_result_preserved': True})
        except BaseException:
            pass
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/v1-candidate')
    args = parser.parse_args()
    report = build(args.out)
    print(report['archive'])
