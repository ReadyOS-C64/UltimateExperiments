# ReadyFS Agent Safety Note

ReadyFS hardware tests own only newly created per-run directories named
`/usb1/READYFS_TEST/<run-id>` and `/sdcard/READYFS_TEST/<run-id>`. A matching
ownership marker is mandatory before any destructive action. Do not delete,
replace, format, unmap, or clean up anything outside those validated roots.
Run C64 Ultimate REST/FTP work from a Terminal-owned background bash and
preserve test evidence by default.

ReadyFS UltimateDOS and SoftIEC calls must use the proven ReadyIRC/UCI Tester
state-machine transport: quiet-idle synchronization, asynchronous PUSH and
ABORT handling, full response/status draining, DATA_ACC transitions, bounded
failure loops, and final quiet-idle recovery. Validate at 1, 16, and 64 MHz.

Standalone migration (2026-08-20): ReadyFS source, build rules, automation,
documentation, working notes, artifacts, and retained evidence now live below
`UltimateExperiments/ReadyFS`. Build and run from that project root; do not add
new ReadyFS coupling to the ReadyOS Makefile, release disks, source tree, or
logs. Historical evidence retains its original provenance strings. The final
post-migration physical UI run is
`logs/readyfs_c64u/ui-readonly-migration-20260820-ui-final2`; all five read-only
64 MHz cases passed. It did not create, replace, move, or delete any C64U file.
The prohibition on deleting anything outside a marker-owned ReadyFS test root
remains absolute.

Superseding SoftIEC map boundary (2026-08-17): never claim or repeatedly retry
partition-map commands `$20/$21` on firmware 3.14. Current official target-5
source implements only `$01` and `$10`–`$16`. Marker-gated physical runs
`softwrite-noftp-20260817-155612` and `softwrite-noftp-20260817-160912`
returned target status `$01`, added no partition 1, left partition 0 unchanged,
restored Drive A exactly, and mutated no files. Preserve both failed logs and
all artifacts; perform no cleanup. `$01` is the SoftIEC target's status reply,
not a ReadyIRC/UCI transport error. Future map encoding must preserve the live
`/USB1` virtual-root spelling and translate typed PETSCII underscore `$A4` to
host underscore `$5F` only at the SoftIEC boundary. Map/unmap can be promoted
only on firmware/device that actually exposes `$20/$21`.

2026-08-15 hardware discovery: the successful read-only independent Terminal
run is `logs/readyfs_c64u/preflight-20260815-183301`. Hardware reports FTP
roots `USB1` and `SD`, but SoftIEC's internal default path is `/USB0/`; never
conflate the stable ReadyFS logical name with either raw backend spelling.
Command Interface, 16 MB REU, IEC 8 (1581), and SoftIEC IEC 11 are enabled;
the current CPU speed is 64 MHz. No hardware state was changed by preflight.

2026-08-15 UCI finding: on this 64 MHz C64U, a six-byte UltimateDOS directory
block was followed by a MORE->BUSY->MORE transition too short to observe across
ordinary C call/CPU-port mapping overhead. ReadyFS must retain the bounded
adjacent assembly DATA_ACC/transition observer in `readyfs_uci_asm.s`; do not
weaken the contract to treat unchanged MORE as a new block. Also retain the
streaming block callback: one READ_DIR command returns many entry blocks.

Active ReadyFS hardware mutation scope (2026-08-15) is ONLY the two roots from
`logs/readyfs_c64u/owned-roots-readyfs-20260815-190355-79014`:
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`. The matching marker is
`.readyfs-owner-readyfs-20260815-190355-79014`. A prior partial setup created
the separate owned USB1 root ending `190330-78838`; preserve it and do not use
or delete it.

UltimateDOS firmware 3.14 compatibility: `FILE_STAT` reports `82 FILE NOT
FOUND` for some existing long host paths even after parent navigation. ReadyFS
uses parent `READ_DIR` lookup to resolve the exact raw leaf and
`OPEN_FILE`+`FILE_INFO` for metadata; keep the failing and passing evidence in
`ui-readonly-20260815-193851` and its predecessors. Do not reintroduce
`FILE_STAT` as the sole existence oracle.

Passing owned-root 64 MHz mutation evidence is
`logs/readyfs_c64u/owned-mutations-20260815-194141`. UltimateDOS SEQ access is
a text bridge: the host-side FTP representation was uppercase with LF line
endings (`HW ALPHA\n`), although the C64-side reopen/read comparison was exact.
Do not claim SEQ host round trips prove binary fidelity; use PRG/binary-specific
tests for byte-preservation claims.

ReadyFS physical speed evidence: read-only identify and the full multi-block
directory stream pass at 1/16 MHz in
`logs/readyfs_c64u/speed-matrix-20260815-200638`; create, staged write/replace,
append, copy, and move pass at 1/16 MHz in `speed-matrix-20260815-201026` and
at 64 MHz in `owned-mutations-20260815-201654`. Each mutation rechecked the
owned-root marker. The speed wrappers restored the original
`Turbo Control=TurboEnable Bit`, `CPU Speed=64` settings. Keep the first
`speed-matrix-20260815-200251` failure as evidence of the fixed console-summary
clear bug, not as a UCI failure.

Current ReadyFS filesystem-folder testing must remain paused whenever the FTP
ownership marker cannot be fetched and byte-compared. Runs
`owned-mutations-20260815-202509`, `20260815-203032`, and
`20260815-203104` encountered REST/FTP resets and did not prove folder cases;
do not infer success from the C64 being left on an earlier passing screen and
do not bypass the marker gate. Preserve all partial evidence and all files.

The guarded SoftwareIEC suite is
`build_support/run_readyfs_c64u_softiec_owned.sh`. It must only run from its
Terminal launcher, prove partition 250 says `RAW MAPPING: UNMAPPED`, and
revalidate the owned marker before every mutation. Runs ending `215734` and
`215809` passed the FTP marker gate but REST PRG launch reset/timed out; no
partition was mapped and no filesystem mutation ran. Run `215701` was a local
shell failure before hardware and is not a success despite its obsolete
status file. Do not bypass the pre-map check or infer SoftIEC file support.

ReadyFS now also produces an overlay laboratory D81. The proven first sidecar
is `readyfs-match.prg`, loaded at `$B600`, exact-size checked, and cached in REU
with BASIC ROM banked out; VICE evidence is `vice_auto_20260815_215425`.
Current overlay resident BSS ends at `$B1C5`. Keep the monolithic PRG for the
direct REST hardware runner until that runner can supply overlay sidecars.

ReadyFS VICE evidence added after the speed matrix: normalized protected paths
and wildcard matching pass in `vice_auto_20260815_205402`; versioned config
round-trip passes in `205815` and regression `212933`; REU screen scrollback
passes in `210843` and regression `213116`; shared-workspace copy/move passes
in `213052`; latest full smoke passes in `211700`. The standalone memory map
currently ends near `$BEE5`, so future ReadyOS integration needs a real
overlay window below `$C600`. Do not replace the hardware-tested monolithic
PRG until its direct REST launch path can also supply/preload overlay payloads.

2026-08-15 REU/overlay update: use only the centralized allocation constants in
`readyfs_reu.h`. The session bank's live scroll page ends at `$81A8`; config
rollback begins at `$8400`; stage begins `$9000`; serialized plans are
`$A000-$DFEF`. Matcher and planner caches occupy separate `$0000-$0FFF` and
`$1000-$1FFF` slots in the dedicated overlay bank. Sidecar size checks are
safety boundaries, not advisory. Planner ABI/matcher restoration passes VICE
run `vice_auto_20260815_223235`; live flat-IEC filtered planning passes
`vice_auto_20260815_223204`. Nested enumeration and execution remain unproven.

Ultimate recursive dry-run now passes on physical 64 MHz hardware in
`ui-readonly-20260815-230109` (18 files, no child directories, zero completed
actions). The guarded nested fixture runs `recursive-owned-20260815-230322`
and `231705` passed the owner-marker comparison but REST launch reset ten times
before any command. No fixture was created and nothing was deleted. Do not
bypass this gate or retry in a tight loop.

The third overlay is `readyfs-help.prg`; VICE `233214` proves help executes and
matcher operation still works afterward. Current build report ends resident at
`$B4CC` and monolithic at `$C5EE`. With only 17 monolithic bytes left, add no
new resident feature code there; implement remaining work as cooperative
overlay state machines.

The planner sidecar now also contains `readyfs_exec.c` and is `$F0F` bytes.
Its action remains pending until the resident backend acknowledges it; this is
required so each Ultimate action can use one complete resilient UCI
transaction at any CPU speed. Host tests cover copy/move/delete order, replay,
and stop/continue failures; VICE `233651` proves the combined overlay ABI.
Actual recursive backend wiring and journaling are still incomplete.

The help sidecar now also contains the versioned `RFJ1` operation journal and
is `$BAC`. Its fixed session region is `$0900-$1FFF`; never overlap aliases,
scrollback, config staging, or the action plan. C64 journal I/O must call the
fixed REU session functions directly. Nested multi-argument function-pointer
callbacks corrupted cc65 arguments during diagnostic VICE runs; host builds
may retain callbacks. VICE `vice_auto_20260816_005513` proves actual REU
write/read/finish and exposes `JOURNAL: READY`. The plan sidecar now includes a
single INIT/NEXT/ACK dispatcher and is `$FE2`; boot exercises its bounded
gateway rejection in VICE `010809`. Current resident end is `$B5C9` (54 bytes
before `$B600`); monolithic remains `$C5EE`. Treat resident, plan/executor, and
monolithic slices as closed to feature growth; add the backend as a new slice.

`build_support/readyfs_journal_report.py` is the RFJ1 authority for host-side
JSON/Markdown conversion. Keep its strict magic/version/bounds/record/counter
validation and self-test in `readyfs-host-tests`. Do not call case 58 complete
until real executor events are journaled and a captured journal is converted.

Independent-Terminal nested run `recursive-owned-20260816-011419` stopped at
the first safety gate after ten FTP resets. It did not validate the owner
marker, launch ReadyFS, create anything, or issue a delete/dry-run command. Do
not infer hardware state from it and do not retry the C64U in a tight loop.

ReadyFS parses optional IEC partitions such as `11.3:/folder`, but this is a
reserved namespace until a CMD/SD2IEC-capable driver is detected and enabled.
Keep `cd`/`pwd` lossless, and reject directory, metadata, file, and mount I/O
with `partitioned iec driver not enabled` before touching the device. Host
tests and VICE `vice_auto_20260815_233055` prove the parser, range bound, and
capability-honest refusal.

`make readyfs` must keep `artifacts/readyfs/readyfs-build-report.json` and
`.md` passing. The report is the source of truth for current resident end,
monolithic limit, sidecar header/payload sizes, and non-overlapping REU ranges;
do not update memory-map prose from a stale linker map.

Run `make readyfs-ui-report` after meaningful VICE batches. It selects the
latest manifest for each ReadyFS plan and links its retained screenshots; the
current snapshot is 16/16 successful suites, 121 assertions, and 93 retained
screenshots. Do not equate that raw assertion count with numbered UI-matrix
cases.

ReadyFS has a fourth sidecar, `readyfs-backend.prg`, cached only in the
dedicated overlay-bank range `$3000-$3FFF`. Host tests prove canonical request
composition for IEC, IEC partitions, Ultimate image boundaries, and SoftIEC.
The earlier C64 caller-state diagnosis is superseded: address-level probes
proved `sp` stayed `$B5EE`; nested argument repacking had collapsed all REU
cache stores into slot zero. Keep `readyfs_reu_overlay_asm.s` as the flat
six-byte-argument store/fetch boundary and keep `load_cached()` on its one-byte
slot selector. Do not restore the generic five-argument REU call here.
`make readyfs-build-report` runs `verify_readyfs_overlay_dma.py`; keep that
source-shape gate passing whenever the loader, DMA boundary, or slots change.

VICE `vice_auto_20260816_060538` and `060805` prove the full non-NULL backend
pipeline self-test, matcher restoration, help, and later matching. The boot
text `BACKEND: READY` now depends on plan INIT/ADD, executor INIT/NEXT,
IEC-to-Ultimate request composition, RFJ1 INIT/APPEND/FINISH/READ with injected
status 82, and executor ACK after the append. The authoritative map is resident
`$B5D5` (42 bytes before `$B600`), monolithic `$C5C5`, one-pointer
plan/executor `$B39`, help/journal `$BAC`, and backend/controller `$F1F`.
The overlay slots remain matcher `$0000`, planner `$1000`, help `$2000`, and
backend `$3000`, each 4 KB and disjoint. No C64U hardware was touched in this
batch.

`readyfs_pipeline_test.c` is the current semantic contract for cooperative
recursive execution: a serialized plan yields exactly one pending action, the
backend composes canonical endpoint paths, the simulated resident result is
written to RFJ1, and only then is the action acknowledged. It proves a failed
Ultimate target status remains replayable and `onerror continue` advances.
This is host evidence only; do not describe recursive mutation as enabled on
the C64 until a real resident-I/O result replaces the injected status. The
cross-overlay sequence itself is now C64-proven by `060538`/`060805`.
The backend capability dispatcher is also host-tested for tape and alias
rejection, but it has no resident command hook yet: the first hook exceeded
the `$B600` boundary by 100 bytes and was withdrawn. Expose it through the
future controller overlay; do not spend resident bytes on a standalone hook.

The C64 planner and executor now use one-pointer dispatch all the way down;
do not restore nested calls to six-argument `readyfs_plan_read`. The resident
`readyfs_overlay_nested_from_backend` gateway must restore backend code before
returning to its overwritten caller. `make readyfs-build-report` runs
`verify_readyfs_pipeline_contract.py` to guard journal-before-ACK ordering and
these source boundaries. The stackless walker remains covered by host tests
but is not presently linked into the `$B39` C64 plan/executor sidecar.

VICE `vice_auto_20260816_071749` proves the first real overlay-controller file
action: disposable IEC copy, stat, byte comparison, post-journal matcher, and
post-IEC matcher all pass. Its full REU dump converts to a finished RFJ1 record
for successful `copy-file` stem `8:/RFMATCH`. Use numeric ASCII bytes for RFJ1
magic; cc65 character literals produce PETSCII.

Never call KERNAL/device I/O while the caller/return address is in the shared
overlay window. Resident code owns I/O, using static one-pointer control
records instead of large cc65 software-stack locals. Overlay-to-resident REU
session store/fetch must stay in `readyfs_reu_overlay_asm.s` beside cache DMA;
the old three-argument C boundary corrupted the matcher cache. Keep both flat
six-byte contracts enforced by `verify_readyfs_overlay_dma.py`.

Current map is resident `$B54D` (178 bytes before `$B600`), monolithic `$C52F`,
matcher `$4D1`, plan/executor `$B39`, help/journal `$C93`, and backend `$F12`.
The C64 capability dispatcher is intentionally omitted until it has an
exposed overlay path; the host capability model/tests remain authoritative.

Executor milestone `vice_auto_20260816_074649` supersedes the preceding map
and action evidence. A real resident staged IEC copy now follows
`BEGIN -> pending COPY_FILE -> resident I/O -> finished RFJ1 -> ACK`, then the
plan overlay writes fixed record `RFA1` at session-relative `$8300` (physical
bank-255 `$A300`). `readyfs_action_report.py` must continue rejecting bad
magic, inconsistent totals, non-finished pending state, or anything other
than exactly one attempted action. That run reports RFJ1 success and RFA1
attempted/completed/failed/pending `1/1/0/0`.

Do not put a `char suffix[12]` software-stack local back into
`make_temp_stream`. Once executor orchestration reduced the free resident
ceiling, the nested `sprintf` call crossed into resident BSS and stalled IEC
copy. The safe implementation borrows `io_buf` for the suffix before any file
transfer begins. Breakpoint diagnostics `073244` through `074211` proved the
backend gateway itself preserved cc65 `sp`; `074418` and `074649` prove the
scratch-buffer correction.

The current authoritative build report is resident `$B5BA` (69 bytes before
`$B600`), monolithic `$C53F`, matcher `$4D1`, plan/executor `$FDF`,
help/journal `$FF9`, backend/controller `$FE0`, CMD path `$FD0`, and drive
profiler `$A8C`. Session REU `$0888-$08E3` holds 23 marked per-device profile
records; boot clears them only after the drive ABI passes. Session
`$8200-$83FF` is reserved for the action checkpoint plus RFA1; config backup
still starts at `$8400`. Treat all six sidecars and resident memory as closed
to casual growth, and rerun the build report plus the real pipeline after any
relevant change.

`readyfs_cmdpath.c` is the host-proven CMD/SD2IEC translation authority. Native
rename syntax is `R:new=old`; never reverse it. Image mount uses an absolute
partitioned `CD`, while reliable unmount is two commands (`CD//`, then `CD`
plus PETSCII back-arrow `$5F`). Canonical `!` image-contained access must stay
rejected until a controller can mount, operate, and restore device state as one
transaction. A broad resident-only cache/dispatch trial overflowed `$B600` and
was withdrawn. The replacement caches `$FD0`-byte `RFCMDPATH` at REU
`$4000-$4FFF`, performs its boot self-test, and exposes all eight translations
through a help-sidecar UI plus a nested one-pointer gateway. Do not
claim translated command execution yet. The general diagnostic gateway is
callable, but it only returns/prints strings. `probe iec DRIVE:` does perform
real resident-owned command-channel identity I/O; `RFDRIVE` only parses,
classifies, and renders the reply. Current map is resident `$B5B8` with 71
bytes free, help/journal `$FF9`, CMD path `$FD0`, and drive profiler `$A8C`;
all are closed to casual growth.

