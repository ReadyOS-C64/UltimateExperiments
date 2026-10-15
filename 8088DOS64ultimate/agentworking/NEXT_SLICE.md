# Next bounded slice: M0 assembly-to-Zig/Peddle foundation

Start only when the user resumes implementation after reviewing the plan. First incorporate any review changes and reread STATUS/DECISIONS.

## Objective

From this project root, a single fast test command assembles a minimal real 6510 test payload, runs it in Peddle through Zig, and asserts register/memory/ABI behavior with a reliable bounded failure path. This is the foundation for the emulator, not a full x86 opcode implementation sprint.

## Steps

1. Resolve tools from explicit `DOS64_*` variables, then known sibling tooling/PATH; capture versions, hashes, licenses and machine-independent paths in a manifest. Use Zig 0.16.0. Pin/copy Peddle with license rather than depending indefinitely on a dirty sibling checkout.
2. Add ca65/ld65 raw unit-payload and PRG builds, labels/map outputs, and a memory-contract checker. Define a small test mailbox and ZP/clobber conventions. Validate the display-bank constraints in the proposed map even if the first payload has no renderer.
3. Add a small C++ Peddle bridge and Zig runner/tests. Reuse the approach from ZeroPage, not its fixture-language compiler. Load a real assembled routine, seed state, run to sentinel, assert outputs and non-clobber regions. Demonstrate intentional failure, timeout, stack imbalance detection, and first-failure report.
4. Add only the device/bus skeleton needed by that payload. Distinguish unimplemented REU/UCI semantics explicitly. Do not copy the existing simplified mock and label it complete.
5. Re-run the read-only reference inventory and compare the saved hashes. Set up a project-local DOSBox-X config and disposable disk-1 clone; boot the actual DOS image, record CONFIG diagnostics and VER. Prepare a minimal-config derivative only with a recorded transformation.
6. Update records with exact commands/results and move NEXT_SLICE to M1's bounded measurement probe.

## Acceptance

- A passing assembly behavior test, an intentionally wrong expectation that is caught, and a bounded runaway test all work through Zig/Peddle.
- Labels/map/ABI are used by assertions; no guessed addresses tied to one build.
- No changes to reference images, other project code, root working records, or unrelated physical media.
- `make test` (or the recorded equivalent) runs without physical hardware; unsupported/unavailable lanes are labeled.
- If DOSBox setup remains unresolved, record its exact first failure and continue independent M1 probes; do not claim reference boot has passed.

Do not start a new chat, substitute ZeroPage for assembly, implement a native DOS API, or expand into applications before this gate.
