"""Profile styled fixed-grid publication and parser convergence on real VICE.

This is a read-only product profiler.  It freezes an explicit immutable fixture,
uses public syntax/mode/top/input/undo paths, and delegates source, pixel, stack,
catalog, REU payload, and publication validation to test_display_timing_vice.
The extra trace points count real block/inline/lexical parser entries only while
the corresponding registered overlay is the active overlay frame.

The current-baseline report deliberately does not make the desired convergence
contract a passing requirement.  ``acceptance-gates.json`` records those gates
separately so a candidate can be compared without silently rebaselining it.
Own monitor port 8140; the .NET runner owns its text ports and emulator process.
"""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import threading
import zipfile

import test_display_timing_vice as timing
import test_reu_capacity_vice as runner
import vice_plan


ROOT = timing.ROOT
MODES = ((0, 40), (1, 60), (2, 80))
CAPABILITIES = (("full", 3), ("markdown", 1))
PARSER_SYMBOLS = {
    "viewsource": (
        "se_sm_init",
        "se_sm_feed",
        "se_sm_finish",
    ),
    "styler": (
        "se_si_init",
        "se_si_feed",
        "se_si_finish",
    ),
    "lexical": ("se_sl_init", "se_sl_feed", "se_sl_finish"),
}
TRACE_RE = re.compile(
    r"\.C:([0-9a-f]{4}).*?A:([0-9a-f]{2}) X:([0-9a-f]{2}).*?\s(\d+)\s*$",
    re.I,
)


def symbols(path):
    found = {
        name: int(address, 16)
        for address, name in re.findall(
            r"al ([0-9A-Fa-f]+) \.(\S+)", path.read_text()
        )
    }
    return found


class Plan(timing.Plan):
    def __init__(self, fixture, report, standard, model, phase, reuse=False):
        super().__init__(fixture, report, standard, model)
        self.out = fixture / phase
        if reuse:
            assert (self.out / "run").is_dir()
        else:
            self.out.mkdir()
        self.parser_points = {}
        self.parser_assets = {}
        for asset, required in PARSER_SYMBOLS.items():
            image = (fixture / (asset + ".seo")).read_bytes()
            assert len(image) > 36 and image[:4] == b"SEO2", asset
            self.parser_assets[asset] = {"slot": image[5], "id": image[6]}
            exported = symbols(fixture / "profile-labels" / (asset + ".lbl"))
            points = {name: exported[name] for name in required}
            base = 0xA000 if image[5] == 0 else 0xB000
            assert all(base <= address < base + 0x1000 for address in points.values())
            self.parser_points[asset] = points
            for name, address in points.items():
                # The base timing parser tolerates extra scalar cost points and
                # consequently emits these exact trace commands into plan.yaml.
                self.cost_points["parser_" + asset + "_" + name] = address

    def plan(self):
        plan = super().plan()
        plan["global_defaults"]["monitor_port_start"] = 8140
        plan["global_defaults"]["monitor_port_span"] = 1
        assert not plan["global_defaults"].get("kill_stale", False)
        return plan


def freeze(source):
    fixture = timing.freeze(source, "styled-grid-convergence-baseline")
    label_dir = fixture / "profile-labels"
    label_dir.mkdir()
    for asset in PARSER_SYMBOLS:
        built = source / "build" / "overlays"
        assert (built / (asset + ".seo")).read_bytes() == (
            fixture / (asset + ".seo")
        ).read_bytes()
        shutil.copy2(built / (asset + ".lbl"), label_dir / (asset + ".lbl"))
    return fixture


