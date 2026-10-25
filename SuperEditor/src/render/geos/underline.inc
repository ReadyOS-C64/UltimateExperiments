.ifndef SE_GEOS_UNDERLINE_API
SE_GEOS_UNDERLINE_API=1
.include "render/geos/api.inc"
.ifndef GG_UNDERLINE
GG_UNDERLINE=$04           ;style bit2; bold1/italic2 remain metric bits
.endif
.global se_geos_underline
; X/Y is the existing77B caller-owned GG frame after successful actual glyph.
; The transform uses GG_STYLE bit2, GG_VALID2, BASELINE, HEIGHT, REVERSE and
; already clipped COVERAGE. No new BSS/ZP; clobbers the existing borrowed
; se_gg_context/se_gg_pointer pairs and A/X/Y. Foreground/non-reentrant as GG.
; Styles0..3 return success without writing the frame, even its scratch bytes.
; Underline styles4..7 replace exactly the two INK bytes at baseline+1 only if
; row<HEIGHT<=9. Normal becomes clipped advance coverage; explicit inverse
; becomes zero. This equals OR(raw ink,underline) BEFORE inverse and clipping.
; Row compositor must then vote this underlying ink and union selection/caret
; XOR once as usual. Advance/width/style/coverage/metrics remain unchanged.
; Current measure/glyph accept only0..3: until their admission changes, caller
; must draw with style&3 then restore fullstyle before this post-glyph operation.
; An invalid style/raster/height returns GG_ARGUMENT/Cset without frame writes;
; underline row outside HEIGHT (including baseline255 overflow) is a safe no-op.
; A0/Cclear success. No markup grammar or frontend integration is implied.
.endif
