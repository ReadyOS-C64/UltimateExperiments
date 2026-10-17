# Retained first failures

- `first-link-failure`: original long branch distance failure. Repaired with explicit long branches; no layout expansion beyond the approved phase.
- `first-legacy-entry-fixture`: host called the legacy stage5 wrapper. Corrected to actual optional stage8 overlay PREPARE API; no core policy change.
- `first-84-ACK-counterexample`: actual known84 CLOSE was aborted during ACK/finalization before native FILES could establish handle0. Worker now waits for the native terminal handshake; unknown-close controls still fail closed.
- `first-cleanup-CLOSE-counterexample`: prior sticky content error caused ABORT of the already-issued safety CLOSE. Worker now never ABORTs active CLOSE, retains first cause and bounded drain, and attempts at most one cleanup CLOSE.
- `FIRST_FAULTS_SYNTAX.py/.stderr`: host syntax typo; no native execution.
- `first-leaf-STOP-fixture`: hook mistook the initial valid84 CLOSE for intended OPEN85 failure. Hook now selects actual op2 OPEN; actual posted FILE cause precedes physical STOP and is retained.
- `first-flags-fixture-import`: missing Python Regs import stopped one added test. All other21 cases passed; import-only repair, then all22 passed, then fresh source-closed24 passed.
- `first-default-input-staging` plus `CLOSE_FIRST.stderr` and `closed-incoming/05.stderr`: default expected fixture absent after24 native groups completed. Exact failed exit retained; independent default source-build followup passed and checked all original native inputs/products unchanged. No false claim that the original full runner returned0.
