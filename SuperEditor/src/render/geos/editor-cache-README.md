# GEOS editor packet ABI2

The live page cache is a derived logical REU allocation owned by `$FE`.
It holds a64-byte authenticated header and22 slots of2048bytes beginning at
bank offset `$0200`. Source/history/clipboard remain separate canonical objects.
The ReadyOS reservation `$C600-$C9FF` is never part of this storage.

Header VERSION is2. `editor.inc` is the authoritative byte-level definition.
Each slot has a32-byte prefix and these arrays:

| Field | Offset | Capacity |
| --- | ---: | ---: |
| Native source characters |32 |161 bytes |
| GG styles |194 |161 bytes |
| Semantic roles |356 |161 bytes |
| Clipped pixel-X boundaries |518 |162 words |
| Canonical LEFT boundaries |842 |162 24-bit values |
| Canonical RIGHT boundaries |1328 |162 24-bit values |

The slot uses1814 of2048bytes. A one-pixel pan over2pxglyphs can expose161
intersecting glyphs, with a partial glyph at each edge. Counting only160 fully
contained glyphs is insufficient. Full source offsets are24bit.

Prefix24 contains a signed16-bit first-glyph raster origin. Hit maps remain
clipped to0..320. Prefix26 records canonical caret membership; prefix18/19
records horizontal visibility and viewportX, zero when invalid. Header45 is
horizontal caret visibility, independent of header41's canonical membership.
Prefix27/28 describes the virtual end-space's viewport intersection and signed
origin; CR/EOF eligibility is checked separately before painting. Body selection
must never depend on whether the line's end is onscreen.

`se_gc_width` is `$FF XOR se_r_presentation`, separating source and future
rendered cache identity. Presentation currently initializes to source0; exposing
rendered editing still requires the complete source-mapped command path.

C21 owns page production. C20 measures merged source through R14 snapshots;
C24/C25/C26 provide block/lexical/inline analysis through resident continuation.
C22 paints physical strips; R21 provides proportional glyph rasterization.
C16 operation4 draws the existing logical ReadyOS chrome. C21 releases owner4
and requests that operation through the resident pump. FILEowner1 routes from
resident directly to C16 so its phase at `$8D00-$917F` is never overwritten by
GEOS request fields. No C-slot entry pointer survives a C-slot swap.

The conditional sparse geometry in `line-rendered.s` has a private proof but is
not yet connected to the production frontend. It uses a loaned24-bit glyph
ledger in the inactive source-style plan. `inline.s` already emits a complete-
body hidden-marker bitset in addition to the unchanged style/role outputs.
Neither primitive alone makes rendered editing complete.
