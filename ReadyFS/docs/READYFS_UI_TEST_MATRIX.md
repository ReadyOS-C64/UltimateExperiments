# ReadyFS UI Test Matrix

Target: 60 numbered UI cases. Status is updated from generated reports, not
assumed from implementation.

## Shell and editor (01–12)

1. Boot banner, standalone identity, and REU status.
2. Help opens and lists canonical endpoints.
3. Unknown command reports an error and returns to prompt.
4. Empty command is harmless.
5. 255-byte logical line reaches the parser without overflow.
6. Horizontal editor scroll follows the cursor.
7. Left/right insertion edits the middle of a command.
8. Insert/overwrite toggle changes replacement behavior.
9. Delete and Home/End behavior.
10. Up/Down recalls and edits command history.
11. Page Up/Page Down and C= fallback traverse scrollback.
12. Quoted arguments, spaces, and malformed quote diagnostics.

## Paths, aliases, and matching (13–24)

13. IEC endpoints accept 8 and 30 and reject 7 and 31.
14. Ultimate root and USB1/SD-card absolute paths.
15. SoftIEC partition 0 and 255 boundaries.
16. Tape endpoint capability query.
17. Alias create/list/use/remove.
18. Alias expansion cannot escape its root in automation mode.
19. `!` distinguishes image host and internal names.
20. Invalid image boundaries are rejected before I/O.
21. `*` and `?` component matching.
22. `**` recursive matching.
23. `--include`/`--exclude` full-relative-stem filtering.
24. Native-pattern mode stays distinct from shell matching.

## Discovery and metadata (25–34)

25. `probe uci` absent path in VICE.
26. `probe udos` identify on C64U.
27. `probe softiec` active and module-not-loaded outcomes.
28. `drives scan` covers IEC 8–30 and returns to the prompt.
29. IEC D64 directory and blocks free.
30. IEC D71 16-bit blocks free.
31. IEC D81 directory over 30 entries.
32. UltimateDOS host directory over 30 entries.
33. `stat` reports type, raw/display name, exact/estimated size units.
34. `volume`/`free` distinguish host, image, and C64 block units.

## Safe mutations (35–48)

35. `new` creates an empty SEQ file.
36. `write --line` creates expected bytes.
37. `append --line` preserves old bytes and adds new bytes.
38. Same-backend staged copy and verification.
39. IEC-to-IEC cross-device copy.
40. IEC-to-UltimateDOS copy.
41. UltimateDOS-to-IEC PRG copy preserves bytes/type.
42. UltimateDOS-to-SoftIEC copy.
43. Recursive UltimateDOS-to-SoftIEC tree.
44. Move deletes source only after verified copy.
45. Replacement rollback preserves old destination on failure.
46. Delete prompt defaults to no.
47. Recursive delete summary and `--yes` behavior.
48. REL cross-backend copy rejects with an explicit capability error.

## Dry-run, mounts, batch, and recovery (49–60)

49. Delete dry-run reports zero writes/deletes/mounts.
50. Copy dry-run enumerates sources/destination/conflicts without writes.
51. Move dry-run leaves source and destination unchanged.
52. Recursive dry-run applies filters and leaves trees unchanged.
53. Ultimate image mount/dismount on disposable image.
54. Ultimate disk swap command.
55. SoftIEC partition map/unmap under owned root.
56. SD2IEC-compatible image mount/root/unmount sequence.
57. Batch `onerror stop` and `continue` behavior.
58. Batch expected-result journal and report conversion.
59. UCI transport recovery followed by a successful identify at 1/16/64 MHz.
60. Configuration restoration and owned-root preservation after forced suite failure.

Current proven UI cases: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 35, 36, 37, 38, 39,
44, 45, 46, 47, 48, 49, 50, 51, 57, and 58. That is 46 numbered cases. Evidence comes from VICE runs
`vice_auto_20260815_174951`, `vice_auto_20260815_190200`,
`vice_auto_20260815_192229`, `vice_auto_20260815_194550`,
`vice_auto_20260815_194939`, `vice_auto_20260815_195522`,
`vice_auto_20260816_161744`,
`vice_auto_20260815_205402`, and `vice_auto_20260815_210843`, plus the Terminal-owned physical 64 MHz runs
`readyfs_c64u/ui-readonly-20260815-185313`,
`readyfs_c64u/ui-readonly-20260815-193851`, and
`readyfs_c64u/owned-mutations-20260815-194141`. Physical RF-HW cases currently
supplement the matrix rather than silently promoting unrelated numbered rows.
Other rows remain incomplete until a report names the case and supplies
artifacts.

Supplemental passing VICE suites cover explicit rename and capability-honest
flat IEC `mkdir` rejection (`vice_auto_20260815_202433`), versioned config
save/load round-trip (`vice_auto_20260815_205815` and regression
`vice_auto_20260815_212933`), shared-workspace copy/move regression
(`vice_auto_20260815_213052`), REU scrollback regression
(`vice_auto_20260815_213116`), and the latest complete smoke
(`vice_auto_20260815_233207`). The supplemental partition-namespace checks in
`vice_auto_20260815_233055` preserve `11.3:/folder`, reject partitioned IEC I/O
before touching the device, and reject partition 255. Case 24 is promoted
separately by `vice_auto_20260816_160722`/`160730`: unflagged
`dir 8:/RF*` returns `UNSUPPORTED`, the explicit flag performs a real `$:RF*`
IEC listing with seven directory records, and a non-pattern flagged form
returns `XLATE ERR`. Case 25 is proven by
`vice_auto_20260816_161342`, which reports `UCI: OFF` in VICE and returns
to the prompt. Cases 5 and 6 are proven by `vice_auto_20260816_161744`:
the visible 36-column viewport contains the unique `READYFS255END` tail,
the complete monolithic `$B069-$B168` dump equals all 255 input bytes plus
NUL, and Enter reaches the parser. The generated inventory is 26/26 suites
with 258 assertions and 46/60 numbered cases proven.
Native action WhatIf authority `vice_auto_20260816_165721` extends case 24
without silently promoting a tree case: it prints six exact typed `RF*`
targets, proves the `--whatif` spelling, applies an include filter after
native selection, reports zero completed mutations, denies a non-dry delete,
and proves `RFDRIVE` remains. Case 52 stays partial because this fixture is
flat rather than a nested directory tree.
Full-relative-stem action filtering is proven by
`vice_auto_20260815_220211`: accepted include, excluded source, component
boundary mismatch, zero-action dry-run, and accepted actual copy. These do not silently promote unrelated
numbered rows.

The post-split overlay regression `vice_auto_20260815_223235` proves the
planner sidecar's ABI executes, caches in a separate REU bank, and the matcher
can be restored for subsequent wildcard calls. `vice_auto_20260815_223204`
adds live flat-IEC enumeration: four entries are serialized, three different
filters produce exact copy/delete/move plans, actual recursion is rejected,
and a source file remains present. Case 52 stays partial until the same evidence
covers nested directories.

