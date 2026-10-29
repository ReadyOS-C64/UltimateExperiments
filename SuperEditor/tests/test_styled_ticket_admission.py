"""Actual 6510 regression for direct C6 styled-ticket admission.

Public fixed-grid edits stop at the return from editor input, before idle C14
can consume the ticket.  A minimal published-checkpoint fixture isolates C6;
the test then observes the real overlay gateway and ticket ABI.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import binascii
import ctypes as C
import importlib.util
import json

import test_cache_hotpath_profile as profile


ROOT = profile.ROOT
TEXT = profile.observer.geos.native_text(
    "Intro row.\rStyled **boldword** tail.\rFollowing row.\r")
LAST = profile.observer.geos.native_text("Only **boldword** tail.")
Q = profile.observer.geos.native_text("Q")[0]
TX_BYTES = 20
TX_ADMITTED = 0xA5
TX_SEED = 0xA7


def configure(g):
    points, returns = profile.points(g.f)
    assert len(returns) <= 8
    names = g.identity["names"]
    g.dll.hp_config(
        g.f.s["se_overlay_active"], g.f.s["se_overlay_frame"],
        g.f.s["se_e_draw_sequence"], (C.c_uint16 * 8)(*points),
        len(returns), (C.c_uint16 * len(returns))(*returns),
        names.index("gtype") + 1, names.index("code") + 1)
    return names


def setup(f, mode, data=TEXT, position=None):
    f.source(data, physical=256)
    f.typed(profile.observer.geos.native_text("syntax full"))
    f.command(96 + mode)
    profile.drain(f)
    at = (data.index(profile.observer.geos.native_text("boldword")) + 4
          if position is None else position)
    f.position(at)
    profile.drain(f)
    # Establish one already-published style/checkpoint authority.  This test is
    # about C6 admission, not the independent cold C14 producer regression.
    anchors = [0] + [i + 1 for i, value in enumerate(data) if value == 13]
    rows = anchors + [len(data)] * (23 - len(anchors))
    f.m.load(f.s["se_v_rows"], b"".join(v.to_bytes(3, "little")
                                          for v in rows[:22]))
    f.put("se_v_bottom", rows[22], 3)
    f.put("se_v_length", len(data), 3)
    f.put("se_v_top", 0, 3)
    f.put("se_l_pan", 0, 3)
    f.put("se_l_mode", 0, 1)
    f.put("se_l_need_wrap", 0, 1)
    f.put("se_l_valid", 1, 1)
    f.m.load(f.s["se_l_original"], f.read(f.s["se_doc_original"], 10))
    f.m.load(f.s["se_l_generation"], f.read(f.s["se_doc_generation"], 2))
    f.m.load(f.s["se_l_revision"], f.read(f.s["se_r_revision"], 4))
    f.put("se_e_redraw", 0, 1)
    f.put("se_r_presentation", 0, 1)
    f.put("se_e_ui", 0, 1)
    f.put("se_sel_mark", 0, 1)
    carry = bytearray(22 * 5)
    for row in range(len(anchors)):
        carry[row * 5] = 0x80
    f.m.load(f.s["se_st_cp_rows"], carry)
    f.put("se_st_cp_crc", binascii.crc_hqx(carry, 0xFFFF), 2)
    f.put("se_st_cp_count", len(anchors), 1)
    f.put("se_st_cp_valid", 1, 1)
    descriptor = (f.read(f.s["se_doc_meta"], 15) +
                  f.read(f.s["se_doc_generation"], 2) +
                  f.read(f.s["se_r_revision"], 4) +
                  len(data).to_bytes(3, "little") + bytes(6) +
                  f.read(f.s["se_reu_epoch"], 2) + bytes((mode << 1,)))
    assert len(descriptor) == 33
    f.m.load(f.s["se_st_descriptor"], descriptor)
    f.put("se_st_valid", 1, 1)
    f.put("se_st_request", 0, 1)
    f.m.load(f.s["se_st_tx"], bytes(TX_BYTES))
    assert f.get("se_st_valid", 1) == 1
    assert f.get("se_st_cp_valid", 1) == 1
    assert f.get("se_st_request", 1) == 0
    return at


def checkpoint_span(f, position):
    count = f.get("se_st_cp_count", 1)
    rows = [f.get("se_v_rows", 3)]
    rows += [int.from_bytes(f.read(f.s["se_v_rows"] + i * 3, 3), "little")
             for i in range(1, 22)]
    rows.append(f.get("se_v_bottom", 3))
    row = max(i for i in range(min(count, 22)) if rows[i] <= position)
    carry = f.read(f.s["se_st_cp_rows"], count * 5)
    first = row
    while first and not carry[first * 5] & 0x80:
        first -= 1
    end = row + 1
    while end < count and not carry[end * 5] & 0x80:
        end += 1
    return rows, first, end, count


def observed_key(g, names, key):
    f, dll = g.f, g.dll
    before_loads = f.get("se_overlay_loads", 2)
    dll.hp_begin(f.get("se_e_draw_sequence", 2))
    try:
        f.key(key)
    finally:
        dll.hp_end()
    r25_tag = names.index("geostail") + 1
    image = f.assets["geostail"]
    group = image[5] * 64 + image[6]
    calls = int(dll.hp_group(group, 0))
    admission_instructions = int(dll.hp_group(group, 2))
    frame18 = int(dll.hp_op(r25_tag, 18))
    assert calls == frame18 == admission_instructions == 0, (
        "styled C6 admission entered/loaded R25 frame18",
        calls, frame18, admission_instructions)
    assert int(dll.hp_get(3, names.index("styler") + 1)) == 0, \
        "background C14 ran before ticket observation"
    return (f.get("se_overlay_loads", 2) - before_loads) & 0xFFFF


def assert_admitted(f, mode, action, at, rows, first, end, count):
    assert end < count, "positive fixture must have an outgoing carry"
    tx = f.read(f.s["se_st_tx"], TX_BYTES)
    delta = 1 if action == "insert" else -1
    expected = bytearray(TX_BYTES)
    expected[0] = TX_ADMITTED
    expected[2:5] = rows[first].to_bytes(3, "little")
    expected[5:8] = (rows[end] + delta).to_bytes(3, "little")
    expected[8] = ((((mode << 1) | f.get("se_l_mode", 1)) << 5) | first) & 0xFF
    expected[9] = end - first | (0x20 if action == "delete" else 0)
    expected[10:12] = f.read(f.s["se_e_draw_sequence"], 2)
    expected[12:16] = f.read(f.s["se_r_revision"], 4)
    expected[16:18] = f.read(f.s["se_doc_generation"], 2)
    expected[18:20] = f.read(f.s["se_doc_epoch"], 2)
    check = TX_SEED ^ TX_ADMITTED
    for value in expected[2:]:
        check ^= value
    expected[1] = check
    assert tx == expected, (mode, action, tx.hex(), expected.hex(), at)
    folded = TX_SEED
    for value in tx:
        folded ^= value
    assert folded == 0
    assert f.get("se_st_request", 1) == 1
    assert f.get("se_st_valid", 1) == 0
    assert f.get("se_f_owner", 1) == 0
    return tx


def assert_refused(f):
    tx = f.read(f.s["se_st_tx"], TX_BYTES)
    assert tx[0] == 0
    assert f.m.read(0xCFE8) == 0       # refused one-edit certificate retired
    assert f.get("se_f_owner", 1) == 0


def run(out, fixture=None):
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location(
        "styled_ticket_runner",
        ROOT / "src/cache/hotpath-profile-probe/runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    saved_runner = profile.observer.runner
    profile.observer.runner = runner.build
    try:
        g = profile.observer.Gate(out, fixture)
    finally:
        profile.observer.runner = saved_runner
    f = g.f
    names = configure(g)
    cases = []
    try:
        for mode, width in enumerate((40, 60, 80)):
            for action in ("insert", "delete"):
                at = setup(f, mode)
                position = at if action == "insert" else at - 1
                rows, first, end, count = checkpoint_span(f, position)
                loads = observed_key(g, names, Q if action == "insert" else 0x14)
                tx = assert_admitted(f, mode, action, at, rows, first, end, count)
                wanted = (TEXT[:at] + bytes((Q,)) + TEXT[at:] if action == "insert"
                          else TEXT[:at - 1] + TEXT[at:])
                assert f.merged() == wanted
                cases.append(dict(tag=f"{width}-{action}", ticket=tx.hex(),
                                  total_overlay_loads=loads))

        refusals = []
        at = setup(f, 2)
        corrupt = f.s["se_st_cp_rows"] + 7
        f.m.write(corrupt, f.m.read(corrupt) ^ 1)
        observed_key(g, names, Q)
        assert_refused(f)
        assert f.merged() == TEXT[:at] + bytes((Q,)) + TEXT[at:]
        refusals.append("one-bit-checkpoint-corruption")

        at = setup(f, 0)
        f.put("se_st_cp_count", 0, 1)
        observed_key(g, names, Q)
        assert_refused(f)
        assert f.merged() == TEXT[:at] + bytes((Q,)) + TEXT[at:]
        refusals.append("corrupt-checkpoint-count")

        at = setup(f, 1)
        stale = f.s["se_st_descriptor"] + 17
        f.m.write(stale, f.m.read(stale) ^ 1)
        observed_key(g, names, Q)
        assert_refused(f)
        assert f.merged() == TEXT[:at] + bytes((Q,)) + TEXT[at:]
        refusals.append("stale-checkpoint-descriptor")

        at = setup(f, 2, LAST)
        _, _, end, count = checkpoint_span(f, at)
        assert end >= count
        observed_key(g, names, Q)
        assert_refused(f)
        assert f.merged() == LAST[:at] + bytes((Q,)) + LAST[at:]
        refusals.append("last-line-without-outgoing-carry")

        result = dict(status="PASS", identity=g.identity, cases=cases,
                      refusals=refusals, scope=__doc__)
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
        return result
    finally:
        f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    destination = ROOT / "build/styled-ticket-admission" / \
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", destination, flush=True)
    run(destination, args.fixture.resolve() if args.fixture else None)
