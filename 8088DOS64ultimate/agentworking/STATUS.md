# Current state

Updated: 2026-10-15, America/Los_Angeles.

**Phase: implementation active toward the entire real DOS 3.3 emulator.** The final quick checkpoint passes **150 Zig/Peddle + 45 tooling tests**; the final full CPU checkpoint passes all **2,555 pinned hardware cases**. Genuine guest reset and unchanged boot-sector execution reach IO.SYS at **0070:0000**, with all **22,398 file bytes and 51 raw sectors** independently checked. Continuing IO.SYS reaches unsupported PIC **OUT 20h at 0070:2BFB after 2,335 completed instructions**. COMMAND.COM prompt acceptance remains false. Native startup still initializes then idles; actual Ultimate/IEC loading and a native runtime loop are not implemented.

Implementation and verified local commits are authorized; never push. Last accepted checkpoint before this integration is `c7450ff`. The final quick, full-corpus, profile and physical range gates passed. [Baseline evidence](evidence/storage-bootstrap-20261015.json) records source/tool/artifact identity and the actual scope; [kernel trace](evidence/dos-kernel-handoff-20261015.json) and [profile](evidence/cpu-profile-baseline-20261015.json) are retained separately.

## User decisions to preserve

- Build a real DOS 3.3 emulator for the 64 MHz C64U in this directory.
- Original **8088 / IBM PC XT** compatibility is the target; 8086 sources are references. Implement requirements regardless of what reusable cores provide.
- Target code should be **6502 assembly**, not ZeroPage-generated code. ZeroPage is the reference for the Peddle testing workflow.
- Retain **Zig tests that assert observable behavior of the actual assembled target**, like the existing compiler tests.
- 640 KiB guest RAM via REU paging, whole floppy images in REU, cached parts of hard disks around 2 MiB then 20 MiB.
- **4 MiB minimum REU**, larger optional; baseline budget fits guest RAM, two full floppy slots, HD cache, overlays, staging and traces.
- Keyboard, 40/80-column text and limited CGA; first application tests are applicable DOS tools on supplied images.
- Mock fast, exercise VICE/IEC/D81 as a second lane, and test on the physical C64U.
- All working records/scratch belong in this project's `agentworking`, not the enclosing repository folder.

## Completed planning work

- Inspected the supplied conversation, all three disk BPBs/root directories/configs, ZeroPage documentation/runner/shim, ReuSQL64 testing/storage integration, ReadyFS UCI rules/code, and .NET VICE harness usage.
- Researched primary instruction/BIOS references, hardware-generated tests, Ultimate firmware/docs, Soft-80 source, VICE, DOSBox-X, and timing-reference options.
- Wrote architecture, concrete RAM/REU allocation, memory ownership rules, storage persistence, display/input policy, test matrix, performance experiments, phased plan, requirements coverage and continuation records.
- Added a read-only disk-inventory research helper. It is not emulator code.
- Verified a disposable D81 can store disk 1 as a SEQ file and extract it byte-for-byte; this is container evidence, not emulator/IEC runtime acceptance.
- Planning validation passed: all 28 local links resolved, both address-space budgets are contiguous and complete, inventory repeats, originals retain their hashes, and ignore rules keep project context versionable while excluding scratch.

## Verified implementation slice: M0 foundation

- ca65/ld65 PRG and raw test payload, labels/maps, memory-contract checks and dependency/tool/artifact manifest.
- Vendored original Peddle core at its pinned upstream commit with license and per-file hashes.
- Zig tests exercise the linked reset routine and actual PRG startup; 10 tests cover state/ABI, error detection, runaway budget, stack imbalance, forbidden writes, unimplemented-device rejection, raw payload identity and exact CPU clocks.
- Four negative/positive linker-contract tests guard resident/entry placement.
- DOSBox-X boots a cloned supplied disk 1 with original CONFIG.SYS and an injected evidence AUTOEXEC. Guest VER reports **MS-DOS Version 3.30**; DIR and completion marker were read back from the guest floppy; original SHA-256 matches.
- Found and fixed clock integration: Peddle's embedding application must increment `clock` after each microcycle. The first runaway test exposed the missing clock advancement; exact LDA/RTS timing now guards it.

## Limits at the historical M0 checkpoint

At that checkpoint the target had an initial instruction subset but no full interpreter, BIOS, UCI/file backend or target DOS boot. Physical C64U timing and XT performance remain unmeasured. The reference DOSBox process was stopped after its guest output files closed; this is not a clean-storage-shutdown test. Original CONFIG diagnostics were not captured as screen text.

