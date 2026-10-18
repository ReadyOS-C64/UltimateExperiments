#!/usr/bin/env python3
"""Report permanent ReuSQL64 benchmark timing and exact REU page ownership."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PAGE = 256
NONE = 0xFFFF
FIRST_USABLE = 102
OVERLAY_PAGES = 544
JOURNAL_PAGES = 16


def u16(data: bytes, offset: int) -> int:
    return data[offset] | data[offset + 1] << 8


def u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little")


def page(data: bytes, number: int) -> bytes:
    return data[number * PAGE : (number + 1) * PAGE]


def petscii(text: str) -> bytes:
    """cc65's C64 target stores uppercase literals as high-bit PETSCII."""
    return bytes(ord(character) | 0x80 for character in text)


def ascii_name(raw: bytes) -> str:
    # cc65 maps source '_' to PETSCII $A4, not high-bit ASCII underscore.
    return "".join("_" if value == 0xA4 else chr(value & 0x7F) for value in raw)


def chain(data: bytes, head: int, next_offset: int, magic: bytes) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    current = head
    while current != NONE:
        if current in seen:
            raise ValueError(f"page-chain loop at {current}")
        seen.add(current)
        item = page(data, current)
        if item[:4] != magic:
            raise ValueError(f"page {current} has {item[:4]!r}, expected {magic!r}")
        result.append(current)
        current = u16(item, next_offset)
    return result


def latest_file(root: Path, pattern: str) -> Path:
    candidates = list(root.rglob(pattern))
    if not candidates:
        raise FileNotFoundError(f"no {pattern!r} below {root}")
    return max(candidates, key=lambda item: item.stat().st_mtime_ns)


def timing(root: Path, label: str, marker: int) -> tuple[int, Path]:
    path = latest_file(root, f"*{label}*.bin")
    raw = path.read_bytes()
    if len(raw) != 4 or raw[0] != marker:
        raise ValueError(f"bad {label} timing artifact {path}: {raw.hex(' ')}")
    jiffies = raw[1] | raw[2] << 8 | raw[3] << 16
    return jiffies, path


