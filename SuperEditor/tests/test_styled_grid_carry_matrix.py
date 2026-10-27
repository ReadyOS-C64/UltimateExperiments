"""Actual-6510 qualification matrix for styled fixed-grid carry convergence.

This verifier is deliberately outside production. It freezes an immutable
product fixture, drives public editor input, observes the real
C6 -> C14/R14 -> C33 transaction, counts parser entry points, and compares the
completed screen with the independent fixed-grid oracle. No source, ticket,
pixel, carry, or parser result is seeded on a successful path.

Qualification binds directly to the shipped overlay labels: C6 admission in
window, the bounded R14 reader, the C14 fallback, and the C33 consumer in
geostail. The five-byte carry record packs fence and language into byte0,
keeps region depth in byte1, and retains the 24-bit region-overflow value in
bytes2-4. The logical-start bit is transport metadata and never participates
in convergence.

The full matrix covers Full/Markdown at 40/60/80 columns, heading/prose and
inline transitions, BASIC/assembler token edits, unchanged-code avoidance,
CR/wrap/fence/region fallback, stale/corrupt carry refusal, active-work input
and UI cancellation, source/pixels/attributes/anchors/history, and observed
foreground stack balance.  It is a CPU/Peddle gate; PAL/NTSC cycle and native
VIC evidence remain separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import binascii
import ctypes as C
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

import test_cache_hotpath_profile as profile
import test_styled_grid_convergence_profile_vice as native_profile


ROOT = profile.ROOT
BUILD = ROOT / "build" / "styled-grid-carry-matrix"
ORIGINAL_OBSERVER_RUNNER = profile.observer.runner
MODES = ((0, 40), (1, 60), (2, 80))
CAPABILITIES = (("markdown", 1), ("full", 3))
PARSER_POINTS = {
    "viewsource": ("se_sm_init", "se_sm_feed", "se_sm_finish"),
    "styler": ("se_si_init", "se_si_feed", "se_si_finish"),
    "lexical": ("se_sl_init", "se_sl_feed", "se_sl_finish"),
}
SEMANTIC_TUPLE = {
    "bytes": 5,
    "fence": {"byte": 0, "mask": 0x0F, "shift": 0},
    "language": {"byte": 0, "mask": 0x30, "shift": 4},
    "regions": {"byte": 1, "mask": 0x1F, "shift": 0},
    "region_overflow": [2, 3],
    "boundary_start": {"byte": 0, "mask": 0x80, "semantic": False},
    "reserved": [{"byte": 0, "mask": 0x40}, {"byte": 1, "mask": 0xE0}],
    "regions_mask": 0x1F,
}


def petscii(text):
    return profile.observer.geos.native_text(text)


@dataclass(frozen=True)
class Edit:
    name: str
    source: bytes
    position: int
    key: int
    route: str
    lexical: str = "none"
    changed_line_limit: int | None = None

    def edited(self):
        if self.key == 0x14:
            assert self.position
            return self.source[: self.position - 1] + self.source[self.position :]
        return self.source[: self.position] + bytes((self.key,)) + self.source[self.position :]


def edit_definitions(width):
    ordinary = petscii(
        "Intro prose with room.\r"
        "Second neutral paragraph.\r"
        ":::basic\r10 PRINT \"UNCHANGED\"\r:::\r"
        ":::asm\rlabel: lda #$20 ; unchanged\r:::\rTail.\r"
    )
    heading = petscii("# Heading\rNeutral successor.\rTail.\r")
    prose = petscii("Heading candidate\rNeutral successor.\rTail.\r")
    inline = petscii("Alpha *strong** tail.\rNeutral successor.\rTail.\r")
    strong = petscii("Alpha **strong** tail.\rNeutral successor.\rTail.\r")
    basic = petscii(":::basic\r10 PRNT \"X\"\r20 GOTO 10\r:::\rAfter.\r")
    asm = petscii(":::asm\rlabel: la #$20 ; comment\r .word label\r:::\rAfter.\r")
    fence = petscii(":::basc\r10 PRINT 1\r:::\rAfter fence.\rTail.\r")
    region = petscii(":::regin Work\rHidden candidate.\r:::end\rAfter region.\r")
    wrap = b"A" * (width - 1) + b"\rTail.\r"
    return (
        Edit("prose-insert", ordinary, ordinary.index(petscii("room")) + 2,
             petscii("Q")[0], "converge"),
        Edit("prose-to-heading", prose, 0, petscii("#")[0], "converge"),
        Edit("heading-to-prose", heading, 1, 0x14, "converge"),
        Edit("inline-open", inline, inline.index(b"*") + 1, petscii("*")[0],
             "converge"),
        Edit("inline-break", strong, strong.index(b"*") + 2, 0x14,
             "converge"),
        Edit("basic-token", basic, basic.index(petscii("PRNT")) + 2,
             petscii("I")[0], "converge", "changed-code"),
        Edit("asm-token", asm, asm.index(petscii("la #")) + 1,
             petscii("d")[0], "converge", "changed-code"),
        Edit("unchanged-code", ordinary, ordinary.index(petscii("room")) + 1,
             petscii("Z")[0], "converge", "unchanged-code"),
        Edit("CR", ordinary, ordinary.index(petscii("room")) + 1, 13,
             "fallback"),
        Edit("wrap", wrap, width - 2, petscii("Q")[0], "fallback"),
        Edit("fence", fence, fence.index(petscii("basc")) + 3,
             petscii("i")[0], "fallback"),
        Edit("region", region, region.index(petscii("regin")) + 4,
             petscii("o")[0], "fallback"),
    )


def matrix_description():
    cases = []
    for mode, width in MODES:
        for syntax, caps in CAPABILITIES:
            for edit in edit_definitions(width):
                cases.append({
                    "id": f"{syntax}-{width}-{edit.name}",
                    "mode": mode,
                    "width": width,
                    "syntax": syntax,
                    "caps": caps,
                    "edit": edit.name,
                    "route": edit.route,
                    "lexical": edit.lexical,
                })
    return {
        "abi": "styled-fixed-grid-ticket-v3",
        "semantic_tuple": SEMANTIC_TUPLE,
        "production_contract": {
            "records_symbol": "se_st_cp_rows",
            "record_stride": 5,
            "valid_symbol": "se_st_cp_valid",
            "count_symbol": "se_st_cp_count",
            "crc_symbol": "se_st_cp_crc",
            "crc_bytes": 2,
            "crc_coverage": 22 * 5,
            "key_symbol": "se_st_descriptor",
            "anchor_symbol": "se_v_rows",
            "anchor_stride": 3,
            "anchor_index_bias": 0,
            "required_execution_labels": {
                "admit_symbol": "C6 ticket admission entry",
                "reader_symbol": "R14 bounded source-reader entry",
                "consumer_symbol": "C33 READY consumer entry",
                "consumer_finish_symbol": "R25 frame17 publication entry",
                "fallback_symbol": "C14 transfer to the cold planner",
            },
            "interpretation": (
                "record i is the incoming carry for visible physical row i; its "
                "persistent anchor is se_v_rows[i]. Byte0 bit7 is logical-start transport "
                "authority and is masked before comparing the packed semantic tuple."
            ),
        },
        "cases": cases,
        "additional_gates": [
            "stale carry key refuses to full fallback before optimized writes",
            "one corrupt carry-table bit fails CRC before ADMITTED and falls back",
            "queued edit cancels active style work and newest source wins",
            "F6 UI cancels active style work and closing it restores exact body",
            "Undo and Redo preserve canonical history and exact body",
            "every top-level CPU call returns with balanced hardware stack",
            "separate matching registered CFG proof remains <=68 bytes with one IRQ/NMI",
        ],
        "qualification": {
            "converge": [
                "exact source, bitmap/screen, attributes/colors, 23 anchors and caret",
                "exactly one draw-sequence publication",
                "no parser or overlay work after publication",
                "no C11 full-layout op4/op5 graph",
                "block and inline feeds bounded by changed logical line through CR",
                "unchanged code invokes zero lexical feeds",
                "Markdown invokes zero lexical feeds",
                "C6 admission, R14 reader, and C33 consumer each execute once",
                "settled edit uses at most 10 overlay loads and 300000 instructions",
            ],
            "fallback": [
                "established full parser/layout path is observed",
                "same exact output/history/stack cleanup gates",
            ],
        },
    }


def symbols(path):
    return {
        name: int(address, 16)
        for address, name in re.findall(r"al ([0-9A-Fa-f]+) \.(\S+)", path.read_text())
    }


def runner(out):
    """Extend the existing read-only hot-path observer with parser/stack counts."""
    source = ROOT / "src/cache/hotpath-profile-probe/runner.py"
    spec = importlib.util.spec_from_file_location("carry_hotpath_runner", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Gate temporarily installs this function as observer.runner.  The reused
    # hot-path builder must still derive from the original observer, not recurse
    # through the temporary installation it saw at import time.
    module.ORIGINAL = ORIGINAL_OBSERVER_RUNNER
    original = module.build(out)
    cpp = out / "runner.cpp"
    text = cpp.read_text()
    needle = "static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);hp_step(m,r);"
    assert text.count(needle) == 1
    extra = r'''
static bool cm_on=false;static uint16_t cm_active,cm_seq,cm_prior,cm_overlay,cm_pc[32];
static uint8_t cm_tag[32];static unsigned cm_n;static uint64_t cm_calls[32],cm_post[32];
static uint8_t cm_min_sp=255;static uint64_t cm_wrap=0,cm_overlay_post=0;
extern "C" void cm_config(uint16_t active,uint16_t seq,uint16_t overlay,unsigned n,const uint16_t*pc,const uint8_t*tag){cm_active=active;cm_seq=seq;cm_overlay=overlay;cm_n=n;memcpy(cm_pc,pc,n*2);memcpy(cm_tag,tag,n);}
extern "C" void cm_begin(uint16_t seq){cm_prior=seq;memset(cm_calls,0,sizeof(cm_calls));memset(cm_post,0,sizeof(cm_post));cm_min_sp=255;cm_wrap=cm_overlay_post=0;cm_on=true;}
extern "C" void cm_end(){cm_on=false;}
extern "C" uint64_t cm_get(unsigned kind,unsigned i){if(kind==0)return cm_calls[i];if(kind==1)return cm_post[i];if(kind==2)return cm_min_sp;if(kind==3)return cm_wrap;if(kind==4)return cm_overlay_post;return 0;}
static void cm_step(ZeroPagePeddle*m,const decltype(zeropage_peddle_regs((ZeroPagePeddle*)nullptr))&r){if(!cm_on)return;
 if(r.sp<cm_min_sp)cm_min_sp=r.sp;auto op=zeropage_peddle_read(m,r.pc);if((op==0x20&&r.sp<2)||((op==0x48||op==0x08)&&r.sp==0))cm_wrap++;
 uint16_t seq=zeropage_peddle_read(m,cm_seq)|(zeropage_peddle_read(m,cm_seq+1)<<8);uint8_t active=0;
 if(r.pc==cm_overlay&&seq!=cm_prior)cm_overlay_post++;
 if(r.pc>=0xa000&&r.pc<0xc000)active=zeropage_peddle_read(m,cm_active+(r.pc>=0xb000));
 for(unsigned i=0;i<cm_n;i++)if(r.pc==cm_pc[i]&&active==cm_tag[i]){cm_calls[i]++;if(seq!=cm_prior)cm_post[i]++;}}
'''
    text = text.replace(needle, extra + needle + "cm_step(m,r);")
    cpp.write_text(text)
    suffix = ".dylib" if sys.platform == "darwin" else ".so"
    target = out / ("carry-matrix-runner" + suffix)
    subprocess.run([
        "clang++", "-std=c++20", "-O2",
        "-dynamiclib" if sys.platform == "darwin" else "-shared", "-fPIC",
        "-I" + str(profile.observer.geos.grid.VENDOR), cpp,
        ROOT / ("build/libse_peddle" + suffix), "-o", target,
    ], check=True)
    dll = C.CDLL(str(target))
    for name in (
        "gm_rom", "gm_rom_count", "gm_profile", "gm_metric", "gm_run", "gm_idle",
        "gm_read", "gm_reu", "fr_begin", "fr_end", "fr_mask", "fr_bad",
        "fr_writes", "pb_config", "pb_begin", "pb_end", "pb_get",
        "pb_fault_get", "ob_ring", "ob_ring_get", "hp_config", "hp_begin",
        "hp_end", "hp_get", "hp_op", "hp_group",
    ):
        old, new = getattr(original, name), getattr(dll, name)
        new.argtypes, new.restype = old.argtypes, old.restype
    dll.cm_config.argtypes = [C.c_uint16, C.c_uint16, C.c_uint16, C.c_uint,
                              C.c_void_p, C.c_void_p]
    dll.cm_begin.argtypes = [C.c_uint16]
    dll.cm_get.argtypes = [C.c_uint, C.c_uint]
    dll.cm_get.restype = C.c_uint64
    return dll


def configure(g, contract=None):
    f, dll = g.f, g.dll
    points, crc_returns = profile.points(f)
    names = g.identity["names"]
    dll.hp_config(
        f.s["se_overlay_active"], f.s["se_overlay_frame"],
        f.s["se_e_draw_sequence"], (C.c_uint16 * 8)(*points),
        len(crc_returns),
        (C.c_uint16 * len(crc_returns))(*crc_returns),
        names.index("gtype") + 1, names.index("code") + 1,
    )
    hooks = []
    for asset, required in PARSER_POINTS.items():
        exported = symbols(g.frozen / "build/overlays" / (asset + ".lbl"))
        tag = names.index(asset) + 1
        for name in required:
            hooks.append((asset, name, exported[name], tag))
    if contract and contract.get("admit_asset"):
        fields = [
            ("admit_asset", "admit_symbol", "admit"),
            ("reader_asset", "reader_symbol", "reader"),
            ("consumer_asset", "consumer_symbol", "consumer"),
            ("consumer_asset", "consumer_finish_symbol", "finish"),
            ("fallback_asset", "fallback_symbol", "fallback"),
        ]
        for asset_field, symbol_field, label in fields:
            asset = contract[asset_field]
            exported = symbols(g.frozen / "build/overlays" / (asset + ".lbl"))
            hooks.append(("transaction", label, exported[contract[symbol_field]],
                          names.index(asset) + 1))
    dll.cm_config(
        f.s["se_overlay_active"], f.s["se_e_draw_sequence"],
        f.s["se_overlay_call"], len(hooks),
        (C.c_uint16 * len(hooks))(*(row[2] for row in hooks)),
        (C.c_uint8 * len(hooks))(*(row[3] for row in hooks)),
    )
    return names, hooks


def counts(dll, hooks):
    result = {}
    post = {}
    for index, (asset, name, _, _) in enumerate(hooks):
        key = asset + ":" + name
        result[key] = int(dll.cm_get(0, index))
        post[key] = int(dll.cm_get(1, index))
    return result, post


def observe(g, names, hooks, operation):
    f, dll = g.f, g.dll
    initial = f.total_instructions
    loads = f.get("se_overlay_loads", 2)
    dmas = f.get("se_reu_dma_calls", 2)
    dma_bytes = f.get("se_reu_dma_bytes", 3)
    sequence = f.get("se_e_draw_sequence", 2)
    dll.hp_begin(sequence)
    dll.cm_begin(sequence)
    try:
        operation()
        profile.drain(f)
    finally:
        dll.cm_end()
        dll.hp_end()
    parser, post = counts(dll, hooks)
    entries = {
        name: {
            "calls": int(dll.hp_get(3, index + 1)),
            "ops": {str(op): int(dll.hp_op(index + 1, op))
                    for op in range(256) if dll.hp_op(index + 1, op)},
        }
        for index, name in enumerate(names) if dll.hp_get(3, index + 1)
    }
    publications = (f.get("se_e_draw_sequence", 2) - sequence) & 0xFFFF
    return {
        "instructions": f.total_instructions - initial,
        "first_publication_instructions": int(dll.hp_get(0, 1)),
        "publications": publications,
        "loads": (f.get("se_overlay_loads", 2) - loads) & 0xFFFF,
        "dma_calls": (f.get("se_reu_dma_calls", 2) - dmas) & 0xFFFF,
        "dma_bytes": (f.get("se_reu_dma_bytes", 3) - dma_bytes) & 0xFFFFFF,
        "entries": entries,
        "parser": parser,
        "parser_after_publication": post,
        "minimum_sp": int(dll.cm_get(2, 0)),
        "stack_wraps": int(dll.cm_get(3, 0)),
        "overlay_calls_after_publication": int(dll.cm_get(4, 0)),
    }


def anchors(f):
    return tuple(
        int.from_bytes(f.read(f.s["se_v_rows"] + index * 3, 3), "little")
        for index in range(22)
    ) + (f.get("se_v_bottom"),)


def pixel_oracle(f, source, caps, tag):
    (primary, attributes), wanted_anchors, seen, _ = \
        profile.observer.geos.grid.expected(f, source)
    if caps == 1:
        primary, attributes = native_profile.markdown_expected(
            f, source, primary, attributes
        )
    mode = f.get("se_mode", 1)
    if mode == 0:
        actual_primary = f.read(0x4000, 1000)
        actual_attributes = f.read(0xD800, 1000)
    else:
        actual_primary = f.read(0x6000, 8000)
        actual_attributes = f.read(0x4000, 1000)
    assert actual_primary == primary, (tag, "primary pixels/screen")
    assert actual_attributes == attributes, (tag, "attributes/colors")
    assert anchors(f) == wanted_anchors, (tag, "23 exact anchors")
    assert seen == (f.get("se_v_caret_row", 1), f.get("se_v_caret_col", 1)), \
        (tag, "caret row/column")
    return hashlib.sha256(primary + attributes).hexdigest()


def history(f):
    fields = (
        ("se_h_current", 4), ("se_h_saved", 4), ("se_h_end", 2),
        ("se_h_cursor", 2), ("se_h_counter", 4), ("se_h_group", 1),
        ("se_h_open_group", 1), ("se_h_fault", 1), ("se_h_trimmed", 2),
    )
    return b"".join(f.read(f.s[name], width) for name, width in fields)


def setup(f, edit, mode, syntax, caps):
    f.source(edit.source, physical=256)
    f.typed(petscii("syntax " + syntax))
    f.command(96 + mode)
    profile.drain(f)
    f.position(edit.position)
    profile.drain(f)
    assert f.get("se_mode", 1) == mode
    assert f.get("se_render_caps", 1) == caps
    assert f.get("se_st_valid", 1) == 1
    pixel_oracle(f, edit.source, caps, "setup")


def line_bound(source, position):
    start = source.rfind(b"\r", 0, position) + 1
    end = source.find(b"\r", position)
    if end < 0:
        end = len(source)
    else:
        end += 1
    return end - start


def verify_route(row, edit, caps, source, qualification, width):
    parser = row["parser"]
    block = parser.get("viewsource:se_sm_feed", 0)
    inline = parser.get("styler:se_si_feed", 0)
    lexical = parser.get("lexical:se_sl_feed", 0)
    layout_ops = row["entries"].get("layout", {}).get("ops", {})
    full_layout = bool({"4", "5"} & layout_ops.keys())
    failures = row.setdefault("gate_failures", [])

    def require(condition, gate, detail=None):
        if not condition:
            failures.append({"gate": gate, "detail": detail})

    require(not row["stack_wraps"], "hardware-stack-wrap", row["stack_wraps"])
    require(row["minimum_sp"] <= 0xFD, "observer-inactive", row["minimum_sp"])
    if not qualification:
        return
    if edit.route == "converge":
        require(row["loads"] <= 10, "overlay-load-budget", row["loads"])
        require(row["instructions"] <= 300_000, "instruction-budget",
                row["instructions"])
        require(row["publications"] == 1, "single-publication", row["publications"])
        require(not any(row["parser_after_publication"].values()),
                "parser-after-publication", row["parser_after_publication"])
        require(row["overlay_calls_after_publication"] == 0,
                "overlay-after-publication", row["overlay_calls_after_publication"])
        bound = edit.changed_line_limit or line_bound(source, edit.position)
        require(block <= bound and inline <= bound, "parse-crossed-converged-CR",
                {"block": block, "inline": inline, "bound": bound})
        require(not full_layout, "full-layout-graph", layout_ops)
        if caps == 1 or edit.lexical == "unchanged-code":
            require(lexical == 0, "unnecessary-lexer", lexical)
        elif edit.lexical == "changed-code":
            require(0 < lexical <= bound, "changed-code-lexer-bound",
                    {"lexical": lexical, "bound": bound})
        for point in ("admit", "reader", "consumer", "finish"):
            key = "transaction:" + point
            require(parser.get(key, 0) == 1, "unique-" + point,
                    parser.get(key, 0))
        require(parser.get("transaction:fallback", 0) == 0,
                "admitted-edit-entered-fallback",
                parser.get("transaction:fallback", 0))
    else:
        require(parser.get("transaction:finish", 0) == 0,
                "structural-transaction-published",
                parser.get("transaction:finish", 0))
        require(parser.get("transaction:reader", 0) >= 1,
                "structural-missing-cold-reader",
                parser.get("transaction:reader", 0))
        if width > 40:
            require(full_layout, "structural-missing-full-fallback", layout_ops)
        # C6 can refuse before admission (CR), C14 can reject changed carry,
        # or C33 can reject changed row geometry (wrap). 40-column cold paint
        # does not use C11; wide cold paint does. None may reach frame17.


def read_contract(path, g):
    f = g.f
    if path is None:
        # The production ABI uses the existing style-checkpoint window.  These
        # exports add no instrumentation counters or test-only product state.
        value = {
            "abi": "styled-fixed-grid-ticket-v3",
            "semantic_tuple": SEMANTIC_TUPLE,
            "records_symbol": "se_st_cp_rows",
            "valid_symbol": "se_st_cp_valid",
            "count_symbol": "se_st_cp_count",
            "crc_symbol": "se_st_cp_crc",
            "crc_bytes": 2,
            "crc_coverage": 22 * 5,
            "key_symbol": "se_st_descriptor",
            "record_stride": 5,
            "semantic_offset": 0,
            "anchor_symbol": "se_v_rows",
            "anchor_stride": 3,
            "anchor_index_bias": 0,
            "marker_byte": 0,
            "marker_mask": 0x80,
            "fence_mask": 0x0F,
            "language_mask": 0x30,
            "language_shift": 4,
            "regions_byte": 1,
            "regions_mask": 0x1F,
            "admit_asset": "window",
            "admit_symbol": "lrv_style_ticket",
            "reader_asset": "viewsource",
            "reader_symbol": "se_sb_init",
            "consumer_asset": "geostail",
            "consumer_symbol": "lrv_style_admit",
            "consumer_finish_symbol": "lrv_finish",
            "fallback_asset": "styler",
            "fallback_symbol": "se_st_fast_fallback",
        }
    else:
        value = json.loads(path.read_text())
    failures = []
    if value.get("abi") != "styled-fixed-grid-ticket-v3":
        failures.append("wrong abi")
    if value.get("semantic_tuple") != SEMANTIC_TUPLE:
        failures.append("semantic tuple is not exact five-byte ABI")
    for field in ("records_symbol", "valid_symbol", "key_symbol"):
        symbol = value.get(field)
        if not symbol or symbol not in f.s:
            failures.append("missing export " + str(symbol or field))
    if value.get("record_count") is None:
        symbol = value.get("count_symbol")
        if not symbol or symbol not in f.s:
            failures.append("missing export " + str(symbol or "count_symbol"))
    crc_symbol = value.get("crc_symbol")
    if (not crc_symbol or crc_symbol not in f.s or value.get("crc_bytes") != 2
            or value.get("crc_coverage") != 22 * 5):
        failures.append("checkpoint CRC16 must seal all 110 carry-table bytes")
    if value.get("record_stride", 0) < value.get("semantic_offset", 0) + 5:
        failures.append("record stride cannot hold packed semantic5")
    inline_anchor = value.get("anchor_offset") is not None
    external_anchor = value.get("anchor_symbol") in f.s and value.get("anchor_stride") == 3
    if not inline_anchor and not external_anchor:
        failures.append("record needs inline or external 24-bit anchor")
    if value.get("marker_byte") != 0 or value.get("marker_mask") != 0x80:
        failures.append("logical-start marker must be bit7 of packed byte0")
    if (value.get("fence_mask") != 0x0F or
            value.get("language_mask") != 0x30 or
            value.get("language_shift") != 4 or
            value.get("regions_byte") != 1):
        failures.append("wrong packed carry fields")
    if value.get("regions_mask") != 0x1F:
        failures.append("region depth must use low5 bits of carry byte1")
    for asset_field, symbol_fields in (
        ("admit_asset", ("admit_symbol",)),
        ("reader_asset", ("reader_symbol",)),
        ("consumer_asset", ("consumer_symbol", "consumer_finish_symbol")),
        ("fallback_asset", ("fallback_symbol",)),
    ):
        asset = value.get(asset_field)
        if not asset or asset not in g.identity["names"]:
            failures.append("missing sealed " + asset_field)
            continue
        exported = symbols(g.frozen / "build/overlays" / (asset + ".lbl"))
        for field in symbol_fields:
            label = value.get(field)
            if not label:
                failures.append("missing execution label " + field)
            elif label and label not in exported:
                failures.append("missing execution label " + label)
    return value, failures


def locate_record(f, contract, anchor):
    base = f.s[contract["records_symbol"]]
    count = contract.get("record_count")
    if count is None:
        count = f.get(contract["count_symbol"], 1)
    stride = contract["record_stride"]
    matches = []
    for index in range(count):
        if contract.get("anchor_offset") is not None:
            address = base + index * stride + contract["anchor_offset"]
        else:
            address = (f.s[contract["anchor_symbol"]]
                       + (index + contract.get("anchor_index_bias", 0))
                       * contract["anchor_stride"])
        found = int.from_bytes(f.read(address, 3), "little")
        if found == anchor:
            matches.append(base + index * stride)
    assert len(matches) == 1, ("carry record anchor", anchor, matches)
    return matches[0]


def semantic_carry(raw, contract):
    """Canonical six-byte semantic tuple decoded from packed transport."""
    assert len(raw) == 5
    packed = raw[0]
    return bytes((
        packed & contract["fence_mask"],
        (packed & contract["language_mask"]) >> contract["language_shift"],
        raw[contract["regions_byte"]] & contract["regions_mask"],
        *raw[2:5],
    ))


def validate_carry_table(f, contract, source):
    """Decode actual published records, masking transport bit7 from regions."""
    assert f.get(contract["valid_symbol"], 1) == 1
    count = contract.get("record_count")
    if count is None:
        count = f.get(contract["count_symbol"], 1)
    assert 0 < count <= 22, ("carry count", count)
    base = f.s[contract["records_symbol"]]
    sealed = f.read(base, contract["crc_coverage"])
    observed_crc = f.get(contract["crc_symbol"], contract["crc_bytes"])
    assert observed_crc == binascii.crc_hqx(sealed, 0xFFFF), \
        ("carry table CRC16", observed_crc)
    rows = []
    for index in range(count):
        raw = f.read(base + index * contract["record_stride"]
                     + contract["semantic_offset"], 5)
        fence = raw[0] & contract["fence_mask"]
        language = ((raw[0] & contract["language_mask"])
                    >> contract["language_shift"])
        regions = raw[contract["regions_byte"]] & contract["regions_mask"]
        marker = bool(raw[contract["marker_byte"]] & contract["marker_mask"])
        semantic = semantic_carry(raw, contract)
        toggled = bytearray(raw)
        toggled[contract["marker_byte"]] ^= contract["marker_mask"]
        assert semantic_carry(bytes(toggled), contract) == semantic, \
            ("transport marker entered semantic equality", index, raw.hex())
        assert raw[0] & 0x40 == 0 and raw[1] & 0xE0 == 0, \
            ("reserved carry bits", index, raw.hex())
        assert fence <= 14 and language <= 2 and regions <= 16, \
            ("normalized carry range", index, raw.hex())
        if fence == 0:
            assert language == 0, ("text carry language normalization", index, raw.hex())
        if contract.get("anchor_offset") is not None:
            anchor_address = (base + index * contract["record_stride"]
                              + contract["anchor_offset"])
        else:
            anchor_address = (f.s[contract["anchor_symbol"]]
                              + (index + contract.get("anchor_index_bias", 0))
                              * contract["anchor_stride"])
        anchor = int.from_bytes(f.read(anchor_address, 3), "little")
        logical_start = anchor == 0 or (anchor <= len(source) and source[anchor - 1] == 13)
        assert marker == logical_start, \
            ("boundary-start marker", index, anchor, marker, logical_start)
        rows.append({
            "index": index, "anchor": anchor, "fence": fence,
            "language": language, "regions": regions,
            "overflow": int.from_bytes(raw[2:5], "little"),
            "boundary_start": marker,
            "semantic_hex": semantic.hex(),
        })
    return rows


def carry_fault(g, names, hooks, contract, mode, syntax, caps, kind):
    f = g.f
    edit = edit_definitions((40, 60, 80)[mode])[0]
    setup(f, edit, mode, syntax, caps)
    before_history = history(f)
    validate_carry_table(f, contract, edit.source)
    if kind == "stale-key":
        address = f.s[contract["key_symbol"]] + contract.get("key_revision_offset", 17)
        old = f.m.read(address)
        f.m.write(address, old ^ 1)
    else:
        boundary = edit.source.rfind(b"\r", 0, edit.position) + 1
        record = locate_record(f, contract, boundary)
        if kind == "corrupt-semantic":
            address = record + contract["semantic_offset"]
            f.m.write(address, f.m.read(address) ^ 1)
        elif kind == "bad-marker":
            address = (record + contract["semantic_offset"]
                       + contract["marker_byte"])
            f.m.write(address, f.m.read(address) ^ contract["marker_mask"])
        elif kind == "short-count":
            index = (record - f.s[contract["records_symbol"]]) // contract["record_stride"]
            f.put(contract["count_symbol"], index, 1)
        elif kind == "invalid":
            f.put(contract["valid_symbol"], 0, 1)
        else:
            raise AssertionError(("unknown carry fault", kind))
    expected = edit.edited()
    post_edit = []
    def operation():
        f.key(edit.key)
        post_edit.append(f.canonical())
    row = observe(g, names, hooks, operation)
    assert f.merged() == expected
    assert f.canonical() == post_edit[0], (kind, "render changed canonical/history")
    # A pending hot edit need not advance the committed Undo descriptor until
    # its normal flush point; canonical identity above is the relevant guard.
    row["pixels_sha256"] = pixel_oracle(f, expected, caps, kind)
    layout_ops = row["entries"].get("layout", {}).get("ops", {})
    assert {"4", "5"} & layout_ops.keys(), \
        (kind, "faulted carry did not refuse to full fallback", row["entries"])
    assert row["parser"].get("transaction:admit", 0) == 1, \
        (kind, "fault did not exercise C6 admission", row["parser"])
    assert row["parser"].get("transaction:consumer", 0) == 0, \
        (kind, "fault reached C33 READY consumer", row["parser"])
    # A C6 preflight fault can return before R14. Requiring the full graph
    # above proves refusal without imposing a synthetic common fallback edge.
    return row


def cancellation_cases(g, mode=2):
    f = g.f
    source = petscii(
        ":::basic\r10 PRINT \"" + "A" * 300 + "\"\r20 GOTO 10\r:::\rTail.\r"
    )
    position = len(petscii(":::basic\r"))
    rows = []
    for tag, key in (("queued-edit", petscii("Q")[0]), ("F6-help", 0x8B)):
        edit = Edit(tag, source, position, 32, "fallback")
        setup(f, edit, mode, "full", 3)
        f.key(32)
        edited = edit.edited()
        f.begin_style()
        assert not f.call("se_doc_read_acquire").p & 1
        f.queued(key)
        f.tick()
        assert not f.get("se_st_busy", 1) and not f.get("se_fs_owned", 1)
        assert f.get("se_doc_read_locks", 1) == 1, (tag, "foreign lease lost")
        assert not f.call("se_doc_read_release").p & 1
        if tag == "queued-edit":
            expected = edited[: position + 1] + bytes((key,)) + edited[position + 1 :]
            profile.drain(f)
        else:
            assert f.get("se_e_ui", 1) == 1, (tag, "help did not open")
            f.key(0x8B)
            assert f.get("se_e_ui", 1) == 0, (tag, "help did not close")
            expected = edited
            profile.drain(f)
        assert f.merged() == expected, (tag, "newest source")
        digest = pixel_oracle(f, expected, 3, tag)
        rows.append({"tag": tag, "source_bytes": len(expected),
                     "pixels_sha256": digest})
    return rows


def validate_stack_result(path, identity):
    if path is None:
        return {"status": "NOT_READY", "reason": "missing --stack-result"}
    result = json.loads(path.read_text())
    resident = result.get("resident_sha256") or result.get("identity", {}).get("prg_sha256")
    foreground = result.get("foreground", result)
    relative = foreground.get("relative_combined")
    assert resident == identity["prg_sha256"], ("stack result fixture mismatch", resident)
    assert foreground.get("status") in ("bounded", "bounded-declared-foreground")
    assert relative is not None and relative <= 68, ("stack bound", relative)
    return {"status": "PASS", "relative_combined": relative,
            "source": str(path)}


def run(out, fixture, contract_path=None, stack_result=None, smoke=False):
    out.mkdir(parents=True)
    saved = profile.observer.runner
    profile.observer.runner = runner
    try:
        gate = profile.observer.Gate(out, fixture)
    finally:
        profile.observer.runner = saved
    f = gate.f
    contract, contract_failures = read_contract(contract_path, gate)
    qualification = not contract_failures
    names, hooks = configure(gate, contract if qualification else None)
    cases = []
    try:
        selected = {"prose-insert", "heading-to-prose", "unchanged-code", "CR"} if smoke else None
        run_modes = (MODES[-1],) if smoke else MODES
        run_caps = CAPABILITIES
        for mode, width in run_modes:
            for syntax, caps in run_caps:
                for edit in edit_definitions(width):
                    if selected is not None and edit.name not in selected:
                        continue
                    tag = f"{syntax}-{width}-{edit.name}"
                    setup(f, edit, mode, syntax, caps)
                    carry_rows = (validate_carry_table(f, contract, edit.source)
                                  if qualification else [])
                    expected = edit.edited()
                    post_edit = []
                    def operation(edit=edit):
                        f.key(edit.key)
                        post_edit.append({
                            "canonical": f.canonical(),
                            "ticket_phase": f.get("se_st_tx", 1),
                            "view_length": f.get("se_v_length", 3),
                        })
                    row = observe(gate, names, hooks, operation)
                    assert f.merged() == expected, (tag, "source")
                    assert f.canonical() == post_edit[0]["canonical"], \
                        (tag, "render changed source/history/clipboard")
                    if post_edit[0]["ticket_phase"] == 0xA5:
                        assert post_edit[0]["view_length"] == len(expected), \
                            (tag, "C6 admitted stale view length",
                             post_edit[0]["view_length"], len(expected))
                    assert not any(f.get(name, 1) for name in (
                        "se_e_job", "se_e_draw_busy", "se_e_redraw", "se_f_owner",
                        "se_doc_read_locks", "se_e_error",
                    )), (tag, "cleanup", f.debug())
                    assert f.get("se_st_request", 1) != 1, \
                        (tag, "style request still pending", f.debug())
                    row["pixels_sha256"] = pixel_oracle(f, expected, caps, tag)
                    verify_route(row, edit, caps, expected, qualification, width)
                    before_undo = history(f)
                    f.command(16)
                    profile.drain(f)
                    assert f.merged() == edit.source, (tag, "Undo source")
                    pixel_oracle(f, edit.source, caps, tag + "-undo")
                    f.command(17)
                    profile.drain(f)
                    assert f.merged() == expected, (tag, "Redo source")
                    pixel_oracle(f, expected, caps, tag + "-redo")
                    assert history(f) != before_undo, (tag, "Undo/Redo history did not move")
                    row.update(id=tag, mode=mode, width=width, syntax=syntax,
                               caps=caps, edit=edit.name, route=edit.route,
                               admission=post_edit[0]["ticket_phase"] == 0xA5,
                               admission_view_length=post_edit[0]["view_length"],
                               carry_records=len(carry_rows),
                               carry_sha256=(hashlib.sha256(json.dumps(
                                   carry_rows, sort_keys=True
                               ).encode()).hexdigest() if carry_rows else None))
                    cases.append(row)
                    (out / "progress.json").write_text(json.dumps(cases, indent=2) + "\n")
                    print(("FAIL" if row.get("gate_failures") else
                           "PASS" if qualification else "BASELINE"), tag,
                          row["instructions"], "instructions", flush=True)
        faults = []
        cancellations = []
        if qualification:
            for kind in (
                "stale-key", "corrupt-semantic", "bad-marker",
                "short-count", "invalid",
            ):
                try:
                    faults.append({"kind": kind, **carry_fault(
                        gate, names, hooks, contract, 2, "full", 3, kind
                    )})
                except AssertionError as error:
                    faults.append({"kind": kind, "status": "FAIL",
                                   "error": repr(error)})
            try:
                cancellations = cancellation_cases(gate)
            except AssertionError as error:
                cancellations = [{"status": "FAIL", "error": repr(error)}]
        stack = validate_stack_result(stack_result, gate.identity) if qualification else {
            "status": "NOT_READY", "reason": "carry contract missing/invalid"
        }
        failed = (any(row.get("gate_failures") for row in cases)
                  or any(row.get("status") == "FAIL" for row in faults)
                  or any(row.get("status") == "FAIL" for row in cancellations))
        status = ("FAIL" if failed else "PASS"
                  if qualification and stack["status"] == "PASS" else "NOT_READY")
        result = {
            "status": status,
            "identity": gate.identity,
            "qualification_enabled": qualification,
            "contract_failures": contract_failures,
            "semantic_tuple": SEMANTIC_TUPLE,
            "cases": cases,
            "faults": faults,
            "cancellations": cancellations,
            "stack": stack,
            "matrix": matrix_description(),
            "scope": __doc__,
        }
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        f.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--carry-contract", type=Path)
    parser.add_argument("--stack-result", type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.describe:
        print(json.dumps(matrix_description(), indent=2))
        return
    if args.fixture is None:
        parser.error("--fixture is required unless --describe is used")
    out = BUILD / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", out, flush=True)
    result = run(
        out, args.fixture.resolve(),
        args.carry_contract.resolve() if args.carry_contract else None,
        args.stack_result.resolve() if args.stack_result else None,
        args.smoke,
    )
    print(json.dumps({"status": result["status"], "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
