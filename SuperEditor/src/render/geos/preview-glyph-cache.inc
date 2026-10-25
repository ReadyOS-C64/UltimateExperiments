.ifndef SE_PREVIEW_GLYPH_CACHE_ABI
SE_PREVIEW_GLYPH_CACHE_ABI=1
; Exact optional R23 allocation within current typed FE; no new bank.
PGC_VERSION=3
PGC_BASE=$EB69
PGC_END=$FBA9
PGC_BYTES=4160
.assert PGC_END-PGC_BASE=PGC_BYTES,error,"glyph cache extent"
.assert PGC_END<=$10000,error,"glyph cache outside FE"
.endif