def database_report(image_path: Path) -> dict[str, object]:
    data = image_path.read_bytes()
    if len(data) < 512 * 1024 or data[:4] != petscii("RSQL"):
        raise ValueError(f"not a 512KB+ ReuSQL64 REU image: {image_path}")
    reu_pages = len(data) // PAGE
    # RsqlSuperblock is byte-packed by cc65; catalog_root begins at byte 13.
    root_page = u16(data, 13)
    root = page(data, root_page)
    if root[:4] != petscii("RCAT"):
        raise ValueError(f"catalog root page {root_page} is not RCAT")

    tables: list[dict[str, object]] = []
    table_names: dict[int, str] = {}
    descriptor = u16(root, 8)
    seen: set[int] = set()
    while descriptor != NONE:
        if descriptor in seen:
            raise ValueError("table descriptor loop")
        seen.add(descriptor)
        item = page(data, descriptor)
        if item[:4] != petscii("RTBL"):
            raise ValueError(f"table descriptor {descriptor} is corrupt")
        name = ascii_name(item[20 : 20 + item[19]])
        rows = u32(item, 12)
        width = u16(item, 16)
        row_pages = chain(data, u16(item, 8), 8, petscii("RROW"))
        table_names[descriptor] = name
        tables.append(
            {
                "name": name,
                "rows": rows,
                "row_width": width,
                "logical_bytes": rows * width,
                "row_pages": len(row_pages),
                "row_page_bytes": len(row_pages) * PAGE,
                "including_descriptor_bytes": (len(row_pages) + 1) * PAGE,
            }
        )
        descriptor = u16(item, 6)

    indexes: list[dict[str, object]] = []
    descriptor = u16(root, 20)
    seen.clear()
    while descriptor != NONE:
        if descriptor in seen:
            raise ValueError("index descriptor loop")
        seen.add(descriptor)
        item = page(data, descriptor)
        if item[:4] != petscii("RIDX"):
            raise ValueError(f"index descriptor {descriptor} is corrupt")
        name = ascii_name(item[21 : 21 + item[20]])
        leaves = chain(data, u16(item, 10), 6, petscii("RILF"))
        indexes.append(
            {
                "name": name,
                "table": table_names.get(u16(item, 8), f"page-{u16(item, 8)}"),
                "entries": u32(item, 14),
                "key_width": item[18],
                "leaf_pages": len(leaves),
                "leaf_bytes": len(leaves) * PAGE,
                "including_descriptor_bytes": (len(leaves) + 1) * PAGE,
            }
        )
        descriptor = u16(item, 6)

    bitmap = data[2 * PAGE : 2 * PAGE + 8192]
    limit = reu_pages - OVERLAY_PAGES - JOURNAL_PAGES
    used = sum(
        1 for number in range(FIRST_USABLE, limit)
        if bitmap[number >> 3] & (1 << (number & 7))
    )
    return {
        "reu_image_bytes": len(data),
        "database_capacity_pages": limit - FIRST_USABLE,
        "database_used_pages": used,
        "database_used_bytes": used * PAGE,
        "database_free_pages": limit - FIRST_USABLE - used,
        "tables": tables,
        "indexes": indexes,
        "unattributed_pages": used
        - sum(int(t["row_pages"]) + 1 for t in tables)
        - sum(int(i["leaf_pages"]) + 1 for i in indexes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    image = latest_file(root, "reu_benchmark_database_full.img")
    summary_jiffies, _ = timing(root, "sales_summary_timing", 0xB2)
    eligible_jiffies, _ = timing(root, "eligible_sales_timing", 0xC2)
    summary_pal = summary_jiffies / 50.0
    summary_ntsc = summary_jiffies / 60.0
    eligible_pal = eligible_jiffies / 50.0
    eligible_ntsc = eligible_jiffies / 60.0
    report = database_report(image)
    report["timings"] = {
        "sales_summary_jiffies": summary_jiffies,
        "sales_summary_seconds_pal": summary_pal,
        "sales_summary_seconds_ntsc": summary_ntsc,
        "eligible_sales_jiffies": eligible_jiffies,
        "eligible_sales_seconds_pal": eligible_pal,
        "eligible_sales_seconds_ntsc": eligible_ntsc,
    }
    report["reu_image"] = str(image)

    print("ReuSQL64 real-world benchmark (query execution only; setup excluded)")
    print(
        f"  sales summary: {summary_jiffies} jiffies = {summary_pal:.3f} s PAL / "
        f"{summary_ntsc:.3f} s NTSC"
    )
    print(
        f"  eligible sales: {eligible_jiffies} jiffies = {eligible_pal:.3f} s PAL / "
        f"{eligible_ntsc:.3f} s NTSC"
    )
    print("Tables:")
    for table in report["tables"]:
        print(
            f"  {table['name']}: {table['rows']} rows, width {table['row_width']}, "
            f"logical {table['logical_bytes']} B, {table['row_pages']} row pages / "
            f"{table['row_page_bytes']} B ({table['including_descriptor_bytes']} B with descriptor)"
        )
    print("Indexes:")
    for index in report["indexes"]:
        print(
            f"  {index['name']} on {index['table']}: {index['entries']} entries, "
            f"key width {index['key_width']}, {index['leaf_pages']} leaf pages / "
            f"{index['leaf_bytes']} B ({index['including_descriptor_bytes']} B with descriptor)"
        )
    print(
        f"Database allocation: {report['database_used_pages']} pages / "
        f"{report['database_used_bytes']} B used, {report['database_free_pages']} pages free; "
        f"whole-REU export {report['reu_image_bytes']} B"
    )
    print(f"  catalog/other attributed pages: {report['unattributed_pages']}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
