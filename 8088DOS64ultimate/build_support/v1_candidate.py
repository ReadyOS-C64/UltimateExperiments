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
if Path(sys.pycache_prefix).exists() or sys.flags.optimize:
    raise RuntimeError('Source-only cache prefix must be absent')
COUPLED = ('START.TPL', 'START.REL', 'START.INO', 'DOS64.PRG', 'DOS64.REL')
COLD = (*COUPLED, 'DOS64.MNU', 'START.RCV', 'START.RFW')
RUNTIME_NATIVE = ('SETUP.PRG', 'SETUP.FAT', 'SETUP.PUB', 'CONFIG.PRG', *COLD)
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

RUNTIME_README = """DOS64 Ultimate runtime-media development candidate

This source-built candidate is not a qualified V1 or physical release.
Keep backups. It includes twelve matched native files, no DOS images or
configured user disks. Copy all twelve into one NEW folder on the Ultimate.
Keep the three SETUP files, CONFIG.PRG and all eight runtime/START assets
together. Do not mix assets from another build or replace an existing home.

Supply your own three DOS 3.3 360 KiB raw images. Enable Ultimate DOS/UCI
and at least 4 MiB REU. The modeled profile is PAL, Turbo Control Manual,
CPU Speed 64. Record your usual settings; a speed labelled 64 alone does
not prove Manual turbo is active. Build success is not hardware acceptance.

Run SETUP.PRG, choose this home and your three DOS images, then choose
2 or 20 MiB C, or the supported existing-C import. SETUP creates C, A/B,
a configured START.PRG and DOS64.CFG, and copies the matched runtime assets.
Existing destinations are refused. After interruption, retain all files
and choose a fresh home; do not overwrite an uncertain installation.
No blank HD download, dummy D81 or guest FORMAT/COPY is required.

Run the generated START.PRG. It verifies the matching runtime, menu and
startup recovery assets. A pending save journal is not silently ignored:
follow its explicit recovery screen, retaining the original and new files.
CONFIG.PRG can prepare a new launch folder using existing absolute media
paths. It asks for the release folder, new folder and supported 40/80 startup
preference. A missing same-home DOS64.INI defaults to 80; the included ASCII
example documents that option. Do not move launch folders without rebuilding
the launcher/configuration through the supported tools.

During DOS, Ctrl + Commodore + Run/Stop opens native floppy controls.
A/B selects the drive; S saves to a new managed image version; N is Save as;
I inserts/changes an image; E ejects; W changes session write protection.
Follow Save/Discard/Cancel prompts for modified media. Eject/protect are
session-only. R resumes DOS when ownership and closure checks permit it.
Before ending a session, exit guest applications to DOS, then use F Finish.
Restart only after the native screen reports that it is safe. Finish ends
the guest session; it does not resume DOS. Errors or unknown file ownership
must not be treated as a completed save or permission to restart normally.

Model workflows and source builds do not establish physical keyboard,
display, power-loss or Turbo Pascal acceptance for this exact package.
No performance target is claimed. See docs/V1_ENDPOINT.md in the project.
SHA256SUMS checks copy integrity, not authenticity or release qualification.
"""


def digest(path):
    data = Path(path).read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def atomic_json(path, value):
    pending = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    primary = None
    try:
        pending.write_text(json.dumps(value, indent=2) + '\n')
        os.replace(pending, path)
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            pending.unlink(missing_ok=True)
        except BaseException:
            if primary is None:
                raise


def verify(records):
    for name, wanted in records.items():
        if digest(name) != wanted:
            raise RuntimeError('Component input/product changed: ' + name)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def merge(records, rows):
    for name, wanted in rows.items():
        if name in records and records[name] != wanted:
            raise RuntimeError('Mixed source generations: ' + name)
        records[name] = wanted


def declared_products(report, records):
    for name, row in report.get('products', {}).items():
        path = Path(row['path'] if 'path' in row else name).resolve()
        wanted = {k: row[k] for k in ('sha256', 'bytes')}
        merge(records, {str(path): wanted})


def metadata_paths(report, records):
    run = Path(report['run']).resolve()
    found = []
    for name, legacy in [('START.labels', 'start/controller.labels'),
                         ('START.map', 'start/controller.map'),
                         ('DOS64.labels', 'main/build/dos64.labels')]:
        row = report.get('products', {}).get(name)
        path = Path(row['path']).resolve() if row else (run / legacy).resolve()
        wanted = {k: row[k] for k in ('sha256', 'bytes')} if row else records.get(str(path))
        if not path.is_relative_to(run) or wanted is None or digest(path) != wanted:
            raise RuntimeError('Unbound coupled release metadata: ' + name)
        merge(records, {str(path): wanted})
        found.append(path)
    return found


