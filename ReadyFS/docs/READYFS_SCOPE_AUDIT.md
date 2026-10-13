# ReadyFS Original-Scope Audit

Status: active implementation checklist. This is deliberately broader than
the 60-case UI matrix; a green matrix is not permission to call the original
application scope complete.

## Commands currently dispatched

| Area | Commands | Current state |
|---|---|---|
| discovery | `probe`, `drives`, `profile`, `native`, `capabilities` | endpoint capabilities and limits are dispatched; physical backend coverage incomplete |
| navigation | `pwd`, `cd`, `dir`/`ls`, `stat`, `volume`/`free` | flat IEC plus physically proven nested UltimateDOS/SoftwareIEC paths; lowercase Ultimate host/access, exact byte size, contained D81 volume identity, C64 blocks, and unavailable SoftIEC capacity are physically proven |
| shell | `help`, `history`, `status`, `clear`/`cls`, `alias`, `unalias`, `config`, `test`, `run` | implemented slices; `run` stages a bounded SEQ in a dedicated REU bank, closes the source, then cooperatively dispatches comments/commands with `onerror` and `expect rc`; prompts are forbidden in batch mode; status reports the stable typed result of the previous command while conversion of legacy handlers remains incomplete |
| matching | `match`, `--include`, `--exclude`, `--native-pattern` | component, relative-stem, and exact-name native plan behavior proven |
| content | `type`/`cat`, `head`, `tail`, `crc32`, `compare`/`verify` | resident-owned streaming I/O with slot-9 rendering; bounded line views, explicit tail truncation, and a backend-neutral CRC-32 stream checksum |
| nested discovery | `tree`, `find` | bounded breadth-first controller with resident UltimateDOS, SoftIEC, flat regular-IEC, and profile-gated CMD/SD2IEC adapters dispatched; `find` caches and applies positional or `--include`/`--exclude` patterns to complete relative stems; VICE proves CMD/SD2IEC root translation and resident handoff, while real nested device enumeration remains incomplete |
| mutation | `copy`/`cp`, `move`/`mv`, `rename`/`ren`, `delete`/`rm`, `new`, `write`, `append`, `mkdir`/`md`, `rmdir`/`rd` | flat/local slices proven; nested and cross-backend matrix incomplete |
| media | `mount`, `dismount`/`unmount`, `swap`, `format` | disposable IEC format plus physical Ultimate mount/swap/dismount and exact Drive A restoration are proven; SoftIEC map/unmap is future-firmware provisional because firmware 3.14 target 5 lacks `$20/$21`; the SD2IEC-compatible capability/routing path is VICE-emulated, but physical SD2IEC success remains incomplete |

Every current mutator recognizes `--dry-run` and exact alias `--whatif` at
admission. Native-pattern execution also requires `--apply` and consumes only
the frozen exact-name plan.

## Original commands not yet dispatched

None. Every command token in the original command contract is now routed. This
does not make the original application scope complete: the backend matrices and
typed-result gaps below remain substantive completion work.

## Functional gaps that are not just commands

- The common cooperative nested enumerator now feeds the existing
  plan/executor for UltimateDOS and SoftwareIEC. SoftwareIEC 3.14
  component-wise `CD:` command generation runs in utility slot 7, resident
  code checks every command-channel reply, and the global-root-to-`USB1`
  bridge is physically proven. Folder-capable CMD/SD2IEC paths now enter the
  same tree controller through the shared drive-profile/path translator, with
  resident IEC enumeration. VICE proves admission, translation, and bounded
  failure on its deliberately ordinary 1581; successful nested physical-device
  enumeration remains incomplete. SoftwareIEC mutation still uses
  ordinary checked OPEN/CLOSE rather than unproven `MD:`/`R:` commands.
- Flat IEC↔UltimateDOS copy is physically proven with a 4069-byte PRG, type
  preservation, independent length/CRC comparison, and exact Drive A
  restoration. Recursive UltimateDOS→SoftwareIEC folder copy is also
  physically proven for two flat files plus one nested file, including
  translated IEC names, independent byte comparison, marker gates, and exact
  Drive A restoration. Physical read-only
  `softwrite-noftp-whatif-filter-casefold-180400` also proves a nested
  `**/inside` filter selects exactly one leaf while all source/destination
  directory snapshots, source CRCs, owner markers, and Drive A remain exact.
  The reverse SoftwareIEC→UltimateDOS tree source is implemented and passes
  host/VICE contracts, including component-wise SoftwareIEC `CD:` and runtime
  IEC-bus binding, but current physical attempts were blocked by C64U
  program/sidecar launch stalls before a successful owner-gated copy. It is
  therefore not promoted as physical proof. Cross-backend recursive
  move/delete is also not complete.
- Image/volume metadata is now physically proven by
  `softwrite-noftp-metadata-lowercase5-20260817-2004`: `stat` reports the
  canonical display path, exact lowercase UltimateDOS access spelling,
  decoded lowercase host filename, type `$10`, and 819200 host bytes, while
  the mounted image independently reports volume `RFMEDIA1` and 3160 C64
  blocks. SoftwareIEC partition 0 reports target `$01` and `FREE UNAVAILABLE`
  rather than inventing host capacity. USB1/SD owner gates pass before,
  around, and after mount/dismount, and Drive A restores byte-for-byte.
- Physical Ultimate mount/dismount/swap and exact media restoration are
  proven by marker-gated `softwrite-noftp-media-145816`. Current official
  firmware 3.14 target-5 source has no `$20/$21` SoftIEC partition handlers.
  Physical attempts `softwrite-noftp-20260817-155612` and
  `softwrite-noftp-20260817-160912` therefore returned target status `$01`
  cleanly, added no partition, left partition 0 unchanged, restored Drive A
  exactly, and mutated no files. Map/unmap stays capability-honest provisional
  until supporting firmware/device exists. This is not a UCI transport fault:
  ReadyIRC-derived UCI abort/recovery is proven at 1/16/64 MHz.
- VICE `vice_auto_20260817_230948` emulates the ReadyFS cached SD2IEC
  capability record, not the device. It proves the transition from legacy
  denial to `SD2IEC P1 F1 I1`, translated partition directory/tree/mkdir/image
  dispatch, bounded non-SD2IEC device results, clean failed-action journaling,
  and a byte-identical D81 fixture. `TREE FAILED F0 D0` is routing evidence,
  not a claim that VICE's 1581 enumerated SD2IEC folders. Physical SD2IEC
  support stays provisional
  until a real device completes the same sequence successfully. Tape now has
  dedicated disposable-TAP evidence: named sequential write/read, disk-to-tape,
  REU-spooled tape-to-disk with staged verification, metadata, WhatIf, and
  explicit rejection of unsupported random-access/tree mutations all pass.
- `tail` currently retains the final 243 bytes in its 256-byte controller
  workspace. It reports `TAIL TRUNCATED` whenever older input was discarded;
  a future REU-backed ring can increase retention without changing the path or
  command scheme.
- `status` and batch `expect rc` now carry stable typed codes for the proven
  usage/not-found/conflict cases, with reserved interaction, unsupported, I/O,
  verify, partial, and internal values. Unsupported and unavailable outcomes
  now set 7 and 2 across the resident command surface. Conversion is still
  intentionally incomplete: several legacy I/O/verify/partial/internal paths
  leave the default result, and batch literals currently accept one digit only.

## Completion rule

The original scope is complete only when every item above is implemented and
evidenced, or explicitly retained as capability-honest provisional behavior
because the corresponding hardware is unavailable. The generated 60-case
report is one evidence view, not the scope boundary.
