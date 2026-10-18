#!/usr/bin/env python3
"""Generate a read-only FAT12 oracle for the unchanged DOS disk-1 boot lane.

This never loads guest RAM or interprets guest instructions. IO.SYS comes from
FAT12 chain traversal; the additional raw extent models this sector's observed
read-to-track-end policy. The target test independently records the actual reads.
"""
import argparse
import json
from pathlib import Path
from dos_image import Fat12Image, canonical_json, sha256

SOURCE = 'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img'
SOURCE_SHA = 'bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb'
IO_SHA = 'b0bbdb145bd201c025b7921542cc3ee5244b47cdbc06be849f0d9ce8ba46a9c4'


def oracle(source=SOURCE):
    source = Path(source)
    image = Fat12Image.from_path(source)
    if sha256(image.data) != SOURCE_SHA:
        raise ValueError('immutable source SHA-256 mismatch')
    entry = image.find('IO.SYS')
    payload = image.read_file('IO.SYS')
    if sha256(payload) != IO_SHA:
        raise ValueError('IO.SYS FAT12 extraction SHA-256 mismatch')
    chain = image.cluster_chain(entry)
    lbas = [image.cluster_lba(c) for c in chain]
    spc = image.bpb['sectors_per_cluster']
    if lbas != list(range(lbas[0], lbas[0] + len(chain) * spc, spc)):
        raise ValueError('this unchanged boot sector requires contiguous IO.SYS')
    rounded = (len(payload) + 511) // 512
    spt = image.bpb['sectors_per_track']
    end = ((lbas[0] + rounded + spt - 1) // spt) * spt
    extent = image.read_sectors(lbas[0], end - lbas[0])
    if extent[:len(payload)] != payload:
        raise ValueError('FAT12 payload differs from boot raw extent')
    if source.read_bytes() != image.data:
        raise ValueError('source changed during read-only operation')
    return {
        'schema': 1, 'source_path': str(source), 'source_bytes': len(image.data),
        'source_sha256': SOURCE_SHA, 'boot_sector_sha256': sha256(image.data[:512]),
        'oracle': 'Independent read-only FAT12 traversal; no guest DOS replacement',
        'kernel_name': entry.name, 'kernel_bytes': len(payload),
        'kernel_sha256': IO_SHA, 'kernel_clusters': list(chain),
        'kernel_cluster_lbas': lbas, 'kernel_rounded_sectors': rounded,
        'kernel_lba': lbas[0], 'load_physical': 0x700,
        'handoff_cs': 0x70, 'handoff_ip': 0,
        'sectors_per_track': spt, 'heads': image.bpb['heads'],
        'raw_extent_sectors': end - lbas[0], 'raw_extent_bytes': len(extent),
        'raw_extent_sha256': sha256(extent), 'raw_extent_hex': extent.hex(),
        'limits': 'Kernel-entry byte oracle only. COMMAND.COM prompt and complete DOS boot are separate milestones.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=SOURCE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = canonical_json(oracle(args.source))
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
