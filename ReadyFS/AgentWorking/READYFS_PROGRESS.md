# ReadyFS Progress

## 2026-08-15 — architecture grounding

- Confirmed ReadyIRC and UCI Tester share the current bounded asynchronous UCI
  transaction pattern and 1/16/64 MHz failure-bound rationale.
- Confirmed UltimateDOS targets 1 and 2 have independent state, while SoftIEC
  target 5 exposes partition mapping and FAT/IEC name translation.
- Established endpoint-first canonical paths and the owned-root hardware-test
  boundary documented in `READYFS_SAFETY.md`.
- No C64 Ultimate filesystem mutation was performed during planning.

## 2026-08-15 — standalone slice and VICE smoke

- Built with `make readyfs`; produced `artifacts/readyfs/readyfs.prg` and
  `artifacts/readyfs/readyfs-lab.d81`.
- Added the ReadyFS UCI transport to
  `python3 build_support/verify_readyfs_uci_protocol_contract.py`; it passes alongside
  ReadyIRC, System Info, and UCI Tester.
- Ran `/bin/bash build_support/run_readyfs_vice_smoke.sh`.
- First failure: the banner was overwritten because CR and LF were handled as
  interchangeable. Fixed the console newline contract to emit CR+LF.
- Second failure: in-place tokenization overwrote the delimiter before the
  read cursor advanced. Fixed multi-argument parsing.
- Passing run: `logs/vice_auto_20260815_174951`.
- Proven in VICE: standalone launch, REU detection/history initialization,
  help UI, 255-byte editor path entry, canonical Ultimate path acceptance, and
  `delete ... --dry-run` reporting zero writes/deletes/mounts.
- Ultimate-specific UCI behavior remains unproven until the owned-root physical
  1/16/64 MHz suites run; VICE is not being used as UCI evidence.

## 2026-08-15 — physical C64 Ultimate read-only preflight

- Fixed the Terminal launcher to pass absolute script/workspace paths; the
  first attempted tab therefore performed no REST, FTP, or filesystem action.
- Successful true Terminal-owned run:
  `logs/readyfs_c64u/preflight-20260815-183301` (`status.txt` = `success`).
- Read-only REST evidence identifies a C64 Ultimate Starlight, firmware 3.14,
  FPGA 121, core 1.47. The Command Interface and 16 MB REU are enabled.
- Current CPU speed is 64 MHz. Drive A is an enabled 1581 on IEC 8; SoftIEC is
  enabled on IEC 11 with internal default path `/USB0/`.
- FTP reports physical roots `USB1` and `SD`. This establishes that display /
  user-facing volume spelling cannot be assumed to equal Ultimate's internal
  pathname (`USB1` versus `/USB0/`); ReadyFS discovery must preserve a raw
  backend name and expose a stable logical volume alias separately.
- Both media roots were listed read-only. No directories, files, settings,
  mounts, or drive state were changed.

## 2026-08-15 — ReadyFS on physical C64U at 64 MHz

- Launched the standalone `readyfs.prg` and drove its UI through the C64
  keyboard buffer from independent Terminal-owned automation.
- Passing read-only cases prove UCI discovery at `$DF1C` (`$C9`),
  UltimateDOS identity `ULTIMATE-II DOS V1.2`, and SoftIEC identity
  `SOFTWARE IEC TARGET V1.0` on bus 11.
- Hardware exposed a firmware-compatibility detail: SoftIEC IDENTIFY on this
  firmware returns legacy ASCII `00,OK`, while the current target document
  specifies binary `$00`. ReadyFS now accepts both success encodings without
  accepting empty status.
- A focused `READ_DIR` run exposed a 64 MHz race after a six-byte
  `DATA_MORE` block: ordinary C call overhead missed the brief required
  `MORE -> COMMAND_BUSY` transition and later saw the next `$B0` state.
  ReadyFS now performs only the DATA_ACC write plus bounded transition
  observation in a tight assembly helper; the C transport continues to own
  all queue draining, timeouts, and recovery. The protocol verifier passes.
- UltimateDOS directory results are a multi-block response to one READ_DIR.
  Added a block callback so entry boundaries are retained while every block is
  drained. `dir u:/USB1` now completes at 64 MHz with 105 entries and returns
  to the prompt; UI displays the first 14 and reports the full count.
- Passing focused evidence:
  `logs/readyfs_c64u/ui-readonly-20260815-185222`.
- Passing four-case 64 MHz read-only suite:
  `logs/readyfs_c64u/ui-readonly-20260815-185313` (all rows PASS).
- The earlier `ui-readonly-20260815-183918` directory failure is retained as
  regression evidence and is not counted as a pass.

## 2026-08-15 — aliases, relative paths, and VICE UI expansion

- Added eight exact-root aliases with create/list/use/remove commands. Alias
  state is mirrored into a reserved REU session region; explicit persistence
  is still pending `config save`.
- `@name:/suffix` expands to a canonical backend path, and any `..` in an
  alias-relative suffix is rejected as `path escapes alias root` before I/O.
- Added relative path resolution against `cwd` and endpoint-root `/path`
  resolution (for example `/other` while on `u:` becomes `u:/other`).
- First expanded run `vice_auto_20260815_185933` exposed command-output
  corruption at the KERNAL bottom-row scroll boundary. A clean-page guard now
  keeps the visible prompt stable; full REU scrollback is still pending.
- Passing run: `logs/vice_auto_20260815_190200`, with JSON manifest, Markdown
  trace, decoded screens, state snapshots, and screenshots.
- Newly proven matrix cases: 3, 4, 12, 13, 14, 15, 16, 17, 18, and 20.

## 2026-08-15 — owned physical mutation roots

- First setup `owned-roots-readyfs-20260815-190330-78838` created only its
  unique USB1 root and marker, then stopped because FTP hides dotfiles from
  directory listings. The root remains preserved and will not be reused.
- Verification now downloads the exact marker and byte-compares it rather
  than trusting a directory listing.
- Successful independent Terminal-owned setup:
  `logs/readyfs_c64u/owned-roots-readyfs-20260815-190355-79014`.
