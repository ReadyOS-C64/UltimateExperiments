# Additive lessons log

## 2026-10-14 — planning inspection

1. User clarified target language to 6502 assembly and separately reinforced Zig behavior assertions. This supersedes the planning-stage C/ZeroPage possibilities before any target code was written.
2. Three images are all 360 KiB FAT12. Disk 1 and disk 3 have matching system-file hashes but different config/boot metadata. OEM text does not establish runtime DOS version.
3. Disk 1 refers to a non-existent initial C: installation; plan original-behavior and minimal-config boot lanes separately. Never edit the original to conceal a fixture dependency.
4. Existing Peddle shims provide a useful starting point but not a complete REU/banking/timing model. ReuSQL64 wraps REU addresses by capacity; ZeroPage truncates. Neither behavior can be generalized without device evidence.
5. Ultimate prose docs and inspected upstream code differ on REU transfer length masking. Actual transferred count and installed firmware must govern correctness.
6. A complete bitmap layout must satisfy VIC bank relationships and alignment, not just fit 64 KiB. The proposal places matrix 4000 and bitmap 6000 in bank 4000–7FFF.
7. Parent .gitignore ignores working-record directories recursively. Project-local override is necessary if these planning/continuation records are to be tracked, while scratch/runs stay ignored.
8. DOSBox-X was already installed. Version detection was performed; no guest run or emulator benchmark occurred in planning.
9. D81 SEQ roundtrip was verified using c1541. Its directory output can contain PETSCII bytes and must not be assumed UTF-8; this initially broke the research wrapper, not the container bytes.

## 2026-10-14 — M0 implementation

1. The first runaway fixture hung because Peddle `executeInstruction()` leaves `clock` advancement to the embedding application. Stopped that specific test process, changed the bridge to bounded per-microcycle stepping with explicit increments, and added an exact 8-cycle LDA/RTS assertion. All 10 Zig tests then passed.
2. DOSBox-X works with SDL dummy video/audio for automated reference boot. Copy AUTOEXEC into the disposable image before BOOT, then capture guest-written VER/DIR/DONE from the FAT12 image. The original config remained and the guest reported MS-DOS 3.30.
3. DOSBox-X did not exit promptly on SIGTERM in this run; the wrapper killed only its own process after a bounded wait. The captured files were already closed and verified; this is a functional boot baseline, not clean-shutdown evidence.

## 2026-10-14 — REU primitive and reference investigation

1. A descriptor at E000 cannot be read through KERNAL ROM. Establish RAM/I/O mapping before any request access; restore it after storing status/error. Tests invoke the routine with KERNAL initially visible.
2. Expanded REU increment wraps its low 19-bit REC counter with upper bank latches preserved. Split requests at 64 KiB banks and make higher-level range handling explicit.
3. First VICE attempt failed plan-schema validation because global retry_policy was missing. Adding that required field allowed the run; this was not a target probe failure.
4. A success mailbox is weak evidence alone. Compare every captured byte independently and associate results with captured executable bytes so an old run cannot validate new code.
5. The shared VICE harness selects 16 MiB REU. A successful low-address probe does not prove a 4 MiB configuration; the fast model covers 4/8/16 MiB separately. Physical capacity/firmware/timing remain outstanding.
6. Search hits often describe the opposite direction or independent desktop CPU emulators. NES86 is a verified 6502-hosted 8086 core; Appler runs 6502 emulation on an 8088. Record direction, CPU profile and license explicitly.

## 2026-10-14 — coherent memory implementation

1. A failed new-page load may have overwritten part of the victim's host buffer. Write back dirty data first, remove old ownership before loading, and publish the new tag only on success. On write-back failure retain the dirty old owner. Prefix-transfer fault tests exercise both orders.
2. The first test pass attempt had 38/39 passing; the flag test incorrectly expected 28 after masking P with 0C. The target returned the correct 08. Corrected the assertion, preserving the decimal/interrupt check. Target flag behavior did not require a fix.
3. Import zero-page assembly symbols with `.importzp`; a regular import produced a linker address-size warning and unnecessary absolute-address instructions. Fixed the interface before the successful full run.
4. Distinct pinned-page and replacement-page patterns matter. All-zero buffers could conceal accidental frame reuse even when a retained pointer still reads zero.
5. A direct page map consumes 2 KiB before descriptors. Current BSS/map/frame metadata total 2,302 bytes, leaving 1,794 bytes including alignment gaps for future storage/control needs.
6. Successful VICE eviction across a REC seam strengthens the mock evidence but does not measure physical stalls. Warm public byte reads already cost 221 host cycles, so future instruction fetch must exploit spans rather than call the full bus API for every byte indefinitely.
7. C64U physical discovery succeeded through a Terminal-owned read-only client. Firmware is 3.14; the speed field is 64 but register-controlled turbo means the field alone does not prove current speed. Preserve actual configuration and overwritten REU bytes before a test program.

