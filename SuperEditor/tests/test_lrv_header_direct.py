"""Exact LRV direct-header oracle against the former authenticated rebuild.

The test builds a private control from the same frozen product, changing only
R25's header handling back to save/restore plus ``fields``.  It compares all
256 header bytes for 12 styled edits and four Plain bottom-row edits, verifies
the header and changed-row CRCs independently, and exercises three refusal
boundaries.  Production sources and build products are never modified.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import binascii
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile

import test_cache_hotpath_profile as profile
import test_plain_direct_row_hotpath as plain
import test_styled_ticket_admission as admission
import test_styled_ticket_consumer as styled


ROOT = profile.ROOT
N_KEY, N_BOTTOM, N_STYLE = 4, 42, 45
N_PENDING, N_HOTLEN, N_ROWS = 87, 91, 124
N_CARET, N_SEEN, N_ROW, N_COL = 196, 199, 200, 201
N_VALID, N_ROWCRC, N_CRC = 204, 209, 254


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:80]
    return text.replace(old, new, 1)


def build_control(out, production):
    """Build only grid/geostail after restoring the old header transaction."""
    project = out / "control-project"
    project.mkdir()
    with zipfile.ZipFile(production / "product-sources.zip") as archive:
        archive.extractall(project)
    (project / "build/overlays").mkdir(parents=True)
    for name in ("editor.prg", "editor.lbl", "editor-report.json"):
        shutil.copy2(production / "build" / name, project / "build" / name)
    for name in ("grid80", "grid60", "styler", "viewsource"):
        shutil.copy2(production / "build/overlays" / (name + ".seo"),
                     project / "build/overlays" / (name + ".seo"))
    (project / "fonts").mkdir()
    shutil.copy2(production / "fonts/native8.bin", project / "fonts/native8.bin")

    consumer = project / "src/render/grid/caret/lrv3-consumer.inc"
    text = consumer.read_text()
    text = replace_once(text, "LT_HOT_REV=45              ;4, separate from the length/row scratch\n",
                        "LT_HOT_REV=45              ;4, separate from the length/row scratch\n"
                        "LRV_OLD_NC=$8500           ;private authenticated header control\n")
    direct = """ lda LRVT+LT_CARET_ROW
 sta H+N_ROW
 lda LRVT+LT_CARET_COL
 sta H+N_COL
 lda #1
 sta H+N_SEEN
 ldx #2
@header_valid:
 lda LRVT+LT_GC_VALID,x
 sta H+N_VALID,x
 dex
 bpl @header_valid
 ldx #3
@header_revision:
 lda se_r_revision,x
 sta H+N_KEY+17,x
 bit LRVT+LT_FLAGS
 bpl :+
 sta H+N_STYLE+17,x
 sta se_st_descriptor+17,x
: dex
 bpl @header_revision
 ldx #2
@header_caret:
 lda se_hot_caret,x
 sta H+N_CARET,x
 dex
 bpl @header_caret
 lda se_hot_pending
 sta H+N_PENDING
 ldx #1
@hotlen:
 lda se_hot_length,x
 sta H+N_HOTLEN,x
 dex
 bpl @hotlen
 ldx #2
@length:
 lda se_v_length,x
 sta H+N_KEY+21,x
 bit LRVT+LT_FLAGS
 bpl :+
 sta H+N_STYLE+21,x
 sta se_st_descriptor+21,x
: dex
 bpl @length
"""
    rebuild = """ ldx #0
@restore_nc:
 lda LRV_OLD_NC,x
 sta H,x
 inx
 bne @restore_nc
 lda #0
 sta OP
 jsr fields
 jcs lrv_bad
 lda #1
 sta OP
 sta H+N_SEEN
 lda LRVT+LT_CARET_ROW
 sta H+N_ROW
 lda LRVT+LT_CARET_COL
 sta H+N_COL
 ldx #2
