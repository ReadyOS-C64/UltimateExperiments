"""Generate exact linked C24 code witnesses for its optional ABI consumers."""
from pathlib import Path
import argparse
import binascii


def generate(image, output):
    raw = image.read_bytes()
    assert 32 <= len(raw) <= 4096, 'C24 payload outside the command slot'
    crc = binascii.crc_hqx(raw, 65535)
    output.mkdir(parents=True, exist_ok=True)
    for name, prefix in [('seed-witness.inc', 'SEED'), ('consumer-witness.inc', 'GSC_SEED')]:
        text = f'{prefix}_SIZE={len(raw)}\n{prefix}_CRC={crc}\n'
        path = output / name
        if not path.exists() or path.read_text() != text:
            path.write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    generate(args.image, args.output)
