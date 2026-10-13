#!/usr/bin/env python3
"""Validate and convert a ReadyFS RFA1 executor-completion record."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


RECORD = struct.Struct("<4sBBBB")


class ActionReportError(ValueError):
    pass


def parse_action_report(data: bytes) -> dict[str, object]:
    if len(data) < RECORD.size:
        raise ActionReportError("record is shorter than 8 bytes")
    magic, attempted, completed, failed, pending = RECORD.unpack_from(data)
    if magic != b"RFA1":
        raise ActionReportError("bad RFA1 magic")
    if pending not in (0, 1):
        raise ActionReportError("invalid pending flag")
    if completed + failed != attempted:
        raise ActionReportError("executor totals are inconsistent")
    if attempted != 1 or pending != 0:
        raise ActionReportError("single-action executor did not finish exactly once")
    return {
        "schema": "readyfs-rfa1-report-v1",
        "state": "finished",
        "attempted": attempted,
        "completed": completed,
        "failed": failed,
        "pending": bool(pending),
        "result": "success" if completed == 1 else "failure",
    }


def markdown(report: dict[str, object]) -> str:
    return (
        "# ReadyFS Executor Completion\n\n"
        f"State: **{str(report['state']).upper()}**; result: "
        f"**{str(report['result']).upper()}**; attempted: "
        f"**{report['attempted']}**; completed: **{report['completed']}**; "
        f"failed: **{report['failed']}**; pending: "
        f"**{str(report['pending']).lower()}**.\n"
    )


def self_test() -> None:
    success = parse_action_report(RECORD.pack(b"RFA1", 1, 1, 0, 0))
    assert success["result"] == "success"
    assert "FINISHED" in markdown(success)
    failure = parse_action_report(RECORD.pack(b"RFA1", 1, 0, 1, 0))
    assert failure["result"] == "failure"
    for broken in (
        RECORD.pack(b"BAD1", 1, 1, 0, 0),
        RECORD.pack(b"RFA1", 1, 0, 0, 0),
        RECORD.pack(b"RFA1", 1, 1, 0, 1),
    ):
        try:
            parse_action_report(broken)
        except ActionReportError:
            pass
        else:
            raise AssertionError("invalid RFA1 record was accepted")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--reu-bank", type=lambda value: int(value, 0))
    parser.add_argument("--reu-offset", type=lambda value: int(value, 0),
                        default=0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("readyfs action report tests passed")
        return 0
    if args.input is None:
        parser.error("input is required unless --self-test is used")
    try:
        data = args.input.read_bytes()
        if args.reu_bank is not None:
            if not 0 <= args.reu_bank <= 255 or not 0 <= args.reu_offset <= 0xFFFF:
                raise ActionReportError("REU bank or offset is outside its range")
            start = args.reu_bank * 0x10000 + args.reu_offset
            data = data[start : start + RECORD.size]
        report = parse_action_report(data)
    except (OSError, ActionReportError) as exc:
        print(f"readyfs action report: {exc}", file=sys.stderr)
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
