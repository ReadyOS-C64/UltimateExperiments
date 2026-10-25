# Released private split-eight deletion worker

Only `wide.s` is the chosen candidate. Its SHA256 is
`6e3d5abcf1129c1ff69251923e1633c84e251f47580c17e795a74137f7e4c1e5`.
`wide-before.s` is frozen production input; `wide-compact.s` preserves the
superseded24-byte per-byte-dispatch alternative for the measured tradeoff.
No production file was changed by this lane.

The per-row branch selects only deletion advance8..11. Eight original
triple-byte left shifts are exactly replacement of A by immutable oldnext1;
the remainder0..3 needs oldnext2 as the carry source. All next-byte reads occur
before the original common tail zeroing/base publication. The narrow/insert
byte loops are unchanged. Prefix masks, suffix masks, dirty-tail zeroing,
glyph/caret union,80-attribute proof and original strict validation remain.
There is no table, self modification, new persistent state, frame growth,
BSS, ZP, REU object or resident code.

Copy this `wide.s` over `src/render/geos/style-typing/wide.s`, then rebuild
C32 and generated stage CRC/length constants plus R30 together using the
normal `src/render/geos/style-typing/build.py` pipeline, and package normally.
This release does not change Makefile/config/API or catalog entries.
Measured C32 grows3404→3553 (raw3372→3521;543raw bytes spare), R30 stays2073.
The private CPU candidate fixture deliberately substitutes only its rebuilt
C32/R30 assets; its D81 is historical input, not a claim of a new native disk.

Exact verifier:
`python3 tests/test_geos_shift8_candidate.py --base build/geos-incremental-editor/20261025T133435860867Z/fixture`
The current2154cases are the original1456 vectors/RNG unchanged, followed by
698 additional8..11 cases with dirty input tails, zero-width insertion,
row-end/EOF-like geometry, byte boundaries, width319, top16/183. Each variant
also passes the original17 malformed-frame/attribute rejection cases. Every
call has an exact64KiB RAM write oracle; source/history/shim and whole16MiB
remain unchanged. Both variants pass18 actual public editor transactions
against forced full rendering and independent canonical source/font pixels.
All18 PNG pairs are byte-identical;14 distinct outputs were directly viewed.

Sustained public CPU instruction savings: italic BACK5067, combined BACK6255,
combined W/M deletions6579. Narrow BACK adds45instructions; warm INSERT adds18.
The longer immutable stage costs3038extra instructions on first prime in these
fixtures. This is a disclosed first-key tradeoff; no native latency claim.
The compact+24 alternative saved4320/5184/5508 respectively, but added198–252
instructions on narrow BACK; root chose per-row dispatch for sustained typing.

Proof: `build/geos-shift8-candidate/20261025T140007955397Z/result.json`.
No additional optimization is included. Native PAL/NTSC, promoted media seals
and the final finite global stack rerun belong to root after integration.