Supplemental VICE `vice_auto_20260816_005513` displays `JOURNAL: READY` only
after the help/journal sidecar has completed a versioned action-record
write/read/finish round trip through real REU memory, then proves help and
matcher swaps still work. This is prerequisite evidence for case 58; it does
not promote that case until executor events are converted into a host report.

Supplemental VICE `vice_auto_20260816_060538` and `060805` load and exact-size
check the fourth backend/request sidecar, cache it at overlay-bank
`$3000-$3FFF`, and display `BACKEND: READY` only after both an in-place and a
non-NULL fetched gateway pipeline self-test. That test crosses the real plan,
executor, backend, and journal sidecars; it journals injected status 82 before
ACK, closes/replays RFJ1, and restores backend code after every nested call.
It then proves help and matcher swaps. The earlier diagnostic sequence
established that nested C
argument repacking had collapsed all cache stores into slot zero; a flat
assembly REU store/fetch boundary plus one-byte loader selector fixed it. This
is prerequisite evidence but does not promote recursive mutation until a real
resident-I/O result replaces the injected status.

Physical read-only run `readyfs_c64u/ui-readonly-20260815-230109` exercises the
UltimateDOS breadth-first adapter at 64 MHz and plans 18 owned-root files with
zero completed actions. It supplements case 52 but does not promote it because
the enumerated root contained no child directories. The guarded nested-fixture
runs ending `230322` and `231705` stopped after marker verification when REST
launch reset; no filesystem command ran.

Additional physical speed evidence is in
`readyfs_c64u/speed-matrix-20260815-200638` (read-only 1/16 MHz),
`readyfs_c64u/speed-matrix-20260815-201026` (read-only plus six owned-root
mutations at 1/16 MHz), and `readyfs_c64u/owned-mutations-20260815-201654`
(the expanded six mutations at 64 MHz). These prove transport speed resilience
but do not promote case 59 until a deliberate transport fault is recovered and
followed by a successful identify.

Supplemental VICE `vice_auto_20260816_071749` is the first real action through
the overlay controller. On a freshly generated disposable D81 it copies
`RFMATCH` to `RFPIPE`, verifies bytes and metadata, proves matcher restoration
immediately and after more IEC I/O, and captures a full REU image. Extracted
RFJ1 JSON/Markdown reports one finished successful IEC copy record. This
advances case 58's prerequisites but does not promote the batch case until
multiple expected results and failure policy run together.

Regression `vice_auto_20260816_074649` extends that evidence through the
cooperative executor itself. The full REU image now yields both a finished
RFJ1 copy record and a fixed RFA1 completion record with attempted 1,
completed 1, failed 0, and pending false. Host coverage separately proves
failed ACK and duplicate-ACK rejection. Case 58 remains partial because it
still requires a multi-result batch with explicit stop/continue policy.

Regression `vice_auto_20260816_080238` supersedes that plan's latest run after
the staged `RFCMDPATH` sidecar was added to the D81. It again produces a
finished successful one-event RFJ1 and independent RFA1 `1/1/0/0`, proving the
extra disk artifact does not disturb the four runtime-loaded sidecars. It does
not claim CMD/SD2IEC runtime coverage because `RFCMDPATH` remains disabled.

The independent Terminal-owned SoftIEC attempt
`readyfs_c64u/softiec-owned-20260816-075039` is a retained safe failure, not a
passing UI case. Ten FTP connection resets prevented the owner-marker preflight
from completing, so the harness stopped before launching ReadyFS, mapping a
partition, issuing a filesystem command, or mutating either owned root. Do not
count or retry this run as test evidence until connectivity is stable.

VICE `vice_auto_20260816_081226` supersedes the pipeline plan again and adds
case `rf_ui_121_cmdpath_runtime_ready`. The assertion is displayed only after
REU slot-5 caching, ABI verification, and exact C64 translations for open,
rename (`new=old`), D64 mount, and two-command unmount. Its screenshot is
`screens/rf_ui_121_cmdpath_runtime_ready.png`. The same run retains successful
RFJ1 and RFA1 reports for the real IEC copy. This advances SD2IEC translation
coverage but does not promote command-channel or physical-device cases.

Dedicated callable suite `vice_auto_20260816_090349` adds exact UI evidence for
all eight CMD/SD2IEC translations plus matcher restoration. Screenshots
`rf_ui_122_native_open.png` through `rf_ui_130_match_after_cmdpath.png` include
directory, scratch, mkdir/rmdir, wrapped `R:new=old`, D64 mount, `CD//`, and
the separate `CD`+back-arrow follow-up. Failed diagnostics `082858` and
`084104` are retained because they exposed the shifted-PETSCII prefix defect;
they are not counted as passing suites. Case 56 remains partial until these
strings are actually issued to a disposable compatible command channel.
Pipeline regression `090503` proves the new nested gateway does not regress
the real IEC copy/RFJ1/RFA1 path.

Independent hardware attempt `softiec-owned-20260816-091304` is another safe
preflight failure, not UI evidence. Ten FTP resets prevented the exact marker
round trip, and the Terminal-owned harness stopped before launch/map/I/O. Do
not count it or retry it in a tight loop.

VICE `vice_auto_20260816_100352` adds a real, resident-owned IEC command-channel
probe before the CMD-path diagnostics. Drive 8 replies
`73,VIRTUAL DRIVE EMULATION V3.5,00,00`; the sixth sidecar classifies it as
`PROFILE: LEGACY P0 F0 I0`. The suite then repeats all eight translations,
the stateful unmount follow-up, and matcher restoration, for 13 assertions and
15 screenshots. Failed diagnostic `100250` is retained because it proved this
VICE version omits the literal word `VICE`; the exact `VIRTUAL DRIVE EMULATION`
signature is now host-tested. This is identity/capability evidence, not
permission to issue CMD/SD2IEC commands to a legacy drive and not completion
of case 56. Pipeline regression `vice_auto_20260816_100428` independently
passes the real copy, RFJ1, RFA1, and matcher path. Generated inventory is now
17/17 latest suites with 135 assertions.

VICE `vice_auto_20260816_101151` supersedes the driver-profile portion with a
deterministic REU registry and operation gate. After boot reset, device 9 is
`UNPROBED`; after a live device-8 probe, a separately issued query reloads and
validates `LEGACY P0 F0 I0`. `profile iec 8: mount` then reports `OP: DENIED`
without issuing a command. Screenshots include
`rf_ui_122_profile9_unprobed.png`, `rf_ui_123a_profile8_cached.png`, and
`rf_ui_123c_legacy_mount_denied.png`. The same suite retains all translator
and restoration assertions. Regression `101231` keeps the real cooperative
copy/RFJ1/RFA1 path green. Inventory is 17/17 with 139 assertions. This is
strong capability-denial evidence but does not promote case 56 until a
compatible disposable device actually executes mount/root/unmount.