- Active roots for later mutation suites are exactly
  `u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
  `u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`.
- Both contain marker
  `.readyfs-owner-readyfs-20260815-190355-79014`, proven by upload/download
  byte comparison. No pre-existing path was reused and nothing was deleted.

## 2026-08-15 — staged mutations and UltimateDOS file metadata

- Passing VICE mutation suite: `logs/vice_auto_20260815_192229`.
  It proves empty SEQ creation, `write --line`, staged forced replacement,
  reopen/read byte verification, default-no replacement/delete prompts,
  forced delete, and mutation-free `new --dry-run` behavior.
- UltimateDOS firmware 3.14 returned `82 FILE NOT FOUND` from `FILE_STAT` for
  existing long host paths, both as a full path and after parent navigation.
  ReadyFS therefore resolves the exact raw leaf through a parent-directory
  scan, and obtains file metadata with `OPEN_FILE` plus `FILE_INFO`.
- Passing physical metadata evidence:
  `logs/readyfs_c64u/ui-readonly-20260815-193851`. The command returned to the
  prompt with a valid 37-byte data response and five-byte OK status.
- Two earlier owned mutation runs (`owned-mutations-20260815-192350` and
  `owned-mutations-20260815-192659`) safely stopped after creating their unique
  empty test file because the old `FILE_STAT` verification failed. They did
  not proceed to replacement or deletion and remain preserved as evidence.
- Passing independent Terminal-owned 64 MHz mutation suite:
  `logs/readyfs_c64u/owned-mutations-20260815-194141`. Cases RF-HW-64-101
  through 103 prove guarded empty-file creation, staged new-file write, and
  forced staged replacement inside the active owned USB1 root. Every operation
  first downloaded and byte-compared the ownership marker; both writes were
  reopened and compared on the C64 before completion.
- FTP round trips show that the UltimateDOS SEQ host bridge represents the
  C64 text as uppercase host bytes and converts the C64 line terminator to LF.
  The passing host oracle observed `HW ALPHA\n` and `HW REPLACED`. This is a
  text-bridge capability, not evidence of byte-preserving binary transfer;
  later PRG/binary copy cases must use a binary-preserving path and oracle.

## 2026-08-15 — verified IEC transfers and editor/history UI

- Passing VICE copy/move suite: `logs/vice_auto_20260815_194550`.
  It proves copy and move dry-runs leave the inspected destination absent,
  same-device staged copy is byte-identical, and move removes its source only
  after the copied destination verifies. The final screen shows `COPYTEST`
  absent and `MOVED` present.
- Added stock-C64 End semantics: Shift+Home/PETSCII `$93` is treated as End
  while the line editor is active. Home remains PETSCII `$13`.
- Passing VICE editor/history suite: `logs/vice_auto_20260815_194939`.
  It proves left/right middle insertion, insert/overwrite mode, Home/End plus
  deletion at both ends, and REU-backed Up/Down recall followed by editing and
  re-execution.
- Numbered UI matrix now has 27 proven cases, satisfying the lower bound while
  the target remains 60 and backend/recursive/mount coverage is still open.

## 2026-08-15 — append/readback and physical 1/16/64 MHz matrix

- Added staged `append` with a sibling temporary, backup/rollback swap, and
  post-swap verification using a 32-bit byte count plus CRC-16 signature. REL
  append is rejected explicitly because it requires record semantics.
- Added `type`/`cat` readback. Passing VICE run
  `logs/vice_auto_20260815_195522` proves `ONE` followed by `TWO` and eight
  bytes after append; matrix case 37 is now proven.
- Copy/type byte counters and UltimateDOS size display now use paired 16-bit
  words, avoiding both cc65 `long` overhead and the prior 65,535-byte wrap.
- First speed run `speed-matrix-20260815-200251` passed UCI/UltimateDOS/
  SoftIEC identify at 1 MHz and completed the directory command, but the
  temporary console guard cleared its summary before capture. The suite failed
  safely and restored the exact original turbo settings. Directory previews
  are now eight entries with a retained full count for both IEC and Ultimate.
- Passing read-only matrix:
  `logs/readyfs_c64u/speed-matrix-20260815-200638`. UCI discovery,
  UltimateDOS identify, SoftIEC identify/bus query, and the complete 106-entry
  multi-block `u:/USB1` directory stream pass at both 1 and 16 MHz. Together
  with `ui-readonly-20260815-185313`, the same transport path is proven at
  1, 16, and 64 MHz.
- Passing guarded read/write matrix:
  `logs/readyfs_c64u/speed-matrix-20260815-201026`. At both 1 and 16 MHz, six
  cases prove create, staged write, forced replacement, staged append,
  verified copy, and verified move. Every case revalidated the owned-root
  marker; FTP byte oracles matched and moved sources were absent.
- Passing expanded 64 MHz mutation run:
  `logs/readyfs_c64u/owned-mutations-20260815-201654`, covering the same six
  cases. Thus the ReadyIRC-derived UCI state machine is physically proven for
  current ReadyFS read, streamed-directory, write, rename, and delete paths at
  1/16/64 MHz. Explicit injected transport-recovery case 59 remains open.
- All speed wrappers restored `Turbo Control = TurboEnable Bit` and
  `CPU Speed = 64`; no configuration or path outside the owned test root was
  left changed.

## 2026-08-15 — paths, config, scrollback, folders, and memory regressions

- Passing path/matcher run `logs/vice_auto_20260815_205402` proves absolute
  normalization, removal of `.`, bounded `..`, refusal to cross endpoint or
  image roots, case-insensitive component `*`/`?`, and recursive `**`. The
  matcher is not yet wired into recursive copy/delete filters, so matrix case
  23 remains open.
- Added versioned RFC1 config persistence for cwd and aliases. Save is staged,
  CRC-verified, and rollback-capable; load validates into REU-held rollback
  state before commit. Passing runs are `vice_auto_20260815_205815` and, after
  shared-workspace refactoring, `vice_auto_20260815_212933`.
- Added REU-backed physical-screen history (24 pages) with F1/F3 stock-key
  Page Up/Page Down fallbacks. Passing runs are `vice_auto_20260815_210843`
  and the post-refactor regression `vice_auto_20260815_213116`.
- Explicit rename now uses backup/rollback and same-backend constraints.
  UltimateDOS mkdir/rmdir opcodes are implemented; a regular 1581 correctly
  reports capability-honest `MKDIR FAILED` rather than pretending native
  folder support. Passing VICE evidence is `vice_auto_20260815_202433`.
- Added confirmation/force/dry-run-gated Ultimate image mount/dismount/swap and
  SoftIEC map/unmap command encoders. They remain physically unproven and will
  only be exercised with disposable images/owned roots plus an exact pre-test
  configuration snapshot and restoration.
- Reduced resident BSS through shared command streams, path workspaces, and a
  single-row wildcard DP buffer. Current map ends near `$BEE5`: valid for this
  standalone build, but about 2.3 KB beyond the future ReadyOS `$B600`
  overlay boundary. The overlay runtime must preserve the existing direct-PRG
  C64U test path, whose REST runner does not currently provide sidecars.
- Latest complete smoke is `vice_auto_20260815_211700`; post-refactor
  copy/move regression is `vice_auto_20260815_213052`. The UCI protocol
  verifier passes in every build.
- Physical folder cases were attempted in
  `owned-mutations-20260815-202509`, `20260815-203032`, and
  `20260815-203104`, but the C64U FTP service began resetting marker reads.
  The suites stopped at their ownership gate or before a completed folder
  result. No folder case is counted as proven and no marker check is bypassed.

## 2026-08-15 — normalized capacity, first real overlay, and action filters

- Added `volume`/`free` with backend-honest units. IEC uses cc65's terminal
  directory return to retain the full 16-bit blocks-free value; the test D81
  reports volume `READYFS LAB` and 3003 free C64 blocks. UltimateDOS and
  SoftwareIEC explicitly report that their UCI APIs do not expose host byte
  capacity; tape reports free space as not meaningful. Passing VICE run:
  `vice_auto_20260815_213528`, regression `220017`.
- Added a SoftwareIEC stream backend using the discovered bus and native
  partition-prefixed names (`s250:/x` -> `250:/x`). It supports staged file
  operations, parent-directory scans, nested directory listings, and MD/RD
  command paths; direct physical behavior remains unproven.
- Reworked aliases as an REU-backed eight-slot table with a single resident
  slot and preserved the byte-for-byte RFC1 config format. Config validates a
  staged REU image before commit and restores the saved image on commit
  failure. Alias/config regressions pass in `vice_auto_20260815_214434`,
  `214458`, and `215447`.
- Added a real standalone overlay variant:
  `readyfs-overlay.prg`, `readyfs-match.prg`, and
  `readyfs-overlay-lab.d81`. Its linker enforces the `$B600-$C5FF` window;
  resident BSS currently ends at `$B1C5`. Boot closes stale autostart channels,
  loads the `$4D1` sidecar at `$B600`, caches it in REU, banks BASIC out for
  cache transfer/execution, and restores the CPU port. Passing overlay UI run:
  `vice_auto_20260815_215425`. The monolithic `readyfs.prg` remains the direct
  REST hardware artifact because that runner cannot supply sidecars.
- Added actual and dry-run `--include`/`--exclude` filtering against the full
  canonical relative stem. Passing `vice_auto_20260815_220211` covers accepted
  include, excluded source, component-boundary mismatch, zero-action plans,
  and an accepted verified copy. Recursive enumeration remains open.
- Prepared a marker-gated SoftwareIEC physical suite. Attempt
  `softiec-owned-20260815-215701` stopped locally before hardware due a fixed
  shell variable bug. Attempts `215734` and `215809` byte-compared the owner
  marker successfully, then all REST PRG-launch attempts reset/timed out.
  Neither run launched ReadyFS, checked/mapped partition 250, or mutated files.

## 2026-08-15 — bounded recursive-plan foundation and second overlay

- Centralized the REU session allocation map and fixed a previously unnoticed
  overlap: the live scrollback page ended at `$81A8` while config rollback had
  started at `$8000`. Config rollback now starts at `$8400`; its complete RFC1
  image, the staged image, and the `$A000-$DFEF` plan arena are disjoint.
  Overlay caches subsequently moved to their own reserved REU bank. Config and
  scrollback regressions after that split pass in `vice_auto_20260815_223246`
  and `vice_auto_20260815_223302`.
- Added a serialized, variable-length action-plan format in REU. Each record
  has an explicit kind/selection flag, full relative stem, and reverse link;
  counters distinguish files, directories, and selected actions. Capacity is
  checked before either header or stem becomes visible, so overflow prevents
  later execution instead of yielding a partial executable plan.
- Added a stackless breadth-first walk core. It seeds an empty relative root,
  discovers appended directory records without recursion, enforces a caller
  depth bound, rejects `.`/`..`, `/`, and `!` in backend-returned child names,
  and keeps filtered records separate from traversal. Host tests cover forward
  and reverse record metadata, 255-byte limits, atomic overflow, dynamic queue
  growth, depth limits, invalid names, and normal completion.
- Added `readyfs-plan.prg` (now `$A94` after READ dispatch) as a second `$B600`
  sidecar. Matcher and planner each have a full 4 KB slot in a dedicated REU
  overlay bank. Boot executes the planner ABI entry while the sidecar is live,
  caches it, restores the matcher, and reports `PLANNER: READY` only after that
  call succeeds. Passing post-split UI evidence is
  `vice_auto_20260815_231620` after the third-overlay extension.
- The overlay resident image now ends at `$B3A7`, leaving 600 bytes before
  `$B600`; substantial planner/backend work must remain in overlays. The
  direct REST hardware artifact remains the monolithic PRG and ends at `$C5DF`.
- Every `make readyfs` now generates `readyfs-build-report.json` and Markdown.
  The report parses both linker maps, validates the `$B600` PRG headers and
  exact payload sizes, enforces the resident/monolithic ceilings, checks each
  sidecar against its own REU slot, and verifies all allocated REU intervals
  are disjoint. The current report is PASS.
- Added a consolidated UI report generator. It reads the BOM-bearing VICE
  manifests, selects the latest run per ReadyFS plan, and emits JSON/Markdown
  with direct manifest and screenshot links. Its initial report summarized 12
  latest suites, all successful, with 94 screen/state assertions and 66
  retained screenshots. This is suite evidence; numbered-case promotion still
  comes only from the explicit UI matrix.

## 2026-08-15 — first live recursive-plan enumeration

- Added a generic planner dispatcher so the resident shell can swap in the
  planner overlay for atomic INIT/ADD calls while matcher calls safely swap a
  different sidecar between records. The action-plan arena increased from
  `$2FF0` to `$3FF0` bytes after overlay caches moved to their own REU bank.
- Added the first real backend recursive-preview adapter for a legacy IEC root
  (a bounded depth-zero tree). It enumerates the live directory, skips the
  header, serializes every file/directory stem, applies include/exclude to each
  relative stem, refuses incomplete/over-limit enumeration, and reports exact
  copy/move/delete counts. It never opens the destination or a write channel.
- Passing VICE run `vice_auto_20260815_223204` creates mixed PRG/SEQ/USR
  fixtures, plans four live entries, proves include/exclude and move counts,
  rejects actual recursive execution, and verifies `TWO.SEQ` remains present.
  Failed diagnostic runs `222917` and `223029` were expectation issues (the
  D81 program is named `READYFS`, not `READYFS.PRG`, and a 40-column message
  wrapped); neither indicated a planner mutation.
- The consolidated UI report now has 13/13 latest successful suites, 106
  assertions, and 73 linked screenshots. Matrix case 52 remains partial until
  a genuinely nested backend tree—not just a flat IEC root—is planned and
  proven unchanged.

## 2026-08-15 — Ultimate recursive adapter and third overlay

- Added a nested UltimateDOS planning adapter to the monolithic hardware lab.
  It uses the planner READ dispatcher as a growing breadth-first queue, walks
  at most 32 levels/512 entries, validates every returned child stem, and keeps
  draining each UCI directory stream even if the plan rejects an entry. Its
  callback carries the required ReadyIRC-derived UCI state-machine contract.
- Independent-Terminal read-only run
  `readyfs_c64u/ui-readonly-20260815-230109` passed at 64 MHz. It recursively
  planned the active marker-owned USB1 root and reported 18 files, zero
  directories, 18 selected writes, and `DONE W0 D0 M0`. This proves the new
  adapter on hardware but not nested descent because that root currently had
  no child directories.
- Added marker-gated `run_readyfs_c64u_recursive_owned.sh`. It is designed to
  create and preserve one uniquely named three-level subtree only below the
  active USB1 owned root, verify the marker before every mkdir/write, run
  filtered copy/delete dry-runs, and FTP-read all three files afterward. Runs
  `recursive-owned-20260815-230322` and `231705` both byte-compared the marker,
  then all ten REST launch attempts reset. Neither launched ReadyFS or executed
  any filesystem command, so no directory or file was created or deleted.
- Added `readyfs-help.prg` as a third sidecar in its own 4 KB overlay-bank slot.
  Boot size-checks/caches and ABI-probes it; the `help` command runs from the
  `$B600` window. `vice_auto_20260815_231620` proves help execution followed by
  planner/matcher swaps. Current build report: resident ends `$B3A7` (600
  bytes free), monolithic ends `$C5DF` (32 bytes free), planner/walker is
  `$A94`, and help is `$17A`. Further monolithic growth is prohibited; the
  executor/remaining drivers must be state-machine overlays.
- Latest flat recursive regression is `vice_auto_20260815_231635`.

## 2026-08-15 — partition-aware IEC namespace

- The canonical parser now accepts an optional numeric IEC partition suffix,
  including `11.3:/folder`, preserves it through normalization, and rejects
  values above 254. `11.3:/one/../two` normalizes to `11.3:/two`.
- This is namespace support, not a claim that a CMD/SD2IEC driver exists.
  `cd`/`pwd` may retain the canonical location, while `dir`, `volume`, file
  preparation, and device-only mount designators reject a nonzero partition
  with `PARTITIONED IEC DRIVER NOT ENABLED` before any device I/O.
- Host path tests pass. VICE `vice_auto_20260815_233055` proves canonical path
  retention, the capability-honest I/O refusal, and the partition-255 bound.
  The first diagnostic run `232919` caught a mixed-case C64 character-mode
  display bug (`IEC` rendered as graphics); the corrected lowercase source
  literal is proven by the passing run.
- Compact monolithic help and full overlay help pass in
  `vice_auto_20260815_233207` and `vice_auto_20260815_233214`. The current
  build report is PASS: resident ends `$B4C1` (318 bytes before `$B600`) and
  monolithic ends `$C5EE` (17 bytes before `$C5FF`). Remaining functionality
  must be implemented as cooperative overlays, not resident growth.
- The consolidated report now selects 13/13 successful suites with 110
  screen/state assertions and 77 retained screenshots.

## 2026-08-15 — cooperative recursive executor protocol

- Added `readyfs_exec.c` to the planner sidecar. It turns a frozen REU action
  plan into one backend-neutral action at a time: destination `mkdir`, copy,
  verified move, delete, or reverse-order `rmdir`. The traversal-only empty
  root and filtered records never become actions.
- An action remains pending and is returned again until the resident backend
  explicitly acknowledges success or failure. This makes a slow UltimateDOS
  action one complete ReadyIRC-derived UCI transaction rather than making the
  overlay depend on timing. Stop-on-error and continue-on-error policies keep
  attempted/completed/failed counters separately.
- Host tests prove copy ordering, move's forward-file/reverse-directory
  phases, delete's child-before-parent order, pending replay, filtered-record
  skipping, and both error policies. VICE `vice_auto_20260815_233651` proves
  the planner sidecar's combined planner/executor ABI loads and executes on a
  C64 before matcher/help swaps continue.
- The planner/walker/executor payload is now `$F0F` in its 4 KB cache slot.
  Resident ends `$B4CC` (307 bytes before `$B600`); monolithic remains
  `$C5EE`. The next step is resident/backend action wiring and a durable REU
  journal, not another monolithic implementation.

## 2026-08-16 — versioned REU operation journal

- Added a variable-length `RFJ1` journal to the help sidecar and reserved the
  disjoint session-bank range `$0900-$1FFF` (5,888 bytes). Its 16-byte header
  records version, mode, open/finished state, overflow, used bytes, and
  completed/failed totals. Each record keeps action, result, backend, kind,
  backend detail/status, plan offset, and the complete relative stem.
- Record bytes are written before the visible header advances, so capacity or
  transport failure cannot expose a partial executable/reportable event.
  Host tests cover version/header fields, success and failure records,
  full-stem readback, finish state, post-finish rejection, atomic overflow,
  dispatcher reads, and the portable self-test.
- The first physical-REU VICE attempts exposed a cc65 boundary bug: indirect
  multi-argument callbacks worked at shallow depth but corrupted arguments in
  nested append/read paths, at times also corrupting the displayed REU bank
  count. Diagnostic runs `234816`, `000933`, `001123`, `001434`, `002240`,
  `003229`, `003303`, `003407`, `003512`, `003604`, `003640`, `003716`,
  `004747`, `004826`, `004915`, and `005243` remain failure evidence.
- The corrected C64 build binds journal I/O directly to its fixed REU region;
  host builds retain callback-backed storage. Serialization buffers and the
  self-test state are static to avoid cc65 software-stack hazards. Clean VICE
  `vice_auto_20260816_005513` proves a real REU write/read/finish round trip,
  then full help and matcher swaps. The UI now displays `JOURNAL: READY` only
  after that self-test succeeds.
- Current build report: resident `$B573` (140 bytes before `$B600`),
  monolithic `$C5EE`, plan/executor `$F0F`, help/journal `$BAC`; every ceiling,
  sidecar, and REU overlap check passes. The latest report selects 13/13
  successful suites, 111 assertions, and 78 screenshots.
- Added a single executor gateway for INIT/NEXT/ACK calls. Boot exercises its
  bounded NULL rejection after fetching the plan sidecar; host tests exercise
  real dispatcher initialization, action yield, and acknowledgement. Clean
  VICE `vice_auto_20260816_010809` passes afterward. Current authoritative map
  is resident `$B5C9` (54 bytes free), monolithic `$C5EE`, plan/executor
  `$FE2` (30 bytes free), and help/journal `$BAC`. Both the resident and first
  two functional slices are now closed to feature growth; backend work needs
  another overlay slice and only small resident gateways.
- Added `build_support/readyfs_journal_report.py`. It strictly validates RFJ1
  magic/version/state, used bounds, every variable record and NUL-terminated
  stem, record count, and completed/failed totals before emitting JSON or
  Markdown. Its self-test proves successful/failed events, action-name
  rendering, and rejection of a corrupted counter; `readyfs-host-tests` runs
  it on every build. Case 58 remains partial until actual executor results are
  written and a captured journal is converted.
- True-independent Terminal run
  `readyfs_c64u/recursive-owned-20260816-011419` failed safely before launch:
  all ten FTP owner-marker fetches reset. The marker was never validated, so
  ReadyFS did not launch and no mkdir, write, dry-run, or delete command ran.
  Preserve the evidence and do not retry in a tight loop.

## 2026-08-16 — fourth backend/request overlay and C64 ABI gate

- Added `readyfs-backend.prg` as a fourth `$B600` sidecar and reserved the
  disjoint overlay-bank slot `$3000-$3FFF`. The build report now validates its
  PRG header, mapped payload, 4 KB ceiling, and REU non-overlap along with the
  first three slices.
- Added a backend-neutral request format and one-pointer dispatcher. It joins
  executor-relative stems to canonical source/destination roots and preserves
  endpoint, IEC unit/partition, and Ultimate image depth. Host tests cover
  IEC-to-Ultimate copy, image-to-SoftIEC copy, delete, mkdir, partitioned IEC
  to image move, unresolved aliases, parent escape, and short-buffer failure.
- C64 diagnostic composition was deliberately not promoted. Run `012235`
  found cc65 placing a function-local static between an overlay procedure
  label and its first instruction. File-scope storage fixed that boot hang,
  but composed requests in `013012`, `014150`, `020349`, `020509`, `020535`,
  and guarded attempt `021726` displaced or corrupted caller state (REU count
  rendering and later matcher arguments). A one-pointer rewrite and an `sp`
  save/restore guard did not make the boundary trustworthy.
- The shipped C64 gateway therefore exposes no non-NULL backend call and the
  UI says `BACKEND: ABI`, not `READY`. Clean VICE
  `vice_auto_20260816_022610` proves exact load/cache/ABI, journal/help, and
  subsequent matcher swaps without shell corruption. No hardware was touched.
- Current authoritative build report passes: resident `$B5C1` (62 bytes before
  `$B600`), monolithic `$C5EE`, matcher `$4D1`, planner/executor `$FE2`,
  help/journal `$BAC`, and backend/request `$4BB`. The UI report is 13/13
  successful suites, 112 assertions, and 79 screenshots. Executor-to-backend
  actions and RFJ1 result wiring remain the active next step after the C64 ABI
  defect is root-caused.

## 2026-08-16 — backend gateway root cause and promotion

- Added an address-level VICE probe covering zero page, resident BSS, the
  shared overlay window, REU registers, CPU registers, and a matcher call after
  the backend boundary. Clean baseline is `024704`; focused diagnostic runs
  include `024843`, `025827`, `030033`, `030117`, `030155`, `032217`,
  `032339`, `035038`, and `040047`.
- The backend composer itself was not corrupting cc65 `sp`: both the mkdir and
  full IEC-to-Ultimate copy self-tests left it at `$B5EE` and later matching
  passed once the redundant cache fetch was absent. The later-fetch failures
  exposed the real defect in two layers: the four-argument sidecar loader lost
  its REU offset, and generic overlay store/fetch repacked five more arguments.
  All sidecars were therefore overwriting slot zero; generic fetches sometimes
  mirrored the same mistake and hid it.
- Replaced overlay cache DMA with a flat assembly ABI that directly programs
  one REU store/fetch and removes exactly six cc65 argument bytes. Replaced the
  four-argument loader with a one-byte slot selector that derives the sidecar
  name, expected size, 4 KB limit, and exact REU offset internally. Diagnostic
  `040608` shows a clean boot and matcher bytes restored at `$B600`.
- Added `RF_BACKEND_CALL_SELFTEST` and a real non-NULL gateway recheck. Boot
  now fetches the backend from `$3000-$3FFF`, composes and validates
  `8:/d/a.prg` to `u:/usb1/out/d/a.prg`, restores the matcher, and displays
  `BACKEND: READY` only if that sequence succeeds. VICE `040738` and `040745`
  pass the gateway, help, matcher, zero-page/BSS dumps, and register capture.
- Current build report passes: resident `$B5C7` (56 bytes before `$B600`),
  monolithic `$C5EE`, backend `$60B`, plan/executor `$FE2`, help/journal
  `$BAC`. Host path/plan/executor/journal/backend tests and the UCI contract
  verifier pass. No C64U hardware state was touched.

## 2026-08-16 — DMA invariant and cooperative pipeline contract

- Added `verify_readyfs_overlay_dma.py` to `readyfs-build-report`. It rejects
  loss of either flat assembly entry point, any REU DMA register write, the
  exact six-byte cc65 cleanup, explicit cache offsets/slot selectors, or the
  exclusion of the generic nested C wrapper from overlay builds.
- Added a cross-component host pipeline test. A selected recursive copy plan
  now flows through executor yield, IEC-to-Ultimate canonical request
  composition, an injected target result, RFJ1 append, and only then executor
  acknowledgement. It proves mkdir/file ordering, filtered-entry omission,
  one failed status `82`, continue-on-error totals, journal close, and exact
  replay of all three action records.
- The latest UI inventory is 15/15 successful suites, 115 screen/state
  assertions, and 85 retained screenshots. After adding a backend capability
  model, exact-size gateway/DMA reruns `vice_auto_20260816_042756` and `042851`
  pass with the backend sidecar at `$7B8`; resident still ends `$B5C7`.
- This establishes the protocol between components but does not yet authorize
  recursive mutation on C64. The next implementation boundary is the small
  resident controller that invokes real backend I/O between RFJ1 append and
  executor ACK. No C64U hardware state was touched.
- A direct resident `capabilities` command experiment crossed the `$B600`
  boundary by 100 bytes and was removed. The backend-owned structured model
  remains host-tested (including capability-honest tape, Ultimate hierarchy,
  provisional SoftIEC, and alias rejection)
  and must be exposed through the future controller overlay, not new resident
  feature code.

## 2026-08-16 — C64 cross-overlay pipeline proven

- Added a resident one-pointer nested gateway that can replace the executing
  backend overlay with plan/executor or help/journal code, dispatch one call,
  then restore backend bytes before returning to the overwritten caller.
  Mutable state lives in the existing resident command scratch buffer; no
  pointer targets the shared overlay window across a swap.
- The first attempt exposed another cc65 depth defect: executor `NEXT` still
  reached a six-argument `readyfs_plan_read`. The C64 plan and executor paths
  now implement INIT/ADD/READ and INIT/NEXT/ACK directly from one-pointer call
  records. Host builds retain the public multi-argument API and all host walk,
  plan, and executor regressions pass.
- Backend readiness now runs a real cooperative C64 protocol probe: serialize
  `d/a.prg`, yield copy, compose `8:/d/a.prg` to
  `u:/usb1/out/d/a.prg`, append injected target status `82` to RFJ1, ACK the
  pending action only afterward, finish the journal, and replay/validate the
  record. Every stage crosses/restores its actual REU sidecar.
- `vice_auto_20260816_060538` passes the exact-size backend gateway and later
  help/matcher calls; `060805` independently passes the DMA boot assertion.
  `BACKEND: READY` depends on the complete pipeline probe. Temporary failing
  traces `045006` through `054356` and the zero-assertion hang diagnostic are
  retained as diagnosis but excluded from UI-suite counts.
- Added `verify_readyfs_pipeline_contract.py`; the build rejects loss of the
  one-pointer executor read, backend restore, C64 pipeline dependency, or
  RFJ1-before-ACK/finish/replay ordering. UI reporting now excludes
  zero-assertion diagnostic runs from suite counts.
- Current build report passes at resident `$B5D5` (42 bytes free), monolithic
  `$C5C5`, matcher `$4D1`, plan/executor `$B39`, help/journal `$BAC`, and
  backend/controller `$F1F`. The stackless walker remains host-proven but was
  removed from this C64 slice while the one-pointer controller path is made
  real; it must return in a later planner/controller slice.
- This still performs no filesystem mutation: status `82` is injected. The
  active next boundary is to call resident file I/O for one marker-owned or
  disposable VICE action, record its actual result, and only then ACK. No C64U
  hardware state was touched.

## 2026-08-16 — first real C64 action and RFJ1 report proven

- The overlay build now executes a real staged IEC copy from resident code,
  then re-enters the backend solely to append/finalize its result. Overlay code
  never owns KERNAL/device I/O or a return address spanning it.
- VICE exposed three cc65 lifetime defects first: a three-argument
  overlay-to-resident copy returned into clobbered code; large software-stack
  control records corrupted deep IEC calls; and journal overlay calls into
  three-argument C session DMA corrupted the REU matcher cache. The final
  boundaries use resident static one-pointer copy/backend records plus flat
  assembly overlay and session DMA.
- `vice_auto_20260816_071749` passes a disposable `8:/RFMATCH` to `8:/RFPIPE`
  copy, stat, byte comparison, immediate post-RFJ1 matching, and matching after
  further IEC I/O. Its full REU dump converts to JSON/Markdown: finished mode
  1, one successful IEC `copy-file`, stem `8:/RFMATCH`.
- RFJ1 magic is fixed numeric ASCII (`52 46 4A 31`), not cc65 PETSCII
  character literals. The journal is at bank 255 offset `$2900`.
- Current map: resident `$B54D` (178 bytes free), monolithic `$C52F`, matcher
  `$4D1`, planner/executor `$B39`, help/journal `$C93`, backend `$F12`.
  UI inventory is 16/16 suites, 121 assertions, and 93 screenshots. No C64U
  hardware state was touched.

## 2026-08-16 — real action executor ACK independently proven

- The real copy now enters the one-action controller with `BEGIN`, yields one
  pending selected `COPY_FILE`, checkpoints that controller in the session
  REU, returns to resident staged IEC I/O, writes/finishes RFJ1, and only then
  restores and acknowledges the exact pending action.
- Added the fixed eight-byte `RFA1` completion record at session-relative
  `$8300` (physical bank-255 offset `$A300`). It records attempted, completed,
  failed, and pending after ACK. `readyfs_action_report.py` strictly validates
  the magic and single-action totals and emits JSON/Markdown. Host tests cover
  successful ACK, failed ACK, restart, and duplicate-ACK rejection.
- VICE `vice_auto_20260816_074649` passes the disposable `RFMATCH` to `RFPIPE`
  copy, byte verification, stat, matcher restoration, full REU capture, RFJ1
  conversion, and RFA1 conversion. RFJ1 says one successful IEC copy; RFA1
  independently says attempted 1, completed 1, failed 0, pending false.
- Diagnostic `072830` found the first executor build stalled during temporary
  name formatting. Breakpoint runs `073244` through `074211` proved the
  backend call was stack-balanced but the deep cc65 call path left the
  12-byte `suffix` local against the resident/overlay ceiling. The suffix now
  reuses `io_buf` before transfer begins; clean runs `074418` and `074649`
  prove the correction. The transient diagnostic plan is excluded from UI
  suite inventory, while its logs remain retained evidence.
- Authoritative build report: resident `$B5CA` (53 bytes before `$B600`),
  monolithic `$C52D`, matcher `$4D1`, planner/executor `$E35`, help/journal
  `$C93`, backend/controller `$FD7`. The session map now explicitly includes
  `$8200-$83FF` for action checkpoint/report. No C64U hardware state was
  touched.

## 2026-08-16 — CMD/SD2IEC translation contract host-proven

- Added a bounded one-pointer CMD/SD2IEC translator and host suite. Canonical
  `11.3:/...` paths now have exact tested translations for absolute file open,
  directory listing, scratch, mkdir, rmdir, rename, image mount, and image
  unmount. Rename was corrected to native `R:new=old` order.
- The contract enforces partitions 1–254, 16-byte components, a conservative
  234-byte directory path, D64/D71/D81/DNP mount names, same-device/partition
  rename, and explicit rejection of `!` image-contained paths until a stateful
  mount/open/restore controller exists. The same source cc65-compiles into a
  staged fifth `RFCMDPATH` sidecar at `$B600`; its `$DAE` payload fits a 4 KB
  slot and is included on the overlay lab D81. Host-only English diagnostics
  stay out of the cc65 image, leaving 594 bytes in the slot for controller work.
- A trial resident cache/dispatch hook was rejected by the linker because it
  overflowed the safe resident region by 85 bytes. The hook was withdrawn;
  `RFCMDPATH` is intentionally not loaded or callable at runtime yet. The
  build report reserves REU overlay `$4000-$4FFF` but labels the sidecar
  runtime-disabled. The `$B5CA` resident ceiling remains unchanged.
- `make readyfs-host-tests` and `make readyfs` pass, including the UCI,
  overlay-DMA, pipeline-order, RFJ1, RFA1, and build-size gates. The
  authoritative C64 map is unchanged.
- Fresh VICE regression `vice_auto_20260816_080238` passes after packaging the
  extra sidecar: the real disposable IEC copy, verification, matcher restore,
  full REU capture, finished RFJ1, and RFA1 totals `1/1/0/0` all remain exact.
  The generated UI inventory remains 16/16 successful with 121 assertions.
- A true independent Terminal-owned SoftIEC attempt is retained at
  `logs/readyfs_c64u/softiec-owned-20260816-075039`. The initial owner-marker
  FTP gate received ten connection resets and failed before launch, mapping,
  filesystem commands, or mutation. No retry loop was started and no C64U
  state was changed.

## 2026-08-16 — fifth sidecar runtime self-test proven

- Reworked the smaller runtime boundary after the rejected general dispatcher:
  `load_cached(5)` now stores `RFCMDPATH` in dedicated REU
  `$4000-$4FFF`, verifies `RF_CMDPATH_ABI`, and calls a sidecar-owned,
  stack-safe self-test before restoring the matcher.
- The C64 self-test proves exact absolute open, `R:new=old`, D64 mount, and
  two-command unmount translations. Host tests retain the broader directory,
  scratch, mkdir/rmdir, limits, rejection, and extension matrix.
- Long English diagnostics remain host-side; shorter but precise resident
  messages recovered enough space without removing behaviors. The final map
  passes at resident `$B5B9` (70 bytes free), monolithic `$C4B1`, and CMD path
  `$FCC` (52 bytes free). Treat both regions as closed to casual growth.
- `verify_readyfs_overlay_dma.py` now requires explicit slots 1–5 and the
  translation self-test. The generated build report labels CMD path as a
  cached runtime sidecar rather than staged/disabled.
- VICE `vice_auto_20260816_081226` explicitly asserts and captures
  `CMDPATH: READY`, then repeats the real disposable IEC copy, byte/stat/match
  verification, RFJ1 extraction, and RFA1 `1/1/0/0` extraction. The UI report
  is 16/16 successful latest suites with 122 assertions. This proves runtime
  translation, not yet command-channel execution of the translated strings.
- A follow-on direct resident `native OP PATH` diagnostic plus general
  dispatcher was measured and rejected: it overflowed `$B600` by 486 bytes
  (556 bytes beyond the 70-byte baseline). The entire attempt was withdrawn
  and the build returned to `$B5B9`. The next callable design must place its
  parser/UI in the help sidecar and use a one-pointer nested CMD-path gateway
  that restores help code before returning; it must not grow a resident CLI.

## 2026-08-16 — callable C64 CMD-path UI and PETSCII correction

- Implemented the replacement architecture: `native OP PATH [DEST]` parsing
  and rendering live in `RFHELP`; its complete mutable context and nested
  CMD-path call live in `readyfs_pipeline_scratch`. The resident gateway loads
  slot 5, dispatches one pointer, restores help before its return address runs,
  and finally restores matcher code.
- Added dedicated `readyfs_cmdpath` VICE automation with exact results for all
  eight operations: open, directory, scratch, mkdir, rmdir, rename, image
  mount, and image unmount. It separately asserts the unmount follow-up and a
  matcher call after repeated help/CMD swaps.
- Diagnostic runs `vice_auto_20260816_082858` and `084104` stopped at scratch.
  The capture proved uppercase cc65 string literals emitted shifted PETSCII
  command prefixes (`S` decoded as `.`), while keyboard path bodies were
  unshifted. CMD/SD2IEC prefixes now use cc65-specific unshifted literals, and
  boot fixtures use keyboard-equivalent encoding so the self-test cannot mirror
  the old defect.
- Final callable suite `vice_auto_20260816_090349` passes 11 assertions and 13
  screenshots. Rename no longer exposes its scratch operand as a `THEN`
  command; only unmount prints the required second command. Fresh real-pipeline
  regression `vice_auto_20260816_090503` also passes RFJ1 and RFA1 extraction.
- UI inventory is now 17/17 latest suites and 133 assertions. Current map:
  resident `$B578` (135 bytes free), monolithic `$C382`, help/journal `$FF9`,
  and CMD path `$FD0`. Help and CMD path are closed to further growth.
- True independent Terminal-owned SoftIEC run
  `logs/readyfs_c64u/softiec-owned-20260816-091304` retried only after this
  local milestone. It again received ten FTP connection resets at the exact
  owner-marker preflight and stopped with an empty results table. No ReadyFS
  launch, SoftIEC map, filesystem command, configuration change, or mutation
  occurred.

## 2026-08-16 — detected IEC profile through resident-owned I/O

- Added pure driver classification for SD2IEC, CMD, Pi1541, Ultimate, SoftIEC,
  legacy drives, and unknown replies, with explicit partition/folder/image
  flags and host fixtures for every profile. Detection does not itself enable
  any operation.
- A direct resident probe experiment was rejected after measuring a 468-byte
  overflow. The replacement is the sixth `RFDRIVE` sidecar at REU
  `$5000-$5FFF`: it parses/renders/classifies, while resident
  `probe_iec_io()` exclusively opens, reads, and closes command channel 15.
  Mutable state stays in resident scratch, and every sidecar call restores the
  matcher before returning.
- The structural verifier now requires explicit overlay slots 1–6, the drive
  wrapper's matcher restoration, resident ownership of `cbm_open`, and the
  absence of KERNAL/UCI I/O in `readyfs_driveui.c`. The build report validates
  `RFDRIVE` against its map and 4 KB slot.
- Diagnostic VICE run `vice_auto_20260816_100250` received the exact status
  `73,VIRTUAL DRIVE EMULATION V3.5,00,00` but initially classified it unknown
  because this VICE release omits the word `VICE`. That emitted phrase is now
  an exact host-tested legacy signature.
- Final UI run `vice_auto_20260816_100352` passes command-channel identity,
  `PROFILE: LEGACY P0 F0 I0`, every native translation, unmount follow-up, and
  matcher restoration. Real-pipeline regression `100428` passes RFJ1 and RFA1
  unchanged. UI inventory is 17/17 latest suites, 135 assertions.
- Authoritative map: resident `$B545` (186 bytes free), monolithic `$C4E6`,
  matcher `$4D1`, planner/executor `$E35`, help/journal `$FF9`, backend `$FD7`,
  CMD path `$FD0`, and drive profiler `$6A9`. Compatible translated command
  execution remains gated until the profile grants it; physical SD2IEC and
  SoftIEC evidence remains outstanding.

## 2026-08-16 — persistent per-drive profiles and capability gate

- Reserved the previously unused session-REU gap `$0888-$08E3` for 23
  independent four-byte IEC profile records. Each record contains a fixed
  marker, its exact device number, detected kind, and capability flags. Boot
  clears the whole registry only after the drive-sidecar ABI is verified, so
  random or stale REU bytes cannot authorize an operation.
- Added `profile iec DRIVE: [OP]`. An unprobed device reports `UNPROBED`; a
  probed device is fetched from REU and revalidates marker plus device before
  displaying its profile. Optional operations report `ALLOWED` or `DENIED`
  without issuing any device command.
- The pure host capability matrix requires partitions for open/scratch,
  partitions+folders for directory/mkdir/rmdir/rename, and
  partitions+folders+images for mount/unmount. Thus CMD can allow its folder
  family without silently gaining SD2IEC image behavior; legacy allows none.
- VICE `vice_auto_20260816_101151` passes deterministic drive-9 `UNPROBED`, a
  live drive-8 identity probe, cached `LEGACY P0 F0 I0`, explicit legacy mount
  denial, all eight native translations, unmount follow-up, and matcher
  restoration. It has 17 assertions and 19 screenshots. Pipeline regression
  `101231` again passes the real IEC copy, RFJ1, RFA1, and matcher path.
- Generated inventory is 17/17 latest suites with 139 assertions. Current map
  is resident `$B5B8` (71 bytes free), monolithic `$C53F`, and drive profiler
  `$A8C`; all other sidecar sizes are unchanged. Actual translated command
  execution remains the next overlay-heavy boundary.
- Fresh true Terminal-owned C64U run
  `softiec-owned-20260816-100658` failed at the exact prelaunch owner-marker
  gate after ten FTP connection resets. Its result table is empty: it did not
  launch ReadyFS, map SoftIEC, perform file I/O, change configuration, or
  mutate USB1/SD. No immediate retry was started.

## 2026-08-16 — five-action journal controller and real action UI suite

- Generalized the one-action controller from copy-only to the exact contiguous
  action set: mkdir, copy-file, move-file, delete-file, and rmdir. BEGIN derives
  the correct plan kind and executor mode, checkpoints the pending state in
  REU, and ACK reloads that state, advances exactly once, rejects duplicates,
  and emits RFA1.
- Backend BEGIN/COMPLETE now validates only those five actions, requires the
  appropriate source/destination roots, derives journal kind from the pending
  plan record, writes RFJ1 before ACK, and never performs device I/O. Host
  tests prove success and duplicate-ACK rejection for every action.
- Added a C64 boot self-test inside the planner/executor sidecar. `PLANNER:
  READY` now requires all five actions to complete BEGIN → REU checkpoint →
  ACK → RFA1 through cc65's one-pointer path, not merely ABI equality.
- Wrapped normal overlay copy/move, delete, mkdir, and rmdir commands around
  the controller. Confirmation/filter/dry-run gates occur before BEGIN;
  resident I/O runs while the overlay is restored; COMPLETE receives the full
  result. Move is not acknowledged until its source deletion also succeeds.
- Dedicated VICE suite `vice_auto_20260816_112225` performs real disposable
  copy → move → delete, verifies source/destination postconditions after move
  and absence after delete, then converts a full REU image. RFJ1 reports one
  successful `delete-file` for `8:/RFMOVED`; RFA1 reports `1/1/0/0`.
  Pipeline copy regression `111729` remains green.
- UI inventory is 18/18 latest suites with 148 assertions. Current map:
  resident `$B5BA` (69 bytes free), planner/executor `$FDF`, backend `$FE0`,
  drive profiler `$A8C`; other sidecars are unchanged. The first generalized
  backend build overflowed by 88 bytes; range checks and smaller self-test
  buffers recovered the slot without removing validation. Resident hooks
  initially overflowed by 104 bytes; concise distinct diagnostics recovered
  space without removing behaviors.
- Actual C64 file I/O is proven for copy, move, and delete. Mkdir/rmdir have
  host and C64 controller coverage and resident wrapping, but still require a
  folder-capable disposable backend for physical I/O proof.
- Independent read-only preflight `preflight-20260816-112357` initially
  reported success, but audit found its script used `set -u` without `-e`:
  three resetting FTP commands created empty files, then the final manifest
  write returned zero. That run is invalid as FTP evidence. The harness now
  uses strict mode, bounded retries, `--list-only`, and nonempty-output gates.
- Corrected Terminal-owned preflight `preflight-20260816-113019` captured all
  seven nonempty REST version/info/drive/config responses, then correctly
  failed after ten FTP root-list resets. A guarded SoftIEC run launched only
  after the provisional preflight, `softiec-owned-20260816-112412`, also
  stopped at ten exact-marker RETR resets with an empty case table. It did not
  launch ReadyFS, map a partition, issue filesystem I/O, change configuration,
  or mutate any root. No further hardware retry was started.

## 2026-08-16 — capability-gated normal partition mkdir/rmdir bridge

- Added the first normal-command route through the detected IEC driver:
  `mkdir` and forced `rmdir` resolve aliases, require an exact cached profile,
  translate in `RFCMDPATH`, and return the command to resident channel-15 I/O.
  Legacy/unprobed profiles stop before BEGIN or I/O; compatible profiles use
  the five-action BEGIN → RFJ1 → ACK → RFA1 controller.
- The outer command record lives in the existing resident destination-stream
  workspace, the backend call uses its existing resident object, and only
  backend transient state uses pipeline scratch. Nested drive → CMD
  path/backend → drive returns cannot overwrite the outer call.
- `probe_iec_io(call)` remains the sole KERNAL command-channel owner. Identity
  uses `UI`; mutations use the translated string and accept success only when
  status begins `00`. `readyfs_driveui.c` contains no KERNAL or UCI I/O.
- Host tests add in-place directory/mkdir/rmdir translation. Structural gates
  require nested backend restoration and authorize → resident I/O → complete
  ordering. The ReadyIRC-derived UCI verifier remains green.
- Diagnostic `vice_auto_20260816_120421` exposed help being restored and then
  overwritten by backend; `120650` exposed native rename using a 32-byte
  transfer buffer despite its 256-byte ABI. Help now returns immediately after
  restoration, and native output/follow-up use two 256-byte stream workspaces.
- Final authorities: `vice_auto_20260816_121327` (45-step CMD-path, direct and
  alias-resolved legacy-profile denial, all translations, matcher restoration), `120846`
  (five-action pipeline), `120942` (real copy/RFJ1/RFA1), and `121013` (flat
  rename/directory regression). Inventory is 18/18 with 151 assertions.
- Current map: resident `$B5AB` (84 bytes free), monolithic `$C265`, matcher
  `$4D1`, planner/executor `$FDF`, help/journal `$FF9`, backend `$FE0`, CMD
  path `$FD0`, drive/controller `$F85`. Compatible physical folder execution
  remains unproven; no hardware attempt or storage mutation occurred.

## 2026-08-16 — normal partition directory route and KERNAL-safe ceiling

- Extended the normal bridge to partitioned `dir`. The drive sidecar applies
  the same exact profile and `P+F` gate, `RFCMDPATH` returns `$partition//...`,
  and resident `dir_iec()` owns enumeration. Listing does not enter the
  mutation journal; mkdir/rmdir still use BEGIN/COMPLETE.
