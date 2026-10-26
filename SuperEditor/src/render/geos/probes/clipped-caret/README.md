# Private clipped GEOS source caret fix

Released candidate; no canonical/shared build, Git, hardware or native changes.
Input is packedcold54 fixture `build/cache-editor-product/20261026T051042908519Z/fixture`:
PRG `a2578487c8a552b0c7fbc41f8b965fad8fa05020d7dd90be3820c30d3cbd8ce7`,
binding `f50620a2a2594b3617209b3ad36ed32a`. The sealed mapped INLINE release
is unchanged. This component does not implement mapped REKEY or E47 composition.

## Diagnosis and intended behavior

The independent raster selects the actual canonical caret cell (`at == caret`),
unions that flag with selection, then clips each output pixel. This matches R21's
existing selected/caret union: one inversion, after underlying ink color voting.
It deliberately permits an intersecting part of a cell whose left boundary is
negative. Native8 code uses the same source-cell and clipping contract.

C20 already retains the first intersecting glyph and its signed `GPR_RASTER_X`.
C21 independently publishes two different facts: `GPR_MEMBER` says the caret
belongs to this logical row even if panned offscreen; `GPR_CARET_VALID` and
`GPH_CARET_VISIBLE` describe whether its **boundary point** is in the viewport.
Its actual CR/EOF tail has a separate signed-cell intersection witness,
`GPR_TAIL_VALID`. These definitions are explicit in the frozen `editor.inc`.

C22 incorrectly used the boundary-point flag twice to decide whether to consider
caret inversion of a glyph. It also tested the boundary X range before drawing
its virtual CR/EOF cell. At caret0/TOP0/PAN1/manual1, the first six-pixel `A`
starts at −1: its remaining five pixels are visible, but its boundary is not.
Original C22 omits those five caret pixels in all nine font scanlines. Exactly
bitmap bytes640..647 and960 differ by XOR $F8; attributes are identical.
This is a product rendering bug, not an oracle exception inferred from history.

The three-hunk `ready.patch` changes both glyph caret gates to authenticated
logical row membership. Existing per-cell canonical comparisons still determine
which packet cell receives the caret; fully hidden cells are absent from the
packet and receive no inversion. The virtual-cell path uses `TAIL_VALID`, then
its existing canonical equality/union and signed R21/native renderer. No map,
point visibility flag, source caret, preferred X or metadata is fabricated.
Boundary visibility remains0 for a negative point; logical `se_v_seen` remains1.
R27's conservative refusal of any nonzero pan remains asserted, avoiding its
separate caret-free rectangle cache assumptions.

## Fit and reproduce

```
python3 tests/test_geos_clipped_caret.py --smoke
python3 tests/test_geos_clipped_caret.py
```

The builder extracts only frozen sources to private output and proves original
C22 raw bytes equal the packaged image before compiling the patch. The actual
public fixture imports that C22 capsule before source setup. There are no
resident operand seams, new IDs, banks, objects, BSS or ZP, and no new call edges.
Only caller pan/manual, source caret and selection inputs are supplied; emitted
semantic, geometry, cache flags, row packets or pixels are never seeded.

C22 original4070 bytes, candidate4056 (14 bytes reclaimed,40 free).
Candidate raw SHA256:
`364f32b6755410846343dc1b44154e8c7b94dd979f5b65ba7b2d7998a4f20fb0`.
Original raw SHA256:
`ae5ab53e14199c63f21cfabb8572b15a851bbf19b471dd3f197bb4b73d8c256b`.
Promotion needs only the three source hunks, normal C22 sealing/rebinding and
whole-product regression; this is not a production promotion or native claim.

## Terminal verification and costs

Run `build/geos-clipped-caret/20261026T075551540510Z` passes90 source frames:
original/candidate and repeated repaint comparisons, plus Plain and recovery.
Vectors cover first-cell width2/6, partially/fully clipped and visible caret,
actual bold/italic/both advances, selection forward/reverse and union, empty CR,
empty EOF, partial/hidden EOF virtual spaces, unaligned native8 code,161-glyph
right-edge clipping and24-bit PAN65537. The original nine-byte discrepancy is
required, not silently accepted as correct. Every candidate bitmap/attribute
and canonical row/geometry matches the unchanged independent oracle.

Actual queued STOP at the pending C22→R21 boundary consumes STOP and releases
owner4; this differs legitimately from the observer-held INLINE early preemption
which cancels before consuming its key. Missing R21 gives actual error17 and
resident cleanup. Both recover through real public input/render to exact pixels.
Eighteen wrong-owner calls (six owners × BEGIN/STEP/CANCEL) refuse with B2 before
phase, pixels or REU writes. No owner guard or failure cleanup was removed.

6,420 actual C22 public service invocations compare all64KiB outside declared
raster/loader/request scratch extents. These declarations are explicit in the
verifier; they do not claim every RAM byte is immutable. Committed roots,
canonical/pending source, undo/clipboard/selection and observer queue get an
additional exact invariant. Every complete C22 pass is all16MiB read-only.
Whole public renders permit only documented typed FE output spans; changed64B
outgoing certificates independently pass type/source-key/canonical-anchor/CRC
checks before their exact spans are allowed. Shim/neighbor/foreign memory stays
exact. No full-REU snapshots are duplicated in the archive.

Two actual read-only preview frames are byte-identical original/candidate and
match the raw-font preview oracle; preview makes zero C22 calls, so this fix does
not add a preview caret. Its exact typed preview/glyph cache spans are guarded.
Preview instruction counts reflect prior cache history and are not an A/B speed
claim. Six representative source/original/preview PNGs were directly inspected.

Measured source instructions include newly correct work: A/PAN1 increases
511,320→519,050 (+7,730); fully hidden A increases374,065→377,881 (+3,816) because
canonical comparisons are now considered for the logical row; ordinary visible
A is384,294→384,292 (−2). This is a correctness fix, not a performance claim.
The wider mapped cache and navigation limitations remain open.
