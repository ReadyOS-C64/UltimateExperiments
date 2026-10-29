# Plain physical-row geometry

C33 uses the existing R24 slot sequentially for BOUNDARY(5), PREPARE(3) and
APPLY(4). Original fold operations0..2 remain intact. This extends ordinary
Plain60/80 insertion/BACK across a wrap boundary that adds/removes an empty CR
physical row; actual Return-key splitting/merging retains its existing fallback.

The existing source transformation, NC/header/packet/font/provider checks remain.
BOUNDARY binds the old NC key and actual new source, capturing all59 source
identity fields. PREPARE/APPLY check that same snapshot, every affected packet
CRC and independently derived ranges before mutation. The transaction does not
yield. It explicitly revokes sparse-index authority before borrowing its RAM.
R24 writes only bounded body pixels/attributes and the genuine FE scratch bank;
no physical bank literal, source lease, semantic certificate or new RAM exists.

R24 moves packets,24-bit anchors, true-CR bits and bitmap/attributes in matching
overlap-safe directions. It preserves inactive60-column packet cells. Derived
validity is revoked before mutations; failure leaves no newly published NC or
draw sequence. Existing R25 alone performs final NC/header publication.

The checked source-row bound is FIRST<23. Existing independent count/destination
bounds make FIRST22 legal only with COUNT0/direction-1: that operation performs
zero DMA and permits the bottommost known-empty suffix deletion. The complete
3125-plan component gate proves this is the only extra accepted tuple. Unknown
offscreen exposure, selection/folds/pan, Full geometry and actual CR edits still
fall back. This does not complete structural typing performance.

R24 is3983bytes; C33 CODE/RODATA endsBEFD with2bytes before its BF00 font. No
new resident/BSS/ZP, asset, object or REU bank is allocated. It is combined with
the qualified R16 raster and same-call lexical batching; actual R25/C33 native
font/helper CRC witnesses are rebuilt against those genuine inputs.

CPU qualification uses the released source/pixel/packet/CRC/whole16MiB DMA,
provider/fault/compatibility/fold/stack oracles through
`tests/test_grid_geometry_current.py`. The earlier private source release and
limits are in `../probes/row-geometry/full/README.md`; its FIRST22 refusal is
superseded by the separately qualified zero-suffix extension.

Paired nativePAL on the combined59 build, with identical PNGs:

| Operation | Control cycles | Geometry cycles |
| --- | ---: | ---: |
| 60 new wrapped row |1828397|979343|
| 60 BACK removes row |1869966|794142|
| 80 new wrapped row |1437075|780418|
| 80 BACK removes row |1486065|834053|

The gain is43.9–57.5%; overlay loads remain9. Return split/merge stays within
0.02% of fallback, about1.73–2.55million PAL cycles. These timings use the
documented instruction-entry PC/SP seam, not physical-key latency. Eight
control and eight candidate frames plus eleven combined source/settings/preview
frames were directly reviewed at1:1. Native evaluation retains exact source,
history, all59 capsules, fonts and the1024-byte ReadyOS reserve. The presentation
gate uses its existing typed53 initial-allocation/immutable-retained-arena oracle.

The native candidate itself succeeded. Its first host-output copy ran out of
disk space; the complete ended runtime was recovered by exact hash-linked copy
and the unchanged evaluator rerun offline. No product execution was repeated or
oracle weakened. New captures use `tools/closed_runtime_copy.py` to share only
successful closed-run output. Ordinary C64 responsiveness remains open.
