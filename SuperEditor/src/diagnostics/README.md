# Integrated read-only source diagnostics

In the actual source40 editor, F7 `diag` or Help/D starts a bounded diagnostic
job over the visible merged document, including pending RAM edits. It does not
flush or commit pending typing. On completion the read-only popup shows the
snapshot ABI, source length, committed generation, caret, explicit
CRC16/CCITT-FALSE hash type/value, pending/dirty flags, provider epoch/capacity,
logical allocated/free physical counts, overlay loads/hits/calls and borrowed
logical/physical ownership table addresses. All displayed numbers are hex.

STOP cancels an active scan and releases only its own epoch's read lease.
F1/F6/F7 or STOP closes/switches away from a completed popup. Arbitrary popup
keys cannot index the six ordinary menu tables or edit the document. Source,
hot bytes, history, index, navigation and REU data remain unchanged by scanning.
Ordinary document I/O/cache, request fields and shared CRC/ZP remain transient.

This is not a cryptographic hash. Hash type1 means CRC16/CCITT-FALSE:
polynomial1021, initialFFFF, no reflection and no final XOR. The job saves its
private CRC across slices, so ordinary overlay admission/other clients may
clobber the shared resident CRC between calls.

`api.inc` defines the complete128-byte DGS1/ABI1 descriptor. Its status is1
scanning,2 complete,3 cancelled or4 failed; only2 makes the CRC authoritative.
The descriptor lives in an exclusively borrowed128-byte portion of COW output
scratch at8800, protected during the scan by the service's read lease. R1 paints
with8000/8400/hot memory and leaves it intact before C7 draws the popup. The
coordinator retains this scratch until the popup closes; consumers must not
persist the descriptor after another operation reuses COW output scratch.

Owner counts are captured at BEGIN: logical owner1..254 includes control, and
free physical owner0 excludes unavailable255. Map/logical-owner/physical-owner
pointers describe three live256-byte provider arrays; they are explicitly not
copied archival allocation tables. They remain valid only for the recorded
provider epoch and while the foreground coordinator prevents allocation changes.
Logical handles and physical banks are separate identities.

The implementation links only needed assembler micromodules:

- Resident `state`, `cancel` and `dispatch`:28 persistent bytes, no new ZP;
  cleanup also works after C11 admission/reload failure.
- C11 `snapshot`, `context`, `scan`: D_BEGIN1/D_STEP2 share C11 with existing
  bounded layout operations4/5. Each STEP consumes at most128 native bytes and
  eight committed source-piece spans. Gap runs stop at their prefix/suffix seam.
- C7 `ui`: ReadyOS blue/white/light-blue frame, yellow title, cyan values and
  gray close hint, using ordinary TUI cells. Help toggle U_HELP7 is also in C7.
- `tools/diagnostics_bindings.py`: zero-byte aliases for actual module imports
  against the complete sealed resident build, excluding cold/slot/shim bindings.

BEGIN refuses active document/hot/history/block/clipboard/snapshot work and
validates every hot bound/token. Continuations check full source tokens,
generation/length/epoch, hot context and visible edit revision. Competing BEGIN
refuses78 without destroying an active job. Context mismatch79, buffer/caret7A
and malformed-gap7B refuse; lower provider/object/document/overlay errors retain
their values. Failed C11 reload routes through resident abort before displaying
the original error. Same-epoch foreign counted leases and new-provider leases
are preserved.

`make diagnostics-test` runs the actual editor/overlay pipeline with independent
merged-source CRC and complete popup/restored screen/color oracles, including
over64KiB source, pending high PETSCII/CR, eviction, STOP, foreign leases, missing
C11 and context failure. `make diagnostics-vice-test` uses the actual ROM/D81/
IRQ-native-byte queue and records native pixels/source/REU/shim evidence. Native
input is not proof of physical modifier chords or hardware autorepeat.

The separate `probes/diagnostics/` fixture remains useful for full1MiB/2048-piece
boundaries and service isolation. It does not substitute for integrated UI/native
evidence. Current linked measurements and exact asset identities belong in the
retained build reports and dated session/evidence; no whole-goal completion is
implied by this feature.
