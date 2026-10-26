"""Bind the CR leaf's font CRCs to the actual sealed native backend images."""
from pathlib import Path
import argparse
import binascii
import hashlib
import json
from bindings import verify

p = argparse.ArgumentParser()
p.add_argument('--base', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
base = a.base.resolve()
seal = verify(base/'build/editor.prg', base/'build/editor.lbl')
digest = bytes.fromhex(seal['digest'])
values, records = [], {}
for width, name, ident in ((4, 'grid80', 16), (5, 'grid60', 17)):
    image = (base/f'build/overlays/{name}.seo').read_bytes()
    raw = image[36:]
    assert len(raw) == 4096 and image[5:8] == bytes((0, ident, 0))
    assert image[20:36] == raw[:16] == digest
    assert binascii.crc_hqx(raw, 65535) == int.from_bytes(image[12:14], 'little')
    assert binascii.crc_hqx(image[:14]+image[16:36], 65535) == int.from_bytes(image[14:16], 'little')
    font = (base/f'assets/fonts/generated/narrow{width}.bin').read_bytes()
    assert len(font) == 1024 and raw[0x800:0xc00] == font
    crc = binascii.crc_hqx(font, 65535)
    values.append(f'FONT{width}_CRC={crc}')
    records[name] = dict(image_sha256=hashlib.sha256(image).hexdigest(),
                         font_sha256=hashlib.sha256(font).hexdigest(), crc=crc)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text('\n'.join(values)+'\n')
a.output.with_suffix('.json').write_text(json.dumps(dict(
    binding=seal['digest'], backends=records), indent=2)+'\n')