Do not reintroduce the direct resident `native OP PATH` implementation. Its
measured build overflowed `$B600` by 486 bytes and was fully withdrawn. Put
the translation diagnostic/parser in the help sidecar, keep its mutable call
record in resident scratch, and add only a one-pointer nested gateway that
loads CMD path and restores help before returning. The same nested-lifetime
rule used by backend applies: no return address or mutable record may remain in
the overwritten shared window.

VICE `082858`/`084104` proved C64 native command prefixes must use unshifted
cc65 literals (lowercase source spelling), while uppercase source literals
produce shifted PETSCII and can display as `.`. Keep host prefixes uppercase
ASCII and cc65 prefixes unshifted via the `RF_NATIVE_*` macros. The boot
self-test inputs must remain keyboard-equivalent rather than sharing the same
bad shifted encoding. Callable suite `090349` and pipeline regression `090503`
are the current authorities.

Independent SoftIEC run `softiec-owned-20260816-075039` failed at the very
first owner-marker FTP gate with ten connection resets. It executed no launch,
map, filesystem command, or mutation. Retain the logs and do not tight-loop
retries; every later mutation attempt still requires a fresh exact marker
round trip in the Terminal-owned/background harness.

The later independent retry `softiec-owned-20260816-091304` failed at the same
first marker gate with ten FTP connection resets and an empty results table.
It made no launch, map, configuration, filesystem, or mutation call. Do not
tight-loop another attempt; continue local/VICE work and require the same exact
fresh marker gate whenever hardware connectivity is next revisited.

Driver/profile detection is capability evidence, never authorization. The
host classifier recognizes SD2IEC, CMD, Pi1541, Ultimate, SoftIEC, legacy, and
unknown replies and returns partition/folder/image flags. `RFDRIVE` is cached
at overlay-bank `$5000-$5FFF`; it must not contain `cbm_` or UCI calls. Only
resident `probe_iec_io()` may touch channel 15, and the wrapper must restore
the matcher afterward. VICE `100352` is the authority for
`73,VIRTUAL DRIVE EMULATION V3.5,00,00` -> `LEGACY P0 F0 I0`; `100428` proves
the real copy/RFJ1/RFA1 pipeline afterward. UI inventory is 17/17 and 135
assertions. Do not enable partition paths or issue translated mutations until
a compatible detected profile and a disposable-device test gate both pass.

The newer profile authority is VICE `101151`: device 9 is deterministically
`UNPROBED`, device 8 survives a clear-and-query round trip as
`LEGACY P0 F0 I0`, and legacy mount is denied without I/O. The pure operation
matrix grants open/scratch with `P`, folder operations with `P+F`, and image
mount/unmount only with `P+F+I`. Pipeline `101231` remains green; inventory is
17/17 with 139 assertions. Hardware run `softiec-owned-20260816-100658`
failed safely at the marker FTP gate with zero cases and no launch/map/I/O.
Do not retry it in a tight loop.

The action controller is no longer copy-only. It supports the exact contiguous
range mkdir/copy/move/delete/rmdir, derives plan kind and mode, checkpoints
pending state, writes RFJ1 before ACK, rejects duplicate ACK, and emits RFA1.
`PLANNER: READY` depends on a cc65 boot self-test of all five actions. Normal
overlay copy/move/delete/mkdir/rmdir commands must use resident
`action_begin()` before I/O and `action_complete()` afterward; move completes
only after source deletion succeeds. Structural verification guards all five
hooks. VICE `112225` is the real copy/move/delete authority and its final REU
reports `delete-file 8:/RFMOVED` plus RFA1 `1/1/0/0`; `111729` is the copy
regression. Inventory is 18/18 with 148 assertions. Do not claim real
mkdir/rmdir I/O until a folder-capable disposable backend passes.

Do not cite `preflight-20260816-112357` as successful FTP evidence. The old
preflight lacked `set -e`, so empty/reset FTP calls were masked by its final
successful manifest write. The script now uses strict mode, bounded retries,
`--list-only`, and nonempty gates. Corrected true Terminal run `113019` proves
all nonempty REST reads but fails honestly after ten FTP root-list resets;
SoftIEC run `112412` fails at exact marker RETR with zero cases and no
launch/map/I/O/mutation. Keep the marker gate intact and do not tight-loop.

The current partition-command authority supersedes the earlier “translation
only” note. Normal overlay `mkdir` and forced `rmdir` now resolve aliases,
require a marked per-device profile with `P+F`, translate through RFCMDPATH,
perform only resident-owned channel-15 I/O, and complete through the existing
RFJ1-before-ACK/RFA1 controller. A legacy/unprobed profile stops before BEGIN
and I/O. VICE `121327` proves direct and alias-resolved denial plus all native translations/matcher
restoration; `120846`, `120942`, and `121013` are the action, real-copy, and
flat-command regressions. Inventory is 18/18 with 151 assertions.

Keep the outer partition command record in resident `dest` (`drive_command`),
with `backend_call` and `backup` as separate backend/action workspaces. Never
move it into `readyfs_pipeline_scratch`: backend dispatch overwrites that
scratch. A CMD-path call returning to help must restore help and immediately
return; generic backend fallthrough overwrites the caller's return path.
Native translation output/follow-up must use the two 256-byte stream canonical
buffers, never the small IEC/UCI transfer scratch.

Authoritative map: resident `$B5AB` (84 bytes free), monolithic `$C265`,
matcher `$4D1`, planner/executor `$FDF`, help/journal `$FF9`, backend `$FE0`,
CMD path `$FD0`, drive/controller `$F85`. Transfer chunks are deliberately
32-byte file/IEC and 64-byte UCI capture buffers; loops and the UCI transport
still drain complete operations. No physical compatible-folder execution is
claimed. Never weaken the marker check, and never delete or mutate anything
outside the two marker-owned ReadyFS roots.