- Runs `vice_auto_20260816_121620` and `121741` stalled before readiness after
  the first build ended resident BSS at `$B5EB`. A focused delayed register
  and memory capture (`122154`) found PC `$0009` and nonzero KERNAL scratch
  beginning at `$B5AC`. The linker-valid `$B5FF` ceiling was therefore unsafe
  for disk-loading initialization.
- The build report now independently requires resident end below `$B5AC`.
  Diagnostics were compacted without removing checks; current end is `$B59E`,
  leaving 13 hardware-safe bytes. Dedicated `readyfs_boot_diag` run `122619`
  passes readiness, registers, and resident-tail/overlay/REU memory capture.
- Final `vice_auto_20260816_122410` passes 48 steps: direct and alias-resolved
  mkdir denial, alias-resolved partition `dir` denial, all eight native
  translations, and matcher restoration. Fresh action/copy regressions
  `122455` and `122520` pass. Inventory is 19/19 with 154 assertions.
- Authoritative map: resident `$B59E` (13 safe bytes), monolithic `$C21D`,
  matcher `$4D1`, planner/executor `$FDF`, help/journal `$FF9`, backend `$FE0`,
  CMD path `$FD0`, and drive/controller `$FBE`. These regions are closed.
- Fresh true Terminal-owned read-only preflight
  `preflight-20260816-1228-final-local` captured seven nonempty REST
  version/info/drive/config documents, then received ten FTP root-list resets
  and ended `failed:1`. It performed no launch, map, configuration write, FTP
  write, marker bypass, or filesystem mutation. No mutation suite followed.

## 2026-08-16 — capability-gated normal partition file delete

- Normal overlay `delete` now preserves recursive refusal, relative-stem
  filtering, and `--dry-run` before resolving the partition route. A
  partition delete then requires `--force`, an exact cached profile granting
  partitions, RFCMDPATH scratch translation, and resident-owned channel-15
  I/O. DELETE_FILE BEGIN/RFJ1/RFA1/COMPLETE wraps only the authorized mutation.
- `verify_readyfs_pipeline_contract.py` now fixes that ordering and requires
  the drive sidecar to map SCRATCH to DELETE_FILE with a source root. The
  overlay DMA guard and ReadyIRC-derived UCI verifier also pass.
- VICE `vice_auto_20260816_123243` passes 54 steps and 23 assertions. The
  alias-resolved command without force stops at `USE --FORCE`; the forced
  command stops at `PROFILE DENIED` on VICE's cached legacy profile, before
  BEGIN or IEC I/O. It retains all native translations and matcher restoration.
- Shared regressions `123329` and `123405` pass the five-action controller and
  real copy/RFJ1/RFA1 paths. Boot-memory run `123448` passes readiness and
  resident-tail/overlay/REU captures. Generated inventory is 19/19 suites and
  156 assertions.
- Current map is resident `$B5AA` (one safe byte before `$B5AC`), monolithic
  `$C21D`, matcher `$4D1`, planner/executor `$FDF`, help/journal `$FF9`,
  backend `$FE0`, CMD path `$FD0`, and drive/controller `$FFC`. All regions are
  closed; future feature work must first reclaim space or use another overlay.
- This proves safety routing and denial, not execution on CMD/SD2IEC hardware.
  The latest true Terminal preflight still failed the exact FTP marker gate,
  so no physical launch, command-channel mutation, or storage change followed.

## 2026-08-16 — partition rename and single-command image mount

- Partition rename now resolves both aliases into separate 256-byte resident
  workspaces, requires `--force` and `P+F`, translates `R:new=old`, and records
  the operation through the existing MOVE_FILE BEGIN/RFJ1/ACK/RFA1 path around
  resident channel-15 I/O. A dedicated 256-byte follow-up workspace fixes a
  compatible-device bug that profile-denial tests could not expose.
- Partition mount syntax is `mount UNIT.PART:/path/image.dxx --force`; the
  source endpoint selects the IEC device. It requires `P+F+I`, translates the
  absolute `CD` command, and performs resident-owned single-command I/O. Media
  mount is intentionally outside the five file-action journal until RFJ1/RFA1
  has distinct media actions.
- SD2IEC/CMD unmount now uses the proven `CD//` followed by `CD` plus
  back-arrow sequence. The resident dispatcher performs the already-bounded
  single-command primitive twice only for UNMOUNT, clears the follow-up pointer
  before the second call, and completes only after its status. Structural
  verification fixes this exact two-command upper bound.
- VICE `vice_auto_20260816_125444` passes 72 steps and 29 assertions: alias
  rename, mount, and unmount each stop without force, then stop at cached
  legacy-profile denial when forced. Failed `124914` retained the invalid
  PETSCII `| 32` folding diagnostic; explicit cc65 folding fixed it.
- Regressions `125544`, `125610`, and boot-memory `125645` pass. Inventory is
  19/19 suites with 162 assertions. Current map: resident `$B592` (25 safe
  bytes), monolithic `$C107`, matcher `$4D1`, plan `$FDF`, help `$FF9`, backend
  `$FE0`, CMD path `$FD0`, drive/controller `$FFB`.
- No compatible physical execution is claimed and no C64U storage or
  configuration mutation occurred; the exact owner-marker gate remains
  mandatory before any future hardware run.