True Terminal-owned hardware run `softiec-owned-20260816-100658` is retained
as a safe preflight failure. Ten connection resets prevented the exact owner
marker comparison, so the harness executed zero cases and performed no
launch, mapping, I/O, configuration change, or mutation.

VICE `vice_auto_20260816_112225` adds the dedicated overlay action suite. Its
boot assertion is reachable only after the C64 planner sidecar self-tests
mkdir, copy, move, delete, and rmdir through REU checkpoint/ACK/RFA1. The UI
then performs disposable `RFMATCH -> RFACTL` copy, `RFACTL -> RFMOVED` move,
checks source absence and destination presence, deletes `RFMOVED`, and checks
absence. Screenshots `rf_ui_136_action_copy.png` through
`rf_ui_140_action_delete_postcheck.png` retain each stage. The full REU report
ends with successful `delete-file`, stem `8:/RFMOVED`, and RFA1 `1/1/0/0`.
This is real copy/move/delete action evidence. Mkdir/rmdir remain controller-
proven but await a disposable folder-capable backend for real I/O evidence.
The generated inventory is now 18/18 suites and 148 assertions. Case 58 is
still partial because RFJ1 currently records each single action independently;
the three-operation UI sequence does not yet retain all three as one batch.

Hardware preflight `preflight-20260816-112357` must not be counted: audit
proved its old non-strict shell treated three failed, empty FTP captures as
success. The corrected independent preflight `113019` proves all REST reads
but fails at ten FTP root-list resets. SoftIEC suite `112412` fails at the
exact marker retrieval with an empty results table. Neither run is UI or
filesystem evidence, and neither changed C64U configuration or storage.

VICE `vice_auto_20260816_121327` supersedes the CMD-path suite with 45 passing
steps and 20 assertions. It adds direct `mkdir 8.1:/DENIED --force`, creates
`@PART:` for `8.1:/`, and repeats mkdir through that alias; the cached VICE
legacy profile returns `PROFILE DENIED` before action BEGIN or channel-15 I/O
in both cases. The suite then proves all eight
translator operations and final matcher restoration. Failed diagnostics
`120421` (help overwritten after restoration) and `120650` (native rename on
a 32-byte buffer) are retained but are not passing cases. Follow-ups `120846`,
`120942`, and `121013` pass the five-action pipeline, real copy with
RFJ1/RFA1, and flat rename/directory behavior. Inventory is 18/18 with 151
assertions. Compatible folder I/O remains partial pending a disposable device
and the exact physical owner-marker gate.

VICE `vice_auto_20260816_122410` supersedes that run with 48 passing steps. It
adds `dir @PART:/` and proves the alias resolves to the partitioned IEC path,
then the cached legacy profile denies listing before resident directory I/O.
Failed boots `121620`/`121741` and delayed diagnostic `122154` exposed KERNAL
scratch beginning at `$B5AC`; they are retained as failure evidence. Dedicated
boot/memory suite `122619` passes after the build gained a strict `$B5AC`
ceiling. Action and real-copy regressions `122455`/`122520` also pass. The
latest inventory is 19/19 suites with 154 assertions. None of these VICE gates
is compatible-device execution evidence.

VICE `vice_auto_20260816_123243` supersedes the command-path suite with 54
passing steps and 23 assertions. `delete @PART:/DENIED` stops at
`USE --FORCE`; the forced form stops at `PROFILE DENIED` under the cached
legacy profile. The clear-screen boundary between them prevents stale-text
false positives. These assertions prove the destructive and capability gates
occur before partition IEC I/O; they do not promote case 56 because no
compatible device executed the translated scratch command. Regressions
`123329`, `123405`, and boot-memory `123448` pass. Generated inventory is
19/19 suites with 156 assertions.

VICE `vice_auto_20260816_125444` supersedes the command-path suite with 72
passing steps and 29 assertions. Alias-resolved rename, partition image mount,
and partition unmount each stop at `USE --FORCE`, then at `PROFILE DENIED`
when forced under the cached legacy profile. Clear-screen boundaries prevent
stale matches. The structural guard separately proves unmount is bounded to
the translated `CD//` command and exactly one cleared `CD`+back-arrow follow-
up. This still does not promote case 56 because no compatible profile executed
the media sequence. Regressions `125544`, `125610`, and boot `125645` pass;
inventory is 19/19 with 162 assertions.

VICE `vice_auto_20260816_140348` supersedes the first real multi-entry run. On
freshly generated device-8 and device-9 D81s its 60 steps and 27 assertions
pass filtered two-file WhatIf, IEC8→IEC9 copy and compare, move/delete
postconditions, default stop-on-error, and `--continue` in one uninterrupted
C64 session. Declining the first conflict in the stop batch yields exact
`0/1 fail 1` totals and proves the second file absent. The continue batch
declines its first conflict, copies the second file, reports `1/2 fail 1`, and
proves that destination present. Exact RFJ1 conversion asserts successful
`RFZA`/`RFZB`, then failed `RFCA` plus successful `RFCB`. This promotes case
57; cases 39 and 58 remain proven. Case 52 remains partial until a nested
directory tree is unchanged under WhatIf. Inventory is 20/20 suites with 191
assertions.

VICE `vice_auto_20260816_141948` promotes case 31 on a fresh D81 containing 40
generated files plus the eight ReadyFS volume/artifact entries. The 19-step,
11-assertion plan proves bounded 18-line paging, F40 visibility beyond the old
30-entry ceiling, exact `ENTRIES: 48`, and `FREE: 2213 C64 BLOCKS`. Captures
show the first page ending at F10, the second at F28, and the final at F40.
F1/F3 then traverse both stored pages and return to the live final page,
proving directory paging shares the REU scrollback rather than discarding
earlier entries. Aggregate inventory is 21/21 suites with 203 assertions.

VICE `vice_auto_20260816_142523` promotes cases 29 and 30 using two freshly
formatted images in one session: an empty D64 on IEC 9 and a bootable D71 on
IEC 8. Seven assertions prove both `dir` and `volume` paths, exact media titles,
device identity, 664 D64 blocks free, and the D71's full 16-bit 1157-block
value. The captured screens return to the prompt after every query. Aggregate
inventory is 22/22 suites with 210 assertions.

VICE `vice_auto_20260816_143000` promotes case 48. It first proves the
disposable source entry is `CAL26CFG.REL`, cc65 type `$13`, two C64 blocks.
The cross-backend command `COPY 9:/CAL26CFG.REL U:/RELCOPY` then reports only
`REL UNSUPPORTED` before returning to `RF>`. An earlier diagnostic `142842`
showed destination probes before the rejection; source read-open/close
preflight was moved ahead of destination existence/replacement I/O, and the
pipeline structural guard now enforces that ordering. Aggregate inventory is
23/23 suites with 215 assertions. Post-fix regressions `143116` and `143137`
pass staged copy/move and overlay copy with exact RFJ1/RFA1 analysis.

