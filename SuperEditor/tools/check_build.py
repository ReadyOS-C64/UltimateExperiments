"""Validate emitted image, named segments and ReadyOS reservation."""
from pathlib import Path
from bindings import verify
import hashlib
import json
import re
import argparse

ROOT = Path(__file__).resolve().parents[1]
build = ROOT / 'build'
parser = argparse.ArgumentParser()
parser.add_argument('--stem', default='supereditor')
args = parser.parse_args()
image = (build / f'{args.stem}.prg').read_bytes()
assert image[:2] == b'\x01\x08', 'PRG must load at $0801'
end = 0x0801 + len(image) - 2
assert end <= 0x4000, f'cold image reaches display RAM: ${end:04x}'
symbols = {}
for line in (build / f'{args.stem}.lbl').read_text().splitlines():
    m = re.match(r'al ([0-9A-Fa-f]+) \.([\w]+)', line)
    if m:
        symbols[m[2]] = int(m[1], 16)
assert symbols['se_entry'] == 0x1000
assert symbols['se_diagnostics'] == 0xC000
assert symbols['__BSS_RUN__'] + symbols['__BSS_SIZE__'] <= 0xC600
segments = []
for line in (build / f'{args.stem}.map').read_text().splitlines():
    m = re.fullmatch(r'(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+\S+', line.strip())
    if m:
        name, start, stop, size = m.groups()
        start, stop, size = (int(v, 16) for v in (start, stop, size))
        assert stop < 0xC600 or start > 0xC9FF, f'{name} overlaps ReadyOS'
        if name == 'ZEROPAGE' and args.stem == 'editor':
            # The versioned standalone snapshot copies exactly 0002..0019.
            # A new resident seal alone must not authorize omitted ZP bytes.
            assert (start, stop, size) == (2, 0x19, 24), 'lifecycle ABI requires exact 24-byte ZP extent'
        if name == 'COLD':
            assert 0x080D <= start <= stop < 0x1000, 'cold helpers escaped BOOT memory'
        if name == 'COLD' and symbols.get('se_probe_original')==0x0F00:
            assert stop < 0x0F00, 'editor cold code overlaps REU saved probe bytes'
        if name == 'VIEWSTATE':
            assert 0x8C00 <= start <= stop < 0x8D00, 'view state escaped its workspace'
        if name == 'OVERLAY_CATALOG':
            capacity = symbols['se_overlay_capacity']
            fixed_entry = symbols.get('se_overlay_fixed_entry', 0)
            assert fixed_entry in (0, 1), 'invalid overlay entry policy'
            assert symbols.get('se_overlay_header_fixed_entry', 0) == fixed_entry, 'cache/header entry policy mismatch'
            arrays = 6 if fixed_entry else 8
            assert size == arrays * capacity, 'overlay catalog array/limit mismatch'
            assert 0 < capacity <= (64 if fixed_entry else 24), 'overlay catalog exceeds asset bank capacity'
            if fixed_entry and capacity > 32:
                assert start == 0xCA00 and stop <= 0xCB7F, 'editor catalog escaped second warm extent'
                if args.stem == 'editor':
                    assert capacity == 51, 'editor catalog capacity must equal its 51 packaged assets'
                    assert size == 306 and stop == 0xCB31, 'editor51 catalog must occupy exactly CA00..CB31'
                elif capacity == 64:
                    assert size == 384 and stop == 0xCB7F, 'editor64 catalog must occupy CA00..CB7F'
                assert symbols.get('se_overlay_stage') == 0x5000, 'editor runtime stage must preserve executable slots'
                assert symbols.get('se_overlay_asset_count') == 4, 'editor64 catalog needs four logical asset handles'
            else:
                assert start == 0x7F40 and stop <= 0x7FFF, 'overlay catalog escaped undisplayed bitmap tail'
        if name == 'SETTINGS_STATE':
            assert (start,stop,size) == (0xCB80,0xCBBF,64), 'editor settings escaped second warm extent'
        if name == 'FONT_STORE_STATE':
            assert (start,stop,size)==(0xCBC0,0xCBFF,64), 'font descriptor escaped second warm extent'
        if name == 'PREVIEW_STATE':
            assert (start,stop,size)==(0xCC00,0xCFFF,1024), 'preview state escaped second warm extent'
        if name == 'STYLE_DESCRIPTOR':
            assert 0x8C00 <= start <= stop < 0x8D00, 'style descriptor escaped view workspace'
        if name == 'STYLE_PLAN':
            assert start == 0x4400 and stop == 0x476F, 'source40 style plane overlaps display work'
        if name == 'STYLE_CHECKPOINT':
            assert 0x4770 <= start <= stop < 0x4800, 'style checkpoint overlaps font RAM'
        if name in ('STYLE_STATE', 'SM_STATE', 'FOLD_SOURCE_STATE'):
            assert 0x8D00 <= start <= stop < 0x9180, 'style phase escaped shared workspace'
        fold_segments = {'FOLD_STATE': (0x8D00,197),
                         'FOLD_BUILD_STATE': (0x8E60,89),
                         'FOLD_BUFFER': (0x8EB9,32),
                         'FOLD_BUILD_BUFFER': (0x8F36,160)}
        if name in fold_segments:
            expected_start, expected_size = fold_segments[name]
            assert (start,size)==(expected_start,expected_size), f'{name} escaped owner3 phase ABI'
            assert stop < 0x9180, 'fold phase escaped shared workspace'
            assert symbols['se_sm_state']==0x8E11 and symbols['se_fs_state']==0x8EE0, 'fold source/parser aliases moved'
        if name == 'LINEINDEX':
            assert 0x8D00 <= start <= stop < 0x9180, 'line checkpoints escaped workspace'
        if name == 'FILESTATE':
            assert start == 0x8D00 and stop < 0x9180, 'file phase union escaped workspace'
            assert 0xC000 <= symbols['se_f_owner'] < 0xC600, 'file union owner must live outside union'
        if name == 'NAVSTATE':
            assert 0x9180 <= start <= stop < 0x9200, 'navigation frame overlaps hot gap'
        if name == 'DOCSTATE':
            assert 0x9A00 <= start <= stop < 0x9E00, 'document state escaped its protected workspace'
        if name == 'OBJECTS':
            assert 0x9E00 <= start <= stop < 0xA000, 'object registry escaped its protected workspace'
        segments.append(dict(name=name, start=start, end=stop, size=size))
report = dict(schema=1, sha256=hashlib.sha256(image).hexdigest(), prg_bytes=len(image),
              cold_start=0x0801, cold_end_exclusive=end, entry=symbols['se_entry'],
              state_bytes=symbols['__BSS_SIZE__'], segments=segments,
              readyos_reserved=[0xC600, 0xC9FF], symbols=symbols)
if 'se_overlay_binding_digest' in symbols:
    report['resident_binding']=verify(build/f'{args.stem}.prg',build/f'{args.stem}.lbl')
(build / ('build-report.json' if args.stem=='supereditor' else f'{args.stem}-report.json')).write_text(json.dumps(report, indent=2)+'\n')
print(f'Build checked: {len(image)} PRG bytes; cold end ${end:04X}; '
      f'{report["state_bytes"]} state bytes; ReadyOS reservation clear')
