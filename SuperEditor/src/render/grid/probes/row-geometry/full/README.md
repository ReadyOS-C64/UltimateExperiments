# Complete private raw physical-row transaction

This version adds/removes the empty CR physical row created when an ordinary
Plain insert/BACK crosses a 60/80-column wrap boundary. It is an actual C33
transaction, with final packet, anchor, CR-bit, header and draw-sequence
publication. It is not linked by the shared Makefile and has no native proof.
The earlier primitive/component archive is unchanged.

## Exact inputs and fit

`build.py` pins the committed-source946 fixture
`build/capture-lexical-integrated/20261026T190219265642Z/fixture`, binding
`7abb2d3f53543b3dfd5c297c6760a5f6`. It first reconstructs the frozen C33/R25
and R24 controls byte for byte. Only C33 `grid` and R24 `geosfold` are replaced
in the private CPU fixture; its D81 remains the control disk, so this fixture
must not be described as a native package.

Final `build/grid-row-geometry-full-fit11` has:

| Image | Bytes | Remaining space |
| --- | ---: | ---: |
| C33 | 4096 padded | CODE+RODATA ends BEFD inclusive; 2 bytes before BF00 |
| R24 | 3983 | 113 bytes |
| R25 | 4057 | byte-identical to the frozen control |

No new asset, resident code, BSS, ZP, object or REU bank is allocated. The fixed
C33 BF00 font remains unchanged. R24 original fold operations0/1/2 and their
CF00 state remain present. New operations are3 PREPARE,4 APPLY,5 BOUNDARY.

## Complete authority and lifetime

The actual C33/R25 NC/source/font/provider/old-packet admission remains in
force. Every affected paragraph source byte is compared to the genuine old
packet under the existing one-edit transformation. New BOUNDARY additionally
binds old NC token/generation/epoch, length, revision, hot base and caret to
the actual new source. It captures all59 live FS identity fields at that point.
PREPARE and APPLY validate that snapshot without recapturing it. Actual document,
view and all three typed source objects are checked, along with busy and foreign
source-lock exclusions. This is one uninterrupted foreground C33 operation;
there is no saved continuation over an idle/input mutation and no fabricated
source lease or semantic/SP2 certificate.

The prospective latch was corrected to occur **after** old-source admission and
`se_i_ready/se_i_count/se_n_cache_count` retirement. The corrected capture ordering
also remains: redraw/drawbusy refusal precedes any capture-table write.

Phase map during this exclusive raw transaction:

| Span | Use |
| --- | --- |
| 8A00..8AFF | actual NC header |
| 88C4..89B3 | actual 240-byte row packet |
| 8B00..8BFF | checked header/packet transfer scratch |
| 8D00..8D14 | existing paragraph state |
| 8D40..8D68 | existing pure R14 carry state |
| 8D80..8DFF | geometry plan, snapshot59, CRC/control and latch |
| 8E00..8FFF | CRC tables regenerated from resident immutable tables |

These spans overlap the retired sparse index. The CRC tables also overlap the
inactive legacy FS frame; this operation owns no live source-reader context and
does not call source-reader operations. R14 is used only for the existing pure
pixel carry operations. Full/GEOS jobs cannot concurrently own this phase.

PREPARE authenticates the actual published FE header against the local NC
header, checks its CRC, and checks every following 240-byte packet CRC before
old-caret removal. APPLY repeats the source/FE/header/packet proofs and recomputes
all derived metadata controls before its first mutation. All three GC-valid
bytes are then cleared. Body suffix copies use the real mapped FE handle and
checked DMA; bitmap and attributes are bounded to6280..7DFF and4050..43BF.
Temporary FE extents2000..3B7F/3C00..3F6F are disjoint from live source-grid
packets, NC1500 and SP21600. No physical bank literal is used.

Packets, their full240-byte CRCs, true-CR bits and24-bit anchors move in the same
overlap-safe direction as the body. The new blank row is sealed and the real
VIEW anchors updated. Existing C33 then paints the new caret/status/changed
paragraph, and **existing R25 final commit alone publishes the NC header and
draw sequence**. Late failure leaves the old published header and no new draw
sequence; derived validity is invalidated, or the old source/header tuple
rejects the next fast attempt, before the normal renderer repairs the frame.

Mode60's producer updates only60 active packet cells. The final candidate
preserves its20 inactive cells from the validated packet. Normalizing all80
was incorrect: it made later fallback compare unchanged packets as dirty.
The failed A/B remains retained; output bytes were correct but BACK fallback
cost rose to1.599M instructions. The final fix restores465k on that case.

