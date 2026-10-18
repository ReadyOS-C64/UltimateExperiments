#!/usr/bin/env python3
"""Generate and validate the complete ReadyFS 60-case evidence report."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "docs" / "READYFS_UI_TEST_MATRIX.md"
SOURCE = ROOT / "build_support" / "readyfs_ui_case_evidence.json"
UI_REPORT = ROOT / "artifacts" / "readyfs" / "readyfs-ui-report.json"
OUT_JSON = ROOT / "artifacts" / "readyfs" / "readyfs-ui-case-report.json"
OUT_MD = ROOT / "artifacts" / "readyfs" / "readyfs-ui-case-report.md"


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    matrix_text = MATRIX.read_text(encoding="utf-8")
    titles = {
        int(number): title
        for number, title in re.findall(r"^(\d+)\.\s+(.+)$", matrix_text,
                                        flags=re.MULTILINE)
    }
    target = int(source["target_cases"])
    expected = set(range(1, target + 1))
    if set(titles) != expected:
        raise SystemExit("ReadyFS case report: matrix must contain cases 1-60 exactly")

    cases: dict[int, dict[str, object]] = {}
    for group in source["proven_groups"]:
        for number in group["cases"]:
            number = int(number)
            if number in cases:
                raise SystemExit(f"ReadyFS case report: duplicate case {number}")
            cases[number] = {
                "case": number,
                "title": titles[number],
                "status": "PROVEN",
                "evidence": group["evidence"],
                "note": group["note"],
                "remaining": "keep regression evidence green",
            }
    for text_number, item in source["open_cases"].items():
        number = int(text_number)
        if number in cases:
            raise SystemExit(f"ReadyFS case report: duplicate case {number}")
        if item["status"] not in ("PARTIAL", "MISSING"):
            raise SystemExit(f"ReadyFS case report: bad status for case {number}")
        cases[number] = {
            "case": number,
            "title": titles[number],
            "status": item["status"],
            "evidence": item["evidence"],
            "note": "",
            "remaining": item["remaining"],
        }
    if set(cases) != expected:
        missing = sorted(expected - set(cases))
        extra = sorted(set(cases) - expected)
        raise SystemExit(f"ReadyFS case report: missing={missing} extra={extra}")

    ordered = [cases[number] for number in sorted(cases)]
    counts = {
        status: sum(item["status"] == status for item in ordered)
        for status in ("PROVEN", "PARTIAL", "MISSING")
    }
    ui = json.loads(UI_REPORT.read_text(encoding="utf-8-sig"))
    report = {
        "schema": "readyfs-ui-case-report-v1",
        "target_cases": target,
        "counts": counts,
        "latest_ui_suites": ui["latest_plan_count"],
        "successful_ui_suites": ui["successful_plan_count"],
        "screen_state_assertions": ui["assertion_count"],
        "cases": ordered,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# ReadyFS 60-Case Evidence Report",
        "",
        f"Status: **{counts['PROVEN']} proven**, **{counts['PARTIAL']} partial**, "
        f"**{counts['MISSING']} missing**.",
        "",
        f"Latest UI inventory: **{report['successful_ui_suites']}/"
        f"{report['latest_ui_suites']} suites**, "
        f"**{report['screen_state_assertions']} assertions**.",
        "",
        "| Case | Status | Requirement | Evidence | Remaining proof |",
        "|---:|---|---|---|---|",
    ]
    for item in ordered:
        evidence = ", ".join(f"`{value}`" for value in item["evidence"]) or "—"
        remaining = item["remaining"] if item["status"] != "PROVEN" else "—"
        lines.append(
            f"| {item['case']} | {item['status']} | {item['title']} | "
            f"{evidence} | {remaining} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("ReadyFS UI case report: "
          f"{counts['PROVEN']} proven, {counts['PARTIAL']} partial, "
          f"{counts['MISSING']} missing ({OUT_MD})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
