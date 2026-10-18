#!/usr/bin/env python3
"""Generate and validate the standalone ReadyFS memory/overlay inventory."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "readyfs"
OVERLAY_MAP = ROOT / "obj" / "readyfs-overlay.map"
MONOLITHIC_MAP = ROOT / "obj" / "readyfs.map"

SEGMENT_RE = re.compile(
    r"^([A-Z0-9]+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+"
)


def segments(path: Path) -> dict[str, dict[str, int]]:
    found: dict[str, dict[str, int]] = {}
    in_list = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "Segment list:":
            in_list = True
            found = {}
            continue
        if not in_list:
            continue
        match = SEGMENT_RE.match(line)
        if match:
            name, start, end, size = match.groups()
            found[name] = {
                "start": int(start, 16),
                "end": int(end, 16),
                "size": int(size, 16),
            }
        elif found and not line.strip():
            break
    if not found:
        raise ValueError(f"no segment list in {path}")
    return found


def map_symbol(path: Path, name: str) -> int:
    # ld65 packs multiple exports onto one line. A symbol can therefore move
    # between display columns when the export set changes; column position is
    # not part of the map format's symbol/value contract.
    match = re.search(rf"(?:^|\s){re.escape(name)}\s+([0-9A-F]{{6}})\s+",
                      path.read_text(encoding="utf-8", errors="replace"),
                      re.MULTILINE)
    if match is None:
        raise ValueError(f"no {name} in {path}")
    return int(match.group(1), 16)


def sidecar(path: Path, expected: dict[str, int], slot_bytes: int) -> dict[str, object]:
    data = path.read_bytes()
    load_address = data[0] | (data[1] << 8) if len(data) >= 2 else -1
    payload = max(0, len(data) - 2)
    checks = {
        "load_address_b600": load_address == 0xB600,
        "payload_matches_map": payload == expected["size"],
        "fits_reu_slot": payload <= slot_bytes,
        "fits_overlay_window": payload <= 0x1000,
    }
    return {
        "file": str(path.relative_to(ROOT)),
        "load_address": load_address,
        "payload_bytes": payload,
        "map_bytes": expected["size"],
        "reu_slot_bytes": slot_bytes,
        "checks": checks,
    }


def main() -> int:
    overlay = segments(OVERLAY_MAP)
    # Cached payload includes code, constants and zero-filled overlay BSS.
    # These must remain distinct assembler segments: cc65 can emit constants
    # after a function label, before switching back to its code segment.
    for index in range(1,29):
        name = f"OVERLAY{index}"
        parts = [overlay[k] for k in (name,name+"R",name+"B") if k in overlay]
        overlay[name] = {"start":min(x["start"] for x in parts),
                         "end":max(x["end"] for x in parts),
                         "size":sum(x["size"] for x in parts)}
        assert map_symbol(OVERLAY_MAP, f"__{name}_SIZE__") == overlay[name]["size"], name
    monolithic = segments(MONOLITHIC_MAP)
    stack_top = (map_symbol(OVERLAY_MAP, "__MAIN_START__") +
                 map_symbol(OVERLAY_MAP, "__MAIN_SIZE__"))
    resident_end = max(
        value["end"]
        for name, value in overlay.items()
        if not name.startswith("OVL") and not name.startswith("OVERLAY")
        and value["size"]
    )
    monolithic_end = max(
        value["end"] for value in monolithic.values() if value["size"]
    )
    match = sidecar(OUT / "readyfs-match.prg", overlay["OVERLAY1"], 0x1000)
    plan = sidecar(OUT / "readyfs-plan.prg", overlay["OVERLAY2"], 0x1000)
    help_sidecar = sidecar(OUT / "readyfs-help.prg", overlay["OVERLAY3"],
                           0x1000)
    backend = sidecar(OUT / "readyfs-backend.prg", overlay["OVERLAY4"],
                      0x1000)
    cmdpath = sidecar(OUT / "readyfs-cmdpath.prg", overlay["OVERLAY5"],
                      0x1000)
    drive = sidecar(OUT / "readyfs-drive.prg", overlay["OVERLAY6"], 0x1000)
    utility = sidecar(OUT / "readyfs-utility.prg", overlay["OVERLAY7"],
                      0x1000)
    tree = sidecar(OUT / "readyfs-tree.prg", overlay["OVERLAY8"], 0x1000)
    content = sidecar(OUT / "readyfs-content.prg", overlay["OVERLAY9"], 0x1000)
    batch = sidecar(OUT / "readyfs-batch.prg", overlay["OVERLAY10"], 0x1000)
    recursive = sidecar(OUT / "readyfs-recursive.prg", overlay["OVERLAY11"],
                        0x1000)
    tape = sidecar(OUT / "readyfs-tape.prg", overlay["OVERLAY12"], 0x1000)
    ui = sidecar(OUT / "readyfs-ui.prg", overlay["OVERLAY13"], 0x1000)
    present = sidecar(OUT / "readyfs-present.prg", overlay["OVERLAY14"], 0x1000)
    command_help = sidecar(OUT / "readyfs-command-help.prg", overlay["OVERLAY15"], 0x1000)
    stream = sidecar(OUT / "readyfs-stream.prg", overlay["OVERLAY16"], 0x1000)
    iec = sidecar(OUT / "readyfs-iec.prg", overlay["OVERLAY17"], 0x1000)
    udos = {name: sidecar(OUT / f"readyfs-udos-{name}.prg", overlay[f"OVERLAY{21+i}"], 0x1000)
            for i,name in enumerate(("prepare","lookup","execute","name"))}
    files_plan = sidecar(OUT / "readyfs-files-plan.prg", overlay["OVERLAY20"], 0x1000)
    files = sidecar(OUT / "readyfs-files.prg", overlay["OVERLAY19"], 0x1000)
    native = sidecar(OUT / "readyfs-native.prg", overlay["OVERLAY18"], 0x1000)
    scripting = {name: sidecar(OUT / f"readyfs-{name}.prg", overlay[f"OVERLAY{25+i}"], 0x1000)
                 for i, name in enumerate(("environment", "expand", "flow", "config"))}
    script_layout = [
        ("environment_overlay_cache", 0x0000, 0x1000),
        ("expansion_overlay_cache", 0x1000, 0x2000),
        ("flow_overlay_cache", 0x2000, 0x3000),
        ("config_overlay_cache", 0x3000, 0x4000),
        ("session_variables", 0x4000, 0x4920),
        ("config_variable_stage", 0x5000, 0x5920),
        ("config_variable_merge", 0x6000, 0x6920),
        ("script_arguments", 0x7000, 0x7A00),
    ]
    batch_layout = [("batch_overlay_cache",0,0x1000),
                    ("batch_script",0x1000,0x5000),
                    ("batch_checkpoint",0x5000,0x5100),
                    ("tape_overlay_cache",0x5100,0x6100),
                    ("ui_overlay_cache",0x6100,0x7100),
                    ("ui_live_screen",0x7100,0x74E8),
                    ("ui_live_color",0x7500,0x78E8),
                    ("ui_draft",0x7900,0x7A00),
                    ("presentation_overlay_cache",0x7A00,0x8A00),
                    ("command_help_overlay_cache",0x8A00,0x9A00),
                    ("last_mount_session_paths",0x9A00,0xB100),
                    ("stream_policy_overlay_cache",0xB100,0xC100),
                    ("iec_config_policy_overlay_cache",0xC100,0xD100),
                    ("native_iec_media_overlay_cache",0xD100,0xE100),
                    ("native_files_overlay_cache",0xE100,0xF100)]
    layout = [
        ("aliases", 0x0000, 0x0888),
        ("drive_profiles", 0x0888, 0x08E4),
        ("operation_journal", 0x0900, 0x2000),
        ("native_files_policy_overlay_cache", 0x2000, 0x3000),
        ("udos_prepare_overlay_cache", 0x3000, 0x4000),
        ("udos_lookup_overlay_cache", 0x4000, 0x5000),
        ("udos_execute_overlay_cache", 0x5000, 0x6000),
        ("udos_name_overlay_cache", 0x6000, 0x7000),
        ("retired_scroll_pages_reserved", 0x7000, 0x7DC0),
        ("retired_scroll_live_reserved", 0x7DC0, 0x81A8),
        ("action_checkpoint", 0x8200, 0x8300),
        ("action_report", 0x8300, 0x8308),
        ("action_reserved", 0x8308, 0x8400),
        ("config_backup", 0x8400, 0x8D88),
        ("recursive_checkpoint", 0x8E00, 0x8F00),
        ("tree_checkpoint", 0x8F00, 0x9000),
        ("config_stage", 0x9000, 0x9988),
        ("recursive_roots", 0x9988, 0x9B88),
        ("action_plan", 0xA000, 0xDFF0),
    ]
    overlay_layout = [
        ("overlay_match", 0x0000, 0x1000),
        ("overlay_plan", 0x1000, 0x2000),
        ("overlay_help", 0x2000, 0x3000),
        ("overlay_backend", 0x3000, 0x4000),
        ("overlay_cmdpath_reserved", 0x4000, 0x5000),
        ("overlay_drive_profile", 0x5000, 0x6000),
        ("overlay_utility_tree", 0x6000, 0x7000),
        ("overlay_tree_controller", 0x7000, 0x8000),
        ("overlay_content_view", 0x8000, 0x9000),
        ("tree_queue", 0x9000, 0xEFF0),
        ("overlay_recursive", 0xF000, 0x10000),
    ]
    overlap_free = all(layout[index][2] <= layout[index + 1][1]
                       for index in range(len(layout) - 1))
    checks = {
        "scripting_sidecars": all(all(x["checks"].values()) for x in scripting.values()),
        "reu_script_regions_disjoint": all(script_layout[i][2] <= script_layout[i+1][1] for i in range(len(script_layout)-1)),
        "resident_below_b600": resident_end < 0xB600,
        "resident_below_kernal_scratch": resident_end < 0xB5AC,
        "software_stack_top_d000": stack_top == 0xD000,
        "monolithic_below_c600": monolithic_end < 0xC600,
        "reu_regions_disjoint": overlap_free,
        "reu_overlay_regions_disjoint": all(
            overlay_layout[index][2] <= overlay_layout[index + 1][1]
            for index in range(len(overlay_layout) - 1)),
        "reu_batch_regions_disjoint": all(batch_layout[i][2] <= batch_layout[i+1][1] for i in range(len(batch_layout)-1)),
        "reu_console_ring_fits_bank": 800 * 80 <= 0x10000,
        "stream_policy_sidecar": all(stream["checks"].values()),
        "iec_config_policy_sidecar": all(iec["checks"].values()),
        "udos_file_sidecars": all(all(x["checks"].values()) for x in udos.values()),
        "native_files_policy_sidecar": all(files_plan["checks"].values()),
        "native_files_sidecar": all(files["checks"].values()),
        "native_iec_media_sidecar": all(native["checks"].values()),
        "presentation_sidecar": all(present["checks"].values()),
        "command_help_sidecar": all(command_help["checks"].values()),
        "ui_sidecar": all(ui["checks"].values()),
        "match_sidecar": all(match["checks"].values()),
        "plan_sidecar": all(plan["checks"].values()),
        "help_sidecar": all(help_sidecar["checks"].values()),
        "backend_sidecar": all(backend["checks"].values()),
        "cmdpath_sidecar": all(cmdpath["checks"].values()),
        "drive_sidecar": all(drive["checks"].values()),
        "utility_sidecar": all(utility["checks"].values()),
        "tree_sidecar": all(tree["checks"].values()),
        "content_sidecar": all(content["checks"].values()),
        "batch_sidecar": all(batch["checks"].values()),
        "recursive_sidecar": all(recursive["checks"].values()),
        "tape_sidecar": all(tape["checks"].values()),
    }
    passed = all(checks.values())
    report = {
        "schema": "readyfs-build-report-v1",
        "status": "pass" if passed else "fail",
        "checks": checks,
        "resident": {
            "end": resident_end,
            "limit": 0xB5AB,
            "free_bytes": 0xB5AC - resident_end - 1,
        },
        "software_stack": {"top": stack_top},
        "monolithic": {"end": monolithic_end, "limit": 0xC5FF},
        "sidecars": {"scripting": scripting, "udos_files": udos, "native_files_policy": files_plan, "native_files": files, "native_iec_media": native, "iec_config_policy": iec, "stream_policy": stream, "command_help": command_help, "presentation": present, "matcher": match, "planner_executor": plan,
                     "extended_help": help_sidecar,
                     "backend_controller": backend,
                     "cmdpath_translator": cmdpath,
                     "drive_profiler": drive,
                     "utility_controller": utility,
                     "tree_controller": tree,
                     "content_controller": content,
                     "batch_alias_controller": batch,
                     "command_editor_controller": ui,
                     "recursive_controller": recursive,
                     "tape_core_controller": tape},
        "reu_session_regions": [
            {"name": name, "start": start, "end_exclusive": end,
             "bytes": end - start}
            for name, start, end in layout
        ],
        "reu_overlay_bank_regions": [
            {"name": name, "start": start, "end_exclusive": end,
             "bytes": end - start}
            for name, start, end in overlay_layout
        ],
        "reu_batch_bank_regions": [
            {"name": name, "start": start, "end_exclusive": end,
             "bytes": end-start} for name,start,end in batch_layout
        ],
        "reu_script_bank_regions": [
            {"name": name, "start": start, "end_exclusive": end, "bytes": end-start}
            for name, start, end in script_layout
        ],
        "reu_console_bank_regions": [
            {"name":"output_row_ring", "start":0, "end_exclusive":64000,
             "bytes":64000, "physical_rows":800, "bytes_per_row":80}
        ],

    }
    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "readyfs-build-report.json"
    md_path = OUT / "readyfs-build-report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ReadyFS Build Report",
        "",
        f"Status: **{report['status'].upper()}**",
        "",
        "- DOS batch scripting: four cached sidecars and a dedicated fifth high REU bank; tape spool stops below it.",
        f"- Resident end: `${resident_end:04X}`; "
        f"{report['resident']['free_bytes']} safe bytes remain before "
        "KERNAL scratch at `$B5AC`.",
        f"- Monolithic end: `${monolithic_end:04X}` (limit `$C5FF`).",
        f"- Overlay-build cc65 software-stack top: `${stack_top:04X}`.",
        f"- IEC configuration policy payload: `${iec['payload_bytes']:X}` bytes (seventeenth cached sidecar).",
        "- UltimateDOS control: four cold phases in session slots $3000–$6FFF; code/constants/BSS are cached together.",
        f"- Native file policy payload: `${files_plan['payload_bytes']:X}` bytes (twentieth cached sidecar; retired session scroll region).",
        f"- Native filesystem payload: `${files['payload_bytes']:X}` bytes (nineteenth cached sidecar).",
        f"- Native IEC/media payload: `${native['payload_bytes']:X}` bytes (eighteenth cached sidecar).",
        f"- Stream policy payload: `${stream['payload_bytes']:X}` bytes (sixteenth cached sidecar).",
        f"- Matcher payload: "
        f"`${match['payload_bytes']:X}` bytes.",
        f"- Planner/executor payload: `${plan['payload_bytes']:X}` bytes.",
        f"- Help/journal payload: `${help_sidecar['payload_bytes']:X}` bytes.",
        f"- Backend/controller payload: `${backend['payload_bytes']:X}` bytes.",
        f"- CMD/SD2IEC translator payload: `${cmdpath['payload_bytes']:X}` "
        "bytes (cached runtime sidecar with boot self-test).",
        f"- IEC drive profiler payload: `${drive['payload_bytes']:X}` bytes "
        "(resident-owned command-channel I/O).",
        f"- Utility/history payload: "
        f"`${utility['payload_bytes']:X}` bytes "
        "(seventh REU-cached runtime sidecar).",
        f"- Cooperative tree-controller payload: `${tree['payload_bytes']:X}` "
        "bytes (eighth REU-cached runtime sidecar).",
        f"- Bounded content-view payload: `${content['payload_bytes']:X}` "
        "bytes (ninth REU-cached runtime sidecar).",
        f"- Batch/alias payload: `${batch['payload_bytes']:X}` bytes "
        "(tenth sidecar in a dedicated REU bank).",
        f"- Recursive controller/name translator payload: "
        f"`${recursive['payload_bytes']:X}` bytes "
        "(eleventh sidecar; cached above the tree queue).",
        f"- Tape/core policy and signature payload: "
        f"`${tape['payload_bytes']:X}` bytes "
        "(twelfth sidecar; dedicated batch-bank cache).",
        f"- Command/editor payload: `${ui['payload_bytes']:X}` bytes (thirteenth sidecar).",
        f"- Presentation payload: `${present['payload_bytes']:X}` bytes (fourteenth sidecar).",
        f"- Command-help payload: `${command_help['payload_bytes']:X}` bytes (fifteenth sidecar).",
        f"- REU regions disjoint: {'yes' if overlap_free else 'NO'}.",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {'PASS' if ok else 'FAIL'}: `{name}`"
                 for name, ok in checks.items())
    lines.extend(["", "## REU Session Map", "",
                  "| Region | Start | End (exclusive) | Bytes |",
                  "|---|---:|---:|---:|"])
    lines.extend(f"| {name} | `${start:04X}` | `${end:04X}` | {end-start} |"
                 for name, start, end in layout)
    lines.extend(["", "## REU Overlay Bank Map", "",
                  "| Region | Start | End (exclusive) | Bytes |",
                  "|---|---:|---:|---:|"])
    lines.extend(f"| {name} | `${start:04X}` | `${end:04X}` | {end-start} |"
                 for name, start, end in overlay_layout)
    lines.extend(["", "## REU Batch Bank Map", "",
                  "| Region | Start | End (exclusive) | Bytes |",
                  "|---|---:|---:|---:|",
                  "| batch_overlay_cache | `$0000` | `$1000` | 4096 |",
                  "| batch_script | `$1000` | `$5000` | 16384 |",
                  "| batch_checkpoint | `$5000` | `$5100` | 256 |",
                  "| tape_overlay_cache | `$5100` | `$6100` | 4096 |"])
    lines.extend(["", "## REU Scripting Bank Map", "", "| Region | Start | End (exclusive) | Bytes |", "|---|---:|---:|---:|"])
    for name, start, end in script_layout:
        lines.append(f"| {name} | `${start:04X}` | `${end:04X}` | {end-start} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ReadyFS build report: {report['status']} ({md_path})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
