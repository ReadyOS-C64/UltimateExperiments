"""Focused actual-C33/R25 proof for row-relative packet construction.

The test drives public edits through the packaged direct-row transaction and a
real READY styled ticket.  It poisons all three packet planes before every
accepted consume, then checks the produced characters, roles and selector
flags byte-for-byte.  The cases cover 24-bit row origins, a retained wrapped
row, no-wrap pan, empty/short/end cells, and the exact-width refusal boundary.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import importlib.util
import json

import test_cache_hotpath_profile as profile
import test_plain_direct_row_hotpath as direct
import test_styled_ticket_admission as admission
import test_styled_ticket_consumer as consumer


ROOT = profile.ROOT
PACKET = 0x88C4
POISON_CHAR = 0xA5
POISON_ROLE = 13
POISON_FLAG = 0xFF


def poison(f):
    f.m.load(PACKET, (bytes((POISON_CHAR,)) * 80 +
                      bytes((POISON_ROLE,)) * 80 +
                      bytes((POISON_FLAG,)) * 80))


def anchor(f, row):
    if row == 22:
        return f.get("se_v_bottom", 3)
    return int.from_bytes(f.read(f.s["se_v_rows"] + row * 3, 3), "little")


def assert_packet(f, source, width, tag, *, start=None, roles=None):
    """Check the final one-row packet, including the real endpoint and padding."""
    if start is None:
        row = f.get("se_v_caret_row", 1)
        start, stop = anchor(f, row), anchor(f, row + 1)
        end = stop - 1 if stop > start and source[stop - 1] == 13 else stop
    else:
        cr = source.find(b"\r", start)
        end = len(source) if cr < 0 else cr
    content = source[start:min(end, start + width)]
    wanted_chars = content + bytes((32,)) * (width - len(content))
    wanted_roles = bytes(width) if roles is None else roles
    wanted_flags = bytearray(width)
    caret = f.get("se_hot_caret")
    column = caret - start
    if 0 <= column < width and caret <= end:
        wanted_flags[column] = 4
    raw = f.read(PACKET, 240)
    assert raw[:width] == wanted_chars, (tag, "packet chars", start, end)
    assert raw[80:80 + width] == wanted_roles, (tag, "packet roles")
    assert raw[160:160 + width] == wanted_flags, (tag, "packet flags")
    # Narrow packets own exactly their logical width; this also proves the
    # poison is effective rather than accidentally matching cleared padding.
    if width < 80:
        assert raw[width:80] == bytes((POISON_CHAR,)) * (80 - width)
        assert raw[80 + width:160] == bytes((POISON_ROLE,)) * (80 - width)
        assert raw[160 + width:240] == bytes((POISON_FLAG,)) * (80 - width)
    return {"start": start, "end": end, "caret_column": column,
            "packet_sha256": __import__("hashlib").sha256(raw).hexdigest()}


def assert_direct_route(row, tag):
    entries = row["entries"]
    direct.assert_plain(entries, tag)
    assert entries.get("geostail", {}).get("ops", {}).get("18") == 1, \
        (tag, "missing C33 prepare", entries)
    assert entries.get("geostail", {}).get("ops", {}).get("14") == 1, \
        (tag, "missing R25 admission", entries)
    assert entries.get("geostail", {}).get("ops", {}).get("17") == 1, \
        (tag, "missing R25 finish", entries)
    assert entries.get("grid", {}).get("ops", {}).get("1") == 1, \
        (tag, "not one R25 packet consume", entries)
    assert not ({"layout", "viewsource"} & entries.keys()), \
        (tag, "fell back instead of consuming the packet", entries)


def direct_case(g, names, tag, mode, data, position, key):
    f = g.f
    direct.setup(f, mode, data, position)
    poison(f)
    expected = (data[:position - 1] + data[position:] if key == 0x14 else
                data[:position] + bytes((key,)) + data[position:])
    row = direct.observation(g, names, tag, lambda: f.key(key))
    assert f.merged() == expected, (tag, "source")
    direct.pixels(f, expected, tag)
    assert_direct_route(row, tag)
    width = (40, 60, 80)[mode]
    packet = assert_packet(f, expected, width, tag)
    row.update(tag=tag, mode=mode, width=width,
               source_bytes=len(expected), packet=packet)
    print("PASS", tag, row["instructions"], "instructions", flush=True)
    return row


def refusal_case(g, names, tag, mode, data, position, key):
    f = g.f
    direct.setup(f, mode, data, position)
    expected = (data[:position - 1] + data[position:] if key == 0x14 else
                data[:position] + bytes((key,)) + data[position:])
    row = direct.observation(g, names, tag, lambda: f.key(key))
    assert f.merged() == expected, (tag, "source")
    direct.pixels(f, expected, tag)
    assert direct.PARSER_NAMES.isdisjoint(row["entries"]), (tag, row["entries"])
    assert row["entries"].get("geostail", {}).get("ops", {}).get("18") == 1
    assert {"layout", "viewsource"} & row["entries"].keys(), \
        (tag, "exact-width geometry was not refused", row["entries"])
    row.update(tag=tag, mode=mode, width=(40, 60, 80)[mode],
               source_bytes=len(expected), refusal="geometry")
    print("REFUSAL PASS", tag, row["instructions"], "instructions", flush=True)
    return row


def styled_pan_case(g, names):
    """Consume a real READY ticket with nowrap source=start+24-bit pan."""
    f = g.f
    mode, width = 1, 60
    data = b"A" * 180 + b"\rTail."
    position = 120
    admission.setup(f, mode, data, position)
    f.command(77)
    profile.drain(f)
    f.position(position)
    profile.drain(f)
    assert f.get("se_l_mode", 1) == 1 and f.get("se_l_pan") > 0
    f.key(admission.Q)
    assert f.get("se_st_tx", 1) == admission.TX_ADMITTED
    source = data[:position] + bytes((admission.Q,)) + data[position:]
    _, first, count, _ = consumer.make_ready(f, mode, source)
    assert first == 0 and count == 1
    poison(f)
    f.put("se_overlay_frame", 1, 1)
    registers, instructions = f.fast_call(
        f.s["se_overlay_call"], a=33, x=1, limit=8_000_000)
    assert not registers.p & 1 and registers.a == 0
    # The insertion leaves the caret exactly one column beyond the panned
    # viewport.  Compare the painted row/anchors directly: no padding cell may
    # alias that logical position as a second caret.
    (pixels, attrs), wanted_anchors, seen, _ = \
        profile.observer.geos.grid.expected(f, source)
    assert seen is None
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
    pan = f.get("se_l_pan")
    packet = assert_packet(f, source, width, "60-nowrap-pan", start=pan)
    result = {"tag": "60-nowrap-pan", "mode": mode, "width": width,
              "instructions": instructions, "pan": pan, "packet": packet}
    print("PASS", result["tag"], instructions, "instructions", flush=True)
    return result


def refusal_preserves_reu(g, names):
    """Selection makes R25 refuse before packet/output or any REU mutation."""
    f = g.f
    mode = 2
    at = admission.setup(f, mode)
    f.key(admission.Q)
    source = admission.TEXT[:at] + bytes((admission.Q,)) + admission.TEXT[at:]
    consumer.make_ready(f, mode, source)
    poison(f)
    f.put("se_sel_mark", 1, 1)
    before_reu = g.reu()
    before_output = f.read(0x4000, 1000) + f.read(0x6000, 8000)
    before_source = f.merged()
    f.put("se_overlay_frame", 1, 1)
    registers, instructions = f.fast_call(
        f.s["se_overlay_call"], a=33, x=1, limit=8_000_000)
    assert registers.a == 2, \
        (registers.a, registers.p, f.get("se_st_tx", 1),
         f.get("se_sel_mark", 1))
    assert f.merged() == before_source == source
    assert f.read(0x4000, 1000) + f.read(0x6000, 8000) == before_output
    assert g.reu() == before_reu, "refused R25 consume changed the 16MiB REU"
    assert f.read(PACKET, 240) == (bytes((POISON_CHAR,)) * 80 +
                                  bytes((POISON_ROLE,)) * 80 +
                                  bytes((POISON_FLAG,)) * 80)
    result = {"tag": "selection-refusal", "instructions": instructions,
              "reu_bytes_preserved": len(before_reu)}
    print("REFUSAL PASS", result["tag"], instructions, "instructions", flush=True)
    return result


def run(out, fixture=None):
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location(
        "lrv_row_relative_runner", ROOT / "src/cache/hotpath-profile-probe/runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    saved = profile.observer.runner
    profile.observer.runner = runner.build
    try:
        gate = profile.observer.Gate(out, fixture)
    finally:
        profile.observer.runner = saved
    f = gate.f
    names = direct.configure(gate)
    cases = []
    try:
        # Empty content: its only live cell is simultaneously first and end.
        cases.append(direct_case(gate, names, "40-empty-first-end", 0,
                                 b"A\rTail.", 1, 0x14))
        # First content cell, an interior live cell, and the real end cell.
        cases.append(direct_case(gate, names, "40-caret-first", 0,
                                 b"ABCDE\rTail.", 1, 0x14))
        cases.append(direct_case(gate, names, "40-width-minus-one-live", 0,
                                 b"A" * 38 + b"\rTail.", 20, ord("Q")))
        cases.append(direct_case(gate, names, "40-caret-end", 0,
                                 b"ABCDE\rTail.", 5, ord("Q")))

        # The retained row itself begins beyond $ffff; the packet must not
        # truncate source, range or caret subtraction to 16 bits.
        prefix = b"X\r" * 33000
        high = direct_case(gate, names, "80-row-start-above-ffff", 2,
                           prefix + b"ABCDE\rTail.", len(prefix) + 2, ord("Q"))
        assert high["packet"]["start"] > 0xFFFF
        cases.append(high)

        # The accepted row is the final short row of a wrapped physical line;
        # its retained source origin is the two-width wrapped offset.
        wrapped = direct_case(gate, names, "80-wrapped-row-offset", 2,
                              b"A" * 170 + b"\rTail.", 165, ord("Q"))
        assert wrapped["packet"]["start"] == 160
        cases.append(wrapped)
        cases.append(styled_pan_case(gate, names))

        # Exact-width CR and EOF need an extra terminal caret row.  The bounded
        # one-row certificate must refuse them and the established full render
        # must retain exact source/pixels.
        cases.append(refusal_case(gate, names, "60-exact-width-CR-refusal", 1,
                                  b"A" * 61 + b"\rTail.", 60, 0x14))
        cases.append(refusal_case(gate, names, "60-exact-width-EOF-refusal", 1,
                                  b"A" * 61, 60, 0x14))
        refusals = [refusal_preserves_reu(gate, names)]
        result = {"status": "PASS", "identity": gate.identity,
                  "cases": cases, "refusals": refusals, "scope": __doc__}
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    destination = ROOT / "build/lrv-row-relative" / \
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", destination, flush=True)
    result = run(destination,
                 args.fixture.resolve() if args.fixture else None)
    print(json.dumps({"status": result["status"],
                      "output": str(destination)}, indent=2))