## 2026-08-16 — real multi-entry recursive IEC batch

- Added an overlay-1 recursive controller ABI (`INIT/ADD/START/NEXT/ACK`). Its
  plan, executor, journal, and current action are checkpointed at session REU
  `$8E00-$8EFF`; two canonical roots are retained at `$9988-$9B87`; the plan
  remains at `$A000-$DFEF`. Each nested plan/executor/journal/backend call asks
  the resident gateway to restore overlay 1 before returning.
- The controller composes backend-neutral source/destination requests and
  yields one action at a time. Resident code alone performs copy/move/delete/
  mkdir/rmdir I/O. ACK re-reads the pending stem, appends RFJ1, and only then
  advances the executor. C64 roots are reloaded from REU after KERNAL I/O.
- Reconnected normal overlay `copy`, `move`, and `delete --recursive` for a
  bounded flat IEC root. `--include`/`--exclude` operate on complete relative
  stems; `--dry-run` enumerates and reports without filesystem I/O; default
  failure policy stops and `--continue` selects continue policy. Nested IEC
  directories remain profile-gated rather than guessed.
- Replaced four `sprintf` sites with bounded decimal/hex formatters, removing
  the formatted-I/O runtime. This made room for the resident action loop while
  preserving the hard KERNAL scratch ceiling. Current map after the failure-
  policy/stack correction: resident `$B59B` (16 safe bytes), monolithic
  `$BB08`, matcher/controller `$FE3`, plan `$FDF`,
  help `$FF9`, backend `$FE0`, CMD path `$FD0`, drive `$FFB`.
- Host controller tests pass copy/continue with an injected failure, pending
  replay, move reverse-order cleanup, stop-on-error, and cross-backend path
  composition. Structural guards require scratch fit, C64 journal callbacks,
  REU state/root checkpoints, overlay restoration, resident-only device I/O,
  and exact NEXT→I/O→ACK ordering.
- VICE `vice_auto_20260816_132123` passes all 30 dual-drive steps: four fixture
  writes, filtered two-file WhatIf, real IEC8→IEC9 copy, compare, move source/
  destination postchecks, delete, and survivor postcheck. Its immediate copy
  REU snapshot converts to a finished two-record RFJ1 (`RFZA`, `RFZB`), mode
  1, completed 2, failed 0, with expected actions/stems enforced by the runner.
  Follow-up action `133436`, copy `132530`, and boot-memory `133501`
  regressions pass; aggregate UI evidence is now 20/20 suites and 179
  assertions. The action plan now waits for the real prompt boundary after
  copy and uses an isolated one-byte fixture because overlay 1 itself is no
  longer an appropriate mutable-operation fixture.
- No C64U call or storage/configuration mutation was attempted. The strict
  marker gate and owned USB1/SD roots remain mandatory; the last independent
  preflight still failed FTP after successful REST reads.

## 2026-08-16 — recursive failure policy and stack contract

- VICE `vice_auto_20260816_140348` passes all 60 steps and 27 assertions in
  one uninterrupted shell session. The first batch declines a destination
  conflict under the default stop policy, reports `0/1 fail 1`, and proves the
  second source was not attempted. A following `--continue` batch declines its
  first conflict, copies its second file, reports `1/2 fail 1`, and proves the
  second destination exists.
- Exact RFJ1 conversion passes twice: `RFZA`/`RFZB` are two successful copy
  events; `RFCA` is failed and `RFCB` succeeds, with completed/failed totals
  `1/1`. The generated inventory is now 20/20 suites and 191 assertions, and
  UI matrix case 57 is promoted (35/60 cases proven).
- The mixed-result run exposed that C64 crt0 derives the software-stack top
  from `MAIN start + size`. The overlay linker previously ended `MAIN` at
  `$B600`, so the deeper failure path overwrote capability state at
  `$B590-$B596`. `MAIN` now extends symbolically to `__HIMEM__` (`$D000`) while
  loaded resident segments still end at `$B59B` and overlays remain
  `$B600-$C5FF`. The build report and structural verifier require stack top
  `$D000`; 16 bytes remain before hard KERNAL scratch `$B5AC`.
- Current payloads: matcher/controller `$FE3`, plan/executor `$FDF`,
  help/journal `$FF9`, backend `$FE0`, CMD path `$FD0`, drive `$FFB`, and
  monolithic `$BB08`. Host tests, UCI contract checks, and focused pipeline
  copy `vice_auto_20260816_135535` pass.
- Testing remained wholly on fresh VICE images. No C64U REST/FTP call, feature
  toggle, or storage/configuration mutation occurred; owned USB1/SD marker
  gates remain mandatory.

## 2026-08-16 — complete large-directory paging and guarded hardware recheck

- Replaced the old eight-entry display preview with shared IEC/Ultimate
  directory paging. Every bounded entry is displayed; after 18 entry lines the
  shell shows `-- MORE --`, waits for a key, saves the full screen to the REU
  scrollback ring, clears, and resumes. IEC and Ultimate listings reset the
  same page counter, and the structural pipeline verifier fixes that contract.
- Fresh large-directory authority `vice_auto_20260816_141948` passes 19 steps
  and 11 assertions on a generated D81 with 48 entries. Page captures end at
  F10 and F28, the final page reaches F40 and reports exactly 48 entries/2213
  free C64 blocks, and F1/F3 traverse both saved pages and return to live.
  This promotes UI case 31.
- The current volume regression `vice_auto_20260816_141932` passes IEC device,
  volume title, exact 2989-block free value, capability-honest UltimateDOS
  unavailability in VICE, and sequential-tape `NO TAPE FREE`. Its waits now
  match current user-visible output and include a prompt-safe clear boundary.
- Fresh mixed-format run `vice_auto_20260816_142523` passes 15 steps and seven
  assertions with a D71/1571 on unit 8 and D64/1541 on unit 9. D64 `dir` and
  `volume` return the exact empty-media 664 blocks; D71 returns its title and
  exact 1157 blocks through the 16-bit terminal-directory value. Cases 29 and
  30 are promoted.
- REL safety authority `vice_auto_20260816_143000` identifies a real two-block
  IEC REL entry and proves IEC→Ultimate copy rejects it explicitly before any
  destination probe. Diagnostic `142842` exposed the old destination-first
  order. Copy now performs a read-only source open/close preflight before
  destination existence/replacement I/O; the pipeline verifier fixes this.
  Case 48 is promoted. Post-fix staged copy/move `143116` and overlay
  copy/RFJ1/RFA1 `143137` both pass.
- Replacement rollback authority `vice_auto_20260816_143517` forces a
  171-block source onto a D64 with only 134 blocks free and an existing
  17-block destination. Copy fails after 34,016 bytes; the old destination is
  still byte-identical, the directory returns to five entries/134 blocks, and
  both C64 UI and host `c1541` analysis prove no `RF~xx` stage remains. Case 45
  is promoted.
- Recursive delete confirmation authority `vice_auto_20260816_144213` proves
  default-No preservation and prompt-free `--yes` deletion with exact `1/1/0`
  summary/postcheck. `--yes` is now centralized as the alias for `--force`,
  removing four duplicated media/map checks. The first implementation exceeded
  `$B5AC`; the consolidated one passes at resident `$B598` with 19 bytes safe.
- Full recursive regression `152157` passes all 60 steps, RFJ1 analyses, and
  exact current capability bytes at `$B110-$B111`/`$B574-$B579`. Command-path
  `144704` passes all 72 steps; its redundant flaky blanket final-REU dump is
  disabled while its 31 targeted screenshots/states remain. Case 47 is
  promoted.
- Generated UI inventory is 25/25 latest suites with 229 screen/state
  assertions; 41/60 numbered cases are proven. `make readyfs`, all host tests,
  the ReadyIRC-derived UCI contract verifier, overlay DMA guard, and pipeline
  guard pass. Current map: resident `$B598` (19 bytes before `$B5AC`),
  monolithic `$BADF`, stack top `$D000`, and sidecars `$FE3`, `$FDF`, `$FF9`,
  `$FE0`, `$FD0`, and `$FFB`.
- Physical read-only automation now acknowledges at most 32 `-- MORE --`
  prompts so a large Ultimate directory cannot deadlock the 1/16/64 MHz suite.
  Independent Terminal preflight `preflight-20260816-1421-pagination`
  captured all seven nonempty REST documents, then every one of ten bounded
  FTP root-list attempts reset. It ended `failed:1` before marker retrieval,
  PRG launch, feature/configuration changes, filesystem commands, or storage
  mutation. Do not tight-loop; exact USB1/SD ownership markers remain required.

## 2026-08-16 — bounded IEC 8–30 discovery

- VICE diagnostics `vice_auto_20260816_144932` and `145231` proved that using
  a complete DOS command-channel open as a presence probe could hold
  `DRIVES SCAN` beyond both 60- and 180-second bounds after finding units 8
  and 9. This was treated as a shell defect rather than hidden by a longer UI
  timeout.
- ReadyFS discovery now performs only the KERNAL
  `LISTEN`/status/`UNLISTEN` listener handshake and interprets ST bit 7 as
  device-not-present. Real directory/file commands continue to use their
  normal data and command channels. The pipeline verifier requires the fast
  handshake and rejects a return to full command-channel discovery.
- Strict authority `vice_auto_20260816_145814` passes 22 steps and 12
  assertions: the C64 screen shows `IEC SCAN 8-30`, units 8 and 9, sequential
  tape, and the returned `RF>` prompt under a 20-second completion bound. This
  promotes UI case 28; aggregate inventory is 25/25 suites, 234 assertions,
  and 42/60 numbered cases proven.
- The new libc imports reordered paired ld65 exports and exposed a report-only
  parser assumption that symbols always begin a map line. The build report now
  accepts either export column. Current verified map: resident `$B581` (42
  bytes before `$B5AC`), monolithic `$BAC8`, stack top `$D000`, and sidecars
  `$FE3`, `$FDF`, `$FF9`, `$FE0`, `$FD0`, `$FFB`.
- All work was on disposable VICE D64/D71 images. No C64U REST/FTP request,
  feature/configuration change, launch, or storage mutation occurred; the exact
  USB1/SD marker gates remain mandatory.

## 2026-08-16 — typed and unit-honest `stat` metadata

- `stat` on regular IEC now labels the canonical/display name separately from
  the actual directory-entry raw name, reports the CBM file type, and labels
  the directory block count as an estimate rather than pretending it is an
  exact byte length. SoftIEC reports unknown raw name/size honestly until its
  metadata API is proven. Ultimate FILE_INFO output is labeled as an exact
  byte count and includes the opened file type.
- Focused authority `vice_auto_20260816_150616` batches this into the existing
  action-filter suite: a real PRG reports `DISPLAY: FILTERED`, `RAW: FILTERED`,
  `TYPE: $11`, and `SIZE EST: 1 C64 BLOCKS`. The pipeline verifier locks down
  display/raw, estimated-block, and exact-byte labels.
- Case 33 remains partial, not promoted: Ultimate raw-host-name output still
  needs to move into a backend overlay and be exercised on physical hardware.
  Aggregate inventory is 25/25 suites with 237 assertions and 42/60 cases.
- A first resident implementation of the Ultimate raw-name rescan failed the
  strict `$B5AC` boundary by 73 bytes and was removed rather than weakening
  the memory contract. The accepted build is resident `$B57F` (44 bytes safe),
  monolithic `$BAC6`, stack `$D000`, with unchanged six sidecars.
- The layout change also invalidated the recursive suite's old fixed-address
  memory oracle, as intended. Diagnostic `151705` passed all 60 UI steps but
  rejected the stale slices. Exact cc65 BSS listings located session admission
  at `$B110-$B111` and all six overlay flags at `$B574-$B579`; authority
  `vice_auto_20260816_152157` passes the full UI, RFJ1, and exact-byte oracle.

## 2026-08-16 — native-pattern implementation audit

- Source and UI-plan audit found no executable `--native-pattern` path. The
  syntax/isolation policy is documented, while shell matching and full-stem
  filters are real, but backend C64-DOS pattern forwarding is currently
  missing. Evidence and matrix case 24 remain honest about that gap.
- Resident has only 44 bytes before `$B5AC`, so this must not be added as more
  inline command code. The selected design extends the cached CMD-path sidecar:
  compact its 219-byte runtime self-test to a small ABI/translation probe while
  retaining the host suite and callable C64 CMD-path regression, then add a
  legacy IEC `$:pattern` translator and a resident-scratch call record.
- The first executable milestone will be read-only `dir --native-pattern` with
  exact translated-open evidence and explicit rejection on non-IEC/nested
  forms. Delete/copy/move native patterns remain disabled until separate
  WhatIf enumeration and confirmation prove their complete target set.

## 2026-08-16 — read-only IEC native-pattern route

- Implemented the first executable native-pattern milestone without adding a
  seventh overlay or moving KERNAL I/O into a sidecar. Overlay 5 translates an
  absolute, unpartitioned, flat legacy-IEC wildcard into `$:PATTERN`; overlay
  6 authorizes the read-only route and returns; resident `dir_iec()` owns the
  actual directory channel. The component is limited to 16 characters and
  must contain `*` or `?`; partitioned, nested/image, Ultimate, non-pattern,
  and undersized-output forms are rejected by host tests.
- Focused VICE authority `vice_auto_20260816_155612` proves unflagged
  `dir 8:/RF*` returns `UNSUPPORTED`, while
  `dir 8:/RF* --native-pattern` reaches the real IEC directory API: the screen
  contains all six `RF*` sidecars plus the matching directory header and
  reports `ENTRIES: 7`. It also proves a non-wildcard native request returns
  `XLATE ERR`. Full command-path authority `155630` passes 83 steps and 33
  assertions, including all older profile/force/translation/matcher checks.
- The byte-saving drive command fold initially used ASCII `OR $20`; repeated
  diagnostics `154556`/`154641`/`154715` exposed that this breaks cc65 PETSCII
  command parsing. The accepted implementation clears PETSCII case bit 7 with
  `AND $7F`; both focused and full suites pass. Keep the nearby source comment
  and do not restore ASCII folding.
- Strict build and structural guards pass. Current map is resident `$B5A8`
  (three bytes before `$B5AC`), monolithic `$BAA8`, stack `$D000`, and six
  sidecars `$FE3`, `$FDF`, `$FF9`, `$FE0`, `$FFD`, `$FFF`. Recursive authority
  `vice_auto_20260816_155730` passes all 60 steps and exact post-STOP bytes at
  session flags `$B139-$B13A` and six overlay flags `$B59D-$B5A2`.
- Generated inventory is 26/26 successful suites with 246 screen/state
  assertions. Requirement case 24 is promoted and the proven count is 43/60:
  unflagged non-root IEC directory paths cannot silently enter C64-DOS native
  matching, while the exact opt-in route is executable. Copy/delete/move
  native patterns remain disabled until their target sets are enumerated under
  WhatIf and confirmed before mutation.
- All new filesystem execution used disposable VICE images. No C64U REST/FTP
  request, feature toggle, launch, configuration change, or storage mutation
  occurred. Never delete or mutate outside
  `u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014` and
  `u:/SD/READYFS_TEST/readyfs-20260815-190355-79014`, and only after re-reading
  marker `.readyfs-owner-readyfs-20260815-190355-79014` in a fresh
  Terminal-owned preflight.

## 2026-08-16 — native action-plan sizing and gateway compaction

- Fixed the mutation contract before implementation: native wildcard commands
  may only perform a read-only directory selection, freeze exact returned
  names into the REU plan, show the complete WhatIf/confirmation set, and then
  run ordinary exact-name actions. Raw wildcard scratch/rename/write commands
  are forbidden. Entry-limit truncation invalidates the plan. The detailed
  contract and intended syntax are in `READYFS_PATH_RESEARCH.md` and the master
  plan.
- A first integrated WhatIf slice reused `recursive_batch`, translated through
  the drive/CMD sidecars, and attempted read-only native enumeration. Even
  after consolidating repeated overlay fetches it ended at `$B5F6`, 75 bytes
  beyond strict `$B5AC`. The entire incomplete slice was removed; no native
  pattern mutation or action preview is shipped or claimed.
- Kept two behavior-preserving gateway compactions: nested operation flags are
  masked once, and every shared-window REU fetch uses one two-argument helper.
  This reduces current resident end to `$B529` (130 safe bytes), monolithic
  `$BAA8`; stack remains `$D000`, sidecars remain
  `$FE3/$FDF/$FF9/$FE0/$FFD/$FFF`. Structural guards were updated to require
  the shared fetch and exact return ordering.
- Post-refactor authorities pass: native pattern `160722`, full command path
  `160730`, and full recursive/capability oracle `160831`. The exact current
  oracle is session flags `$B0BA-$B0BB` and six overlay flags
  `$B51E-$B523`. Inventory remains 26/26 suites, 246 assertions, and 43/60
  numbered cases.
- The next implementation must cooperatively split native admission/enumeration
  rather than putting the rejected 205-byte integrated path back into the
  resident. All testing remained on disposable VICE images; no C64U access,
  feature/configuration change, launch, or storage mutation occurred.

## 2026-08-16 — complete case report and exact editor boundary oracle

- Added a generated 60-row evidence report at
  `artifacts/readyfs/readyfs-ui-case-report.md`/JSON. It rejects missing,
  duplicate, or out-of-range case records and reports the aggregate current
  UI inventory alongside each case's named evidence and remaining proof.
- `vice_auto_20260816_161342` promotes case 25 by proving the VICE
  UCI-absent result and prompt return. `vice_auto_20260816_161744` promotes
  cases 5 and 6: its viewport capture visibly ends in `READYFS255END`, its
  monitor range `$B069-$B168` is exactly the 255 entered bytes followed by
  NUL, and the command reaches the parser without destabilizing editor cases
  7-10.
- The editor runner now treats a missing or byte-different memory artifact as
  failure rather than relying on a screenshot alone. Current generated status
  is 26/26 successful suites, 250 assertions, 46 proven cases, 10 partial,
  and 4 missing.
- All execution was against disposable VICE media. No C64U REST/FTP request,
  launch, configuration change, feature toggle, or storage mutation occurred;
  the exact marker-owned USB1/SD roots remain the only permitted physical
  mutation targets after a fresh Terminal-owned preflight.

## 2026-08-16 — native-pattern exact-name WhatIf proven

- Replaced the rejected inline native-action attempt with a cooperative split:
  backend overlay 4 performs read-only pattern admission, matcher calls,
  exact-name recursive-plan insertion, target/type display, and plan-summary
  rendering. Resident code alone opens and drains the IEC directory channel.
  No sidecar performs IEC/UCI device I/O.
- `vice_auto_20260816_165721` proves the PowerShell-style `--whatif`
  spelling on `copy 8:/RF* 9:/OUT --native-pattern --whatif`. It freezes and
  displays all six exact `RF*` PRG names/types, reports six planned writes
  and zero completed actions, then proves filtered delete WhatIf selects only
  `RFDRIVE`. A non-dry native delete is rejected and the postcondition
  `stat 8:/RFDRIVE` succeeds.
- Native-pattern mutation remains deliberately unavailable. The next phase
  must execute the already-frozen exact plan after confirmation and retain
  RFJ1-before-ACK; it must never send raw wildcard scratch, rename, or write.
