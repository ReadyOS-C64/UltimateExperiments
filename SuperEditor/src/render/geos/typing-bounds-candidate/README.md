# Private segmented bitmap-shift bounds

`wide.s` / `wide.patch` is the released recommendation against the immutable
942-byte style-typing-candidate/wide.s. `normal.s` is a measured private analogue
against typing/patch-buffered.s; the current4091-byte R30 has no room for it and
it is not proposed for that production image. No existing production or other
agent files were edited by this lane.

Validation guarantees an actual width below320 and x<=newwidth. Therefore
xb=floor(x/8)<=nb=floor(newwidth/8)<=39. The existing unused private byte `np`
now contains nb+1, in1..40. Per scanline:

1. Copy base bytes [0,xb) directly; every pixel is before the edit.
2. Run the original shift/mask/merge on [xb,nb], inclusive. The edit and new-tail
   boundary bytes retain their original masks, glyph insertion and caret union.
3. Explicitly zero bytes [nb+1,40), independent of dirty old input-tail bits.

The old unreachable prefix-copy branch and beyond-tail mask branch are removed
from the middle loop. The base-cache copy, caret overlay, VIC addressing, all
validation and attribute guard paths remain unchanged. There is no new frame,
BSS, zero-page or REU storage. The only newly used scratch is the existing np
byte: wide frame8A80 +GT_PRIVATE29 +7 =8AA4; its lifetime is one primitive call.

Final gate: build/geos-typing-bounds/20261025T115607140911Z/result.json.
Tests/test_geos_typing_bounds.py reuses the exact existing1456 wide vectors/RNG
and independent bit-list pixel oracle, adding per-vector before/after hashes and
instruction counts. The new normal1024 vectors are explicitly new, include dirty
unused input tails, and are not mislabeled as a historical1024 gate.

| Primitive | Before | After | Instructions before → after | Aggregate saving |
|---|---:|---:|---:|---:|
| wide |942B|964B|48,321,909 →39,466,733|18.325%|
| normal |815B|837B|26,199,828 →14,720,489|43.815%|

There are zero regressing vectors; even the full319px row/front-edit case saves
331 instructions. Wide maximum saving is32,101 instructions. Wide17 malformed
paths and normal20 malformed paths preserve every output byte: op/flags/top,
advance/caret bounds, malformed X/width high bytes, glyph bits outside advance,
and all four edge positions in the80-byte attribute guard. Every normal/success
case validates all65,536 CPU bytes with only the existing private/stack/loan
scratch and exact output spans allowed; source/shim and full16MiB stay exact.

These are actual CPU instruction counts for a low-level trusted caret-free
base/pretransformed-glyph seam. No new root/controller, source-certificate,
native timing or latency claim. Integration belongs to the parent. A prior
per-column-check variant is retained as `*-columnchecks.s`: although correct,
it regressed833 of1456 wide cases. Do not promote that variant.
