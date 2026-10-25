; R23 variable-font glyph operation. Stage refills happen AFTER this image is
; admitted, before any font pointer is dereferenced; no R->C nesting.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/preview.inc"
.include "render/geos/settings.inc"
.include "render/geos/catalog-glyph.inc"
.include "render/geos/font-store.inc"
.exportzp se_gg_context,se_gg_pointer
se_gg_context=text_ptr
se_gg_pointer=screen_ptr
F=PP_GLYPH
.segment "CODE"
 OVL_BINDING
.export entry
.import se_geos_catalog_ink_preview
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda #0
 sta F+CG_ENCODING
 sta F+CG_LEFT
 sta F+CG_TOP
 lda PP_INVERSE
 sta F+CG_FLAGS
 lda #32
 sta F+CG_RIGHT
 lda #24
 sta F+CG_BOTTOM
 lda #<$4800
 sta F+CG_NATIVE
 lda #>$4800
 sta F+CG_NATIVE+1
 lda PP_VALUE
 sta F+CG_VALUE
 lda PP_STYLE
 sta F+CG_STYLE
 lda PP_PROFILE+SES_ORIGIN
 bne catalog
 lda PP_PROFILE+SES_FAMILY
 cmp #SES_BUILTIN_NATIVE
 bne builtin
 lda #0
 sta F+CG_FONT
 sta F+CG_FONT+1
 sta F+CG_LENGTH
 sta F+CG_LENGTH+1
 beq raster
builtin:
 lda #2
 sta $CBD0
 lda #$FF
 sta $CBD1
 sta $CBD2
 lda #9
 sta $CBD3
 bne fetch
catalog:
 sta $CBD0
 lda PP_PROFILE+SES_FAMILY
 sta $CBD1
 lda PP_PROFILE+SES_FAMILY+1
 sta $CBD2
 lda PP_PROFILE+SES_POINT_SIZE
 sta $CBD3
fetch:
 jsr se_gf_fetch_preview
 bcs done
 lda #<$5000
 sta F+CG_FONT
 lda #>$5000
 sta F+CG_FONT+1
 lda $CBD8
 sta F+CG_LENGTH
 lda $CBD9
 sta F+CG_LENGTH+1
raster:
 ldx #<F
 ldy #>F
 jsr se_geos_catalog_ink_preview
 bcs done
 ; Inline and block code always retain the chosen font's fixed advance.
 ; Procedural styles are clipped into that cell rather than widening columns.
 lda PP_ROLE
 cmp #4
 beq fixed
 lda PP_CODE
 beq success
fixed:
 lda F+CG_WIDTH
 sta F+CG_ADVANCE
success:
 clc
done:
 rts
busy:
 lda #$B2
 sec
 rts