VICE `vice_auto_20260816_143517` promotes case 45 with an actual disk-full
failure. A D64 starts with `OLD` byte-identical to device-8 `RFMATCH`, three
171-block fillers, and 134 free blocks. Forced replacement by the larger
`READYFS` fails after 34,016 bytes. The C64 then compares `OLD` byte-for-byte
again, lists exactly the original five entries and 134 free blocks, and shows
no `RF~xx` stage. The runner independently parses the final D64 directory,
requires `OLD` and 134 blocks, and rejects any staged name. Aggregate inventory
is 24/24 suites with 222 assertions.

VICE `vice_auto_20260816_144213` promotes case 47. A filtered recursive delete
first enumerates one selected file and stops at `DELETE [Y/.]`; answering `N`
returns to the prompt and `STAT` proves RFNO remains. Repeating the identical
command with `--yes` bypasses the prompt, reports exact `BATCH DONE 1/1 FAIL
0`, and the postcheck is `NOT FOUND`. `--yes` is centralized as the alias for
confirmation-bypassing `--force`, so map/mount/media paths retain the same
semantics without duplicated resident code. Full recursive regression
`144440` and command-path regression `144704` pass. Aggregate inventory is
25/25 suites with 229 assertions.

VICE `vice_auto_20260816_145814` promotes case 28 under a strict 20-second
completion bound. `DRIVES SCAN` displays its exact IEC 8–30 range, discovers
mounted units 8 and 9, retains the sequential-tape capability line, and
returns to `RF>`. Diagnostics `144932` and `145231` showed that opening a full
DOS command channel for each absent unit failed to finish in 60 and 180
seconds respectively. Discovery now uses the KERNAL
`LISTEN`/status/`UNLISTEN` presence handshake; normal file operations still
open their required channels and surface DOS errors. A structural guard rejects
regression to command-channel discovery. Aggregate inventory is 25/25 suites
with 234 assertions and 42/60 numbered cases proven.

VICE `vice_auto_20260816_150616` adds focused partial evidence for case 33
without promoting it. A real PRG on disposable IEC media reports separate
`DISPLAY` and directory-derived `RAW` names, type `$11`, and `SIZE EST: 1 C64
BLOCKS`; the structural guard also requires Ultimate metadata to use `SIZE
EXACT: ... BYTES`. Ultimate raw-host-name display still needs an overlay-backed
implementation and physical UI evidence. Aggregate inventory remains 25/25
suites and 42/60 cases, now with 237 assertions.

VICE `vice_auto_20260816_170718` is the native-pattern execution authority.
Its 58 steps and 28 assertions retain unflagged rejection, real read-only IEC
pattern forwarding, typed WhatIf/filter output, zero completed WhatIf actions,
and denial of a bare native action. Explicit `--apply` then deletes only the
printed singleton `RFNX1`, copies exactly `RFNC1`/`RFNC2` from IEC 8 to a
fresh IEC 9 D81, and moves exactly `RFNM1`. Screen postconditions prove delete
and move source absence, destination presence, and byte-identical copy. Two
REU dumps parse as finished RFJ1 journals: copy mode has two successful exact
stems at plan offsets 0/12, and move mode has one successful exact stem at
offset 0. This strengthens cases 24, 38, 39, and 44 without changing their
already-proven status; case 52 remains partial because the fixture is flat.
Aggregate inventory is 26/26 suites, 273 assertions, 46 proven cases, 10
partial, and 4 missing.

Final admission authority is `vice_auto_20260816_171906`: the native plan now
has 61 steps/29 assertions and additionally rejects `9:/OUT` as a collection
destination on a regular flat IEC drive before enumeration, while the valid
root-target WhatIf and all applied delete/copy/move paths remain green. The
separate overlay D71 plan `vice_auto_20260816_171852` matches the real
`CAL26CFG.REL` entry as type `$13`, reports `UNSUPPORTED`, returns to the
prompt, and proves `8:/CAL26CFG.REL` is absent. Recursive regression `171947`
passes all 60 steps/27 assertions and the updated exact capability-byte oracle
at `$B12E-$B12F` and `$B592-$B597`; command-path regression `170922` passes all
83 steps/33 assertions. Aggregate inventory is 27/27 suites, 278 assertions,
46 proven cases, 10 partial, and 4 missing.

Overlay utility authority `vice_auto_20260816_173129` executes the seventh
cached sidecar. It proves explicit `history` renders the REU ring
oldest-to-newest and retains exact zero-execution WhatIf summaries for write,
write+delete, and media action classes. Recursive authority
`vice_auto_20260816_173239` supersedes the capability oracle with session
bytes `$AF7E-$AF7F` and all seven loaded flags at `$B3E2-$B3E8`; RFJ1
stop/continue remains green. Aggregate inventory is 28/28 suites and 287
assertions. No numbered row is silently promoted by this supplemental suite.

Cooperative tree authority `vice_auto_20260816_175239` executes the eighth
cached sidecar and proves its REU `INIT`, resident UCI yield, and bounded
`REPORT` path. Because VICE has no Ultimate UCI, the honest expected result is
`TREE FAILED F0 D0`; this is runtime-controller evidence, not physical nested
filesystem evidence and does not promote a numbered row. Recursive authority
`vice_auto_20260816_175442` relocates the post-STOP oracle to current session
bytes `$B121-$B122` and seven capability flags `$B586-$B58C`, all exactly `01`.

Superseding utility/tree authority `vice_auto_20260816_180719` also proves
sidecar-rendered drive discovery, the retained tape endpoint, sidecar 16-bit
D81 directory/free formatting, and the SoftwareIEC tree capability gate. In
UCI-less VICE, `TREE S3:/` correctly reports `SOFTIEC OFF`; the resident
SoftwareIEC enumeration adapter therefore has UI admission evidence but not a
mapped physical folder result. Recursive authority `vice_auto_20260816_180815`
passes after the resident lifetime union, with exact current session flags
`$B1A1-$B1A2` and seven capability flags `$B513-$B519`, all `01`. Aggregate
inventory remains 28/28 successful plans and 46 proven, 10 partial, 4 missing.

VICE `vice_auto_20260816_181108` adds the first successful end-to-end tree UI
cycle. `TREE 8:/` reads the actual overlay D81 through resident IEC I/O, shows
all nine files, and reports exactly `TREE DONE F9 D0`; screenshot authority is
`screens/readyfs_tree_iec_flat.png` within that run. This proves the common
controller's INIT/ADD/NEXT/DONE/REPORT runtime path, while remaining a flat
regular-IEC result rather than a physical UltimateDOS/SoftIEC nested-tree case.
Superseding recursive authority `vice_auto_20260816_181146` passes at session
`$B1FD-$B1FE` and seven capability flags `$B56F-$B575`, all `01`.

