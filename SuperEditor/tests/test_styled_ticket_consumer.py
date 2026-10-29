"""Actual 6510 proof for the C33/R25 styled READY-ticket consumer.

The fixture uses the production C6 edit path to create ADMITTED.  It then
supplies C14's public boundary only: an independently projected provisional
plan, a READY checksum, request release, and READY written last.  Production
C33/R25 must paint exactly the ticket rows, rebase the retained anchors, publish
the style descriptor valid-last, and retire the ticket without frame15.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import importlib.util
import json

import test_cache_hotpath_profile as profile
import test_styled_ticket_admission as admission


ROOT = profile.ROOT
READY = 0x5A


def configure(gate):
    return admission.configure(gate)


def make_ready(f, mode, source):
    width = (40, 60, 80)[mode]
    tx = bytearray(f.read(f.s["se_st_tx"], admission.TX_BYTES))
    assert tx[0] == admission.TX_ADMITTED
    first = tx[8] & 0x1F
    count = tx[9] & 0x1F
    nowrap = bool(f.get("se_l_mode", 1))
    pan = f.get("se_l_pan") if nowrap else 0
    anchors = profile.observer.geos.grid.row_starts(
        source, f.get("se_v_top"), width, nowrap)
    if mode == 0:
        plan = profile.observer.geos.grid.semantic_plan(
            source, anchors, nowrap, pan, lexical=True)
        address = 0x4400
    else:
        plan = profile.observer.geos.grid.projected_plan(
            source, anchors, width, pan)
        address = 0x4800
    f.m.load(address, plan)

    tx[0] = READY
    tx[1] = admission.TX_SEED ^ READY
    for value in tx[2:]:
        tx[1] ^= value
    # Body/check first, request release next, phase last.
    f.m.load(f.s["se_st_tx"] + 1, tx[1:])
    f.put("se_st_request", 0, 1)
    f.put("se_st_tx", READY, 1)
    return width, first, count, anchors


def exact_rows(f, source, mode, first, count):
    (pixels, attrs), wanted_anchors, seen, _ = \
        profile.observer.geos.grid.expected(f, source)
    if mode == 0:
        lo = (first + 2) * 40
        hi = lo + count * 40
        assert f.read(0x4000 + lo, hi - lo) == pixels[lo:hi]
        assert f.read(0xD800 + lo, hi - lo) == attrs[lo:hi]
    else:
        bitmap_lo = (first + 2) * 320
        bitmap_hi = bitmap_lo + count * 320
        attr_lo = (first + 2) * 40
        attr_hi = attr_lo + count * 40
        assert f.read(0x6000 + bitmap_lo, bitmap_hi - bitmap_lo) == \
            pixels[bitmap_lo:bitmap_hi]
        assert f.read(0x4000 + attr_lo, attr_hi - attr_lo) == \
            attrs[attr_lo:attr_hi]
    actual_anchors = tuple(
        int.from_bytes(f.read(f.s["se_v_rows"] + index * 3, 3), "little")
        for index in range(22)) + (f.get("se_v_bottom"),)
    assert actual_anchors == wanted_anchors
    assert seen == (f.get("se_v_caret_row", 1),
                    f.get("se_v_caret_col", 1))


def run(out, fixture=None):
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location(
        "styled_ticket_consumer_runner",
        ROOT / "src/cache/hotpath-profile-probe/runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    saved_runner = profile.observer.runner
    profile.observer.runner = runner.build
    try:
        gate = profile.observer.Gate(out, fixture)
    finally:
        profile.observer.runner = saved_runner
    f = gate.f
    names = configure(gate)
    cases = []
    try:
        for mode, width in enumerate((40, 60, 80)):
            for action in ("insert", "delete"):
                at = admission.setup(f, mode)
                old_generation = f.get("se_st_generation", 2)
                if action == "insert":
                    f.key(admission.Q)
                    source = (admission.TEXT[:at] + bytes((admission.Q,)) +
                              admission.TEXT[at:])
                else:
                    f.key(0x14)
                    source = admission.TEXT[:at - 1] + admission.TEXT[at:]
                _, first, count, _ = make_ready(f, mode, source)

                # NR_COUNT bounds glyph rasterization, but the native leaf
                # must still clear the complete physical row before painting
                # the shorter live prefix. Poison the whole destination here
                # so insert/delete exactness proves stale suffix removal.
                if mode:
                    physical = first + 2
                    f.m.load(0x6000 + physical * 320,
                             bytes((0xA5,)) * 320)
                    f.m.load(0x4000 + physical * 40,
                             bytes((0xFE,)) * 40)

                # Every packet flag byte must be produced by this transaction.
                # Poisoning catches padding cells that skip the live/end paths
                # and would otherwise inherit selection/reverse state.
                f.m.load(0x88C4 + 160, bytes((2,)) * 80)

                loads = f.get("se_overlay_loads", 2)
                gate.dll.hp_begin(f.get("se_e_draw_sequence", 2))
                try:
                    f.put("se_overlay_frame", 1, 1)
                    registers, instructions = f.fast_call(
                        f.s["se_overlay_call"], a=33, x=1, limit=8_000_000)
                finally:
                    gate.dll.hp_end()
                assert not registers.p & 1 and registers.a == 0
                expected_state = {
                    "se_st_tx": 0,
                    "se_st_valid": 1,
                    "se_st_request": 0,
                    "se_st_cp_valid": 1,
                    "se_f_owner": 0,
                }
                assert {name: f.get(name, 1) for name in expected_state} == \
                    expected_state
                assert f.get("se_st_generation", 2) == \
                    ((old_generation + 1) & 0xFFFF)
                descriptor_revision = f.read(f.s["se_st_descriptor"] + 17, 4)
                current_revision = f.read(f.s["se_r_revision"], 4)
                assert descriptor_revision == current_revision, \
                    (width, action, descriptor_revision.hex(), current_revision.hex())
                descriptor_length = f.read(f.s["se_st_descriptor"] + 21, 3)
                current_length = len(source).to_bytes(3, "little")
                assert descriptor_length == current_length, \
                    (width, action, descriptor_length.hex(), current_length.hex())
                exact_rows(f, source, mode, first, count)

                entries = {
                    name: {str(frame): int(gate.dll.hp_op(index + 1, frame))
                           for frame in range(256)
                           if gate.dll.hp_op(index + 1, frame)}
                    for index, name in enumerate(names)
                    if gate.dll.hp_get(3, index + 1)
                }
                assert entries.get("geostail") == {"14": 1, "17": 1}
                assert "15" not in entries["geostail"]
                assert entries.get("grid") == {"1": 1}
                native = "grid60" if mode == 1 else "grid80"
                if mode:
                    assert entries.get(native) == {"0": 1, "2": 1}
                cases.append({
                    "tag": f"{width}-{action}",
                    "rows": count,
                    "instructions": instructions,
                    "loads": (f.get("se_overlay_loads", 2) - loads) & 0xFFFF,
                    "entries": entries,
                })
                print("PASS", cases[-1]["tag"], instructions,
                      "instructions", cases[-1]["loads"], "loads", flush=True)

        # A styled line growing from width-1 to width requires an additional
        # terminal caret row.  The READY consumer must reject the stale
        # one-row ticket before painting or publishing it.
        mode, width = 1, 60
        data = b"A" * (width - 1) + b"\rTail.\rAfter."
        at = admission.setup(f, mode, data, position=width - 2)
        f.key(admission.Q)
        source = data[:at] + bytes((admission.Q,)) + data[at:]
        make_ready(f, mode, source)
        before = (f.read(0x4000, 1000), f.read(0x6000, 8000),
                  f.read(f.s["se_v_rows"], 66), f.get("se_v_bottom", 3))
        f.put("se_overlay_frame", 1, 1)
        registers, instructions = f.fast_call(
            f.s["se_overlay_call"], a=33, x=1, limit=8_000_000)
        assert registers.a == 2, ("styled width-1 to width growth was admitted",
                                  registers.a, registers.p,
                                  f.get("se_st_tx", 1), f.get("se_l_mode", 1))
        assert f.get("se_st_tx", 1) == 0, "refusal left READY published"
        after = (f.read(0x4000, 1000), f.read(0x6000, 8000),
                 f.read(f.s["se_v_rows"], 66), f.get("se_v_bottom", 3))
        assert after == before, "refusal changed pixels or row authority"
        cases.append({"tag": "60-styled-wrap-growth-refusal",
                      "instructions": instructions, "rows": 1, "loads": 0})
        print("PASS", cases[-1]["tag"], instructions, "instructions", flush=True)
        result = {
            "status": "PASS",
            "identity": gate.identity,
            "cases": cases,
            "scope": __doc__,
        }
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    destination = ROOT / "build/styled-ticket-consumer" / \
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", destination, flush=True)
    result = run(destination,
                 args.fixture.resolve() if args.fixture else None)
    print(json.dumps({"status": result["status"],
                      "output": str(destination)}, indent=2))