- Full regressions pass: command path `vice_auto_20260816_165229`; recursive
  stop/continue, RFJ1, and exact post-STOP capability oracle
  `vice_auto_20260816_165148`. Current exact addresses are session flags
  `$B138-$B139` and overlay flags `$B59C-$B5A1`.
- Strict layout is resident `$B5A7` (4 safe bytes before `$B5AC`),
  monolithic `$BAA8`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FF9/$FF0/$FFD/$FFF`. Backend boot admission now uses its ABI
  plus compact build probe; the removed oversized pipeline boot self-test is
  superseded by the real VICE action/RFJ1 suites.
- All filesystem execution used disposable VICE images. No C64U REST/FTP
  access, launch, feature/configuration change, or storage mutation occurred.
- Generated status after this milestone is 26/26 successful suites, 258
  assertions, 46 proven cases, 10 partial, and 4 missing.

## 2026-08-16 — native-pattern exact-name apply proven

- Added explicit `--apply` admission for native-pattern copy/move/delete.
  `--whatif` is still zero-write, while a bare native-pattern action remains
  denied even when `--force`/`--yes` is present. The applying invocation first
  performs the same read-only directory query, filters and prints all exact
  targets, freezes them in the REU plan, and only then starts the ordinary
  exact-name recursive executor. No wildcard scratch/write/rename operation
  exists.
- `vice_auto_20260816_170718` proves three real disposable-media paths:
  singleton wildcard delete, two-file IEC8→IEC9 copy with exact comparison,
  and IEC8→IEC9 move with source-absent/destination-present postconditions.
  Exact screen totals are `1/1`, `2/2`, and `1/1`, all with zero failures.
- The runner dumps and parses RFJ1 after copy and move. Copy is FINISHED mode
  1 with exact successful stems `RFNC1`/`RFNC2` at plan offsets 0/12; move is
  FINISHED mode 2 with exact successful stem `RFNM1` at offset 0. This is the
  journal-before-ACK oracle, independent of the screenshots.
- Strict resident layout is unchanged at `$B5A7` (4 bytes before `$B5AC`).
  Help/journal is now `$FFC`; backend/native planner is `$FFF` (one byte free);
  the other sidecars remain `$FE3/$FDF/$FFD/$FFF`. Further backend/help work
  requires measured compaction, not an overflow exception.
- Generated inventory is 26/26 suites, 273 assertions, 46 proven cases, 10
  partial, and 4 missing. All new mutation used freshly formatted local VICE
  D81 images. No C64U REST/FTP access, launch, mapping/configuration change, or
  physical filesystem operation occurred; the exact USB1/SD marker gates are
  unchanged.

## 2026-08-16 — native whole-plan admission hardened

- Compacted dry-run option lookup and the backend option scanner, then added
  two pre-execution gates. Native copy/move to a regular IEC device now
  requires its flat root rather than a fictitious subdirectory; native plan
  entries admit only SEQ/PRG/USR and reject REL/other types before START.
- `vice_auto_20260816_171906` proves the invalid `9:/OUT` collection target
  returns `BAD DEST`, while root-target WhatIf, denial without `--apply`, exact
  delete, two-file cross-drive copy, and move all remain green with parsed
  finished RFJ1 journals.
- New overlay D71 suite `vice_auto_20260816_171852` identifies the real
  `CAL26CFG.REL` fixture as `$13`, selects it through native `CAL26CFG*`,
  rejects the plan as `UNSUPPORTED`, and proves the destination absent.
- Full recursive regression `vice_auto_20260816_171947` passes 60 steps/27
  assertions, both RFJ1 parses, and exact post-STOP capability bytes at
  `$B12E-$B12F` and `$B592-$B597`. Command-path `170922` remains 83/33 green.
- Current strict layout: resident `$B59D` (14 bytes before `$B5AC`), monolithic
  `$BA74`, stack `$D000`; sidecars `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF`.
  Generated inventory is 27/27 suites, 278 assertions, 46 proven, 10 partial,
  4 missing.
- All new actions used fresh local VICE D71/D81 copies. No C64U REST/FTP call,
  launch, mapping/configuration change, or physical filesystem operation was
  made; exact marker-owned USB1/SD restrictions remain unchanged.

## 2026-08-16 — resumed physical preflight remains FTP-blocked

- Launched a genuinely Terminal-owned read-only preflight as
  `logs/readyfs_c64u/preflight-20260816-resume-172314` after the user reported
  the C64U available. All seven REST documents (`version`, `info`, `drives`,
  complete configs, and the three relevant config groups) were captured and
  nonempty.
- The first FTP root list reset the connection on all ten bounded attempts.
  Status is exactly `failed:1`; SD/USB1 listings and the two exact ownership
  marker round trips were therefore not available.
- No PRG launch, key injection, feature/configuration call, mapping, file I/O,
  or storage mutation followed. Do not tight-loop retries. A later destructive
  physical suite still requires a fresh successful Terminal-owned FTP marker
  retrieval from the exact USB1 and SD owned roots.

## 2026-08-16 — seventh utility/history sidecar and full-scope audit

- Moved mutation-preview rendering out of the resident and added `rfutil`, a
  seventh `$B600` sidecar cached at overlay-bank `$6000-$6FFF`. It also
  implements explicit `history` output from the existing REU ring and reserves
  its remaining space for the cooperative tree/batch controller. Structural
  guards require slot 7, its ABI, D81 artifact, linker segment, matcher restore,
  and the rule that the sidecar performs no IEC/UCI device I/O.
- Authoritative build report passes at resident `$B3EE` (445 safe bytes before
  `$B5AC`), monolithic `$BF4E`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$6E9`. The build report and REU map now
  inventory all seven cache regions.
- Runtime-overlay UI `vice_auto_20260816_173129` proves history order and exact
  WhatIf summaries for `new`, `move`, and `mount`. Full recursive regression
  `vice_auto_20260816_173239` passes RFJ1 stop/continue and exact post-STOP
  bytes at session `$AF7E-$AF7F` plus seven overlay flags `$B3E2-$B3E8`.
  Generated inventory is 28/28 successful suites with 287 assertions; numbered
  status remains 46 proven, 10 partial, 4 missing.
- Added `READYFS_SCOPE_AUDIT.md`. It explicitly records that the original plan
  still lacks dispatched `capabilities`, `status`, `tree`, `find`, `head`,
  `tail`, `crc32`, `format`, `run`, and `test` commands, plus nested
  cross-backend and physical evidence. A green 60-case report is not the full
  scope boundary.
- No physical call or mutation occurred in this slice. The failed
  Terminal-owned preflight `preflight-20260816-resume-172314` remains the
  latest hardware state; do not retry tightly or mutate until both exact
  markers round-trip in a fresh preflight.

## 2026-08-16 — eighth cooperative tree sidecar and REU runtime proof

- Added `rftree`, an eighth `$B600` sidecar cached at overlay-bank
  `$7000-$7FFF`. Its stackless breadth-first controller keeps 255-byte relative
  stems, exact entry/depth limits, atomic overflow handling, and a session-bank
  checkpoint. Resident code owns UltimateDOS directory streaming and yields
  each entry through the sidecar gateway; the sidecar contains no IEC/UCI I/O.
- Corrected the initial queue map after VICE exposed a real boundary violation:
  session-relative `$E000` is outside the session API's `$0000-$DFEF` range.
  The queue now occupies overlay-bank `$8000-$FFEF`, above all sidecar caches
  and below the probe byte. `vice_auto_20260816_175239` proves REU `INIT`, the
  resident ReadyIRC-derived UCI yield, and bounded `REPORT`; VICE correctly
  produces `TREE FAILED F0 D0` because it has no Ultimate UCI instead of the
  former `TREE OFF` failure.
- Current build authority passes at resident `$B592` (25 safe bytes before
  `$B5AC`), monolithic `$BFED`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$85A/$AD9`. Host tree tests cover nested
  root/child traversal, invalid names, depth, exact limits, and reporting.
  UCI contract verification still passes for four C transports, two assembly
  transports, and five call-site groups.
- Full recursive regression `vice_auto_20260816_175442` passes after relocating
  its diagnostic oracle to current session flags `$B121-$B122` and seven
  capability flags `$B586-$B58C`; captured bytes are exactly `01 01` and seven
  `01` values. This relocation is diagnostic-only and the recursive UI suite
  itself remained green.
- No C64U REST/FTP request or physical mutation occurred. The failed
  Terminal-owned marker preflight `preflight-20260816-resume-172314` remains
  authoritative, so physical tree and 1/16/64 MHz proof are still pending.

## 2026-08-16 — SoftIEC tree adapter and resident workspace lifetime proof

- Added a resident SoftwareIEC adapter to the same `rftree` controller.
  `tree sN:/path` capability-checks UCI, constructs the native `$sN:/path`
  directory request, performs `cbm_opendir/readdir` only in resident code, and
  feeds identical name/kind records into the backend-neutral breadth-first
  queue. UltimateDOS continues to use the ReadyIRC-derived asynchronous UCI
  streaming transport; no device call moved into a sidecar.
- Moved 16-bit formatting and drive-list presentation into `rfutil`. Resident
  drive discovery still performs every bounded IEC LISTEN/status/UNLISTEN
  probe from 8 through 30, then supplies results to the sidecar. VICE authority
  `vice_auto_20260816_180719` proves the drive/tape display, formatted D81
  directory/free values, the existing Ultimate no-UCI tree report, and honest
  `SOFTIEC OFF` refusal for `tree s3:/` when UCI is absent.
- Reclaimed resident space with a guarded lifetime union between alias scratch
  and the staged-backup stream. Tree uses alias scratch while backup is idle;
  staged mutations use backup only after path resolution; the recursive outer
  call now has a distinct resident record and cannot alias backup. The source
  contract verifier rejects restoration of the old recursive alias.
- Current build authority is resident `$B51F` (140 bytes before `$B5AC`),
  monolithic `$C22F`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$AAC/$AD9`. Full recursive authority
  `vice_auto_20260816_180815` passes with exact current session flags
  `$B1A1-$B1A2 = 01 01` and seven capability flags `$B513-$B519 = 01`.
  Aggregate reports remain 28/28 successful plans, 46 proven numbered cases,
  10 partial, and 4 missing; absent physical SoftIEC does not promote a case.
- No physical REST/FTP call or mutation occurred. Fresh exact marker retrieval
  remains mandatory before physical nested or 1/16/64 MHz execution.

## 2026-08-16 — complete successful IEC tree-controller UI cycle

- Added the regular IEC root adapter to `tree`. It deliberately accepts only
  a flat, unpartitioned `N:/` root; folder-capable CMD/SD2IEC paths still
  require profile-specific translation rather than guessing DOS syntax.
- VICE `vice_auto_20260816_181108` is the first complete runtime traversal:
  `tree 8:/` enumerates all nine D81 files through resident IEC I/O, feeds nine
  ADD records to `rftree`, and reports exactly `TREE DONE F9 D0`. The retained
  screenshot is `screens/readyfs_tree_iec_flat.png` in that run.
- Final build authority for this slice is resident `$B57B` (48 bytes before
  `$B5AC`), monolithic `$C22F`, stack `$D000`; sidecar sizes remain
  `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$AAC/$AD9`. Full recursive regression
  `vice_auto_20260816_181146` passes with exact current session flags
  `$B1FD-$B1FE = 01 01` and seven overlay capability flags
  `$B56F-$B575 = 01`. Aggregate reports are 28/28 successful plans and
  46 proven/10 partial/4 missing numbered cases.
- No C64U request or physical filesystem action occurred. UltimateDOS and
  SoftwareIEC successful nested traversal remain behind the fresh exact-marker
  gate; VICE is not being presented as UCI evidence.

## 2026-08-16 — current-build contract regressions and dynamic rollback oracle

- Restored the established user-visible contracts `CONFIG SAVED AND VERIFIED`
  and `VERIFY: IDENTICAL SIGNATURE`. Current-build VICE authorities are
  `vice_auto_20260816_182919` for configuration save/load, `182951` for staged
  copy/move, and `183209` for append and signature verification.
- Replaced case 45's historical fixed free-space oracle with a fixture-derived
  invariant. The wrapper measures the freshly seeded target before launch;
  after a forced disk-full replacement failure it requires the UI and the D64
  directory to report that same value. `vice_auto_20260816_183813` passes at
  113 blocks before and after, with `OLD` byte-identical, exactly five entries,
  and no `RF~xx` staging file.
- Recalculated diagnostic locations from the final map/object layout. Full
  recursive authority `vice_auto_20260816_184011` passes all 60 steps and both
  RFJ1 reports; its post-STOP bytes are session `$B212-$B213 = 01 01` and
  overlay flags `$B584-$B58A = 01` seven times.
- Final build authority is resident `$B590` (27 bytes before `$B5AC`),
  monolithic `$C244`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFC/$FF8/$FFD/$FFF/$AAC/$AD9`. Generated inventory is 28/28
  successful plans, 293 assertions, 46 proven cases, 10 partial, and 4 missing.
- A true Terminal-owned physical preflight at
  `logs/readyfs_c64u/preflight-20260816-resume-physical-181348` captured all
  seven REST documents (firmware 3.14, 16 MiB REU, UCI enabled, 64 MHz,
  SoftIEC bus 11 at `/USB0/`, drive A bus 8/1581) but all ten bounded FTP root
  listings reset. It stopped at `failed:1`; no launch, mapping, config change,
  filesystem I/O, or mutation followed. Do not retry tightly, and do not
  mutate until both exact USB1/SD ownership markers round-trip freshly.

## 2026-08-16 — sidecar command IDs and dispatched capabilities

- Moved the complete command-name/alias table from resident comparisons into
  `rfutil`. Resident dispatch now asks slot 7 for a numeric command ID, then
  invokes the existing typed handler. This reduced resident end from `$B590`
  to `$B2B4`, leaving 759 bytes before `$B5AC`, while retaining all established
  aliases and an explicit unknown-command result.
- Added `capabilities [path]`, with relative paths and aliases resolved by the
  resident before sidecar rendering. It reports endpoint identity, path/leaf
  limits, size units, explicit read/write/delete/rename/mkdir/recurse/image/
  mount/free/sequential bits, and an honest provisional flag. `sN:` displays
  the SoftIEC selector rather than the unrelated IEC partition field.
- VICE `vice_auto_20260816_191949` proves regular IEC, UltimateDOS, SoftIEC
  selector 255, and sequential tape capability screens, the 40-column grouped
  layout, help discovery, unknown-command fallback, history/WhatIf, drives,
  and all three tree admission/runtime paths in one session.
- Current regressions are config `191537`, copy/move `191556`, append `191625`,
  baseline-derived rollback `191722` (104 free blocks both before/after),
  standalone smoke `191826`, and recursive/RFJ1 `192022`. Current diagnostic
  bytes are session `$AF36-$AF37 = 01 01` and seven overlay flags
  `$B2A8-$B2AE = 01`.
- Final build authority is resident `$B2B4`, monolithic `$C4E5`, stack `$D000`;
  sidecars are `$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$FFD/$AD9`. The utility and help
  slots are intentionally near-full; the reclaimed resident space is for
  gateways/device I/O, not for returning command strings to resident RAM.
  Aggregate evidence is 28/28 successful suites, 305 assertions, 46 proven
  numbered cases, 10 partial, and 4 missing. `capabilities` leaves the original
  undispatched list; `status`, `find`, `head`, `tail`, `crc32`, `format`,
  `run`, and `test` remain.

## 2026-08-16 — dispatched status and previous-dispatch state

- Added `status` to the packed slot-7 command table and to help. Its renderer
  lives in the still-spacious `rftree` sidecar, while resident code supplies
  only the current CWD, alias count, REU bank count, readiness bits, and the
  prior dispatch class. No device I/O moved into a sidecar.
- The result label is deliberately `last dispatch`, not a claimed filesystem
  return code. It distinguishes `known`, `unknown`, and `subsystem off` until
  the legacy void command handlers are converted to typed results.
- VICE `vice_auto_20260816_192849` proves CWD `8:/`, zero then one alias, 256
  REU banks, all seven readiness labels, preservation of a prior unknown
  command, and transition back to known after `alias`.
- Final recursive/RFJ1 authority `vice_auto_20260816_192947` passes with exact
  session bytes `$B06D-$B06E = 01 01` and seven overlay flags
  `$B3E0-$B3E6 = 01`. Dynamic rollback `vice_auto_20260816_193027` passes at
  104 free blocks before/after, five entries, preserved `OLD`, and no stage.
- Current build is resident `$B3EC` (447 bytes before `$B5AC`), monolithic
  `$C52F`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFE/$FF8/$FFD/$FFF/$FFE/$C8E`. Aggregate evidence is 28/28
  suites, 312 assertions, 46 proven numbered cases, 10 partial, and 4 missing.
  `status` leaves the undispatched list; typed filesystem results still remain.

## 2026-08-16 — dispatched full-stem find and current safety gate

- Added command ID 35, `find PATH [PATTERN]`, with the same cooperative
  breadth-first traversal used by `tree`. A positional pattern or
  `--include`/`--exclude` is evaluated by the cached matcher against the
  complete relative stem. Directories are still queued when they do not match,
  so a filter cannot prune descendants accidentally; only selected entries are
  displayed and counted.
- `vice_auto_20260816_193554` is the current utility/tree authority. On the
  real overlay D81, `find 8:/ --include RFU*` displays only `RFUTIL` and reports
  exactly `FIND DONE N1 F9 D0`. The captured screen is
  `screens/readyfs_find_filtered.png`. This is flat-IEC UI/controller proof,
  not a claim of physical nested UltimateDOS or SoftIEC traversal.
- The structural pipeline verifier now requires find's include/exclude lookup,
  complete-stem matcher call, command-ID dispatch, cooperative tree gateway,
  and explicit selected/files/directories report. UCI, pipeline, and overlay
  DMA contract verifiers all pass.
- Current recursive/RFJ1 regression `vice_auto_20260816_193818` passes all 60
  steps. The linker-derived diagnostic locations are session
  `$B220-$B221 = 01 01` and seven overlay flags `$B595-$B59B = 01`.
  Baseline-derived rollback `vice_auto_20260816_193859` passes with 104 blocks
  before and after, five entries, byte-preserved `OLD`, and no stage artifact.
- Current build authority is resident `$B5A1`, leaving only 10 bytes before the
  strict `$B5AC` ceiling; monolithic end is `$C54F`, stack `$D000`, and sidecars
  are `$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$FF9/$CF4`. Further command families must
  reclaim resident bytes or add a carefully bounded gateway/sidecar design.
  Aggregate evidence is 28/28 successful suites, 314 assertions, 46 proven
  numbered cases, 10 partial, and 4 missing. `find` is no longer undispatched.
- True Terminal-owned read-only preflight
  `logs/readyfs_c64u/preflight-20260816-resume-goal-1935` captured the REST
  documents but all ten bounded FTP attempts ended with connection reset;
  status is `failed:1`. It did not fetch the exact ownership markers, launch
  ReadyFS, change configuration, map media, or perform filesystem mutation.
  Do not tight-loop retries. Never delete or mutate anything outside the exact
  owned USB1 and SD roots, and perform no mutation at all until each exact
  marker round-trips freshly.

## 2026-08-16 — ninth content sidecar and bounded `head`/`tail`