def component_inputs(coupled_path, setup_path, config_path, *, runtime_media=False):
    paths = [Path(p).resolve() for p in (coupled_path, setup_path, config_path)]
    records = {str(p): digest(p) for p in paths}
    coupled, setup, config = [json.loads(p.read_text()) for p in paths]
    if any(r.get('status') != 'passed' for r in (coupled, setup, config)):
        raise RuntimeError('All three component builds must have passed')
    for report in (coupled, setup, config):
        merge(records, report['source_inputs'])
        merge(records, report.get('native_products', {}))
    # SETUP product keys are relative to its build directory; the other two
    # reports support both historical absolute keys and checked named rows.
    for report in (coupled, config):
        declared_products(report, records)
    verify(records)
    bundle = Path(coupled['bundle']).resolve()
    run = Path(coupled['run']).resolve()
    if not bundle.is_relative_to(run):
        raise RuntimeError('Coupled assets must belong to their immutable run')
    selected_assets = COLD if runtime_media else COUPLED
    if set(coupled['assets']) != set(selected_assets) or {p.name for p in bundle.iterdir()} != set(selected_assets):
        raise RuntimeError('Exact coupled asset inventory required')
    validator_path = ROOT / 'build_support/start_ini_bundle.py'
    records[str(validator_path)] = digest(validator_path)
    validator = module('candidate_coupled_validator', validator_path)
    for path in validator.dependencies().values():
        merge(records, {str(path): digest(path)})
    validator.validate_bundle(bundle, *metadata_paths(coupled, records),
                              start20k=runtime_media, cold_inventory=runtime_media,
                              mnu56k=runtime_media)
    if runtime_media:
        runtime_path = Path(coupled['runtime_result']).resolve()
        if digest(runtime_path) != coupled['runtime_result_identity']:
            raise RuntimeError('Cold bundle has stale runtime receipt')
        runtime = json.loads(runtime_path.read_text())
        if runtime.get('status') != 'passed' or runtime.get('role') != 'runtime' or runtime.get('schema') != 1:
            raise RuntimeError('Require passed actual runtime result')
        if runtime.get('flags', {}).get('DOS64_FLOPPY_FORMAT') != 1:
            raise RuntimeError('Candidate requires enabled runtime floppy FORMAT')
        if runtime.get('MNU_REU_spans') != [[0x3da000, 24576], [0x3f0000, 32768]]:
            raise RuntimeError('Unsupported runtime menu layout')
        merge(records, {str(runtime_path): digest(runtime_path)})
        for section in ('source_inputs', 'native_products'):
            merge(records, runtime[section])
        declared_products(runtime, records)
        if set(runtime['assets']) != {'DOS64.PRG', 'DOS64.REL', 'DOS64.MNU'}:
            raise RuntimeError('Exact runtime asset inventory required')
        for name, wanted in runtime['assets'].items():
            row = runtime['products'][name]
            if wanted != coupled['assets'][name] or wanted != {k: row[k] for k in ('sha256', 'bytes')}:
                raise RuntimeError('Cold bundle uses different runtime assets: ' + name)
    if config['release']['assets'] != coupled['assets'] or config['release']['result_identity'] != digest(paths[0]):
        raise RuntimeError('CONFIG was built for a different coupled release')
    if not setup.get('runtime_preflight') or not setup.get('release'):
        raise RuntimeError('Candidate requires release-bound SETUP runtime preflight')
    if setup['release']['assets'] != coupled['assets'] or setup['release']['result_identity'] != digest(paths[0]):
        raise RuntimeError('SETUP was built for a different coupled release')
    if runtime_media:
        checks = setup.get('memory', {}).get('checks', {})
        if not all(checks.get(k) is True for k in (
                'trusted_DIAG_source_lifetime', 'trusted_DIAG_device_tail',
                'file_helper_run', 'file_helper_source', 'file_helper_BSS_disjoint')):
            raise RuntimeError('Candidate requires checked SETUP startup/file diagnostics')
        if config.get('memory', {}).get('trusted_boot_diagnostics') is not True:
            raise RuntimeError('Candidate requires checked CONFIG startup diagnostics')
    selected = {name: bundle / name for name in selected_assets}
    setup_build = Path(setup['work']) / 'build'
    for name, original in [('SETUP.PRG', 'setup.prg'), ('SETUP.FAT', 'SETUP.FAT'), ('SETUP.PUB', 'SETUP.PUB')]:
        path = setup_build / original
        if digest(path) != setup['products'][original]:
            raise RuntimeError('SETUP product differs from its receipt: ' + name)
        selected[name] = path
    selected['CONFIG.PRG'] = Path(config['products']['CONFIG.PRG']['path']).resolve()
    for name, path in selected.items():
        expected = coupled['assets'][name] if name in selected_assets else (
            {k: config['products'][name][k] for k in ('sha256', 'bytes')} if name == 'CONFIG.PRG' else digest(path))
        if digest(path) != expected:
            raise RuntimeError('Native product differs from its receipt: ' + name)
        merge(records, {str(path): expected})
    merge(records, {str(setup_build / name): value for name, value in setup['products'].items()})
    verify(records)
    return selected, records