Current-build regression authority supersedes the mutable artifact-size
details above without changing case status. Configuration round-trip
`vice_auto_20260816_182919`, copy/move `182951`, and append `183209` all pass
with the established UI strings restored. Replacement rollback
`vice_auto_20260816_183813` derives its expected free count from the newly
seeded D64: both pre/post host directories and the final UI report 113 blocks,
`OLD` remains byte-identical, five entries remain, and no `RF~xx` file exists.
This avoids tying case 45 to a particular ReadyFS PRG size. Recursive authority
`vice_auto_20260816_184011` passes 60 steps/27 assertions, both RFJ1 parses,
and exact post-STOP bytes at session `$B212-$B213` plus seven overlay flags
`$B584-$B58A`, all `01`. Aggregate inventory is 28/28 suites, 293 assertions,
46 proven, 10 partial, and 4 missing.

Command-ID/capability authority is `vice_auto_20260816_191949`. The utility
sidecar decodes every long/short command name and renders capability screens
for `8:/`, `u:/USB1`, `s255:/`, and `t:/`; it also proves help discovery and
the unknown-command fallback. This is command/runtime evidence, not physical
UltimateDOS or SoftIEC operation proof, so no numbered row is promoted.
Current command-family regressions are config `191537`, copy/move `191556`,
append `191625`, dynamic rollback `191722`, smoke `191826`, and recursive
`192022`. The rollback fixture now has 104 blocks both before and after its
forced failure, demonstrating why its oracle must remain baseline-derived.
The latest recursive diagnostic bytes are session `$AF36-$AF37` and seven
overlay flags `$B2A8-$B2AE`, all `01`. Aggregate inventory is 28/28 suites,
305 assertions, 46 proven, 10 partial, and 4 missing.

Status authority is included in `vice_auto_20260816_192849`. After an unknown
command, `STATUS` reports CWD `8:/`, zero aliases, 256 REU banks, all resident/
overlay controller readiness labels, and `LAST DISPATCH: UNKNOWN`; after
creating alias `DEMO`, it reports one alias and `KNOWN`. This is intentionally
dispatch state rather than a fabricated filesystem return code and does not
promote a numbered case. Recursive authority `vice_auto_20260816_192947`
passes at session `$B06D-$B06E` and seven overlay flags `$B3E0-$B3E6`, all
`01`. Dynamic rollback `vice_auto_20260816_193027` remains green at a measured
104 blocks before/after. Aggregate inventory is 28/28 suites, 312 assertions,
46 proven, 10 partial, and 4 missing.

Find UI authority is `vice_auto_20260816_193554`. The overlay D81 command
`find 8:/ --include RFU*` traverses all nine files, displays only `RFUTIL`, and
reports `FIND DONE N1 F9 D0`; retain
`screens/readyfs_find_filtered.png`. This supplements the already-proven
complete-relative-stem matcher case without promoting physical nested-tree
cases: UltimateDOS and SoftIEC still require fresh-marker-gated C64U evidence.
Current recursive authority is `vice_auto_20260816_193818` with session bytes
`$B220-$B221` and overlay flags `$B595-$B59B`, all `01`. Current dynamic
rollback is `vice_auto_20260816_193859`, at a fixture-derived 104 blocks before
and after. Aggregate inventory is 28/28 suites and 314 assertions; numbered
status remains 46 proven, 10 partial, and 4 missing.

Read-only physical preflight
`logs/readyfs_c64u/preflight-20260816-resume-goal-1935` stopped at `failed:1`
after ten bounded FTP connection resets. No marker was fetched and no physical
mutation occurred. Never delete outside the exact owned USB1/SD roots, and do
not mutate even those roots until their exact marker files are freshly read.

Bounded content-view authority is `vice_auto_20260816_203314`. It exercises
four UI scenarios in the real overlay build: three-line `head`, two-line
`tail`, a 360-byte input whose 243-byte tail ring explicitly reports
`TAIL TRUNCATED`, and rejection of line count zero. Retained screenshots are
`readyfs_head_three_lines.png`, `readyfs_tail_two_lines.png`,
`readyfs_tail_bounded_truncation.png`, and
`readyfs_head_invalid_count.png`. Host controller tests independently cover
split chunks and byte accounting. These commands supplement the broader shell
probe; they do not promote any numbered physical cross-backend case.

Current recursive authority is `vice_auto_20260816_203751`, with session bytes
`$B226-$B227 = 01 01` and nine-sidecar readiness bytes
`$B59B-$B5A1 = 01 01 01 01 01 01 07`. Current replacement rollback is
`vice_auto_20260816_203833`, measured at 101 free blocks before and after.
Generated inventory is 28/28 successful plans and 325 assertions; numbered
status remains 46 proven, 10 partial, and 4 missing.

Streaming checksum authority is `vice_auto_20260816_205049`: `CRC32 8:/RFVIEW`
returns the independently calculated CRC-32/ISO-HDLC value `$6126E7F6` for
the exact 84-byte fixture. The retained screenshot is
`readyfs_crc32_stream.png`. Full utility authority is
`vice_auto_20260816_205132`; current recursive authority is
`vice_auto_20260816_205233` at session `$B222-$B223` and readiness
`$B597-$B59D = 01 01 01 01 01 01 07`; rollback authority is
`vice_auto_20260816_205318` at 101 blocks before/after. Aggregate inventory is
29/29 successful suites and 331 assertions. CRC is additional shell evidence
and does not alter the 46 proven/10 partial/4 missing physical case split.

Built-in diagnostic authority is `vice_auto_20260816_221431`. The atomic
`test` command prints `RFT1 SUITES`, names `CORE`, and reports
`RFT1 CORE PASS 4/4`; the checks cover the bounded count parser, rejected
zero/overflow counts, the standard CRC-32 `123456789` oracle, and minimum
content-ring workspace. Both retained test screenshots were visually
inspected. Full utility authority is `vice_auto_20260816_221450`; recursive
authority is `vice_auto_20260816_221535` with session
`$B20D-$B20E = 01 01` and readiness
`$B582-$B588 = 01 01 01 01 01 01 07`; rollback authority is
`vice_auto_20260816_221634`. The current inventory is 29/29 successful suites
and 334 assertions. Numbered status remains 46 proven, 10 partial, 4 missing.

Safe-format authority is `vice_auto_20260816_224759`. It uses a newly created
drive-9 D81 and proves the unchanged `--whatif` plan (`M1`, zero completion),
cached legacy-profile admission, unprobed-drive refusal, rejection without
`--disposable`, rejection without `--yes`, 16-byte label and two-byte ID
bounds, and successful exact `N:LAB,RF` command-channel execution. The final
UI directory reports `LAB` and 3160 free blocks; independent `c1541` readback
reports ID `RF` and an empty image. This is supplemental command evidence and
does not silently promote physical mount/swap cases 53–56.

