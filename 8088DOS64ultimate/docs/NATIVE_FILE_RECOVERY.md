# Opt-in native whole-file REU recovery

This development backend restores the complete first4MiB of an enabled REU from an immutable verified backup through one native read-only UCI file stream. The ordinary DeltaService remains the default. The native helper and host integration have been independently reviewed; physical whole-file throughput and recovery remain unvalidated. REST/FTP are development control and evidence paths, not guest/runtime networking.

Build from a clean checkout with `make native-file-recovery`. The standard-library Python builder and ca65/ld65 compile tracked native_file_restore_boot.s/native_file_restore.s with shared REU, UCI, FILES, host_clock and elapsed sources. FILES exports an owned-target alias without emitting extra bytes. There are no code overlays. It produces:

- build/dos64-native-file-restore.prg,4624bytes,disabled config, SHA25638806976236c39df7b392b8dbf5312adb92c4ac4f9ac60460f664a3eb61e905b.
- build/dos64-bulk-reu-service.prg,592bytes, SHA25640fe690953c245c8093c7cd5e5cb91684df7290602d8afa44dbd2e0b5b30d09e.
- Adjacent labels/maps and build/dos64-native-file-recovery.json with exact source/output identities and resolved ca65/ld65 paths, version output and compiler binary SHA256 values.

The builder rejects different output bytes. Updating shared helper semantics or assembler output requires new review, pins and relevant tests; do not bypass the digest check. No binary-only tracked recovery artifact or ignored scratch input is required.

## Host selection

`build_support/c64u_native_file_runner.py --recovery native-file` is an explicit separate CLI; no change is made to c64u_native_ftp_put_runner.py or its default delta backend. It imports the current shared Application/support, preserving genuine DOS behavior, AH01 observation, cursor-local/required pagination and UCI code identity checks. Application mode accepts the existing --prg, --labels, --map, --build-manifest, --media-manifest, --source and --expected-prg-sha256 inputs.

`--recovery-only` restores an existing read-only --backup/--backup-manifest without running an application, and requires --registered-native-prg plus --native-diag-address for the independently verified original two-PRG registry. Both modes require --host, --output, --service, --staging-manifest and --pal-clock-evidence. The default restore base is the generated build/dos64-native-file-restore.prg. `--validate-only` reads local identities/inputs and constructs the strict registry without FTP/REST contact or creating the output directory. Physical launch remains a reviewed Terminal operation with fresh owned output.

Each restoration attempt re-verifies the read-only local backup against its complete manifest and held immutable4MiB bytes. It creates a new /usb1/DOS64_TEST/reu-native-UUID-pN directory and only OWNER.JSON, BACKUP.REU and REU-FILE-RESTORE.PRG. Marker and both files get complete exact byte/length/SHA readback. Existing directories and ambiguous failures are rejected; no delete, rename, mount, Temp cleanup, source overwrite or unknown-data fallback exists. Failed owned files remain available for evidence.

The third PRG is reconstructed only from the exact reviewed disabled base. Only DRF config enable/pathLen/CRC/path changes are accepted. Registration binds the complete configured bytes to the verified backup SHA/CRC and new owned path, refuses directory reuse, and consumes launch capability before its potentially ambiguous request. The original two known PRG registrations remain unchanged.

## Bounds and lifecycle

A single absolute600-second acceptance budget spans native preflight, allowed Manual64 selection, FTP staging/readback, native execution, original DRS1 reload and the complete4MiB service comparison. It is never reset between those steps. The existing outer pre-attempt service load retains its separate12-second bound. Actual socket waits are clamped to min(5seconds, remaining phase) for REST and min(20seconds, remaining phase) for FTP. Successful calls and transfer callbacks check the same deadline. This is an acceptance deadline, not an asynchronous interruption guarantee: a blocking network/OS call can return late and is then rejected. Failure capture/outer cleanup retain their independent bounded requests.