Partitioned normal `dir` now shares the profile/translation bridge and returns
to resident `dir_iec`; it must not enter the mutation journal. VICE `122410`
is the current authority for direct/alias mkdir denial plus alias directory
denial and all translation/restoration checks. Action/copy regressions are
`122455` and `122520`; boot-memory regression is `122619`. Inventory is 19/19
with 154 assertions.

Treat `$B5AC` as the hard KERNAL scratch boundary, regardless of the nominal
linker space through `$B5FF`. Runs `121620`/`121741` ended BSS at `$B5EB` and
crashed during sidecar disk loading; delayed capture `122154` recorded PC
`$0009` and overwritten resident tail from `$B5AC`. The generated build report
must keep `resident_below_kernal_scratch` green. Current authoritative map is
resident `$B59E` with only 13 safe bytes, monolithic `$C21D`, matcher `$4D1`,
planner/executor `$FDF`, help/journal `$FF9`, backend `$FE0`, CMD path `$FD0`,
and drive/controller `$FBE`. All resident and sidecar regions are closed to
casual growth.

Fresh independent Terminal preflight `preflight-20260816-1228-final-local`
proves current REST reachability (seven nonempty documents) but FTP root list
still resets ten times; strict status is `failed:1`. It performed no launch,
mapping, configuration change, marker bypass, or storage mutation. Do not
tight-loop and do not start mutation automation until an exact marker RETR
succeeds in a fresh Terminal-owned run.

Normal partition file delete now joins dir/mkdir/rmdir in the profile-gated
bridge. Keep its exact order: recursive refusal and filter, dry-run, alias/path
resolution, mandatory `--force`, cached capability authorization, RFCMDPATH
SCRATCH translation, DELETE_FILE BEGIN, resident-only channel-15 I/O, then
COMPLETE/RFJ1-before-ACK/RFA1. VICE `123243` proves no-force and legacy-profile
denial without I/O; it is not compatible-device execution evidence.

Current authority after delete integration is `make readyfs`, pipeline guard,
overlay DMA guard, and UCI verifier all passing; VICE command path `123243`,
actions `123329`, copy/RFJ1/RFA1 `123405`, and boot-memory `123448` all pass.
UI inventory is 19/19 with 156 assertions. The map is resident `$B5AA` (only
one safe byte before hard KERNAL scratch `$B5AC`), monolithic `$C21D`, matcher
`$4D1`, plan `$FDF`, help `$FF9`, backend `$FE0`, CMD path `$FD0`, and drive
`$FFC`. Do not add resident or sidecar-6 code without first reclaiming space.

Partition rename now uses the normal bridge with both aliases resolved into
separate 256-byte resident buffers. It requires force plus `P+F`, translates
`R:new=old`, maps to MOVE_FILE, and keeps RFJ1-before-ACK/RFA1 around the
resident channel-15 command. Never remove `drive_command.followup =
backup.canonical`: compatible rename translation needs that full workspace
even though legacy-profile VICE denial occurs before translation.

Partition image mount is now a capability-gated single-command route. Syntax
is `mount UNIT.PART:/path/image.dxx --force`; require `P+F+I`, RFCMDPATH `CD`
translation, and resident-only command-channel I/O. It is not a file action and
must not be mislabeled in RFJ1/RFA1. SD2IEC/CMD unmount now performs `CD//`
and exactly one `CD`+back-arrow follow-up through the same resident primitive.
Keep the operation check, success check, nonempty follow-up check, pointer
clear, second I/O, and only then COMPLETE; never issue only `CD//`.

Current authority is command path `125444`, actions `125544`, copy/RFJ1/RFA1
`125610`, boot-memory `125645`, and 19/19 suites with 162 assertions. Failed
`124914` proves ASCII-style `| 32` folding is invalid here; keep explicit cc65
folding. Current map is resident `$B592` (25 safe bytes), monolithic `$C107`,
matcher `$4D1`, plan `$FDF`, help `$FF9`, backend `$FE0`, CMD path `$FD0`, and
drive `$FFB`. No compatible hardware execution or storage mutation is claimed.

The stackless multi-entry controller is now live in overlay 1. State is
checkpointed at session `$8E00-$8EFF`, canonical roots at `$9988-$9B87`, and
actions follow `NEXT -> resident device I/O -> RFJ1 append -> executor ACK`.
Never place the outer call record in `readyfs_pipeline_scratch` because the
controller owns that 259-byte scratch; resident currently overlays it on
`alias_slot` and reconstructs the record around every I/O. C64 RFJ1 INIT must
set `readyfs_reu_session_store/fetch` callbacks explicitly.

VICE `vice_auto_20260816_132123` was the first real recursive batch run. Its
copy/move/delete and exact two-event RFJ1 evidence is retained historically;
the superseding authority below adds C64 stop/continue policy and the corrected
software-stack contract. Keep all overlay regions closed to casual growth.

Superseding recursive batch authority is `vice_auto_20260816_140348`: 60
steps/27 assertions pass real filtered IEC8→IEC9 copy+compare, move/delete,
default stop after a declined conflict, and a later `--continue` mixed-result
batch in the same C64 session. Exact RFJ1 reports are 2 completed/0 failed for
`RFZA`,`RFZB`, then 1 completed/1 failed for `RFCA`,`RFCB`. Inventory is 20/20
with 191 assertions; UI matrix case 57 is proven and the total is 35/60.

Critical linker lesson: C64 crt0 sets cc65 `sp` from `__MAIN_START__ +
__MAIN_SIZE__`. In an overlay build, never end `MAIN` at `$B600`; doing so
makes deep calls overwrite resident BSS below the overlay. ReadyFS overlay
`MAIN` must extend to `__HIMEM__` so stack top is `$D000`, while resident BSS
continues to stop below `$B600` and sidecars own `$B600-$C5FF`. The build
report/verifier enforce this. Current map is resident `$B59B` (16 bytes before
hard `$B5AC`), monolithic `$BB08`, overlay1 `$FE3`, plan `$FDF`, help `$FF9`,
backend `$FE0`, CMD path `$FD0`, drive `$FFB`. Do not delete the post-stop
capability-memory diagnostic from the recursive UI plan unless an equivalent
stack-regression assertion replaces it. No hardware mutation was attempted.

Large directories now use one shared IEC/Ultimate 18-line pager. At each
`-- MORE --`, keep the order `cgetc()` → `scroll_store_page()` → `clrscr()`;
do not restore an arbitrary display-only entry cap. VICE authority
`vice_auto_20260816_141948` proves all 48 D81 entries through F40, exact free
blocks, two saved REU pages, and return to live with F1/F3. The physical
read-only UI harness must keep its bounded 32-page acknowledgement guard so
UltimateDOS listings do not stall the speed matrix. Inventory is 21/21 with
203 assertions, and UI case 31 brings the proven total to 36/60.

Current map after paging is resident `$B565` (70 bytes before hard `$B5AC`),
monolithic `$BAD2`, cc65 stack top `$D000`, and sidecars `$FE3`, `$FDF`,
`$FF9`, `$FE0`, `$FD0`, `$FFB`. `make readyfs`, UCI contract, overlay DMA,
and pipeline contract pass. Independent Terminal preflight
`preflight-20260816-1421-pagination` read all seven REST documents but FTP
root listing reset ten times and status is `failed:1`; no marker bypass,
launch, feature/configuration call, filesystem command, or mutation occurred.
Do not tight-loop. Never delete or mutate outside the exact marker-owned USB1
and SD roots, and never proceed without re-reading the ownership marker.

Disposable regular-floppy authority is `vice_auto_20260816_142523`: one C64
session boots ReadyFS from D71/1571 unit 8 and queries a D64/1541 on unit 9.
Both `dir` and `volume` agree on names and free space: D64 is 664 blocks, D71
is 1157 blocks, proving the latter is not truncated to eight bits. UI cases 29
and 30 are proven; current inventory is 22/22 with 210 assertions and 38/60
numbered cases. Regenerate these disposable images only with
`run_readyfs_vice_floppy_formats.sh`; they are not C64U-owned-root fixtures.

REL rejection authority is `vice_auto_20260816_143000`. Copy must perform a
read-only source open/close preflight before `stream_exists(&dest)`; this makes
IEC/SoftIEC REL rejection occur before destination probing or replacement.
Keep the structural verifier's source-preflight → close → destination-probe →
actual-source-open → staged-destination-open order. `142842` is a retained
diagnostic showing why destination-first ordering is wrong. Current map is
resident `$B583` (40 bytes before `$B5AC`) and monolithic `$BAF0`; inventory is
23/23 with 215 assertions and 39/60 numbered cases. Post-fix regressions
`vice_auto_20260816_143116` and `143137` pass staged copy/move and overlay
copy with RFJ1/RFA1.

Disk-full replacement rollback authority is `vice_auto_20260816_143517`.
Its disposable target begins with 134 free D64 blocks; forced copy fails after
34,016 bytes, the original remains byte-identical, and the final image has the
same five entries/134 blocks with no `RF~xx` stage. The runner must keep its
post-VICE `c1541` oracle as well as the C64 assertions. Case 45 is proven;
inventory is 24/24 with 222 assertions and 40/60 numbered cases.

Recursive delete must enumerate and display its plan, then require confirmation
before `RF_RECURSIVE_CALL_START`. Default `N` preserves the selection;
`--force` or `--yes` bypasses the prompt. `--yes` is implemented centrally in
`option_present()` as the alias for `--force`; do not reintroduce duplicated
checks in media/map commands. Authority is `vice_auto_20260816_144213`, with
full recursive/capability regression `144440` and command-path regression
`144704`. Capability memory addresses for that historical map were
`$B129-$B12A` and `$B58D-$B592`. Current resident was `$B598` (19 bytes before `$B5AC`),
monolithic `$BADF`; inventory is 25/25, 229 assertions, and 41/60 cases.

IEC drive discovery must not open a full DOS command channel for every absent
unit. Diagnostics `vice_auto_20260816_144932` and `145231` exceeded 60/180
seconds after finding 8/9. Use the KERNAL `LISTEN` -> `READST` -> `UNLISTEN`
presence handshake and interpret ST bit 7; real operations still open normal
channels. Strict authority `vice_auto_20260816_145814` proves scan 8-30,
mounted units 8/9, tape capability, and prompt return. The structural verifier
locks this down. Current build is resident `$B581` (42 bytes before `$B5AC`),
monolithic `$BAC8`, stack `$D000`; inventory is 25/25 with 234 assertions and
42/60 cases. The ld65 map parser must find exported symbols in either packed
column, not only at line start. No hardware access or mutation was used.

`stat` metadata authority `vice_auto_20260816_150616` proves a real IEC PRG
prints distinct display/raw fields, type `$11`, and an explicitly estimated
C64-block size. Ultimate FILE_INFO is labeled exact bytes in the guarded code,
but case 33 remains partial until raw host naming is implemented outside the
resident and physically rerun. Do not restore the rejected resident raw-name
rescan: it crossed `$B5AC` by 73 bytes. Current accepted map is resident
`$B57F` (44 safe bytes), monolithic `$BAC6`, stack `$D000`; inventory is 25/25
with 237 assertions and still 42/60 proven cases. No hardware access occurred.

After the discovery/stat layout changes, the exact recursive memory oracle is
session flags `$B110-$B111` and six overlay flags `$B574-$B579`. Diagnostic
`vice_auto_20260816_151705` passed all 60 UI steps but correctly rejected the
old fixed slices; authority `152157` passes UI, RFJ1 analysis, and exact bytes.
Do not revert the YAML to the historical addresses or broaden it into a search.

Audit result: `--native-pattern` is documented but not implemented; case 24 is
not proven. Do not squeeze it into the 44-byte resident margin. Extend overlay
5 (`RFCMDPATH`) by compacting its 219-byte runtime selftest to a small boot ABI
probe, retaining host tests/callable CMD-path VICE coverage, then add read-only
legacy IEC `$:pattern` translation through resident scratch. Prove directory
forwarding/rejections before enabling any mutation pattern; mutations require
WhatIf enumeration and confirmation first.

