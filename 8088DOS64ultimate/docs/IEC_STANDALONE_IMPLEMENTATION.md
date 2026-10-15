# Standalone IEC / D81 development helper

This explicit opt-in helper imports a PC floppy from a CBM SEQ file in an owned D81. It is separate from the emulator's default build and runtime. It does not implement a production IEC FILE profile, start DOS, replace INT21, save media or contact a physical C64U.

`make iec-standalone` builds full and small helpers. `make test-iec-standalone` executes actual linked 6502 assembly in Peddle and the isolated tooling checks. `make vice-iec-standalone` explicitly launches an owned local VICE instance for the original 360 KiB image with serial traps. `make vice-iec-standalone-serial` runs a deterministic 512-byte fixture through a true-drive 1581 with traps disabled. None of these targets is a dependency of `all`, normal `test`, or the native runtime. The standalone program starts only when explicitly loaded/run; it has no D64N startup configuration and must never be registered as the native DOS runtime.

For individual VICE error cases, use `python3 build_support/vice_iec_standalone.py --case short|long|crc|missing`; add `--serial` for the small true-drive fixture. The normal image path is the supplied disk 1 under `reference/`; its SHA-256 must be `bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb`. Inputs are read-only, derived files and D81s are fresh under `agentworking/runs/`, and all build artifacts go under `build/`. No original image or unrelated process is an output or cleanup target.

## Exact source and binary cohort

The full PRG is 1049 bytes, loading 0801–0C17, SHA-256 `4a2308ff3c6a369ed5f7cd7da03d91f429fcc20c716b450f38add97cc2863ba4`. The small PRG is also 1049 bytes, SHA-256 `37e044cd94d71300297fbea4afd75762d31f40df8af87af84b8bba1c738d3cb5`. Both reproduce the independently reviewed fixed standalone binaries byte-for-byte. The only new source parameterization selects the previously reviewed length/CRC constants for the 512-byte variant; default emitted code is unchanged.

The reviewed fix defers loaded publication until all final guards pass, clears loaded on every failure, and best-effort closes LFN15 then LFN2 after close/status failure while retaining the primary error. This cleanup does not establish physical drive closure or recovery after a stuck handshake. Native known-closed remains false on that path.

The explicit Make target validates every product on each invocation and rebuilds when a PRG, map, label file or stamp is absent/stale. A retained JSON stamp cannot hide a missing output. Valid complete products retain their modification times. Build manifests pin assembler/linker binaries and versions, every direct assembly/include/configuration input, PRGs, labels and maps. `check_build` rejects stale sources or output metadata before launch/verification. No ROM is bundled or redistributed. VICE uses the user's installed ROMs; Peddle substitutes only the explicitly documented external KERNAL API entrypoints.

## Target operations and memory

The real target performs SETNAM/SETLFS/OPEN/CHKIN/CHRIN/READST/CLOSE/CLRCHN, computes CRC32, validates exact final-byte EOI, and executes the existing shared REU primitive for each 512-byte chunk. All original 368640 bytes must arrive, CRC must be 30770A37, LFN2 must close with zero serial status, drive status must be `00`, and LFN15 must close before loaded can become true. There is no extra read after EOI. Oversized input is rejected at the permitted count before another read/final DMA; incomplete input never publishes loaded media.

| Allocation | Measured use |
|---|---|
| CODE | 1020 bytes: helper 838 + identical shared REU 182 |
| BASIC / RODATA / initialized guard | 12 / 14 / 1 bytes |
| BSS | 56 bytes at 2000–2037 |
| REU scratch zero page | FB–FE, four bytes |
| Stream buffer | C000–C1FF, guards BFFF/C200 |
| Standalone mailbox | 6000–601F |
| Whole floppy | REU 100000–159FFF |
| F000 host-extension guard | all 3584 bytes F000–FDFF |

These are standalone allocations. They do not establish fit in the production runtime or permit reusing the mailbox after bitmap/cold memory takeover. The helper owns a freshly booted test machine, masks/acknowledges CIA and VIC interrupt sources, installs complete RAM IRQ/NMI RTI vectors before any RAM35 mapping, and uses ROM37 for KERNAL calls. The shared DMA primitive maps RAM35 with interrupts disabled and restores the previous mapping. KERNAL serial routines can enable IRQs; SEI at entry alone is not an ownership guarantee.

## Actual Peddle tests and their limits

Three Zig tests cover 13 scenarios: original/short/long/CRC at 512 bytes; missing/open/select/read failures; status and CLOSE failures; a late buffer-guard failure; an 11-byte partial DMA failure; and a complete original 360 KiB import crossing every REU bank seam. Every scenario compares all 4 MiB against an independent expected transfer prefix and guard pattern, all executable bytes except the initialized guard, host F000 shadow, adjacent buffer guards, vectors, stack balance, LFNs, counters and publication/error state. Tests enforce a 600-million-cycle execution budget and explicit unsupported-device failures.

