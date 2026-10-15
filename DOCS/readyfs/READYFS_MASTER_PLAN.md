# ReadyFS Lab Master Plan

Status: active long-horizon implementation contract. This file preserves the
full intended scope across context compactions. Passing a narrow probe is not
completion.

## Purpose and deliverables

ReadyFS Lab is a standalone C64 filesystem shell and experimental storage
architecture. It is not yet a ReadyOS launcher app. Deliver:

- `artifacts/readyfs/readyfs.prg`
- `artifacts/readyfs/readyfs-lab.d81`
- host/parser/planner tests
- VICE UI automation with 25–100 cases and screenshots
- physical C64 Ultimate automation at 1, 16, and 64 MHz
- machine-readable and Markdown reports covering every suite
- documented proven versus provisional behavior suitable for later ReadyOS
  filesystem integration

## Canonical path model

Endpoint-first paths use `/` separators:

- `8:/FILE` through `30:/FILE`: IEC devices
- `11.3:/folder/file.prg`: partition 3 on IEC device 11, with support depending
  on the detected driver; native SD2IEC implements this partition-qualified form
- `u:/usb1/folder/file.prg`: UltimateDOS host filesystem
- `s3:/folder/file.prg`: SoftIEC partition 3 through UCI bypass
- `t:/NAME`: tape endpoint
- `@work:/src/file.c`: alias rooted at an exact canonical location
- `u:/usb1/disks/demo.d81!/PROGRAM`: explicit image boundary
- `10.1:/games/demo.d64!/PROGRAM`: SD2IEC-compatible partition/image boundary

The dot suffix selects a native partition, not another IEC device: `10.1:/`
and `10.2:/` mean partitions 1 and 2 on device 10, if both exist. `10:/` uses
its current partition. `IEC 10: PARTITIONS` inspects what is available;
partition-qualified file operations do not themselves change the current
selection. The [native reference](SD2IEC_NATIVE.md) describes implemented
behavior and media-transition limits.

`!` always separates the host image file from its internal filesystem. Host
filename, internal volume label/id, displayed PETSCII name, raw FAT name, and
contained filename remain distinct metadata.

The shell resolves every operation to an absolute logical path and does not
trust mutable backend current-directory state. Canonical lines and expanded
paths support 255 bytes. Each driver reports and enforces its native component,
path, channel, and command limits before mutation.

Shell matching supports `*` within a component, `?` for one character, and
`**` across directories. `--include` and `--exclude` match the whole relative
stem. Backend/C64-DOS pattern forwarding is explicit through
`--native-pattern`; it is never confused with shell recursion.

For mutating commands, a native pattern is selection syntax only. ReadyFS
first performs a read-only native directory query, freezes every returned exact
name in the REU plan, displays the complete WhatIf/confirmation set, and then
executes ordinary exact-name actions. It never sends a wildcard scratch,
rename, or write command to a device. Entry-limit truncation invalidates the
plan instead of authorizing a partial mutation, and newly matching files are
not included after confirmation.

The standalone lab now implements both halves of this contract. `--whatif`
enumerates, prints, and freezes exact targets while completing zero actions.
A real native-pattern action additionally requires explicit `--apply`; the
same invocation prints and freezes the complete set before its normal
RFJ1-before-ACK exact-name executor starts. Bare `--native-pattern`, including
with `--force`/`--yes`, is denied. `vice_auto_20260816_171906` proves singleton
delete plus two-file IEC8-to-IEC9 copy and one-file move, byte comparison,
source/destination postconditions, and parsed finished RFJ1 records. No raw
wildcard mutation is issued. Regular flat IEC destinations are admitted only
at their root, and `vice_auto_20260816_171852` proves a native match returning
REL type `$13` invalidates the whole plan before any destination action.

## Command contract

Discovery/navigation:

- `drives [scan]`, `probe [all|uci|udos|softiec|iec|tape|recover]`
- `capabilities [path]`, `status`, `pwd`, `cd`
- `dir`/`ls`, `tree`, `find`, `stat`, `volume`, `free`
- `type`/`cat`, `head`, `tail`, `compare`, `verify`, `crc32`

Mutation:

- `new path [--type seq|prg|usr]`
- `write path "text" [--line]`
- `append path "text" [--line]`
- `copy`/`cp`, `move`/`mv`, `rename`/`ren`
- `delete`/`rm`, `mkdir`, `rmdir`
- `format endpoint --label NAME --id ID`, restricted to a confirmed disposable
  IEC image

Mounting:

