# Read-only 8088 TF profile review

Scope: listed Root source read-snapshot only. No author edits, native execution, source-close acceptance or performance claim. Primary source: Intel1979 Family User's Manual pp2-24..2-28, especially2-28 and figure2-31, https://studylib.net/doc/27791273/9800722-03-the-8086-family-users-manual-oct79 . Pinned Marty files are an implementation cross-check, not authority overriding this original manual.

## Required correctness followup

External IRQ can be admitted with actual TF set while trap_state0: e.g. POPF changes TF0→1 while IF was already1, so no IF shadow is introduced. virtual_irq clears guestTF before the next CPU boundary; boundary then sees no sampled trace and never nests type1 before the IRQ routine. Intel's original nested rule covers an external interrupt in single-step mode. Root independently identified the same gap.

Minimal narrow hook: on accepted hardware IRQ, after FLAGS push and before clearing guestTF, set trap_state2 if currentTF is1. Do not clear existing state2 if currentTF0, since POPF clearing TF can leave one pending trace. A failed partial IRQ entry remains terminal/no retry. A small permanent helper can save PIT bytes if needed. Actual controls should prove new TF/currentstate0 → INTR → type1 before any handler opcode, pendingIRQ mask-deferred → next ordinary instruction traces normally, existingstate2 with currentTF0 stays due, and saved IRQ flags retain originalTF.

## Build graph followup

Selected trap runtime/unit cfg files are missing from PRG prerequisites; editing them need not relink. The existing tracked floppy-format.flag contains only FORMAT value, so changing TRAP1 in the same populated tree lacks object/profile invalidation. Fresh forced builds do not expose this. Track TRAP value in owned profile flag, include selected cfg prerequisites, and test same-tree0→1→0 plus cfg-touch rebuild.

## Resolved concern

Initial suppression hypothesis inferred from Marty step_finish else-if was incorrect for this chosen original8088 contract. Intel2-28 explicitly requires type1 after ordinary interrupt entry and before its first instruction. Preserving state2 across INTR and completing sampled software INT/INT3/divide entry into pendingtype1 is therefore intentional. Do not erase it based on modern processor behavior.

## Source-consistent observations

POPF/IRET sample-before behavior correctly delays newly enabled TF to the following instruction and permits one trap when a traced POPF clears TF. Segment-load own-boundary suppression is separate from STI's IRQ shadow; subsequent instructions are sampled afresh. Prefix host slices retain sample without retirement; REP boundaries retain original opcode-minus2 restart convention. WAIT retains original IP/no retirement while exposing a test-cycle boundary under the existing fixed TEST policy. HLT's completed boundary can wake into trap with post-HLT IP. Host-memory errors clear/suppress further CPU execution; interrupt-frame failure cannot be retried.

Layout inspected:209B CPUTRAP FE00..FED0, separate HDBIOS F000..FDF8. Packer places trap in old sourcegap AE00, and15-page cold HDB copy+exact compare reaches FEFF but not FF00..FFFF. Native startup calls cpu_init only after overlay/HDB bootstrap; isolated tests explicitly install the exact packaged helper. UNIT EF00 sidecar is disjoint. No new overlay or REU allocation/cached-frame reduction found. Existing gap metadata denotes reclaimable startup source after verified copy, not perpetual zero bytes. These are source/map observations, not independent run results.
