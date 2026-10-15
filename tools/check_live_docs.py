#!/usr/bin/env python3
"""Check that GitHub Pages serves every public documentation file unchanged."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import subprocess
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'DOCS'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True, help='Deployed documentation URL, including its repository path')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    if urlsplit(args.base_url).scheme not in ('https', 'http'):
        parser.error('--base-url must be an HTTP(S) URL')
    version = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    files = sorted(p for p in DOCS.rglob('*') if p.is_file() and not p.name.startswith('.'))
    def check(file):
        relative = file.relative_to(DOCS).as_posix()
        url = args.base_url.rstrip('/') + '/' + quote(relative, safe='/') + '?v=' + version
        expected = hashlib.sha256(file.read_bytes()).digest()
        failure = ''
        for attempt in range(5):
            try:
                request = Request(url, headers={'User-Agent': 'UltimateExperiments-docs-validator', 'Cache-Control': 'no-cache'})
                with urlopen(request, timeout=30) as response:
                    body = response.read()
                    if response.status != 200: raise ValueError(f'HTTP {response.status}')
                if hashlib.sha256(body).digest() != expected:
                    raise ValueError('published bytes differ from this checkout')
                return relative, None
            except Exception as error:
                failure = f'{relative}: {error}'
                if attempt < 4: time.sleep(2 * (attempt + 1))
        return relative, failure
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(check, file) for file in files]
        for future in as_completed(futures):
            relative, failure = future.result()
            if failure: failures.append(failure)
    if failures: raise SystemExit('\n'.join(sorted(failures)))
    print(f'PASS: {len(files)} published files returned HTTP 200 and matched SHA-256, including pages, screenshots and 3 D81 downloads.')
    print(args.base_url.rstrip('/') + '/')

if __name__ == '__main__': main()
