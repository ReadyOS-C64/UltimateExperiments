# Private physical-row geometry service

This page describes the earlier component/budget checkpoint. The subsequent
complete editor transaction, exact final scope and executable qualification are
documented in [full/README.md](full/README.md). Its earlier component archive
remains unchanged.

This is an unfinished editor candidate. No files here are linked by the shared
Makefile. No source, NC header, row anchors or packet publication is implemented
by the vertical primitive. Its successful component tests do **not** demonstrate
an editor fast path.

## Measured placement

The first placement controls came from the immutable first-capture fixture
at`agentsworking/evidence/M8/20261026T083129610982Z-grid-capture-cost`.
Current R24/C33 builders instead pin the corrected current59-asset fixture
`build/capture-index-fixed/20261026T183928480377Z/fixture`, including both
capture refusal ordering and sparse-index revocation. No mutable labels are read.

| Existing R-slot | Actual payload | Space | Result |
| --- | ---: | ---: | --- |
| R16 grid80 | 4096 | 323 before fixed A800 font | too small for complete geometry |
| R17 grid60 | 4096 | 0 before fixed A800 font | too small |
| R30 gtype | 3656 | 440 | checked primitive alone overflows by88 |
| R24 geosfold | 1541 | 2555 | selected private placement |

`r24-budget.py` first reassembles R24 byte for byte. It then adds owner4-only
operations3 PREPARE and4 APPLY, leaving the existing fold opcodes0..2 and their
CF00..CF2F state intact. The first primitive image is2125 bytes. Adding the
actual FS59 capture/check component makes2389 bytes, leaving1707. All bindings
are generated from the frozen resident report. No BSS, ZP or extra asset is
allocated.

`r30-budget.py` records the rejected R30 placement, rather than trusting the
historical2073-byte size. The current R30 has grown to3656.

## Component contract and lifetime

The primitive frame is8D80..8D98; the source-authority extension uses8D99..8DDA.
These do not overlap C33 LS8D00..8D14, R14 carry LPF8D40..8D68, or the legacy
FS frame8EE0. They **do** overlap the retained sparse line index. Actual C33
long_try revokes se_i_ready/se_i_count/se_n_cache_count before these phases;
that is a required caller lifetime, not something established by owner4 alone.
The component fixture explicitly retires those index fields before borrowing
the phase; it cannot establish the complete editor caller contract. C33's CAPTURE-only CRC tables may alias this frame only during its
separate, lease-free OP0 job. New geometry must only enter after the actual
redraw/drawbusy refusal. It must not inherit the historical capture release's
initialization-before-redraw-check ordering.

Inputs: version1, direction+1/-1, first logical body row0..21, row count0..22.
PREPARE computes CPU addresses and lengths, checks both source/destination body
bounds, and captures the actual FE logical handle, physical mapping and epoch.
READY is published last. APPLY checks ownership, FE tuple, READY and recomputes
all derived addresses/lengths before any write. It clears the existing three GC
valid bytes before mutation. Missing/old R24 rejects the new operation before
pixels; a future C33 caller must require C clear/A0 at PREPARE before removing
its old caret.

Bitmap source/destination are inside6280..7DFF; attributes inside4050..43BF.
The operation uses the real checked DMA adapter, with no physical bank literal.
It first stashes the source interval in the same actual FE bank, then fetches
that interval to the destination. Thus overlapping moves work in either
vertical direction. Temporary offsets2000..3B7F (bitmap) and3C00..3F6F
(attributes) are disjoint from current source-grid packets0..149F, NC1500..15FF
and SP21600..167F. The contract is Plain source60/80 only. GEOS packet layout
uses other FE extents and is not admitted. Pixel and attribute bytes are copied
unchanged, including arbitrary inverse/color patterns.

`authority.s` captures the exact public FS_FIELDS59 live tuple, not a fabricated
host certificate. It calls actual view/document validation, checks all three
typed objects and excludes document/hot/history/block/clipboard/snapshot busy
states and foreign source leases. CHECK validates the same tuple without
recapturing. It borrows only the already-foreground text pointer. This is an
internal component, not a new public operation. The future caller must still
retain real R25 old-NC authentication and C33's complete byte-for-byte proof of
the one actual edit. Capturing live source fields is not proof that arbitrary
old NC metadata matches that source.

