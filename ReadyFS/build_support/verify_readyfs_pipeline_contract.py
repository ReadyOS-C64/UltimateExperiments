#!/usr/bin/env python3
"""Guard ReadyFS's cooperative cross-overlay pipeline source contract."""

from __future__ import annotations

import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "src" / "apps" / "readyfs"


def main() -> int:
    overlay = (APP / "readyfs_overlay.c").read_text(encoding="utf-8")
    backend = (APP / "readyfs_backend.c").read_text(encoding="utf-8")
    resident = (APP / "readyfs.c").read_text(encoding="utf-8")
    plan = (APP / "readyfs_plan.c").read_text(encoding="utf-8")
    executor = (APP / "readyfs_exec.c").read_text(encoding="utf-8")
    driveui = (APP / "readyfs_driveui.c").read_text(encoding="utf-8")
    cmdpath = (APP / "readyfs_cmdpath.c").read_text(encoding="utf-8")
    recursive = (APP / "readyfs_recursive.c").read_text(encoding="utf-8")
    utility = (APP / "readyfs_utility.c").read_text(encoding="utf-8")
    utility_header = (APP / "readyfs_utility.h").read_text(encoding="utf-8")
    tree = (APP / "readyfs_tree.c").read_text(encoding="utf-8")
    ui = (APP / "readyfs_ui.c").read_text(encoding="utf-8")
    console = (APP / "readyfs_console.s").read_text(encoding="utf-8")
    content = (APP / "readyfs_content.c").read_text(encoding="utf-8")
    utility_test = (APP / "readyfs_utility_test.s").read_text(encoding="utf-8")
    content_format = (APP / "readyfs_content_format.s").read_text(
        encoding="utf-8")
    script_batch = (APP / "readyfs_batch.c").read_text(encoding="utf-8")
    tape = (APP / "readyfs_tape.c").read_text(encoding="utf-8")
    tape_spool = (APP / "readyfs_tape_spool.s").read_text(encoding="utf-8")
    commands = (APP / "readyfs_commands.c").read_text(encoding="utf-8")
    commands_header = (APP / "readyfs_commands.h").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    # Color controls decorate messages without changing the pipeline contract.
    # Normalize only adjacent severity macros, retaining every structural check.
    def uncolored(text):
        return re.sub(r'\bRF_(?:ERROR|SUMMARY|NORMAL)\s+(?=")', '', text)
    overlay, backend, resident, plan, executor, driveui, cmdpath, recursive, utility, tree, content, script_batch, tape = map(uncolored, (overlay, backend, resident, plan, executor, driveui, cmdpath, recursive, utility, tree, content, script_batch, tape))

    c64_executor = executor.split("#else", 1)[-1]
    failures: list[str] = []

    required = {
        "resident nested gateway": "readyfs_overlay_nested_from_backend",
        "backend restore":
            "fetch_cached(RF_REU_OVERLAY_BACKEND_OFF",
        "shared overlay fetch":
            "readyfs_reu_overlay_fetch(reu_offset, _OVERLAY1_LOAD__, size)",
        "resident scratch": "readyfs_pipeline_scratch",
        "backend build probe": "readyfs_backend_selftest",
    }
    combined = overlay + backend
    for label, token in required.items():
        if token not in combined:
            failures.append(f"missing {label}")

    preview_entry = resident.find(
        "static void cmd_mutation_preview(unsigned char argc) {")
    preview_operation = resident.find(
        "utility_ui.operation = RF_UTILITY_PREVIEW", preview_entry)
    preview_gateway = resident.find(
        "readyfs_overlay_utility(&utility_ui)", preview_operation)
    history_dispatch = resident.find("command == RF_COMMAND_HISTORY")
    history_operation = resident.find(
        "utility_ui.operation = RF_UTILITY_HISTORY", history_dispatch)
    history_gateway = resident.find(
        "readyfs_overlay_utility(&utility_ui)", history_operation)
    utility_preview = utility.find("static unsigned char preview(")
    utility_would = utility.find('cputs("would ")', utility_preview)
    utility_summary = utility.find(
        'cputs("; done w0 d0 m0\\r\\n")', utility_would)
    utility_history = utility.find("static unsigned char history(")
    utility_history_count = utility.find(
        "readyfs_reu_history_count()", utility_history)
    utility_history_get = utility.find(
        "readyfs_reu_history_get(age, call->buffer)", utility_history_count)
    if min(preview_entry, preview_operation, preview_gateway,
           history_dispatch, history_operation, history_gateway,
           utility_preview, utility_would, utility_summary, utility_history,
           utility_history_count, utility_history_get) < 0 or not (
               preview_entry < preview_operation < preview_gateway and
               history_dispatch < history_operation < history_gateway and
               utility_preview < utility_would < utility_summary <
               utility_history < utility_history_count < utility_history_get):
        failures.append(
            "resident WhatIf/history commands must dispatch to utility slot 7; "
            "that sidecar must retain exact would/plan summaries and read the "
            "REU history ring oldest-to-newest")
    resident_preview_body = resident[preview_entry:preview_gateway]
    if 'cputs("would ")' in resident_preview_body or \
       'cputs("plan w")' in resident_preview_body:
        failures.append("mutation preview logic must remain outside resident RAM")
    soft_cd_id = utility_header.find("#define RF_UTILITY_SOFT_CD 7u")
    soft_cd_controller = utility.find("static unsigned char soft_cd(")
    soft_cd_dispatch = utility.find(
        "RF_UTILITY_SOFT_CD) return soft_cd(call)", soft_cd_controller)
    soft_parent = resident.find("static unsigned char softiec_enter_parent(")
    soft_read_close = resident.find(
        'uci_call(5u, 0x14u, "\\2")', soft_parent)
    soft_worker_barrier = resident.find(
        'uci_call(5u, 0x01u, 0)', soft_read_close)
    soft_root = resident.find(
        'iec_command_ok(stream->device, "cd:/")', soft_parent)
    soft_operation = resident.find(
        "utility_ui.operation = RF_UTILITY_SOFT_CD", soft_root)
    soft_gateway = resident.find(
        "readyfs_overlay_utility(&utility_ui)", soft_operation)
    soft_status = resident.find(
        "iec_command_ok(stream->device, temp_text)", soft_gateway)
    if min(soft_cd_id, soft_cd_controller, soft_cd_dispatch, soft_parent,
           soft_read_close, soft_worker_barrier,
           soft_root, soft_operation, soft_gateway, soft_status) < 0 or not (
               soft_cd_controller < soft_cd_dispatch and
               soft_parent < soft_read_close < soft_worker_barrier <
               soft_root < soft_operation < soft_gateway < soft_status):
        failures.append(
            "SoftwareIEC parent entry must complete read LFN2, serialize the "
            "firmware worker through the ReadyIRC-derived UCI transport, reset "
            "at the virtual root, ask utility slot 7 for bounded component CD "
            "commands, and require resident status after every step")
    iec_ok = resident.find("static unsigned char iec_command_ok(")
    iec_ok_end = resident.find("#ifdef READYFS_OVERLAY_RUNTIME", iec_ok)
    iec_ok_body = resident[iec_ok:iec_ok_end]
    if iec_ok < 0 or iec_ok_end < 0 or \
       iec_ok_body.count("iec_command_status(device, command)") != 1 or \
       'iec_command_status(device, "")' in iec_ok_body:
        failures.append(
            "each IEC command must use one status-bearing command-channel "
            "transaction; a second drain OPEN reintroduces the 64 MHz stall")
    if "cbm_" in utility or "readyfs_uci_" in utility:
        failures.append(
            "utility sidecar must generate SoftwareIEC CD commands but own "
            "no IEC or UCI device I/O")
    soft_find = resident.find("static unsigned char softiec_find_type(")
    soft_find_end = resident.find(
        "static unsigned char stream_find_type(", soft_find)
    soft_find_body = resident[soft_find:soft_find_end]
    soft_probe_close = soft_find_body.find(
        '(void)uci_call(5u, 0x14u, "\\6");')
    soft_probe_status = soft_find_body.find(
        'iec_command_status(stream->device, "")')
    soft_probe_accept = soft_find_body.find("if (io_buf[0] == '0'")
    if min(soft_find, soft_find_end) < 0 or \
       "for (type = CBM_T_SEQ; type <= CBM_T_USR; ++type)" not in soft_find_body or \
       "iec_open_name(temp_text, stream->native_name, type, 'r')" not in soft_find_body or \
       soft_find_body.count("cbm_close(6u);") != 1 or \
       min(soft_probe_close, soft_probe_status, soft_probe_accept) < 0 or \
       not soft_probe_close < soft_probe_status < soft_probe_accept or \
       "return iec_find_type(" in soft_find_body or \
       "&& io_buf[1] == '0'" not in soft_find_body or \
       "if (io_buf[0] != '6' || io_buf[1] != '2')" not in soft_find_body or \
       "iec_command_status(stream->device, \"\") < 2" not in soft_find_body or \
       "return RF_LOOKUP_ERROR;" not in soft_find_body:
        failures.append(
            "SoftwareIEC file lookup must avoid its truncated BASIC directory "
            "stream, explicitly probe only non-creating SEQ/PRG/USR types "
            "with consumed DOS status, never probe REL with OPEN_ALWAYS, and "
            "complete exact LFN6 through target-5 CLOSE before reading status")
    command_operation = resident.find(
        "tree_ui.operation = RF_TREE_CALL_COMMAND_ID")
    command_gateway = resident.find(
        "readyfs_overlay_tree(&tree_ui)", command_operation)
    command_table = commands.find(
        "static const unsigned char command_names[]")
    capability_command = commands.find("RF_COMMAND_CAPABILITIES", command_table)
    crc_command = commands.find("RF_COMMAND_CRC32", capability_command)
    capability_renderer = utility.find(
        "static unsigned char capabilities(")
    capability_dispatch = utility.find(
        "RF_UTILITY_CAPABILITIES) return capabilities(call)",
        capability_renderer)
    tree_command_dispatch = ui.find(
        "call->result = readyfs_command_id(call->name)")
    tree_command_object = makefile.find(
        "overlay13/$(READYFS_SRC_DIR)/readyfs_commands.o")
    if min(command_operation, command_gateway, command_table,
           capability_command, crc_command, capability_renderer,
           capability_dispatch, tree_command_dispatch,
           tree_command_object) < 0 or not (
               command_operation < command_gateway and
               command_table < capability_command < crc_command and
               capability_renderer < capability_dispatch):
        failures.append(
            "the shared command-name decoder must be linked into UI slot 13 "
            "behind the resident numeric-ID gateway; capabilities rendering "
            "must remain in utility slot 7")
    option_type = resident.find("static unsigned char option_file_type(")
    option_type_end = resident.find("static void iec_open_name(", option_type)
    option_type_body = resident[option_type:option_type_end]
    if "tree_ui.operation = RF_TREE_CALL_COMMAND_ID" not in option_type_body or \
       "tree_ui.result & 0x80u" not in option_type_body or \
       "#define RF_COMMAND_FILE_PRG 0x91u" not in commands_header or \
       "#define RF_COMMAND_FILE_USR 0x92u" not in commands_header or \
       "#define RF_COMMAND_FILE_SEQ 0x90u" not in commands_header or \
       "RF_COMMAND_FILE_PRG, 'p','r','g',0" not in commands or \
       "RF_COMMAND_FILE_USR, 'u','s','r',0" not in commands or \
       "RF_COMMAND_FILE_SEQ, 's','e','q',0" not in commands:
        failures.append(
            "resident --type decoding must stay behind the slot-8 command "
            "gateway and preserve the high-bit/cc65 file-type ABI")
    if 'same_word(args[0],' in resident:
        failures.append("command-name decoding must not return to resident RAM")
    status_command = resident.find("command == RF_COMMAND_STATUS")
    status_operation = resident.find(
        "tree_ui.operation = RF_TREE_CALL_STATUS")
    status_gateway = resident.find(
        "readyfs_overlay_tree(&tree_ui)", status_operation)
    status_renderer = tree.find("static unsigned char render_status(")
    status_last = tree.find('cputs("\\r\\nlast result: ")',
                            status_renderer)
    if min(status_command, status_operation, status_gateway,
           status_renderer, status_last) < 0 or not (
               status_operation < status_gateway and
               status_renderer < status_last):
        failures.append(
            "status must pass resident state through the slot-8 gateway and "
            "label its bounded typed previous result as last result")
    status_preserve = resident.find(
        "command != RF_COMMAND_STATUS && command != RF_COMMAND_UNKNOWN")
    status_reset = resident.find("last_result = RF_RESULT_OK;", status_preserve)
    if min(status_preserve, status_reset) < 0 or not status_preserve < status_reset:
        failures.append(
            "dispatch must preserve the prior typed result for STATUS while "
            "resetting other recognized commands to OK")
    tree_init = resident.find("tree_ui.operation = RF_TREE_CALL_INIT")
    tree_next = resident.find("tree_ui.operation = RF_TREE_CALL_NEXT", tree_init)
    tree_uci = resident.find(
        "dir_ultimate_run(temp_text, tree_ultimate_block)", tree_next)
    tree_report = resident.find(
        "tree_ui.operation = RF_TREE_CALL_REPORT", tree_uci)
    tree_state = tree.find("RF_REU_TREE_STATE_OFF")
    tree_queue = tree.find("RF_REU_TREE_QUEUE_OFF", tree_state)
    tree_dispatch = tree.find("readyfs_tree_dispatch")
    if min(tree_init, tree_next, tree_uci, tree_report, tree_state,
           tree_queue, tree_dispatch) < 0 or not (
               tree_init < tree_next < tree_uci < tree_report and
               tree_state < tree_queue < tree_dispatch):
        failures.append(
            "cooperative tree command must INIT/NEXT, yield Ultimate I/O to "
            "resident, REPORT, and checkpoint its bounded queue in REU")
    if "readyfs_uci_" in tree or "cbm_" in tree:
        failures.append("cooperative tree sidecar must not own device I/O")
    content_begin = resident.find("static unsigned char content_begin(")
    content_init = resident.find(
        "RF_UTILITY_CONTENT_INIT", content_begin)
    content_gateway = resident.find(
        "readyfs_overlay_utility(&utility_ui)", content_init)
    content_command = resident.find("static void cmd_type(", content_gateway)
    stream_open_begin = resident.find("static unsigned char stream_open_read(")
    stream_open_end = resident.find(
        "static unsigned char stream_open_write(", stream_open_begin)
    stream_open_body = resident[stream_open_begin:stream_open_end]
    if stream_open_begin < 0 or stream_open_end < 0 or \
       "leaf = udos_enter_parent(stream, target);" not in stream_open_body or \
       "udos_find_leaf" in stream_open_body:
        failures.append(
            "Ultimate read-open must enter the parent and let OPEN resolve "
            "the raw leaf; READ_DIR is not an existence oracle for hidden "
            "dot-prefixed ownership markers")
    content_open = resident.find(
        "stream_open_read(&command_stream, 1u, 2u)", content_command)
    content_read = resident.find(
        "stream_read(&command_stream, io_buf, sizeof(io_buf))", content_open)
    content_add = resident.find(
        "utility_ui.operation = RF_UTILITY_CONTENT_ADD", content_read)
    content_report = resident.find(
        "utility_ui.operation = RF_UTILITY_CONTENT_REPORT", content_add)
    controller_init = content.find("static unsigned char initialize(")
    controller_add = content.find("static unsigned char add(", controller_init)
    controller_ring = content.find("RF_CONTENT_RING_BYTES", controller_add)
    controller_report = content.find("static unsigned char report(",
                                     controller_ring)
    controller_truncated = content.find('cputs("\\r\\ntail truncated")',
                                        controller_report)
    controller_crc_byte = content.find("static void crc32_byte(")
    controller_crc_mode = content.find("RF_CONTENT_CRC32", controller_crc_byte)
    controller_crc_report = content.find('cputs("crc32 $")',
                                         controller_report)
    resident_crc_range = resident.find("command <= RF_COMMAND_TEST")
    controller_test = utility_test.find("_readyfs_utility_test:")
    controller_test_report = utility_test.find('msg_pass:')
    if min(content_begin, content_init, content_gateway, content_command,
           content_open, content_read, content_add, content_report,
           controller_init, controller_add, controller_ring,
           controller_report, controller_truncated, controller_crc_byte,
           controller_crc_mode, controller_crc_report,
           resident_crc_range, controller_test,
           controller_test_report) < 0 or not (
           content_begin < content_init < content_gateway < content_command <
           content_open < content_read < content_add < content_report and
           controller_init < controller_add < controller_ring <
           controller_report < controller_truncated and
           controller_crc_byte < controller_crc_mode and
           controller_report < controller_crc_report and
           content_command < resident_crc_range):
        failures.append(
            "content views must INIT the slot-9 controller, yield stream I/O "
            "to resident, ADD chunks, REPORT, and expose bounded tail-ring "
            "truncation and CRC32; slot 7 must expose the versioned RFT1 "
            "built-in report")
    for token in ("rft1 suites", "rft1 core pass 4/4", "count_255",
                  "count_256", "crc_text"):
        if token not in utility_test:
            failures.append(f"slot-7 RFT1 diagnostic missing {token}")
    if "readyfs_uci_" in content or "cbm_" in content:
        failures.append("bounded content sidecar must not own device I/O")
    format_command = commands.find("RF_COMMAND_MOUNT, 'f','o','r','m','a','t'")
    format_entry = resident.find("static void cmd_mount")
    format_dry = resident.find("if (has_dry_run(argc))", format_entry)
    format_route = resident.find("RF_CMDPATH_FORMAT", format_dry)
    format_gateway = overlay.find(
        "call->operation == RF_UTILITY_FORMAT_MEDIA")
    format_content = content.find(
        "call->operation == RF_UTILITY_FORMAT_MEDIA")
    format_io = resident.find("probe_iec_io(&drive_command)",
                              resident.find("drive_partition_command"))
    if min(format_command, format_entry, format_dry, format_route,
           format_gateway, format_content, format_io) < 0 or not (
           format_entry < format_dry < format_route):
        failures.append(
            "format must dry-run first, route through the content validator, "
            "then yield command-channel I/O to resident")
    for token in ('"--label"', '"--id"', '"--disposable"', '"--yes"',
                  "cmp #8", "cmp #6", "cmp #31", "cmp #22",
                  "_readyfs_reu_session_fetch"):
        if token not in content_format:
            failures.append(f"format safety validator missing {token}")
    if "cbm_" in content_format or "readyfs_uci_" in content_format:
        failures.append("format validator must not own device I/O")
    if "$(READYFS_OVERLAY_OBJ_DIR)/overlay9/$(READYFS_SRC_DIR)/readyfs_content_format.o" not in makefile:
        failures.append("format validator must be linked into slot 9")
    run_command = commands.find("RF_COMMAND_RUN, 'r','u','n'")
    run_entry = resident.find("static void cmd_run(unsigned char argc)")
    run_stage = resident.find("RF_REU_BATCH_DATA_OFF", run_entry)
    run_close = resident.find("stream_close(&command_stream)", run_stage)
    run_init = resident.find("batch_ui.operation = RF_BATCH_INIT", run_close)
    run_next = resident.find("batch_ui.operation = RF_BATCH_NEXT", run_init)
    run_dispatch = resident.find("keep_running = dispatch(argc)", run_next)
    run_ack = resident.find("batch_ui.operation = RF_BATCH_ACK", run_dispatch)
    run_report = resident.find("batch_ui.operation = RF_BATCH_REPORT", run_ack)
    batch_next = script_batch.find("static unsigned char evaluate(")
    batch_onerror = script_batch.find('same_word(call->args[0], "onerror")',
                                      batch_next)
    batch_expect = script_batch.find('same_word(call->args[0], "expect")',
                                     batch_onerror)
    batch_nested = script_batch.find('same_word(call->args[0], "run")',
                                     batch_expect)
    batch_checkpoint = script_batch.find("RF_REU_BATCH_STATE_OFF")
    editor_dispatch = overlay.find("readyfs_ui_editor")
    resident_editor = resident.find("batch_ui.operation = RF_BATCH_EDITOR")
    if min(run_command, run_entry, run_stage, run_close, run_init, run_next,
           run_dispatch, run_ack, run_report, batch_next, batch_onerror,
           batch_expect, batch_nested, batch_checkpoint, editor_dispatch,
           resident_editor) < 0 or not (
           run_entry < run_stage < run_close < run_init < run_next <
           run_dispatch < run_ack < run_report and
           batch_next < batch_onerror < batch_expect < batch_nested):
        failures.append(
            "run must stage and close its stream before cooperative INIT/NEXT/"
            "dispatch/ACK/REPORT; the batch sidecar must checkpoint state and "
            "own onerror, expect rc, and nested-run rejection; the UI gateway must own the editor")
    if "batch needs --yes" not in resident or "if (batch_active)" not in resident:
        failures.append("batch mode must reject rather than wait at prompts")
    if "readyfs_uci_" in script_batch or "cbm_" in script_batch:
        failures.append("batch/editor sidecar must not own device I/O")
    tree_command = resident.find("static void cmd_tree(")
    tree_soft_gate = resident.find(
        "dest.path.endpoint == RF_EP_SOFTIEC", tree_command)
    tree_soft_buffer = resident.find(
        "dest.device == 1u ? source.canonical : temp_text", tree_soft_gate)
    tree_soft_bus = resident.find(
        "source.device = readyfs_uci_softiec_bus()", tree_soft_buffer)
    tree_soft_enter = resident.find(
        "softiec_enter_parent(&source)", tree_soft_bus)
    tree_soft_leaf_cd = resident.find(
        '"cd:", source.native_name', tree_soft_enter)
    tree_soft_prefix = resident.find(
        "temp_text[0] = '$'; temp_text[1] = 0", tree_soft_leaf_cd)
    tree_soft_iec = resident.find(
        "dir_iec(source.device, temp_text, 1u)",
        tree_soft_prefix)
    if min(tree_soft_gate, tree_soft_buffer, tree_soft_bus,
           tree_soft_enter, tree_soft_leaf_cd, tree_soft_prefix,
           tree_soft_iec) < 0 or not (
           tree_soft_gate < tree_soft_buffer <
           tree_soft_bus < tree_soft_enter < tree_soft_leaf_cd < tree_soft_prefix <
           tree_soft_iec):
        failures.append(
            "SoftIEC tree must enter each canonical directory component-wise, "
            "bind its runtime IEC bus, issue a plain native directory request, "
            "and yield resident IEC "
            "enumeration; probe softiec owns explicit capability reporting")
    tree_native_gate = resident.find(
        "dest.path.endpoint == RF_EP_IEC", tree_command)
    tree_native_dispatch = resident.find(
        "if (dest.device == 2u)", tree_native_gate)
    tree_native_directory = resident.find(
        "drive_partition_command(temp_text, 0, 0u,", tree_native_dispatch)
    if min(tree_native_gate, tree_native_dispatch, tree_native_directory) < 0 or not (
            tree_native_gate < tree_native_dispatch < tree_native_directory):
        failures.append(
            "IEC tree must route every native directory through automatic "
            "device preparation and yield enumeration to the common controller")
    find_filter = resident.find("static unsigned char tree_filter_accept(")
    find_match = resident.find(
        "readyfs_overlay_match(RF_MATCH_ULTIMATE_FILTER", find_filter)
    find_stem = resident.find(
        "tree_filter_accept(temp_text, kind)", find_match)
    find_include = resident.find(
        'tree_include = option_value(argc, "--include")', find_stem)
    find_exclude = resident.find(
        'tree_exclude = option_value(argc, "--exclude")', find_include)
    find_dispatch = resident.find("command == RF_COMMAND_FIND")
    find_gateway = resident.find("cmd_tree(argc, 1u)", find_dispatch)
    find_report = tree.find('"find done n"')
    if min(find_filter, find_include, find_exclude, find_match, find_stem,
           find_dispatch, find_gateway, find_report) < 0 or not (
            find_filter < find_match < find_stem < find_include < find_exclude and
            find_dispatch < find_gateway):
        failures.append(
            "find must apply include/exclude matching to the complete relative "
            "stem, dispatch through the cooperative tree controller, and "
            "render an explicit selected/files/directories summary")
    alias_storage = resident.find("alias_backup_storage[sizeof(ReadyFsAlias) + 2u]")
    alias_view = resident.find("#define alias_slot", alias_storage)
    backup_view = resident.find("#define backup", alias_view)
    recursive_outer = resident.find(
        "static ReadyFsRecursiveCall recursive_call;", backup_view)
    stale_recursive_alias = resident.find(
        "#define recursive_call (*(ReadyFsRecursiveCall")
    if min(alias_storage, alias_view, backup_view, recursive_outer) < 0 or not (
            alias_storage < alias_view < backup_view < recursive_outer) or \
            stale_recursive_alias >= 0:
        failures.append(
            "resident alias/backup lifetime union requires a distinct "
            "recursive outer call; recursive state must not alias backup")

    append = backend.find("RF_JOURNAL_CALL_APPEND")
    ack = backend.find("RF_EXEC_CALL_ACK")
    finish = backend.find("RF_JOURNAL_CALL_FINISH")
    read = backend.find("RF_JOURNAL_CALL_READ")
    if min(append, ack, finish, read) < 0 or not append < ack < finish < read:
        failures.append("pipeline must journal before ACK, then finish and replay")
    if "readyfs_backend_abi() == RF_BACKEND_ABI" not in overlay or \
       "readyfs_backend_selftest()" not in overlay:
        failures.append("BACKEND READY must depend on ABI and build probe")
    if "#ifdef __CC65__" not in plan or \
       "one-pointer call" not in plan:
        failures.append("C64 planner must use its one-pointer dispatcher")
    if "static ReadyFsPlanCall exec_plan_call;" not in c64_executor or \
       "readyfs_plan_dispatch(&exec_plan_call)" not in c64_executor:
        failures.append("C64 executor must read plans through one-pointer call")
    if "readyfs_plan_read(exec->plan" in c64_executor:
        failures.append("C64 executor regained nested multi-argument plan read")
    if "readyfs_action_selftest()" not in overlay:
        failures.append("plan readiness must run the five-action C64 self-test")
    recursive_next = recursive.find("static unsigned char next_action")
    recursive_backend = recursive.find(
        "RF_BACKEND_CALL_BUILD", recursive_next)
    recursive_ack = recursive.find("static unsigned char acknowledge")
    recursive_journal = recursive.find(
        "RF_JOURNAL_CALL_APPEND", recursive_ack)
    recursive_exec_ack = recursive.find("RF_EXEC_CALL_ACK", recursive_journal)
    recursive_checkpoint = recursive.find(
        "readyfs_reu_session_store(RF_REU_RECURSIVE_OFF")
    recursive_restore = recursive.find(
        "readyfs_reu_session_fetch(RF_REU_RECURSIVE_OFF")
    if min(recursive_next, recursive_backend, recursive_ack,
           recursive_journal, recursive_exec_ack, recursive_checkpoint,
           recursive_restore) < 0 or not (
           recursive_next < recursive_backend < recursive_ack <
           recursive_journal < recursive_exec_ack):
        failures.append(
            "recursive controller must restore/checkpoint REU state, build "
            "each request, then journal before executor ACK")
    if "operation | RF_NESTED_RESIDENT" not in recursive:
        failures.append(
            "recursive nested calls must restore overlay 11 before returning")
    if "readyfs_overlay_recursive" not in overlay:
        failures.append("resident recursive overlay gateway is missing")
    if "cbm_" in recursive or "readyfs_io_" in recursive or \
       "readyfs_uci_" in recursive:
        failures.append("recursive overlay must yield all device I/O to resident")
    if "RF_RECURSIVE_CALL_IMPORT_TREE" not in recursive or \
       "RF_REU_TREE_QUEUE_OFF" not in recursive or \
       "readyfs_reu_overlay_fetch" not in recursive:
        failures.append(
            "recursive overlay must import the resident Ultimate tree ledger")
    if "RF_TREE_RECORD_SELECTED" not in tree or \
       "RF_TREE_RECORD_FILE" not in tree or \
       "call->queue_used = tree_state.used" not in tree:
        failures.append(
            "tree ledger must retain selected file and directory records")
    resident_batch = resident.rfind("static unsigned char recursive_batch(")
    roots_store = resident.find(
        "readyfs_reu_session_store(RF_REU_RECURSIVE_ROOTS_OFF")
    roots_fetch = resident.find(
        "readyfs_reu_session_fetch(RF_REU_RECURSIVE_ROOTS_OFF",
        roots_store)
    roots_second_store = resident.find(
        "return readyfs_reu_session_store(", roots_store)
    roots_second_fetch = resident.find(
        "return readyfs_reu_session_fetch(", roots_fetch)
    batch_soft_source = resident.find(
        "source.path.endpoint - RF_EP_IEC", resident_batch)
    batch_tree_walk = resident.find("cmd_tree(argc, 2u)", batch_soft_source)
    batch_tree_import = resident.find(
        "RF_RECURSIVE_CALL_IMPORT_TREE", batch_tree_walk)
    batch_enumerate = resident.find("cbm_opendir(7u", resident_batch)
    batch_add = resident.find(
        "native_plan.phase = RF_NATIVEPLAN_ADD", batch_enumerate)
    batch_report = resident.find(
        "native_plan.phase = RF_NATIVEPLAN_REPORT", batch_add)
    batch_preview = resident.find(
        "if (native_plan.dry_run)", batch_report)
    batch_delete_confirm = resident.find(
        "mode == RF_EXEC_MODE_DELETE", batch_preview)
    batch_force = resident.find('option_present(argc, "--force")',
                                batch_delete_confirm)
    batch_ask = resident.find('ask_yes(args[0])', batch_force)
    batch_start = resident.find("RF_RECURSIVE_CALL_START", batch_ask)
    batch_next = resident.find("RF_RECURSIVE_CALL_NEXT", batch_start)
    batch_io = resident.find("recursive_execute(action, force)", batch_next)
    batch_ack = resident.find("RF_RECURSIVE_CALL_ACK", batch_io)
    copy_route = resident.find(
        "recursive_batch(argc, move_source ? RF_EXEC_MODE_MOVE")
    delete_route = resident.find(
        "recursive_batch(argc, RF_EXEC_MODE_DELETE)", copy_route)
    if min(resident_batch, roots_store, roots_fetch, roots_second_store,
           roots_second_fetch, batch_soft_source, batch_tree_walk,
           batch_tree_import, batch_enumerate,
           batch_add, batch_report, batch_preview, batch_delete_confirm,
           batch_force,
           batch_ask, batch_start, batch_next, batch_io, batch_ack,
           copy_route, delete_route) < 0 or not (
           roots_store < roots_second_store < roots_fetch <
           roots_second_fetch < resident_batch < batch_soft_source <
           batch_tree_walk < batch_tree_import < batch_enumerate <
           batch_add < batch_report < batch_preview <
           batch_delete_confirm < batch_force <
           batch_ask < batch_start < batch_next < batch_io < batch_ack and
           copy_route < delete_route < resident_batch):
        failures.append(
            "resident recursive batch must checkpoint roots, admit and "
            "import native IEC/Ultimate/SoftIEC trees, enumerate/"
            "sidecar-add/report, "
            "dry-run/confirm delete, start, yield NEXT, perform device I/O, "
            "ACK, and route copy/move/delete")
    option_parser = resident.find("static unsigned char option_present(")
    option_force_alias = resident.find('same_word(option, "--force")',
                                       option_parser)
    option_yes_alias = resident.find('same_word(args[i], "--yes")',
                                     option_force_alias)
    if min(option_parser, option_force_alias, option_yes_alias) < 0 or not (
            option_parser < option_force_alias < option_yes_alias):
        failures.append("--yes must remain the central alias for --force")
    nested_backend = overlay.find("RF_NESTED_BACKEND")
    nested_backend_dispatch = overlay.find(
        "readyfs_backend_dispatch((ReadyFsBackendCall *)nested->call)",
        nested_backend)
    return_drive = overlay.find("RF_NESTED_RETURN_DRIVE", nested_backend_dispatch)
    restore_drive = overlay.find("RF_REU_OVERLAY_DRIVE_OFF", return_drive)
    if min(nested_backend, nested_backend_dispatch, return_drive,
           restore_drive) < 0 or not (
           nested_backend < nested_backend_dispatch < return_drive <
           restore_drive):
        failures.append(
            "nested backend must dispatch, then restore the drive sidecar")

    execute = backend.find("call->operation == RF_BACKEND_CALL_BEGIN")
    action_first = backend.find(
        "call->action >= RF_EXEC_ACTION_MKDIR", execute)
    action_last = backend.find(
        "call->action <= RF_EXEC_ACTION_RMDIR", execute)
    source_guard = backend.find("action_needs_source(call->action)", execute)
    destination_guard = backend.find(
        "action_needs_destination(call->action)", execute)
    root_helper = backend.find("static unsigned char execute_root_ok")
    root_parse = backend.find("readyfs_path_parse(root, &execute_path)",
                              root_helper)
    action_selected = backend.find(
        "state->call.action.action = call->action", execute)
    journal_one = backend.find("RF_JOURNAL_CALL_ONE", execute)
    journal_action = backend.find(
        "state->call.one.action = call->action", journal_one)
    journal_kind = backend.find(
        "state->call.one.kind = call->state->record.kind", journal_one)
    journal_nested = backend.find(
        "pipeline_nested(state, RF_NESTED_JOURNAL", execute)
    action_ack = backend.find("RF_ACTION_CALL_ACK", journal_nested)
    execute_end = backend.find("#endif", execute)
    if min(execute, action_first, action_last, source_guard,
           destination_guard, root_helper, root_parse, action_selected,
           journal_one, journal_action, journal_kind, journal_nested,
           action_ack, execute_end) < 0 or not (
               root_helper < root_parse < execute < action_first <
               action_last < source_guard < destination_guard <
               action_selected < journal_one < journal_action <
               journal_kind < journal_nested < action_ack < execute_end):
        failures.append(
            "C64 backend must validate exact action range and roots, journal "
            "state-derived kind, then ACK")
    if "readyfs_io_copy" in backend or "cbm_" in backend:
        failures.append("backend overlay must never own KERNAL/device I/O")
    resident_begin = resident.find("static unsigned char action_begin")
    resident_begin_op = resident.find(
        "backend_call.operation = RF_BACKEND_CALL_BEGIN", resident_begin)
    resident_begin_gateway = resident.find(
        "readyfs_overlay_backend_call(&backend_call)", resident_begin_op)
    resident_complete = resident.find("static unsigned char action_complete")
    resident_complete_op = resident.find(
        "backend_call.operation = RF_BACKEND_CALL_COMPLETE",
        resident_complete)
    resident_complete_gateway = resident.find(
        "readyfs_overlay_backend_call(&backend_call)", resident_complete_op)
    mkdir_identity = resident.find(
        "action_begin(RF_EXEC_ACTION_MKDIR, command_stream.canonical,")
    copy_command = resident.find("static void cmd_copy_move")
    copy_begin = resident.find("action_begin(move_source ?", copy_command)
    copy_resolve = resident.find("!path_prepare(args[1], &source)", copy_command)
    if copy_resolve < 0 or copy_resolve > copy_begin or "source.canonical, dest.canonical" not in resident[copy_begin:copy_begin+220]:
        failures.append("single-file copy admission must use both resolved canonical paths")
    for action in ("DELETE_FILE", "RMDIR"):
        if "action_begin(RF_EXEC_ACTION_"+action+", command_stream.canonical, 0)" not in resident:
            failures.append("single-path mutations must admit canonical paths: "+action)

    copy_body = resident[copy_command:resident.find("static void cmd_delete",copy_command)]
    if "copy_call.source = source.canonical" not in copy_body or "copy_call.destination = dest.canonical" not in copy_body or "path_prepare(source.canonical, &command_stream)" not in copy_body:
        failures.append("single-file I/O must retain canonical identities after action BEGIN; alias scratch overlaps action state")
    prepare = resident[resident.find("static unsigned char path_prepare(const char *text,"):]
    if "memset(stream, 0, sizeof(*stream))" in prepare:
        failures.append("stream preparation must preserve in-place canonical text")
    copy_begin_failure = resident.find('cputs("op failed\\r\\n")', copy_begin)
    resident_copy = resident.find(
        "readyfs_io_copy_call(&copy_call)", copy_begin_failure)
    copy_complete = resident.find("action_complete(copy_result)", resident_copy)
    if "static ReadyFsIoCopyCall copy_call;" not in resident or \
       min(resident_begin, resident_begin_op, resident_begin_gateway,
           resident_complete, resident_complete_op,
           resident_complete_gateway, mkdir_identity, copy_command, copy_begin,
           copy_begin_failure,
           resident_copy, copy_complete) < 0 or not (
           resident_begin < resident_begin_op < resident_begin_gateway <
           resident_complete < resident_complete_op <
           resident_complete_gateway < copy_command < copy_begin <
           copy_begin_failure < resident_copy < copy_complete):
        failures.append(
            "resident must use an explicit BEGIN failure block, run static "
            "one-pointer I/O, then COMPLETE")
    copy_io = resident.find("unsigned char readyfs_io_copy_call(")
    copy_source_preflight = resident.find(
        "stream_open_read(&source, 1u, 2u)", copy_io)
    copy_tape_preflight_gate = resident.rfind(
        "if (source.path.endpoint != RF_EP_TAPE)", copy_io,
        copy_source_preflight)
    copy_source_close = resident.find(
        "stream_close(&source)", copy_source_preflight)
    copy_destination_probe = resident.find(
        "existed = stream_exists(&dest)", copy_source_close)
    copy_source_actual = resident.find(
        "stream_open_read(&source, 1u, 2u)", copy_destination_probe)
    copy_destination_open = resident.find(
        "stream_open_write(output", copy_source_actual)
    copy_stage_signature = resident.find(
        "signature_file(&temp, &right_signature)", copy_destination_open)
    copy_commit = resident.find(
        "rename_stream(&temp, &dest)", copy_stage_signature)
    if min(copy_io, copy_source_preflight, copy_source_close,
           copy_destination_probe, copy_source_actual,
           copy_destination_open, copy_tape_preflight_gate,
           copy_stage_signature, copy_commit) < 0 or not (
           copy_io < copy_tape_preflight_gate < copy_source_preflight <
           copy_source_close <
           copy_destination_probe < copy_source_actual <
           copy_destination_open < copy_stage_signature < copy_commit):
        failures.append(
            "copy must preflight non-tape sources, consume tape sources only "
            "once, signature-check the stage, then commit")
    # Optional readback is scoped to one user command; default transfers still
    # verify their temporary stage before committing or removing a source.
    copy_handler = resident[resident.find("static void cmd_copy_move("):resident.find("static void cmd_delete(")]
    if 'copy_call.skip_verify = option_present(argc, "--no-verify");' not in copy_handler:
        failures.append("COPY/MOVE must refresh the skip-readback flag on every command")
    stage_gate = resident[resident.rfind("    if (", copy_io, copy_stage_signature):copy_stage_signature]
    if '!call->skip_verify &&' not in stage_gate:
        failures.append("only an explicit skip-readback flag may bypass staged signature verification")
    preview = (APP / "readyfs_preview.c").read_text(encoding="utf-8")
    if any(token in preview for token in ('readyfs_reu_session_store(', 'readyfs_reu_batch_store(', 'readyfs_overlay_recursive(', 'readyfs_overlay_backend_call(', 'readyfs_io_copy_call(', 'cbm_', 'readyfs_uci_')):
        failures.append("named what-if presentation must remain read-only and must not invoke storage or the executor")
    if 'RF_PLAN_SELECTED' not in preview or 'RF_PLAN_HEADER_BYTES' not in preview or 'whatif: no files changed' not in preview:
        failures.append("named what-if must display only selected serialized plan records and report no changes")
    delete_command = resident.find("static void cmd_delete")
    delete_begin = resident.find(
        "action_begin(RF_EXEC_ACTION_DELETE_FILE", delete_command)
    delete_io = resident.find("result = delete_stream", delete_begin)
    delete_complete = resident.find("action_complete(result)", delete_io)
    directory_command = resident.find("static void cmd_mkdir_rmdir")
    mkdir_begin = resident.find(
        "action_begin(RF_EXEC_ACTION_MKDIR", directory_command)
    mkdir_io = resident.find("result = create_directory", mkdir_begin)
    mkdir_complete = resident.find("action_complete(result)", mkdir_io)
    rmdir_begin = resident.find(
        "action_begin(RF_EXEC_ACTION_RMDIR", mkdir_complete)
    rmdir_io = resident.find("result = remove_directory", rmdir_begin)
    rmdir_complete = resident.find("action_complete(result)", rmdir_io)
    if min(delete_begin, delete_io, delete_complete, mkdir_begin, mkdir_io,
           mkdir_complete, rmdir_begin, rmdir_io, rmdir_complete) < 0 or not (
            delete_begin < delete_io < delete_complete and
            mkdir_begin < mkdir_io < mkdir_complete < rmdir_begin <
            rmdir_io < rmdir_complete):
        failures.append(
            "delete/mkdir/rmdir must wrap resident I/O in action BEGIN/COMPLETE")
    partition_helper = resident.find(
        "static unsigned char drive_partition_command")
    partition_begin = resident.find(
        "drive_command.operation = operation == RF_CMDPATH_FORMAT",
        partition_helper)
    partition_begin = resident.find("RF_DRIVEUI_COMMAND_BEGIN",
                                    partition_begin)
    partition_gateway = resident.find(
        "readyfs_overlay_drive(&drive_command)", partition_begin)
    partition_io = resident.find(
        "probe_iec_io(&drive_command)", partition_gateway)
    partition_unmount = resident.find(
        "operation == RF_CMDPATH_UNMOUNT", partition_io)
    partition_followup_output = resident.find(
        "drive_command.output = drive_command.followup", partition_unmount)
    partition_followup_clear = resident.find(
        "drive_command.followup = 0", partition_followup_output)
    partition_followup_io = resident.find(
        "probe_iec_io(&drive_command)", partition_followup_clear)
    partition_complete = resident.find(
        "drive_command.operation = RF_DRIVEUI_COMMAND_COMPLETE",
        partition_followup_io)
    directory_hook = resident.find(
        "drive_partition_command(args[1], 0, argc", directory_command)
    if min(partition_helper, partition_begin, partition_gateway, partition_io,
           partition_unmount, partition_followup_output,
           partition_followup_clear, partition_followup_io,
           partition_complete, directory_hook) < 0 or not (
           partition_helper < partition_begin < partition_gateway <
           partition_io < partition_unmount < partition_followup_output <
           partition_followup_clear < partition_followup_io <
           partition_complete < directory_hook):
        failures.append(
            "partition mutations must authorize, perform resident IEC I/O, "
            "bound unmount to one cleared follow-up, then complete")
    delete_filter = resident.find("action_filter_accept(argc, args[1]",
                                  delete_command)
    delete_preview = resident.find("if (has_dry_run(argc))", delete_filter)
    partition_delete_hook = resident.find(
        "drive_partition_command(args[1], 0, argc,",
        delete_preview)
    partition_delete_kind = resident.find(
        "RF_CMDPATH_SCRATCH", partition_delete_hook)
    delete_path_prepare = resident.find(
        "path_prepare(args[1], &command_stream)", partition_delete_kind)
    if min(delete_filter, delete_preview, partition_delete_hook,
           partition_delete_kind, delete_path_prepare) < 0 or not (
           delete_filter < delete_preview < partition_delete_hook <
           partition_delete_kind < delete_path_prepare):
        failures.append(
            "partition delete must filter and dry-run before drive routing, "
            "then fall back to legacy path preparation")
    rename_command = resident.find("static void cmd_rename")
    rename_preview = resident.find("if (has_dry_run(argc))", rename_command)
    partition_rename_hook = resident.find(
        "drive_partition_command(args[1], args[2], argc", rename_preview)
    partition_rename_kind = resident.find(
        "RF_CMDPATH_RENAME", partition_rename_hook)
    rename_path_prepare = resident.find(
        "path_prepare(args[1], &source)", partition_rename_kind)
    destination_resolve = resident.find(
        "resolve_path(destination, dest.canonical)", partition_helper)
    destination_assign = resident.find(
        "destination == 0 ? 0 : dest.canonical", destination_resolve)
    followup_assign = resident.find(
        "drive_command.followup = backup.canonical", destination_assign)
    followup_capacity = resident.find(
        "drive_command.followup_capacity = sizeof(backup.canonical)",
        followup_assign)
    if min(rename_command, rename_preview, partition_rename_hook,
           partition_rename_kind, rename_path_prepare, destination_resolve,
           destination_assign, followup_assign, followup_capacity) < 0 or not (
           partition_helper < destination_resolve < destination_assign <
           followup_assign < followup_capacity and
           rename_command < rename_preview < partition_rename_hook <
           partition_rename_kind < rename_path_prepare):
        failures.append(
            "partition rename must dry-run before resolving both aliases, "
            "then route before legacy source/destination preparation")
    drive_range_first = driveui.find(
        "call->native_operation < RF_CMDPATH_DIRECTORY")
    drive_range_last = driveui.find(
        "call->native_operation > RF_CMDPATH_NATIVE_DIR", drive_range_first)
    drive_force_not_dir = driveui.find(
        "call->native_operation != RF_CMDPATH_DIRECTORY", drive_range_last)
    drive_force_not_native = driveui.find(
        "call->native_operation != RF_CMDPATH_NATIVE_DIR",
        drive_force_not_dir)
    drive_force_not_mkdir = driveui.find(
        "call->native_operation != RF_CMDPATH_MKDIR",
        drive_force_not_native)
    drive_force_guard = driveui.find("!call->force", drive_force_not_mkdir)
    drive_action_helper = driveui.find(
        "static unsigned char command_action")
    drive_delete_action = driveui.find(
        "RF_EXEC_ACTION_DELETE_FILE", drive_action_helper)
    drive_move_action = driveui.find(
        "RF_EXEC_ACTION_MOVE_FILE", drive_delete_action)
    drive_delete_source = driveui.find(
        "backend->source_root = call->source")
    drive_move_destination = driveui.find(
        "action == RF_EXEC_ACTION_MOVE_FILE ?", drive_delete_source)
    drive_media_begin = driveui.find(
        "call->native_operation >= RF_CMDPATH_MOUNT", drive_force_guard)
    drive_begin = driveui.find("RF_BACKEND_CALL_BEGIN", drive_media_begin)
    drive_command_complete = driveui.find(
        "call->operation == RF_DRIVEUI_COMMAND_COMPLETE", drive_begin)
    drive_media_complete = driveui.find(
        "call->native_operation >= RF_CMDPATH_MOUNT", drive_command_complete)
    drive_complete = driveui.find(
        "RF_BACKEND_CALL_COMPLETE", drive_media_complete)
    if min(drive_range_first, drive_range_last, drive_force_not_dir,
           drive_force_not_native,
           drive_force_not_mkdir, drive_force_guard, drive_action_helper,
           drive_delete_action, drive_move_action, drive_delete_source,
           drive_move_destination, drive_media_begin, drive_begin,
           drive_command_complete, drive_media_complete,
           drive_complete) < 0 or not (
           drive_delete_source < drive_move_destination < drive_action_helper <
           drive_delete_action < drive_move_action < drive_range_first <
           drive_range_last < drive_force_not_dir < drive_force_not_native <
           drive_force_not_mkdir <
           drive_force_guard < drive_media_begin < drive_begin <
           drive_command_complete < drive_media_complete < drive_complete):
        failures.append(
            "drive sidecar must require force for scratch/rename/mount, map "
            "file actions to DELETE_FILE/MOVE_FILE, retain the canonical "
            "source for journal completion, and keep media outside "
            "file-action BEGIN/COMPLETE")
    mount_command = resident.find("static void cmd_mount")
    mount_preview = resident.find("if (has_dry_run(argc))", mount_command)
    partition_mount_hook = resident.find(
        "drive_partition_command(args[1], 0, argc", mount_preview)
    partition_mount_kind = resident.find(
        "RF_CMDPATH_MOUNT", partition_mount_hook)
    mount_legacy_args = resident.find("if (argc < 3u)", partition_mount_kind)
    mount_legacy_path = resident.find(
        "path_prepare(args[1], &command_stream)", mount_legacy_args)
    if min(mount_command, mount_preview, partition_mount_hook,
           partition_mount_kind, mount_legacy_args, mount_legacy_path) < 0 or \
       not (mount_command < mount_preview < partition_mount_hook <
            partition_mount_kind < mount_legacy_args < mount_legacy_path):
        failures.append(
            "partition mount must dry-run before profile/translation routing "
            "and precede the legacy Ultimate target path")
    softmap_path = resident.find("static unsigned char softiec_raw_path")
    softmap_mount = resident.find("static void cmd_softiec_mount", softmap_path)
    softmap_body = resident[softmap_path:softmap_mount]
    if softmap_path < 0 or softmap_mount < 0 or \
       "strcpy(raw, host);" not in softmap_body or \
       "(unsigned char)*scan == 0xA4u" not in softmap_body or \
       "*scan = 0x5Fu" not in softmap_body or \
       'strcpy(raw, "/USB0")' in softmap_body:
        failures.append(
            "SoftIEC ADD_PARTITION must preserve the live Ultimate virtual-"
            "root path, normalize PETSCII underscores at that boundary, and "
            "never rewrite USB1 to the stale USB0 default")
    media_command = resident.find("static void cmd_drive_media")
    media_preview = resident.find("if (has_dry_run(argc))", media_command)
    partition_unmount_hook = resident.find(
        "drive_partition_command(args[1], 0, argc", media_preview)
    partition_unmount_kind = resident.find(
        "RF_CMDPATH_UNMOUNT", partition_unmount_hook)
    softiec_unmap_fallback = resident.find(
        "softiec_designator(args[1], &unit)", partition_unmount_kind)
    if min(media_command, media_preview, partition_unmount_hook,
           partition_unmount_kind, softiec_unmap_fallback) < 0 or not (
           media_command < media_preview < partition_unmount_hook <
           partition_unmount_kind < softiec_unmap_fallback):
        failures.append(
            "partition unmount must dry-run before two-command routing and "
            "precede SoftIEC-map/Ultimate-drive fallbacks")
    partition_list = resident.find(
        "operation == RF_CMDPATH_DIRECTORY", partition_gateway)
    native_list = resident.find(
        "operation == RF_CMDPATH_NATIVE_DIR", partition_list)
    partition_list_io = resident.find(
        "return dir_iec(drive_command.device, drive_command.output, 1u)",
        native_list)
    partition_tree_mode = resident.find(
        "dir_iec(drive_command.device, drive_command.output, 0u)",
        partition_list_io)
    partition_mutation_io = resident.find(
        "probe_iec_io(&drive_command)", partition_tree_mode)
    if min(partition_list, native_list, partition_list_io, partition_tree_mode,
           partition_mutation_io) < 0 or not (
           partition_list < native_list < partition_list_io <
           partition_tree_mode <
           partition_mutation_io):
        failures.append(
            "partition and opt-in native-pattern directories must use "
            "resident listing I/O without a mutation completion")
    partition_tree = resident.find(
        "drive_partition_command(temp_text, 0, 0u,", resident.find(
            "static void cmd_tree"))
    partition_tree_op = resident.find(
        "RF_CMDPATH_DIRECTORY", partition_tree)
    if min(partition_tree, partition_tree_op) < 0:
        failures.append(
            "CMD/SD2IEC tree traversal must route queued logical paths "
            "through the shared drive-profile translator")
    if "#define drive_command (*(ReadyFsDriveUiCall *)(void *)&source)" \
            not in resident or \
       "resolve_path(text, temp.canonical)" not in resident:
        failures.append(
            "partition tree translation must preserve the queued tree root "
            "instead of aliasing the drive call over dest")
    if "RF_MATCH_RAW_STEM" not in resident or \
       "(call->file & RF_MATCH_RAW_STEM) == 0u" not in \
            (APP / "readyfs_match.c").read_text(encoding="utf-8"):
        failures.append(
            "tree filtering must use one cached matcher call while limiting "
            "Ultimate name normalization to Ultimate entries")
    native_function = cmdpath.find(
        "static unsigned char native_directory_pattern")
    native_endpoint = cmdpath.find("path->endpoint != RF_EP_IEC",
                                   native_function)
    native_partition = cmdpath.find("path->partition != 0u", native_endpoint)
    native_image = cmdpath.find("path->image_depth != 0u", native_partition)
    native_flat = cmdpath.find("strchr(body, '/') != 0", native_image)
    native_limit = cmdpath.find("length > RF_CMDPATH_COMPONENT_MAX",
                                native_flat)
    native_star = cmdpath.find("strchr(body, '*')", native_limit)
    native_question = cmdpath.find("strchr(body, '?')", native_star)
    native_prefix_dollar = cmdpath.find("call->output[0] = '$'",
                                        native_question)
    native_prefix_colon = cmdpath.find("call->output[1] = ':'",
                                       native_prefix_dollar)
    native_dispatch = cmdpath.find(
        "call->operation == RF_CMDPATH_NATIVE_DIR", native_prefix_colon)
    native_cmd = resident.find('same_word(args[2], "--native-pattern")')
    native_route = resident.find("RF_CMDPATH_NATIVE_DIR", native_cmd)
    legacy_native_guard = resident.find(
        "temp_text[path.path_offset + 1u] != 0", native_route)
    legacy_native_reject = resident.find('result_unsupported("unsupported\\r\\n")',
                                         legacy_native_guard)
    legacy_root_list = resident.find("dir_iec(path.unit, 0, 0u)",
                                     legacy_native_reject)
    if min(native_function, native_endpoint, native_partition, native_image,
           native_flat, native_limit, native_star, native_question,
           native_prefix_dollar, native_prefix_colon, native_dispatch,
           native_cmd, native_route, legacy_native_guard,
           legacy_native_reject, legacy_root_list) < 0 or not (
           native_function < native_endpoint < native_partition <
           native_image < native_flat < native_limit < native_star <
           native_question < native_prefix_dollar < native_prefix_colon <
           native_dispatch and native_cmd < native_route <
           legacy_native_guard < legacy_native_reject < legacy_root_list):
        failures.append(
            "--native-pattern must opt into flat unpartitioned IEC wildcard "
            "translation, enforce the 16-character component limit, emit "
            "$:PATTERN, route back to resident directory I/O, and keep an "
            "unflagged non-root IEC path out of the native open")
    native_prepare = backend.find("call->phase == RF_NATIVEPLAN_PREPARE")
    native_dry_gate = backend.find("native_is_dry(call)", native_prepare)
    native_apply_gate = backend.find('native_find(call, "--apply")',
                                     native_dry_gate)
    native_apply_denial = backend.find('cputs("need --apply\\r\\n")',
                                       native_apply_gate)
    native_translate = backend.find("RF_CMDPATH_NATIVE_DIR",
                                    native_apply_denial)
    native_add = backend.find("call->phase != RF_NATIVEPLAN_ADD",
                              native_translate)
    native_type_gate = backend.find("RF_NATIVE_TYPE_FIRST", native_add)
    native_match = backend.find("RF_NESTED_MATCH", native_type_gate)
    native_recursive = backend.find("RF_NESTED_RECURSIVE", native_match)
    native_target = backend.find('cputs("target ")', native_recursive)
    native_batch_option = resident.find(
        'option_present(argc, "--native-pattern")', resident_batch)
    native_dest_endpoint = resident.find(
        "dest.path.endpoint == RF_EP_IEC", native_batch_option)
    native_dest_root = resident.find(
        "dest.canonical[dest.path.path_offset + 1u] != 0",
        native_dest_endpoint)
    native_open = resident.find(
        "cbm_opendir(7u, source.path.unit, temp_text)", native_dest_root)
    native_report = resident.find("RF_NATIVEPLAN_REPORT", native_open)
    if min(native_prepare, native_dry_gate, native_apply_gate,
           native_apply_denial, native_translate, native_add, native_type_gate,
           native_match, native_recursive, native_target,
           native_batch_option, native_dest_endpoint, native_dest_root,
           native_open, native_report) < 0 or not (
           native_prepare < native_dry_gate < native_apply_gate <
           native_apply_denial < native_translate < native_add <
           native_type_gate < native_match < native_recursive < native_target and
           resident_batch < native_batch_option < native_dest_endpoint <
           native_dest_root < native_open < native_report):
        failures.append(
            "native actions must require WhatIf or explicit --apply, "
            "translate read-only, "
            "enumerate in resident, reject unsupported file types for the "
            "whole plan, filter/freeze exact names through the "
            "recursive controller, print targets, and only then reach the "
            "journaled exact-name executor; regular IEC collection "
            "destinations must remain the flat root")
    presence = resident.find("unsigned char readyfs_iec_present(")
    drive_scan = resident.find("static void cmd_drives(void)", presence)
    presence_body = resident[presence:drive_scan]
    listen = presence_body.find("cbm_k_listen(device)")
    read_status = presence_body.find("cbm_k_readst()", listen)
    unlisten = presence_body.find("cbm_k_unlsn()", read_status)
    if min(presence, drive_scan, listen, read_status, unlisten) < 0 or not (
            listen < read_status < unlisten) or "cbm_open" in presence_body:
        failures.append(
            "drive discovery must use the bounded IEC LISTEN/status/UNLISTEN "
            "presence handshake, not full command-channel opens")
    drive_scan_first = resident.find("device = 8u", drive_scan)
    drive_scan_last = resident.find("device <= 30u", drive_scan_first)
    drive_scan_step = resident.find("++device", drive_scan_last)
    drive_scan_probe = resident.find("readyfs_iec_present(device)", drive_scan_step)
    drive_scan_gateway = resident.find(
        "readyfs_overlay_utility(&utility_ui)", drive_scan_probe)
    utility_drives = utility.find("static unsigned char drives(")
    drive_scan_tape = utility.find("t: sequential tape", utility_drives)
    if min(drive_scan, drive_scan_first, drive_scan_last, drive_scan_step,
           drive_scan_probe, drive_scan_gateway, utility_drives,
           drive_scan_tape) < 0 or not (
           drive_scan < drive_scan_first < drive_scan_last < drive_scan_step <
           drive_scan_probe < drive_scan_gateway and
           utility_drives < drive_scan_tape):
        failures.append(
            "drive discovery must probe every IEC device 8 through 30 and "
            "dispatch resident results to a sidecar that retains the "
            "sequential-tape capability line")
    stat_cmd = resident.find("static void cmd_stat(")
    stat_end = resident.find("static unsigned char print_softiec_mapping(",
                             stat_cmd)
    stat_body = resident[stat_cmd:stat_end]
    stat_type = stat_body.find('cputs("type: $")')
    stat_estimate = stat_body.find('cputs("size est: ")', stat_type)
    stat_exact = stat_body.find('cputs("size exact: ")', stat_estimate)
    stat_bytes = stat_body.find('cputs(" bytes\\r\\n")', stat_exact)
    if min(stat_cmd, stat_end, stat_type, stat_estimate, stat_exact,
           stat_bytes) < 0 or not (
           stat_type < stat_estimate < stat_exact < stat_bytes):
        failures.append(
            "stat must report file type, estimated IEC C64 blocks, and "
            "exact Ultimate byte sizes")
    if "ca = (unsigned char)*a++ & 0x7Fu;" not in resident or \
       "cb = (unsigned char)*b++ & 0x7Fu;" not in resident or \
       resident.count("strcpy(name, entry.name);") != 1 or \
       "iec_find_type(stream->device, stream->native_name, &stream->type)" not in resident:
        failures.append(
            "IEC lookup must compare bit-7 PETSCII variants and retain the "
            "exact raw directory spelling for subsequent device opens")
    pager = resident.find("static void dir_page_line(void)")
    pager_wait = resident.find("cgetc()", pager)
    pager_clear = resident.find("clrscr()", pager_wait)
    iec_dir = resident.find("static unsigned char dir_iec(")
    iec_page_reset = resident.find("dir_page_lines = 0u", iec_dir)
    iec_page_call = resident.find("dir_page_line()", iec_page_reset)
    ultimate_block = resident.find("static void dir_ultimate_block(")
    ultimate_page_call = resident.find("dir_page_line()", ultimate_block)
    ultimate_dir = resident.find("static void dir_ultimate(")
    ultimate_page_reset = resident.find("dir_page_lines = 0u", ultimate_dir)
    if min(pager, pager_wait, pager_clear, iec_dir,
           iec_page_reset, iec_page_call, ultimate_block,
           ultimate_page_call, ultimate_dir, ultimate_page_reset) < 0 or not (
           pager < pager_wait < pager_clear < iec_dir <
           iec_page_reset < iec_page_call < ultimate_block <
           ultimate_page_call < ultimate_dir < ultimate_page_reset):
        failures.append(
            "IEC and Ultimate directories must share bounded paging that "
            "waits, clears, and resumes; all output rows must be captured before scrolling")
    if "jsr console_stash_row" not in console or "readyfs_console_recording = 1u" not in resident:
        failures.append("continuous REU output capture must remain active outside editor drawing")
    action_begin = c64_executor.find("readyfs_action_dispatch")
    action_store = c64_executor.find("readyfs_reu_session_store", action_begin)
    action_fetch = c64_executor.find("readyfs_reu_session_fetch", action_store)
    action_ack_dispatch = c64_executor.find(
        "readyfs_exec_dispatch(&action_exec_call)", action_fetch)
    action_report = c64_executor.find("action_report[0] = 0x52u", action_fetch)
    action_report_store = c64_executor.find(
        "RF_REU_ACTION_REPORT_OFF", action_report)
    if min(action_begin, action_store, action_fetch, action_ack_dispatch,
           action_report, action_report_store) < 0 or not (
            action_begin < action_store < action_fetch < action_ack_dispatch <
            action_report < action_report_store):
        failures.append(
            "action controller must checkpoint, ACK, then persist RFA1")
    for action in ("RF_EXEC_ACTION_MKDIR", "RF_EXEC_ACTION_COPY_FILE",
                   "RF_EXEC_ACTION_MOVE_FILE", "RF_EXEC_ACTION_DELETE_FILE",
                   "RF_EXEC_ACTION_RMDIR"):
        if action not in c64_executor[action_begin:action_store]:
            failures.append(f"general action controller missing {action}")

    stream_policy = (APP / "readyfs_stream.c").read_text(encoding="utf-8")
    tape_path = stream_policy.find("readyfs_path_parse(stream->canonical")
    tape_device = stream_policy.find(
        "stream->path.endpoint == RF_EP_TAPE ? 1u", tape_path)
    tape_read_open = resident.find("cbm_open(lfn, 1u, 0u, stream->native_name)")
    tape_write_open = resident.find("cbm_open(lfn, 1u, 1u, stream->native_name)")
    tape_eof_guard = resident.find(
        "stream->path.endpoint == RF_EP_TAPE && stream->open == 2u")
    tape_eof_latch = resident.find(
        "(unsigned int)got < cap) stream->open = 2u", tape_eof_guard)
    tape_status_read = resident.rfind("RF_KERNAL_STATUS = 0u", 0,
                                      tape_read_open)
    tape_status_write = resident.rfind("RF_KERNAL_STATUS = 0u", 0,
                                       tape_write_open)
    stream_write_entry = resident.find("static unsigned char stream_write(")
    iec_write_status = resident.find("RF_KERNAL_STATUS = 0u",
                                     stream_write_entry)
    iec_write_call = resident.find("cbm_write(stream->lfn", iec_write_status)
    copy_entry = resident.find("unsigned char readyfs_io_copy_call")
    copy_tape_pair = resident.find('result_unsupported("one tape drive', copy_entry)
    copy_tape_move = resident.find('result_unsupported("tape move off', copy_tape_pair)
    copy_spool_init = resident.find("RF_TAPE_SPOOL_INIT", copy_tape_move)
    copy_open = resident.find("stream_open_read(&source, 1u, 2u)",
                              copy_spool_init)
    copy_spool_store = resident.find("RF_TAPE_SPOOL_STORE", copy_open)
    copy_spool_fetch = resident.find("RF_TAPE_SPOOL_FETCH", copy_spool_store)
    copy_signature = resident.find("signature_add(&left_signature", copy_open)
    copy_stage = resident.find("signature_file(&temp, &right_signature)",
                               copy_signature)
    copy_commit = resident.find("rename_stream(&temp, &dest)", copy_stage)
    if min(tape_path, tape_device, tape_read_open, tape_write_open,
           tape_eof_guard, tape_eof_latch, tape_status_read,
           tape_status_write, stream_write_entry, iec_write_status,
           iec_write_call, copy_entry, copy_tape_pair,
           copy_tape_move, copy_spool_init, copy_open, copy_spool_store,
           copy_spool_fetch, copy_signature, copy_stage,
           copy_commit) < 0 or not (
               tape_path < tape_device and tape_read_open < tape_write_open and
               tape_status_read < tape_read_open and
               tape_status_write < tape_write_open and
               stream_write_entry < iec_write_status < iec_write_call and
               tape_eof_guard < tape_eof_latch and
               copy_entry < copy_tape_pair < copy_tape_move <
               copy_spool_init < copy_open < copy_spool_store <
               copy_signature < copy_spool_fetch < copy_stage < copy_commit):
        failures.append(
            "tape paths must map to KERNAL device 1 with SA0/SA1, latch a "
            "short final read as sequential EOF, reset shared KERNAL status, "
            "reject tape-to-tape/move, spool STORE/FETCH in REU, verify the "
            "staged signature, and only then commit the destination")
    if "STOP TAPE; PRESS KEY" in resident:
        failures.append("tape-to-disk copy must not require an extra UI pause")
    if "fetch_eof:" not in tape_spool or "jmp succeed" not in \
       tape_spool.split("fetch_eof:", 1)[-1].split("; A is", 1)[0]:
        failures.append("assembly tape replay EOF must return success")
    for rejection in ("tape append off", "tape delete off", "tape dirs off",
                      "tape rename off"):
        if rejection not in resident:
            failures.append(f"missing explicit {rejection} rejection")
    if "RF_EP_TAPE" not in tape or "strlen(name) > 16u" not in tape or \
       "TAPE_CBM_SEQ 0x10u" not in tape:
        failures.append(
            "tape sidecar must preserve the t: endpoint, 16-character leaf "
            "limit, and cc65 file-type ABI")
    if "cbm_" in tape or "readyfs_uci_" in tape:
        failures.append("tape sidecar must remain pure; resident owns device I/O")

    if failures:
        for failure in failures:
            print(f"ReadyFS pipeline contract: FAIL: {failure}")
        return 1
    print("ReadyFS pipeline contract: PASS (one-pointer five-action and "
          "multi-entry recursive controllers, flat IEC plus Ultimate tree "
          "import with access/logical name separation, "
          "shared IEC/Ultimate REU directory paging, bounded views, CRC32, "
          "sequential KERNAL device-1 tape transfer with staged copy verify, "
          "RFT1 self-tests, and cooperative run/onerror/expect scripts, "
          "slot-7 SoftwareIEC component-CD generation with resident status, "
          "resident-owned legacy/recursive "
          "and partition "
          "dir/delete/mkdir/rmdir/rename/mount/unmount I/O, "
          "drive/backend restore, RFJ1-before-ACK, RFA1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
