# Private R21 physical-strip raster work avoidance — released

Promote **only** row.s and glyph.s to the corresponding literal-byte files.
measure.s/assets.s are unchanged copies of the immutable48 baseline. No Makefile,
API, catalog, resident, state or ZP change. ready.patch is against the exact frozen
171440 literal-byte sources. Rebuild R21 normally; payload remains4086B, packedfont
ABF3/widthsAEDB/helperAF5B unchanged. This consumes the former8B pre-font padding;
the helper still has10B tail room. On resident b33/binding1ecd the SEO SHA is
884428ddc7cd54b88b19f0f86acdfdbfd6fa3553331920358460bc3773f74071.

The R21-only glyph helper still validates style, exact font header, selected
index/span/order/width/fallback and metrics before rastering. Its caller already
validated the physical strip and signed logical origin. For each of the same
nine logical glyph rows it computes the same signed origin+row clipping predicate
as the compositor. Rows outside [TOP,BOTTOM) advance the original source-raster
pointer without reading/transforming/storing unused ink. Row index/italic phase,
native ninth row, consumed count, advance and source maps remain canonical. The
compositor only reads intersecting rows, so unpublished private INK bytes outside
the strip may retain old values. These are not a public GG raster output. The
initial unused-space glyph still performs every selected-font guard; its unused
raster may also be skipped. No lease, source or cache validity predicate changes.

The row resolver derives $4000+row*40 once from the certified bitmap rowbase,
using dead validation `ending` scratch P+30..31. This removes50B of attribute
lookup tables and their repeated indexed lookup. It funds the clipping code;
no new state is reserved. Row CODE+30, glyph CODE+28, RODATA-50: net8B, precisely
replacing old pre-font padding. No new call/stack edge.

Reproduce:
```
python3 tests/test_geos_strip_raster_candidate.py --variant control --suite component
python3 tests/test_geos_strip_raster_candidate.py --variant candidate --suite component
python3 tests/test_geos_strip_raster_candidate.py --suite inline
python3 tests/test_geos_strip_raster_candidate.py --suite fold
python3 tests/test_geos_strip_raster_candidate.py --suite incremental
```
All default to immutable combined48 fixture171440. Control must byte-reassemble
its sealed production R21. Both2570strip/65fault matrices passed, aggregate
bitmap/attrs/histograms hash479721386e237ace5a0f7f96c47465446cb45af5500bd4a7ee5df38dbce4dd28.
All64KiB RAM and16MiB backing guards retained. Public19inline+28fold+15incremental
passed independent source/style/layout/selection/pixels/history/REU guards.

A private native D81 replaced only R21, byte-compared all48 assets/resident and
then byte-reassembled that exact ZIP to the packaged candidate. Matched PAL TOP0
forcedfresh A/B:12,258,205→11,533,248 cycles (-724957/-5.91%). Both118loads,
1015calls,748DMA/444464bytes, CRC0. R21self5,472,033→4,747,496 (-13.24%). Native
finalPNG byte-identical. Unchanged finite48+7selector stack bound52+16 relativeidle.
These are stopwatch public-render PC/SP seams, not physical input latency. It is
a modest full-rebuild improvement; it does not eliminate the remaining11.5M
rebuild, high service peak, source/parser passes or overlay admissions.
