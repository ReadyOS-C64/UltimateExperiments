#!/usr/bin/env python3
"""Validate and convert a ReadyFS RFJ1 operation journal."""

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
from pathlib import Path


HEADER = struct.Struct("<4sBBBBHHHH")
RECORD = struct.Struct("<BBBBHHH")
ACTION_NAMES = {
    1: "mkdir",
    2: "copy-file",
    3: "move-file",
    4: "delete-file",
    5: "rmdir",
}


class JournalError(ValueError):
    pass


def parse_journal(data: bytes) -> dict[str, object]:
    if len(data) < HEADER.size:
        raise JournalError("journal is shorter than its 16-byte header")
    magic, version, mode, open_flag, overflow, used, count, completed, failed = (
        HEADER.unpack_from(data)
    )
    if magic != b"RFJ1":
        raise JournalError("bad RFJ1 magic")
    if version != 1:
        raise JournalError(f"unsupported RFJ version {version}")
    if open_flag not in (0, 1) or overflow not in (0, 1):
        raise JournalError("invalid journal state flag")
    if used < HEADER.size or used > len(data):
        raise JournalError("used-byte count is outside the input")

    records: list[dict[str, object]] = []
    offset = HEADER.size
    success_count = 0
    failure_count = 0
    while offset < used:
        if RECORD.size > used - offset:
            raise JournalError(f"truncated record header at {offset}")
        action, result, backend, kind, detail, plan_offset, stem_len = (
            RECORD.unpack_from(data, offset)
        )
        end = offset + RECORD.size + stem_len + 1
        if end > used:
            raise JournalError(f"truncated stem at {offset}")
        raw_stem = data[offset + RECORD.size : end]
        if not raw_stem or raw_stem[-1] != 0:
            raise JournalError(f"stem at {offset} is not NUL terminated")
        try:
            stem = raw_stem[:-1].decode("latin-1")
        except UnicodeDecodeError as exc:  # pragma: no cover; latin-1 is total
            raise JournalError(f"invalid stem at {offset}") from exc
        records.append(
            {
                "index": len(records),
                "offset": offset,
                "action": action,
                "action_name": ACTION_NAMES.get(action, f"action-{action}"),
                "result": result,
                "succeeded": result == 0,
                "backend": backend,
                "kind": kind,
                "detail": detail,
                "plan_offset": plan_offset,
                "stem": stem,
            }
        )
        if result == 0:
            success_count += 1
        else:
            failure_count += 1
        offset = end

    if offset != used:
        raise JournalError("record walk did not end at used-byte count")
    if len(records) != count:
        raise JournalError(f"header count {count} != parsed count {len(records)}")
    if success_count != completed or failure_count != failed:
        raise JournalError("header result counters do not match records")
    return {
        "schema": "readyfs-rfj1-report-v1",
        "journal": {
            "version": version,
            "mode": mode,
            "state": "open" if open_flag else "finished",
            "overflow": bool(overflow),
            "used_bytes": used,
            "count": count,
            "completed": completed,
            "failed": failed,
        },
        "records": records,
    }


def markdown(report: dict[str, object]) -> str:
    header = report["journal"]
    assert isinstance(header, dict)
    records = report["records"]
    assert isinstance(records, list)
    lines = [
        "# ReadyFS Operation Journal",
        "",
        f"State: **{str(header['state']).upper()}**; mode: `{header['mode']}`; "
        f"events: **{header['count']}**; completed: **{header['completed']}**; "
        f"failed: **{header['failed']}**; overflow: **{str(header['overflow']).lower()}**.",
        "",
        "| # | Action | Result | Backend | Detail | Plan offset | Stem |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for item in records:
        assert isinstance(item, dict)
        stem = str(item["stem"]).replace("|", "\\|")
        lines.append(
            f"| {item['index']} | {item['action_name']} | {item['result']} | "
            f"{item['backend']} | {item['detail']} | {item['plan_offset']} | "
            f"`{stem}` |"
        )
    return "\n".join(lines) + "\n"


def fixture() -> bytes:
    rows = [
        RECORD.pack(1, 0, 3, 2, 0, 9, 3) + b"one\0",
        RECORD.pack(2, 82, 1, 1, 82, 22, 12) + b"one/file.prg\0",
    ]
    used = HEADER.size + sum(map(len, rows))
    return HEADER.pack(b"RFJ1", 1, 2, 0, 0, used, 2, 1, 1) + b"".join(rows)


def self_test() -> None:
    report = parse_journal(fixture())
    assert report["journal"] == {
        "version": 1,
        "mode": 2,
        "state": "finished",
        "overflow": False,
        "used_bytes": 53,
        "count": 2,
        "completed": 1,
        "failed": 1,
    }
    assert report["records"][1]["stem"] == "one/file.prg"
    assert "copy-file" in markdown(report)
    broken = bytearray(fixture())
    broken[10] = 3
    try:
        parse_journal(bytes(broken))
    except JournalError:
        pass
    else:
        raise AssertionError("counter corruption was accepted")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "journal.bin"
        path.write_bytes(fixture())
        assert parse_journal(path.read_bytes())["journal"]["count"] == 2


def validate_expected(report: dict[str, object], args: argparse.Namespace) -> None:
    journal = report["journal"]
    records = report["records"]
    assert isinstance(journal, dict) and isinstance(records, list)
    expected_header = {
        "mode": args.expect_mode,
        "count": args.expect_count,
        "completed": args.expect_completed,
        "failed": args.expect_failed,
    }
    for name, expected in expected_header.items():
        if expected is not None and journal[name] != expected:
            raise JournalError(
                f"expected {name} {expected}, found {journal[name]}")
    if args.expect_stem is not None:
        actual = [str(item["stem"]) for item in records]
        if actual != args.expect_stem:
            raise JournalError(f"expected stems {args.expect_stem}, found {actual}")
    if args.expect_action is not None:
        actual = [str(item["action_name"]) for item in records]
        if actual != args.expect_action:
            raise JournalError(
                f"expected actions {args.expect_action}, found {actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--reu-bank", type=lambda value: int(value, 0))
    parser.add_argument("--reu-offset", type=lambda value: int(value, 0),
                        default=0)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--expect-mode", type=int)
    parser.add_argument("--expect-count", type=int)
    parser.add_argument("--expect-completed", type=int)
    parser.add_argument("--expect-failed", type=int)
    parser.add_argument("--expect-stem", action="append")
    parser.add_argument("--expect-action", action="append")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("readyfs journal report tests passed")
        return 0
    if args.input is None:
        parser.error("input is required unless --self-test is used")
    try:
        data = args.input.read_bytes()
        if args.reu_bank is not None:
            if not 0 <= args.reu_bank <= 255 or not 0 <= args.reu_offset <= 0xFFFF:
                raise JournalError("REU bank or offset is outside its range")
            start = args.reu_bank * 0x10000 + args.reu_offset
            if start + HEADER.size > len(data):
                raise JournalError("RFJ1 header is outside the REU image")
            used = struct.unpack_from("<H", data, start + 8)[0]
            data = data[start : start + used]
        report = parse_journal(data)
        validate_expected(report, args)
    except (OSError, JournalError) as exc:
        print(f"readyfs journal report: {exc}", file=sys.stderr)
        return 1
    rendered = markdown(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(rendered, encoding="utf-8")
    if not args.json and not args.markdown:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