The first read-only native-pattern route is now implemented. Overlay 5 accepts
only absolute unpartitioned flat IEC patterns of at most 16 characters with
`*` or `?`, emits `$:PATTERN`, and overlay 6 returns to resident `dir_iec()` for
all KERNAL I/O. Focused authority `vice_auto_20260816_155612` rejects an
unflagged `dir 8:/RF*`, then lists the six `RF*` sidecars plus matching header
(`ENTRIES: 7`) and rejects a non-pattern; full command-path `155630` passes 83
steps/33 assertions. Host and structural
tests enforce endpoint/partition/image/flat/length/capacity checks and the
resident-owned listing route.

Do not use ASCII `| $20` to fold drive-UI command input. cc65 literals are
PETSCII; diagnostics `154556`/`154641`/`154715` showed every normal `IEC`
query missing. Keep `FOLD_CHAR(value) = value & $7F`. Current strict map is
resident `$B5A8` (three safe bytes before `$B5AC`), monolithic `$BAA8`, stack
`$D000`, sidecars `$FE3/$FDF/$FF9/$FE0/$FFD/$FFF`. Exact recursive authority
`155730` uses session flags `$B139-$B13A` and overlay flags `$B59D-$B5A2` and
passes all 60 steps plus the post-STOP byte oracle. Inventory is 26/26 suites,
246 assertions, 43/60 proven cases.

Case 24 is proven: unflagged non-root IEC `dir` is rejected, and only the
explicit native flag forwards the pattern. Native pattern copy/delete/move
remain off until WhatIf enumerates the full target set and confirmation
precedes mutation.
All work above used disposable VICE images; no hardware access or mutation was
performed. Never delete or mutate outside
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`, and require marker
`.readyfs-owner-readyfs-20260815-190355-79014` from a fresh Terminal-owned
preflight first.

Native action design is fixed in `docs/READYFS_PATH_RESEARCH.md`.
Never issue `S:PATTERN` or any wildcard mutation. Read-only native directory
enumeration must freeze every exact returned filename/type into the existing
REU plan, fail the entire plan on entry-limit truncation, apply optional shell
filters afterward, print all exact WhatIf targets, then execute only ordinary
exact-name staged copy/move/delete actions with RFJ1-before-ACK. Newly matching
files after confirmation are not included. Multi-source copy/move requires a
directory destination; the first generation rejects directories and REL
transfers before mutation. Intended syntax does not require the user to add
`--recursive`; reuse of the batch controller is an internal detail.

The first integrated native-action WhatIf attempt was rejected, not shipped.
It ended at resident `$B5F6`, 75 bytes beyond strict `$B5AC`, even after fetch
consolidation. Do not restore it inline. The retained gateway refactor masks
the nested operation once and routes shared-window loads through
`fetch_cached()`. Current accepted map is resident `$B529` (130 safe bytes),
monolithic `$BAA8`, stack `$D000`, sidecars
`$FE3/$FDF/$FF9/$FE0/$FFD/$FFF`. Authorities are native `160722`, command
path `160730`, and recursive `160831`; current exact memory slices are session
`$B0BA-$B0BB` and overlays `$B51E-$B523`. Native mutations and native action
WhatIf remain unavailable until the admission/enumeration path is split
cooperatively. No C64U access or storage/config mutation occurred.

The complete generated case authority is
`artifacts/readyfs/readyfs-ui-case-report.md`/JSON. Case 25 is proven by
`vice_auto_20260816_161342` (`probe uci` reports absent and returns to the
prompt). Cases 5/6 are proven by `vice_auto_20260816_161744`: the viewport
shows `READYFS255END`, the exact monolithic `$B069-$B168` dump contains
255 entered bytes plus NUL, Enter reaches the parser, and editor regressions
7-10 remain green. The runner must keep the exact byte oracle, not just the
screenshot. Current inventory is 26/26 suites, 250 assertions, 46 proven,
10 partial, and 4 missing cases. This work used only disposable VICE media;
no C64U access or storage/config mutation occurred.

Native-pattern WhatIf is now live; native mutation is still off. The accepted
cooperative split keeps IEC enumeration resident and moves admission,
include/exclude matching, exact-name recursive-plan insertion, typed target
display, and summary rendering into backend overlay 4. Authority
`vice_auto_20260816_165721` uses the literal `--whatif` spelling, lists six
exact `RF*` PRGs, filters delete to `RFDRIVE`, reports zero completed
mutations, denies a non-dry native delete, and proves `RFDRIVE` still exists.
Never replace this with raw wildcard scratch/write/rename. Future execution
must confirm and consume the frozen exact-name plan with RFJ1-before-ACK.

Current authorities are command path `165229`, recursive/RFJ1/capability
`165148`, and native WhatIf `165721`. Exact capability addresses are
`$B138-$B139` and `$B59C-$B5A1`. Strict layout is resident `$B5A7`
(4 safe bytes), monolithic `$BAA8`, stack `$D000`, sidecars
`$FE3/$FDF/$FF9/$FF0/$FFD/$FFF`. The backend boot check is now ABI plus a
compact build probe; real VICE action/RFJ1 suites are the end-to-end authority.
Generated status is 26/26 suites, 258 assertions, 46 proven, 10 partial, and
4 missing cases. No C64U access or storage/config mutation occurred.

Native-pattern exact-name mutation is now available only through explicit
`--apply`. Bare `--native-pattern` remains denied even with `--force`/`--yes`;
`--whatif` remains zero-write. The applying invocation performs a read-only
`$:PATTERN` directory query, prints and freezes the exact names in REU, then
executes only those exact names through the recursive RFJ1-before-ACK loop.
Never replace this with `S:PATTERN` or any wildcard write/rename/scratch.

Authority `vice_auto_20260816_170718` uses fresh local VICE D81s and proves
singleton delete (`RFNX1`), IEC8→IEC9 two-file copy (`RFNC1`, `RFNC2`) with
byte comparison, and IEC8→IEC9 move (`RFNM1`) with source/destination
postconditions. Parsed REU journals are FINISHED: copy mode 1 has two success
records at plan offsets 0/12; move mode 2 has one success record at offset 0.
The native plan has 58 steps/28 assertions; aggregate inventory is 26/26,
273 assertions, 46 proven, 10 partial, 4 missing.

Current strict map after native apply/help discovery is resident `$B5A7`
(4 bytes before `$B5AC`), monolithic `$BAA8`, stack `$D000`, and sidecars
`$FE3/$FDF/$FFC/$FFF/$FFD/$FFF`. Backend overlay 4 has only one byte free;
recover measured space before adding policy. No physical C64U access or
mutation occurred. The only authorized hardware mutation roots remain exactly
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`, each requiring a fresh
exact owner-marker preflight in Terminal-owned/background bash.

Native whole-plan admission authority now supersedes the prior map notes.
`vice_auto_20260816_171906` adds regular-IEC collection-destination rejection
(`9:/OUT` is `BAD DEST`) while retaining exact WhatIf and applied delete/copy/
move plus parsed RFJ1. `vice_auto_20260816_171852` uses the real D71
`CAL26CFG.REL` `$13` entry and proves native selection rejects it as
`UNSUPPORTED` with no destination. Only SEQ/PRG/USR enter a native action plan.

Current regression authorities are recursive `171947` (60/27 plus RFJ1 and
post-STOP capability oracle), command path `170922` (83/33), native action
`171906` (61/29), and native type gate `171852` (9/4). Exact capability bytes
are now `$B12E-$B12F` and `$B592-$B597`. Strict layout is resident `$B59D`
(14 bytes before `$B5AC`), monolithic `$BA74`, stack `$D000`, sidecars
`$FE3/$FDF/$FFC/$FF8/$FFD/$FFF`. Generated inventory is 27/27 suites, 278
assertions, 46 proven, 10 partial, 4 missing.

No physical C64U access or mutation occurred during this milestone. Continue
to restrict hardware mutation to the two exact marker-owned USB1/SD roots and
require a fresh exact marker check from Terminal-owned/background bash before
every destructive physical run.

Latest physical preflight is
`logs/readyfs_c64u/preflight-20260816-resume-172314`. It ran in a real
Terminal-owned shell, captured all seven REST/config documents, then failed
honestly with `failed:1` after ten FTP root-list connection resets. It made no
launch, key injection, configuration/feature change, mapping, filesystem I/O,
or mutation. Do not tight-loop. Physical mutation remains forbidden until a
new Terminal-owned run retrieves and compares both exact ownership markers.

ReadyFS now has a seventh cached sidecar, `rfutil`, at overlay-bank
`$6000-$6FFF`. It owns mutation WhatIf rendering and explicit oldest-to-newest
REU `history` listing; future cooperative tree/batch control belongs there,
while all IEC/UCI device I/O remains resident. Build authority is resident
`$B3EE` (445 safe bytes before `$B5AC`), monolithic `$BF4E`, stack `$D000`,
sidecars `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$6E9`.

Runtime utility authority is `vice_auto_20260816_173129`; recursive/RFJ1 and
seven-sidecar capability authority is `vice_auto_20260816_173239`. Exact
current diagnostic bytes are session `$AF7E-$AF7F` and overlay flags
`$B3E2-$B3E8`; do not restore historical addresses. Generated inventory is
28/28 suites, 287 assertions, 46 proven, 10 partial, 4 missing.

`docs/READYFS_SCOPE_AUDIT.md` is the broader completion checklist.
The original plan still requires dispatched `capabilities`, `status`, `tree`,
`find`, `head`, `tail`, `crc32`, `format`, `run`, and `test`, in addition to
nested cross-backend and physical evidence. Do not equate the 60-case matrix
with complete original scope.

ReadyFS now has an eighth cached sidecar, `rftree`, at overlay-bank
`$7000-$7FFF`. It is a cooperative breadth-first controller only: all IEC/UCI
device I/O stays resident and Ultimate directory reads continue to use the
ReadyIRC-derived asynchronous state machine. Its control checkpoint is at
session `$8F00-$8FFF`; its queue must use overlay-bank `$8000-$FFEF`. Do not
move the queue back to session-relative `$E000`: the session API ends at
`$DFEF`, and VICE proved that invalid map makes `INIT` return `TREE OFF`.
Runtime authority is `vice_auto_20260816_175239`, which reaches the resident
UCI yield and honestly reports `TREE FAILED F0 D0` in UCI-less VICE. Build
authority is resident `$B592` (25 bytes before `$B5AC`), monolithic `$BFED`,
sidecars `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$85A/$AD9`. Recursive authority
`vice_auto_20260816_175442` uses current session flags `$B121-$B122` and seven
overlay capability flags `$B586-$B58C`, all `01`. `tree` is now dispatched for
UltimateDOS, but SoftIEC/CMD/SD2IEC adapters and physical nested proof remain
pending; `capabilities`, `status`, `find`, `head`, `tail`, `crc32`, `format`,
`run`, and `test` are still undispatched.

The resident SoftwareIEC tree adapter is now implemented. It capability-gates
UCI, converts the canonical `sN:/...` request to the native `$sN:/...` IEC
directory spelling, and feeds resident `cbm_opendir/readdir` results to the
same `rftree` controller. `rfutil` now also renders resident drive-scan results
and owns 16-bit decimal formatting. Runtime authority
`vice_auto_20260816_180719` proves drive/tape output, formatted D81 directory
values, Ultimate's bounded no-UCI tree failure, and honest `SOFTIEC OFF` for
`tree s3:/`; it is not physical mapped-folder proof.

