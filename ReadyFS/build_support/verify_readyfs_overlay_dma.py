#!/usr/bin/env python3
"""Reject regressions in ReadyFS's flat cc65-to-REU overlay DMA boundary."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ASM = ROOT / "src" / "apps" / "readyfs" / "readyfs_reu_overlay_asm.s"
OVERLAY = ROOT / "src" / "apps" / "readyfs" / "readyfs_overlay.c"
REU = ROOT / "src" / "apps" / "readyfs" / "readyfs_reu.c"
RESIDENT = ROOT / "src" / "apps" / "readyfs" / "readyfs.c"
DRIVE_UI = ROOT / "src" / "apps" / "readyfs" / "readyfs_driveui.c"
RECURSIVE = ROOT / "src" / "apps" / "readyfs" / "readyfs_recursive.c"
RECURSIVE_NAME = (ROOT / "src" / "apps" / "readyfs" /
                  "readyfs_recursive_name.s")
BACKEND = ROOT / "src" / "apps" / "readyfs" / "readyfs_backend.c"
UTILITY = ROOT / "src" / "apps" / "readyfs" / "readyfs_utility.c"
TREE = ROOT / "src" / "apps" / "readyfs" / "readyfs_tree.c"
CONTENT = ROOT / "src" / "apps" / "readyfs" / "readyfs_content.c"
BATCH = ROOT / "src" / "apps" / "readyfs" / "readyfs_batch.c"
TAPE = ROOT / "src" / "apps" / "readyfs" / "readyfs_tape.c"
TAPE_SPOOL = (ROOT / "src" / "apps" / "readyfs" /
              "readyfs_tape_spool.s")
SOFTNAME = ROOT / "src" / "apps" / "readyfs" / "readyfs_softname.s"
MAKEFILE = ROOT / "Makefile"
LINKER_CFG = ROOT / "cfg" / "readyfs_overlay.cfg"


def require(text: str, pattern: str, label: str, failures: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        failures.append(label)


def main() -> int:
    asm = ASM.read_text(encoding="utf-8")
    overlay = OVERLAY.read_text(encoding="utf-8")
    reu = REU.read_text(encoding="utf-8")
    resident = RESIDENT.read_text(encoding="utf-8")
    drive_ui = DRIVE_UI.read_text(encoding="utf-8")
    recursive = RECURSIVE.read_text(encoding="utf-8")
    recursive_name = RECURSIVE_NAME.read_text(encoding="utf-8")
    backend = BACKEND.read_text(encoding="utf-8")
    utility = UTILITY.read_text(encoding="utf-8")
    tree = TREE.read_text(encoding="utf-8")
    content = CONTENT.read_text(encoding="utf-8")
    batch = BATCH.read_text(encoding="utf-8")
    ui = (BATCH.parent / "readyfs_ui.c").read_text(encoding="utf-8")
    tape = TAPE.read_text(encoding="utf-8")
    tape_spool = TAPE_SPOOL.read_text(encoding="utf-8")
    softname = SOFTNAME.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    linker_cfg = LINKER_CFG.read_text(encoding="utf-8")
    failures: list[str] = []

    require(linker_cfg,
            r"MAIN:[\s\S]*?size\s*=\s*__HIMEM__\s*-\s*__HEADER_LAST__",
            "overlay build must start the cc65 software stack at $D000",
            failures)

    for symbol in ("_readyfs_reu_overlay_store",
                   "_readyfs_reu_overlay_fetch",
                   "_readyfs_reu_session_store",
                   "_readyfs_reu_session_fetch",
                   "_readyfs_reu_batch_store",
                   "_readyfs_reu_batch_fetch"):
        require(asm, rf"^\s*\.export\s+{symbol}\s*$",
                f"missing export {symbol}", failures)
        require(asm, rf"^{symbol}:\s*$",
                f"missing entry {symbol}", failures)

    require(asm, r"^\s*\.importzp\s+sp\s*$", "missing cc65 sp import",
            failures)
    require(asm, r"^\s*\.import\s+pushax,\s*incsp6\s*$",
            "missing flat six-byte argument helpers", failures)
    require(asm, r"lda\s+#\$90", "missing REU stash command", failures)
    require(asm, r"lda\s+#\$91", "missing REU fetch command", failures)
    for register in range(0xDF01, 0xDF09):
        require(asm, rf"sta\s+\${register:04X}",
                f"missing REU register ${register:04X}", failures)
    if len(re.findall(r"jmp\s+incsp6", asm)) != 4:
        failures.append(
            "overlay/session success and failure must remove exactly six bytes")
    require(asm, r"adc\s+#\$20", "session DMA must add the $2000 base",
            failures)

    require(overlay, r"static unsigned char load_cached\(unsigned char slot\)",
            "cache loader must accept only a one-byte slot selector", failures)
    for slot in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        require(overlay, rf"load_cached\({slot}u\)",
                f"missing cache slot {slot}", failures)
    for offset in ("MATCH", "PLAN", "HELP", "BACKEND", "CMDPATH", "DRIVE",
                   "UTILITY", "TREE", "CONTENT", "RECURSIVE"):
        require(overlay, rf"RF_REU_OVERLAY_{offset}_OFF",
                f"missing explicit {offset.lower()} cache offset", failures)
    require(overlay, r"readyfs_cmdpath_selftest\(\)",
            "CMD/SD2IEC sidecar must execute its translation self-test",
            failures)
    require(overlay,
            r"RF_NESTED_CMDPATH[\s\S]*?readyfs_cmdpath_dispatch"
            r"[\s\S]*?RF_REU_OVERLAY_HELP_OFF",
            "nested CMD path calls must dispatch then restore help",
            failures)
    operation_fold = overlay.find(
        "operation = (unsigned char)(nested->operation & 0x1Fu)")
    cmdpath_branch = overlay.find(
        "operation == RF_NESTED_CMDPATH", operation_fold)
    help_restore = overlay.find("RF_REU_OVERLAY_HELP_OFF", cmdpath_branch)
    help_return = overlay.find("return result;", help_restore)
    backend_branch = overlay.find(
        "operation == RF_NESTED_BACKEND", cmdpath_branch)
    if min(operation_fold, cmdpath_branch, help_restore, help_return,
           backend_branch) < 0 or not (
           operation_fold < cmdpath_branch < help_restore < help_return <
           backend_branch):
        failures.append(
            "help-owned CMD path calls must return before backend restore")
    require(overlay,
            r"RF_NESTED_BACKEND[\s\S]*?readyfs_backend_dispatch"
            r"[\s\S]*?RF_NESTED_RETURN_DRIVE[\s\S]*?"
            r"RF_REU_OVERLAY_DRIVE_OFF",
            "nested backend calls must restore the drive controller",
            failures)
    require(overlay,
            r"RF_NESTED_RECURSIVE[\s\S]*?readyfs_recursive_dispatch"
            r"[\s\S]*?RF_NESTED_MATCH[\s\S]*?readyfs_match",
            "backend planning must reach recursive and matcher sidecars",
            failures)
    require(overlay,
            r"RF_NESTED_RETURN_BACKEND[\s\S]*?"
            r"RF_REU_OVERLAY_BACKEND_OFF",
            "native nested calls must restore backend code before RTS",
            failures)
    require(overlay,
            r"unsigned char readyfs_overlay_drive[\s\S]*?"
            r"readyfs_driveui_dispatch[\s\S]*?RF_REU_OVERLAY_MATCH_OFF",
            "drive sidecar calls must dispatch then restore matcher",
            failures)
    require(drive_ui, r"RF_REU_DRIVE_PROFILE_OFF[\s\S]*?"
            r"readyfs_reu_session_store",
            "detected profiles must persist in the session REU", failures)
    require(overlay, r"readyfs_driveui_abi\(\) == RF_DRIVEUI_ABI[\s\S]*?"
            r"readyfs_driveui_reset\(\)",
            "drive profile registry must be cleared after ABI validation",
            failures)
    require(overlay, r"readyfs_utility_abi\(\) != RF_UTILITY_ABI",
            "utility sidecar must reject an ABI mismatch", failures)
    require(overlay, r"readyfs_tree_abi\(\) != RF_TREE_ABI",
            "tree sidecar must pass its ABI probe", failures)
    require(overlay, r"readyfs_content_abi\(\) == RF_CONTENT_ABI",
            "content sidecar must pass its ABI probe", failures)
    require(overlay, r"readyfs_batch_abi\(\) == RF_BATCH_ABI",
            "batch/editor sidecar must pass its ABI probe", failures)
    require(overlay, r"readyfs_tape_abi\(\) == RF_TAPE_ABI",
            "tape/core sidecar must pass its ABI probe", failures)
    require(overlay,
            r"unsigned char readyfs_overlay_utility[\s\S]*?"
            r"RF_REU_OVERLAY_CONTENT_OFF[\s\S]*?"
            r"readyfs_content_dispatch[\s\S]*?"
            r"RF_REU_OVERLAY_UTILITY_OFF[\s\S]*?"
            r"readyfs_utility_dispatch[\s\S]*?restore_match\(\)",
            "utility gateway must route cached utility/content slots then restore matcher",
            failures)
    require(overlay,
            r"unsigned char readyfs_overlay_tree[\s\S]*?"
            r"RF_REU_OVERLAY_TREE_OFF[\s\S]*?"
            r"readyfs_tree_dispatch[\s\S]*?restore_match\(\)",
            "tree gateway must dispatch cached slot 8 then restore matcher",
            failures)
    require(overlay,
            r"unsigned char readyfs_overlay_batch[\s\S]*?"
            r"open_batch_cached\(call->operation == RF_BATCH_EDITOR \? 1u : 0u\)[\s\S]*?"
            r"readyfs_batch_dispatch[\s\S]*?restore_match\(\)",
            "batch gateway must use its dedicated bank then restore matcher",
            failures)
    require(overlay,
            r"unsigned char readyfs_overlay_tape[\s\S]*?"
            r"open_batch_cached\(2u\)[\s\S]*?"
            r"readyfs_tape_dispatch[\s\S]*?restore_match\(\)",
            "tape gateway must use its dedicated batch-bank cache then restore matcher",
            failures)
    require(overlay, r"batch_offsets\[\][\s\S]*?RF_REU_BATCH_CACHE_OFF, RF_UI_CACHE_OFF, RF_REU_TAPE_CACHE_OFF, RF_PRESENT_CACHE_OFF, RF_COMMAND_HELP_CACHE_OFF",
            "shared batch cache indices must keep their documented bank offsets", failures)
    require(overlay, r"open_batch_cached[\s\S]*?readyfs_reu_batch_fetch\(batch_offsets\[slot\], _OVERLAY1_LOAD__[\s\S]*?batch_sizes\[slot\]",
            "shared opener must fetch the exact slot from the dedicated REU bank", failures)
    require(overlay, r"readyfs_overlay_present[\s\S]*?open_batch_cached\(help \? 4u : call->operation == RF_PRESENT_MEDIA \? 7u : 3u\)[\s\S]*?readyfs_command_help\(call\)[\s\S]*?readyfs_present\(call\)[\s\S]*?restore_match\(\); return result;",
            "presentation must restore the matcher before returning", failures)
    require(makefile,
            r"READYFS_OVERLAY_RECURSIVE_OBJS[\s\S]*?overlay11/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_recursive\.o",
            "recursive controller must be linked into overlay 11", failures)
    require(makefile,
            r"READYFS_OVERLAY_RECURSIVE_OBJS[\s\S]*?overlay11/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_recursive_name\.o",
            "recursive Ultimate-name translator must be linked into overlay 11",
            failures)
    require(makefile,
            r"READYFS_OVERLAY_UTILITY_OBJ[\s\S]*?overlay7/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_utility\.o",
            "utility controller must be linked into overlay 7", failures)
    require(makefile,
            r"READYFS_OVERLAY_TREE_OBJS[\s\S]*?overlay8/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_tree\.o",
            "tree controller must be linked into overlay 8", failures)
    require(makefile,
            r"READYFS_OVERLAY_CONTENT_OBJS[\s\S]*?overlay9/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_content\.o",
            "content controller must be linked into overlay 9", failures)
    require(makefile,
            r"READYFS_OVERLAY_BATCH_OBJ[\s\S]*?overlay10/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_batch\.o",
            "batch/editor controller must be linked into overlay 10", failures)
    require(makefile,
            r"READYFS_OVERLAY_TAPE_OBJS[\s\S]*?overlay12/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_tape\.o",
            "tape/core controller must be linked into overlay 12", failures)
    require(makefile,
            r"READYFS_OVERLAY_TAPE_OBJS[\s\S]*?overlay12/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_tape_spool\.o",
            "tape REU spool assembly must be linked into overlay 12", failures)
    require(makefile,
            r"READYFS_OVERLAY_ASM_OBJS[\s\S]*?resident/"
            r"\$\(READYFS_SRC_DIR\)/readyfs_softname\.o",
            "resident word comparison must be linked outside overlays", failures)
    require(makefile, r"-write \$\(READYFS_UTILITY_OVERLAY\) rfutil",
            "overlay D81 must contain the rfutil sidecar", failures)
    require(makefile, r"-write \$\(READYFS_TREE_OVERLAY\) rftree",
            "overlay D81 must contain the rftree sidecar", failures)
    require(makefile, r"-write \$\(READYFS_CONTENT_OVERLAY\) rfcontent",
            "overlay D81 must contain the rfcontent sidecar", failures)
    require(makefile, r"-write \$\(READYFS_BATCH_OVERLAY\) rfbatch",
            "overlay D81 must contain the rfbatch sidecar", failures)
    require(makefile, r"-write \$\(READYFS_RECURSIVE_OVERLAY\) rfrecur",
            "overlay D81 must contain the rfrecur sidecar", failures)
    require(makefile, r"-write \$\(READYFS_TAPE_OVERLAY\) rftape",
            "overlay D81 must contain the rftape sidecar", failures)
    require(linker_cfg,
            r"OVL7ADDR:[\s\S]*?readyfs-utility\.prg[\s\S]*?"
            r"OVERLAY7:\s+load\s*=\s*OVL7",
            "linker must emit utility sidecar and overlay-7 segment", failures)
    require(linker_cfg,
            r"OVL8ADDR:[\s\S]*?readyfs-tree\.prg[\s\S]*?"
            r"OVERLAY8:\s+load\s*=\s*OVL8",
            "linker must emit tree sidecar and overlay-8 segment", failures)
    require(linker_cfg,
            r"OVL9ADDR:[\s\S]*?readyfs-content\.prg[\s\S]*?"
            r"OVERLAY9:\s+load\s*=\s*OVL9",
            "linker must emit content sidecar and overlay-9 segment", failures)
    require(linker_cfg,
            r"OVL10ADDR:[\s\S]*?readyfs-batch\.prg[\s\S]*?"
            r"OVERLAY10:\s+load\s*=\s*OVL10",
            "linker must emit batch sidecar and overlay-10 segment", failures)
    require(linker_cfg,
            r"OVL11ADDR:[\s\S]*?readyfs-recursive\.prg[\s\S]*?"
            r"OVERLAY11:\s+load\s*=\s*OVL11",
            "linker must emit recursive sidecar and overlay-11 segment", failures)
    require(linker_cfg,
            r"OVL12ADDR:[\s\S]*?readyfs-tape\.prg[\s\S]*?"
            r"OVERLAY12:\s+load\s*=\s*OVL12",
            "linker must emit tape sidecar and overlay-12 segment", failures)
    require(recursive, r"ReadyFsRecursiveScratchFits[\s\S]*?"
            r"RF_PIPELINE_SCRATCH_BYTES",
            "recursive scratch must have a compile-time resident fit guard",
            failures)
    require(recursive, r"readyfs_reu_session_store\(RF_REU_RECURSIVE_OFF",
            "recursive controller must checkpoint state in session REU",
            failures)
    require(recursive, r"readyfs_reu_session_fetch\(RF_REU_RECURSIVE_OFF",
            "recursive controller must restore state from session REU",
            failures)
    require(recursive,
            r"readyfs_recursive_decode_name\(text\)[\s\S]*?"
            r"readyfs_recursive_strip_type\(text\)",
            "Ultimate recursive sources must retain access spelling while "
            "IEC destinations receive logical names", failures)
    for symbol in ("_readyfs_recursive_decode_name",
                   "_readyfs_recursive_strip_type"):
        require(recursive_name, rf"^\s*\.export\s+{symbol}\s*$",
                f"missing recursive-name export {symbol}", failures)
        require(recursive_name, rf"^{symbol}:\s*$",
                f"missing recursive-name entry {symbol}", failures)
    require(recursive_name, r'^\s*\.segment\s+"OVERLAY11"\s*$',
            "recursive-name translator must remain in overlay 11", failures)
    require(recursive,
            r"work->call\.journal\.write = readyfs_reu_session_store;"
            r"[\s\S]*?work->call\.journal\.read = "
            r"readyfs_reu_session_fetch;",
            "recursive RFJ1 init must supply C64 session callbacks", failures)
    require(overlay,
            r"unsigned char readyfs_overlay_recursive[\s\S]*?"
            r"RF_REU_OVERLAY_RECURSIVE_OFF[\s\S]*?"
            r"readyfs_recursive_dispatch[\s\S]*?restore_match\(\)",
            "resident recursive gateway must run cached overlay 11 safely",
            failures)
    require(drive_ui, r"readyfs_reu_session_fetch[\s\S]*?"
            r"record\[0\] != 0x52u[\s\S]*?record\[1\] != call->device",
            "profile lookup must validate marker and device", failures)
    require(resident,
            r"static void probe_iec_io\(ReadyFsDriveUiCall \*call\)"
            r"[\s\S]*?cbm_open",
            "IEC identity I/O must remain resident-owned", failures)
    require(resident,
            r"#define drive_command[\s\S]*?ReadyFsDriveUiCall"
            r"[\s\S]*?\(void \*\)&dest",
            "partition command call must use a resident stream workspace",
            failures)
    require(resident,
            r"native_ui\.output = source\.canonical;[\s\S]*?"
            r"native_ui\.followup = dest\.canonical;",
            "native translation must use two 256-byte stream workspaces",
            failures)
    if "native_ui.output = (char *)io_buf" in resident:
        failures.append("native translation regained the short transfer buffer")
    if re.search(r"\bcbm_", drive_ui):
        failures.append("drive UI sidecar must not perform KERNAL IEC I/O")
    if re.search(r"\breadyfs_uci_|\buci_", drive_ui):
        failures.append("drive UI sidecar must not perform UCI I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", recursive):
        failures.append("recursive controller must not perform device I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", backend):
        failures.append("backend/native planner sidecar must not perform device I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", utility):
        failures.append("utility sidecar must not perform device I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", tree):
        failures.append("tree sidecar must not perform device I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", content):
        failures.append("content sidecar must not perform device I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", batch):
        failures.append("batch/editor sidecar must not perform device I/O")
    if re.search(r"\bcbm_|\breadyfs_uci_|\buci_", tape):
        failures.append("tape/core sidecar must not perform device I/O")
    for symbol in ("_readyfs_tape_open_name_dispatch",
                   "_readyfs_tape_spool_dispatch"):
        require(tape_spool, rf"^\s*\.export\s+{symbol}\s*$",
                f"missing tape assembly export {symbol}", failures)
        require(tape_spool, rf"^{symbol}:\s*$",
                f"missing tape assembly entry {symbol}", failures)
    for name, value in (("TC_OPERATION", 0), ("TC_DATA", 5),
                        ("TC_LENGTH", 7), ("TC_SPOOL", 9),
                        ("TC_RESULT", 11), ("TC_TEXT", 15),
                        ("TC_OUTPUT", 19), ("TC_VALUE", 25),
                        ("TC_VALUE2", 26)):
        require(tape_spool, rf"^{name}\s*=\s*{value}$",
                f"tape assembly offset {name} must remain {value}", failures)
    require(tape_spool,
            r"fetch_eof:\s*[\s\S]*?sta\s+\(ptr1\),y[\s\S]*?"
            r"jmp\s+succeed",
            "tape replay EOF must return success unconditionally", failures)
    require(tape_spool, r"cmp\s+_readyfs_reu_console_bank_value",
            "spool capacity must protect the console and all three cache banks", failures)
    if "_readyfs_reu_batch_bank_value" in tape_spool:
        failures.append("spool may not use batch bank as its capacity ceiling")
    eof_block = tape_spool.split("fetch_eof:", 1)[-1].split("; A is", 1)[0]
    if re.search(r"\bbeq\s+succeed\b", eof_block):
        failures.append("tape replay EOF must not depend on LDY/INY flags")
    require(softname, r"^\s*\.export\s+_readyfs_same_word\s*$",
            "missing resident same-word export", failures)
    require(softname, r"^_readyfs_same_word:\s*$",
            "missing resident same-word entry", failures)
    for pattern in (r"cmp\s+#\$41", r"cmp\s+#\$5B"):
        require(softname, pattern, "resident word folding requires numeric ASCII bounds", failures)
    if re.search(r"cmp\s+#'A'|cmp\s+#'Z'", softname):
        failures.append("C64-target character literals must not define ASCII folding bounds")
    require(resident, r"#ifdef READYFS_OVERLAY_RUNTIME\s+extern unsigned char __fastcall__ readyfs_same_word[\s\S]*?#define same_word readyfs_same_word",
            "resident comparisons must call the resident assembly comparator without overlay DMA", failures)
    require(ui, r"unsigned char readyfs_ui_editor[\s\S]*?"
            r"readyfs_reu_history_get",
            "UI sidecar must retain editable REU history", failures)
    require(batch, r"RF_REU_BATCH_STATE_OFF[\s\S]*?state_store",
            "batch state must checkpoint outside the overlay window", failures)
    require(resident, r"RF_REU_BATCH_DATA_OFF[\s\S]*?stream_close"
            r"[\s\S]*?RF_BATCH_INIT",
            "resident must close the script before cooperative dispatch",
            failures)
    require(resident, r"if \(batch_active\)[\s\S]*?batch needs --yes",
            "batch commands must never wait at a confirmation prompt",
            failures)

    present = (BATCH.parent / "readyfs_present.c").read_text()
    media = (BATCH.parent / "readyfs_media.c").read_text()
    require((BATCH.parent / "readyfs_iec.c").read_text(), r"readyfs_iec_abi[\s\S]*?readyfs_media_reset\(\)",
            "startup must clear session-only mount hints", failures)
    require(makefile, r"overlay18/\$\(READYFS_SRC_DIR\)/readyfs_media\.o",
            "last-mount presentation must share native leaf sidecar18", failures)
    require(resident, r"media\(RF_MEDIA_FORGET, unit, 0\);[\s\S]*?uci_cmd\[1\] = 0x23u;[\s\S]*?uci_target_ok\(1u\)[\s\S]*?media\(RF_MEDIA_REMEMBER, unit, command_stream.canonical\)",
            "mount invalidation must precede shared command-buffer construction and remembering must follow target OK", failures)
    require(media, r"for \(unit = 8u; unit <= 30u; \+\+unit\)[\s\S]*?readyfs_iec_present\(unit\)[\s\S]*?t: sequential tape",
            "media discovery must use the local native IEC handshake", failures)
    if re.search(r"\bcbm_(?:open|write|read|close)\b|0x23u|0x24u|0x25u|socket|http", media):
        failures.append("mount presentation must not issue disk mutations or network requests")
    if re.search(r"unsigned char readyfs_reu_(?:overlay|session|batch|console)_(?:store|fetch)\s*\(", reu):
        failures.append("all public REU DMA must use the flat assembly boundary")
    require(asm, r"^_readyfs_reu_console_fetch:",
            "output history must use flat REU fetch", failures)
    require(overlay, r"readyfs_ui_editor\(",
            "resident gateway must dispatch the separate UI sidecar", failures)

    stream_policy = (BATCH.parent / "readyfs_stream.c").read_text()
    require(overlay, r"load_batch_cached\(5u\)[\s\S]*?readyfs_stream_abi\(\)[\s\S]*?restore_match\(\)[\s\S]*?RF_STREAM_ABI",
            "stream policy must be cached and ABI checked at startup", failures)
    require(overlay, r"readyfs_overlay_stream[\s\S]*?open_batch_cached\(5u\)[\s\S]*?readyfs_stream_prepare\(call\)[\s\S]*?restore_match\(\)",
            "stream policy gateway must restore matcher after dispatch", failures)
    require(resident, r"resolve_path\(text, stream->canonical\)[\s\S]*?stream_call.stream = stream;[\s\S]*?readyfs_overlay_stream\(&stream_call\)",
            "resident must resolve before loading stream policy", failures)
    require(stream_policy, r"stream->text = stream->canonical;[\s\S]*?stream->native_name = name;",
            "stream policy must return pointers into resident canonical data", failures)
    require(linker_cfg, r'OVL16ADDR:[\s\S]*?readyfs-stream.prg[\s\S]*?OVERLAY16: load = OVL16',
            "linker must emit independent stream policy sidecar16", failures)
    files = (BATCH.parent / "readyfs_files.c").read_text()
    files_plan = (BATCH.parent / "readyfs_files_plan.c").read_text()
    require(overlay, r"readyfs_overlay_files[\s\S]*?open_batch_cached\(5u\)[\s\S]*?readyfs_files_plan\(call\)[\s\S]*?restore_match\(\)[\s\S]*?open_batch_cached\(8u\)",
            "file request formatting and I/O must run in sequential leaves", failures)
    if re.search(r"\bcbm_|readyfs_overlay_|readyfs_uci_", files_plan):
        failures.append("file formatter must not issue I/O or nested overlay calls")
    require(resident, r"files_call.request = temp_text;[\s\S]*?files_call.reply = \(unsigned char \*\)temp_text \+ 128u;",
            "native requests/replies must use disjoint resident storage", failures)
    require(overlay, r"load_batch_cached\(8u\)[\s\S]*?readyfs_files_abi\(\)[\s\S]*?RF_FILES_ABI",
            "native file service must be cached and ABI checked", failures)
    require(overlay, r"readyfs_overlay_files[\s\S]*?open_batch_cached\(8u\)[\s\S]*?readyfs_files\(call\)[\s\S]*?restore_match\(\)",
            "native file gateway must restore matcher", failures)
    require(linker_cfg, r'OVL19ADDR:[\s\S]*?readyfs-files.prg[\s\S]*?OVERLAY19: load = OVL19',
            "linker must emit native files sidecar19", failures)
    require(files, r"cbm_k_talk[\s\S]*?cbm_k_tksa\(0x6Fu\)[\s\S]*?cbm_k_untlk",
            "native file status must preserve live channels with TALK", failures)
    if re.search(r"readyfs_overlay_|load_sidecar|readyfs_uci_", files):
        failures.append("native file leaf must not load overlays or use UCI")
    iec_plan = (BATCH.parent / "readyfs_iec_plan.c").read_text()
    iec_io = (BATCH.parent / "readyfs_iec.c").read_text()
    require(overlay, r"load_batch_cached\(6u\)[\s\S]*?readyfs_iec_plan_abi\(\)[\s\S]*?RF_IEC_PLAN_ABI",
            "IEC policy must be cached and ABI checked at startup", failures)
    require(overlay, r"readyfs_overlay_iec[\s\S]*?open_batch_cached\(6u\)[\s\S]*?readyfs_iec_plan\(call\)[\s\S]*?restore_match\(\)[\s\S]*?open_batch_cached\(7u\)[\s\S]*?readyfs_iec_execute\(call\)[\s\S]*?restore_match\(\)",
            "IEC policy and native I/O must run in sequential leaf overlays", failures)
    require(linker_cfg, r'OVL17ADDR:[\s\S]*?readyfs-iec.prg[\s\S]*?OVERLAY17: load = OVL17',
            "linker must emit IEC policy sidecar17", failures)
    require(overlay, r"load_batch_cached\(7u\)[\s\S]*?readyfs_iec_abi\(\)[\s\S]*?RF_IEC_ABI",
            "native media service must be cached and ABI checked at startup", failures)
    require(linker_cfg, r'OVL18ADDR:[\s\S]*?readyfs-native.prg[\s\S]*?OVERLAY18: load = OVL18',
            "linker must emit native media sidecar18", failures)
    require(media, r'0x90u = 0u;[\s\S]*?cbm_k_listen\(device\); cbm_k_second\(0x6Fu\)',
            "native discovery must clear ST and complete LISTEN/SECOND", failures)
    require(makefile, re.escape('--code-name OVERLAY$(1) --rodata-name OVERLAY$(1)R --bss-name OVERLAY$(1)B'),
            "sidecar code/constants/BSS must remain distinct assembler segments", failures)
    for slot in range(1,20):
        require(linker_cfg, re.escape(f'__OVERLAY{slot}_SIZE__: type = export, value = __OVL{slot}_LAST__ - __OVL{slot}_START__'),
                f"slot{slot} cache size must include code/constants/BSS", failures)
        for suffix in ('R','B'):
            require(linker_cfg, re.escape(f'OVERLAY{slot}{suffix}: load = OVL{slot}'),
                    f"slot{slot} must package separate {suffix} into its sidecar", failures)
    if re.search(r"\bcbm_|readyfs_overlay_|load_sidecar", iec_plan):
        failures.append("IEC policy must not issue I/O or load overlays")
    if re.search(r"readyfs_overlay_|load_sidecar|readyfs_uci_", iec_io):
        failures.append("native IEC leaf must not call overlays, load files or use UCI")
    if re.search(r"\bcbm_|readyfs_overlay_|load_sidecar", stream_policy):
        failures.append("stream policy must not invoke device I/O, nested overlays or runtime disk loading")

    if failures:
        for failure in failures:
            print(f"ReadyFS overlay DMA contract: FAIL: {failure}")
        return 1
    print("ReadyFS overlay DMA contract: PASS (flat 6-byte overlay/session/"
          "batch boundaries, explicit slots 1-19; REU-checkpointed recursive, "
          "backend/native, utility, tree, content, batch, UI, and tape controllers; "
          "resident-owned device I/O)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
