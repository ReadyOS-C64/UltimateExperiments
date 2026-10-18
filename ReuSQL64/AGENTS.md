# ReuSQL64 Agent Guidelines

`docs/architecture.md`, `docs/memory-map.md`, and `docs/sql-language.md` are the
current design contract. Implement the project in small target-tested slices.

## Non-negotiable rules

- Never access, reset, upload to, mount media on, or otherwise use a physical
  C64 Ultimate while working on this project. Do not invoke `run-ultimate-plan`.
- Use Peddle for the fast 6510 suite and the .NET VICE task harness for
  integration tests.
- Keep `$0801-$30FF` client-owned. The link/map check must fail when engine code
  or data crosses into that range.
- Preserve support for 512KB through 16MB REUs.
- Do not add an optimizer or cost-based execution planner. An unhinted source
  scans; `USING INDEX` explicitly selects a named index.
- Add or update tests with every behavior change.
- Unsupported SQL must return a focused error rather than being guessed at.

## Long-horizon records

- Update `AgentsWorking/STATUS.md` after every verified slice.
- Keep `AgentsWorking/NEXT_SLICE.md` pointed at the next bounded slice.
- Append evidence and course corrections to
  `AgentsWorking/LessonsLearntAdditive.md`; never rewrite old entries.
- Rewrite `AgentsWorking/LessonsLearnt.md` whenever the current concise advice
  changes. Remove stale advice so it remains the fresh set of lessons.
- Record durable choices and supersessions in `AgentsWorking/DECISIONS.md`.
- Record exact test commands and first failures in `AgentsWorking/TEST_LOG.md`.
- Update `AgentsWorking/MEMORY_BUDGET.md` from linked map evidence.

## C64 implementation rules

- Target cc65 C plus ca65 assembly. Use explicit-width project types instead of
  assuming host C widths.
- Avoid `long` in hot loops; 24-bit REU addresses and 64-bit database values use
  explicit byte-array helpers where practical.
- Keep the seven overlay images stateless. Persistent state belongs in resident
  RAM or REU.
- A REU page is 256 bytes and page identifiers are 16-bit. Zero page-id values
  are valid physical pages but reserved by the storage format.
- Every persistent format change requires a version bump, migration decision,
  corruption test, and documentation update.