Overlay resident alias scratch and staged-backup stream now share one guarded
workspace. Their lifetimes are exclusive only because the recursive outer
call has its own distinct resident record; never alias that call back onto
alias/backup storage. Current build authority is resident `$B51F` (140 bytes
before `$B5AC`), monolithic `$C22F`, sidecars
`$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$AAC/$AD9`. Recursive authority
`vice_auto_20260816_180815` uses session flags `$B1A1-$B1A2` and seven overlay
flags `$B513-$B519`, all `01`. Physical SoftIEC nested enumeration, CMD/SD2IEC
tree adaptation, cross-backend tree actions, and 1/16/64 MHz proof remain
pending behind the exact marker gate.

`tree 8:/` now provides the successful non-UCI runtime oracle. It accepts only
the flat unpartitioned regular-IEC root, leaving CMD/SD2IEC nested syntax to the
profile translator. VICE `vice_auto_20260816_181108` enumerates the nine files
on the overlay D81 and reports exactly `TREE DONE F9 D0`; retain
`screens/readyfs_tree_iec_flat.png`. Current build authority is resident
`$B57B` (48 bytes before `$B5AC`), monolithic `$C22F`, sidecars
`$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$AAC/$AD9`. Current recursive authority is
`vice_auto_20260816_181146`; diagnostic bytes are session `$B1FD-$B1FE` and
seven overlay flags `$B56F-$B575`, all `01`. The 28 latest UI plans are all
successful; numbered scope remains 46 proven, 10 partial, 4 missing.

Current authority supersedes those layout addresses. Build report:
resident `$B590` with 27 bytes before `$B5AC`, monolithic `$C244`, stack
`$D000`, sidecars `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$AAC/$AD9`. Current
recursive run is `vice_auto_20260816_184011`; session flags are
`$B212-$B213 = 01 01` and the seven overlay flags are `$B584-$B58A = 01`.
Current UI regressions are config `182919`, copy/move `182951`, append
`183209`, and replacement rollback `183813`. Rollback free-space assertions
must remain fixture-derived: the current artifact seeds 113 free blocks and
the test proves exactly 113 both before and after the failed staged copy; do
not restore the obsolete literal 134.

Latest true Terminal-owned C64U preflight is
`logs/readyfs_c64u/preflight-20260816-resume-physical-181348`. REST succeeded
and recorded firmware 3.14, 16 MiB REU, enabled UCI, 64 MHz, SoftIEC bus 11 at
`/USB0/`, and drive A as bus 8/1581. FTP root listing reset on all ten bounded
attempts, status `failed:1`, so no launch, mapping, config write, filesystem
I/O, or mutation followed. Do not tight-loop. Any physical mutation still
requires a fresh exact marker round trip for both owned roots:
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`, marker
`.readyfs-owner-readyfs-20260815-190355-79014`. Never delete outside them.

Generated evidence is 28/28 successful VICE suites, 293 assertions, 46
proven numbered cases, 10 partial, and 4 missing. `tree` is dispatched for
UltimateDOS, SoftwareIEC, and flat regular IEC; the older line saying it is
undispatched is historical. CMD/SD2IEC nested traversal, real cross-backend
nested actions, physical UCI recovery at 1/16/64 MHz, and commands
`capabilities`, `status`, `find`, `head`, `tail`, `crc32`, `format`, `run`,
and `test` remain pending.

Superseding command architecture: all command-name and short-alias decoding is
now in `rfutil`; resident receives a numeric command ID. Never move the packed
name table or `same_word(args[0], ...)` chain back into resident RAM. This
reclaimed 732 bytes: current resident end is `$B2B4`, 759 bytes before
`$B5AC`; monolithic end is `$C4E5`. Sidecars are
`$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$FFD/$AD9`.

`capabilities [path]` is dispatched and listed in help. It resolves aliases/
relative paths resident-side, then reports endpoint, max path/leaf lengths,
size units, operation bits, and provisional state in the utility sidecar.
Runtime authority `vice_auto_20260816_191949` covers `8:/`, `u:/USB1`,
`s255:/`, and `t:/`, plus help and unknown dispatch. It is not physical UCI
proof. Current regressions: config `191537`, copy/move `191556`, append
`191625`, dynamic rollback `191722` at 104 free blocks before/after, smoke
`191826`, and recursive `192022`. Recursive diagnostic addresses are now
session `$AF36-$AF37` and overlay `$B2A8-$B2AE`, all `01`.

Generated evidence is 28/28 suites and 305 assertions; numbered scope remains
46 proven, 10 partial, 4 missing. `capabilities` is no longer on the missing
command list. `status`, `find`, `head`, `tail`, `crc32`, `format`, `run`, and
`test` remain pending, as do CMD/SD2IEC nested traversal, real nested
cross-backend actions, and physical 1/16/64 MHz UCI recovery. The exact owned
root/marker prohibition and failed preflight `181348` remain unchanged.

`status` is now dispatched through command ID 34. Its UI renderer is in
`rftree`; resident supplies CWD, alias count, REU banks, loaded-controller
bits, and prior dispatch state. Keep the label `last dispatch`: current values
are only `known`, `unknown`, and `subsystem off`, not full filesystem return
codes. Runtime authority `vice_auto_20260816_192849` proves unknown retention,
alias count 0→1, CWD `8:/`, 256 banks, and readiness output.

Current build authority after status is resident `$B3EC` (447 bytes before
`$B5AC`), monolithic `$C52F`, stack `$D000`; sidecars
`$FE3/$FDF/$FFE/$FF8/$FFD/$FFF/$FFE/$C8E`. Current recursive authority is
`vice_auto_20260816_192947`, with session `$B06D-$B06E` and seven overlay
flags `$B3E0-$B3E6`, all `01`. Current dynamic rollback is `193027`, 104 free
blocks both before/after. Aggregate is 28/28 suites, 312 assertions, 46
proven, 10 partial, 4 missing. `status` is no longer undispatched; converting
all handlers to typed result codes remains. Physical safety/preflight state is
unchanged and still forbids mutation without fresh exact markers.

`find` is now dispatched as command ID 35 and shares the cooperative `tree`
controller. It applies positional or `--include`/`--exclude` patterns to the
complete relative stem through the matcher overlay; unmatched directories are
still traversed, while only matching entries display/count. Runtime authority
`vice_auto_20260816_193554` proves `find 8:/ --include RFU*` displays only
`RFUTIL` and reports `FIND DONE N1 F9 D0`. This is flat IEC evidence only.

Current build authority after find: resident `$B5A1` (10 bytes before strict
`$B5AC`), monolithic `$C54F`, stack `$D000`; sidecars
`$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$FF9/$CF4`. Do not add resident functionality
without first reclaiming bytes or designing another bounded sidecar gateway.
Current recursive authority is `vice_auto_20260816_193818`, with session
`$B220-$B221` and overlay `$B595-$B59B`, all `01`. Dynamic rollback authority
is `vice_auto_20260816_193859`, 104 free blocks before/after. Aggregate is
28/28 suites, 314 assertions, 46 proven, 10 partial, 4 missing. Remaining
undispatched commands are `head`, `tail`, `crc32`, `format`, `run`, and `test`.

Latest true Terminal-owned preflight is
`logs/readyfs_c64u/preflight-20260816-resume-goal-1935`: REST documents were
captured, all ten bounded FTP attempts reset, and status is `failed:1`. No
exact marker was fetched, so no physical launch, mapping, config write, or
filesystem mutation followed. Do not tight-loop. Never delete or mutate
anything outside
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`; do not mutate even those
roots until `.readyfs-owner-readyfs-20260815-190355-79014` round-trips freshly
from each root.

ReadyFS now has a ninth cached sidecar, `rfcontent`, at overlay-bank
`$8000-$8FFF`; the bounded tree queue moved to `$9000-$FFEF`. `head` and
`tail` are dispatched as numeric command IDs 36 and 37. Resident code owns all
stream I/O and sends bounded chunks through content INIT/ADD/REPORT. `tail`
retains 243 data bytes inside a 256-byte controller workspace and must keep the
explicit `TAIL TRUNCATED` result whenever older bytes were lost; do not hide
or silently widen that contract.

Runtime content authority is `vice_auto_20260816_203314`: screenshots prove
three-line head, two-line tail, long-tail truncation with the last two lines,
and invalid-count usage. Current recursive/RFJ1 authority is
`vice_auto_20260816_203751`; session flags are `$B226-$B227 = 01 01`, and
overlay flags are `$B59B-$B5A1 = 01 01 01 01 01 01 07` (the final byte is the
utility/tree/content bitmask). Current rollback authority is
`vice_auto_20260816_203833`, at 101 free blocks before/after. Aggregate UI
evidence is 28/28 suites and 325 assertions.

Current strict layout is resident `$B5A7`, only four bytes before `$B5AC`;
monolithic `$C5ED`; sidecars
`$FE3/$FDF/$FFE/$FF8/$FFD/$FFF/$DFB/$FAC/$8D6`. Do not add resident code
without first reclaiming space. Remaining undispatched command families are
`crc32`, `format`, `run`, and `test`; nested cross-backend and physical
1/16/64 MHz/fault proof also remain.

