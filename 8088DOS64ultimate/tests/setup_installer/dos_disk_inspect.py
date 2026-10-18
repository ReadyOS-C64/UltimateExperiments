"""Read-only DOS 3.x FAT12/FAT16 raw floppy/MBR inspection; no repair or writing.

FAT32, extended partitions, long names, and non-512-byte sectors are outside
this inspector's scope. All filesystem metadata and allocation chains are
checked before any extracted payload is returned. Unit fixtures are not boot
fixtures; genuine bootable media is created only by dos_hd_fixture.py.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_geometry(geometry):
    if len(geometry) != 3 or not all(isinstance(x, int) for x in geometry):
        raise ValueError("geometry requires cylinders, heads, sectors")
    c, h, s = geometry
    if not (1 <= c <= 1024 and 1 <= h <= 256 and 1 <= s <= 63):
        raise ValueError("geometry outside BIOS CHS limits")
    return c, h, s


def chs_to_lba(c, h, s, geometry):
    cylinders, heads, sectors = validate_geometry(geometry)
    if not (0 <= c < cylinders and 0 <= h < heads and 1 <= s <= sectors):
        raise ValueError("CHS outside geometry")
    return (c * heads + h) * sectors + s - 1


def lba_to_chs(lba, geometry):
    cylinders, heads, sectors = validate_geometry(geometry)
    if not 0 <= lba < cylinders * heads * sectors:
        raise ValueError("LBA outside geometry")
    track, sector = divmod(lba, sectors)
    cylinder, head = divmod(track, heads)
    return cylinder, head, sector + 1


def decode_chs(data):
    if len(data) != 3:
        raise ValueError("encoded CHS requires three bytes")
    return data[2] | ((data[1] & 0xc0) << 2), data[0], data[1] & 63


class Volume:
    def __init__(self, data):
        self.data = bytes(data)
        if len(data) < 512 or data[510:512] != b"\x55\xaa":
            raise ValueError("volume size/signature")
        (bps, spc, reserved, fats, roots, total, media, spf) = struct.unpack_from("<HBHBHHBH", data, 11)
        spt, heads, hidden = struct.unpack_from("<HHI", data, 24)
        if (bps != 512 or spc not in (1, 2, 4, 8, 16, 32, 64, 128)
                or not reserved or fats != 2 or not roots or not spf
                or not total or len(data) != total * bps or not 0xf0 <= media <= 0xff):
            raise ValueError("unsupported/inconsistent DOS 3.x BPB")
        self.bps, self.spc = bps, spc
        self.root_sector = reserved + fats * spf
        root_sectors = (roots * 32 + bps - 1) // bps
        self.data_sector = self.root_sector + root_sectors
        if self.data_sector >= total:
            raise ValueError("filesystem metadata outside volume")
        self.clusters = (total - self.data_sector) // spc
        self.width = 12 if self.clusters < 4085 else 16
        if not 1 <= self.clusters < 65525:
            raise ValueError("unsupported FAT cluster count")
        self.eoc = 0xff8 if self.width == 12 else 0xfff8
        self.bad = 0xff7 if self.width == 12 else 0xfff7
        self.reserved_min = 0xff0 if self.width == 12 else 0xfff0
        self.fat = data[reserved * bps:(reserved + spf) * bps]
        mirror = data[(reserved + spf) * bps:(reserved + 2 * spf) * bps]
        if self.fat != mirror or len(self.fat) * 8 // self.width < self.clusters + 2:
            raise ValueError("FAT size/copies")
        if self.entry(0) != ((0xf00 if self.width == 12 else 0xff00) | media) or self.entry(1) < self.eoc:
            raise ValueError("FAT reserved entries")
        self.bpb = dict(bytes_per_sector=bps, sectors_per_cluster=spc,
                        reserved_sectors=reserved, fats=fats, root_entries=roots,
                        total_sectors=total, media=media, sectors_per_fat=spf,
                        sectors_per_track=spt, heads=heads, hidden_sectors=hidden,
                        oem=data[3:11].decode("ascii", errors="replace"))
        self.owned = set()
        self.files, self.payloads, self.directories, self.labels = [], {}, [], []
        root = data[self.root_sector * bps:self.data_sector * bps][:roots * 32]
        self._directory(root, "", 0, 0, depth=0)
        allocated = {c for c in range(2, self.clusters + 2) if self.entry(c) != 0}
        bad = {c for c in allocated if self.entry(c) == self.bad}
        if allocated != self.owned | bad:
            raise ValueError("lost/invalid FAT allocation")
        self.free_clusters = self.clusters - len(allocated)
        self.bad_clusters = sorted(bad)

    def entry(self, cluster):
        if self.width == 16:
            return struct.unpack_from("<H", self.fat, 2 * cluster)[0]
        value = struct.unpack_from("<H", self.fat, 3 * cluster // 2)[0]
        return value >> 4 if cluster & 1 else value & 0xfff

    def chain(self, first, length=None):
        if first == 0 and length == 0:
            return [], b""
        chain, data = [], bytearray()
        cluster = first
        while cluster < self.eoc:
            if (cluster < 2 or cluster >= self.clusters + 2
                    or cluster >= self.reserved_min or cluster in self.owned):
                raise ValueError("invalid/crosslinked/cyclic chain")
            self.owned.add(cluster)
            chain.append(cluster)
            offset = (self.data_sector + (cluster - 2) * self.spc) * self.bps
            data.extend(self.data[offset:offset + self.spc * self.bps])
            cluster = self.entry(cluster)
        if not chain or (length is not None and len(chain) != (length + self.spc * self.bps - 1) // (self.spc * self.bps)):
            raise ValueError("chain length/EOC")
        return chain, bytes(data if length is None else data[:length])

    def _directory(self, data, prefix, own_cluster, parent_cluster, depth):
        if depth > 64:
            raise ValueError("directory depth exceeds inspection bound")
        names = set()
        dots = set()
        for offset in range(0, len(data), 32):
            ent = data[offset:offset + 32]
            if len(ent) < 32 or ent[0] == 0:
                break
            if ent[0] == 0xe5:
                continue
            attr = ent[11]
            if attr & 0xc0 or attr == 0x0f or attr & 0x18 == 0x18:
                raise ValueError("unsupported directory attributes/long names")
            raw_name = (b"\xe5" + ent[1:11]) if ent[0] == 0x05 else ent[:11]
            base = raw_name[:8].decode("cp437").rstrip()
            ext = raw_name[8:].decode("cp437").rstrip()
            name = base + (("." + ext) if ext else "")
            first, length = struct.unpack_from("<HI", ent, 26)
            if name in names or not base or any(c in name for c in "/\\\x00"):
                raise ValueError("invalid/duplicate DOS short name")
            names.add(name)
            if name in (".", ".."):
                expected = own_cluster if name == "." else parent_cluster
                if not prefix or attr != 0x10 or first != expected or length:
                    raise ValueError("invalid dot directory")
                dots.add(name)
                continue
            if attr & 8:
                if prefix or first or length:
                    raise ValueError("invalid volume label")
                self.labels.append(raw_name.decode("cp437").rstrip())
                continue
            if not length and not attr & 0x10 and first:
                raise ValueError("zero-length allocation")
            chain, payload = self.chain(first, None if attr & 0x10 else length)
            path = prefix + name
            if attr & 0x10:
                if length:
                    raise ValueError("nonzero directory length")
                self.directories.append(dict(name=path, first_cluster=first, clusters=chain))
                self._directory(payload, path + "/", first, own_cluster, depth + 1)
            else:
                self.payloads[path] = payload
                self.files.append(dict(name=path, bytes=length, attributes=attr,
                                       first_cluster=first, clusters=chain, sha256=sha(payload)))
        if prefix and dots != {".", ".."}:
            raise ValueError("missing dot directories")

    def report(self):
        return dict(bytes=len(self.data), sha256=sha(self.data), bpb=self.bpb,
                    fat_bits=self.width, fat_copies_equal=True,
                    data_sector_in_volume=self.data_sector, data_clusters=self.clusters,
                    free_clusters=self.free_clusters,
                    free_bytes=self.free_clusters * self.spc * self.bps,
                    bad_clusters=self.bad_clusters, directories=self.directories,
                    labels=self.labels, files=self.files,
                    trailing_unclustered_sectors=(self.bpb["total_sectors"] - self.data_sector) % self.spc)


def inspect(raw, geometry):
    c, h, s = validate_geometry(geometry)
    if len(raw) != c * h * s * 512:
        raise ValueError("raw size/geometry mismatch")
    if raw[510:512] != b"\x55\xaa":
        raise ValueError("MBR signature")
    entries = [raw[446 + i * 16:462 + i * 16] for i in range(4)]
    used = [e for e in entries if any(e)]
    if len(used) != 1:
        raise ValueError("require one primary partition; empty entries must be zero")
    e = used[0]
    start, count = struct.unpack_from("<II", e, 8)
    if e[0] != 0x80 or e[4] not in (1, 4) or not start or not count or start + count > len(raw) // 512:
        raise ValueError("partition bounds/type/active")
    begin, end = decode_chs(e[1:4]), decode_chs(e[5:8])
    if chs_to_lba(*begin, geometry) != start or chs_to_lba(*end, geometry) != start + count - 1:
        raise ValueError("CHS/LBA disagreement")
    volume = Volume(raw[start * 512:(start + count) * 512])
    bpb = volume.bpb
    if (bpb["total_sectors"] != count or bpb["hidden_sectors"] != start
            or (bpb["heads"], bpb["sectors_per_track"]) != (h, s)
            or bpb["media"] != 0xf8 or volume.width != (12 if e[4] == 1 else 16)):
        raise ValueError("partition/BPB/geometry disagreement")
    result = volume.report()
    result.update(bytes=len(raw), sha256=sha(raw), geometry=list(geometry),
                  mbr_sha256=sha(raw[:512]), volume_boot_sha256=sha(volume.data[:512]),
                  partition=dict(active=e[0], type=e[4], start_lba=start, sectors=count,
                                 start_chs=begin, end_chs=end))
    return result


def read_volume_file(volume, name):
    return Volume(volume).payloads.get(name.upper().replace("\\", "/"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--geometry", help="HD MBR geometry: cylinders,heads,sectors; omit for a raw FAT volume")
    parser.add_argument("--extract", help="DOS short path, writes payload to stdout; image remains read-only")
    args = parser.parse_args()
    raw = args.image.read_bytes()
    geometry = tuple(map(int, args.geometry.split(","))) if args.geometry else None
    report = inspect(raw, geometry) if geometry else Volume(raw).report()
    if args.extract:
        start = report.get("partition", {}).get("start_lba", 0) * 512
        size = report["bpb"]["total_sectors"] * 512
        payload = read_volume_file(raw[start:start + size], args.extract)
        if payload is None:
            parser.error("file not found")
        import sys
        sys.stdout.buffer.write(payload)
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