def assemble(coupled_path, setup_path, config_path, destination, *, runtime_media=False):
    selected, records = component_inputs(coupled_path, setup_path, config_path, runtime_media=runtime_media)
    names = RUNTIME_NATIVE if runtime_media else NATIVE
    # Refuse any preexisting destination rather than replacing user media or CFG.
    destination.mkdir()
    for name in names:
        shutil.copyfile(selected[name], destination / name)
        if digest(destination / name) != records[str(selected[name])]:
            raise RuntimeError('Candidate copy mismatch: ' + name)
    inventory = {name: digest(destination / name) for name in names}
    build = {'schema': 1, 'kind': 'DOS64_DEVELOPMENT_CANDIDATE_NOT_V1_RELEASE',
             'physical_release_qualified': False, 'V1_release_gates_closed': False,
             'minimum_REU_bytes': 4194304, 'native_assets': inventory,
             'runtime_media': runtime_media, 'floppy_FORMAT': runtime_media,
             'vendor_images_included': False, 'configured_home_included': False}
    atomic_json(destination / 'BUILD.json', build)
    (destination / 'README.txt').write_text(RUNTIME_README if runtime_media else README, encoding='ascii')
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


def build(out, *, runtime_media=False):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=out))
    records = {str(Path(__file__).resolve()): digest(__file__)}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for name in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'PYTHONPYCACHEPREFIX', 'PYTHONHOME',
                 'CC65_HOME', 'CC65_INC', 'CA65_INC', 'LD65_LIB', 'LD65_CFG',
                 'CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH', 'OBJC_INCLUDE_PATH',
                 'LIBRARY_PATH', 'COMPILER_PATH', 'GCC_EXEC_PREFIX',
                 'MAKEFLAGS', 'MFLAGS', 'MAKEOVERRIDES'):
        env.pop(name, None)
    phase = 'build coupled release'
    commands = []
    cold_flags = ['--cold-inventory', '--start20k', '--mnu56k', '--startup-diagnostics']
    steps = [
        ('coupled', 'start_ini_bundle.py', []),
        ('setup', 'setup_installer.py', ['--bundle-result', str(run / 'coupled/RESULT.json')]),
        ('config', 'config_generation.py', ['--bundle-result', str(run / 'coupled/RESULT.json')]),
    ]
    if runtime_media:
        steps = [
            ('runtime', 'runtime_media.py', ['--floppy-format']),
            ('coupled', 'cold_start.py', ['--runtime-result', str(run / 'runtime/RESULT.json')]),
            ('setup', 'setup_installer.py', ['--bundle-result', str(run / 'coupled/RESULT.json'), *cold_flags, '--file-diagnostics']),
            ('config', 'config_generation.py', ['--bundle-result', str(run / 'coupled/RESULT.json'), *cold_flags]),
        ]
    try:
        for name, script, extra in steps:
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
                                 run / 'config/RESULT.json', run / 'package', runtime_media=runtime_media)
        merge(records, inputs)
        phase = 'archive'
        zip_path = run / 'DOS64-candidate.zip'
        archive(run / 'package', zip_path, files)
        verify(records)
        result = {'status': 'passed', 'scope': 'COHERENT_SOURCE_BUILT_CANDIDATE_NOT_V1_ACCEPTANCE',
                  'run': str(run), 'package': str(run / 'package'), 'archive': str(zip_path),
                  'archive_identity': digest(zip_path), 'files': files, 'source_products': records,
                  'commands': commands, 'runtime_media': runtime_media,
                  'physical': False, 'V1_complete': False}
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
    parser.add_argument('--runtime-media', action='store_true',
                        help='Build twelve matched files with native media menu, FORMAT and cold recovery')
    args = parser.parse_args()
    report = build(args.out, runtime_media=args.runtime_media)
    print(report['archive'])
