# Current state

Updated: 2026-10-15, America/Los_Angeles.

**Phase: implementation active. Current quick checks: 75 Zig/Peddle + 15 tooling; all 1,622 pinned CPU cases have also passed.** User authorized implementing the plan, progressively verifying, and making local commits without pushing. Planning baseline committed as `67b6954`.

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

## What is not established

The target has an initial instruction subset but no full interpreter, BIOS, UCI/file backend or target DOS boot. Physical C64U timing and XT performance remain unmeasured. The reference DOSBox process was stopped after its guest output files closed; this is not a clean-storage-shutdown test. Original CONFIG diagnostics were not captured as screen text.

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
