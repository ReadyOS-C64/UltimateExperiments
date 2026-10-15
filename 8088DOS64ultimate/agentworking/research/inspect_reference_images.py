#!/usr/bin/env python3
"""Read-only FAT12 inventory for the supplied planning fixtures; never writes images."""
import hashlib
import json
from pathlib import Path
import struct


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path):
    image = path.read_bytes()
    if len(image) < 512:
        raise ValueError(f"short image: {path}")
    fields = struct.unpack_from("<HBHBHHBHHH", image, 11)
    bps, spc, reserved, fats, root_count, sectors, media, spf, spt, heads = fields
    if not bps or not spc or len(image) != bps * sectors:
        raise ValueError(f"invalid geometry/length: {path}")
    root_sector = reserved + fats * spf
    root_sectors = (root_count * 32 + bps - 1) // bps
    data_sector = root_sector + root_sectors
    clusters = (sectors - data_sector) // spc
    if clusters >= 4085:
        raise ValueError("this inventory only handles FAT12")
    fat = image[reserved * bps:(reserved + spf) * bps]
    fat_copies_equal = all(
        image[(reserved + n * spf) * bps:(reserved + (n + 1) * spf) * bps] == fat
        for n in range(fats)
    )
    entries = []
    for pos in range(root_sector * bps, root_sector * bps + root_count * 32, 32):
        entry = image[pos:pos + 32]
        if entry[0] == 0:
            break
        if entry[0] == 0xE5 or entry[11] == 0x0F:
            continue
        base = entry[:8].decode("cp437").rstrip()
        ext = entry[8:11].decode("cp437").rstrip()
        name = base + ("." + ext if ext else "")
        cluster = int.from_bytes(entry[26:28], "little")
        size = int.from_bytes(entry[28:32], "little")
        info = {"name": name, "attributes": entry[11], "first_cluster": cluster, "size": size}
        if not (entry[11] & 0x18):
            payload = bytearray()
            seen = set()
            while cluster >= 2 and cluster < 0xFF8:
                if cluster in seen or cluster >= clusters + 2:
                    raise ValueError(f"bad cluster chain: {path.name}/{name}")
                seen.add(cluster)
                start = (data_sector + (cluster - 2) * spc) * bps
                payload.extend(image[start:start + spc * bps])
                index = cluster * 3 // 2
                value = int.from_bytes(fat[index:index + 2], "little")
                cluster = value >> 4 if cluster & 1 else value & 0xFFF
            if len(payload) < size:
                raise ValueError(f"short cluster chain: {path.name}/{name}")
            payload = bytes(payload[:size])
            info["sha256"] = sha256(payload)
            info["chain_clusters"] = len(seen)
            if name.upper() in {"CONFIG.SYS", "AUTOEXEC.BAT"}:
                info["text_cp437"] = payload.decode("cp437")
        entries.append(info)
    return {
        "path": "reference/" + path.name,
        "bytes": len(image), "sha256": sha256(image),
        "boot_sector_sha256": sha256(image[:512]),
        "boot_signature_hex": image[510:512].hex(),
        "oem_text_cp437": image[3:11].decode("cp437"),
        "oem_hex": image[3:11].hex(),
        "fat_type": "FAT12", "fat_copies_equal": fat_copies_equal,
        "bpb": dict(zip(
            ["bytes_per_sector", "sectors_per_cluster", "reserved_sectors", "fat_count",
             "root_entries", "total_sectors", "media", "sectors_per_fat",
             "sectors_per_track", "heads"], fields)),
        "derived": {"cylinders": sectors // (spt * heads), "data_sector": data_sector,
                    "data_clusters": clusters, "root_sector": root_sector},
        "root_files": entries,
        "limitations": "Root-directory and file-chain inventory only; not a boot or full filesystem-validity test."
    }


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[2]
    paths = sorted((project / "reference").glob("*.img"))
    if not paths:
        raise SystemExit("No reference IMG files found")
    print(json.dumps({"schema": 1, "method": "Read-only BPB/root/FAT12 chain parsing and SHA-256",
                      "images": [inspect(path) for path in paths]}, indent=2))