## Verified implementation slice: REU primitive

- Assembly immediate transfer primitive validates host/count/bank ranges, preserves Y/P and 6510 mapping, and reports completion/error. Descriptor accesses under KERNAL RAM occur with correct banking.
- Functional C64 banking subset and REU register model support used semantics, 4/8/16 MiB capacities and explicit unsupported-feature faults. DMA timing and complete CIA/VIC behavior are not modeled.
- `make test` passes **26 Zig/Peddle tests and 9 tooling tests** (four linker contracts, five acceptance-verifier checks). Shared probe verifies 4 KiB store/clear/reload against all expected bytes.
- Standalone probe passed VICE run `vice_auto_20261014_222223`. Independent verification matches captured executable to the current PRG and checks every returned byte. Compact record: [reu-vice-20261014.json](evidence/reu-vice-20261014.json). Harness used 16 MiB REU/warp, not a physical 4 MiB or 64 MHz validation.
- Runtime CODE 255, BSS 46, ZP 4; standalone probe CODE 416, BSS 46, ZP 6. See [memory ledger](MEMORY_BUDGET.md) and [contract](../docs/REU_IMPLEMENTATION.md).
- NES86 is a real 6502-assembly 8086 core with ca65/ld65, GPLv3, mapper-specific memory and ELKS/serial BIOS. It is a reference, not adopted code or a conformance oracle. Pinned findings: [existing emulators](../docs/EXISTING_EMULATORS.md).

## Verified implementation slice: addressing and coherent byte cache

- Segment/offset helper wraps at 20 bits and preserves input/register/flag contract. A 512-byte cache uses 32 frames in 8000–BFFF, a 2,048-entry direct map and bounded clock replacement, with forced 1/2-frame tests.
- Dirty write-back/load publication order, aliases, pins, PC holes/ROM/CGA and input rejection are tested against actual assembly; synthetic partial-transfer failures preserve authority and retry behavior.
- Latest `make test`: **41 Zig/Peddle + 10 tooling tests**, including all 2,048 physical pages, seeded oracle comparisons and shared cache probe. Warm test execution about four seconds.
- Cache probe passed VICE run `vice_auto_20261014_225535`; all 1,536 bytes and captured executable independently verified. [Evidence](evidence/cache-vice-20261014.json) and [API/limits](../docs/MEMORY_IMPLEMENTATION.md).
- Runtime CODE 1,109, BSS 62, map 2,048, frame metadata 192, ZP 16. Measured public warm byte read is 221 CPU cycles in ALL_RAM mode; this is a correctness baseline requiring fetch/hot-path optimization, not an XT-speed result.
- Physical read-only inventory succeeded at 10.0.0.79: C64 Ultimate firmware 3.14, FPGA 121, core 1.47, enabled 16 MB REU. Configured CPU speed 64 is controlled by C64U registers, so effective speed is not established. [Inventory](evidence/c64u-inventory-20261014.json). No physical probe program run; no machine/media settings changed.

The full-system memory allocation, final page size and performance thresholds remain proposals except user requirements. Disk 1's C:-specific config and disk 3's boot/OEM field still need observed diagnostics; do not silently repair originals.

## Continue from

[NEXT_SLICE](NEXT_SLICE.md), then [PLAN](../docs/PLAN.md), [TESTING](../docs/TESTING.md), [DECISIONS](DECISIONS.md). Implementation is authorized; preserve user clarifications and proceed in verified slices.

Existing unrelated ReadyFS edits and the large dirty sibling ZeroPage checkout were left unchanged. Root `agentworking` was not written. Project `.gitignore` overrides the parent's working-record ignore so these planning records can be versioned; scratch/runs remain ignored.

## Verified physical cache slice

- Native cache probe passed at manual 1/16/64 MHz settings on firmware 3.14. All 1,536 bytes and uploaded executable identity verified. Exact prior REU page envelope 07FC00–0803FF was backed up, restored and byte-compared; machine/turbo/media configuration matched before/after. [Evidence](evidence/c64u-cache-20261014.json), [procedure and limits](../docs/HARDWARE_TESTING.md).
- Latest fast checks: 42 Zig/Peddle + 15 tooling tests. Native backup/restore is tested across the bank seam; workflow tests cover cleanup on failure and firmware-padded speed options.
- First hardware run failed with HTTP 400 because `1` did not match the advertised ` 1` option. Recovery succeeded; corrected mapping and subsequent full matrix passed. No calibrated timing or DOS boot claim.

## Verified initial CPU execution slice