Physical safety state is unchanged. Latest preflight
`logs/readyfs_c64u/preflight-20260816-resume-goal-1935` failed after ten
bounded FTP resets and made no mutation. Never delete or mutate outside
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`; no mutation inside them is
allowed until `.readyfs-owner-readyfs-20260815-190355-79014` is freshly read
and matched from both roots by a true Terminal-owned run.

`crc32 PATH` is now command ID 38 and uses the same resident-stream/slot-9
INIT/ADD/REPORT contract. Its CRC-32/ISO-HDLC implementation must remain
bytewise: the 16-bit-shift version pulled cc65 helpers into resident memory and
crossed `$B5AC`. Host and VICE authority use the 84-byte `RFVIEW` oracle
`$6126E7F6`; focused run is `vice_auto_20260816_205049`, full utility run is
`vice_auto_20260816_205132`.

Superseding build authority is resident `$B5A3` (eight safe bytes), monolithic
`$C5D6`, sidecars `$FE3/$FDF/$FF3/$FF8/$FFD/$FFF/$DFB/$FB3/$B6C`.
Superseding recursive authority is `vice_auto_20260816_205233`, with session
`$B222-$B223 = 01 01` and readiness
`$B597-$B59D = 01 01 01 01 01 01 07`. Rollback authority is
`vice_auto_20260816_205318` at 101 blocks before/after. Aggregate UI evidence
is 29/29 suites and 331 assertions. Remaining undispatched command families
are `format`, `run`, and `test`.

`test` is now dispatched as command ID 39. It is intentionally atomic: one
invocation prints the versioned `RFT1 SUITES` manifest, names `CORE`, and runs
four parser/CRC/workspace checks, ending with `RFT1 CORE PASS 4/4`. Focused UI
authority is `vice_auto_20260816_221431`; full utility is `221450`, recursive
is `221535`, and rollback is `221634`. Current diagnostic bytes are session
`$B20D-$B20E = 01 01` and readiness
`$B582-$B588 = 01 01 01 01 01 01 07`.

Content overlay calls continue to use the shared resident utility call record;
the temporary alias-lifetime record and gateway pointer pin did not solve the
diagnostic syntax issue and were removed before the final regression. Current
strict layout is resident `$B58E` (29 safe bytes
before `$B5AC`), monolithic `$C5C7`, sidecars
`$FE3/$FDF/$FF8/$FF8/$FFD/$FFF/$DFB/$FB9/$D69`, with 29/29 UI suites and 334
assertions. Remaining undispatched command families are `format` and `run`.

A direct `format` handler is rejected, not pending in source: it overflowed the
strict resident ceiling by 230 bytes and `rfcontent` by 86 bytes. Implement it
only as a cooperative nested formatter through the existing media gateway,
with channel-15 I/O resident, `--whatif`, explicit disposable-media admission,
and exact confirmation. Do not resurrect the measured oversized handler.

`format` is now dispatched through the cooperative media route. Slot 9 owns
only validation and `N:LABEL,ID` composition; resident `probe_iec_io()` owns
channel-15 I/O and completion. Exact execution requires a canonical flat IEC
root, a freshly probed recognized non-SoftIEC profile, ordered
`--label NAME --id ID --disposable --yes`, a 1–16 byte comma-free label, and a
two-byte comma-free ID. `--whatif` returns before profile or media I/O.

Format authority is `vice_auto_20260816_224759` on a newly created local
drive-9 D81. It proves WhatIf, all admission failures, exact successful format,
and `LAB`/`RF`/3160-block independent readback. Current content/RFT1 authority
is `224611`, utility `224915`, recursive/RFJ1 `232027`, and rollback `232427`.
Recursive memory probes must resolve exported sentinels from
`artifacts/readyfs/readyfs-overlay.lbl`; current session bytes are
`$B227-$B228` and readiness `$B59C-$B5A2` (`01` x6 then `07`).

Current strict layout is resident `$B5A8` (3 safe bytes before `$B5AC`),
monolithic `$C5BA`, and sidecars
`$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$E19/$FC1/$FF1`. The generated UI report is
30/30 suites and 348 assertions. The only original undispatched command is
`run script.seq`; physical nested/cross-backend, mount/swap/restoration, and
fault-injection evidence also remain. No physical request or mutation occurred
for format. The exact owned-root/marker prohibition is unchanged.

Latest true Terminal-owned read-only preflight is
`logs/readyfs_c64u/preflight-20260816-format-resume`: REST documents succeeded,
then ten bounded FTP attempts reset and status is `failed:1`. No exact marker
was fetched, so no physical launch, config/feature change, filesystem mutation,
or format followed. Do not tight-loop; this supersedes the older 1935 failure
as current connectivity authority without changing the safety gate.

`run SCRIPT.SEQ` is now command ID 40, so every original command token is
dispatched. The tenth sidecar `rfbatch` owns the full editor and a cooperative
INIT/NEXT/ACK/REPORT script controller in a dedicated REU bank: cache
`$0000-$0FFF`, staged script `$1000-$4FFF` (16 KiB maximum), and checkpoint
`$5000-$50FF`. The source file is fully staged and closed before any command
dispatch. Scripts support comments, `onerror stop|continue`, and `expect rc N`;
nested run is rejected and batch confirmation never reads the keyboard.
Current rc0–3 values are dispatch-class v1, not typed filesystem errors.

Batch authority is `vice_auto_20260817_001141`; editor is `001549`, scrollback
is `001605`, recursive/RFJ1 plus ten-sidecar admission is `001612`, and current
rollback is `001649`. Host-created SEQ fixtures must use C64/PETSCII-compatible
uppercase bytes. The editor harness must resolve `_line_buf` from
`readyfs-overlay.lbl`, never a hard-coded BSS address.

Current layout is resident `$B4BB` (240 safe bytes before `$B5AC`), monolithic
`$C1CF`, stack `$D000`, with sidecars
`$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$E19/$FDC/$FF1/$FE2`. UI evidence is 31/31
suites and 362 assertions; numbered status is 46 proven, 10 partial, 4 missing.
UCI verification remains ReadyIRC-derived and green across the state-machine
contract intended for 1/16/64 MHz; injected recovery proof is still open.

No physical action occurred for this milestone. Keep
`preflight-20260816-format-resume` as the current bounded failure and do not
tight-loop it. Mutation remains forbidden until both exact marker files are
freshly fetched from the exact USB1/SD owned roots; never delete or mutate
anything outside those roots.

`probe recover` is now the read-only injected UCI recovery diagnostic. It
starts UltimateDOS IDENTIFY, waits until asynchronous PUSH visibly leaves
quiet idle, enters the shared ABORT_P-aware bounded recovery path, and then
re-identifies normally. `readyfs_uci_test` deterministically proves delayed
PUSH, BUSY, one abort, queue drains, DATA_ACC, quiet idle, and the subsequent
IDENTIFY. VICE `vice_auto_20260817_002400` proves `UCI RECOVER: OFF` when UCI
is absent. The physical read-only speed runner includes this at 1/16/64 MHz,
but has not yet run it on hardware.

Superseding current authorities are editor `002517`, batch `002532`,
recursive/RFJ1 `002551`, and rollback `002634`. Current layout is resident
`$B5A5` (6 safe bytes before `$B5AC`), monolithic `$C2B9`, stack `$D000`, and
help/journal exactly `$1000`; resident additions require compaction. Generated
evidence is 31/31 suites and 363 assertions, with 46 proven, 10 partial, and
4 missing numbered cases.

No physical request occurred for this recovery milestone. Do not retry the
current FTP-reset preflight tightly. The exact two-root/marker gate and the
absolute prohibition on deleting or mutating anything else remain unchanged.

Tape is now a capability-honest partial driver, not merely an endpoint.
`vice_auto_20260817_002914` proves `t:/` is sequential-only, has no meaningful
free-space claim, and refuses directory, random-access copy, delete, and tree
operations before I/O. The inspected copy-refusal screenshot is
`screens/readyfs_tape_copy_refused.png`. Actual disposable-TAP sequential
KERNAL read/write and cancellation behavior remain unimplemented. Current UI
inventory is 31/31 suites and 367 assertions; physical safety state is
unchanged and no C64U request occurred.

Physical UCI abort recovery is proven at all required speeds. True
Terminal-owned `speed-matrix-20260817-uci-recover-only` reports quiet recovery,
UltimateDOS V1.2 re-identify, and prompt return at 1/16/64 MHz, then restores
and freshly reads back exact `TurboEnable Bit` / `64`. Case 59 is proven;
the generated split is 47 proven, 9 partial, 4 missing. No filesystem or media
mutation occurred.

Do not cite `speed-matrix-20260817-uci-recover`: its 1 MHz recovery passed but
the subsequent large USB1 directory case failed. Its restore trap and a
separate Terminal-owned exact-payload restore both verified 64 MHz. The
current connectivity authority is
`preflight-20260817-uci-recovery-resume`: REST and SoftIEC-on/bus-11 succeeded,
then ten FTP resets prevented any marker fetch. Do not tight-loop; all physical
filesystem mutation remains prohibited until both exact markers round-trip.

Physical flat IEC↔UltimateDOS copying is now authoritative at
`logs/readyfs_c64u/cross-owned-20260817-iec-udos-roundtrip-k`. The independent
Terminal-owned harness mounts a disposable D81 by REST attachment, rereads the
exact 116-byte USB1 and SD owner markers before every mutation, writes only
the fresh preserved USB1 folder `cross-20260817-iec-udos-roundtrip-k`, and
restores Drive A exactly. It performs no host deletion. Never delete or mutate
anything outside the two exact marker-owned roots.

The physical 1581 returns directory letters with PETSCII bit 7 set. ReadyFS
now folds that bit for comparison, copies the exact raw directory spelling for
opens/existing rename operands, and leaves new names as supplied; focused VICE
copy/move authority is `vice_auto_20260817_013435`. Both physical directions
copy 4069 bytes, preserve PRG `$11`, pass independent length/CRC comparison,
and the reverse D81 directory contains `RFROUND`. Cases 40/41 are proven:
current reports show 49 proven, 9 partial, 2 missing and 31/31 VICE suites with
367 assertions. Layout is resident `$B549` (98 safe bytes), monolithic `$C25D`.

SoftwareIEC 3.14 physical research established a strict firmware boundary.
UCI ADD_PARTITION returned target status `$01` for unused partitions and
independent `/v1/drives` readback proved no mapping was added. REST Default
Path truncated a long value and did not change the live partition after
disable/enable or reboot; every configuration attempt restored/read back the
exact original. The only live mapping remains partition 0 `/USB0/`, bus 11.

Official documentation and physical behavior agree that 3.14 supports `CD:`
plus ordinary file OPEN/CLOSE, but not `MD:`, `R:`, or path-qualified SD2IEC
directory commands. Runs `softiec-owned-20260817-040632`, `040857`, and
`041716` stopped at the first unsupported/unverified action, ran no later
actions, and deleted nothing. The intended `rf041716` folder is independently
empty; read-only UltimateDOS stat found no `/USB1/sfa.seq`. Preserve every
failed artifact/folder anyway and never clean outside the exact owned roots.

ReadyFS now consumes the IEC status reply and requires `00` after each
SoftwareIEC `CD:` before leaf I/O. It re-derives the parent from immutable
canonical spelling for every stream. Direct creation is admitted only for a
destination already proven absent; replacement still fails closed without
transactional rename. Read-only physical authority
`ui-readonly-soft-status-longpath-20260817-0430` proves the long owned path
returns before leaf I/O. Component-wise status-checked `CD:` is the next
required adapter; do not claim SoftIEC file-copy success yet.

Focused VICE authorities are mutations `vice_auto_20260817_041515`, copy/move
`041535`, batch/typed results `041653`, and command-path `043339`. The stale
native-pattern oracle now advances pagination and counts all 21 current `RF*`
entries. Runs `042734`, `043054`, and `043219` remain failed/non-authoritative
oracle diagnostics. Current strict resident end is `$B5AA`, one byte before
`$B5AC`; the UCI verifier and physical 1/16/64 MHz recovery matrix remain
authoritative.

Superseding SoftwareIEC/build note: component-wise command generation is now
implemented as `RF_UTILITY_SOFT_CD` in utility overlay slot 7. Resident
`softiec_enter_parent()` resets at the virtual root and requires DOS status
`00` after each emitted `CD:`; the sidecar owns no device I/O. This still does
not make SoftwareIEC usable: read-only run
`ui-readonly-soft-root-dir-20260817-0453` shows the global `/`, `SD`, `FLASH`,
`TEMP`, `USB1` namespace, and `ui-readonly-soft-component-diag-20260817-0445`
shows the attempted media transition failing. `dir s0:/` is deliberately
`UNSUPPORTED`; do not claim flat or recursive SoftIEC copy success and do not
run a mutation harness until the bridge is read-only proven.

Superseding VICE/layout authority: `vice_auto_20260817_050201` proves `status`
retains the previous typed result (unknown 1, then successful alias 0), and
`vice_auto_20260817_050249` keeps typed batch results green. Reports remain
31/31 plans and 49 proven / 9 partial / 2 missing cases. Exact current ends are
resident `$B53E` (109 bytes before `$B5AC`), monolithic `$C44C`, and utility
sidecar `$FE9`. UCI, overlay-DMA, pipeline, and build verifiers pass; physical
UCI authority remains `speed-matrix-20260817-uci-recover-only` at 1/16/64 MHz.
`make readyfs` also runs the focused `readyfs_utility_test.c` behavioral oracle
for ordered parent components and leaf exclusion. The `050201` status and
`050249` typed-batch screenshots were visually checked.

ReadyIRC audit superseding note: ReadyFS matches its quiet-IDLE, asynchronous
PUSH, full queue drain, ABORT_P-aware single-abort recovery, DATA_ACC, and
four-pass bounded-wait contract. ReadyFS additionally keeps the 64-MHz-proven
assembly-adjacent MORE-to-BUSY observation. `readyfs_uci_test.c` now covers
MORE/LAST multiblock callbacks, drain-on-truncation with both flags, transport
ERROR recovery, and the 896-byte command limit; the source verifier requires
those markers. All UCI callers must continue through `readyfs_uci_command()`.

Typed-result/layout superseding note: compact fastcall helpers now set result 2
for unavailable UCI/overlay/sidecar paths and result 7 for unsupported endpoint,
path, REL, and SoftIEC directory boundaries. Utility authority
`vice_auto_20260817_052447` visually proves `DIR S0:/` → `SOFTIEC OFF` → 2 and
`DIR T:/` → `UNSUPPORTED` → 7; batch `052540` keeps 4/5/6 green. Current exact
layout is resident `$B587` (36 safe bytes), monolithic `$C49E`, utility `$FE9`.
Generated evidence is 31/31 with 372 assertions and 49/9/2 cases.

SoftwareIEC bridge superseding note (2026-08-17): official firmware source
shows partition 0 defaults to `/USB0/`, but the physical unit's global virtual
root contains `SD`, `FLASH`, `TEMP`, and `USB1`, not `USB0`. True independent
Terminal probe `softpath-readonly-20260817-softpath-source-e` proves lowercase
source commands `cd:/`, relative `cd:usb1`, PETSCII-$5F `READYFS_TEST`, and the
exact owned run component all return DOS `00`. Typed `_` arrives as PETSCII
`$A4`; SoftwareIEC exposes host `_` as `$5F`, so the standalone adapter
normalizes only at the SoftIEC boundary. Never normalize UltimateDOS/global UI
spelling. Overlay-slot normalization remains an explicit integration item.

The marker-gated run `softiec-owned-20260817-061009` reread both exact 116-byte
markers, created only preserved folder
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014/rf061009`, then stopped
without creating a file and without deleting anything. Probe
`softpath-readonly-20260817-softpath-source-i` proves every component including
`rf061009` returns `00`, but an OPEN of missing `sfa.seq` returns KERNAL result
0 with DOS `62`; SoftwareIEC 3.14 can then omit the terminal directory record
for the empty host folder, so the old absence scan blocks. Keep cases 42/43
missing until a compact resident-owned OPEN/status existence path is both
collision-safe and under `$B5AC`. Preserve `rf061009` and every failed folder.