Current authorities after format compaction are content/RFT1
`vice_auto_20260816_224611`, utility/history `224915`, recursive/RFJ1
`232027`, and replacement rollback `232427`. The recursive post-stop audit now
resolves its session/overlay sentinel addresses from
`readyfs-overlay.lbl` on every run instead of hard-coding a moving BSS layout.
Generated inventory is 30/30 successful suites and 348 assertions; numbered
status remains 46 proven, 10 partial, and 4 missing.

Cooperative script authority is `vice_auto_20260817_001141`. The new `run`
suite proves successful multi-command execution, `onerror stop|continue`,
`expect rc N` pass and mismatch paths, nested-run rejection, noninteractive
prompt refusal, and an unchanged existing file after an overwrite would have
required confirmation. Script fixture bytes are C64/PETSCII-compatible
uppercase text; host lowercase ASCII is not a valid C64 SEQ command fixture.
Current editor authority is `vice_auto_20260817_001549`, with its 256-byte
memory oracle now resolved from `_line_buf` in the current linker labels;
scrollback is `001605`, recursive/RFJ1 plus ten-sidecar admission is `001612`,
and replacement rollback is `001649`. Generated inventory is now 31/31
successful suites and 362 assertions; numbered status remains 46 proven,
10 partial, and 4 missing.

UCI recovery groundwork is now executable. `readyfs_uci_test` models an
asynchronous PUSH that initially still reads IDLE, then BUSY, one ABORT request,
ABORT_P service, pending data/status drains, DATA_ACC, quiet idle, and a clean
subsequent UltimateDOS IDENTIFY. Current VICE utility authority
`vice_auto_20260817_002400` proves `probe recover` reports capability-honest
`UCI RECOVER: OFF` without hanging when no UCI exists. The true Terminal-owned
speed runner now places the read-only interrupted-IDENTIFY/re-identify probe
between SoftIEC identify and directory listing at 1/16/64 MHz; physical proof
is still gated by fresh ownership-marker access and was not attempted here.
Current editor is `002517`, batch scripts `002532`, recursive/RFJ1 `002551`,
and rollback `002634`. Inventory is 31/31 suites and 363 assertions; the
numbered split remains 46 proven, 10 partial, and 4 missing.

Tape capability authority is included in `vice_auto_20260817_002914`. The UI
identifies `t:/` as sequential-only and explicitly refuses `dir t:/`, a
random-access `copy t:/x 8:/x`, `delete t:/x --yes`, and `tree t:/` before any
device I/O; the existing volume check remains `NO TAPE FREE`. This promotes
the tape requirement from endpoint-only missing to a partial, capability-honest
driver contract. Actual bounded sequential KERNAL tape read/write against a
disposable TAP image remains unimplemented. Inventory is 31/31 suites and
367 assertions; numbered case status is unchanged.

Physical UCI recovery authority is
`logs/readyfs_c64u/speed-matrix-20260817-uci-recover-only`. In a true
Terminal-owned run, the recovery-only matrix passed at 1, 16, and 64 MHz. At
each speed the fresh screen reads `UCI RECOVER: QUIET`, then
`UDOS1: ULTIMATE-II DOS V1.2`, then returns to `RF>`. The matrix restored and
freshly read back the exact original `TurboEnable Bit` / `64` settings. This
promotes numbered case 59; the generated split is now 47 proven, 9 partial,
and 4 missing. The earlier all-read-only attempt
`speed-matrix-20260817-uci-recover` is explicitly failed and non-authoritative:
its 1 MHz recovery passed, but the following large USB1 directory case failed;
both its normal trap and a separate exact-payload restore verified 64 MHz.

Physical flat cross-backend authority is
`logs/readyfs_c64u/cross-owned-20260817-iec-udos-roundtrip-k`. A true
Terminal-owned suite attached a disposable D81 through the REST multipart
mount API, proved its 17-block PRG, reread both exact 116-byte owner markers
before every mutation, and wrote only the fresh preserved USB1 folder
`cross-20260817-iec-udos-roundtrip-k`. IEC→UltimateDOS and UltimateDOS→IEC
each copied 4069 bytes, returned `VERIFY: IDENTICAL`, retained type `$11`, and
passed independent comparison; the final IEC directory contains `RFROUND`.
Drive A `enabled/bus_id/type/image_file/image_path` exactly matches its
captured baseline after removal. Cases 40 and 41 are therefore proven, making
the generated split 49 proven, 9 partial, and 2 missing. No host file or test
folder was deleted; never delete or mutate outside the two exact marker-owned
USB1/SD roots.

SoftwareIEC 3.14 negative evidence does not promote cases 42 or 43.
`softiec-owned-20260817-040632` stops at unsupported `MD:`, `040857` at
unsupported staged `R:`, and `041716` after a too-long absolute `CD:` was not
verified. All passed fresh dual-marker gates, used unique exact-owned folders,
stopped before later actions, and deleted nothing. Independent read-only UI
shows the intended folder empty and root `sfa.seq` absent.

The repaired adapter consumes the command-channel reply and requires `00`
before leaf I/O. True Terminal-owned read-only run
`ui-readonly-soft-status-longpath-20260817-0430` proves the long path now fails
closed. This is safety evidence, not interoperability proof: cases 42 and 43
remain missing until component-wise `CD:` enables successful owned flat and
recursive copy matrices.

The component generator now exists in utility slot 7, but the firmware media
bridge remains unproven. Read-only `ui-readonly-soft-root-dir-20260817-0453`
shows the global namespace (`/`, `SD`, `FLASH`, `TEMP`, `USB1`), while
`ui-readonly-soft-component-diag-20260817-0445` records the attempted media
transition failing. ReadyFS therefore fails before leaf I/O and reports
`UNSUPPORTED` for `dir s0:/`; this does not promote cases 42 or 43.

Current VICE utility authority is `vice_auto_20260817_050201`: it exercises
history, WhatIf, capabilities, content tools, and proves `status` reports the
previous unknown result as 1 and the subsequent successful alias result as 0.
Current batch authority is `vice_auto_20260817_050249`, including typed
usage/not-found/conflict expectations. Generated reports remain 31/31 latest
plans, 49 proven, 9 partial, and 2 missing cases.

Superseding utility authority is `vice_auto_20260817_052447`. In addition to
the prior status/history/content/capability coverage, it proves the stable
unavailable result (`DIR S0:/`, `SOFTIEC OFF`, `LAST RESULT: 2`) and stable
unsupported result (`DIR T:/`, `UNSUPPORTED`, `LAST RESULT: 7`). Both new
screenshots were visually inspected. Batch authority is `052540`; the current
inventory is 31/31 suites and 372 assertions, with the same 49/9/2 case split.