- Moved the packed numeric command decoder into the shared command module and
  linked it with slot 8, then added command IDs 36/37 for `head` and `tail`.
  Resident dispatch still receives only numeric IDs; no long command-name
  comparisons returned to the four-byte resident margin.
- Added `rfcontent`, a ninth `$B600` sidecar cached at overlay-bank
  `$8000-$8FFF`. The former tree queue now occupies `$9000-$FFEF` (28,656
  bytes), still above its fixed 512-entry bound. The utility gateway routes
  content INIT/ADD/REPORT operations to slot 9 and restores the matcher after
  every chunk. Resident code alone opens, reads, and closes streams.
- `head PATH [LINES]` and `tail PATH [LINES]` default to ten lines and accept
  explicit counts 1 through 255. `head` stops rendering after the requested
  logical lines. `tail` uses a 256-byte controller workspace containing a
  243-byte circular data area; if older bytes fall out, it prints the honest
  `TAIL TRUNCATED` result rather than claiming a complete tail. Both commands
  report a 32-bit read-byte count without cc65 `long` arithmetic.
- Host tests cover bad counts, split-chunk head, split-chunk tail, the bounded
  ring, truncation, last-two-line selection, and the 360-byte total. The
  pipeline verifier now requires INIT, resident stream I/O, ADD, REPORT, the
  bounded ring, and honest truncation; overlay/UCI contract checks remain
  green.
- VICE authority `vice_auto_20260816_203314` proves `HEAD 8:/RFVIEW 3`
  (`VIEW01` through `VIEW03`, 32 bytes), `TAIL 8:/RFVIEW 2` (`VIEW11` and
  `VIEW12`, 84 bytes), the 360-byte long-tail case (`LONG19`, `LONG20`, and
  `TAIL TRUNCATED`), and invalid-count usage. All screenshots were visually
  inspected.
- Full recursive/RFJ1 authority `vice_auto_20260816_203751` passes. Current
  diagnostic bytes are session `$B226-$B227 = 01 01` and overlay flags
  `$B59B-$B5A1 = 01 01 01 01 01 01 07`; `07` is the utility/tree/content
  readiness bitmask. Dynamic rollback `vice_auto_20260816_203833` passes at
  its measured 101-block baseline with the old file preserved and no staging
  artifact.
- Final build authority is resident `$B5A7` (four safe bytes before strict
  `$B5AC`), monolithic `$C5ED`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFE/$FF8/$FFD/$FFF/$DFB/$FAC/$8D6`. No further resident feature
  may be added without compaction or a bounded gateway redesign.
- Generated evidence is 28/28 successful suites and 325 assertions; numbered
  status remains 46 proven, 10 partial, and 4 missing. `head` and `tail` leave
  the undispatched list; `crc32`, `format`, `run`, and `test` remain, along
  with nested cross-backend and physical speed/fault evidence.
- No C64U request or physical filesystem mutation occurred in this slice.
  The latest true Terminal-owned preflight remains
  `logs/readyfs_c64u/preflight-20260816-resume-goal-1935` (`failed:1` after
  ten FTP resets). Never delete or mutate outside the two exact owned roots,
  and do not mutate even those until both exact markers round-trip freshly.

## 2026-08-16 — backend-neutral streaming CRC-32

- Added command ID 38 and `crc32 PATH` to the shared slot-8 decoder and help.
  It reuses the slot-9 INIT/ADD/REPORT gateway, so resident code owns every
  stream open/read/close and the checksum controller remains backend-neutral.
- The controller implements reflected CRC-32/ISO-HDLC (`0xEDB88320`, initial
  and final XOR `0xFFFFFFFF`) as four bytewise lanes. This is deliberate: an
  initial 16-bit expression version caused cc65 to pull shift helpers into the
  resident and fail the strict `$B5AC` ceiling. The bytewise version keeps all
  new work in `rfcontent` and is covered by a split-chunk host oracle.
- Focused VICE authority `vice_auto_20260816_205049` computes
  `CRC32 $6126E7F6` for the exact 84-byte `RFVIEW` fixture, then rechecks head
  and truncated tail. Full utility authority `vice_auto_20260816_205132`
  repeats CRC alongside all prior utility/tree/status/content assertions.
- Final recursive/RFJ1 authority `vice_auto_20260816_205233` passes with
  session `$B222-$B223 = 01 01` and overlay readiness
  `$B597-$B59D = 01 01 01 01 01 01 07`. Final rollback authority
  `vice_auto_20260816_205318` passes at the fixture-derived 101-block baseline.
- Current build report passes at resident `$B5A3` (eight safe bytes before
  `$B5AC`), monolithic `$C5D6`, and sidecars
  `$FE3/$FDF/$FF3/$FF8/$FFD/$FFF/$DFB/$FB3/$B6C`. Aggregate automation is
  29/29 successful suites and 331 assertions. `crc32` leaves the original
  undispatched list; `format`, `run`, and `test` remain.
- Physical state and deletion rules are unchanged; this milestone used only
  fresh local VICE disk images.

## 2026-08-16 — versioned atomic `test` command

- Added command ID 39 and an RFT1 core diagnostic in `rfcontent`. One atomic
  `test` invocation prints its suite manifest and a `PASS 4/4` report. It
  checks count parsing boundaries, CRC-32 against `123456789`, and the bounded
  content workspace without performing filesystem mutation.
- The content call record now uses the alias/backup lifetime storage, which is
  idle during content commands. The utility gateway also pins its one-pointer
  argument in resident BSS before `open_cached()`, avoiding a cc65 nested-call
  lifetime hazard across overlay DMA.
- Focused VICE authority is `vice_auto_20260816_221431`; both test screens were
  visually inspected. Full utility `221450`, recursive/RFJ1 `221535`, and
  replacement rollback `221634` all pass. The recursive diagnostic oracle is
  session `$B20D-$B20E = 01 01` and readiness
  `$B582-$B588 = 01 01 01 01 01 01 07`.
- The strict build report passes at resident `$B58E` (29 safe bytes before
  `$B5AC`), monolithic `$C5C7`, stack `$D000`, with sidecars
  `$FE3/$FDF/$FF8/$FF8/$FFD/$FFF/$DFB/$FB9/$D69`. UCI, overlay-DMA, pipeline,
  host, and UI-report gates are green.
- Aggregate automation is 29/29 suites and 334 assertions; the numbered split
  remains 46 proven, 10 partial, and 4 missing. `test` leaves the original
  missing-command list; `format` and `run` remain.
- No physical request or mutation was made. The latest strict Terminal-owned
  preflight remains `preflight-20260816-resume-goal-1935`, which stopped after
  bounded FTP resets before either exact marker could be read.
- A direct `format` implementation was measured and rejected: it exceeded the
  strict resident ceiling by 230 bytes and slot 9 by 86 bytes. The green tree
  contains none of that command. The next design must reuse the cooperative
  media gateway and a nested sidecar formatter; it may not move IEC I/O into
  an overlay or weaken the disposable-media/WhatIf contract.

## 2026-08-16 — cooperative disposable IEC `format`

- Added a compact formatter to slot 9 and routed `format` through the existing
  media gateway. The validator rechecks a flat `8:/`–`30:/` root, requires a
  freshly cached recognized non-SoftIEC profile, exact ordered
  `--label NAME --id ID --disposable --yes`, a 1–16 byte comma-free label,
  and an exact two-byte comma-free ID. It composes only `N:LABEL,ID`.
  Resident `probe_iec_io()` remains the sole owner of channel-15 write/status
  I/O and normal completion.
- `--dry-run`/`--whatif` is admitted before profile lookup or media I/O and
  reports one planned media action with zero completion. Missing safety
  tokens, unprobed drives, overlong labels, and bad IDs return without I/O.
- To fit safely, the RFT1 diagnostic moved into compact assembly beside the
  formatter and now calls the production count parser. Its CRC32 and workspace
  checks remain independent. Lowercase ca65 source spelling is mandatory for
  assembly-owned words so emitted C64 PETSCII matches keyboard/cc65 strings.
- VICE authority `vice_auto_20260816_224759` uses a freshly generated drive-9
  D81 and passes WhatIf, all rejection gates, exact execution, and final
  directory proof. Independent `c1541` readback reports volume `LAB`, ID `RF`,
  empty media, and 3160 blocks free. Content/RFT1 authority `224611` remains
  `PASS 4/4`; utility/history `224915`, recursive/RFJ1 `232027`, and rollback
  `232427` pass.
- Recursive post-stop automation now emits `readyfs-overlay.lbl` and resolves
  moving BSS admission sentinels for every run. Current labels are session
  `$B227-$B228 = 01 01` and overlay readiness
  `$B59C-$B5A2 = 01 01 01 01 01 01 07`.
- Strict layout passes at resident `$B5A8` (3 safe bytes before `$B5AC`),
  monolithic `$C5BA`, stack `$D000`; sidecars are
  `$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$E19/$FC1/$FF1`. Generated UI inventory is
  30/30 suites and 348 assertions; numbered status remains 46 proven,
  10 partial, and 4 missing. The only original command still undispatched is
  `run script.seq`.
- This milestone formatted only a newly created local VICE image. No C64U
  request or physical filesystem mutation occurred. Physical mutation remains
  forbidden until both exact owned-root markers freshly round-trip in a true
  Terminal-owned run; never delete or mutate outside those two roots.
- One later true Terminal-owned read-only preflight is retained at
  `logs/readyfs_c64u/preflight-20260816-format-resume`. REST version/info/
  drive/config documents were captured, then all ten bounded FTP attempts
  reset and status became `failed:1`. It did not fetch either exact marker,
  launch ReadyFS, change a feature/configuration, mutate a file, or format
  physical media. Do not tight-loop another attempt.

## 2026-08-17 — cooperative `run` scripts and tenth sidecar

- Added command ID 40 and `run SCRIPT.SEQ`. The resident stages the complete
  input stream into a dedicated REU batch bank and closes the source before
  dispatching any command. A 16 KiB script cap, 256-byte checkpoint, and 4 KiB
  `rfbatch` cache are disjoint from the session and nine-main-slice overlay
  banks. Operations are cooperative INIT/NEXT/ACK/REPORT calls.
- Scripts accept one command per line, `#` comments, `onerror stop|continue`,
  and `expect rc N`. Nested `run` is rejected. Interactive confirmations are
  never read from a batch: an operation without its explicit safety tokens
  reports `batch needs --yes` and rc3. Current result codes are deliberately
  described as dispatch-class v1 (0 known, 1 unknown, 2 subsystem off,
  3 batch/directive/prompt error), not yet typed filesystem result codes.
- VICE `vice_auto_20260817_001141` proves success, continue, stop, expected
  failure, expectation mismatch, nested rejection, prompt refusal, and an
  unchanged `ORIGINAL` overwrite guard. C64 SEQ script fixtures must contain
  C64/PETSCII-compatible uppercase bytes; lowercase host ASCII rendered as
  non-command glyphs and is not an admissible fixture encoding.
- The full 255-byte editor moved into `rfbatch`; the monolithic build retains
  a minimal fallback. Current overlay editor `001549` and scrollback `001605`
  pass. The editor memory oracle now resolves `_line_buf` from linker labels,
  avoiding stale BSS addresses after resident layout changes.
- Current recursive/RFJ1 authority `001612` passes after all ten sidecars are
  admitted; replacement rollback `001649` passes. Strict layout is resident
  `$B4BB` (240 safe bytes before `$B5AC`), monolithic `$C1CF`, stack `$D000`;
  sidecars are `$FE3/$FDF/$FFF/$FF8/$FFD/$FFF/$E19/$FDC/$FF1/$FE2`.
- UCI verification remains green for 4 C transports, 2 assembly transports,
  and 5 call-site groups. ReadyFS retains the ReadyIRC-derived asynchronous
  state machine: idle synchronization, one asynchronous PUSH, queue draining,
  DATA_ACC transitions, asynchronous abort recovery, and final quiet-idle
  wait, with poll counts used only as failure bounds so 1/16/64 MHz timing
  cannot become implicit pacing.
- The generated inventory is 31/31 successful suites and 362 assertions;
  numbered status stays 46 proven, 10 partial, and 4 missing. Every original
  command token is now dispatched, but nested physical cross-backend trees,
  mount/swap/map restoration, injected UCI recovery, tape, and typed result
  codes remain functional/evidence gaps.
- No physical C64U request or mutation occurred in this slice. The bounded
  `preflight-20260816-format-resume` failure remains authoritative; both exact
  marker files must freshly round-trip before any mutation, and nothing
  outside the two exact owned USB1/SD roots may ever be deleted or changed.

## 2026-08-17 — read-only UCI abort/recovery probe

- Added `probe recover`. It synchronizes to reusable quiet idle, starts the
  read-only UltimateDOS IDENTIFY command, ignores the first immediate IDLE
  samples until asynchronous PUSH is visibly observed, then uses the shared
  ABORT_P-aware recovery path exactly once and performs a normal re-identify.
  It adds no timing delays; all 4x60000 loops remain failure bounds only.
- `readyfs_uci_test` is a deterministic register/state oracle for delayed
  PUSH, BUSY, ABORT_P, queued data/status draining, DATA_ACC, quiet idle, and
  successful follow-up IDENTIFY. The UCI source verifier now requires this
  contract and requires the physical runner to include `probe recover`.
- VICE utility authority `vice_auto_20260817_002400` proves the no-UCI path
  returns `UCI RECOVER: OFF` and the prompt remains usable. That suite was also
  corrected for the now-20-entry overlay D81: it advances the directory page
  and expects exact tree/find totals of 20 instead of the stale 12.
- Current editor `002517`, batch `002532`, recursive/RFJ1 `002551`, and
  rollback `002634` pass after the resident change. Layout is resident `$B5A5`
  (6 safe bytes), monolithic `$C2B9`, stack `$D000`; the help/journal sidecar is
  exactly `$1000`. Inventory is 31/31 suites and 363 assertions.
- The true Terminal-owned 1/16/64 MHz read-only runner now executes interrupted
  IDENTIFY/recovery/re-identify at every speed. It was intentionally not run:
  the latest bounded preflight could not fetch either marker because FTP reset
  ten times, and tight-looping is prohibited. No physical request, config
  change, file mutation, or deletion occurred.

## 2026-08-17 — capability-honest tape boundary

- Extended the utility UI suite to prove that `t:/` advertises only sequential
  access and never pretends to have directories, random-access copies,
  deletion, recursion, or meaningful free space. `dir`, copy, delete, and tree
  all return `UNSUPPORTED` before device I/O.
- VICE authority is `vice_auto_20260817_002914`; the tape-copy refusal screen
  was visually inspected. The host backend oracle independently checks exact
  `RF_CAP_SEQUENTIAL` with byte-size units disabled/provisional.
- This moves tape from endpoint-only missing to a partial driver boundary.
  Disposable TAP-backed KERNAL sequential read/write, motor/user-prompt
  behavior, cancellation, and byte-for-byte playback/recording oracles remain.
- Inventory is 31/31 suites and 367 assertions. No physical request or
  filesystem mutation occurred; the exact owned-root/marker gate is unchanged.

## 2026-08-17 — physical UCI recovery at 1/16/64 MHz

- A new recovery-only speed-matrix mode isolates `probe recover` from unrelated
  directory rendering. True Terminal-owned authority
  `speed-matrix-20260817-uci-recover-only` passes at 1, 16, and 64 MHz. Every
  screen reports `UCI RECOVER: QUIET`, successful UltimateDOS V1.2 re-identify,
  and the returned prompt.
- The matrix EXIT trap restored and freshly read back the exact original
  `Turbo Control: TurboEnable Bit` and `CPU Speed: 64`. It performed no file,
  mapping, or media mutation. Numbered case 59 is now proven, producing
  47 proven, 9 partial, and 4 missing cases.
- The first full read-only attempt `speed-matrix-20260817-uci-recover` is
  retained as failed/non-authoritative: recovery passed at 1 MHz, then the
  unrelated large USB1 directory step failed. Its normal restore and a
  separate Terminal-owned exact-payload restore both read back 64 MHz.
- Current preflight `preflight-20260817-uci-recovery-resume` captured REST,
  confirmed SoftIEC enabled on bus 11, then failed after ten FTP resets. It
  fetched no marker and made no filesystem mutation. Marker-gated work remains
  forbidden; do not tight-loop FTP.

## 2026-08-17 — physical IEC↔UltimateDOS PRG round trip

- Added the true Terminal-owned `run_readyfs_c64u_cross_owned.sh` harness. It
  uses no FTP: it multipart-mounts a disposable D81 on Drive A, refuses a
  nonempty original slot, and restores/readbacks the exact original Drive A
  enabled/bus/type/image state on every exit path.
- Authoritative run `cross-owned-20260817-iec-udos-roundtrip-k` rereads the
  exact USB1 and SD 116-byte ownership markers immediately before each
  mutation. It creates only the fresh preserved USB1 folder
  `cross-20260817-iec-udos-roundtrip-k`; it does not delete any host file or
  folder. Never delete or mutate outside the two exact marker-owned roots.
- Physical 1581 directory entries exposed bit-7 PETSCII names (`D2...` versus
  typed `52...`). ReadyFS now compares those forms coherently, retains the raw
  directory spelling for opens and existing-name rename operands, and leaves
  new destination spelling untouched. Focused VICE authority
  `vice_auto_20260817_013435` keeps copy/move behavior green.
- Both directions copy exactly 4069 bytes and preserve PRG type `$11`.
  Forward Ultimate stat reports exact 4069 bytes; reverse IEC stat reports 17
  blocks, and the final D81 directory contains `RFROUND`. Independent content
  comparison reads endpoints sequentially and compares full 32-bit length plus
  the existing running CRC signature, so backend chunk sizes cannot create a
  false mismatch.
- Cases 40 and 41 are promoted. Current generated status is 49 proven, 9
  partial, 2 missing; 31/31 VICE suites and 367 assertions remain green.
  Strict layout is resident `$B549` (98 safe bytes before `$B5AC`) and
  monolithic `$C25D`.
- Visually inspected the current focused VICE capture
  `vice_auto_20260817_013435/screens/rf_ui_44_move_postcheck.png`; it shows the
  old source absent and the moved PRG as display/raw `MOVED`, type `$11`, and
  one estimated C64 block at the returned prompt.

## 2026-08-17 — SoftwareIEC 3.14 fail-closed boundary

- Primary documentation and physical tests establish the current contract:
  OPEN/CLOSE and `CD:` work; `MD:`, `R:`, and SD2IEC path-qualified directory
  commands do not. ADD_PARTITION returned `$01` without changing drive
  inventory. REST Default Path truncated long input and never changed the live
  partition; every config experiment restored/read back the exact baseline.
- Safe failed runs `softiec-owned-20260817-040632`, `040857`, and `041716`
  stopped at their first unsupported/unverified operation. Each used fresh
  dual-marker gates and a unique exact-owned USB1 folder, and deleted nothing.
  Independent read-only evidence shows `rf041716` empty and root `sfa.seq`
  absent; preserve all possible failed artifacts regardless.
- `softiec_enter_parent()` now derives the parent from immutable canonical
  spelling and requires command-channel status `00`; OPEN success alone can no
  longer authorize a leaf operation. Direct create applies only after absence
  is proven, never to replacement.
- True Terminal-owned read-only run
  `ui-readonly-soft-status-longpath-20260817-0430` proves fail-closed behavior
  for the long owned path. Component-by-component status-checked `CD:` remains
  required for actual owned file/copy/tree evidence.
