#!/usr/bin/env python3
"""Reject timing-sensitive regressions in the standalone ReadyFS UCI transport."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def require(relative: str, needles: tuple[str, ...]) -> None:
    source = text(relative)
    for needle in needles:
        if needle not in source:
            ERRORS.append(
                f"{relative}: missing required UCI contract marker {needle!r}"
            )


def forbid(relative: str, patterns: tuple[str, ...]) -> None:
    source = text(relative)
    for pattern in patterns:
        if re.search(pattern, source, re.MULTILINE):
            ERRORS.append(f"{relative}: forbidden legacy UCI pattern /{pattern}/")


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", source, re.DOTALL)
    if not match:
        return ""
    depth = 1
    position = match.end()
    while position < len(source) and depth:
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
        position += 1
    return source[match.end():position - 1]


TRANSPORT = "src/apps/readyfs/readyfs_uci.c"
require(
    TRANSPORT,
    (
        "UCI_STAT_ACCEPT",
        "UCI_STAT_ERROR",
        "quiet_idle",
        "wait_response_state",
        "PUSH_CMD is asynchronous",
        "DATA_ACC is asynchronous",
        "wait_accept_advance",
        "abort_and_recover",
        "UCI_WAIT_PASSES",
        "drain_tries",
        "asm_accept_data();",
    ),
)
forbid(
    TRANSPORT,
    (
        r"\bdrain_guard\b",
        r"\bUCI_WAIT_SHORT\b",
        r"if\s*\(state\s*==\s*UCI_STATE_IDLE\)",
        r"state\s*==\s*UCI_STATE_LAST\s*\|\|\s*state\s*==\s*UCI_STATE_MORE\s*\|\|\s*state\s*==\s*UCI_STATE_IDLE",
    ),
)

source = text(TRANSPORT)
idle = function_body(source, "wait_idle")
response = function_body(source, "wait_response_state")
sync = function_body(source, "sync_interface")
accept = function_body(source, "wait_accept_advance")
recover = function_body(source, "abort_and_recover")
command = function_body(source, "readyfs_uci_command")
recovery_probe = function_body(source, "readyfs_uci_recovery_probe")

if not idle:
    ERRORS.append(f"{TRANSPORT}: could not locate wait_idle body")
elif "clear_error" in idle:
    ERRORS.append(f"{TRANSPORT}: wait_idle must report ERROR, not clear it")
if not response:
    ERRORS.append(f"{TRANSPORT}: could not locate wait_response_state body")
elif "UCI_STATE_IDLE" in response:
    ERRORS.append(f"{TRANSPORT}: wait_response_state must accept only LAST/MORE")
if "asm_abort();" in sync:
    ERRORS.append(f"{TRANSPORT}: sync_interface must service ABORT_P")
if re.search(r"(?m)^\s*tries\s*=\s*0u\s*;", sync):
    ERRORS.append(f"{TRANSPORT}: sync_interface resets its failure bound")
if "asm_accept_data();" in sync and "wait_accept_advance(state)" not in sync:
    ERRORS.append(f"{TRANSPORT}: recovery can re-issue asynchronous DATA_ACC")
for name, body in (
    ("wait_idle", idle),
    ("wait_response_state", response),
    ("wait_accept_advance", accept),
):
    if "UCI_WAIT_PASSES" not in body:
        ERRORS.append(f"{TRANSPORT}: {name} needs a bounded top-speed pass count")
if "UCI_STAT_ABORT" not in recover or "== 0u" not in recover:
    ERRORS.append(f"{TRANSPORT}: recovery must check ABORT_P before ABORT")
if "readyfs_uci_asm_accept_more_transition(state)" not in command:
    ERRORS.append(f"{TRANSPORT}: MORE must use the adjacent transition observer")
for marker in (
    "UltimateDOS IDENTIFY is read-only",
    "!status_is_quiet_idle(st)",
    "abort_and_recover()",
    "Poll counts are failure bounds",
):
    if marker not in recovery_probe:
        ERRORS.append(f"{TRANSPORT}: recovery probe missing {marker!r}")
if "readyfs_uci_asm_abort" in recovery_probe:
    ERRORS.append(f"{TRANSPORT}: recovery probe bypasses shared recovery")

require(
    "src/apps/readyfs/readyfs_uci_asm.s",
    (
        "_readyfs_uci_asm_accept_more_transition",
        "DATA_ACC is asynchronous",
        "MORE -> BUSY",
        "4096-sample",
    ),
)
require(
    "build_support/readyfs_uci_test.c",
    (
        "accept_more_count == 1u",
        "xfer.block_count == 2u",
        "RF_UCI_TRUNC_DATA | RF_UCI_TRUNC_STAT",
        "RF_UCI_ERROR",
        "897u",
    ),
)
require(
    "build_support/run_readyfs_c64u_readonly_ui.sh",
    ("probe recover", "UCI RECOVER: QUIET", "RF-HW-$test_speed-004"),
)
require(
    "build_support/run_readyfs_c64u_speed_matrix.sh",
    (
        "READYFS_MATRIX_CASE",
        "READYFS_UI_COMMAND='probe recover'",
        "UCI RECOVER: QUIET",
    ),
)

if ERRORS:
    print("READYFS UCI PROTOCOL CONTRACT VERIFICATION FAILED", file=sys.stderr)
    for error in ERRORS:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("READYFS UCI PROTOCOL CONTRACT VERIFICATION PASSED")