@header_caret:
 lda se_hot_caret,x
 sta H+N_CARET,x
 dex
 bpl @header_caret
 ldx #3
@control_descriptor_revision:
 lda se_r_revision,x
 sta se_st_descriptor+17,x
 dex
 bpl @control_descriptor_revision
 ldx #2
@control_descriptor_length:
 lda se_v_length,x
 sta se_st_descriptor+21,x
 dex
 bpl @control_descriptor_length
"""
    text = replace_once(text, direct, rebuild)
    style_point = """ lda LRVT+LT_FLAGS
 bpl @store
 clc
 lda se_st_generation
"""
    style_rebuild = """ lda LRVT+LT_FLAGS
 bpl @store
 ldx #3
@header_revision:
 lda se_r_revision,x
 sta H+N_STYLE+17,x
 dex
 bpl @header_revision
 ldx #2
@header_length:
 lda se_v_length,x
 sta H+N_STYLE+21,x
 dex
 bpl @header_length
 clc
 lda se_st_generation
"""
    text = replace_once(text, style_point, style_rebuild)
    save_point = """ lda H+3
 cmp #LRV_PUBLISHED
 bne @bad
@done:
"""
    save_control = """ lda H+3
 cmp #LRV_PUBLISHED
 bne @bad
 ldx #0
@save:
 lda H,x
 sta LRV_OLD_NC,x
 inx
 bne @save
