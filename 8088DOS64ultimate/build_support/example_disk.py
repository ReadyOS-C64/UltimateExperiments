"""Build a deterministic 360 KiB FAT12 disk containing only our examples."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
from dos_fat_populate import Populate
from dos_disk_inspect import Volume

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('README.TXT', 'RIPPLE.PAS', 'RIPPLE.EXE', 'HANGMAN.BAS')


def build(folder):
    image = bytearray(368640)
    image[:11] = b'\xeb\x3c\x90DOS64   '
    struct.pack_into('<HBHBHHBH', image, 11, 512, 2, 1, 2, 112, 720, 0xfd, 2)
    struct.pack_into('<HHI', image, 24, 9, 2, 0)
    # Original boot-error stub: BIOS teletype a message, then halt. No DOS code.
    stub = bytes.fromhex('b800008ed8be587cbb0700b40eac84c07404cd10ebf7faf4ebfd')
    assert len(stub) == 26
    image[62:88] = stub
    message = b'Data disk - boot DOS from A.\r\n\0'
    image[88:88 + len(message)] = message
    image[510:512] = b'\x55\xaa'
    for offset in (512, 1536):
        image[offset:offset + 3] = b'\xfd\xff\xff'
    writer = Populate(bytes(image))
    expected = {name: (folder / name).read_bytes() for name in NAMES}
    for name, data in expected.items():
        writer.put(name, data)
    result, _ = writer.finish()
    # Independent read-only parser checks mirrors, chains, lost/cross allocations.
    assert Volume(result).payloads == expected
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'examples/EXAMPLES.IMG')
    args = parser.parse_args()
    data = build(ROOT / 'examples')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(json.dumps({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'files': list(NAMES), 'vendor_media_template': False}))