Current build authority is resident `$B587` (36 safe bytes), monolithic
`$C4E7`, utility `$FE7`, batch `$FD7`. Focused VICE authorities are editor
`vice_auto_20260817_062227`, batch `062243`, utility `062304`, smoke `062532`,
and paced paths `063042`; reports are again 31/31 successful with 49/9/2 cases.

Superseding SoftwareIEC/UCI note (2026-08-17): firmware 3.14 BASIC-directory
enumeration is not a type authority; it can expose the host-path header and
stop before later FAT entries. ReadyFS now discovers only SEQ/PRG/USR through
explicit ordinary OPEN plus DOS status and never probes REL. Official firmware
source proves REL uses `FA_OPEN_ALWAYS`, so an existence probe would create a
file. The early unsafe diagnostic created
`USB1/.../rf065128/ap1000.rel`; preserve it permanently and never repeat that
probe. The focused app-write authorities are trace
`softwrite-noftp-20260817-1100-af` and production `1115-ag`.

Official `softiec_target.cc` and `iec_channel.cc` also prove target-5 command
`$14` takes a secondary address and synchronously executes
`ext_close_file()`/`push_command($E0)`. ReadyFS therefore completes the exact
stale read channel 2 before another SoftwareIEC path command and completes
existence-probe channel 6 before reading DOS status. Both calls still use the
single ReadyIRC-derived UCI state machine; no delay loop is used. The order is
important because UCI status aliases the resident IEC-status scratch buffer:
DOS status must be read after target CLOSE. Read-only run
`softwrite-noftp-20260817-ap0846-read2` proves an absent leaf reports both
SoftIEC `NOT FOUND` and raw UltimateDOS `FILE DOESN'T EXIST`.

Focused compare-to-immediate-SoftIEC-read passed in trace
`softwrite-noftp-20260817-uci-close-trace` and production
`softwrite-noftp-20260817-uci-close-prod`, including exact USB1/SD marker
checks before and after. Trace new-file run
`softwrite-noftp-20260817-uci-close6-trace2` created only preserved
`rf083856/ap0853.seq`, then proved logical SoftIEC and raw UltimateDOS
readback plus both post-owner checks. Failed diagnostic full run
`softiec-owned-20260817-uci-close-full` created only preserved folder
`rf083856`; its first write did not complete. Never delete that folder or any
earlier artifact. Current strict build is resident `$B5AA` (one safe byte),
monolithic `$C502`; trace ends `$C5F7`. All build/UCI/DMA/pipeline/host checks
pass. A new full marker-gated production suite
`softiec-owned-20260817-close26-full2` is currently the pending authority.

Final superseding SoftwareIEC authority (2026-08-17): the production-speed
adapter now combines exact target-5 CLOSE of read secondary address 2, a full
target-5 IDENTIFY transaction as the serialized firmware-worker barrier, exact
post-probe CLOSE of secondary address 6, and one status-bearing IEC command
transaction per `CD:`. A separate status-drain OPEN doubled command-channel
traffic and reproducibly stalled on the ninth OPEN at 64 MHz. These are
ReadyIRC-derived state transitions, never delay loops. The source verifier
locks the close→barrier→root-CD ordering and forbids the extra drain.

Physical production authority is combined mutation run
`softiec-owned-20260817-nested-parent-prod-full` and read-only completion
`softwrite-noftp-20260817-treeverify-final`. In fresh preserved
`rf091800/rf100154`, ReadyFS writes/reads SoftIEC, copies SoftIEC→UltimateDOS,
writes an UltimateDOS source, copies UltimateDOS→SoftIEC with
`VERIFY: IDENTICAL`, rereads and independently compares it, creates `nested`,
writes/reads `nested/inside` through SoftIEC, lists raw lowercase host names,
reads the nested raw `.seq`, and passes both exact USB1/SD owner checks after
all mutations. Case 42 is PROVEN. Case 43 is PARTIAL: nested interoperability
is physical, but one recursive whole-tree copy command is still required.

Firmware 3.14 has a breadth boundary: newly appended folders directly under
the now-crowded owned run root (`rf094315`, even after seeding and reboot) are
not enterable through SoftwareIEC, while a new folder under visible,
uncrowded `rf091800` is immediately usable. Preserve `rf094315/rfseed.seq` and
all diagnostics. Final build is resident `$B5A2` (nine bytes before `$B5AC`)
and monolithic `$C4FA`. VICE utility `vice_auto_20260817_101607`, smoke
`101701`, and paths `101711` pass. Reports are 31/31 suites, 372 assertions,
and 50 proven / 10 partial / 0 missing cases.

Recursive cross-backend superseding authority (2026-08-17): preserve physical
destination `u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014/rf091800/rr111505`
forever. `rr5-final3` is the successful true Terminal-owned whole-tree
UltimateDOS-to-SoftwareIEC run: `RECURSIVE PLAN F4 SELECTED 4`, inline exact
10/11/7-byte verification, and `BATCH DONE 4/4 FAIL 0`, followed by three
independent comparisons, normal lowercase host-name directory evidence,
logical nested read, dual post-owner checks, and exact Drive A restoration.
Fresh read-only `rr5-verify` independently proves the final raw/logical tree,
owners, and drive restoration. Case 43 is now PROVEN.

The required name rule is asymmetric: retain UltimateDOS bracket-hex access
spelling on the source, but decode it for IEC/SoftIEC destination components;
strip the final `.SEQ/.PRG/.USR/.REL` UCI annotation and a matching preceding
host type extension. Never reuse the earlier encoded SoftIEC destination
behavior. Preserve `rr111504` as diagnostic evidence and never delete it.

Current firmware 3.14 can return 404/`Cannot open file` from the REST
`runners:run_prg` attachment handoff while drives/config/memory remain healthy
and FTP resets. The no-FTP physical harness has a bounded fallback: mount the
disposable overlay D81, reset/resume, normal-IEC load build-owned
`READYFS-OVERLAY`, wait 180 seconds without screen DMA, then require
`BATCH: READY` and both exact owner markers. For long physical KERNAL/SoftIEC
commands, do not DMA-read screen memory every second: `rr5-final2` proves that
polling can stall the nested transition after two otherwise verified files.
Use a quiet command window, then one bounded result poll. The application uses
no timing delay for UCI itself; all UCI remains under the ReadyIRC-derived
asynchronous state-machine contract and the 1/16/64-MHz recovery authority.
Current green build is resident `$B5A0` (11 bytes before `$B5AC`), monolithic
`$C491`, recursive sidecar `$F67`, and 11 disjoint sidecars. Full
`make readyfs`, all host/verifier checks, recursive VICE
`vice_auto_20260817_135206`, and its post-stop capability oracle pass. Reports
are 32/32 suites, 373 assertions, and 51 proven / 9 partial / 0 missing cases.

Physical media superseding authority (2026-08-17): preserve owned
`u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014/md145816` and its uppercase
`DISK1.D81`/`DISK2.D81` forever. True Terminal-owned
`softwrite-noftp-media-145816` passes dual owner gates before every mutation,
lists both images, mounts disk 1 on drive 8, swaps to disk 2, dismounts to empty
image fields, rechecks both owners, and restores the original enabled bus-8
1581 Drive A state exactly. Independent REST snapshots prove every transition.
No delete was issued.

The run also fixed a real RFJ1 edge: MKDIR is destination-only, but the compact
completion journal stores `source_root`; resident admission must therefore pass
the destination in both identity slots. Without that, the host directory is
created but ReadyFS returns silently before its success line. Pipeline
verification locks the corrected call. Current build is resident `$B5A6` (five
bytes before `$B5AC`), monolithic `$C491`, backend `$FF8`, recursive `$F67`.

For physical overlay launch, never take the first `READYFS LAB` screenshot
while `RFMATCH` starts loading. On this 64-MHz C64U that REST DMA can pin the
KERNAL transfer. Wait through the complete sidecar preload without DMA, then
admit only on `BATCH: READY`; likewise use a quiet window around media UCI
commands. This is harness pacing, never an application UCI delay.

Preserve lowercase diagnostic pair `md144209/disk1.d81` and `disk2.d81`, plus
empty `md140757` and `md142820`. Lowercase images list normally, but mount
preflight still receives a bracket-hex UltimateDOS access spelling; keep cases
19/33 partial until display/raw/access identities are unified. Current reports
are 32/32 suites, 373 assertions, and 53 proven / 7 partial / 0 missing cases.

Nested filtered WhatIf superseding authority (2026-08-17): preserve every
failed read-only diagnostic, especially `whatif-filter-162725`,
`whatif-filter-logical-164055`, `whatif-filter-fixed-165954`,
`whatif-filter-atomic-172920`, and
`softwrite-noftp-whatif-filter-asm-175230`; they performed no writes and
restored Drive A exactly. The rejected `...asm-175200` launch failed local
name admission before contacting hardware. Never delete these logs or any
physical artifact.

The filter fault was cc65 character encoding: target `'A'` is PETSCII `$C1`,
while C64U keyboard injection uses ASCII uppercase and UltimateDOS can retain
ASCII lowercase in the same relative stem. Matcher case folding must always
normalize `$41-$5A`, `$61-$7A`, and `$C1-$DA`; do not replace this with
target character-literal comparisons. Matcher-side Ultimate access-name
normalization uses `readyfs_match_name.s`, copied from the physically proven
recursive assembly converter.

True Terminal-owned read-only authority is
`softwrite-noftp-whatif-filter-casefold-180400`: exact command
`copy u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014/rf091800/rf100154
s0:/wf180400 --recursive --whatif --include **/inside` reports
`RECURSIVE PLAN F4 SELECTED 1` and
`PLAN W1 D0 M0; DONE W0 D0 M0`. Source, nested, and destination directory
screens plus all three source CRCs are unchanged; no destination was created;
both owner markers pass before/after; Drive A restores byte-for-byte. Case 52
is PROVEN. Current build is resident `$B599` (18 safe bytes), monolithic
`$C428`, matcher `$733`, recursive `$F67`; `make readyfs` and recursive VICE
`vice_auto_20260817_180205` pass. Generated status is 54 proven / 6 partial /
0 missing. Continue using the ReadyIRC-derived UCI asynchronous state machine;
this fix introduced no timing loop or transport change.

