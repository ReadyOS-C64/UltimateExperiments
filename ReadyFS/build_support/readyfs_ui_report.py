#!/usr/bin/env python3
"""Summarize the latest ReadyFS VICE run for each UI plan."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
OUT = ROOT / "artifacts" / "readyfs"
NON_SUITE_PLANS = {"readyfs_pipeline_executor_diag"}


def relative(value: str) -> str:
    path = Path(value)
    try:
        return str(path.resolve().relative_to(ROOT))
    except (OSError, ValueError):
        return value


def main() -> int:
    latest: dict[str, dict[str, object]] = {}
    for path in LOGS.glob("vice_auto_*/manifest.json"):
        if path.parent.name == "vice_auto_latest" or path.parent.is_symlink():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        plan_id = data.get("plan_id")
        if not isinstance(plan_id, str) or not plan_id.startswith("readyfs_"):
            continue
        if plan_id in NON_SUITE_PLANS:
            continue
        previous = latest.get(plan_id)
        if previous is None or str(data.get("started_utc", "")) > str(
                previous.get("started_utc", "")):
            latest[plan_id] = data

    plans = []
    for plan_id, data in sorted(latest.items()):
        steps = data.get("steps", [])
        assertions = [
            step for step in steps
            if step.get("step_type") in {"screen.wait_contains", "screen.assert_contains",
                                         "memory.assert", "file.assert"}
        ]
        # Address-level diagnostics are useful evidence, but a run with no
        # assertion is not a UI test suite and must not inflate suite counts.
        if not assertions:
            continue
        screenshots = []
        for step in steps:
            screen = step.get("artifacts", {}).get("screen.png")
            if isinstance(screen, str) and Path(screen).exists():
                screenshots.append(relative(screen))
        plans.append({
            "plan_id": plan_id,
            "run_id": data.get("run_id"),
            "status": data.get("status"),
            "started_utc": data.get("started_utc"),
            "finished_utc": data.get("finished_utc"),
            "step_count": len(steps),
            "assertion_count": len(assertions),
            "failed_step": data.get("failed_step"),
            "manifest": relative(str(LOGS / str(data.get("run_id")) / "manifest.json")),
            "screenshots": screenshots,
        })
    successful = sum(plan["status"] == "success" for plan in plans)
    report = {
        "schema": "readyfs-ui-report-v1",
        "status": "pass" if plans and successful == len(plans) else "attention",
        "latest_plan_count": len(plans),
        "successful_plan_count": successful,
        "assertion_count": sum(int(plan["assertion_count"]) for plan in plans),
        "plans": plans,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "readyfs-ui-report.json"
    md_path = OUT / "readyfs-ui-report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ReadyFS UI Automation Report",
        "",
        f"Latest suites: **{len(plans)}**; successful: **{successful}**; "
        f"screen/state assertions: **{report['assertion_count']}**.",
        "",
        "This report summarizes the latest run of each VICE plan. Numbered "
        "requirement promotion remains governed by `READYFS_UI_TEST_MATRIX.md`.",
        "",
        "| Plan | Latest run | Status | Steps | Assertions | Screenshots |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for plan in plans:
        manifest = plan["manifest"]
        lines.append(
            f"| `{plan['plan_id']}` | [{plan['run_id']}](../../{manifest}) | "
            f"{plan['status']} | {plan['step_count']} | {plan['assertion_count']} | "
            f"{len(plan['screenshots'])} |"
        )
    lines.extend(["", "## Latest Screenshots", ""])
    for plan in plans:
        if plan["screenshots"]:
            screen = plan["screenshots"][-1]
            lines.append(f"- `{plan['plan_id']}`: [{Path(screen).name}](../../{screen})")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ReadyFS UI report: {len(plans)} latest plans, {successful} successful")
    return 0 if plans else 1


if __name__ == "__main__":
    sys.exit(main())