## 2026-10-14 — physical recovery and firmware options

- Native backup/restore, independent REU re-read and configuration comparison made the failed first physical attempt recoverable. Keep these before/after checks for future hardware tests.
- Firmware speed options can contain leading spaces. `1` produced HTTP 400; ` 1` is the advertised valid value. Normalize only for matching, then send the original advertised string.
- A successful physical integrity matrix does not measure effective elapsed CPU/DMA throughput. Preserve that distinction in results.

## 2026-10-14 — first instruction execution

- Keep IP wrapping, segmented word-byte address calculation and physical 1 MiB wrap separate. Hardware data at FFFE does not prove a word beginning at FFFF; disclose evidence gaps.
- Long prefix streams need bounded host work without inventing a modern 15-byte guest limit. Preserve pending decode state and instruction counts across prefix yields.
- Full 1 MiB RAM comparisons caught the scope of each hardware case, including bytes expected to remain unchanged. Separate the six-second development lane from the 26-second broader corpus run.
- Isolate physical probes from the evolving execution module so CPU-only changes do not invalidate or require repeating unrelated hardware tests.

- A Zig 0.16 readFileAlloc limit equal to the file length produced StreamTooLong in the new boot fixture. Use bounded headroom and assert the expected image size separately.
- Keep full-RAM comparison coverage when improving host test speed; test the comparator's mismatch and bounds paths independently.


## 2026-10-15 — execution expansion

- Original-8088 hardware vectors include undocumented opcode-extension aliases. C7 first row uses /6; rejecting every extension except /0 caused a real conformance failure. Preserve evidence and implement the observed alias, rather than remove failing vectors.
- A decoded operand must survive later immediate fetch and eviction. Store its segment/offset, not a transient cache pointer.
- REU banking preserves DDR/output bits, not necessarily raw input-bit latches. A stack test expected raw $01=35 after DMA but saw F5; assert the established output-bit contract.
- Batching host instruction stepping helps, but compiling the host Peddle engine with optimization is the larger test acceleration. Verify exact target clocks, all memory/write markers, failure precedence and diagnostics before using the faster runner. This does not accelerate the C64 target.
- Explicitly set make's default goal when adding generated-file dependencies before the main target; otherwise a prerequisite can become the default build.


## 2026-10-15 — strings, branches, shifts and interrupts

- Original8088 /6 shifts are SETMO/SETMOC, not later SHL aliases. Follow original hardware vectors and metadata; original CL counts are unmasked. All new functional gates passed on their first execution.
- A host REP yield is not a guest interrupt: retain decoded prefixes/opcode across scheduling and count only a completed instruction. Original multiple-prefix interrupt restart requires separate event work.
- Compare an entire completed hardware string instruction, not one scheduling slice. Keep both per call and aggregate cycle/call budgets, and record maximum slices (currently 8).
- INT/IRET must use guest IVT/stack and preserve mutable hooks; capture a reference-derived IVT target before overlapping stack writes. Test a normal guest handler modifying saved flags, not only a native callback.
- A plain IRET fixture is useful CPU evidence but provides no BIOS disk service. Record real INT 13h entry and the subsequent missing CBW separately from target boot acceptance.
- Freeze owned files after signaling integration readiness; extra assertions arriving after a global run require explicit revalidation and consistent manifests. Three material subagents were coordinated with parent integration/review in this slice.


## 2026-10-15 — math, indirect control and genuine storage bootstrap

