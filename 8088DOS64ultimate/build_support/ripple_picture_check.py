"""Offline verification of the guest's finished RIPPLE text picture.

Compare every guest cell before the separate native-renderer/VIC pixel check.
No device access, image editing or replacement screen generation.
"""
import argparse
import json
from pathlib import Path


def check(directory: Path) -> dict:
    captures = sorted(directory.glob('*-Ripple-finished-drawing-CGA.bin'))
    assert len(captures) == 1, 'Require exactly one finished-picture capture'
    capture = captures[0]
    tag = capture.name[:-8]
    bda = (directory / (tag + '-BDA.bin')).read_bytes()
    assert bda[0x49] == 1, '40-column colour text mode'
    assert int.from_bytes(bda[0x4a:0x4c], 'little') == 40
    actual = capture.read_bytes()
    assert len(actual) == 2000
    palette = (1, 5, 4, 12, 14, 15, 11, 9)
    expected = bytearray(b' \x07' * 1000)
    caption = b'RIPPLE - press a key'
    for column, character in enumerate(caption):
        expected[column * 2] = character
    for row in range(1, 25):
        for column in range(40):
            left = ((column - 11) ** 2 + (row - 12) ** 2) // 6
            right = ((column - 28) ** 2 + (row - 12) ** 2) // 6
            cell = 2 * (40 * row + column)
            expected[cell:cell + 2] = bytes((219, palette[(left ^ right) % 8]))
    for cell in range(1000):
        lo = cell * 2
        assert actual[lo:lo + 2] == expected[lo:lo + 2], (
            'Guest cell mismatch', cell % 40, cell // 40,
            actual[lo:lo + 2].hex(), expected[lo:lo + 2].hex())
    return {'status': 'passed', 'capture': str(capture.resolve()),
            'mode': '40-column 16-colour text', 'cells_compared': 1000,
            'picture_blocks': 960, 'selected_guest_colours': list(palette),
            'separate_native_RAM_and_VIC_pixel_check_required': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.directory), indent=2))