- Assembly step/init, immediate register MOV, AX exchanges/NOP, accumulator byte/word memory transfers, relative/far jumps, guest control flags and halt. Prefix streams yield in 64-prefix slices without an invented length exception. Unsupported instructions and host memory failures latch explicit diagnostics.
- `make test`: 55 Zig/Peddle + 15 tooling, including 41 hardware cases, approximately six seconds warm. `make test-cpu-corpus`: all 481 pinned SingleStepTests cases pass with register and complete 1 MiB RAM comparison, approximately 26 seconds. [CPU contract/limits](../docs/CPU_IMPLEMENTATION.md).
- Runtime CODE 2,019, RODATA 8, BSS 84, ZP 16, map 2,048, frame metadata 192; PRG 2,041 bytes. Probe binaries are isolated from the execution module and retain their physically tested identity.
- Word transfers use wrapping 16-bit offset then 20-bit translation per byte, following pinned original-8088 MartyPC implementation. Hardware projection covers FFFE, but contains no audited FFFF word case; that particular hardware corner remains open.
- No arithmetic/ModR/M/stack/string/I/O/interrupt execution, synthetic BIOS, target DOS boot or speed claim yet.


## Verified arithmetic, operand and stack slice — 2026-10-15

- 6502 ALU supports byte/word ADD/OR/ADC/SBB/AND/SUB/XOR/CMP/INC/DEC with eager guest flags, plus TEST. All 16-bit ModR/M forms, register/high-byte operands, general/segment MOV, LEA, LES/LDS, immediate groups and C6/C7 original extension aliases now execute.
- Stack words, register/segment PUSH/POP, PUSHF/POPF/SAHF/LAHF, direct near/far CALL and RET with cleanup preserve original SP ordering and reserved flags. Interrupt shadows are recorded; interrupt/trap delivery remains absent.
- **75/75 Zig/Peddle + 15/15 tooling pass**. Quick includes **338 hardware cases**, full **1,622**, all guest registers/defined flags and all 1 MiB RAM checked. Independent ALU 3,200 and address 720 case sets supplement hardware vectors. Measured commands: quick5.21 seconds, full 11.57 seconds, including build checks; host runner optimization accelerates feedback, not target execution.
- Real unchanged disk-1 sector completes16 instructions, then unsupported LODSB AC at 0000:7C51. IVT is zero in that fixture; no BIOS/DOS boot claim. Next: strings and conditional flow, then interrupt/BIOS/boot transport.
- Runtime CODE 4,394, RODATA 305, BSS 116, ZP 16; PRG 4,713. Hardware probe bytes still match prior VICE captures; no new physical run warranted by CPU-only changes. [Evidence](evidence/cpu-arithmetic-operands-stack-20261015.json), [contract/limits](../docs/CPU_IMPLEMENTATION.md), [ledger](MEMORY_BUDGET.md).
- Three user-authorized subagents owned stack, operand/corpus tests and runner improvements; parent integrated arithmetic/CPU, reviewed, verified and retained all context under this project. No pushes.


## Verified strings, control and software interrupt slice — 2026-10-15

- Implemented all 10 byte/word string forms with DF/segment rules and bounded 16-iteration REP continuation. Host yields preserve decoded state and count one completed instruction; asynchronous interrupt restart remains future work.
- Added all 32 Jcc encodings (including 60–6F original aliases), LOOPNE/LOOPE/LOOP/JCXZ, D0–D3 rotates/shifts with unmasked CL and original SETMO/SETMOC, INT3/INT/INTO/IRET normal guest routing.
- **95/95 Zig/Peddle + 15/15 tooling pass**; quick 502/full 2,278 hardware cases. Independent assertions include 1,024 branch flag combinations, 64 LOOP cases, 1,748 shift/rotate cases, 8 string tests and 4 interrupt tests. Full command 15.82 seconds. Hardware corpus's longest instruction uses 8 bounded host calls.
- Unchanged disk sector reaches real INT 13h disk reset; explicit guest IRET fixture returns to 7C70; first missing CPU instruction is CBW 98 at 7C75. No native BIOS/disk service, genuine target DOS boot or throughput claim. Next priority: CBW/CWD and multiply/divide, then BIOS ROM/IVT/BDA and coherent disk range support.
- Runtime CODE 6,094, RODATA 305, BSS 137, ZP 16; PRG 6,413. Standalone hardware probe images remain unchanged. [Evidence](evidence/cpu-strings-control-20261015.json), [API and remaining limitations](../docs/CPU_IMPLEMENTATION.md).


## In progress after c7450ff