- Strict resident layout is `$B5AA` (one safe byte). Focused green VICE runs
  are `041515`, `041535`, full batch/typed `041653`, and command-path `043339`.
  The command-path harness now advances pagination and expects all 21 current
  `RF*` entries. Earlier `042734`/`043054`/`043219` runs are retained as failed
  stale-oracle diagnostics.

## 2026-08-17 — SoftwareIEC component sequencer and typed-status regression

- Added `RF_UTILITY_SOFT_CD` to slot 7. It emits bounded component `CD:`
  commands from immutable canonical paths; `softiec_enter_parent()` resets to
  the virtual root, invokes the sidecar cooperatively, and keeps all IEC
  command-channel I/O/status validation resident. The pipeline verifier now
  enforces this ownership and ordering.
- This is preparatory, not interoperability proof. Read-only physical evidence
  `ui-readonly-soft-root-dir-20260817-0453` shows the global SoftwareIEC root
  (`/`, `SD`, `FLASH`, `TEMP`, `USB1`), while
  `ui-readonly-soft-component-diag-20260817-0445` records `CD:/USB0` returning
  directory error. The exact media bridge is unresolved, so leaf I/O fails
  closed and `dir s0:/` returns `UNSUPPORTED` rather than presenting that
  global namespace as partition contents. Cases 42/43 remain missing.
- No further physical mutation was attempted. Preserve `rf040857`, `rf041716`,
  and every earlier failed artifact; never delete or mutate outside the exact
  marker-owned USB1/SD roots.
- Fixed a typed-result regression found by UI automation: dispatch reset
  `last_result` before `status` rendered it. `status` now observes the previous
  command, while every other recognized command starts at `OK`. VICE utility
  authority `vice_auto_20260817_050201` proves unknown result 1 followed by a
  successful alias result 0; batch authority `vice_auto_20260817_050249`
  keeps the typed usage/not-found/conflict cases green.
- Current generated reports are 31/31 successful plans, 49 proven, 9 partial,
  and 2 missing cases. The exact build report is resident `$B53E` (109 safe
  bytes before `$B5AC`), monolithic `$C44C`, utility sidecar `$FE9`; UCI,
  overlay-DMA, pipeline, and build-contract verifiers all pass.
- Added `readyfs_utility_test.c` to `make readyfs`; its behavioral oracle
  verifies the virtual-root bridge command, ordered parent components, leaf
  exclusion, and root-file termination. The `050201` typed-status and `050249`
  typed-batch screenshots were also visually inspected and match their screen
  decodes.

## 2026-08-17 — explicit ReadyIRC UCI transport audit

- Compared ReadyFS directly with `readyirc_uci.c`: both require reusable quiet
  IDLE with BUSY/DATA_ACC/ABORT_P/ERROR clear, treat immediate post-PUSH IDLE
  as unobserved work, accept only DATA_LAST/DATA_MORE, drain data and status
  queues completely, request ABORT at most once, service ABORT_P, and use four
  bounded 60,000-poll passes as failure limits rather than timing delays.
- ReadyFS retains the hardware-derived strengthening needed at 64 MHz: the
  slot-local assembly helper places DATA_ACC adjacent to observation of the
  required MORE-to-BUSY transition, so ordinary C call overhead cannot miss
  the transient. Every app-level UCI operation still enters through the sole
  `readyfs_uci_command()` gateway.
- Expanded `readyfs_uci_test.c` beyond recovery/re-identify. It now proves a
  two-block MORE/LAST response and callback boundaries, complete drain despite
  capture truncation, data/status truncation flags, transport ERROR recovery,
  and rejection of commands larger than the documented 896-byte queue. The
  UCI source verifier now requires these oracles and the adjacent assembly
  transition helper. Verifier and full host suite pass.

## 2026-08-17 — typed unavailable/unsupported command results

- Converted resident command-surface `UNAVAILABLE` and `UNSUPPORTED` paths to
  stable result codes 2 and 7 using two compact fastcall helpers. This covers
  missing UCI/SoftIEC, missing overlays/sidecars, unsupported endpoint/path/
  REL cases, and the fail-closed SoftIEC directory boundary. Existing typed
  usage 4, not-found 5, and conflict 6 cases remain intact.
- A generic two-argument helper failed the strict layout gate by 132 bytes;
  cc65 software-stack setup made it unsuitable. The final result-specific
  design passes at resident `$B587`, leaving 36 bytes before `$B5AC`;
  monolithic ends `$C49E` and utility remains `$FE9`.
- VICE utility authority `vice_auto_20260817_052447` proves `dir s0:/` with
  absent UCI reports `SOFTIEC OFF` then `LAST RESULT: 2`, and `dir t:/`
  reports `UNSUPPORTED` then `LAST RESULT: 7`. Both captures were visually
  inspected. Batch authority `vice_auto_20260817_052540` remains green.
- Generated evidence is 31/31 suites with 372 assertions; the numbered split
  remains 49 proven, 9 partial, and 2 missing. Full build, UCI, DMA, pipeline,
  component-CD, and host tests pass.

## 2026-08-17 — SoftwareIEC virtual-root bridge proven; empty-dir boundary isolated

- Official firmware source and the physical unit explain the earlier mismatch:
  configured partition 0 still names legacy `/USB0/`, while the live global
  virtual root exposes `USB1`. Read-only Terminal probes now prove the bounded
  sequence `cd:/`, relative `cd:usb1`, `cd:READYFS_TEST`, and the exact owned
  run component with DOS status `00` at every step. The decisive evidence is
  `softpath-readonly-20260817-softpath-source-e`; `source-h` also enters the
  short exact-owned `rf061009` folder.
- cc65/PETSCII requires a backend spelling rule: the typed underscore key is
  `$A4`, but SoftwareIEC's FAT-name bridge matches host `_` as `$5F`. ReadyFS
  now converts that byte only in the standalone SoftwareIEC component adapter,
  including the leaf, and keeps visible/UltimateDOS spelling unchanged. The
  host utility test covers both parent and leaf conversion. A compact overlay
  implementation remains pending rather than overflowing slot 7.
- The marker-gated suite `softiec-owned-20260817-061009` freshly verified both
  exact 116-byte USB1/SD markers, created only preserved folder `rf061009`,
  reverified both markers, and then timed out before the first file write. It
  performed no delete and created no file. Preserve the folder.
- `softpath-readonly-20260817-softpath-source-i` isolates the remaining issue:
  read-only OPEN of missing `sfa.seq` returns 0 from `cbm_open` but DOS `62`.
  SoftwareIEC 3.14 can omit the terminating BASIC-directory record in that
  empty host folder, so exhaustive absence lookup blocks. An attempted direct
  OPEN/status implementation was rejected because it exceeded strict resident
  memory; no unsafe overwrite shortcut was retained. Cases 42/43 stay missing.
- Current green build is resident `$B587` (36 bytes before `$B5AC`), monolithic
  `$C4E7`, utility `$FE7`, batch `$FD7`. Focused VICE runs editor `062227`,
  batch `062243`, utility `062304`, smoke `062532`, and paced paths `063042`
  pass. The path harness now updates stale typed-result text and generates a
  paced plan to prevent stale-screen command concatenation. Reports are 31/31
  successful, 49 proven, 9 partial, and 2 missing.

## 2026-08-17 — SoftwareIEC type authority and exact-channel completion

- Firmware 3.14's BASIC directory stream is not exhaustive for host folders;
  it can emit a host-path header and stop before later FAT entries. ReadyFS
  replaced directory-based type lookup with explicit non-creating SEQ, PRG,
  and USR OPEN/status probes. REL is deliberately excluded: official firmware
  source shows REL OPEN uses `FA_OPEN_ALWAYS` and can create a missing file.
  Preserve the diagnostic artifact `rf065128/ap1000.rel`; do not delete it.
- Standalone startup now performs KERNAL `CLALL`, preventing a REST-launched
  PRG from inheriting stale logical files. Trace app write authority
  `softwrite-noftp-20260817-1100-af` and production `1115-ag` both write,
  verify, and read the same four-byte SEQ through SoftwareIEC and raw
  UltimateDOS with both ownership markers unchanged.
- Flat SoftwareIEC-to-UltimateDOS and UltimateDOS-to-SoftwareIEC transfers
  completed in trace `softiec-owned-20260817-1145-ai` and production
  `softiec-owned-20260817-1235-al`; the latter then stalled only when the next
  command reopened the just-read SoftIEC file. All created files/folders are
  preserved and neither suite issued a delete.
- Official `softiec_target.cc`/`iec_channel.cc` prove target-5 `$14` closes one
  exact secondary address synchronously. ReadyFS now closes read channel 2 at
  the next SoftIEC parent boundary and probe channel 6 before reading DOS
  status, using the ReadyIRC-derived UCI transaction state machine. This is
  protocol completion, not MHz-sensitive pacing. Because UCI status aliases
  IEC-status scratch, reading DOS status after CLOSE is mandatory; the earlier
  order temporarily made an absent `ap0846` appear as SEQ. Read-only authority
  `softwrite-noftp-20260817-ap0846-read2` now proves `NOT FOUND` and raw
  `FILE DOESN'T EXIST` for the same leaf.
- The exact formerly failing sequence passes both trace
  `softwrite-noftp-20260817-uci-close-trace` and production
  `softwrite-noftp-20260817-uci-close-prod`: compare UltimateDOS against
  SoftIEC, immediately type the SoftIEC file in the same process, then recheck
  both exact owner markers. Trace new-file authority
  `softwrite-noftp-20260817-uci-close6-trace2` additionally creates only
  preserved `rf083856/ap0853.seq`, verifies SoftIEC and raw readback, and
  passes post-owner gates.
- Failed full diagnostic `softiec-owned-20260817-uci-close-full` created only
  preserved `rf083856` before the channel-6 fix. Full production rerun
  `softiec-owned-20260817-close26-full2` is pending. Current green layout is
  resident `$B5AA` (one byte before `$B5AC`), monolithic `$C502`, trace
  `$C5F7`; all UCI, overlay-DMA, pipeline, build, and host checks pass.

## 2026-08-17 — physical flat and nested SoftwareIEC interoperability

- A non-screen diagnostic build used one RAM stage byte and proved the
  production stall was at SoftwareIEC root command entry, not file probing.
  Trace-only passes were correctly rejected as timing evidence. The final
  production sequence is exact LFN2 CLOSE, target-5 IDENTIFY as a serialized
  firmware-worker transaction, then the IEC root/component commands. Exact
  target-5 LFN6 CLOSE remains after each non-REL type probe.
- Removed the redundant pre-command status-drain OPEN. Each `CD:` now executes
  once and returns its own status; the old two-OPEN form reproducibly stalled
  on the ninth command-channel OPEN at 64 MHz. Pipeline verification enforces
  the single transaction and close→barrier→root ordering.
- Focused production `softwrite-noftp-20260817-ident-close2-prod` proves the
  formerly failing UltimateDOS→SoftwareIEC copy, immediate SoftIEC read,
  independent compare, and exact post-owner checks without timing loops.
- The broad owned root exposed a firmware breadth limit: newly appended
  top-level `rf094315` remains unreachable through SoftwareIEC even after a
  preserved `rfseed.seq` and reboot with exact SoftIEC config equality. A
  fresh child under visible, uncrowded `rf091800` works immediately. This
  backend boundary stays explicit in the path/refresh design.
- Production mutation authority
  `softiec-owned-20260817-nested-parent-prod-full` created preserved
  `rf091800/rf100154`, wrote/read `sfa`, copied it to raw `fs100154.seq`, wrote
  raw `us100154.seq`, copied it back to `fromu`, verified and reread it,
  created `nested`, and wrote/read `nested/inside`. Every mutation had fresh
  USB1/SD owner gates. Its only failure was a stale uppercase raw-name oracle.
  Final-artifact read-only continuation `softwrite-noftp-20260817-treeverify-final` proves the
  lowercase raw listing, both flat contents, independent comparison, nested
  raw readback, and both final owner markers.
- Case 42 is PROVEN. Case 43 is PARTIAL because nested physical behavior is
  proven but recursive whole-tree copy is not. Reports are 31/31 VICE suites,
  372 assertions, 50 proven, 10 partial, 0 missing. Final layout is resident
  `$B5A2` (nine safe bytes), monolithic `$C4FA`; utility `101607`, smoke
  `101701`, paths `101711`, all host tests, and all verifiers pass.

## 2026-08-17 — recursive UltimateDOS-to-SoftwareIEC tree physically proven

- UltimateDOS `READ_DIR` returns a C64-facing access spelling for lowercase
  host names, for example `[736661].[736571].SEQ`. Recursive copy now keeps
  that exact spelling on the Ultimate source path but decodes it only on the
  IEC destination side. It removes the final Ultimate type annotation and a
  matching host type extension, producing logical `sfa`, `fromu`, and
  `nested/inside` names rather than encoded SoftIEC filenames. The compact
  implementation lives in recursive sidecar assembly; host tests cover flat,
  nested, type-suffix, and non-type-extension cases.
- Physical diagnostic `rr5-final2` passed both owner gates and copied/verifed
  the two flat files, then stalled while REST automation DMA-read the screen
  every second during the nested KERNAL/SoftIEC transition. It timed out
  boundedly, restored Drive A exactly, and is preserved. No file is deleted.
- Production `rr5-final3` reran the same exact-owned `rr111505` target but gave
  the recursive command a four-minute no-poll window. It reports
  `RECURSIVE PLAN F4 SELECTED 4`, verifies/copies 10, 11, and 7 bytes, and
  finishes `BATCH DONE 4/4 FAIL 0`. Independent comparisons for all three
  files pass, the raw Ultimate directory contains normal lowercase host names,
  logical `nested/inside` reads `INSIDE`, both final owner markers pass, and
  Drive A matches its captured empty 1581 baseline exactly.
- Fresh read-only process `rr5-verify` independently proves the preserved
  `rf091800/rr111505` tree: both flat logical reads, source-to-destination
  compare, raw destination directory, raw nested read, both exact owners, and
  exact Drive A restoration all pass. Case 43 is therefore PROVEN.
- Firmware 3.14's POST runner attachment handoff currently returns
  404/`Cannot open file`; FTP also resets. The physical harness now has a
  bounded fallback that loads only build-owned `READYFS-OVERLAY` from the
  already mounted disposable D81 by normal IEC, waits without REST DMA during
  the 167-block transfer, and still requires overlay admission plus both owner
  markers before any mutation. Runner diagnostics do not authorize cleanup.
- Preserve `rr111504` with its earlier encoded-name diagnostics,
  `rr111505` with the corrected tree, failed `rr5-final`/`rr5-final2`, and all
  runner diagnostic logs. Never delete any of them or anything outside the two
  exact marker-owned roots. Generated evidence is now 51 proven, 9 partial,
  and 0 missing cases after regeneration. Full `make readyfs` passes with
  resident `$B5A0` (11 safe bytes), monolithic `$C491`, recursive sidecar
  `$F67`, all host tests, UCI/DMA/pipeline/build verifiers, and 11 disjoint
  sidecars. Current recursive VICE authority `vice_auto_20260817_135206`
  passes plus post-stop capability memory; the generated UI inventory is
  32/32 suites with 373 assertions.

## 2026-08-17 — physical mount/swap/dismount and mkdir RFJ1 fix

- Physical media diagnostics exposed a real post-mutation bug: UltimateDOS
  created an owned directory, but `MKDIR` supplied no `source_root` to the
  fixed-size completion journal and returned silently before its UI result.
  Resident admission now duplicates the mkdir destination as its compact RFJ1
  identity while the backend continues treating mkdir as destination-only.
  The pipeline verifier locks that call shape. Full build and all host/UCI/
  DMA/pipeline checks pass at resident `$B5A6` (five safe bytes), monolithic
  `$C491`, backend `$FF8`, recursive `$F67`, and 11 disjoint sidecars.
- The physical harness no longer screen-DMAs immediately after overlay launch;
  one early read can pin the first KERNAL sidecar load at `RFMATCH` on the
  64-MHz machine. It gives the complete preload one quiet window and also
  gives each UCI media mutation a quiet completion window. These delays are
  automation discipline only; application UCI remains the ReadyIRC-derived
  asynchronous state machine.
- True Terminal-owned authority `softwrite-noftp-media-145816` passes every
  owner gate, creates and preserves `md145816/DISK1.D81` and `DISK2.D81`,
  mounts disk 1 on drive 8, swaps deterministically to disk 2, dismounts to
  empty image fields, rechecks both owners, and restores the original Drive A
  state exactly. Independent REST snapshots verify all three transitions.
  No delete was issued.
- Preserve lowercase diagnostic pair `md144209/disk1.d81` and `disk2.d81`:
  listing displays those names normally, but mount preflight sees the
  firmware's bracket-hex access spelling. This remains a deliberate metadata/
  raw-name gap for cases 19 and 33, not a hidden success. Preserve empty
  diagnostic folders `md140757` and `md142820` too.
- Cases 53 and 54 are PROVEN. Generated evidence is 53 proven, 7 partial,
  0 missing. Stale VICE prompt text `RF> #` was corrected to the actual
  `RF>`; action suite `vice_auto_20260817_151512` passes and current inventory
  is 32/32 suites with 373 assertions.

## 2026-08-17 — SoftIEC map capability boundary and current regressions

- Current official firmware target-5 implementation and its bundled UCI
  documentation expose IDENTIFY `$01` and file/channel operations `$10`–`$16`.
  They do not implement the speculative partition add/delete commands
  `$20/$21` found in the ReadyOS UCI test catalog. Therefore firmware 3.14
  cannot presently execute ReadyFS SoftIEC map/unmap.
- True Terminal-owned, marker-gated runs
  `softwrite-noftp-20260817-155612` and
  `softwrite-noftp-20260817-160912` each completed all read-only prechecks,
  then received target status `$01` for `$20`. Neither added partition 1;
  partition 0 remained exactly
  `/USB1/READYFS_TEST/READYFS-20260815-190355-79014/RF091800/RR111505/`.
  Drive A was restored exactly, no delete was issued, and no filesystem object
  was changed. Preserve these failed runs as the capability-boundary evidence.
- This is not a transport race. ReadyFS still uses the ReadyIRC-derived
  asynchronous UCI contract, and its interrupted-command recovery remains
  physically proven at 1, 16, and 64 MHz. Target status `$01` is a valid reply
  from unsupported target command handling, not a UCI `ERROR`.
- The future-facing map path encoder was corrected independently: it preserves
  the current live `/USB1` virtual-root spelling instead of rewriting it to
  legacy `/USB0`, and converts typed PETSCII underscore `$A4` to host
  underscore `$5F` only at the SoftIEC boundary. Pipeline verification locks
  both rules. Case 55 remains PARTIAL/provisional until firmware/device support
  for `$20/$21` exists; do not burn hardware time retrying path variants on
  firmware 3.14.
- Stale VICE assertions were aligned with current exact output:
  `VERIFY: IDENTICAL` in the append suite and `DRY-RUN` in the recursive-plan
  suite. Fresh authorities are smoke `vice_auto_20260817_160934`, paths
  `vice_auto_20260817_160944`, pipeline actions
  `vice_auto_20260817_161030`, append `vice_auto_20260817_160143`, and
  recursive plan `vice_auto_20260817_161401`. Full `make readyfs` passes at
  resident `$B523` (136 bytes before `$B5AC`), monolithic `$C40E`, recursive
  `$F67`, and 11 disjoint sidecars. Reports remain 32/32 suites with 373
  assertions and 53 proven / 7 partial / 0 missing cases.