- `mount u:/path/image.d81 8:` and `dismount 8:` through UltimateDOS UCI
- `mount 10:/path/image.d64` and `dismount 10:` through CMD/SD2IEC semantics
- `mount u:/usb1/root s3: --name READYFS` and `dismount s3:` for SoftIEC maps
- `swap 8:` for Ultimate disk swap
- tape-image mounting reports REST-only unless a documented C64-side API is
  proven

Shell management:

- `alias`, `unalias`, `config load`, `config save`
- `history`, `clear`, `help`
- `run script.seq`, `test list`, `test run SUITE`

The command contract remains the authority even where dispatch is not yet
implemented. `READYFS_SCOPE_AUDIT.md` records the current command-by-command
gap list; the 60-case UI matrix is not a substitute for that broader audit.

GNU-style options are canonical. Every mutator accepts `--dry-run`, with
`--whatif` as an exact alias. Common options include `--recursive`, `--force`,
`--skip-existing`, `--error-existing`, `--include`, `--exclude`, `--verify`,
and `--yes`.

Interactive conflicts prompt per destination. Batch mode never waits: an
unspecified conflict is an error. Recursive deletion and format require a
summary confirmation unless `--yes` is supplied.

## Operation and metadata semantics

Every mutation first creates a plan containing resolved source/destination,
backend, recursion, conflicts, estimated entries/bytes/blocks, and unsupported
steps. Dry-run prints that plan and opens nothing for writing.

Same-backend rename is used only when the driver declares it safe.
Cross-backend move is copy, close, byte-for-byte or CRC verification, then
source deletion. Replacement is staged to a sibling, verified, swapped into
place, and rolled back on failure. SD2IEC save-with-replace is prohibited.

Recursive enumeration is client-side, depth/cycle bounded, deterministic, and
records partial failures. Directory metadata includes kind, display/native
names, C64 file type, exact byte size when known, block count, block-byte unit,
free blocks/bytes, timestamps, attributes, volume label/id, image type, and
capability bits.

PRG, SEQ, and USR stream copies preserve bytes. REL listing/stat/delete/rename
may be supported, but generic cross-backend REL copy is rejected unless record
length and destination behavior are proven by a dedicated harness. Tape exposes
only operations proven by its harness; unsupported directory/free/delete/
recursive/mount operations fail explicitly.

## Architecture and memory

The resident executable owns only the shell loop, canonical resolver, overlay
gateway, UCI transaction gateway, small transfer windows, and versioned result
codes. The serialized planner, stackless walk, and cooperative executor occupy
one `$B600` sidecar. The executor yields one action and waits for an explicit
resident acknowledgement, so backend I/O—including a complete UCI
transaction—finishes before the plan advances. Conflict policy,
IEC/CMD/SD2IEC, UltimateDOS, SoftIEC, tape, and batch/self-test remain or move
into overlays; extended help and the backend-neutral request composer occupy
separate sidecars. The latter carries endpoint, unit, partition, image depth,
and canonical source/destination paths across one-pointer dispatcher calls.
All required sidecars preload into disjoint REU slots before drive 8 can be
remounted. The backend is promoted only after a non-NULL C64 request succeeds
through fetch/dispatch/matcher-restore and later help/matcher calls remain
clean; host composition tests do not substitute for that C64 proof.

The current accepted build uses ten 4 KiB sidecars: nine disjoint slices in
the overlay bank and `rfbatch` at `$0000-$0FFF` of a dedicated batch bank. The
seventh `rfutil` sidecar owns mutation-preview rendering and explicit history
listing. The eighth `rftree` sidecar owns the cooperative breadth-first tree
controller. The ninth `rfcontent` sidecar owns bounded `type`/`head`/`tail`
rendering, streaming CRC-32, the compact RFT1 diagnostic, and the validation/
composition half of disposable IEC format. Resident code retains the command-
channel write and status read. Tree control checkpoints in the session bank
and its bounded queue occupies overlay-bank `$9000-$FFEF`, above all nine
main-bank cached sidecars. The tenth `rfbatch` sidecar owns the full command
editor plus cooperative `run` parsing; its bank reserves `$1000-$4FFF` for a
closed-before-dispatch script and `$5000-$50FF` for checkpoint state. Device
I/O stays resident; walkers and content/batch controllers
yield requests across the overlay gateway and resume from resident/REU state
rather than call IEC/UCI from a sidecar.