def scenario(fixture, syntax, caps):
    plan = Plan(
        fixture,
        json.loads((fixture / "editor-report.json").read_text()),
        1,
        0,
        "timing-" + syntax,
    )
    plan.cost_profile = True
    plan.boot()
    # Select capability on the empty document, then let File/Open construct the
    # first style cache in that capability.  Syntax-switch invalidation is a
    # separate behavior and must not contaminate this edit-convergence profile.
    plan.typed("syntax_" + syntax, "syntax " + syntax)
    plan.memory("caps_" + syntax, "se_render_caps", caps)
    plan.open("open_diverse", b"DIVERSE")
    source = timing.native.live.grid.fixture()
    inserted = timing.native.live.grid.native_text("Q") + source
    for mode, columns in MODES:
        tag = syntax + "-" + str(columns) + "-front-heading"
        plan.mode_to(mode)
        plan.typed(tag + "-top", "top")
        plan.memory(tag + "-caret-before", "se_hot_caret", 0, 3)
        plan.measure(
            tag,
            inserted,
            mode,
            key=inserted[0],
            category="styled-structural-front-insert",
        )
        # Return through the real history path.  The following case's source
        # oracle catches a failed undo as a duplicate insertion.
        plan.send(tag + "-undo", b"\x1a")
        plan.memory(tag + "-undo-caret", "se_hot_caret", 0, 3)
        plan.memory(tag + "-undo-length", "se_doc_length", len(source), 3)
    return plan


def parser_trace(plan, text):
    boundaries = plan.cost_points
    lookup = {}
    for asset, points in plan.parser_points.items():
        identity = plan.parser_assets[asset]
        for name, address in points.items():
            lookup.setdefault(address, []).append((asset, name, identity))

    stack = []
    events = []
    for line in text.splitlines():
        match = TRACE_RE.match(line)
        if not match:
            continue
        pc, a, x = (int(value, 16) for value in match.groups()[:3])
        clock = int(match.group(4))
        if pc == boundaries["se_overlay_call"]:
            stack.append({"id": a, "slot": x, "active": False})
        elif pc == boundaries["jump_overlay"]:
            assert stack and not stack[-1]["active"]
            stack[-1]["active"] = True
        elif pc == boundaries["overlay_payload_return"]:
            assert stack and stack[-1]["active"]
            stack[-1]["active"] = False
        elif pc == boundaries["overlay_complete_rts"]:
            assert stack and not stack[-1]["active"]
            stack.pop()
        elif pc in lookup:
            assert stack and stack[-1]["active"], (hex(pc), "parser outside overlay")
            matched = False
            for asset, name, identity in lookup[pc]:
                if (stack[-1]["slot"], stack[-1]["id"]) == (
                    identity["slot"],
                    identity["id"],
                ):
                    events.append(
                        {"asset": asset, "symbol": name, "clock": clock}
                    )
                    matched = True
                    break
            # Shared overlay windows reuse addresses.  A trace at the same PC
            # in a different active image is intentionally not a parser event.
            if not matched:
                continue
    assert not stack, "truncated overlay trace"
    return events


def grouped_parser(events):
    groups = []
    for asset, name in sorted({(event["asset"], event["symbol"]) for event in events}):
        groups.append(
            {
                "asset": asset,
                "symbol": name,
                "calls": sum(
                    event["asset"] == asset and event["symbol"] == name
                    for event in events
                ),
            }
        )
    return groups


def phase_summary(measurement, events):
    publications = measurement["publication_cycles"]
    first = publications[0]
    intervals = measurement["cost_profile"]["overlay_intervals"]
    before = [event for event in events if event["clock"] < first]
    after = [event for event in events if event["clock"] >= first]
    overlay_before = [row for row in intervals if row["end"] <= first]
    overlay_after = [row for row in intervals if row["entry"] >= first]
    overlay_spanning = [
        row for row in intervals if row["entry"] < first < row["end"]
    ]

    def overlay_groups(rows):
        result = []
        for slot, identity in sorted({(row["slot"], row["id"]) for row in rows}):
            selected = [
                row
                for row in rows
                if (row["slot"], row["id"]) == (slot, identity)
            ]
            result.append(
                {
                    "slot": slot,
                    "id": identity,
                    "calls": len(selected),
                    "payload_self": sum(row["payload_self"] for row in selected),
                    "admission": sum(row["admission"] for row in selected),
                }
            )
        return result

    return {
        "id": measurement["id"],
        "mode": measurement["mode"],
        "oracle_status": measurement.get("oracle_status", "passed"),
        "oracle_failure": measurement.get("oracle_failure"),
        "oracle_note": measurement.get("oracle_note"),
        "publication_count": len(publications),
        "publication_cycles": publications,
        "first_publish_cycles": first,
        "quiescent_cycles": measurement["emulated_cycles"],
        "parser_calls": grouped_parser(events),
        "parser_before_first": grouped_parser(before),
        "parser_after_first": grouped_parser(after),
        "parser_calls_after_first": len(after),
        "overlay_calls": measurement["counter_deltas"]["se_overlay_calls"],
        "overlay_before_first": overlay_groups(overlay_before),
        "overlay_after_first": overlay_groups(overlay_after),
        "overlay_calls_after_first": len(overlay_after),
        "overlay_spanning_first": overlay_groups(overlay_spanning),
        "counter_deltas": measurement["counter_deltas"],
    }


