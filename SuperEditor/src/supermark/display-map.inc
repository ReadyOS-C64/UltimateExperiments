.ifndef SE_SUPERMARK_DISPLAY_MAP
SE_SUPERMARK_DISPLAY_MAP=1
DM_START=0 ;absolute24-bit source origin
DM_LENGTH=3 ;0..128 source bytes
DM_EOF=4 ;1 completeEOF packet;0 requires final CR
DM_COLUMN=5 ;24-bit original logical column of body origin (0 at line start)
DM_BUSY=8
DM_VALID=9
DM_ERROR=10
DM_STAGE=11
DM_INDEX=12
DM_COUNT=13 ;visible glyph count0..128
DM_EVENTS=14
DM_WIDTH=15
DM_END=16 ;exclusive canonical source end
DM_TEMP=19 ;six scratch bytes
DM_SOURCE=25 ;canonical input boundary / output glyph-source byte anchor
DM_VISIBLE=28 ;visible boundary/glyph input; from_source output
DM_LEFT=29 ;minimum canonical boundary mapping to visible boundary
DM_RIGHT=32 ;maximum canonical boundary mapping to visible boundary
DM_LOW=35
DM_HIGH=36
DM_SPARE=37
DM_INPUT=40 ;128 immutable source bytes, caller-owned packet
DM_RAW=168 ;128-byte lossless ledger, preserves every hidden/control byte
DM_HIDDEN=296 ;128 flags:1 hidden proven delimiter/escape,0 visible rawbyte
DM_GLYPHS=424 ;128 native sourcebytes, never screen codes/CHROUT
DM_V2S=552 ;129 byte-offsets: glyph origins, followed by canonicalEOF offset
DM_S2V=681 ;129 prefixcounts: sourceboundaryoffset ->visibleboundary
DM_FRAME_SIZE=810
DM_RANGE=$B8
DM_STATE=$B1
DM_EVENT=$B2
; Caller-owned frame plus the existing complete inline-parser context. No
; resident BSS/ZP, reader, DMA, VIC, or document writes. Binary arithmetic.
; Scope: a COMPLETE single inline-eligible logical body line, <=128 bytes.
; Packet begins at real line/body origin; COLUMN from actual block body anchor.
; An arbitrary transport chunk is NOT complete evidence. CR permitted only as
; final byte; otherwise EOF must be1. Longer lines/unknown context stay literal
; in the caller until a streaming complete-line consumer is integrated.
; Actual se_si PAIR descriptors hide only matched opening/closing delimiters;
; confirmed ESCAPE hides only £, leaving escaped byte literal. Unsupported,
; unmatched, incomplete, graphics/control bytes remain native literal data.
; Heading/list/fence prefix removal is NOT implemented by this inline primitive.
;
; BEGIN validates bounds/complete-packet contract, resets inline state and marks
; outputs unpublished. STEP processes <=one sourcebyte plus one bounded parser
; event (<=6 hide flags), or <=one composition byte. <=2*N+2 STEPs; A1pending,
; A0done/Cclear. Errors Cset/Acode, VALID0; INPUT remains unchanged. BUSY BEGIN
; refuses without replacing the active mapping. Callers own source lifetime and
; full identity; never reuse a map after source mutation without rebuilding.
;
; FROM_SOURCE consumes absolute SOURCE boundary in [START,END], outputs VISIBLE.
; FROM_VISIBLE consumes boundary0..COUNT, outputs LEFT/RIGHT canonical preimage.
; Hidden runs map many source boundaries to one visible boundary: forward/right
; affinity chooses RIGHT, backward/left chooses LEFT. Typing at RIGHT of final
; closing markers inserts outside that span; LEFT inserts before closing marks.
; GLYPH consumes glyphindex0..COUNT-1, outputs SOURCE anchor to exactly one raw
; canonicalbyte. ForwardDelete at boundary k targets GLYPH(k); Backspace targets
; GLYPH(k-1). Hidden delimiter bytes are never implicitly deleted. Reparsing may
; make an emptied/malformed span literal. Selection/clipboard stays canonical;
; affinity must remain explicit in a later editor integration.
; Queries bounded by <=129 source boundaries. Cclear/A0 success; invalid query
; leaves published map and outputs intact (only scratch can change).
; Raw CR is a preserved line-break token in the visible stream, never a
; printed glyph/CHROUT; downstream layout consumes it as a row break.
; RAW+HIDDEN+GLYPHS+V2S reconstructs all canonical bytes, not just rendered text.
.import se_dm_frame
.ifndef SE_DISPLAY_MAP_IMPLEMENTATION
.import se_dm_begin,se_dm_step,se_dm_from_source,se_dm_from_visible,se_dm_glyph
.endif
.endif