Forced-failure restoration authority (2026-08-17): use only the opt-in
`READYFS_FORCE_FAIL_AFTER_OWNERS=1` branch with `whatif` mode and an explicit
test speed. It must admit/read back the speed, preload every overlay, pass both
owners twice, create `forced-failure.txt`, and exit 73. The EXIT trap must read
both owners again before any reset can erase ReadyFS, then restore Drive A and
the entire `U64 Specific Settings` object. Status 73 is expected authority;
status 97 means restoration failed and must never be promoted.

Physical authority is
`softwrite-noftp-forced-restore-put-16-183320`: Manual/16 is observed, six
exact owner-marker commands pass, the deliberate trigger exists, final status
is `failed:73`, emergency speed restore reports success after aggregate HTTP
500, complete original/restored U64 JSON is equal, and full original/restored
drive JSON is equal. No filesystem object or media mapping changed. Case 60 is
PROVEN and reports are 55 proven / 5 partial / 0 missing.

Preserve `softwrite-noftp-forced-restore-182200` and
`softwrite-noftp-forced-restore-16-183100` as excluded diagnostics. They failed
during aggregate config admission before the trigger. Although configuration
was restored, post-reboot BASIC screens can contain stale ReadyFS text and are
not valid owner evidence. Never cite them as marker passes. Current harness
uses per-setting PUT for admission and the exact saved-payload helper for
restoration.

Lowercase metadata authority (2026-08-17): preserve physical run
`softwrite-noftp-metadata-lowercase5-20260817-2004` and owned images
`md144209/disk1.d81` plus `disk2.d81`. ReadyFS `stat` now keeps canonical
display, exact UltimateDOS access spelling, and decoded host name distinct;
the observed firmware spelling is raw lowercase `disk1.d81` (not bracket
hex), type `$10`, exactly 819200 bytes. Host tests still cover bracket-hex
decoding for names that require it. Mounted image identity is independently
`RFMEDIA1` with 3160 C64 blocks. SoftwareIEC partition 0 reports bus 11,
target `$01`, and `FREE UNAVAILABLE`; do not synthesize a host capacity.

That authority passes exact USB1/SD owners before, around, and after the
mount/dismount lifecycle, preserves both images, and restores full Drive A
JSON byte-for-byte. Preserve but exclude `...metadata-lowercase-1927`,
`...lowercase2-1933`, `...lowercase3-1943`, and `...lowercase4-1953`; they
stopped on harness parse/oracle defects before complete proof, restored the
drive, and performed no filesystem mutation. Never edit a physical runner
script while its Terminal-owned process is active: bash can read later source
chunks after launch, producing a mixed-version parse.

Cases 19, 33, and 34 are PROVEN. Current build authority is resident `$B59A`
(17 safe bytes before `$B5AC`), monolithic `$C429`, matcher `$AE3`; all host
checks and the complete VICE wrapper set pass. Generated status is 58 proven /
2 partial / 0 missing; only cases 55 (future-firmware SoftIEC map/unmap) and 56
(compatible-profile physical SD2IEC execution) remain partial. The metadata
work did not change UCI pacing: keep using the ReadyIRC-derived asynchronous
state machine and its 1/16/64 MHz proof discipline.

SD2IEC-compatible emulation authority (2026-08-17) is
`vice_auto_20260817_203654`. It first proves real VICE drive 8 caches as
`LEGACY P0 F0 I0` and denies partition operations, then DMA-stashes only
ReadyFS's four-byte `{magic,device,kind,flags}` record at IEC-8 session offset
`$0888` (absolute REU `$2888`, bank `$FF`). ReadyFS reports
`SD2IEC P1 F1 I1` and dispatches translated partition directory, mkdir, and
image-mount requests. The ordinary VICE 1581 remains explicitly non-SD2IEC;
its failures are routing/failure-handling evidence, not physical compatibility.
The wrapper requires the D81 SHA-256 to remain identical.

Partition mkdir completion must retain `backend->source_root = call->source`
even though endpoint validation uses `destination_root`. RFJ1 single-action
completion journals the source-root stem for every action; clearing it caused
`END ERR` after command-channel I/O. Current run reaches clean `CREATED`
completion and all 100 steps/38 assertions pass. Overall UI inventory is
32/32 and 379 assertions; case 56 stays PARTIAL only for real SD2IEC success.
Build remains resident `$B59A`, monolithic `$C429`, drive sidecar `$FF1`.

SoftwareIEC-to-Ultimate recursive diagnostic note (2026-08-17): recursive
source admission now accepts both adjacent folder-capable endpoints, Ultimate
and SoftwareIEC, through the same cooperative tree import. The SoftwareIEC
tree adapter resets to partition root, enters every canonical component with
checked `CD:`, then opens a plain `$` directory stream. A physical diagnostic
found that this new path must explicitly bind `source.device` to the runtime
SoftwareIEC IEC bus; without it, the first command went to device 0/tape and
waited. The fix resolves the bus once and reuses it for component `CD:` and
directory I/O. It does not change UCI transport or add application pacing:
the ReadyIRC-derived async PUSH/DATA_ACC/queue-drain/recovery/final-IDLE state
machine remains authoritative and `verify_readyfs_uci_protocol_contract.py` passes.

Current build authority after that fix is resident `$B5A8` (three safe bytes
before `$B5AC`), monolithic `$C410`; all host, overlay, pipeline, and UCI
contracts pass. Focused recursive VICE authority is
`vice_auto_20260817_224708`. The physical reverse direction is **not yet
proven** and must not change the 58 proven / 2 partial numbered summary.
Preserve the owned-only empty diagnostic destinations `rv204208` (`SOURCE
BAD`), `rv205834` (zero-entry plan), `rv212140` (unbound bus timeout), and
`rv214019` (screen-DMA-polling timeout). Preserve later launch diagnostics
`rv215603`, `rv220053`, `rv220538`, `rv221039`, `rv221734`, `rv222247`,
`rv223343`, and `rv223506`; they did not reach an owner-gated ReadyFS mutation
command. REST `run_prg` returned 404, serial IEC stopped returning to BASIC,
and an experimental chunked RAM launch reached `SEARCHING FOR RFMATCH` but
could not complete the first IEC sidecar load at either 64 or 16 MHz. That RAM
fallback was removed from the default harness rather than promoted. The
harness retains a 240-second no-screen-DMA window for reverse WhatIf and
explicit Terminal pass-throughs for IEC-load/overlay-admission bounds.

Never delete any of those physical logs or directories. Continue to mutate
only below the exact marker-owned USB1/SD roots and always re-read both owner
markers before every physical mutation. A runner-script edit is allowed only
after its Terminal-owned process and restoration helper have both exited.

CMD/SD2IEC tree routing authority (2026-08-17): use
`vice_auto_20260817_230948` for the current compatible-profile UI evidence.
It passes 103 steps/39 assertions and adds `TREE 8.1:/` after stashing only the
ReadyFS `{52,08,02,07}` capability record. The visible result is
`TREE FAILED F0 D0` at
`logs/vice_auto_20260817_230948/stages/sd2iec_tree_dispatch_result/screen.png`.
That is proof that profile admission, `$1//` translation, the cooperative tree
controller, and resident IEC handoff all execute; VICE drive 8 is still an
ordinary 1581, so this is not real SD2IEC nested-enumeration proof. Case 56
remains PARTIAL until successful physical SD2IEC folder/image execution.

Implementation rule: queued CMD/SD2IEC logical directories must go through
`drive_partition_command(..., argc=0, RF_CMDPATH_DIRECTORY)`, which returns
resident `dir_iec(..., tree=1)` success. `drive_command` deliberately aliases
`source`, not `dest`, and resolves the translator input into `temp.canonical`;
aliasing it back over `dest` corrupts the tree root after the first directory.
Tree include/exclude options are cached once and sent through the matcher
sidecar with `RF_MATCH_RAW_STEM` for non-Ultimate names. Never move IEC I/O
into a sidecar.

Current build authority is resident `$B591` (26 safe bytes before `$B5AC`),
monolithic `$C3E6`, matcher `$AF2`; `make readyfs`, overlay DMA, pipeline, all
host checks, and the ReadyIRC-derived UCI verifier pass. Recursive regression
authority is `vice_auto_20260817_231116` (61 steps/27 assertions plus exact
post-stop capability bytes). Generated status is 32/32 suites, 380 assertions,
58 proven / 2 partial / 0 missing. No physical runner was launched for this
change, no USB1/SD object was changed or deleted, and every earlier physical
diagnostic must remain preserved under the exact owner-safety rules above.

Latest reverse physical retries (2026-08-17) are preserved launch diagnostics,
not ReadyFS evidence. `softwrite-noftp-reverse-tree-20260817-231700` used a
fresh Terminal at 1 MHz and new target `rv231700`, but REST speed admission
returned HTTP 400/500 before owner checks or fixture mount. Full runner and
manual-restored U64 config JSON match the original hash exactly; manual restore
is `success`.

`softwrite-noftp-reverse-tree-20260817-231800` used a fresh Terminal at 16 MHz
and new target `rv231800`. Speed/config and overlay D81 mount succeeded, but
ten `runners:run_prg` calls returned 404. After the complete no-DMA 240-second
serial IEC wait, the keyboard buffer still did not drain for `SYS2061`.
ReadyFS therefore never reached `BATCH: READY`, owner admission, or any shell
command. Original/restored/manual U64 config SHA-256 values are identical;
original/restored Drive A SHA-256 values are identical; manual restore reports
`success`; `results.tsv` has only its header. No destination or filesystem
object was created, modified, or deleted. Preserve both runs and do not claim
reverse physical proof. This remains a pre-application C64U launch-state
block, not a reason to change UCI pacing or the ReadyIRC-derived transport.

## 2026-08-18 — ReadyFS tape media path proven

ReadyFS now supports named sequential tape paths as `t:/NAME` (1–16
characters), using KERNAL device 1 SA0 read and SA1 write. Disposable-TAP
authority is `vice_auto_20260818_025149`; fresh-session tape-to-D64 authority
is `vice_auto_20260818_025218`; same-session disk-write/tape-read/disk-write
authority is `vice_auto_20260818_025055`; the focused KERNAL oracle is
`vice_auto_20260817_235139`. Disk-to-tape writes 84 bytes as `RFCOPY`, and
tape-to-disk uses REU spool/replay, staged verification, promotion to
`TAPOUT`, and a byte-identical comparison with `8:/RFVIEW`.

Two boundary rules are now mandatory. Clear shared KERNAL status `$90` before
device-1 OPEN and immediately before non-Ultimate `cbm_write`, because tape EOF
`$40` otherwise contaminates the next serial write. In
`readyfs_tape_spool.s`, `fetch_eof` must `jmp succeed`; `LDY/INY` change Z, so
branching on a presumed zero accumulator falls into the DMA routine and rolls
back an otherwise complete copy. `verify_readyfs_overlay_dma.py` and
`verify_readyfs_pipeline_contract.py` enforce these rules, packed call offsets,
the target `name,s,w` formatter, sidecar linkage, and resident same-word logic.

Final layout is resident `$B5A3` (8 bytes before `$B5AC`), monolithic `$C4EB`,
and tape sidecar `$F47`. UCI verification still passes unchanged: all UCI
calls retain the ReadyIRC-derived asynchronous PUSH/DATA_ACC/queue-drain/
ABORT/final-IDLE state machine and existing physical 1/16/64 MHz authority.
Final VICE inventory is 36/36 suites with 414 assertions; numbered status is
unchanged at 58 proven / 2 partial / 0 missing. This phase ran only disposable
local VICE media. It did not launch a physical mutation runner and did not
create, modify, or delete anything below USB1 or SD. Preserve the exact owned
roots `u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
`u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`, and never delete any other
physical artifact or prior diagnostic.