## Scope and explicit fallbacks

Admission is Plain source60/80, ordinary non-CR insert/BACK, no selection,
fold projection, pan, UI job or source fault, with the existing complete raw
source transformation proof. An insertion may move following rows down and
drop row21; deletion initially requires old EOF visible so the newly exposed
bottom row is known blank. Insertion at old terminal row21 refuses. Actual CR
split/merge, Full semantic geometry and deletion exposing an unknown offscreen
row still use the normal renderer. Deletion with old terminal row21 also
falls back: its zero-length suffix starts at22, outside the existing checked
kernel's source-row contract. Row20 insertion with zero suffix is admitted.
This increment does not finish general
structural typing performance.

## Reproduction

Use unique output directories. These commands never build shared products:

```
python3 src/render/grid/probes/row-geometry/full/build.py build/UNIQUE
python3 tests/test_grid_row_geometry.py --transaction-build build/UNIQUE --out build/UNIQUE-proof
```

The aggregate verifier calls the same public, fault, compatibility, regression,
registered-stack and precise-PC profile modules used for the sealed individual
runs. The component-only default remains a separate API/proof.

Final individual receipts:

- `build/grid-row-geometry-full-public11/result.json`:20 actual public frames,
  independent complete bitmap/attributes/packet/23anchors/NC CRC checks,
  canonical/history/clipboard/Plain semantic preservation and exact16MiB
  checked-DMA guards; includes source positions above64KiB.
- `build/grid-row-geometry-full-fault11/result.json`:40 early and late actual
  source/token/revision/gap/lease/mode/header/packet/plan/FE faults, no partial
  new header/draw-sequence publication, followed by real fallback repair.
- `build/grid-row-geometry-full-compat11/result.json`:8 mixed-generation frames,
  10 public insert/Undo/Redo/caret frames,2 missing-R24 prewrite repairs.
- `build/grid-row-geometry-full-opaque11/result.json`:18 owner-first opaque
  calls for all new opcodes, entire borrowed phase and16MiB preserved.
- `build/grid-row-geometry-full-edges11b/result.json`:8 public row20/21 edge
  frames with exact pixels/packets; last-row and one-past-empty-suffix fallback.
- `build/grid-row-geometry-full-regress11/result.json`:unchanged released
  Full/Plain edit40 and complete original GEOS fold28 suites.
- `build/grid-row-geometry-full-stack11/proof/result.json`:all59 actual images,
  foreground52, one IRQ/NMI16, relative combined68, no new opaque call edges.
- `build/grid-row-geometry-precise-{control,candidate}/result.json`:PC-observed
  first draw-sequence publication and settled idle, excluding later oracle reads.

CPU instruction counts, **not** native cycles or physical-key latency:

| Case | Control first / settled | Candidate first / settled |
| --- | ---: | ---: |
| 60 insert new row | 403857 /482609 | 304111 /304117 |
| 60 BACK remove row | 415080 /493729 | 201502 /201508 |
| 80 insert new row | 330170 /408703 | 313533 /313539 |
| 80 BACK remove row | 343391 /421836 | 212131 /212137 |

CR insertion and BACK remain within one instruction of the original fallback:
60 settled668751/653762;80 settled535835/519751. New-row candidate first
publication is also completion, with only six instructions to settled idle.

## Promotion manifest

Parent owns all canonical changes. The exact generated source to review/copy is:

- `build/grid-row-geometry-full-fit11/bridge/tree/src/render/grid/caret/caret.s`
- `build/grid-row-geometry-full-fit11/bridge/tree/src/render/grid/paragraph/controller.inc`
- `build/grid-row-geometry-full-fit11/bridge/tree/src/render/geos/fold-entry.s`
- `build/grid-row-geometry-full-fit11/kernel.s`
- owned `full/authority.s` and `full/transaction.s`.

R24 links original `fold-query.s` plus the new kernel/authority/transaction
objects. No R14, R25, C14, C16, R16 or R17 source change is required. C33 adds
one sequential R24 helper and boundary/PREPARE/APPLY hooks; no C-slot nesting.
The builder emits actual `module_bindings` aliases once and asserts zero BSS/ZP.

If combined with a changed R16/R17, regenerate **real native witnesses into
R25, then real R25/helper and paragraph witnesses into C33**, using the normal
production build order. Do not transplant old generated witness constants or
waive size/CRC checks to preserve the private hashes. The R24 geometry code
itself does not use an R16 code address. Native/package qualification belongs
to the parent after coherent rebinding.
