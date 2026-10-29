.ifndef SE_PRESENTATION_API
SE_PRESENTATION_API=1
; Session capabilities, separate from the immutable64-byte font settings ABI.
; Zero is genuine raw source; nonzero admits structural formatting.
RENDER_PLAIN=0
RENDER_MARKDOWN=1
RENDER_FULL=3
RENDER_STRUCTURE=1
RENDER_CODE_COLOR=2
; Internal raw-layout context, NEVER an output kind claimed by C24's parser.
; C20/C21 already reserve kinds>=4 for literal, non-inline input.
GS_RAW_SOURCE_KIND=9
.global se_render_caps,se_ef_visible
.endif