- Original-8088 math policy differs from later x86 at signed minimum quotient and divide saved IP. Keep zero-divisor, REP IDIV, minimum-quotient and PUSH SP alias rows pinned; no REP MUL/IMUL/unsigned DIV source rows exist at this corpus pin, so label independent coverage correctly.
- Capture indirect near/far targets before stack pushes when pointers and stack overlap. XCHG must preserve the original decoded EA while replacing a base register; POP memory must retain its decoded destination across stack reads/eviction.
- Coherent range import must merge through the guest bus so dirty neighboring bytes survive. Export must read dirty cache authority. Direct REU overwrite followed by cache flush would resurrect stale data.
- The range bounce added a genuine layout allocation: C000–C0FF. The memory gate caught a missing RANGEBUFFER reservation, forcing the complete host map and resident budget to account for it. The extra resident-code window is now C100–CFFF, 3,840 bytes.
- Adding a privately compiled, older object to a Makefile's link list did not trigger relinking when prerequisites omitted the Makefile. Fixed link prerequisites; verify maps and final binaries after changing the object set, not only build exit status.
- A host FAT12 oracle initially counted only the rounded IO.SYS file length (44 sectors); the actual unchanged bootloader reads 51. Preserve and compare the complete raw extent, all padding and overread, rather than changing the guest or relaxing checks.
- BIOS native callbacks must be physically whitelisted at the owned ROM opcode, not merely a port number or INT vector. Ordinary INT/IRET and PUSHF/CALL FAR chaining prove real guest hooks and saved carry behavior.
- INT 11h/12h queries read mutable BDA through normal guest code, including dirty resident bytes. INT 15h on the XT returns unsupported AH=86h/CF=1; pretending an AT configuration pointer exists would send this real kernel down the wrong branch.
- Physical range recovery must cover all three touched envelopes, 5,120 bytes total, not only the previous cache probe's guest 2 KiB. Six descriptors explicitly split bank seams; restore failure can write a prefix, so retry the whole owned snapshot and independently re-read it.
- Real reset→boot sector→IO.SYS handoff is accepted independently from continuation. The next missing PIC OUT 20h at 0070:2BFB is retained rather than faked. Kernel entry and a passing integration test do not establish a COMMAND.COM prompt or native startup/media loading.
- Real-assembly profiles establish a costly pre-optimization baseline (warm register/branch about 1,762 cycles/instruction; 20 KiB REP about 1,081 cycles/byte). Report caller/setup/validation/DMA/VIC/physical exclusions. Unlinked optimization files are not evidence of an optimized runtime.

- 2026-10-15: A fetch optimization must survive one-frame operand eviction and cold cache reset, not merely sequential reads. Compare the entire guest state after each instruction and full RAM at completion against the prior assembled path. Profile short-loop and large REP separately: faster fetch reduced the former substantially while large REP changed negligibly.


## 2026-10-15 — resident logical video and auxiliary BIOS integration

- Moving logical video code to DEVICECODE at 5000–5FFF preserves the 4000–4FFF screen/font and 6000–7FFF bitmap reservations. A contiguous PRG needs MAIN padding and explicit 4000–4FFF startup zeros to reach that code; those bytes must not be reported as linked executable allocations. Standalone hardware configurations/binaries remain separate.
- New mutable scratch belongs in the bounded EA00–EEFF DEVICESTATE allocation rather than overflowing scarce E000 pre-map BSS. Keep CACHEMETA bounded to E900–E9FF and reserve EF00–EFFF; count the conditional future C100–C8FF UCI buffer before promising C000-window code headroom.
- The first combined quick gate exposed two test-fixture mistakes, not target failures: the old unsupported-opcode sentinel D6 is now valid SALC, so the test uses unsupported input port FE instead; a new BIOS gate loop wrote REU backing behind a live dirty cache, so its guest code writes now use the coherent memory API.
- Original XT zero serial/printer base checks precede AH dispatch and preserve AX. A missing device is not a timeout; retain unchecked wrapping DX indexing and fail explicitly for a present-device contract that is unimplemented.
- Logical video mode/page/cursor/scroll/pixel/teletype tests prove BDA/VRAM behavior. They do not prove host fonts, rendering, keyboard input, retrace timing or physical readability. Native POST initializes mode 3 coherently while preserving guest AX.
- Original adjust hardware corrected an AAM-zero flag expectation before acceptance: SZP reflects zero while AX stays unchanged and INT 0 saves the post-immediate IP. Keep undefined-flag masking scoped to actual hardware metadata and disclose source gaps for REP AAM/AAD.


