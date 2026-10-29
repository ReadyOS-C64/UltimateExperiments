# Private R21 next raster measurement

Source-released **vertical** candidate, frozen against canonical54 fixture
`build/cache-editor-product/20261026T045019460982Z/fixture`. No canonical edits,
shared build, added asset, native run or general performance completion claim.

Promotable files: `row.s`, `measure.s`, `glyph.s` in this directory, replacing
only their `src/render/geos/literal-byte/` counterparts after parent review.
Assets, row-fast.s, generic row-validate.s and linker configuration stay exact.
The generic measure/glyph/row APIs are unchanged. `build.py` reproduces both the
byte-identical packaged control and private candidate from the frozen ZIP.

```
python3 tests/test_geos_raster_next.py --variant vertical --full --fixture FIXTURE
python3 tests/test_geos_raster_next.py --variant vertical --public --fixture FIXTURE
```

Both payloads remain4094B. PackedfontABF3, widthsAEDB, fasttailAF5B and every
font byte match the packaged control. Candidate raw SHA256 is
`550e7bd933d21ecdd4fbc11c5aceedfb68dcf76517746f835a834db249742cfa` on this binding.
No BSS/ZP or retained5000 scratch is added. One previously unused caller-private
byte P+41 (`GR_PRIVATE+41`, inside the existing704B frame) is transient.

## Change and proof

The real glyph service already rasterizes only rows intersecting the physical
strip. The compositor was nevertheless repeating signed origin arithmetic and
both clip tests for every glyph scanline. It now intersects the legal origin
-8..7, TOP/BOTTOM0..8 with glyph rows0..8 once per glyph:

- start=max(TOP-origin,0), end=min(BOTTOM-origin,9);
- empty intersections still consume the glyph/advance/map exactly as before;
- nonempty rows increment sy/gy directly, never read an ungenerated ink row.

Horizontal clipping/byte paths, complete560-byte saturating histograms, role
priority/ties, inverse-before-selection union, append and maps are unchanged.
Safe compactions fund the code: ca65-proven short branches in the three R21
private modules; glyph's actual A0 success removes a redundant LDA0; the
0..4+0..4 nibble sum proves carry clear before histogram ADC; TAX/TAY/TXA
replaces PHA/TAX/PLA in that nibble lookup. No JSR depth is added; the lookup
removes one temporary pushed byte. All guards remain. `short-branches.json`
records exact assembled branch changes. Generic row-validate.s is byte-unchanged.

Final component run `20261026T051922494191Z` passes2570 independent strip vectors
and65 fault cases **per side**, plus720 exhaustive legal vertical intersections
per side (all16 origins and45 TOP/BOTTOM pairs). Every pixel, attribute, map,
saturating vote, full64KiB RAM outside declared outputs and whole16MiB REU is
checked. Coverage includes all256 inputs/four styles/eight flags, signed/partial
edges, ninth rows, native fallback, saturated appends/ties, foreign owners,
malformed frames/fonts/widths and deliberate map/style alias corruption.

Final actual renderer run `20261026T052012037062Z` substitutes only the sealed
private R21 in a cloned actual54 fixture; default control reassembly must equal
the packaged SEO. The real public BOTTOM then TOP/render route on422 bytes
passes six independent full-VIC frames with source/history/catalog/shim and
precise checked-DMA whole16MiB guards. Loads/DMA and output hashes agree.

|Actual TOP interval|Control instructions|Candidate instructions|Reduction|
|---|---:|---:|---:|
|Plain|1,713,303|1,663,204|2.924%|
|Markdown|2,601,059|2,562,976|1.464%|
|Full|2,725,382|2,687,299|1.397%|

Component prose62543=>60331, two-run64225=>61198, partial148678=>146465;
blank4331=>4330. These are CPU instruction counts, **not PAL/NTSC cycles**.
Peddle's cycle counter is unavailable here; no cycle inference is emitted.
The native styled-TOP R21 self cost motivated this probe, but no native speedup
is claimed until the parent independently measures a promoted build.

## Bounded rejected alternatives

`--variant uniform` implements an exact OR/AND actual-role witness and a safe
one-role election shortcut. It passes2570+65 per side and fits4094 after
compaction, but favors colored rows (3–5%) while blank costs103 extra instructions
and ordinary prose is nearly flat. It is not recommended over vertical.

`--variant vertical-zero` skips zero-fragment histogram additions. Its nine
independent component probes match, but the extra branch regresses common prose
and heading relative to vertical; it is not released for promotion. No guards
were dropped to fit either experiment. Historical source/build runs are retained.

The released improvement is modest: it removes repeated clipping work, not the
remaining per-glyph decode/byte population cost. It does not close full-page or
structural-navigation usability.
