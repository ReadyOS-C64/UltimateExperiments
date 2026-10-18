#!/usr/bin/env python3
"""Report timings and REU ownership for the opt-in staged benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from report_benchmark import database_report, latest_file, timing


STAGES = (
    "filter orders into FILTERED_ORDERS",
    "index FILTERED_ORDERS(C2,C3)",
    "join active CUSTOMERS into CUSTOMER_SALES",
    "index CUSTOMER_SALES(C2,C5)",
    "join active PRODUCTS into READY_SALES",
    "index READY_SALES(C3,C4)",
    "group and aggregate READY_SALES",
)


def jiffy24(raw: bytes, offset: int) -> int:
    return raw[offset] | raw[offset + 1] << 8 | raw[offset + 2] << 16


def seconds(jiffies: int) -> dict[str, float]:
    return {"pal": jiffies / 50.0, "ntsc": jiffies / 60.0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    root = args.run_dir.resolve()

    image = latest_file(root, "reu_pipeline_database_full.img")
    full_jiffies, _ = timing(root, "full_pipeline_timing", 0xB2)
    final_jiffies, _ = timing(root, "final_query_timing", 0xC2)
    ledger_path = latest_file(root, "*pipeline_step_timings*.bin")
    ledger = ledger_path.read_bytes()
    if len(ledger) != len(STAGES) * 3:
        raise ValueError(f"bad timing ledger {ledger_path}: {len(ledger)} bytes")
    stage_rows = []
    for index, name in enumerate(STAGES):
        elapsed = jiffy24(ledger, index * 3)
        stage_rows.append({"name": name, "jiffies": elapsed, **seconds(elapsed)})

    report = database_report(image)
    report["timings"] = {
        "full_pipeline": {"jiffies": full_jiffies, **seconds(full_jiffies)},
        "final_grouped_query": {"jiffies": final_jiffies, **seconds(final_jiffies)},
        "stages": stage_rows,
    }
    report["reu_image"] = str(image)

    print("ReuSQL64 staged TEMP-table benchmark (setup excluded)")
    print(
        f"  full materialized pipeline: {full_jiffies} jiffies = "
        f"{full_jiffies / 50.0:.3f} s PAL / {full_jiffies / 60.0:.3f} s NTSC"
    )
    for row in stage_rows:
        print(
            f"    {row['name']}: {row['jiffies']} jiffies = "
            f"{row['pal']:.3f} s PAL / {row['ntsc']:.3f} s NTSC"
        )
    print(
        f"  final grouped query only: {final_jiffies} jiffies = "
        f"{final_jiffies / 50.0:.3f} s PAL / {final_jiffies / 60.0:.3f} s NTSC"
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
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