def markdown_expected(frame, source, full_primary, full_attributes):
    """Capability-aware independent grid oracle for Markdown (no lexer)."""
    grid = timing.native.live.geos.grid
    width = (40, 60, 80)[frame.get("se_mode", 1)]
    top = frame.get("se_v_top")
    nowrap = frame.get("se_l_mode", 1)
    pan = frame.get("se_l_pan") if nowrap else 0
    anchors = grid.row_starts(source, top, width, nowrap)
    caret = frame.get("se_hot_caret")
    marked = frame.get("se_sel_mark", 1)
    lo, hi = sorted((caret, frame.get("se_sel_anchor"))) if marked else (0, 0)
    _, _, popup = grid.logical_ui(frame, source)
    assert popup is None and frame.get("se_e_ui", 1) == 0

    if width == 40:
        plan = grid.semantic_plan(source, anchors, nowrap, pan, lexical=False)
    else:
        left = grid.semantic_plan(source, anchors, True, pan, lexical=False)
        right = grid.semantic_plan(source, anchors, True, pan + 40, lexical=False)
        plan = b"".join(
            left[row * 40 : row * 40 + 40]
            + right[row * 40 : row * 40 + width - 40]
            for row in range(22)
        )

    if width == 40:
        attributes = bytearray(full_attributes)
        seen = False
        for row, (start, stop) in enumerate(zip(anchors, anchors[1:])):
            end = stop - 1 if stop > start and source[stop - 1] == 13 else stop
            for column in range(40):
                position = start + pan + column
                ink = 1
                if position <= end:
                    style = plan[row * 40 + column] if position < end else 1
                    ink = style & 15
                    if lo <= position < hi:
                        ink = 3
                    if position == caret and not seen:
                        ink = 7 if marked else 3
                        seen = True
                attributes[(row + 2) * 40 + column] = ink
        return full_primary, bytes(attributes)

    attributes = bytearray(full_attributes)
    font = frame.fonts["narrow5.bin" if width == 60 else "narrow4.bin"]
    seen = False
    for row, (start, stop) in enumerate(zip(anchors, anchors[1:])):
        end = stop - 1 if stop > start and source[stop - 1] == 13 else stop
        characters = []
        flags = []
        roles = []
        for column in range(width):
            position = start + pan + column
            characters.append(source[position] if position < end else 32)
            style = plan[row * width + column] if position < end else 1
            roles.append(grid.semantic_role(style))
            flag = 1 if style & 128 else 0
            if position <= end:
                if lo <= position < hi:
                    flag |= 2
                if position == caret and not seen:
                    flag |= 4
                    seen = True
            flags.append(flag)
        _, row_attributes = grid.narrow_row(
            characters, flags, width, font, roles, True
        )
        attributes[(row + 2) * 40 : (row + 3) * 40] = row_attributes
    return full_primary, bytes(attributes)


