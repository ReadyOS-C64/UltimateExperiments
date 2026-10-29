# Private R21 incremental-tile raster candidate

This is a measured replacement candidate for `render/geos/row.s`; the production
renderer and all shared builds remain unchanged. It keeps the public row frame,
all existing validation, packed glyph service, clear paths, palette arbitration,
lease neutrality and borrowed foreground pointer pairs.

For each visible glyph scanline it clips the signed left prefix, computes the
bitmap and role-histogram pointers once, then advances those pointers only when
crossing an eight-pixel tile. The actual glyph bits, saturating ink votes and
selection/caret union remain per pixel. This avoids a larger word-blit or popcount
implementation in the tight sealed image. Histogram votes count explicit inverse
ink before the single selection/caret inversion, exactly as in production.

There is no new BSS, zero-page storage, private frame byte or REU allocation.
CODE stays1719B and RODATA202B; the tail is155B instead of116B. With the existing
entry, glyph, measure and packed assets, the sealed image is4086B with10B spare.
Packed font remains `$ABF3`, widths `$AEDB`. The candidate relocates `next_pixel`
into the tail and reuses thirteen padding bytes to hold the pre-font size fixed.
It does not change the source map, clipping, reset/append, or publication policy.

Run from the SuperEditor directory:

```sh
python3 tests/test_geos_raster_candidate.py \
  --base build/geos-semantic-editor/20261025T075329265974Z/fixture
```

The proof compiles both actual sealed leaves against the same immutable41-asset
resident, runs the existing independent pixel/attribute/histogram/map oracle and
fault suite for each, then adds signed -15..-1 origins, zero crossing, tile edges,
all four styles and eight inverse/selection/caret combinations, partial clips,
two intersecting runs, append and saturation. Whole64KiB RAM, typed source/leases,
fonts, ReadyOS shim and whole16MiB REU guards are retained.

Accepted private evidence:
`agentsworking/evidence/M8/20261025T081347832294Z-geos-raster-candidate`.
Each variant passed1253 strips/50 faults plus554 extra cases. Identical-output
warm sealed-call instruction counts (including validation/clear/resolve):

| Work | Baseline | Candidate | Reduction |
|---|---:|---:|---:|
| blank full strip |13007|13007|0%|
| prose |155142|121090|21.95%|
| dense combined style |299567|217753|27.31%|
| dense selected/caret union |307446|225632|26.61%|
| partial clip |212538|187952|11.57%|
| two intersecting runs |151823|127103|16.28%|

The Peddle fixture exposes instruction counts here, not usable cycle timing.
These results do not claim a native cycle improvement, complete page speedup,
production integration or a changed font ABI. The parent can integrate this
candidate after reviewing the frozen source and byte-identical output proof.

## Separate byte-flush experiment

`row-blit.s` is a second candidate, not an edit to the released pointer candidate.
It accumulates a covered ink byte, counts its set bits once per tile, adds that
count with saturation to the role histogram and ORs its final selected/inverse
byte into bitmap RAM. A glyph scanline writes at most three destination bytes.
It uses two existing spare caller-frame bytes, `GR_PRIVATE+32/+33`; no new frame,
BSS, zero page or REU allocation. Bit assembly still walks the glyph bits; this
is not an unrolled three-byte font shifter or a new font representation.

This version also needs its two new companion includes:

- `row-blit-validate.s`: validation predicates/instruction sequences unchanged;
  only the11-byte `frame_pointer` helper moves into the tail segment.
- `row-blit-resolve.s`: identical palette algorithm; two equivalent near exits
  use ordinary relative branches.

The remaining fit changes are local branch relays, early RTS error returns,
reclaimed padding and ORing the strip-local0..7 y value into the tile-base's zero
low bits before one rowbase addition. The generic partial clear uses that same
address helper and passes the full oracle/fault gate. Error returns still retain
A/C and validation still finishes before output mutation.

The full sealed image is exactly4096B: CODE1719/RODATA202 remain fixed before
the assets, while the tail reaches165B. Packed font/width addresses remain
`$ABF3/$AEDB`. There are no spare bytes. Integration substitutes `row-blit.s`
for the same R21 row object and retains the original entry, glyph, measure,
assets and linker configuration; its companion includes must be present.

```sh
python3 tests/test_geos_raster_candidate.py \
  --base build/geos-semantic-editor/20261025T075329265974Z/fixture \
  --baseline src/render/geos/raster-candidate/row.s \
  --candidate src/render/geos/raster-candidate/row-blit.s
```

Evidence `M8/20261025T082035440863Z-geos-raster-candidate` passes the same
1253 strips/50 faults and554 extra cases for both pointer and byte candidates.
Additional instruction reduction versus the pointer candidate is0.60% prose,
3.41% dense styled,6.17% dense selected,3.92% partial and1.31% two runs; blank
is unchanged. Exact output hashes agree for pixels, attributes and histograms.
The small extra gain and loss of the last ten bytes make the pointer candidate
the recommended first integration. A native cycle comparison could justify the
byte version later; no such timing claim is made by this CPU proof.