Preflight requires current enabled Command Interface, REU>=4MiB, System Mode=PAL and reviewed prior successful64MHz PAL CIA/VIC clock evidence. Native real I/O validates DF1C identity before control writes; REST readmem is not treated as I/O. Only the already-permitted Turbo Control and CPU Speed keys can change, using Manual and the exact firmware64 option. Current PAL/Manual64 is verified; unchanged outer finally restores full original turbo/machine/media configuration and attempts reset/resume independently. C64 machine/REU/interface settings are never silently changed.

The preceding helper is paused; all32 DRF mailbox bytes are cleared and read back before file RUN. Fresh native initialization/busy must be observed before DONE. Missing startup fails after12seconds, E1 immediately. Full captured C64 RAM verifies every configured resident PRG byte except four known UCI pointer operands. Startup accepts only legitimate low/high publication seams; terminal pointers must be exactly final CLOSE command C101 and last512-byte READ C67F. All fixed DF1C operands and other code/config bytes remain exact.

A5 requires phase6, zero errors/cleanup, handle0, all8192sectors, matching expected/final CRC and native elapsed below its hard limit. Full DONE RAM is saved before the original service is loaded. The original DRS1 service must establish fresh READY/sequence0 and exact code, then compare every one of256 16KiB chunks, checking lengths before differences and final digest. Local source verification remains under the budget. Native CRC alone never establishes restoration.

Native failure, identity rejection or timeout saves full C64 RAM/mailbox diagnostics before any subsequent service overwrite. Failed capture cannot mask the original error or skip outer capture/cleanup. At most two whole attempts use fresh independently verified stages; no partial/payload retry occurs. Application failure stays failed even when recovery succeeds. Late source hashing/evidence failure cannot replace an earlier error or skip cleanup. Backups, journals, failure RAM and owned remote files remain recoverable.

## Native ABI and limits

Standalone code0801..1A0E; config1985,size138; ZP20..25; staging8000..87FF; UCI C100..C8FF; descriptorE000..E009; stateEA00..EA78; mailbox6000..601F. Config: DRF1[0..3],enableA5[4],NUL-inclusive pathLen2..128[5],CRC32LE[6..9],ASCII path[10..137]. Shipped config is disabled. Mailbox: magic0..3,state4 (1init/2busy/A5done/E1fail),engineerror5,clockstatus6,phase7,handle8,cleanup9,fileserrorA,UCIerrorB,expectedCRC10..13,actualCRC14..17,elapsed32LE18..1B,sectorsLE1C..1D.

Entry keeps KERNAL mapped until the full owned RTI NMI vector and CIA2 mask/drain are installed, then selects RAM+I/O and claims the existing CIA2 clock. Initial unknown single-file ownership requires explicit CLOSE before read-only OPEN; uncertain closure remains handle2/cleanup error. Four512-byte READ/CRC groups precede each aligned2048-byte DMA. Exactly2048 bank-contained DMAs cover000000..3FFFFF. Short groups are never DMAed. Complete4MiB, zero-byte EOF probe, matching CRC and accepted final known CLOSE precede A5.

Native elapsed accumulates modulo16 samples into32bits in4096-PAL-phi2-tick units. Operation cutoff141918 is589.999805 nominal seconds; hard cleanup cutoff144323 is599.998181. Poll gaps must be below32768units; independent host deadline remains necessary for a frozen clock.

Only first4MiB is snapshotted/restored; upper REU protection follows unchanged native bounds and the original modeled full upper12MiB equality test, not new physical equality evidence. Prior CPU/timer/NMI execution is not restored. Accepted firmware CLOSE does not prove underlying filesystem durability; native backup access is read-only. CRC detects accidental corruption and is not authentication. See tests/native_file_recovery/README.md and PROVENANCE.json for the retained7actualPeddle/27mock proofs, complete license/provenance and explicit opt-in test commands.
