# Required plain/style typing color witness

A current attribute is an election result, not proof that only one ink role
contributed. `Intro.\rjjj\r- .\rTail.` is a concrete real editor counterexample:
BACK at caret9 deletes middlej. Both old tile bands are white16. The bitmap shift
is pixel-exact, but the cyan list now wins cell160: full render36, old R30 retains16.
Actual unchanged46 reproduction and independent full-render confirmation are in
`build/geos-style-neighbor/actual`, not just a theoretical host fixture.

The private C6 replacement `certify-neighbors.s` is otherwise the exact existing
producer. Its final pre-CRC helper scans <=22 actual typedFE row prefixes. Any
row intersecting `[floor(editedTOP/8)*8, +16)` must have all actual palette roles0.
Rows outside both bands are skipped. Each considered row validates count0..161
and its high byte before reading; empty rows issue no zero-length DMA. Geometry
must be height8/9 and TOP16..191. It saves original GTC_ROW in existing scratch90F3,
uses existing slot/read/zeros helpers and restores the row before certificateCRC
and VALIDlast. GP_RECORD is ordinary caller scratch; exact edited prefix remains
in the sealed GTC_PREFIX. Failure keeps VALID0 and releases the existingowner4.
No source/cache/REU writes, no extra BSS/ZP.

Private linked C6=4030 (+133 from3897),66 spare. Parent promotion should merge only:

```asm
; after final normalglyph/width prefetch, immediately before certificateCRC
jsr neighbors
jcs release
```

and the appended `neighbors` helper. Do not replace newer unrelated producer edits.

Reproduce:

```sh
python3 src/render/geos/style-typing-candidate/build-c6-neighbors.py OUT FIXTURE
python3 tests/test_geos_neighbor_proof.py
```

Actual pendingC6/rootR30 tests prove the counterexample falls back to full correct36,
ordinary white rows still admit, and distant colored rows do not block. Every pixel,
attribute, canonical/history state, foreign16MiB and shim is checked. Explicit
injected derived-cache cases cover count161 including its last role byte, oversized
and high counts and FE epoch/logical/physical ownership faults. This lane made no
canonical production edits or native claim.
