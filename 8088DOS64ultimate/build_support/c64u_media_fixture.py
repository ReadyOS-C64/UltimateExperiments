"""Create a fresh, hash-verified DOS image fixture through development FTP.

No emulator runtime dependency. Never reuse a remote run directory, overwrite
an existing image, delete remote files or alter the original local image.
Root launches the CLI through the established Terminal-owned hardware workflow.
"""
import argparse
from datetime import datetime, timezone
import ftplib
import hashlib
import io
import json
from pathlib import Path
import re
import uuid
import zlib

BASE = '/usb1/DOS64_TEST'
LEAF = 'DOS33A.IMG'
MARKER = 'OWNER.JSON'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare_media(ftp_factory, source, run_id, out, expected_sha256):
    source, out = Path(source), Path(out)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', run_id):
        raise ValueError('Run id must be 1..64 lowercase letters/digits/underscore/hyphen')
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('Expected SHA256 must identify the independent source manifest')
    data = source.read_bytes()
    if len(data) != 360 * 1024 or digest(data) != expected_sha256:
        raise ValueError('Source must be the expected exact 360 KiB image')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Local evidence directory must be new or empty')
    out.mkdir(parents=True, exist_ok=True)
    remote = BASE + '/' + run_id
    record = {'schema': 1, 'status': 'running', 'source': str(source.resolve()),
              'source_sha256': expected_sha256, 'source_bytes': len(data),
              'source_crc32': zlib.crc32(data), 'remote_directory': remote,
              'native_path': remote + '/' + LEAF, 'created_directory': False,
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'limitations': ['Development FTP staging only; no native UCI or DOS acceptance',
                              'Owned fixture retained; no existing remote file is overwritten']}
    def save():
        (out / 'media-fixture.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    try:
        with ftp_factory() as ftp:
            # An existing parent is permitted; the run directory itself must be
            # created successfully before any STOR can occur. Never recover an
            # ambiguous existing run by trying to take ownership of it.
            try:
                ftp.mkd(BASE)
            except ftplib.error_perm:
                ftp.cwd(BASE)  # verify existing directory, session-local only
            ftp.mkd(remote)
            record['created_directory'] = True
            marker = json.dumps({'project': '8088DOS64ultimate', 'run_id': run_id,
                                 'nonce': str(uuid.uuid4()),
                                 'image_sha256': expected_sha256}, sort_keys=True).encode()
            ftp.storbinary('STOR ' + remote + '/' + MARKER, io.BytesIO(marker))
            check = bytearray()
            ftp.retrbinary('RETR ' + remote + '/' + MARKER, check.extend)
            if bytes(check) != marker:
                raise ValueError('Fresh ownership marker readback differs')
            record['marker_sha256'] = digest(marker)
            save()
            ftp.storbinary('STOR ' + record['native_path'], io.BytesIO(data))
            check.clear()
            ftp.retrbinary('RETR ' + record['native_path'], check.extend)
            record['remote_readback_bytes'] = len(check)
            record['remote_readback_sha256'] = digest(check)
            if bytes(check) != data:
                raise ValueError('Remote image readback differs from every original byte')
        if digest(source.read_bytes()) != expected_sha256:
            raise ValueError('Original local image changed during staging')
        record['original_source_unchanged'] = True
        record['status'] = 'verified'
    except Exception as exc:
        record['status'] = 'failed'
        record['error'] = repr(exc)
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', required=True)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--expected-sha256', required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    owned = Path(__file__).resolve().parents[1] / 'agentworking/runs'
    if not args.output.resolve().is_relative_to(owned.resolve()):
        ap.error('Evidence must remain within this project agentworking/runs')
    def connect():
        ftp = ftplib.FTP()
        ftp.connect(args.host, 21, timeout=20)
        ftp.login('anonymous', 'anonymous@')
        return ftp
    result = prepare_media(connect, args.source, args.run_id, args.output,
                           args.expected_sha256)
    print(json.dumps({k: result.get(k) for k in
                      ('status', 'native_path', 'source_sha256', 'source_crc32', 'error')}))
    return 0 if result['status'] == 'verified' else 1


if __name__ == '__main__':
    raise SystemExit(main())