The model replaces only KERNAL API entrypoints, with actual RTS instructions returning through Peddle. It models LFNs, sticky serial status, final-byte EOI, read-only source bytes, status-channel text, close errors and IRQ-enable side effects. It does **not** emulate ROM instructions, IEC bit timing, timers, physical DMA stalls or a drive CPU. Reported cycles are assembly plus model-entry RTS costs, not ROM/IEC timing or an XT comparison. Synthetic tooling captures test rejection policy only and are never target-execution evidence.

## VICE verification and retained evidence

The separate `BinaryMonitor` helper validates framed replies, IDs/types, bank discovery and resource decoding over localhost only. Before the first command, `ChildMonitorOwner` requires OS lsof evidence that the accepted ESTABLISHED TCP connection has the exact reverse server/client four-tuple and belongs to the fresh live child PID. The same check runs before every command, including reads, resume and cleanup quit. An unrelated live child or matching listener port alone is insufficient. Missing lsof, inspection failure, child exit, mismatch or loss of ownership fails closed; the launcher closes its local socket and may terminate only its own child without sending quit to an unproved monitor. The port reservation race can cause a rejected connection; it cannot authorize controlling a foreign monitor. This host lane currently requires Unix/macOS lsof and IPv4 loopback. The runner selects PAL, a real 4 MiB patterned REU, owned D81, 1581 drive, PRG injection, and the appropriate true-drive/trap settings. Injection preserves the mounted D81. The command-line `-warp` override is separate from VICE's InitialWarpMode resource; that resource may read zero even with the explicit command-line override. Do not interpret it as an observed current speed.

The pure independent verifier checks known executable identity, full RAM and REU lengths, actual mailbox/full-RAM agreement, all source/payload hashes, native counts/error/loaded/EOI/closure, complete imported bytes and outside guards, F000 shadow, original image identity, D81 identity and actual VICE resource observations. A success mailbox alone is insufficient. The preserved independent review contains 12 actual VICE cases / 193 checks: four full-size trap cases plus missing-file, five small true-drive cases, and two separately injected-fault binaries. Exact reproduced binaries permit reusing those runs. The original private packaging reused VICE evidence and did not run a physical machine. Root subsequently ran the repaired launcher against a fresh owned VICE instance, as recorded below. Its new verifier independently rechecks the 10 normal full/small captures; injected binaries remain separately pinned review evidence.

## Remaining integration limits

KERNAL serial contains busy-wait loops without a universal caller deadline. The external VICE watchdog bounds a development run; it does not make CHRIN a bounded asynchronous FILE poll or prove native bus recovery. A first production IEC profile must remain explicitly cold/modal, isolate KERNAL scratch and ROM37 from E000/F000 resident state, respect overlay/cold lifetimes, then return to ordinary unchanged guest reset and DOS boot. Runtime file service, persistence/reopen/readback, interactive RESTORE, existing-session restoration and physical IEC at controlled 1 MHz remain separate gates. Never assume 64 MHz IEC bit-banging works.

A 360 KiB floppy uses 1452 D81 blocks. A later verified export should use a separate fresh owned output D81. A 2 MiB or 20 MiB HD image cannot fit in a D81; this helper makes no HD claim.

## Packaging repair verification

The two independent packaging review findings are repaired in a separate additive cohort. Seven new regression tests cover PID/state/four-tuple matching, a live-child port collision with zero command bytes, refusal to quit after ownership is lost, actual localhost accepted-socket ownership/foreign-PID rejection, and real isolated Make recovery after deleting each of all seven generated products. The complete tooling lane passes 29 tests (the prior 22 plus seven new). An incomplete JSON stamp is also rebuilt; complete valid products are not regenerated. No VICE or hardware run is claimed for these repairs. The target assembly and Peddle test sources are unchanged; previous real target evidence retains its original scope.


## Root production verification

Root promoted16 exact additive files plus minimal Make/Zig registration. `make test-iec-standalone` passes3Zig tests/13actualassembly scenarios and29tooling tests. All25dependencies and337predecessor files match; both main emulator PRGs remain22f82091/8a84329c.

Fresh `make vice-iec-standalone` passes the complete360KiB original case in16.549seconds with owned childPID/acceptedESTABLISHED four-tuple proof. All720DMA chunks, complete4MiB expected image/guards, executable/F000 guards, CRC and knownclosure pass. This is a standalone PAL/warp/traps development run, not production DOS-over-IEC, physical64MHz serial or persistence acceptance. [Evidence](../agentworking/evidence/iec-standalone-20261015.json).
