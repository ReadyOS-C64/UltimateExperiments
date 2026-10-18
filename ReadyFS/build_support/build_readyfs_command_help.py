#!/usr/bin/env python3
"""Pack readable console help into the existing 4 KiB presentation sidecar.

Bounded-depth byte-pair tokens expand only while printing HELP. Literal C
characters retain cc65's PETSCII character mapping; token bytes are numeric.
No runtime heap, extra REU bank, or per-keystroke decompression is involved.
"""
from collections import Counter
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
records = json.loads((ROOT/'docs/command-help.json').read_text())
assert [r['id'] for r in records] == list(range(43))
texts = []
for r in records:
    assert r['id'] == 0 or len(r['examples']) >= 2
    text = r['usage'] + '\r\n'
    if r['examples']:
        text += 'examples:\r\n' + '\r\n'.join(r['examples']) + '\r\n'
    assert text == text.lower() and all(ord(c) < 128 for c in text)
    texts.append(text.encode('ascii'))
packed = [list(s) for s in texts]
pairs = []
depth = [0]*128
for token in range(128,256):
    counts = Counter(p for s in packed for p in zip(s,s[1:])
                     if max(depth[p[0]],depth[p[1]]) < 8)
    if not counts: break
    pair, count = counts.most_common(1)[0]
    if count <= 3: break
    pairs.append(pair); depth.append(1+max(depth[pair[0]],depth[pair[1]]))
    for n,s in enumerate(packed):
        out=[];i=0
        while i<len(s):
            if i+1<len(s) and (s[i],s[i+1])==pair:
                out.append(token);i+=2
            else: out.append(s[i]);i+=1
        packed[n]=out

def expand(t):
    if t < 128:return bytes([t])
    a,b=pairs[t-128];return expand(a)+expand(b)
assert all(b''.join(expand(t) for t in s)==original
           for s,original in zip(packed,texts))
def literal(t):
    if t>=128:return str(t)
    return "'"+{13:r'\r',10:r'\n',39:r"\'",92:r'\\'}.get(t,chr(t))+"'"
lines=['/* Generated from docs/command-help.json; do not edit. */',
       'static const unsigned char help_pairs[][2] = {']
lines += ['    {'+', '.join(map(literal,p))+'},' for p in pairs]
lines.append('};')
for n,s in enumerate(packed):
    lines += [f'static const unsigned char help_{n}[] = {{',
              '    '+','.join(map(literal,s))+',0', '};']
lines += ['static const unsigned char * const topics[] = {',
          '    '+','.join('help_'+str(n) for n in range(43)), '};','']
(ROOT/'src/apps/readyfs/readyfs_help_data.h').write_text('\n'.join(lines))
print(json.dumps({'topics':len(records),'original_bytes':sum(map(len,texts)),
                  'packed_bytes':sum(map(len,packed))+43+len(pairs)*2+86,
                  'max_expansion_depth':max(depth)}))