## 2026-10-15 — genuine DOS prompt, VER and DIR

- A later SYSINIT port stop at 9DFD:0A53 was legitimate original relocated code. Binary span/relocation audit plus Microsoft inherited DOS 3.30 comments identified arbitrary-byte GLOBAL REARM writes at 02F2h–02F7h. Preserve narrow absent-board behavior, not blanket unknown-port success.
- The private fast/slow fetch comparison matched every state for 55,583 calls and all coherent conventional/CGA RAM. That rules out regression against the prior fetch path, without claiming universal CPU correctness.
- Original clock AH behavior includes decrementing all nonzero functions, unnormalized sets, full overflow-byte read/clear and equality-only midnight. Native elapsed time and asynchronous ticks are distinct integrations.
- Original keyboard AH=01 loads AX even when empty and exposes exact RET2/CMP flags. Empty AH=00 must retain its guest frame and retry the exact owned OUT without counting completion; key enqueue and host input scanning are separate.
- Separate the short default kernel-handoff test from opt-in interactive DOS acceptance. Ten keys through actual assembly drove the original date/time prompts, VER and DIR; exact names/sizes/count/free bytes plus a returned prompt make a stronger milestone than seeing a substring once.
- The first real COMMAND prompt is at 193,673 instructions; complete VER/DIR/return acceptance takes 588,937. Do not relabel early IO.SYS entry or intermediate screens as the full built-ins proof. Keep CPU-step/support/setup clocks separate from physical elapsed time.
- Generic UCI DONE only completes transport. Streaming/backpressure, saturated FPGA queue limits, stale-state abort and elapsed recovery are required before the separate image-file operation/status/persistence layer can be accepted.
- A CIA counter's unit is phi2, independent from turbo CPU instruction cycles by design but still requiring physical evidence. Destructive timer/NMI ownership cannot be reconstructed from readback; reset/resume is not prior program/timer-state restoration.

- The first physical CIA/VIC clock attempt failed at Manual 1 MHz with error 3 while configuration restoration/reset-resume succeeded. Preserve the failure and fix capture-before-reset diagnosis; functional model/probe success cannot stand in for clock-domain calibration. No 16/64 MHz or timing result follows from a matrix that stops at its first speed.
- Working-tree tooling includes five tests for an unlinked future overlay package. Count the accepted 69-test commit scope separately from the 74-test working set; passing package tooling does not mean a resident overlay runtime is linked.

- Pre-commit clock diagnostic correction: capture full RAM/mailbox/40-byte DCK1 before cleanup resets the evidence. The first error-3 subreason remains unknown. The updated probe's 16-PAL-line endpoint window permits ±1,008 raw ticks, independently checked; six Peddle tests/15 tooling checks do not imply a physical pass. Three added diagnostic cases raise selected feature tooling from 69 to 72 and the working set from 74 to 77 (five unlinked overlay-package tests remain excluded).

- Corrected physical matrix passed all three speeds within independently derived 16-line bounds. This validates raw CIA/raster domain and observed turbo independence, while native deadline conversion and throughput remain separate work. The new 1 MHz 8/8 endpoint observation is a plausible explanation for the first narrow-window failure, not proof of its missing old subreason.

## 2026-10-15 — overlay and dispatch integration

- Measure a real DOS workload before changing dispatch. Preserving the opcode accumulator at family entry is part of the internal ABI; the original unchanged kernel oracle caught the omitted reload in the private prototype. Full hardware cases and complete screen/register/RAM equality then accepted the integrated change.
- Separate linked variant totals, maximum simultaneous overlay bytes, resident file bytes, startup assets and zero padding. Summing two mutually exclusive payloads as permanently resident would misstate the available host RAM.
- Save/restore observable 6510 DDR/output bits. Input-configured port bits are not readable copies of the output latch; exact hidden-latch assertions can reject correct hardware behavior.
- Source freeze plus independent artifact hashes lets full corpus, genuine DOS and profiles run concurrently without racing build mutations. Host wall time from that concurrency is not target throughput.
