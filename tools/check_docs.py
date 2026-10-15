#!/usr/bin/env python3
"""Validate the publishable tree, including links, screenshots and disk downloads."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'DOCS'
errors = []

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []
        self.title = False
        self.sql_blocks = []
        self._sql = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'code' and 'language-sql' in attrs.get('class', '').split():
            self._sql = []
            if 'hljs' not in attrs.get('class', '').split():
                errors.append('SQL example is missing build-time highlighting')
        if tag == 'title': self.title = True
        if tag in ('video', 'audio', 'iframe'):
            errors.append(f'Unexpected media/embed element: {tag}')
        if 'id' in attrs:
            if attrs['id'] in self.ids: errors.append(f'Duplicate anchor: {attrs["id"]}')
            self.ids.add(attrs['id'])
        for key in ('href', 'src', 'poster'):
            if key in attrs: self.refs.append(attrs[key])
    def handle_data(self, data):
        if self._sql is not None: self._sql.append(data)
    def handle_endtag(self, tag):
        if tag == 'code' and self._sql is not None:
            self.sql_blocks.append(''.join(self._sql))
            self._sql = None

pages = {}
for file in DOCS.rglob('*.html'):
    page = Page()
    page.feed(file.read_text())
    pages[file] = page
    if not page.title: errors.append(f'{file.relative_to(DOCS)} has no title')
    markdown = file.with_suffix('.md')
    if markdown.exists():
        expected = [block.rstrip('\n') for block in re.findall(r'```sql\n([\s\S]*?)```', markdown.read_text())]
        if expected != page.sql_blocks:
            errors.append(f'{file.relative_to(DOCS)}: highlighted SQL differs from its Markdown source')

def check_ref(file, url, anchors=False):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc: return
    if parsed.path.startswith('/'):
        errors.append(f'{file.relative_to(DOCS)}: root-relative URL {url}')
        return
    target = (file.parent / unquote(parsed.path)).resolve() if parsed.path else file
    if not target.is_relative_to(DOCS):
        errors.append(f'{file.relative_to(DOCS)}: URL escapes published tree: {url}')
        return
    if not target.exists():
        errors.append(f'{file.relative_to(DOCS)}: missing destination {url}')
        return
    # Check exact case even when the local filesystem is case-insensitive.
    cursor = DOCS
    for part in target.relative_to(DOCS).parts:
        if part not in [p.name for p in cursor.iterdir()]:
            errors.append(f'{file.relative_to(DOCS)}: wrong destination case: {url}')
            break
        cursor = cursor / part
    if anchors and parsed.fragment and target in pages and unquote(parsed.fragment) not in pages[target].ids:
        errors.append(f'{file.relative_to(DOCS)}: missing anchor {url}')

for file, page in pages.items():
    for url in page.refs: check_ref(file, url, anchors=True)
for file in DOCS.rglob('*.md'):
    for url in re.findall(r'\]\(([^\s)]+)[^)]*\)', file.read_text()):
        check_ref(file, url)
for file in DOCS.rglob('*'):
    if not file.is_file(): continue
    if file.suffix.lower() in ['.mp4', '.webm', '.mov', '.mp3', '.wav', '.ogg']:
        errors.append(f'Bundled video/audio: {file.relative_to(DOCS)}')
    if file.suffix in ['.md', '.html', '.json', '.txt', '.css', '.js']:
        text = file.read_text()
        if re.search(r'/(?:Users/[^/\s]+|home/(?!web_user)[^/\s]+)', text):
            errors.append(f'Personal home path: {file.relative_to(DOCS)}')
for original, download in [
    ('ReadyFS/artifacts/readyfs/readyfs-overlay-lab.d81', 'readyfs-overlay-lab.d81'),
    ('ReadyFS/artifacts/readyfs/readyfs-lab.d81', 'readyfs-lab.d81'),
    ('ReuSQL64/build/rsql64_shell.d81', 'rsql64_shell.d81'),
]:
    a, b = ROOT / original, DOCS / 'downloads' / download
    if len(a.read_bytes()) != 819200: errors.append(f'Unexpected D81 size: {original}')
    if hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest():
        errors.append(f'Download differs from committed project image: {download}')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: {len(pages)} HTML pages, Markdown links, anchors, local assets, highlighted SQL preserved, no video or personal home paths, and 3 matching D81s.')
