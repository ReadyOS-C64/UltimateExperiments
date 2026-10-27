"""Actual 6510 proof for the Plain fixed-grid one-row edit transaction.

The gate freezes one coherent product, drives public editor input/render calls,
and observes instructions and overlay entries without intercepting execution.
It checks complete pixels, canonical source, retained row anchors and caret state.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import ctypes as C
import hashlib
import importlib.util
import json

import test_cache_hotpath_profile as profile


ROOT = profile.ROOT
DATA = profile.observer.geos.native_text(
    "First short row.\rSecond editable row.\rThird unchanged row.\r")
Q = profile.observer.geos.native_text("Q")[0]
PARSER_NAMES = {
    "styler", "lexical", "foldparse", "foldfinish", "foldctl",
    "geossema", "geoslex", "geosinln", "sema", "inln", "page",
}


def anchors(f):
    return tuple(int.from_bytes(f.read(f.s["se_v_rows"] + i * 3, 3), "little")
                 for i in range(22)) + (f.get("se_v_bottom"),)


def pixels(f, source, tag):
    (wanted_bits, wanted_attrs), wanted_anchors, seen, _ = \
        profile.observer.geos.grid.expected(f, source)
    mode = f.get("se_mode", 1)
    if mode == 0:
        actual_bits = f.read(0x4000, 1000)
        actual_attrs = f.read(0xD800, 1000)
    else:
        actual_bits = f.read(0x6000, 8000)
        actual_attrs = f.read(0x4000, 1000)
    assert actual_bits == wanted_bits, (tag, "pixels")
    assert actual_attrs == wanted_attrs, (tag, "attributes")
    assert anchors(f) == wanted_anchors, (tag, "retained row anchors")
    assert seen == (f.get("se_v_caret_row", 1), f.get("se_v_caret_col", 1)), \
        (tag, "caret row/column", seen,
         f.get("se_v_caret_row", 1), f.get("se_v_caret_col", 1))
    return hashlib.sha256(actual_bits + actual_attrs).hexdigest()


def configure(g):
    f, dll = g.f, g.dll
    points, crc_returns = profile.points(f)
    assert len(crc_returns) <= 8
    names = g.identity["names"]
    dll.hp_config(
        f.s["se_overlay_active"], f.s["se_overlay_frame"],
        f.s["se_e_draw_sequence"], (C.c_uint16 * 8)(*points),
        len(crc_returns),
        (C.c_uint16 * len(crc_returns))(*crc_returns),
        names.index("gtype") + 1, names.index("code") + 1)
    return names


def observation(g, names, tag, operation):
    f, dll = g.f, g.dll
    start = f.total_instructions
    loads = f.get("se_overlay_loads", 2)
    dmas = f.get("se_reu_dma_calls", 2)
    dma_bytes = f.get("se_reu_dma_bytes", 3)
    dll.hp_begin(f.get("se_e_draw_sequence", 2))
    try:
        operation()
        ticks = profile.drain(f)
    finally:
        dll.hp_end()
    used = f.total_instructions - start
    assert dll.hp_get(0, 0) == used, (tag, "observer instruction total")
    entries = {
        name: dict(
            calls=int(dll.hp_get(3, i + 1)),
            ops={str(op): int(dll.hp_op(i + 1, op))
                 for op in range(256) if dll.hp_op(i + 1, op)},
        )
        for i, name in enumerate(names) if dll.hp_get(3, i + 1)
    }
    groups = []
    for index in range(128):
        if dll.hp_group(index, 0):
            groups.append(dict(
                slot=index // 64, id=index % 64,
                calls=int(dll.hp_group(index, 0)),
                total=int(dll.hp_group(index, 1)),
                admission=int(dll.hp_group(index, 2)),
                payload_inclusive=int(dll.hp_group(index, 3)),
                payload_self=int(dll.hp_group(index, 4))))
    return dict(
        instructions=used,
        first_publication_instructions=int(dll.hp_get(0, 1)),
        idle_ticks=ticks,
        loads=(f.get("se_overlay_loads", 2) - loads) & 0xFFFF,
        DMA_calls=(f.get("se_reu_dma_calls", 2) - dmas) & 0xFFFF,
        DMA_bytes=(f.get("se_reu_dma_bytes", 3) - dma_bytes) & 0xFFFFFF,
        overlay_calls=sum(v["calls"] for v in entries.values()),
        entries=entries,
        overlay_intervals=groups)


def setup(f, mode, data=DATA, position=None):
    f.source(data, physical=256)
    f.typed(profile.observer.geos.native_text("syntax plain"))
    f.command(96 + mode)
    profile.drain(f)
    if position is None:
        position = data.index(profile.observer.geos.native_text("editable")) + 3
    f.position(position)
    profile.drain(f)
    assert f.get("se_mode", 1) == mode
    assert f.get("se_render_caps", 1) == 0
    assert f.get("se_hot_caret") == position
    pixels(f, data, f"setup-{mode}")
    return position


def assert_plain(entries, tag):
    bad = sorted(PARSER_NAMES.intersection(entries))
    assert not bad, (tag, "Plain entered parser/style work", bad)


def run(out, fixture=None):
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location(
        "plain_direct_row_runner",
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
        for mode in (0, 1, 2):
            for action in ("insert", "delete"):
                at = setup(f, mode)
                if action == "insert":
                    expected = DATA[:at] + bytes((Q,)) + DATA[at:]
                    expected_caret = at + 1
                    key = Q
                else:
                    expected = DATA[:at - 1] + DATA[at:]
                    expected_caret = at - 1
                    key = 0x14
                tag = f"{40 if mode == 0 else 60 if mode == 1 else 80}-{action}"
                row = observation(g, names, tag, lambda key=key: f.key(key))
                assert f.merged() == expected, (tag, "source")
                assert f.get("se_hot_caret") == expected_caret, (tag, "caret")
                assert f.get("se_st_valid", 1) == 0, (tag, "Plain style state")
                row["pixels_sha256"] = pixels(f, expected, tag)
                assert_plain(row["entries"], tag)
                assert row["entries"].get("geostail", {}).get("ops", {}).get("18") == 1, \
                    (tag, "missing single direct-row prepare", row["entries"])
                for frame in (14, 17):
                    assert row["entries"].get("geostail", {}).get("ops", {}).get(str(frame)) == 1, \
                        (tag, "direct-row transaction did not complete", frame, row["entries"])
                assert "15" not in row["entries"].get("geostail", {}).get("ops", {}), \
                    (tag, "direct-row transaction repeated row preparation", row["entries"])
                assert row["entries"].get("grid", {}).get("ops", {}).get("1") == 1, \
                    (tag, "missing single direct-row consume", row["entries"])
                assert not ({"layout", "viewsource"} & row["entries"].keys()), \
                    (tag, "ordinary full-grid fallback", row["entries"])
                row.update(tag=tag, mode=mode, action=action,
                           caret=f.get("se_hot_caret"), source_bytes=len(expected))
                cases.append(row)
                print("DIRECT PASS", tag, row["instructions"], "instructions",
                      row["loads"], "loads", row["overlay_calls"], "calls", flush=True)

            at = setup(f, mode)
            tag = f"{40 if mode == 0 else 60 if mode == 1 else 80}-warm-caret"
            row = observation(g, names, tag, lambda: f.key(0x1D))
            assert f.merged() == DATA and f.get("se_hot_caret") == at + 1
            row["pixels_sha256"] = pixels(f, DATA, tag)
            assert_plain(row["entries"], tag)
            assert row["entries"].get("grid", {}).get("ops", {}).get("1") == 1, \
                (tag, "ordinary warm-caret route", row["entries"])
            assert row["entries"].get("geostail", {}).get("ops", {}).get("18", 0) == 0, \
                (tag, "warm caret entered edit prepare", row["entries"])
            row.update(tag=tag, mode=mode, action="warm-caret",
                       caret=f.get("se_hot_caret"), source_bytes=len(DATA))
            cases.append(row)
            print("CARET PASS", tag, row["instructions"], "instructions",
                  row["loads"], "loads", row["overlay_calls"], "calls", flush=True)

        # A CR has no one-row certificate. The public edit must still fall back
        # to a correct complete render.
        at = setup(f, 2)
        tag = "80-insert-CR-refusal"
        expected = DATA[:at] + b"\r" + DATA[at:]
        row = observation(g, names, tag, lambda: f.key(13))
        assert f.merged() == expected and f.get("se_hot_caret") == at + 1
        row["pixels_sha256"] = pixels(f, expected, tag)
        assert_plain(row["entries"], tag)
        assert row["entries"].get("geostail", {}).get("ops", {}).get("18", 0) == 0, \
            (tag, "CR reached direct-row prepare", row["entries"])
        row.update(tag=tag, mode=2, action="refuse-CR",
                   caret=f.get("se_hot_caret"), source_bytes=len(expected))
        cases.append(row)
        print("REFUSAL PASS", tag, row["instructions"], "instructions", flush=True)

        # Growing a short physical line to exactly the mode width is rejected
        # by the bounded transaction because it changes wrap geometry.
        mode = 1
        width = 60
        data = b"A" * (width - 1) + b"\rTail."
        at = setup(f, mode, data, width - 2)
        tag = "60-wrap-boundary-refusal"
        expected = data[:at] + bytes((Q,)) + data[at:]
        row = observation(g, names, tag, lambda: f.key(Q))
        assert f.merged() == expected and f.get("se_hot_caret") == at + 1
        row["pixels_sha256"] = pixels(f, expected, tag)
        assert_plain(row["entries"], tag)
        assert row["entries"].get("geostail", {}).get("ops", {}).get("18") == 1, \
            (tag, "bounded prepare was not attempted", row["entries"])
        assert {"layout", "viewsource"} & row["entries"].keys(), \
            (tag, "refusal did not take established fallback", row["entries"])
        row.update(tag=tag, mode=mode, action="refuse-wrap",
                   caret=f.get("se_hot_caret"), source_bytes=len(expected))
        cases.append(row)
        print("REFUSAL PASS", tag, row["instructions"], "instructions", flush=True)

        result = dict(
            status="PASS",
            identity=g.identity,
            cases=cases,
            scope=__doc__,
            timing="Actual MOS 6510 instruction counts in Peddle; no cycle or native VIC claim.")
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    destination = ROOT / "build/plain-direct-row-hotpath" / \
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", destination, flush=True)
    run(destination, args.fixture.resolve() if args.fixture else None)
