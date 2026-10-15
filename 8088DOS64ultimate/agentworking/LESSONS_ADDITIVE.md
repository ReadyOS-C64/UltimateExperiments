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
