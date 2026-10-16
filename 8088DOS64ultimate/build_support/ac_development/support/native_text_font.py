"""Deterministic, offline CC0 Unscii8 -> CP437 native asset transformation."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/'assets/native-text'
def generate():
 manifest=json.loads((ASSET/'provenance.json').read_text())
 source=(ASSET/'unscii-8.hex').read_bytes()
 if hashlib.sha256(source).hexdigest()!=manifest['files']['unscii-8.hex']:
  raise ValueError('Pinned source mismatch')
 glyphs={int(a,16):bytes.fromhex(b) for a,b in (line.split(':') for line in source.decode().splitlines())}
 original={int(i):bytes.fromhex(b) for i,b in manifest['original_replacements'].items()}
 data=b''.join(original[i] if i in original else glyphs[u] for i,u in enumerate(manifest['mapping']))
 if len(data)!=2048:raise ValueError('Font must have exactly 256 eight-row glyphs')
 if hashlib.sha256(data).hexdigest()!=manifest['files']['cp437-unscii8.bin']:raise ValueError('Derived asset mismatch')
 return data
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();data=generate();dest=ASSET/'cp437-unscii8.bin'
 if a.check:
  if dest.read_bytes()!=data:raise ValueError('Checked-in font differs')
 else:dest.write_bytes(data)
 print(hashlib.sha256(data).hexdigest())