@done:
"""
    consumer.write_text(replace_once(text, save_point, save_control))

    painter = project / "src/render/grid/caret/lrv3-painter.inc"
    text = painter.read_text()
    text = replace_once(text, "LRVT=$8D00\n", "LRVT=$8D00\nLRV_OLD_NC=$8500\n")
    text = replace_once(text, "sta H+N_ROWCRC,x", "sta LRV_OLD_NC+N_ROWCRC,x")
    text = replace_once(text, "sta H+N_ROWCRC+1,x", "sta LRV_OLD_NC+N_ROWCRC+1,x")
    painter.write_text(text)

    subprocess.run([sys.executable, "src/render/grid/caret/build.py",
                    "build/grid-caret", str(project)], cwd=project, check=True)
    fixture = out / "control-fixture"
    shutil.copytree(production, fixture)
    for name in ("grid", "geostail"):
        for suffix in (".seo", ".bin", ".lbl", ".map"):
            shutil.copy2(project / "build/grid-caret" / (name + suffix),
                         fixture / "build/overlays" / (name + suffix))
    identity = json.loads((fixture / "freeze.json").read_text())
    for name in ("grid", "geostail"):
        identity["assets"][name] = sha(fixture / "build/overlays" / (name + ".seo"))
    identity["header_oracle"] = "authenticated save/restore plus generic fields rebuild"
    (fixture / "freeze.json").write_text(json.dumps(identity, indent=2) + "\n")
    return fixture, identity


def gate(out, fixture):
    spec = importlib.util.spec_from_file_location(
        "lrv_header_runner_" + out.name,
        ROOT / "src/cache/hotpath-profile-probe/runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    saved = profile.observer.runner
    profile.observer.runner = runner.build
    try:
        result = profile.observer.Gate(out, fixture)
    finally:
        profile.observer.runner = saved
    styled.configure(result)
    return result


def call(f):
    f.put("se_overlay_frame", 1, 1)
    return f.fast_call(f.s["se_overlay_call"], a=33, x=1, limit=8_000_000)


def prepare_styled(f, mode, data, position, action):
    at = admission.setup(f, mode, data, position=position)
    if action == "insert":
        f.key(admission.Q)
        source = data[:at] + bytes((admission.Q,)) + data[at:]
    else:
        f.key(0x14)
        source = data[:at - 1] + data[at:]
    _, first, count, _ = styled.make_ready(f, mode, source)
    return source, first, count


def cache_header(f):
    cache, _ = f.raw_cache()
    return cache, bytes(cache[0x1500:0x1600])


def validate_header(f, source, first, count, styled_mode):
    cache, header = cache_header(f)
    assert header[:4] == b"NC\x01\xA5" and len(header) == 256
    assert binascii.crc_hqx(header[:N_CRC], 0xFFFF) == \
        int.from_bytes(header[N_CRC:], "little")
    assert header[N_KEY + 17:N_KEY + 21] == f.read(f.s["se_r_revision"], 4)
    assert header[N_KEY + 21:N_KEY + 24] == len(source).to_bytes(3, "little")
    if styled_mode:
        assert header[N_STYLE + 17:N_STYLE + 21] == f.read(f.s["se_r_revision"], 4)
        assert header[N_STYLE + 21:N_STYLE + 24] == len(source).to_bytes(3, "little")
    assert header[N_BOTTOM:N_BOTTOM + 3] == header[N_ROWS + 66:N_ROWS + 69] \
        == f.read(f.s["se_v_bottom"], 3)
    assert header[N_PENDING] == f.get("se_hot_pending", 1)
    assert header[N_HOTLEN:N_HOTLEN + 2] == f.read(f.s["se_hot_length"], 2)
    assert header[N_CARET:N_CARET + 3] == f.read(f.s["se_hot_caret"], 3)
    assert header[N_SEEN] == 1
    assert header[N_ROW] == f.get("se_v_caret_row", 1)
    assert header[N_COL] == f.get("se_v_caret_col", 1)
    assert header[N_VALID:N_VALID + 3] == f.read(f.s["se_gc_valid"], 3)
    row_crcs = []
    for row in range(first, first + count):
        packet = cache[row * 240:(row + 1) * 240]
        actual = binascii.crc_hqx(packet, 0xFFFF)
        assert actual == int.from_bytes(
            header[N_ROWCRC + row * 2:N_ROWCRC + row * 2 + 2], "little")
        row_crcs.append(actual)
    return header, row_crcs


def styled_cases(g):
    f, cases = g.f, {}
    data = admission.TEXT
    positions = (("row0", 2),
                 ("row1", data.index(profile.observer.geos.native_text("boldword")) + 4),
                 ("row2", data.index(profile.observer.geos.native_text("Following")) + 3))
    for mode in (1, 2):
        for label, position in positions:
            for action in ("insert", "delete"):
                source, first, count = prepare_styled(f, mode, data, position, action)
                registers, instructions = call(f)
                assert registers.a == 0 and not registers.p & 1
                header, row_crcs = validate_header(f, source, first, count, True)
                cases[f"{mode}-{label}-{action}"] = {
                    "header": header.hex(), "first": first, "count": count,
                    "row_crcs": row_crcs, "instructions": instructions,
                }
    return cases


def plain_bottom_cases(g):
    f, names, cases = g.f, plain.configure(g), {}
    data, position = b"A\r" * 21 + b"ABCDE", 44
    for mode in (1, 2):
        for action, key in (("insert", ord("Q")), ("delete", 0x14)):
            plain.setup(f, mode, data, position)
            row = plain.observation(g, names, f"plain-{mode}-{action}",
                                    lambda key=key: f.key(key))
            plain.assert_plain(row["entries"], action)
            first, count = f.m.read(0x8D03), f.m.read(0x8D04)
            assert (first, count, first + count) == (21, 1, 22)
            source = data[:position] + (b"Q" if action == "insert" else b"") + \
                data[position:] if action == "insert" else data[:position - 1] + data[position:]
            header, row_crcs = validate_header(f, source, first, count, False)
            cases[f"{mode}-{action}"] = {
                "header": header.hex(), "first": first, "count": count,
                "row_crcs": row_crcs, "instructions": row["instructions"],
            }
    return cases


def stash(f, data, offset):
    f.m.load(0x9000, data)
    f.put("se_reu_logical", f.get("se_gc_handle", 1), 1)
    f.put("se_reu_offset", offset, 2)
    f.put("se_reu_c64", 0x9000, 2)
    f.put("se_reu_length", len(data), 2)
    result = f.call("se_reu_copy", 0)
    assert not result.p & 1


def fault_cases(g):
    f, cases = g.f, {}
    data = admission.TEXT
    position = data.index(profile.observer.geos.native_text("boldword")) + 4
    for fault in ("header-crc", "forged-magic", "dma-owner"):
        prepare_styled(f, 1, data, position, "insert")
        cache, header = cache_header(f)
        header = bytearray(header)
        if fault == "header-crc":
            header[120] ^= 1
            stash(f, header, 0x1500)
        elif fault == "forged-magic":
            header[0] = ord("X")
            header[N_CRC:] = binascii.crc_hqx(header[:N_CRC], 0xFFFF).to_bytes(2, "little")
            stash(f, header, 0x1500)
        else:
            logical = f.get("se_gc_handle", 1)
            physical = f.m.read(f.s["se_reu_map"] + logical)
            owner = f.s["se_reu_physical_owner"] + physical
            f.m.write(owner, f.m.read(owner) ^ 1)
        logical = f.get("se_gc_handle", 1)
        bank = f.m.read(f.s["se_reu_map"] + logical)
        before = g.reu()[bank * 65536:(bank + 1) * 65536]
        registers, instructions = call(f)
        after = g.reu()[bank * 65536:(bank + 1) * 65536]
        assert registers.a == 2 and not registers.p & 1
        assert after[:0x1600] == before[:0x1600]
        assert f.get("se_st_tx", 1) == 0
        cases[fault] = {"a": registers.a, "p": registers.p,
                        "instructions": instructions,
                        "cache_crc32": binascii.crc32(after[:0x1600])}
    return cases


def run(out, fixture=None):
    out.mkdir(parents=True)
    production, production_identity = profile.observer.geos.freeze(
        out / "production", fixture)
    control, control_identity = build_control(out, production)
    results = {}
    gates = []
    try:
        for label, frozen in (("control", control), ("production", production)):
            g = gate(out / (label + "-gate"), frozen)
            gates.append(g)
            results[label] = {
                "styled": styled_cases(g),
                "plain_bottom": plain_bottom_cases(g),
                "faults": fault_cases(g),
            }
        for group in ("styled", "plain_bottom"):
            assert results["production"][group].keys() == results["control"][group].keys()
            for key in results["control"][group]:
                assert results["production"][group][key]["header"] == \
                    results["control"][group][key]["header"], (group, key)
                assert results["production"][group][key]["row_crcs"] == \
                    results["control"][group][key]["row_crcs"], (group, key, "row CRC")
        for key in results["control"]["faults"]:
            expected = results["control"]["faults"][key]
            actual = results["production"]["faults"][key]
            assert (actual["a"], actual["p"], actual["cache_crc32"]) == \
                (expected["a"], expected["p"], expected["cache_crc32"]), key
        result = {
            "status": "PASS", "styled_cases": 12, "plain_bottom_cases": 4,
            "fault_cases": 3, "header_bytes_compared_per_case": 256,
            "crc_layers": ["CCITT-FALSE header bytes 0..253",
                           "CCITT-FALSE each changed 240-byte row packet"],
            "production": {"prg": production_identity["prg_sha256"],
                           "grid": production_identity["assets"]["grid"],
                           "geostail": production_identity["assets"]["geostail"]},
            "control": {"grid": control_identity["assets"]["grid"],
                        "geostail": control_identity["assets"]["geostail"],
                        "oracle": control_identity["header_oracle"]},
            "cases": results,
            "scope": __doc__,
        }
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        for g in gates:
            g.f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    destination = ROOT / "build/lrv-header-direct" / \
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", destination, flush=True)
    answer = run(destination, args.fixture.resolve() if args.fixture else None)
    print(json.dumps({"status": answer["status"], "output": str(destination)}, indent=2))
