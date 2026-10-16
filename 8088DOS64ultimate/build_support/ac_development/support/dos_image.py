#!/usr/bin/env python3
"""Strict read-only FAT12 fixture tools; never a replacement for guest DOS.

Supports whole, 512-byte-sector volumes and root short names only, not partition
containers or long/subdirectory paths. The validation policy intentionally
rejects inconsistent mirrors and overlong chains rather than repairing them.
On-disk field/packing reference: Microsoft FAT specification v1.03 (2000),
https://www.cs.fsu.edu/~cop4610t/assignments/project3/spec/fatspec.pdf
"""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class ImageError(ValueError):
    """Stable reason code plus context for malformed or unsupported fixtures."""
    def __init__(self, code, detail=""):
        self.code = code
        super().__init__(code + (": " + detail if detail else ""))


@dataclass(frozen=True)
class DirectoryEntry:
    name: str
    attributes: int
    first_cluster: int
    size: int
    root_index: int
    raw_hex: str

    @property
    def is_file(self):
        return not self.attributes & 0x18


class Fat12Image:
    def __init__(self, data):
        self.data = bytes(data)
        if len(self.data) < 512:
            raise ImageError("short_boot_sector")
        if self.data[510:512] != b"\x55\xaa":
            raise ImageError("boot_signature")
        fields = struct.unpack_from("<HBHBHHBHHHI", self.data, 11)
        keys = ("bytes_per_sector", "sectors_per_cluster", "reserved_sectors",
                "fat_count", "root_entries", "total_sectors_16", "media",
                "sectors_per_fat", "sectors_per_track", "heads", "hidden_sectors")
        self.bpb = dict(zip(keys, fields))
        b = self.bpb
        total32 = struct.unpack_from("<I", self.data, 32)[0]
        total16 = b["total_sectors_16"]
        if total16 and total32:
            raise ImageError("conflicting_sector_counts")
        self.total_sectors = total16 or total32
        if b["bytes_per_sector"] != 512:
            raise ImageError("sector_size", "only 512-byte sectors are supported")
        if len(self.data) != self.total_sectors * 512:
            raise ImageError("image_length", "must exactly match the BPB sector count")
        spc = b["sectors_per_cluster"]
        if not spc or spc > 128 or spc & (spc - 1):
            raise ImageError("cluster_size")
        if not b["reserved_sectors"] or b["fat_count"] not in (1, 2) or not b["sectors_per_fat"] or not b["root_entries"]:
            raise ImageError("layout_fields")
        if not 1 <= b["sectors_per_track"] <= 63 or not 1 <= b["heads"] <= 256:
            raise ImageError("chs_geometry")
        if b["media"] != 0xf0 and not 0xf8 <= b["media"] <= 0xff:
            raise ImageError("media_descriptor")
        self.root_lba = b["reserved_sectors"] + b["fat_count"] * b["sectors_per_fat"]
        self.root_sectors = (b["root_entries"] * 32 + 511) // 512
        self.data_lba = self.root_lba + self.root_sectors
        if self.data_lba >= self.total_sectors:
            raise ImageError("layout_bounds", "FAT/root extends beyond the volume")
        self.cluster_count = (self.total_sectors - self.data_lba) // spc
        if not 1 <= self.cluster_count < 4085:
            raise ImageError("not_fat12")
        fat_size = b["sectors_per_fat"] * 512
        if (self.cluster_count + 2) * 12 > fat_size * 8:
            raise ImageError("fat_capacity")
        start = b["reserved_sectors"] * 512
        self.fat = self.data[start:start + fat_size]
        for copy in range(1, b["fat_count"]):
            if self.data[start + copy * fat_size:start + (copy + 1) * fat_size] != self.fat:
                raise ImageError("fat_mismatch", "duplicate FATs disagree")
        if self.fat_entry(0) != 0xf00 | b["media"] or self.fat_entry(1) < 0xff8:
            raise ImageError("fat_header")
        self.entries = self._root_entries()

    @classmethod
    def from_path(cls, path):
        return cls(Path(path).read_bytes())

    def fat_entry(self, cluster):
        if not isinstance(cluster, int) or cluster < 0:
            raise ImageError("fat_index")
        index = cluster * 3 // 2
        if index + 1 >= len(self.fat):
            raise ImageError("fat_index")
        packed = self.fat[index] | self.fat[index + 1] << 8
        return packed >> 4 if cluster & 1 else packed & 0xfff

    def lba_to_chs(self, lba):
        if not isinstance(lba, int) or not 0 <= lba < self.total_sectors:
            raise ImageError("lba_bounds")
        track, sector = divmod(lba, self.bpb["sectors_per_track"])
        cylinder, head = divmod(track, self.bpb["heads"])
        return cylinder, head, sector + 1

    def chs_to_lba(self, cylinder, head, sector):
        if not all(isinstance(v, int) for v in (cylinder, head, sector)) or cylinder < 0 or not 0 <= head < self.bpb["heads"] or not 1 <= sector <= self.bpb["sectors_per_track"]:
            raise ImageError("chs_bounds")
        lba = (cylinder * self.bpb["heads"] + head) * self.bpb["sectors_per_track"] + sector - 1
        if lba >= self.total_sectors:
            raise ImageError("chs_bounds")
        return lba

    def read_sectors(self, lba, count=1):
        if not isinstance(count, int) or count <= 0 or not isinstance(lba, int) or lba < 0 or lba + count > self.total_sectors:
            raise ImageError("sector_range")
        return self.data[lba * 512:(lba + count) * 512]

    def _root_entries(self):
        entries, names = [], set()
        start = self.root_lba * 512
        for index in range(self.bpb["root_entries"]):
            raw = self.data[start + index * 32:start + (index + 1) * 32]
            if len(raw) != 32:
                raise ImageError("truncated_root")
            if raw[0] == 0:
                break
            if raw[0] == 0xe5 or raw[11] == 0x0f:
                continue
            if raw[11] & 0xc0 or raw[11] & 0x18 == 0x18:
                raise ImageError("directory_attributes")
            short = (b"\xe5" + raw[1:11]) if raw[0] == 5 else raw[:11]
            base = short[:8].decode("cp437").rstrip(" ")
            ext = short[8:].decode("cp437").rstrip(" ")
            name = base + ("." + ext if ext else "")
            if not base or any(ord(c) < 32 or ord(c) == 127 or c in '\\/:"*+,;<=>?[]|' for c in name):
                raise ImageError("directory_name")
            key = (bool(raw[11] & 8), name.upper())
            if key in names:
                raise ImageError("duplicate_name", name)
            names.add(key)
            entries.append(DirectoryEntry(name, raw[11], struct.unpack_from("<H", raw, 26)[0],
                                          struct.unpack_from("<I", raw, 28)[0], index, raw.hex()))
        return tuple(entries)

    def find(self, name):
        matches = [entry for entry in self.entries if entry.name.upper() == name.upper()]
        if not matches:
            raise FileNotFoundError(name)
        regular = [entry for entry in matches if entry.is_file]
        if not regular:
            raise ImageError("not_regular_file", name)
        return regular[0]

    def cluster_lba(self, cluster):
        if not isinstance(cluster, int) or not 2 <= cluster <= self.cluster_count + 1 or cluster >= 0xff0:
            raise ImageError("cluster_bounds", str(cluster))
        return self.data_lba + (cluster - 2) * self.bpb["sectors_per_cluster"]

    def cluster_chain(self, entry):
        if not entry.is_file:
            raise ImageError("not_regular_file", entry.name)
        if entry.size == 0:
            if entry.first_cluster != 0:
                raise ImageError("empty_file_cluster", entry.name)
            return ()
        cluster_bytes = self.bpb["sectors_per_cluster"] * 512
        needed = (entry.size + cluster_bytes - 1) // cluster_bytes
        if needed > self.cluster_count:
            raise ImageError("file_size_bounds", entry.name)
        chain, seen = [], set()
        cluster = entry.first_cluster
        while True:
            self.cluster_lba(cluster)
            if cluster in seen:
                raise ImageError("cluster_cycle", entry.name)
            seen.add(cluster)
            chain.append(cluster)
            value = self.fat_entry(cluster)
            if value >= 0xff8:
                if len(chain) != needed:
                    raise ImageError("short_chain", entry.name)
                return tuple(chain)
            if value == 0xff7:
                raise ImageError("bad_cluster", entry.name)
            if value < 2 or 0xff0 <= value <= 0xff6:
                raise ImageError("reserved_or_free_cluster", entry.name)
            if len(chain) >= needed:
                # Check the tail even when enough file bytes have been read.
                if value in seen:
                    raise ImageError("cluster_cycle", entry.name)
                self.cluster_lba(value)
                raise ImageError("long_chain", entry.name)
            cluster = value

    def read_file(self, name):
        entry = self.find(name)
        chain = self.cluster_chain(entry)
        chunks = [self.read_sectors(self.cluster_lba(cluster), self.bpb["sectors_per_cluster"]) for cluster in chain]
        return b"".join(chunks)[:entry.size]

    def manifest(self):
        entries = []
        for entry in self.entries:
            item = asdict(entry)
            if entry.is_file:
                chain = self.cluster_chain(entry)
                item.update(sha256=sha256(self.read_file(entry.name)), clusters=list(chain),
                            cluster_lbas=[self.cluster_lba(cluster) for cluster in chain])
            entries.append(item)
        return {"schema": 1, "format": "whole-volume FAT12", "bytes": len(self.data),
                "sha256": sha256(self.data), "boot_sector_sha256": sha256(self.data[:512]),
                "bpb": dict(self.bpb, total_sectors=self.total_sectors),
                "layout": {"root_lba": self.root_lba, "root_sectors": self.root_sectors,
                           "data_lba": self.data_lba, "data_clusters": self.cluster_count},
                "entries": entries,
                "limits": "Strict read-only fixture oracle; root short names only; no lost-cluster/cross-link audit, DOS runtime or filesystem repair."}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def clone_and_extract(source, output_dir, names=()):
    """Create a new owned directory, never overwrite any existing destination."""
    source = Path(source).resolve(strict=True)
    image = Fat12Image.from_path(source)
    names = sorted(names, key=str.upper)
    if len({name.upper() for name in names}) != len(names):
        raise ImageError("duplicate_extraction")
    payloads = []
    for name in names:
        entry = image.find(name)
        if Path(entry.name).name != entry.name or entry.name in (".", "..") or entry.name.upper() in ("DISK.IMG", "MANIFEST.JSON"):
            raise ImageError("unsafe_output_name")
        payloads.append((entry.name, image.read_file(name)))
    # Resolve the existing parent before making the fresh owned directory.
    output = Path(output_dir).absolute()
    output = output.parent.resolve(strict=True) / output.name
    if output.exists() or output.is_symlink():
        raise FileExistsError(str(output))
    report = {"tool": {"path": "build_support/dos_image.py", "sha256": sha256(Path(__file__).read_bytes())},
              "image": image.manifest(), "clone": {"name": "disk.img", "sha256": sha256(image.data)},
              "extracted": [{"name": name, "bytes": len(data), "sha256": sha256(data)} for name, data in payloads]}
    output.mkdir()
    with (output / "disk.img").open("xb") as stream:
        stream.write(image.data)
    for name, data in payloads:
        with (output / name).open("xb") as stream:
            stream.write(data)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(report))
    if source.read_bytes() != image.data:
        raise ImageError("source_changed_during_operation")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("source", type=Path)
    clone = commands.add_parser("clone")
    clone.add_argument("source", type=Path)
    clone.add_argument("output_dir", type=Path, help="new directory; parent must already exist")
    clone.add_argument("--extract", action="append", default=[], metavar="SHORT.NAME")
    args = parser.parse_args()
    if args.command == "inspect":
        report = Fat12Image.from_path(args.source).manifest()
    else:
        report = clone_and_extract(args.source, args.output_dir, args.extract)
    print(canonical_json(report), end="")


if __name__ == "__main__":
    main()