SoftwareIEC bridge evidence is now stronger but does not promote cases 42/43.
Independent Terminal probes `softpath-readonly-20260817-softpath-source-e`,
`source-h`, and `source-i` prove the global-root-to-USB1 transition, PETSCII
underscore conversion, exact owned-run traversal, and entry into preserved
`rf061009`, all with DOS `00`. `source-i` then proves an absent `sfa.seq` OPEN
returns DOS `62` even though `cbm_open` returns 0. The firmware's empty-folder
directory stream can omit its terminal record, so the mutation suite
`softiec-owned-20260817-061009` stopped after fresh dual-marker checks and
folder creation, before any file write; it deleted nothing.

Focused post-change VICE authorities are editor `vice_auto_20260817_062227`,
batch `062243`, utility `062304`, smoke `062532`, and paths `063042`. The path
plan now expects current typed-result wording and is emitted with sufficient
prompt pacing to avoid stale-screen input concatenation. Generated inventory
is again 31/31 successful; numbered status remains 49/9/2.

Superseding physical SoftwareIEC evidence promotes case 42. Production run
`softiec-owned-20260817-nested-parent-prod-full` performs both flat copy
directions inside fresh preserved `rf091800/rf100154`, with exact owner gates,
`VERIFY: IDENTICAL`, immediate logical reads, and a nested directory/file
write/read. Its last assertion alone used stale uppercase raw spelling.
Final-artifact continuation `softwrite-noftp-20260817-treeverify-final` proves
lowercase `fromu.seq`, both logical contents, independent compare, raw
`nested/inside.seq`, and both final owner markers. Case 42 is PROVEN. Case 43
is PARTIAL: nested physical state is proven, but recursive whole-tree copy
remains. Reports are 31/31 suites, 372 assertions, 50 proven, 10 partial, and
0 missing. Final focused VICE authorities are utility `101607`, smoke `101701`,
and paths `101711`.

Superseding recursive physical evidence promotes case 43. True
independent-Terminal run `rr5-final3` loads the build-owned overlay fixture,
revalidates both exact 116-byte owner markers, and executes one whole-tree
`copy ... --recursive --force` from UltimateDOS to SoftwareIEC. Its capture
shows `RECURSIVE PLAN F4 SELECTED 4`, inline `VERIFY: IDENTICAL` for 10, 11,
and 7 bytes, then `BATCH DONE 4/4 FAIL 0`. Three subsequent comparisons, raw
directory listing, and logical nested read all pass. Fresh read-only process
`rr5-verify` independently proves `sfa`, `fromu`, raw `nested/inside.seq`, the
cross-backend compare, both final owner markers, and exact Drive A restoration.
The physical destination is preserved as `rf091800/rr111505`; never delete it.

Firmware 3.14's REST attachment runner remained present but returned
404/`Cannot open file`. The harness therefore used a bounded normal IEC load
of build-owned `READYFS-OVERLAY` from the disposable mounted D81. Per-second
REST screen DMA during the recursive command stalled the nested transition in
preserved diagnostic `rr5-final2`; the successful run gives file I/O a quiet
window before one bounded capture. This is automation transport discipline,
not application pacing. The numbered split is now 51 proven, 9 partial, and
0 missing after report regeneration. Full `make readyfs` passes at resident
`$B5A0`, monolithic `$C491`, and recursive sidecar `$F67`; current recursive
VICE authority `vice_auto_20260817_135206` and its post-stop capability memory
oracle pass. The generated UI inventory is 32/32 suites with 373 assertions.

## 2026-08-17 — physical Ultimate media lifecycle

True independent-Terminal run `softwrite-noftp-media-145816` promotes cases
53 and 54. After fresh USB1 and SD owner-marker reads, ReadyFS creates the
preserved owned folder `md145816`; the corrected single-action completion path
prints `DIRECTORY CREATED` and completes its RFJ1 ACK. REST then creates
uppercase `DISK1.D81` and `DISK2.D81` only inside that folder after separate
dual-owner gates. ReadyFS lists both images, mounts `DISK1.D81` on drive 8,
requests a firmware swap, and dismounts it. Independent `/v1/drives`
snapshots prove the exact sequence `DISK1.D81` → `DISK2.D81` → empty image
fields, while the final snapshot exactly matches the original enabled bus-8
1581 state. Both owner markers pass again after completion and no delete is
issued.

The earlier failed lowercase-fixture run for
`md144209/{disk1.d81,disk2.d81}` remains preserved as a diagnostic; it is
superseded by the successful exact-name metadata authority recorded below.
Earlier empty diagnostics `md140757` and `md142820` are also preserved. After
replacing a stale `RF> #` cursor
oracle with the actual `RF>` prompt, current action authority
`vice_auto_20260817_151512` passes, restoring the UI inventory to 32/32 suites
and 373 assertions.

## 2026-08-17 — case 55 firmware boundary and refreshed VICE authority

Case 55 remains PARTIAL for a capability-honest reason. Current official
firmware 3.14 target-5 source implements UCI commands `$01` and `$10`–`$16`,
but no partition add/delete handlers for `$20/$21`. True Terminal-owned runs
`softwrite-noftp-20260817-155612` and
`softwrite-noftp-20260817-160912` passed both exact owner gates and the
read-only source tree/CRC prechecks, then returned target status `$01` for the
map command. No partition 1 appeared, partition 0 stayed unchanged, Drive A
was restored exactly, and no filesystem mutation or delete occurred. These
runs demonstrate unsupported target capability, not failure of the
ReadyIRC-derived UCI transport; the latter remains physically proven at 1,
16, and 64 MHz.

The future map encoder now retains `/USB1` and normalizes typed PETSCII
underscore `$A4` to host underscore `$5F` at the SoftIEC boundary. Promotion
requires firmware/device that actually exposes `$20/$21`, followed by a
marker-gated successful map/unmap and exact config restoration. Do not retry
path variants on firmware 3.14. Fresh current-build VICE passes are smoke
`vice_auto_20260817_160934`, paths `vice_auto_20260817_160944`, pipeline
actions `vice_auto_20260817_161030`, append `vice_auto_20260817_160143`, and
recursive plan `vice_auto_20260817_161401`. The aggregate remains 32/32 suites,
373 assertions, and 53 proven / 7 partial / 0 missing cases; current build is
resident `$B523`, monolithic `$C40E`, recursive `$F67`.

## 2026-08-17 — case 52 physical filtered WhatIf authority

Case 52 is PROVEN by true Terminal-owned read-only run
`softwrite-noftp-whatif-filter-casefold-180400`. The current overlay build
walks the existing nested UltimateDOS source and applies `--include
**/inside` to its complete logical relative stems. The captured preview is
`RECURSIVE PLAN F4 SELECTED 1` followed by
`PLAN W1 D0 M0; DONE W0 D0 M0`.

