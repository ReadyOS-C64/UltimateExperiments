# Project working instructions

Scope is this directory. Read README.md, agentworking/STATUS.md, agentworking/NEXT_SLICE.md, and agentworking/DECISIONS.md before continuing.

## Phase and implementation

- Implementation is authorized (2026-10-14): progressively verify and make local commits; do not push to GitHub.
- User decisions: target 6502/6510 assembly; Zig host assertions around the actual assembly in Peddle; ZeroPage is a testing reference, not the target compiler.
- Original 8088 / IBM PC XT behavior is the compatibility target. REU minimum is 4 MiB; larger capacities are optional. Existing emulator references do not limit requirements or substitute for independent tests.
- User direction (2026-10-16): use additional REU when conserving it would slow the emulator. Keep the 4 MiB baseline and explicit capacity/ownership bounds; see docs/REU_ALLOCATION_POLICY.md. Native C SETUP is authorized; the emulator remains 6502/6510 assembly.
- Use ca65/ld65 provisionally. Record any assembler change. Do not quietly substitute a C or ZeroPage target implementation.
- Boot genuine DOS 3.3 from the supplied disk images. Do not replace DOS INT 21h or implement a separate native EXE/COM loader as a shortcut to the boot milestone.
- Build in small vertical slices with behavior tests. Treat all proposed commands in the plan as unimplemented until added and run.
- Work only on this project unless a separate change is necessary and explicitly recorded. Nearby projects and their dirty files are reference material, not cleanup targets.

## Evidence and continuity

- Keep all scratch, downloads, runs, and context in this project's `agentworking/`; keep build products in `build/`.
- Update STATUS.md and NEXT_SLICE.md after each verified slice, including incomplete work and first failure.
- Append exact commands, versions, result paths, and limitations to TEST_LOG.md. Never call a test passed because its expected output was written down.
- Add durable decisions and supersessions to DECISIONS.md; update RISKS.md as measurements resolve uncertainty.
- Append lessons to LESSONS_ADDITIVE.md. Keep LESSONS.md as concise current guidance.
- Update MEMORY_BUDGET.md with actual linker evidence after every layout change. Proposed ranges are budgets, not measured usage.
- Pin source/binary hashes, test seeds, fixture hashes, firmware, and machine configuration in each run manifest. The sibling compiler checkout is dirty: a Git HEAD alone does not identify its contents.
- Preserve reference images byte-for-byte. Derive disposable test copies and record each transformation. Destructive DOS commands operate only on those copies.

## Tests and hardware

- Zig tests load real linked 6510 code through a small C ABI into Peddle; do not replace the system under test with host implementations. Host oracles and mocks are separate components.
- Enforce instruction/time budgets, first-divergence diagnostics, defined-flag masks, memory guard checks, and an explicit unsupported-feature list.
- Validate modeled REU/UCI behavior against VICE or hardware. Peddle CPU clocks alone are not physical C64U elapsed time.
- Physical C64U testing is required by this project's user; ReuSQL64's project-specific hardware prohibition does not apply here.
- Hardware runs use newly created owned fixture directories such as `/usb1/DOS64_TEST/<run-id>`, preserve prior machine/media settings, and retain evidence. Never overwrite unrelated or original media.
- Reuse the established Ultimate harness/Terminal wrappers where applicable; use REST only for development control/evidence, not as a runtime dependency or guest networking feature.
- No fixed-delay UCI pacing. Use the complete asynchronous state/queue protocol and elapsed-time failure bounds at all CPU speeds.
