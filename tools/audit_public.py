#!/usr/bin/env python3
"""Check tracked publication files and explicit DOS64 download allowlists.

Audits the current tree, not Git history. Never scans ignored working records.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / '8088DOS64ultimate'
PRIVATE = re.compile(rb'/Users/[A-Za-z0-9_.-]+/')
LINUX_HOME = re.compile(rb'/home/[A-Za-z0-9_.-]+/')
NATIVE = {'SETUP.PRG', 'SETUP.FAT', 'SETUP.PUB', 'CONFIG.PRG', 'DOS64.PRG',
          'DOS64.REL', 'DOS64.MNU', 'START.TPL', 'START.REL', 'START.INO',
          'START.RCV', 'START.RFW'}
PACKAGE = NATIVE | {'README.txt', 'BUILD.json', 'SHA256SUMS', 'DOS64.INI.example'}
IMAGES = {'8088DOS64ultimate/examples/EXAMPLES.IMG', 'DOCS/downloads/DOS64-examples.img'}
errors = []
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1]
for name in files:
    path = Path(name)
    if any(re.fullmatch('agents?working', part, re.I) for part in path.parts):
        errors.append(f'Working records tracked: {name}')
    if path.suffix.lower() in ('.log', '.stdout', '.stderr'):
        errors.append(f'Execution log tracked: {name}')
    if name.startswith('8088DOS64ultimate/reference/'):
        errors.append(f'Vendor input tracked: {name}')
    if name.startswith(('8088DOS64ultimate/', 'DOCS/dos64/', 'DOCS/downloads/DOS64')):
        if path.suffix.lower() in ('.img', '.ima', '.iso') and name not in IMAGES:
            errors.append(f'Unapproved disk image: {name}')
        if path.name.upper() in ('IO.SYS', 'MSDOS.SYS', 'COMMAND.COM', 'GWBASIC.EXE',
                                'TPC.EXE', 'TURBO.EXE', 'TPX.EXE', 'TURBO.TPL'):
            errors.append(f'Vendor application: {name}')
    if (ROOT / name).is_dir():
        errors.append(f'Unexpected tracked directory/link: {name}')
        continue
    body = (ROOT / name).read_bytes()
    # /home/... in tests denotes synthetic Ultimate filesystem fixtures.
    if PRIVATE.search(body) or ('/tests/' not in name and LINUX_HOME.search(body)):
        errors.append(f'Personal home path: {name}')

archives = [P / 'downloads/DOS64-development.zip', ROOT / 'DOCS/downloads/DOS64-development.zip']
for path in archives:
    if not path.exists():
        errors.append(f'Missing package: {path.relative_to(ROOT)}')
        continue
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != PACKAGE or len(archive.namelist()) != len(PACKAGE):
            errors.append('Package must contain exactly twelve assets and four metadata files')
        if archive.testzip() is not None:
            errors.append('Package CRC failure')
        build = json.loads(archive.read('BUILD.json'))
        if build['vendor_images_included'] or build['configured_home_included'] or build['physical_release_qualified']:
            errors.append('Incorrect package scope/qualification')
        for name in NATIVE:
            body = archive.read(name)
            if build['native_assets'][name] != {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}:
                errors.append(f'Package native hash/size: {name}')
        for name in archive.namelist():
            if PRIVATE.search(archive.read(name)):
                errors.append(f'Personal path inside package: {name}')

super_archives = [ROOT / 'SuperEditor/releases/SuperEditor-preview.zip',
                  ROOT / 'DOCS/downloads/SuperEditor-preview.zip']
for path in super_archives:
    if not path.exists():
        errors.append(f'Missing package: {path.relative_to(ROOT)}')
        continue
    with zipfile.ZipFile(path) as archive:
        expected = {'README.txt', 'SUPEREDITOR.D81', 'BUILD.json', 'SHA256SUMS'}
        if set(archive.namelist()) != expected or len(archive.namelist()) != len(expected):
            errors.append('SuperEditor package must contain exactly four approved assets')
        if archive.testzip() is not None:
            errors.append('SuperEditor package CRC failure')
        build = json.loads(archive.read('BUILD.json'))
        disk = archive.read('SUPEREDITOR.D81')
        if len(disk) != 819200 or build['disk']['sha256'] != hashlib.sha256(disk).hexdigest():
            errors.append('SuperEditor D81 metadata mismatch')
        for name in archive.namelist():
            body = archive.read(name)
            if PRIVATE.search(body) or LINUX_HOME.search(body):
                errors.append(f'Personal path inside SuperEditor package: {name}')

sys.path.insert(0, str(P / 'build_support'))
from dos_disk_inspect import Volume
from example_disk import build as example_disk, NAMES
for name in IMAGES:
    path = ROOT / name
    if not path.exists():
        errors.append(f'Missing example image: {name}')
        continue
    body = path.read_bytes()
    if body != example_disk(P / 'examples') or set(Volume(body).payloads) != set(NAMES):
        errors.append(f'Example image differs from own-file allowlist: {name}')

if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: {len(files)} tracked files; no working records/logs/personal home paths; '
      'two exact native-package copies and two vendor-free example-image copies. Git history is a separate audit.')
