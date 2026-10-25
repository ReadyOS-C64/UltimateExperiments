# Released private R21 per-glyph raster hoist

Promote only `row.s`, `glyph.s`, `measure.s` to their matching
`src/render/geos/literal-byte/` names, or apply `ready.patch` to180626 source.
`assets.s` is unchanged. No root/Make/catalog/config/API addition is needed.
FontABF3, widthsAEDB, tailhelperAF5B and entryA010 remain fixed.
Payload4086→4094,2 bytes spare. Existing704B caller frame only, no additional
fields/state/BSS/ZP/REU allocation. The already-existing dead validation work
word P+26..27 temporarily holds the aligned first glyph bitmap-byte pointer.

For the existing full-horizontal, whole-glyph byte path, coverage depends
only on glyphadvance and xphase, so it is shifted once per glyph instead of
once per scanline. The same mask feeds every fragment, including inverse and
selection/caret union; base ink continues to drive saturating role votes.
The first bitmap-byte base is likewise computed once, then each visible
scanline uses baseORsy (base is8-byte aligned, sy0..7). The tile index remains
the same across a glyph; the original histogram_address still rebinds it per
scanline. Signed/partial glyphs use the original slow pixel path.

Fit reclaimed only known unreachable prefix entries12..16 (advance<=11 after
width/style guards), four old paddingNOPs, and50 bytes of rowbase tables in
favor of exact validated row0..24 arithmetic. The unchanged eight-byte expected
fontheader moved from prefontRODATA to the available tail after rowhelpers;
its full check remains. No font content or source authority is inferred or
cached, and no validation was hoisted across service yields.

```
python3 tests/test_geos_raster_loop_candidate.py --suite fit
python3 tests/test_geos_raster_loop_candidate.py --suite component
python3 tests/test_geos_raster_loop_candidate.py --suite component --variant control
python3 tests/test_geos_raster_loop_candidate.py --suite inline
python3 tests/test_geos_raster_loop_candidate.py --suite fold
python3 tests/test_geos_raster_loop_candidate.py --suite incremental
python3 src/render/geos/raster-loop-candidate/package.py
```

Terminal2570strip/65fault candidate and byte-identicalcontrol yield the same
aggregate479721386e237ace5a0f7f96c47465446cb45af5500bd4a7ee5df38dbce4dd28.
All256bytes/4styles/8flag combinations, allroles/ties/saturation/append,
signedclips, descenders, malformedfonts/frames and whole64KiB/16MiB guards
remain. Public19inline+28fold+15incremental, actual48+7helper stack52+16 pass.
Native matched TOP0 current180626 public-render cycles:
11,262,419→11,025,764 (-236,655/-2.10%). R21self4,747,806→4,512,143;
servicepeak412,471→378,716. Loads118/calls967/DMAs652 unchanged; DMAbytes+32
from8B largerR21 across4loads. Exact native PNG unchanged, directly reviewed.
PC/SP stopwatch seam and IRQs are explicit; this is not physical input latency.

Isolated prose98395→91827instr(-6.7%), dense155584→146728(-5.7%),
nativefallback110165→102971(-6.5%). Partial clip172295→172641(+0.20%) retains
its conservative slow path. Blank+10instr. No latency-completion claim:
fullrebuild remains11M cycles. `coverage-only-row.s` is an intermediate2%-R21
variant retained for comparison, not a promotion source.