The intended integration executes within **one uninterrupted existing C33
long transaction**, with only its actual pure R14 pixel calls in between. It
does not retain an unauthenticated source proof over root idle/input mutation.
No source lease is invented, and no semantic/SP2 authority is fabricated.

## Existing executable proof

```
python3 src/render/grid/probes/row-geometry/r24-budget.py build/UNIQUE
python3 tests/test_grid_row_geometry.py --build build/UNIQUE
```

The first gate at`build/grid-row-geometry/20261026T183812245651Z/result.json`
passed160 independent overlapping-copy vectors and29 fault groups. Every call
checks entire64KiB RAM and16MiB REU, canonical/source lease/shim, both chrome
boundaries and the untouched fold CF state. Faults include wrong owner,
malformed bounds, each stored raw-address/length byte, FE epoch/map/logical and
physical ownership, mode/policy/selection changes. Existing fold no-map op0
also passes. The source component gate separately checks the real59 bytes and
all23 source-field groups plus busy exclusions. See its terminal result rather
than assuming it passed from its build.

## Complete next transaction (not implemented)

First support raw alphanumeric insert/BACK that adds/removes an empty CR
physical row. Actual CR split/merge remains a separate extension.

1. Existing C33/R25 authenticates NC/source/font/old packet CRCs, verifies the
   actual source delta and every affected paragraph byte. Geometry admission
   remains Plain, no selection/folds/pan, unchanged real source graph.
2. Before old-caret removal, geometry PREPARE must additionally authenticate all
   following cached packet CRCs and source/NC/FE witnesses. No VIC/header or
   published packet write is allowed on refusal. Keep the exact old NC header
   CRC and source59 tuple across the pure carry calls.
3. For insertion, shift following physical rows down one and drop old row21;
   create the new empty CR row after the former terminal. For deletion, remove
   the existing empty CR row and shift following rows up. Initially require
   old EOF visible for deletion so the newly exposed final row is known blank.
4. Preserve arbitrary following pixel/attribute contents by whole8-scanline row
   copies. Move the corresponding240-byte packets, CRC pairs, true-CR bits and
   24-bit row anchors in the same direction. Recompute the new blank packet's
   CRC and caret ownership; do not merely clear packet/header validity to claim
   a successful update.
5. Adjust LS_LAST only after the original pixel carry, so C33's packet loop and
   final R25 commit operate on the genuine new terminal. Publish a coherent NC
   header and draw sequence only after all packet/anchor/VIC work succeeds.
   Existing failure/fallback must see cache invalid throughout partial writes.

A small C33 bridge can use the boundary-only branch (ordinary same-row and
Full paths stay unchanged), then PREPARE before pixel mutation and APPLY after
R14 carry. Its actual assembled budget still must be measured against80 free
prefont bytes. The remaining R24 body has1707 bytes after the real source59
component; packet/anchor/header code has not yet been assembled. If that does
not fit, an explicit existing-body redistribution or catalogue-slot tradeoff
is required. No internal future MAP5 reservation is treated as a user mandate.

## Concrete C33 bridge budget

`c33-budget.py` reassembles the frozen original C33/R25 pair byte for byte,
then applies only the prospective boundary hooks in its private tree. Both
current capture corrections are inherited and asserted in the pinned source.
The actual linked C33 CODE/RODATA ends BEFF, with zero bytes before the
immutable BF00 font. R25 remains byte-identical4057. This is a **link budget**, not a functional geometry candidate: R24's
terminal admission and metadata transaction remain to be implemented.
`build/grid-row-geometry-c33-fixed-index-budget/result.json` pins the current
emitted image; the earlier BEF4 bridge receipt lacks the later11-byte sparse
index correction and is historical only.
The old/new R24 failure path is fail-closed because unknown op5 returns Cset
before the existing caret or pixels are touched. Mixed-generation runtime
proof is still required before any release.
