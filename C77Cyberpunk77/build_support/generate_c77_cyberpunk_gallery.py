#!/usr/bin/env python3
"""Generate a full-D81 VICE gallery plan for the C77 font/theme preview."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build" / "c77-cyberpunk-77"
D81 = ROOT / "Releases" / "0.5" / "precog-d81" / "readyos-v0.5-d81.d81"
PREBOOT = ROOT / "Releases" / "0.5" / "precog-d81" / "readyos-v0.5-d81-preboot.prg"

APPS = (
    ("editor", 2, 3.0),
    ("readyshell", 3, 5.0),
    ("simplefiles", 4, 4.0),
    ("clipmgr", 5, 3.0),
    ("readybasic", 6, 5.0),
    ("cal26", 7, 5.0),
    ("tasklist", 8, 3.0),
    ("reuviewer", 9, 3.0),
    ("sysinfo", 10, 5.0),
    ("quicknotes", 11, 3.0),
    ("calcplus", 12, 3.0),
    ("hexview", 13, 3.0),
    ("simplecells", 14, 3.0),
    ("game2048", 15, 3.0),
    ("deminer", 16, 3.0),
    ("dizzy", 17, 5.0),
    ("readyirc", 18, 5.0),
    ("ucitest", 19, 4.0),
    ("readme", 20, 3.0),
)


def launch_step(identifier: str) -> list[str]:
    return [
        f"  - id: boot_{identifier}",
        "    type: vice.launch",
        "    params:",
        "      kill_stale: true",
        f"  - id: wait_launcher_{identifier}",
        "    type: screen.wait_contains",
        "    params:",
        '      text: "READY OS"',
        "      wait_timeout_s: 90",
        "      pre_delay_s: 1.0",
    ]


def main() -> None:
    if not D81.exists() or not PREBOOT.exists():
        raise SystemExit("Expected the full precog-d81 0.5 release artifacts")

    lines = [
        "version: 1",
        "kind: vice_task_plan",
        "plan_id: c77_cyberpunk_77_gallery",
        "run_mode: gui_vice",
        "global_defaults:",
        "  monitor_host: 127.0.0.1",
        "  monitor_port_start: 6502",
        "  monitor_port_span: 40",
        "  retry_policy: { max_attempts: 1, backoff_ms: 250, jitter: false }",
        "  timeouts: { launch_s: 45, step_s: 120, read_s: 2 }",
        "  artifact_policy: { capture_screen: true, capture_state: false, capture_dump: false }",
        "  vice:",
        f'    disk8: "{D81}"',
        f'    autostart_prg: "{PREBOOT}"',
        "    drive8_type: 1581",
        "    drive9_enabled: false",
        "    true_drive: false",
        "    close_vice: true",
        "    headless: true",
        "    speed_percent: 100",
        "steps:",
        "  - id: boot_gallery",
        "    type: vice.launch",
        "    params: { kill_stale: true }",
        "  - id: capture_loader",
        "    type: screen.capture",
        "    params:",
        "      label: 00_loader",
        "      pitch: C77 loader with dual-bank character ROM",
        "  - id: wait_launcher_gallery",
        "    type: screen.wait_contains",
        "    params:",
        '      text: "READY OS"',
        "      wait_timeout_s: 90",
        "      capture_on_success: true",
        "      capture_label: 01_launcher",
        "  - id: native_launcher",
        "    type: monitor.command",
        "    params:",
        "      command: 'raw:screenshot \"c77_native_01_launcher\" 2'",
    ]

    for number, (name, downs, delay) in enumerate(APPS, start=2):
        lines.extend(launch_step(name))
        keys = ",".join(["17"] * downs + ["13"])
        lines.extend(
            [
                f"  - id: launch_{name}",
                "    type: input.sequence",
                "    params:",
                f"      keys: [{keys}]",
                "      inter_key_delay_s: 0.08",
                f"      post_delay_s: {delay:.1f}",
                f"  - id: capture_{name}",
                "    type: screen.capture",
                "    params:",
                f"      label: {number:02d}_{name}",
                f"      pitch: C77 Cyberpunk 77 theme inside {name}",
            ]
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plan = OUT_DIR / "gallery.yaml"
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(plan)

    plans_dir = OUT_DIR / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    loader_launcher_lines = [
        "version: 1",
        "kind: vice_task_plan",
        "plan_id: c77_cyberpunk_77_loader_launcher",
        "run_mode: gui_vice",
        "global_defaults:",
        "  monitor_host: 127.0.0.1",
        "  monitor_port_start: 6502",
        "  monitor_port_span: 40",
        "  retry_policy: { max_attempts: 1, backoff_ms: 250, jitter: false }",
        "  timeouts: { launch_s: 45, step_s: 120, read_s: 2 }",
        "  artifact_policy: { capture_screen: true, capture_state: false, capture_dump: false }",
        "  vice:",
        f'    disk8: "{D81}"',
        f'    autostart_prg: "{PREBOOT}"',
        "    drive8_type: 1581",
        "    drive9_enabled: false",
        "    true_drive: false",
        "    close_vice: true",
        "    headless: true",
        "    speed_percent: 100",
        "steps:",
        "  - id: boot",
        "    type: vice.launch",
        "    params: { kill_stale: true }",
        "  - id: wait_loader",
        "    type: screen.wait_contains",
        "    params:",
        '      text: "LOADING"',
        "      wait_timeout_s: 30",
        "      capture_on_success: true",
        "      capture_label: 00_loader",
        "  - id: wait_launcher",
        "    type: screen.wait_contains",
        "    params:",
        '      text: "READY OS"',
        "      wait_timeout_s: 90",
        "      capture_on_success: true",
        "      capture_label: 01_launcher",
        "  - id: native_launcher",
        "    type: monitor.command",
        "    params:",
        "      command: 'raw:screenshot \"c77_native_01_launcher\" 2'",
    ]
    loader_launcher_plan = plans_dir / "00_loader_launcher.yaml"
    loader_launcher_plan.write_text("\n".join(loader_launcher_lines) + "\n", encoding="utf-8")
    print(loader_launcher_plan)

    for number, (name, downs, delay) in enumerate(APPS, start=2):
        keys = ",".join(["17"] * downs + ["13"])
        app_lines = [
            "version: 1",
            "kind: vice_task_plan",
            f"plan_id: c77_cyberpunk_77_{name}",
            "run_mode: gui_vice",
            "global_defaults:",
            "  monitor_host: 127.0.0.1",
            "  monitor_port_start: 6502",
            "  monitor_port_span: 40",
            "  retry_policy: { max_attempts: 1, backoff_ms: 250, jitter: false }",
            "  timeouts: { launch_s: 45, step_s: 120, read_s: 2 }",
            "  artifact_policy: { capture_screen: true, capture_state: false, capture_dump: false }",
            "  vice:",
            f'    disk8: "{D81}"',
            f'    autostart_prg: "{PREBOOT}"',
            "    drive8_type: 1581",
            "    drive9_enabled: false",
            "    true_drive: false",
            "    close_vice: true",
            "    headless: true",
            "    speed_percent: 100",
            "steps:",
            "  - id: boot",
            "    type: vice.launch",
            "    params: { kill_stale: true }",
            "  - id: wait_launcher",
            "    type: screen.wait_contains",
            "    params:",
            '      text: "READY OS"',
            "      wait_timeout_s: 90",
            "      pre_delay_s: 1.0",
            f"  - id: launch_{name}",
            "    type: input.sequence",
            "    params:",
            f"      keys: [{keys}]",
            "      inter_key_delay_s: 0.08",
            f"      post_delay_s: {delay:.1f}",
            f"  - id: capture_{name}",
            "    type: screen.capture",
            "    params:",
            f"      label: {number:02d}_{name}",
            f"      pitch: C77 Cyberpunk 77 theme inside {name}",
            f"  - id: native_{name}",
            "    type: monitor.command",
            "    params:",
            f"      command: 'raw:screenshot \"c77_native_{number:02d}_{name}\" 2'",
        ]
        app_plan = plans_dir / f"{number:02d}_{name}.yaml"
        app_plan.write_text("\n".join(app_lines) + "\n", encoding="utf-8")
        print(app_plan)


if __name__ == "__main__":
    main()
