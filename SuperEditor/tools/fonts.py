"""Reproducible local GEOS font extraction and native narrow-font generation."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'assets/fonts/generated'


def screen_ascii(code):
    if code == 0:
        return 0x40
    if 1 <= code <= 26:
        return code+0x60
    if code in (27, 29):
        return code+0x40
    if 32 <= code <= 63 or 65 <= code <= 90:
        return code
    return None


def png(path, width, height, pixels):
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    rows = b''.join(b'\0'+bytes(pixels[y*width:(y+1)*width]) for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))+
                     chunk(b'IDAT', zlib.compress(rows))+chunk(b'IEND', b''))


def atlas(path, glyphs, widths, height):
    width, rows = 16*20, 8*18
    pixels = [16]*(width*rows)
    for char in range(128):
        ox, oy = (char%16)*20+2, (char//16)*18+2
        for y in range(height):
            for x in range(min(widths[char],16)):
                if glyphs[char][y] & (0x8000 >> x):
                    pixels[(oy+y)*width+ox+x] = 238
    png(path, width, rows, pixels)


def generate():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rom = Path(os.environ.get('C64_CHARGEN', '/opt/homebrew/Cellar/vice/3.10/share/vice/C64/chargen-901225-01.bin'))
    raw = rom.read_bytes()
    assert len(raw) == 4096
    native = bytearray(raw[2048:3072])
    # The editor runs the lowercase set, whose line-art lower corners are
    # square. Graft in the upper/graphics set's visibly rounded PETSCII pair.
    native[0x6d*8:0x6e*8] = raw[0x4a*8:0x4b*8]
    native[0x7d*8:0x7e*8] = raw[0x4b*8:0x4c*8]
    # Shared full-width bitmap menu/status glyphs; normal128glyph charset.
    (OUTPUT/'native8.bin').write_bytes(native)
    # Four ink pixels in five-pixel pitch: preserve outside strokes and combine
    # two middle pairs. Explicit handcrafted 3x7 glyphs below serve dense mode.
    font5 = bytearray()
    for value in native:
        bits = [((value >> (7-x)) & 1) for x in range(8)]
        columns = [bits[1], bits[2] | bits[3], bits[4] | bits[5], bits[6]]
        font5.append(sum(bit << (7-x) for x,bit in enumerate(columns)))
    font4 = bytearray()
    for value in native:
        font4.append(sum(((value >> (7-x)) & 1) << (7-i) for i,x in enumerate([1,3,5])))
    definitions = (ROOT/'assets/fonts/narrow3x7.txt').read_text()
    replacements = {}
    for line in definitions.splitlines():
        if not line or (line.startswith('# ') and not set(line[2:]) <= set('.#/')):
            continue
        char, rows = line.split(' ', 1)
        patterns = rows.split('/')
        assert len(patterns) == 7 and all(len(row)==3 for row in patterns), char
        replacements[ord(char)] = bytes(sum((pixel=='#') << (7-i) for i,pixel in enumerate(row)) for row in patterns)+b'\0'
    for code in range(128):
        char = screen_ascii(code)
        if char in replacements:
            font4[code*8:(code+1)*8] = replacements[char]
            # Widen the hand-designed middle stem for the less dense 60 view.
            font5[code*8:(code+1)*8] = bytes((v&0x80) | ((v&0x40)>>0) |
                ((v&0x40)>>1) | ((v&0x20)>>1) for v in replacements[char])
    font4[32*8:33*8] = bytes(8)
    font5[32*8:33*8] = bytes(8)
    (OUTPUT/'narrow4.bin').write_bytes(font4)
    (OUTPUT/'narrow5.bin').write_bytes(font5)

    source = Path(os.environ.get('GEOS_BSW_SOURCE', str(
        ROOT.parent.parent/'GEOS20/reference/geos/kernal/bswfont/bswfont.s')))
    text = source.read_text()
    # Pin the original English .else branch, not Wheels or gateWay variants.
    assert text.count('\n.else\n') == 1
    branch = text.split('\n.else\n')[1].split('\n.endif')[0]
    bsw = bytes(int(value,16) for line in branch.splitlines()
                if line.lstrip().startswith('.byte')
                for value in re.findall(r'\$([0-9a-fA-F]{2})',line))
    baseline, stride, height, index_at, bits_at = struct.unpack('<BHBHH',bsw[:8])
    assert len(bsw) == bits_at+stride*height and height==9 and baseline==6
    assert index_at==8 and bits_at>index_at and (bits_at-index_at)%2==0
    offsets = [int.from_bytes(bsw[i:i+2],'little') for i in range(index_at,bits_at,2)]
    assert all(a<=b for a,b in zip(offsets,offsets[1:]))
    assert offsets[-1] <= stride*8
    widths, glyphs = [], []
    for code in range(128):
        asc = screen_ascii(code)
        if asc is None or not 0x20<=asc<0x20+len(offsets)-1:
            widths.append(8)
            glyphs.append([native[code*8+y]<<8 if y<8 else 0 for y in range(height)])
            continue
        index = asc-0x20
        start, end = offsets[index:index+2]
        advance = end-start
        assert 0<=advance<=16
        widths.append(advance)
        words = []
        for y in range(height):
            word = 0
            for x in range(advance):
                bit = start+x
                if bsw[bits_at+y*stride+bit//8] & (0x80 >> (bit%8)):
                    word |= 0x8000 >> x
            words.append(word)
        glyphs.append(words)
    (OUTPUT/'bsw9.bin').write_bytes(bytes(b for glyph in glyphs for word in glyph for b in [word>>8,word&255]))
    (OUTPUT/'bsw9-widths.bin').write_bytes(bytes(widths))
    (OUTPUT/'bsw9-original.bin').write_bytes(bsw)
    atlas(OUTPUT/'bsw9-atlas.png', glyphs, widths, height)
    atlas(OUTPUT/'narrow4-atlas.png', [[v<<8 for v in font4[c*8:(c+1)*8]] for c in range(128)], [4]*128,8)
    atlas(OUTPUT/'narrow5-atlas.png', [[v<<8 for v in font5[c*8:(c+1)*8]] for c in range(128)], [5]*128,8)
    row_addresses = [0x6000+(y//8)*320+(y%8) for y in range(200)]
    (OUTPUT/'bitmap-row-low.bin').write_bytes(bytes(v&255 for v in row_addresses))
    (OUTPUT/'bitmap-row-high.bin').write_bytes(bytes(v>>8 for v in row_addresses))
    manifest = dict(schema=1, bsw_source=str(source), bsw_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    original_font_bytes=len(bsw), baseline=baseline, height=height, stride=stride,
                    native_source=str(rom), native_sha256=hashlib.sha256(raw).hexdigest(),
                    narrow4_source='assets/fonts/narrow3x7.txt',
                    glyph_count=128, max_bsw_advance=max(widths),
                    provenance='Original English BSW/9 extracted locally; preserve source media notice',
                    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.glob('*.bin')})
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Fonts generated: {len(bsw)} BSW bytes, 128 mapped glyphs, baseline {baseline}, height {height}')


if __name__ == '__main__':
    generate()