def verify_native_pixels(plan, item, primary, attributes):
    if item["mode"] == 0:
        font = (plan.e / "chargen.bin").read_bytes()[0x800:0x1000]
        bits = bytearray(8000)
        attrs = bytearray(1000)
        for index in range(1000):
            bits[(index // 40) * 320 + (index % 40) * 8 :
                 (index // 40) * 320 + (index % 40) * 8 + 8] = font[
                primary[index] * 8 : primary[index] * 8 + 8
            ]
            attrs[index] = (attributes[index] << 4) | 6
    else:
        bits, attrs = primary, attributes
    width, height, pixels = timing.read_png(
        plan.out / ("native-" + item["id"] + ".png")
    )
    assert (width, height) == (384, 272)
    palette = {}
    for y in range(200):
        for x in range(320):
            attribute = attrs[(y // 8) * 40 + x // 8]
            ink = bits[(y // 8) * 320 + (x // 8) * 8 + y % 8] & (128 >> (x % 8))
            role = attribute >> 4 if ink else attribute & 15
            pixel = pixels[(35 + y) * width + 32 + x]
            assert pixel == palette.setdefault(role, pixel), (
                item["id"], "native VIC pixel", x, y
            )


def failed_oracle_measurement(plan, item, error):
    ident = item["id"]
    text = (plan.out / ("stopwatch-" + ident + ".log")).read_text(
        encoding="utf-8-sig"
    )
    cycles = [int(value) for value in re.findall(r"Stopwatch:\s*(\d+)", text, re.I)]
    assert len(cycles) == 1
    published = []
    service = []
    entered = None
    for pc, clock in re.findall(
        r"(?m)^\.C:([0-9a-f]{4})\s+[^\r\n]*?\s+(\d+)\s*$", text, re.I
    ):
        pc, clock = int(pc, 16), int(clock)
        if pc == plan.s["se_editor_service"]:
            assert entered is None
            entered = clock
        elif pc == plan.service_return:
            assert entered is not None
            service.append(clock - entered)
            entered = None
        elif pc == plan.publish_pc:
            published.append(clock)
    assert entered is None and published

    capture = plan.out / "captures"
    before = (capture / (ident + "-before-ram.bin")).read_bytes()
    finished = (capture / (ident + "-finished-ram.bin")).read_bytes()
    ram = (capture / (ident + "-ram.bin")).read_bytes()
    colors = (capture / (ident + "-colors.bin")).read_bytes()
    frame = timing.Captured(plan.s, ram, colors, plan.e)
    frame.colored = True

    def counter(raw, name, width):
        return int.from_bytes(raw[plan.s[name] : plan.s[name] + width], "little")

    counters = {
        name: (counter(finished, name, width) - counter(before, name, width))
        % (1 << (8 * width))
        for name, width in (
            ("se_overlay_loads", 2),
            ("se_overlay_hits", 2),
            ("se_overlay_calls", 2),
            ("se_reu_dma_calls", 2),
            ("se_reu_dma_bytes", 3),
            ("se_e_draw_sequence", 2),
        )
    }
    assert len(published) == counters["se_e_draw_sequence"]
    reus = timing.native.live.grid.reu_images(plan.out / "run")
    source = bytes.fromhex(item["source"])
    assert timing.native.live.merged(frame, reus[ident]) == source
    assert (capture / (ident + "-stack-before.bin")).read_bytes() == (
        capture / (ident + "-stack-after.bin")
    ).read_bytes()
    assert frame.read(0xC600, 1024) == plan.canary
    assert all(
        frame.get(name, 1) == 0
        for name in (
            "se_e_job",
            "se_e_draw_busy",
            "se_e_redraw",
            "se_doc_read_locks",
            "se_f_owner",
            "se_e_error",
        )
    )
    (full_primary, full_attributes), _, _, _ = timing.native.live.geos.grid.expected(
        frame, source
    )
    assert frame.get("se_render_caps", 1) == 1, (
        ident,
        "only the known Full-only oracle assumption may be recovered",
    )
    expected_primary, expected_attributes = markdown_expected(
        frame, source, full_primary, full_attributes
    )
    if item["mode"] == 0:
        actual_primary = frame.read(0x4000, 1000)
        actual_attributes = bytes(value & 15 for value in colors)
        primary_kind = "screen"
        attribute_kind = "color_ram"
    else:
        actual_primary = frame.read(0x6000, 8000)
        actual_attributes = frame.read(0x4000, 1000)
        primary_kind = "bitmap"
        attribute_kind = "attributes"
    primary_differences = [
        index
        for index, values in enumerate(zip(actual_primary, expected_primary))
        if values[0] != values[1]
    ]
    attribute_differences = [
        index
        for index, values in enumerate(zip(actual_attributes, expected_attributes))
        if values[0] != values[1]
    ]
    failure = {
        "exception": repr(error),
        "primary_kind": primary_kind,
        "primary_difference_count": len(primary_differences),
        "primary_first_offsets": primary_differences[:32],
        "attribute_kind": attribute_kind,
        "attribute_difference_count": len(attribute_differences),
        "attribute_first_offsets": attribute_differences[:32],
        "actual_primary_sha256": hashlib.sha256(actual_primary).hexdigest(),
        "expected_primary_sha256": hashlib.sha256(expected_primary).hexdigest(),
        "actual_attributes_sha256": hashlib.sha256(actual_attributes).hexdigest(),
        "expected_attributes_sha256": hashlib.sha256(expected_attributes).hexdigest(),
    }
    (plan.out / ("oracle-failure-" + ident + ".json")).write_text(
        json.dumps(failure, indent=2) + "\n"
    )
    recovered = not primary_differences and not attribute_differences
    if recovered:
        verify_native_pixels(
            plan, item, expected_primary, expected_attributes
        )
    return dict(
        item,
        oracle_status="passed" if recovered else "failed",
        oracle_failure=None if recovered else failure,
        oracle_note={
            "base_full_only_oracle_rejected": repr(error),
            "capability_aware_markdown_oracle": "passed" if recovered else "failed",
            "detail": failure,
        },
        emulated_cycles=cycles[0],
        service_cycles=service,
        service_calls=len(service),
        service_peak_cycles=max(service) if service else None,
        first_publish_cycles=published[0],
        publication_cycles=published,
        counter_deltas=counters,
        cost_profile=timing.cost_summary(
            plan, text, ident, counters["se_overlay_calls"]
        ),
        caret=frame.get("se_hot_caret"),
        top=frame.get("se_v_top"),
        pending=frame.get("se_hot_pending", 1),
    )


def evaluate_plan(plan):
    original = plan.measurements
    verified = []
    cases = []
    for item in original:
        plan.measurements = [item]
        try:
            individual = timing.evaluate(plan)
            measurement = individual["measurements"][0]
            measurement["oracle_status"] = "passed"
            shutil.copy2(
                plan.out / "result.json", plan.out / ("result-" + item["id"] + ".json")
            )
        except AssertionError as error:
            measurement = failed_oracle_measurement(plan, item, error)
        verified.append(measurement)
        log = (plan.out / ("stopwatch-" + measurement["id"] + ".log")).read_text(
            encoding="utf-8-sig"
        )
        events = parser_trace(plan, log)
        cases.append(phase_summary(measurement, events))
    plan.measurements = original
    result = {
        "status": "passed"
        if all(row["oracle_status"] == "passed" for row in verified)
        else "failed",
        "identity": json.loads((plan.e / "freeze.json").read_text()),
        "measurements": verified,
    }
    (plan.out / "result-all-cases.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result, cases


def write_aggregate(fixture, evaluated):
    cases = [case for _, rows in evaluated for case in rows]
    identities = [result["identity"] for result, _ in evaluated]
    assert len(cases) == 6 and identities[0] == identities[1]
    def parser_calls(case, asset, symbol):
        return next(
            (
                row["calls"]
                for row in case["parser_calls"]
                if row["asset"] == asset and row["symbol"] == symbol
            ),
            0,
        )

    # Q changes the first 31-byte logical row's block classification.  The
    # outgoing state at its CR is neutral and matches the old second-row
    # checkpoint, so a retained-carry candidate must converge there.  No code
    # block changed, hence Full must not invoke the lexical parser at all.
    bounded_front_row = all(
        parser_calls(case, "viewsource", "se_sm_feed") <= 31
        and parser_calls(case, "styler", "se_si_feed") <= 31
        and parser_calls(case, "lexical", "se_sl_feed") == 0
        for case in cases
    )
    candidate = {
        "status": "passed" if all(
            case["oracle_status"] == "passed"
            and case["publication_count"] == 1
            and case["parser_calls_after_first"] == 0
            and case["overlay_calls_after_first"] == 0
            and not case["overlay_spanning_first"]
            for case in cases
        ) and bounded_front_row else "failed",
        "requirements": {
            "all_six_full_markdown_40_60_80_cases_present": len(cases) == 6,
            "all_independent_oracles_pass": all(
                case["oracle_status"] == "passed" for case in cases
            ),
            "one_converged_publication_per_edit": all(
                case["publication_count"] == 1 for case in cases
            ),
            "no_parser_work_after_publication": all(
                case["parser_calls_after_first"] == 0 for case in cases
            ),
            "no_overlay_work_after_publication": all(
                case["overlay_calls_after_first"] == 0 for case in cases
            ),
            "no_overlay_straddles_publication": all(
                not case["overlay_spanning_first"] for case in cases
            ),
            "bounded_front_row_reparse": bounded_front_row,
        },
        "bounded_front_row_contract": {
            "edited_row_bytes_through_CR": 31,
            "maximum_block_feed_calls": 31,
            "maximum_inline_feed_calls": 31,
            "maximum_lexical_feed_calls_for_unchanged_code_blocks": 0,
        },
        "interpretation": (
            "A candidate passes only when the structural edit is withheld until its "
            "styled fixed-grid frame has converged, then publishes exactly once with "
            "no parser or overlay tail. Source/pixels/catalog/stack/REU correctness is "
            "independently enforced by result.json. The edit changes only the first "
            "31-byte logical row and returns to the prior neutral carry at its CR, so "
            "block/inline parsing must stop there and unchanged code blocks must not "
            "invoke the lexer."
        ),
    }
    baseline = {
        "status": "passed"
        if all(case["oracle_status"] == "passed" for case in cases)
        else "failed",
        "fixture": str(fixture),
        "identity": identities[0],
        "standard": "PAL",
        "scope": (
            "Real VICE instruction-entry-to-quiescence cycles for one structural "
            "front insertion in Full and Markdown at 40/60/80 columns. Public editor "
            "commands and input only; no production patch or semantic-state injection."
        ),
        "cases": cases,
        "candidate_gate_status": candidate["status"],
    }
    (fixture / "styled-grid-convergence-baseline.json").write_text(
        json.dumps(baseline, indent=2) + "\n"
    )
    (fixture / "acceptance-gates.json").write_text(
        json.dumps(candidate, indent=2) + "\n"
    )
    print(json.dumps(baseline, indent=2), flush=True)
    return baseline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    fixture = freeze(args.fixture.resolve())
    with zipfile.ZipFile(
        fixture / "styled-grid-convergence-verifier.zip",
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for module in (Path(__file__), ROOT / "tests" / "test_display_timing_vice.py"):
            archive.write(module, module.relative_to(ROOT))

    evaluated = []
    for syntax, caps in CAPABILITIES:
        plan = scenario(fixture, syntax, caps)
        encoded = plan.plan()
        assert len({step["id"] for step in encoded["steps"]}) == len(
            encoded["steps"]
        )
        (plan.out / "plan.yaml").write_text(json.dumps(encoded, indent=2) + "\n")
        (plan.out / "measurements.json").write_text(
            json.dumps(plan.measurements, indent=2) + "\n"
        )
        print("RUN", syntax, fixture, len(plan.steps), "steps", flush=True)
        stop = threading.Event()

        def watch_owned_process():
            while not stop.wait(0.05):
                process = subprocess.run(
                    ["ps", "-axo", "pid=,ppid=,command="],
                    capture_output=True,
                    text=True,
                )
                for line in process.stdout.splitlines():
                    if "/x64sc " in line and str(fixture / "working.d81") in line:
                        values = line.strip().split(None, 2)
                        (plan.out / "owned-process.json").write_text(
                            json.dumps(
                                {"PID": int(values[0]), "command": values[2]},
                                indent=2,
                            )
                            + "\n"
                        )
                        return

        watcher = threading.Thread(target=watch_owned_process, daemon=True)
        watcher.start()
        try:
            project = timing.native.live.grid.synchronous_project(plan.out)
            vice_plan.PROJECT = project
            build = subprocess.run(
                ["dotnet", "build", str(project), "--nologo"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            (plan.out / "dotnet-build.log").write_text(build.stdout + build.stderr)
            assert build.returncode == 0
            runner.run_owned_plan(encoded, plan.out, timeout=900)
            evaluated.append(evaluate_plan(plan))
        finally:
            stop.set()
            watcher.join(timeout=2)
            owned = plan.out / "owned-process.json"
            if owned.exists():
                process = json.loads(owned.read_text())
                current = subprocess.run(
                    ["ps", "-p", str(process["PID"]), "-o", "pid=,comm="],
                    capture_output=True,
                    text=True,
                )
                assert not current.stdout.strip()
                process["closed"] = True
                (plan.out / "closure.json").write_text(
                    json.dumps(process, indent=2) + "\n"
                )
    write_aggregate(fixture, evaluated)


if __name__ == "__main__":
    main()
