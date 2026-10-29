"""Read-only, byte-exact oracle for ordinary unpartitioned 1581 D81 images.

This deliberately does not use c1541's sequential reader. In a terminal sector,
link byte 1 is the last used byte index: 00/01 contains zero file bytes.
"""
from __future__ import annotations
from dataclasses import dataclass

SECTOR_BYTES = 256
SECTORS_PER_TRACK = 40
TRACKS = 80
IMAGE_BYTES = TRACKS * SECTORS_PER_TRACK * SECTOR_BYTES


class D81Error(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    name: bytes
    kind: int
    closed: bool
    locked: bool
    first: tuple[int, int]
    blocks: int
    directory_sector: tuple[int, int]
    slot: int
    raw: bytes


@dataclass(frozen=True)
class File:
    entry: Entry
    data: bytes
    # Retain sectors as well as logical bytes to prove existing files unchanged.
    sectors: tuple[tuple[int, int, bytes], ...]


class D81Image:
    def __init__(self, image: bytes):
        if len(image) != IMAGE_BYTES:
            raise D81Error(f'Expected {IMAGE_BYTES} D81 bytes, got {len(image)}')
        self.image = bytes(image)

    def sector(self, track: int, sector: int) -> bytes:
        if not 1 <= track <= TRACKS or not 0 <= sector < SECTORS_PER_TRACK:
            raise D81Error(f'Sector outside D81: {track}/{sector}')
        offset = ((track - 1) * SECTORS_PER_TRACK + sector) * SECTOR_BYTES
        return self.image[offset:offset + SECTOR_BYTES]

    def entries(self) -> tuple[Entry, ...]:
        header = self.sector(40, 0)
        position = tuple(header[:2])
        visited = set()
        result = []
        while position[0]:
            if position[0] != 40 or position[1] < 3:
                raise D81Error(f'Unsupported directory location: {position}')
            if position in visited:
                raise D81Error(f'Cyclic directory at {position}')
            visited.add(position)
            block = self.sector(*position)
            for slot in range(8):
                raw = block[slot * 32:(slot + 1) * 32]
                kind = raw[2] & 7
                if not kind:
                    continue
                name = raw[5:21].rstrip(b'\xa0')
                if not name:
                    raise D81Error(f'Empty directory name at {position}/{slot}')
                result.append(Entry(name, kind, bool(raw[2] & 0x80),
                                    bool(raw[2] & 0x40), tuple(raw[3:5]),
                                    int.from_bytes(raw[30:32], 'little'),
                                    position, slot, raw))
            position = tuple(block[:2])
        names = [entry.name for entry in result]
        if len(names) != len(set(names)):
            raise D81Error('Duplicate native filenames in directory')
        return tuple(result)

    def read(self, name: bytes, *, kind: int | None = None) -> File:
        matches = [entry for entry in self.entries() if entry.name == name]
        if not matches:
            raise D81Error(f'No exact native filename {name!r}')
        entry = matches[0]
        if not entry.closed:
            raise D81Error(f'Unclosed file {name!r}')
        if kind is not None and entry.kind != kind:
            raise D81Error(f'Wrong file type for {name!r}: {entry.kind}')
        if not entry.first[0]:
            raise D81Error(f'Closed file has no first sector: {name!r}')
        position = entry.first
        visited = set()
        sectors = []
        output = bytearray()
        while position[0]:
            if position in visited:
                raise D81Error(f'Cyclic file {name!r} at {position}')
            if position[0] == 40:
                raise D81Error(f'File uses directory track: {name!r} at {position}')
            visited.add(position)
            block = self.sector(*position)
            sectors.append((*position, block))
            if block[0]:
                output.extend(block[2:])
            else:
                if not block[1]:
                    raise D81Error(f'Invalid terminal used index for {name!r}')
                output.extend(block[2:block[1] + 1])
            position = tuple(block[:2])
        if len(sectors) != entry.blocks:
            raise D81Error(f'Block count mismatch for {name!r}: '
                           f'{entry.blocks} directory, {len(sectors)} actual')
        return File(entry, bytes(output), tuple(sectors))