The oracle is independent of the preview counters: the harness compares exact
before/after directory screens for the source root, its nested directory, and
the mapped destination; compares CRC lines for `sfa.seq`, `fromu.seq`, and
`nested/inside.seq`; refuses a pre-existing destination and proves `wf180400`
was not created; rereads both exact owner markers before and after; and proves
the final Drive A JSON is byte-for-byte identical to the original snapshot.
All 21 command rows pass.

The diagnostic sequence is preserved. `tree-spelling-171326` and
`tree-bytes-172216` establish the real mixed-case UCI stem, while
`match-literal-172014` proves the matcher core. Failed read-only attempts
`whatif-filter-162725`, `whatif-filter-logical-164055`,
`whatif-filter-fixed-165954`, `whatif-filter-atomic-172920`, and
`softwrite-noftp-whatif-filter-asm-175230` all remained `W0 D0 M0` and
restored Drive A. The correction folds ASCII and PETSCII case coherently on
cc65 and keeps access-name normalization in the matcher sidecar.

Current recursive VICE authority `vice_auto_20260817_180205` and full build
pass. The generated split is 54 proven, 6 partial, and 0 missing cases; the UI
inventory remains 32/32 suites with 373 assertions.

## 2026-08-17 — case 60 forced-failure recovery authority

Case 60 is PROVEN by true Terminal-owned run
`softwrite-noftp-forced-restore-put-16-183320`. The harness admits only an
explicit read-only WhatIf/CPU-speed combination. It captures the entire U64
settings object and Drive A, applies Manual/16 through per-setting firmware
PUTs, reads the speed back, preloads ReadyFS, and passes the USB1 and SD exact
owner markers twice before writing its deliberate-trigger record and exiting
with status `73`.

The EXIT trap runs the post-failure owner oracle while ReadyFS is still live:
both exact markers pass again. It then removes the disposable D81, restores
Drive A, and restores the saved configuration. The aggregate restore returned
HTTP 500, deliberately exercising the bounded recovery helper; that helper
reports success. Complete original/restored U64 JSON objects and complete
original/restored drive JSON objects compare equal. Final status is the
expected `failed:73`; restoration failure would replace it with 97. No
filesystem object or media mapping was changed.

Excluded diagnostics `softwrite-noftp-forced-restore-182200` and
`softwrite-noftp-forced-restore-16-183100` failed during aggregate config
admission before their trigger. Their exact config recovery is retained, but
post-reboot BASIC screens are not owner evidence. Generated status is now
58 proven, 2 partial, and 0 missing cases; 32/32 VICE suites and 374 assertions
remain green.

## 2026-08-17 — lowercase host/image metadata and units proven

True Terminal-owned authority
`softwrite-noftp-metadata-lowercase5-20260817-2004` promotes cases 19, 33,
and 34. On preserved owned image `md144209/disk1.d81`, `stat` displays the
canonical `u:/USB1/.../disk1.d81` path separately from exact UltimateDOS
access spelling `disk1.d81` and decoded host spelling `disk1.d81`; it reports
type `$10`, exact size `819200 BYTES`, and `STATUS: OK`. This firmware returns
that safe lowercase name directly rather than bracket-hex encoding it.

The same run reports SoftwareIEC partition 0 on bus 11, target `$01`, and
`FREE UNAVAILABLE` without inventing capacity. It then mounts the lowercase
host image on drive 8 and independently reports contained volume `RFMEDIA1`
with `3160 C64 BLOCKS`, proving host filename, image byte size, internal volume
identity, and filesystem block units are distinct. It dismounts successfully,
passes both exact USB1 and SD owner markers before, around, and after the media
lifecycle, preserves both images, and restores Drive A byte-for-byte.

Excluded oracle-development runs
`softwrite-noftp-metadata-lowercase-20260817-1927`,
`softwrite-noftp-metadata-lowercase2-20260817-1933`,
`softwrite-noftp-metadata-lowercase3-20260817-1943`, and
`softwrite-noftp-metadata-lowercase4-20260817-1953` remain preserved. The
first stopped before owner admission due a shell parse race while its running
script was edited; the others passed progressively more read-only checks but
stopped on overly strict screen-text oracles. All restored Drive A exactly and
none changed filesystem contents; they are not full authority.

VICE `vice_auto_20260817_230948` is the current command-path authority. After
proving ordinary VICE drive 8 is cached as `LEGACY P0 F0 I0` and denying the
partition operations, the harness DMA-stashes only ReadyFS's four-byte IEC-8
profile record into its REU session bank. ReadyFS then reports
`PROFILE: SD2IEC P1 F1 I1` and dispatches translated `DIR 8.1:/`,
`TREE 8.1:/`, `MKDIR 8.1:/RFSIM`, and
`MOUNT 8.1:/RFSIM.D64 --FORCE` through resident IEC I/O. The underlying VICE
1581 is deliberately not represented as SD2IEC: it returns `DIR OPEN FAILED`,
`TREE FAILED F0 D0`, and `FAIL` where appropriate. The tree result proves
profile-gated root translation and handoff to the common cooperative tree
controller without claiming nested hardware enumeration. The mkdir path
reaches clean `CREATED` action completion after retaining its canonical path
for RFJ1 ACK, and the wrapper proves the complete D81 fixture byte-identical
before and after. Case 56 remains PARTIAL only for successful execution on real
SD2IEC hardware. Current generated inventory is 32/32 suites and 380
assertions.

## 2026-08-18 — sequential tape media and cross-device replay

Disposable TAP recording authority is `vice_auto_20260818_025149`. It writes
named `RFSEQ`, reads its 9-byte payload, copies the 84-byte `8:/RFVIEW` fixture
to named `RFCOPY`, proves sequential metadata/capabilities and WhatIf output,
and proves append/delete/move/rename refusals. The TAP verifier reports 97997
recorded bytes.

Fresh-session readback authority is `vice_auto_20260818_025218`: `RFCOPY` is
read once from KERNAL device 1, stored/replayed through REU, staged on a fresh
D64, verified, promoted to `TAPOUT`, and compared byte-identical with
`8:/RFVIEW`. `vice_auto_20260818_025055` independently proves disk write,
paged tape TYPE, then another verified disk write in one session. The focused
KERNAL record oracle remains `vice_auto_20260817_235139`.

The target fixes are guarded: tape OPEN and post-tape IEC writes reset shared
KERNAL status, the packed target formatter emits `name,s,w`, resident
case-folding avoids overlay DMA during IEC scans, and assembly spool EOF jumps
unconditionally to success after the replay cursor reaches the stored length.
Current inventory is 36/36 suites and 414 assertions; numbered status remains
58 proven / 2 partial / 0 missing because tape is supplemental scope evidence.
