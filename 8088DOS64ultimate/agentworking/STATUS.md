# Current state

Updated: 2026-10-14, America/Los_Angeles.

**Phase: implementation active.** User authorized implementing the plan, progressively verifying, and making local commits without pushing. Planning baseline committed as `67b6954`.

## User decisions to preserve

- Build a real DOS 3.3 emulator for the 64 MHz C64U in this directory.
- Target code should be **6502 assembly**, not ZeroPage-generated code. ZeroPage is the reference for the Peddle testing workflow.
- Retain **Zig tests that assert observable behavior of the actual assembled target**, like the existing compiler tests.
- 640 KiB guest RAM via REU paging, whole floppy images in REU, cached parts of hard disks around 2 MiB then 20 MiB.
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

The target PRG initializes state and a mailbox only. No guest instruction interpreter, BIOS, REU/UCI model/driver, target DOS boot, VICE runtime, performance benchmark, or physical-device test exists yet. The foundation bus is ordinary host RAM with explicit rejection of REU/UCI access; C64 ROM banking and DMA timing are not yet modeled. The reference DOSBox process was stopped after its guest output files closed; this is not a clean-storage-shutdown test. Original CONFIG diagnostics were not captured as screen text.

All memory sizes, page/cache policies, assembler choice, and performance thresholds are proposals unless marked as user requirements in DECISIONS. Disk 1's C:-specific config and disk 3's different boot/OEM field need observed reference behavior; do not silently repair originals.

## Continue from

[NEXT_SLICE](NEXT_SLICE.md), then [PLAN](../docs/PLAN.md), [TESTING](../docs/TESTING.md), [DECISIONS](DECISIONS.md). Record the user's review changes before starting M0.

Existing unrelated ReadyFS edits and the large dirty sibling ZeroPage checkout were left unchanged. Root `agentworking` was not written. Project `.gitignore` overrides the parent's working-record ignore so these planning records can be versioned; scratch/runs remain ignored.