## 2026-08-17 — physical nested filtered WhatIf proven

- Read-only tree-spelling diagnostics isolated the filter failure without
  changing the owned media. `tree-spelling-171326` shows the nested relative
  stem `NESTED/inside.seq`; `tree-bytes-172216` captures those exact bytes;
  `match-literal-172014` proves the matcher core accepts a same-spelling
  literal. Preserve failed no-mutation runs `whatif-filter-162725`,
  `whatif-filter-logical-164055`, `whatif-filter-fixed-165954`,
  `whatif-filter-atomic-172920`, and
  `softwrite-noftp-whatif-filter-asm-175230`. Each reported `W0 D0 M0` and
  restored Drive A exactly. Rejected launch
  `softwrite-noftp-whatif-filter-asm-175200` failed its local destination-name
  safety check before contacting the C64U.
- The root cause was target character representation, not UCI transport or
  overlay DMA. cc65 translates the C character literal `A` to PETSCII `$C1`,
  so the old fold ignored ASCII `$41-$5A` from injected commands and ASCII
  `$61-$7A` retained by Ultimate host names. The actual source combined
  uppercase directory bytes with lowercase leaf bytes. Matcher folding now
  maps ASCII uppercase, ASCII lowercase, and PETSCII `$C1-$DA` coherently.
  The cc65 overlay uses the same compact assembly access-name decoder/type
  stripper already proven by recursive copy; host tests retain defensive
  malformed-input normalization and add PETSCII/ASCII coverage.
- True Terminal-owned run
  `softwrite-noftp-whatif-filter-casefold-180400` passes 21 command checks.
  `copy ... --recursive --whatif --include **/inside` reports
  `RECURSIVE PLAN F4 SELECTED 1` and
  `PLAN W1 D0 M0; DONE W0 D0 M0`. Before/after source-root, nested-directory,
  and mapped-destination screens compare exactly; all three source CRC lines
  compare exactly; `wf180400` was never created; both exact owner markers pass
  before and after; and restored Drive A is byte-for-byte identical to its
  captured baseline. Case 52 is PROVEN.
- Full `make readyfs`, the UCI protocol verifier, all host suites, overlay DMA
  and pipeline verifiers pass. Current build is resident `$B599` (18 bytes
  before `$B5AC`), monolithic `$C428`, matcher `$733`, recursive `$F67`, with
  11 disjoint sidecars. Current recursive VICE authority is
  `vice_auto_20260817_180205`. Generated evidence is 32/32 suites, 373
  assertions, and 54 proven / 6 partial / 0 missing cases.

## 2026-08-17 — forced post-config failure restoration proven

- Added an opt-in, fail-closed physical harness branch admitted only for
  read-only WhatIf mode with an explicit CPU speed. It changes only captured
  Turbo Control/CPU Speed values, verifies the new speed, requires full
  overlay admission, reads both exact owners twice, writes a trigger record,
  then deliberately exits 73. Its EXIT trap rereads both owners while the app
  is still live, restores Drive A, restores speed, and requires the complete
  `U64 Specific Settings` object to equal the original. Any recovery mismatch
  changes the final result to 97.
- Aggregate `/configs` writes currently return HTTP 500 on this firmware state.
  Test-speed admission therefore uses the firmware per-setting PUT interface,
  enters Manual before speed, and applies Off last only for 1 MHz. Restoration
  retains the exact saved JSON and bounded reset/reboot/per-setting recovery
  helper. These are harness configuration transactions, not application UCI
  pacing.
- Preserve non-authoritative early failures
  `softwrite-noftp-forced-restore-182200` and
  `softwrite-noftp-forced-restore-16-183100`. Both stopped before the intended
  trigger because aggregate config admission returned 500; full settings were
  restored exactly. Their post-reboot screen attempts are not owner evidence
  and must not be cited as such.
- True Terminal-owned authority
  `softwrite-noftp-forced-restore-put-16-183320` independently reads back
  `Turbo Control: Manual` and `CPU Speed: 16`, passes both USB1/SD marker
  screens twice before the trigger and once again from the live failure trap,
  writes the deliberate-trigger record, and finishes `failed:73`. The helper
  recovers an aggregate restore 500, reports success, and the complete original
  and restored U64 settings JSON objects compare equal. Original/restored drive
  JSON also compares equal, including enabled bus-8 1581 and empty image fields.
  No filesystem or media mutation occurred. Case 60 is PROVEN; generated
  status is 55 proven / 5 partial / 0 missing.

## 2026-08-17 — exact lowercase image metadata and unit identities proven

- UltimateDOS leaf lookup now separates three identities: canonical ReadyFS
  display path, exact READ_DIR access spelling, and decoded host filename.
  The matcher sidecar decodes bracket-hex only when firmware uses it, strips
  only the final UCI type annotation, compares ASCII/PETSCII case coherently,
  and returns the untouched access spelling for subsequent UCI operations.
  The resident callback writes its fixed call record directly into the shared
  pipeline scratch, keeping the hard build boundary intact.
- `stat u:/.../md144209/disk1.d81` on physical firmware 3.14 reports canonical
  display, exact access `disk1.d81`, host `disk1.d81`, type `$10`, exact
  `819200 BYTES`, and `STATUS: OK`. This safe lowercase name is returned raw
  on this firmware; bracket-hex remains supported and host-tested for unsafe
  bytes but is not falsely claimed as the observed physical spelling.
- True Terminal-owned authority
  `softwrite-noftp-metadata-lowercase5-20260817-2004` then reports SoftwareIEC
  partition 0/bus 11/target `$01` with `FREE UNAVAILABLE`, mounts that lowercase
  image, and reports contained volume `RFMEDIA1` plus `3160 C64 BLOCKS`.
  Both exact USB1 and SD markers pass before, around, and after mount/dismount;
  both images are preserved; full Drive A JSON restores byte-for-byte.
- Preserve excluded oracle-development runs `...metadata-lowercase-1927`,
  `...lowercase2-1933`, `...lowercase3-1943`, and `...lowercase4-1953`.
  They stopped before complete evidence on a parse race or overly strict UI
  strings, restored Drive A, and made no filesystem change.
- Full build/host checks pass at resident `$B59A` (17 bytes below `$B5AC`),
  monolithic `$C429`, matcher `$AE3`, and 11 disjoint sidecars. The complete
  VICE wrapper regression is green after refreshing stale current-fixture
  counts, boot admission, full D71 sidecar seeding, and 18-line paging oracles.
  Cases 19, 33, and 34 are PROVEN; generated status is 58 proven / 2 partial /
  0 missing. Remaining partials are future-firmware SoftIEC map/unmap (55) and
  compatible-profile physical SD2IEC execution (56).

## 2026-08-17 — SD2IEC-compatible routing emulated and mkdir ACK fixed

- Command-path VICE `vice_auto_20260817_203654` first retains the real legacy
  profile/denial oracle, then writes only the four-byte ReadyFS IEC-8 profile
  cache record into the REU session bank. The UI reports
  `PROFILE: SD2IEC P1 F1 I1`, proving capability admission independently from
  the physical device classifier.
- The suite dispatches translated partition directory, mkdir, and D64 mount
  operations through resident IEC I/O. VICE's ordinary 1581 is not claimed as
  SD2IEC: directory and mount return explicit bounded failures. The wrapper
  compares SHA-256 before/after and proves the fixture D81 byte-identical.
- This exposed that partition mkdir discarded its canonical path before the
  single-action journal completion. `readyfs_driveui.c` now retains
  `source_root` for every action while still validating mkdir through
  `destination_root`; rejected commands can be ACKed and reported rather than
  producing `END ERR`. The current emulation reaches clean `CREATED` completion.
- Full `make readyfs`, UCI verifier, host checks, DMA/pipeline contracts, and
  the focused 100-step/38-assertion command-path plan pass. Layout remains
  resident `$B59A` (17 safe bytes), monolithic `$C429`, drive sidecar `$FF1`,
  and 11 disjoint sidecars. Generated UI status is 32/32 suites with 379
  assertions; cases remain 58 proven / 2 partial / 0 missing. Case 56 now
  lacks only successful real-SD2IEC execution; case 55 still needs firmware
  exposing SoftIEC `$20/$21`.

## 2026-08-17 — reverse SoftwareIEC tree source implemented; physical proof deferred

- Recursive source admission now routes both UltimateDOS and SoftwareIEC into
  the same cooperative tree ledger. SoftwareIEC directory traversal performs
  checked, component-wise `CD:` from partition root and then opens a plain `$`
  stream, preserving the existing relative-stem filter and recursive planner.
- Three physical diagnostics isolated successive defects without copying or
  deleting data: owned destination `rv204208` returned `SOURCE BAD`,
  `rv205834` planned zero entries, and `rv212140` waited because the new tree
  stream had parsed a SoftwareIEC partition but had not bound its IEC bus.
  The resident adapter now resolves `readyfs_uci_softiec_bus()` once and uses
  that value for both path commands and directory I/O.
- The corrected code passes `make readyfs`, the ReadyIRC-derived UCI protocol
  verifier, overlay/pipeline contracts, and focused recursive VICE run
  `vice_auto_20260817_224708`. Layout is resident `$B5A8` (three bytes before
  `$B5AC`) and monolithic `$C410`.
- Physical proof remains deferred. `rv214019` entered the real traversal but
  the harness polled screen DMA every second; reverse WhatIf now gets the same
  240-second quiet window as reverse copy. Subsequent fresh attempts were
  blocked before an owner-gated mutation by the current hardware launch state:
  REST `run_prg` returned 404, serial IEC no longer returned to BASIC, and a
  diagnostic chunked RAM launch reached `SEARCHING FOR RFMATCH` but stalled on
  its first IEC sidecar at 64 and 16 MHz. The RAM fallback was removed from the
  default harness. Preserve all `rv204208`, `rv205834`, `rv212140`, `rv214019`,
  `rv215603`, `rv220053`, `rv220538`, `rv221039`, `rv221734`, `rv222247`,
  `rv223343`, and `rv223506` artifacts; do not delete them.
- No successful reverse copy is claimed, and generated numbered status stays
  58 proven / 2 partial / 0 missing. Application UCI behavior remains the
  ReadyIRC-derived state machine with separate existing physical 1/16/64 MHz
  transport evidence; no CPU-delay pacing was introduced.

## 2026-08-18 — named sequential tape transfer complete in VICE

- Added `t:/NAME` KERNAL device-1 sequential read/write with explicit
  capability refusals for append/delete/move/rename/directories/trees.
- Disk-to-tape records `8:/RFVIEW` as 84-byte `RFCOPY`. Tape-to-disk consumes
  the cassette once, spools into REU, replays into a staged D64 file, verifies,
  promotes to `TAPOUT`, and compares identical.
- Fixed shared KERNAL status leakage (`$90`) at tape OPEN and IEC write
  boundaries, and fixed assembly replay EOF to jump unconditionally to
  success instead of falling through after `LDY/INY` changed Z.
- Recording `vice_auto_20260818_025149`, readback
  `vice_auto_20260818_025218`, post-tape IEC transition
  `vice_auto_20260818_025055`, and focused oracle
  `vice_auto_20260817_235139` all pass. Smoke/content/copy/recursive final
  regressions also pass, including recursive `vice_auto_20260818_025502`.
- Build: resident `$B5A3` (8 safe bytes), monolithic `$C4EB`, tape `$F47`;
  overlay, pipeline, host, build-report, and ReadyIRC-derived UCI contracts
  pass. UI inventory is 36/36 suites, 414 assertions; numbered status remains
  58 proven / 2 partial / 0 missing.
- Only disposable local VICE media was changed. No physical runner ran and no
  USB1/SD object was created, changed, or deleted. Continue to preserve the
  exact owned roots and every prior physical diagnostic; never delete outside
  those roots.

## 2026-08-17 — CMD/SD2IEC tree routing added and VICE-proven

- `tree` now admits partitioned IEC paths only through the existing cached
  drive-profile gate. Each logical directory queued by the cooperative tree
  controller is translated by the shared CMD/SD2IEC path sidecar, then the
  resident calls `dir_iec(..., tree=1)`; overlays still perform no IEC I/O.
- The drive-command workspace moved from `dest` to `source`, with canonical
  translator input in `temp.canonical`, so per-directory profile translation
  cannot overwrite the tree root or parsed destination state.
- Tree filters now cache `--include`/`--exclude` once per command and use one
  matcher-sidecar request per entry. `RF_MATCH_RAW_STEM` prevents UltimateDOS
  access-name decoding on IEC/SoftIEC names while preserving the existing
  Ultimate normalization and complete-relative-stem semantics.
- Focused VICE authority `vice_auto_20260817_230948` passes 103 steps and 39
  assertions. After emulating only the ReadyFS IEC-8 profile record as
  `SD2IEC P1 F1 I1`, `TREE 8.1:/` reaches translated resident IEC enumeration
  and reports `TREE FAILED F0 D0` on VICE's deliberately ordinary 1581. This
  proves admission/routing and bounded failure, not real SD2IEC enumeration.
  The screenshot is
  `logs/vice_auto_20260817_230948/stages/sd2iec_tree_dispatch_result/screen.png`;
  the wrapper also proves the D81 fixture byte-identical.
- Recursive regression `vice_auto_20260817_231116` passes 61 steps and 27
  assertions, including post-stop capability memory. Full `make readyfs`, host
  tests, overlay DMA, pipeline, and ReadyIRC-derived UCI contracts pass. Layout
  is resident `$B591` (26 bytes before `$B5AC`), monolithic `$C3E6`, matcher
  `$AF2`; generated UI status is 32/32 suites, 380 assertions, and unchanged
  58 proven / 2 partial / 0 missing.
- The shorter confirmation text is now `map softiec partition` / `unmap
  softiec partition`; authorization and firmware-honest behavior are
  unchanged. No physical runner was needed for the adapter proof; the separate
  reverse retry below changed no C64U filesystem object, and all prior
  diagnostics remain preserved.

## 2026-08-17 — reverse physical retry remained launch-blocked

- Fresh true Terminal-owned run
  `softwrite-noftp-reverse-tree-20260817-231700` targeted new preserve-only
  destination `rv231700` at 1 MHz. The C64U rejected the REST speed-setting
  sequence with HTTP 400/500 before owner admission, fixture mount, or any
  filesystem command. Runner and manual-restoration config snapshots both
  match the original SHA-256 exactly; manual restore reports `success`.
- Fresh 16 MHz run
  `softwrite-noftp-reverse-tree-20260817-231800` targeted distinct destination
  `rv231800`. Configuration admission and exact overlay-fixture mount passed,
  but all ten `runners:run_prg` attempts returned 404. The bounded fallback
  gave serial IEC an uninterrupted 240-second load window; afterward the
  keyboard buffer did not drain for `SYS2061`, so ReadyFS never reached owner
  checks or a command prompt.
- The 16 MHz safeguard restored full U64 config and Drive A exactly:
  original/restored/manual config hashes are identical, original/restored
  drive hashes are identical, and manual restore is `success`. `results.tsv`
  contains only its header and there are no command screens; neither new
  destination was created by ReadyFS and no filesystem object was changed or
  deleted.
- Preserve both diagnostic directories. Do not promote reverse physical
  coverage and do not alter the ReadyIRC-derived transport: the block remains
  C64U launch/config state before application UCI or owner-gated filesystem
  work.

## 2026-08-20 — standalone project migration and verification

- Moved the complete ReadyFS proof-of-concept boundary out of ReadyOS into
  `UltimateExperiments/ReadyFS`: 69 source files, the overlay linker config,
  133 build/automation support files, six design/safety documents, working
  notes, generated artifacts, and all identified ReadyFS evidence logs.
- Added the standalone `Makefile`, project `README.md`, local `AGENTS.md`, UCI
  contract verifier, and generated REL fixture builder. VICE runners now find
  the shared harness at `../../agenticdevharness` or `VICE_TASKS_REPO`; REL
  suites no longer copy a ReadyOS release disk.
- Forced the C64 compiler to `cl65` so Make's built-in `CC=cc` cannot select a
  host compiler. A forced `make -B readyfs` passed the ReadyIRC-derived UCI
  contract, all compiled host/self-tests, overlay DMA/pipeline checks, linker
  memory checks, and regenerated both monolithic and 12-sidecar disk builds.
- All 35 VICE plans compile from the new location. Fresh smoke
  `vice_auto_20260820_195205`, native REL gate `vice_auto_20260820_201127`,
  and REL rejection `vice_auto_20260820_201140` pass using artifacts built in
  this project. The UI report now has 33/33 successful latest retained plans,
  with 58 proven, two partial, and zero missing numbered cases.
- Terminal-owned physical run
  `ui-readonly-migration-20260820-ui-final2` launched the relocated
  `artifacts/readyfs/readyfs.prg` at 64 MHz. `probe uci`, `probe udos`, `probe
  softiec`, `probe recover`, and `dir u:/SD` all passed. The directory showed
  `/oneload` and `/READYFS.TEST`; no physical filesystem mutation was issued.
- Removed the ReadyFS-only Makefile, protocol-verifier, safety-note additions,
  source, scripts, docs, artifacts, and logs from ReadyOS while preserving all
  unrelated ReadyOS working-tree changes. Historical ReadyFS evidence was
  preserved, including residual logs under `logs/migrated-readyos-residual/`.

## 2026-10-08 — interactive UI and drawing optimization

- Full overlay app has a four-row wrapped 255-byte editor, continuation, editable
  32-command REU history with draft/cursor/mode restoration, and 800 physical
  output rows with screen/color REU paging (F1/F3, Commodore+Up/Down).
- Ordinary append/overwrite paints one cell; cursor movement paints no text;
  suffix edits are clipped to visible input. Legends and output pages avoid
  repeated full-screen drawing. Cursor-row arithmetic is reused.
- Sidecar 13 owns UI/command lookup; batch sidecar owns aliases. Numeric preview
  command IDs preserve short-name semantics, and nested ru scripts are rejected.
- PETSCII folding uses explicit numeric ASCII bounds in resident assembly.
  Utility and batch use the shared comparer in cc65 builds.
- Complete build passes: resident $B587 (36 safe bytes before $B5AC), UI $1000,
  monolithic $C2A0, stack $D000, disjoint REU regions. The monolithic diagnostic
  reader remains basic; use the overlay app for the full UI.
- Final physical evidence: `logs/readyfs_c64u/editor-20261008-154022`, overall
  success, 55 passing cases at 1/16/64 MHz, 900 lowercase batch commands with
  RC 0, output count 800, newest/oldest paging, draft/color restoration, and
  original CPU/empty-drive restoration. Artifact hashes match the final build.
- Focused VICE find/ring evidence: `logs/vice_auto_20261008_153922`; batch-policy
  evidence after comparer changes: `logs/vice_auto_20261008_153311`.
- User guide: `docs/READYFS_INTERACTIVE_UI.md`. Detailed grounding and debugging
  notes: `../agentworking/readyFS/UI_IMPLEMENTATION_2026-10-08.md`.
- This closes the current UI goal. Broader filesystem scope gaps documented in
  the historical grounding and scope audit remain separate work.
