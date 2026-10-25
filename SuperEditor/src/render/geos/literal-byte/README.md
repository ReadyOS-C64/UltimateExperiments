# Literal R21 byte renderer

Production-only R21 specializations of row, measure and glyph. Generic glyph
consumers continue to use the parent sources. The row caller proves fixed
encoding/full clip; font/header/width/selected span/style checks remain. Partial
or signed clipping retains the fallback compositor. Ink counts precede selection
union; saturation/ties and attribute voting are unchanged.

`cfg/geos-editor-row.cfg` fixes packedfontABF3, widthsAEDB and fasttailAF5B.
Payload4086, no new BSS/ZP. Release proof:2,570 strip vectors/65 faults and130
public frames; actual production PAL+NTSC native19 each passed at resident
4e64d113. Final stack still77 bytes including IRQ/NMI and BASIC entry.

The strip-height version generates only glyph raster rows intersecting the
current physical strip. Full glyph font/width/style/span validation still runs;
the row retains signed clipping, base-ink histogram, selection union and color
arbitration. The attribute-row base is derived once from the certified bitmap
rowbase, replacing50bytes of tables. No new scratch/state is introduced and
R21 remains4086 with the same font and tail addresses. This R21-private glyph
is not a replacement for the generic full-GG glyph API. Native matched TOP0
full paint12,258,205→11,533,248PALcycles, with identical118loads/1015calls/DMAs
and PNG; this modest raster gain does not close full-page/reflow performance.
