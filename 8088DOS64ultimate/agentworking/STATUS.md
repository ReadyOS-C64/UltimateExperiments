# Current state

Updated: 2026-10-14, America/Los_Angeles.

**Phase: implementation active.** User authorized implementing the plan, progressively verifying, and making local commits without pushing. Planning baseline committed as `67b6954`.

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

The target still has no guest interpreter, BIOS, UCI/file backend or target DOS boot. Physical C64U integrity/timing and XT performance remain unmeasured. The reference DOSBox process was stopped after its guest output files closed; this is not a clean-storage-shutdown test. Original CONFIG diagnostics were not captured as screen text.

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