Full mode requires at least 1 MiB REU. Versioned REU regions hold overlays,
console scrollback, command history, aliases/config working state, operation
plans, batch event journal, diagnostics, and optional staging. The editor
supports 255-byte logical lines, horizontal scrolling, insert/overwrite,
left/right, Home/End, Delete, Up/Down history recall, and editable recalled
commands. Console output has line and page scrolling; C=+Up/Down is the C64
fallback for Page Up/Down.

Aliases and history live in REU for the session. Only explicit `config save`
writes settings. Batch scripts use one command per line, `#` comments,
`onerror stop|continue`, and `expect rc N`. Nested `run` is rejected and any
interactive confirmation becomes result 3 rather than reading a key. Result
values are the one-digit dispatch classes 0–3 until all legacy handlers expose
typed filesystem results. The first built-in `test` suite
emits a versioned RFT1 manifest and pass count directly in the console; VICE
tooling retains its screens and folds assertions into JSON/Markdown reports.
Future multi-suite execution can add a versioned REU event journal
without changing the atomic `test` command contract.

## UCI reliability contract

ReadyFS uses the transport proven by ReadyIRC and UCI Tester:

1. Synchronize to fully quiet IDLE; IDLE state alone is insufficient.
2. Clear stale ERROR only during explicit recovery.
3. Write the whole command while idle and issue PUSH exactly once.
4. Treat PUSH as asynchronous; immediate IDLE is not completion.
5. Wait for DATA_LAST or DATA_MORE.
6. Drain both data and status queues completely, even after capture truncation.
7. Issue DATA_ACC only after both availability flags clear.
8. Require DATA_MORE to leave that state before accepting a next block.
9. After DATA_LAST, wait for fully quiet IDLE.
10. Request ABORT once, service pending state/queues, and wait for quiet IDLE.
11. Bounds detect failure only; they never provide timing or reset forever.
12. Validate physical behavior at 1, 16, and 64 MHz. VICE is not UCI evidence.

Every ReadyFS UCI call site carries the nearby contract comment and
`build_support/verify_readyfs_uci_protocol_contract.py` guards the source shape.

## Hardware automation safety

C64 Ultimate REST/FTP work runs only in a genuinely independent
Terminal-owned/background bash, never a foreground Codex curl. Each suite:

1. Creates a unique run id.
2. Creates `/usb1/READYFS_TEST/<run-id>` and/or
   `/sdcard/READYFS_TEST/<run-id>`.
3. Writes a matching ownership marker.
4. Validates normalized prefix and marker before every destructive action.
5. Saves original Ultimate configuration before enabling Command Interface or
   SoftIEC and restores it in every exit path.
6. Preserves roots and evidence by default. Cleanup is explicit and exact-id.

No test may delete, overwrite, format, unmap, or clean up anything outside its
owned roots or a newly generated disposable disk image.

## Verification and completion criteria

Host tests cover path parsing, aliases, image boundaries, normalization,
lengths, globs, filters, quoting, switches, conflicts, plans, dry-run, rollback,
error mapping, and mocked drivers.

VICE covers D64/D71/D81 IEC behavior, shell editing/history/scrollback,
commands, scripts, dry-run invariants, files/types, empty/full/read-only media,
mount-model UI, provisional CMD/SD2IEC semantics, and report generation.

C64U covers owned USB1/SD-card roots, UltimateDOS, SoftIEC, mounted images,
cross-backend files and trees, mount/dismount/swap/map, raw/display names, long
paths, transport recovery, cancellation, and unchanged-state dry runs at
1/16/64 MHz.

Completion requires 25–100 numbered UI cases, screenshots at meaningful
milestones, JSON and Markdown reports, no mutation outside owned roots, clean
host/VICE/protocol gates, successful C64U speed matrix, and a requirement-by-
requirement evidence audit. Provisional SD2IEC/tape behavior must remain
clearly labeled until physical devices are available.

## Current physical flat-copy authority (2026-08-17)

`cross-owned-20260817-iec-udos-roundtrip-k` is the authoritative flat
IEC↔UltimateDOS file matrix. It uses an independently Terminal-owned REST
attachment of a disposable D81, requires fresh exact USB1 and SD owner-marker
reads before every mutation, copies a 4069-byte PRG both ways, preserves type
`$11`, performs backend-neutral length/CRC comparisons, and restores Drive A
exactly. The USB1 test folder is preserved and no host deletion occurs. Never
delete or mutate outside the two exact marker-owned roots.

This closes numbered cases 40/41 but does not close the original scope. The
next physical cross-backend priorities remain UltimateDOS↔SoftIEC flat copy,
recursive nested trees, and mount/map/swap restoration. Typed filesystem
result codes also remain required before batch `expect rc` is semantically
complete.
