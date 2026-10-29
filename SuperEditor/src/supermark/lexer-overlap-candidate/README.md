# Private BASIC streaming keyword-overlap repair

This candidate changes the actual pure lexer, not an oracle or cached row role.
Production `src/supermark/lexer.s` remains parent-owned. The original input
`SECOND` holds `CON` as a possible `CONT` prefix. When `D` rejects `COND`, its
suffix `OND` is already longer than `ON`; the old table skipped that keyword
and discarded the overlap. The unchanged independent greedy BASIC model
correctly expects the reserved `ON` at [3,5).

The candidate resolves buffered suffixes at mismatch, separators, CR and EOF.
BASIC table search can match a complete keyword at the beginning of a longer
buffer. Emission uses `start+matched_length` rather than current input+1; the
remaining buffered letters are replayed before consuming another input byte.
REM retains its original comment start; DATA consumes its literal remainder.
Incomplete valid prefixes are retained only while more input is possible.
ASM table matching remains exact-word matching.

There is no new mutable storage: existing BASIC-normal-only scratch borrows
`sl_quote` as the flush flag and the ASM-only `sl_overflow` byte as the matched
length. Strings initialize `sl_quote` normally. The existing 60-byte public
snapshot and queue2 remain unchanged. No BSS or ZP allocation is added.

Reproduce CPU proof:

```sh
python3 tests/test_lexer_overlap_candidate.py
```

It runs the assembled6510 lexer against the unchanged whole-input host model:
all keyword pairs, every strict/full keyword prefix with every next byte0..255,
random streams, quotes/REM/DATA/CR/EOF, 24-bit spans across64KiB and fresh-CPU
state snapshots inside pending prefixes. The queue never exceeds2. Backpressure
preserves position/unread queue/allstate except the pre-existing `sl_byte`
input scratch assignment made before the busy check. Whole64KiB guards permit
only the60-byte lexical state and hardware stack.

Private coherent placement proof:

```sh
python3 src/supermark/lexer-overlap-candidate/build-fits.py OUT IMMUTABLE_FIXTURE
```

This extracts the exact product source ZIP, substitutes only this lexer, and
links C15, C25 and the production C31/R31 builder. It privately moves the
staging capability stamp from5C80 to5D00 because the new staged code ends at
5CF2. Parent must make that same one-constant adjustment if promoting; all
legitimate window-writer/CBD5 fences remain unchanged. The original executable
jump ABI5000/5003, binding checks and generated CRC witnesses remain intact.

Measured fit against released46 fixture20261025T104900415766Z:

- Pure lexer2845 bytes, +141 from2704; same60-byte state.
- C15 lexical3805, C25 GEOSlex4044, C31 staged image3346/raw3314.
- R31 remains3677 with regenerated exact C31/raw CRC constants.

This is private component/placement proof, not production/native acceptance.
Parent owns canonical lexer promotion, stamp adjustment, all-image rebuild,
editor/source-style regressions and a fresh native frozen build.