Math/sign-extension/indirect execution now passes 114 Zig/Peddle +15 tooling and 2,555 full hardware cases (581quick); not yet committed. Real unchanged sector computes root LBA5/data LBA12 and requests CHS0/0/6 into0000:0500 before fixture stops at7D73. New coherent range copying with reserved C000–C0FF staging is being integrated; disk sector primitive, BIOS bootstrap/ROM gates and host image tools are parallel work. These new storage/BIOS paths are not yet accepted or physically verified. Preserve standalone probe identity and immutable inputs.

## CPU, BIOS and storage baseline — 2026-10-15

- Actual assembly adds CBW/CWD, general XCHG, accumulator TEST, FE INC/DEC, FF indirect CALL/JMP/PUSH including /7 alias, POP r/m16 and F6/F7 TEST/NOT/NEG/MUL/IMUL/DIV/IDIV. Math and indirect checkpoint: 114 Zig + 15 tooling quick; 2,555 full hardware cases. Original signed minimum quotient and REP IDIV/divide-return-IP policies retain pinned evidence and explicit source gaps.
- Coherent guest/REU ranges use a linker-enforced 256-byte staging buffer at C000–C0FF, <=256-byte chunks and explicit REU bank splits. Every guest byte uses the memory bus. Dirty import neighbors/export authority, PC ROM/hole/CGA policy, wrap, input rejection and partial failures/retry are checked. Additional resident code budget is now C100–CFFF, 3,840 bytes.
- Disk A defaults unloaded at REU 100000, 720×512 bytes, 40×2×9 geometry. Actual assembly reset/read/write/verify checks all 720 CHS positions, physical DMA boundaries, exact slot end and errors. Writes are volatile REU mutations; Ultimate/IEC persistence and floppy B/HD remain unfinished.
- Synthetic BIOS populates owned ROM/IVT/BDA through coherent writes. Only exact owned physical OUT opcode entries invoke native bootstrap/disk service; ordinary INT/IRET and mutable hooks remain intact. INT 11h/12h are ordinary guest ROM handlers reading dirty mutable BDA; INT 15h returns original XT AH=86h/CF=1. Wider BIOS/video/input/clock services are absent.
- Genuine boot integration seeds only the whole immutable floppy image into its owned REU slot. Reset→original sector→IO.SYS requires 392 completed guest instructions and 12,019,126 native step cycles excluding setup. All 51 raw sectors, including the bootloader's overread beyond the 44 rounded IO.SYS sectors, match the independent oracle. Source image and in-REU floppy remain unchanged. No host kernel/application loader or native INT 21h replacement exists. Current continuation stops at PIC OUT 20h, and the complete DOS prompt remains ahead.
- Native coherent range probe passed VICE run `logs/vice_auto_20261015_011028`: all 1,536 output bytes include dirty edits and match independently; captured executable matches. Previous four hardware PRG identities remain unchanged. New physical range probe passed Manual 64 MHz with independent exact restoration of 5,120 guest/source/destination bytes and prior machine/turbo/drive JSON equality. [Physical evidence](evidence/c64u-range-20261015.json).
- Final quick integration `build/storage-bootstrap-test.log`: 150 Zig/Peddle + 45 tooling pass, 12.45 seconds. Final full corpus `build/storage-bootstrap-corpus.log`: 150 Zig/Peddle, all 2,555 hardware cases, 23.70 seconds. Runtime map: CODE 9,702, RODATA 673, BSS 211, ZP 16; PRG 10,389 bytes. See [memory ledger](MEMORY_BUDGET.md) for actual boundaries and 45 BSS bytes remaining before E100. Unit helper changes do not change runtime bytes.
- `build/cpu-profile.json` contains 12 validated real-assembly cold/warm samples. Warm register/branch cost is 1,762.55 native cycles/instruction; 20 KiB REP is 1,081.19 cycles/copied byte, before DMA stalls and physical effects. This pre-optimization baseline does not establish XT speed. Unlinked fetch/PC-port/video work is future work, excluded from accepted functionality/performance.

Next acceptance is the full real DOS prompt followed by applicable command/application tests, 640 KiB RAM, 40/80 text and limited CGA, keyboard, native Ultimate/IEC media and 2 MiB→20 MiB file-backed HD persistence. Kernel entry does not reduce that scope. See [NEXT_SLICE](NEXT_SLICE.md) and the [BIOS](../docs/BIOS_IMPLEMENTATION.md), [disk](../docs/DISK_IMPLEMENTATION.md), [range](../docs/RANGE_IMPLEMENTATION.md) contracts.
