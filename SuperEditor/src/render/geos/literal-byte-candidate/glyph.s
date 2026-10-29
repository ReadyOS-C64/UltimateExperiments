; PRIVATE R21-only full GGclip; row applies actual strip clipping independently.
.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.import gg_pointer,gg_save_pointer,gg_format
.export se_geos_glyph
.segment "CODE"
se_geos_glyph:
    jsr se_geos_measure
    bcc :+
    rts
:   ldy #GG_KIND
    lda (se_gg_context),y
    jeq packed
    ; Native fallback is explicit128x8, sharing the existing mixed-case set.
    lda #0
    sta se_gg_pointer+1
    ldy #GG_SCREEN
    lda (se_gg_context),y
    asl
    rol se_gg_pointer+1
    asl
    rol se_gg_pointer+1
    asl
    rol se_gg_pointer+1
    sta se_gg_pointer
    ldy #GG_NATIVE
    lda (se_gg_context),y
    clc
    adc se_gg_pointer
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    adc se_gg_pointer+1
    sta se_gg_pointer+1
    ldy #GG_ROW_POINTER
    jsr gg_save_pointer
    jmp prepare_masks
packed:
    ldy #GG_INDEX
    lda (se_gg_context),y
    asl
    clc
    adc #8
    sta se_gg_pointer
    lda #0
    sta se_gg_pointer+1
    ldy #GG_FONT
    lda (se_gg_context),y
    clc
    adc se_gg_pointer
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    adc se_gg_pointer+1
    sta se_gg_pointer+1
    ; Bias for four consecutive start/end bytes copied into caller scratch.
    lda se_gg_pointer
    sec
    sbc #GG_START
    sta se_gg_pointer
    bcs :+
    dec se_gg_pointer+1
:   ldy #GG_START
@index:
    lda (se_gg_pointer),y
    sta (se_gg_context),y
    iny
    cpy #GG_END+2
    bcc @index
    ldy #GG_END+1
    lda (se_gg_context),y
    cmp #2
    jcs gg_format
    cmp #1
    bne @range_ok
    dey
    lda (se_gg_context),y
    cmp #$E1 ;end<=480 bits per packed raster row
    jcs gg_format
@range_ok:
    ldy #GG_START
    jsr gg_pointer
    ldy #GG_END
    lda (se_gg_context),y
    sec
    sbc se_gg_pointer
    ldy #GG_TEMP
    sta (se_gg_context),y
    ldy #GG_END+1
    lda (se_gg_context),y
    sbc se_gg_pointer+1
    jne gg_format
    ldy #GG_WIDTH
    lda (se_gg_context),y
    ldy #GG_TEMP
    cmp (se_gg_context),y
    jne gg_format
    lda se_gg_pointer
    and #7
    ldy #GG_PHASE
    sta (se_gg_context),y
    .repeat 3
        lsr se_gg_pointer+1
        ror se_gg_pointer
    .endrepeat
    ldy #GG_FONT
    lda (se_gg_context),y
    clc
    adc se_gg_pointer
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    adc se_gg_pointer+1
    sta se_gg_pointer+1
    lda se_gg_pointer
    clc
    adc #204
    sta se_gg_pointer
    bcc :+
    inc se_gg_pointer+1
:   ldy #GG_ROW_POINTER
    jsr gg_save_pointer
prepare_masks:
    ldy #GG_ADVANCE
    lda (se_gg_context),y
    tax
    lda prefix_hi,x
    ldy #GG_CELL_HI
    sta (se_gg_context),y
    lda prefix_lo,x
    iny
    sta (se_gg_context),y
@rows:
    lda #0
    ldy #GG_ROW
    sta (se_gg_context),y
next_row:
    lda #0
    ldy #GG_WORD_HI
    sta (se_gg_context),y
    iny
    sta (se_gg_context),y
    ldy #GG_KIND
    lda (se_gg_context),y
    beq @bsw
    ldy #GG_ROW
    lda (se_gg_context),y
    cmp #8
    beq styles ;same baseline, ninth native-fallback row is empty
    ldy #GG_ROW_POINTER
    jsr gg_pointer
    ldy #0
    lda (se_gg_pointer),y
    ldy #GG_WORD_HI
    sta (se_gg_context),y
    jmp styles
@bsw:
    ldy #GG_ROW_POINTER
    jsr gg_pointer
    ldy #0
    lda (se_gg_pointer),y
    ldy #GG_WORD_HI
    sta (se_gg_context),y
    ldy #GG_PHASE
    lda (se_gg_context),y
    ldy #GG_WIDTH
    clc
    adc (se_gg_context),y
    cmp #9
    bcc @one_byte
    ; Read a second source byte only when actual glyph bits cross a byte.
    ; Never read the next packed raster row or one byte past the asset.
    ldy #1
    lda (se_gg_pointer),y
    ldy #GG_WORD_LO
    sta (se_gg_context),y
@one_byte:
    ldy #GG_PHASE
    lda (se_gg_context),y
    tax
    beq @width_mask
@align:
    ldy #GG_WORD_LO
    lda (se_gg_context),y
    asl
    sta (se_gg_context),y
    dey
    lda (se_gg_context),y
    rol
    sta (se_gg_context),y
    dex
    bne @align
@width_mask:
    ldy #GG_WIDTH
    lda (se_gg_context),y
    tax
    lda prefix_hi,x
    ldy #GG_WORD_HI
    and (se_gg_context),y
    sta (se_gg_context),y
    lda #0 ;mappedBSW9 widths<=8: only the high source byte contains ink
    iny
    sta (se_gg_context),y
styles:
    ldy #GG_STYLE
    lda (se_gg_context),y
    and #GG_BOLD
    beq @italic
    ldy #GG_WORD_HI
    lda (se_gg_context),y
    lsr
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    ror
    sta se_gg_pointer+1
    ldy #GG_WORD_HI
    lda (se_gg_context),y
    ora se_gg_pointer
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    ora se_gg_pointer+1
    sta (se_gg_context),y
@italic:
    ldy #GG_STYLE
    lda (se_gg_context),y
    and #GG_ITALIC
    beq @inverse
    ldy #GG_ROW
    lda (se_gg_context),y
    cmp #6
    bcs @inverse
    ldx #1
    cmp #3
    bcs @slant
    inx
@slant:
    ldy #GG_WORD_HI
    lda (se_gg_context),y
    lsr
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    ror
    sta (se_gg_context),y
    dex
    bne @slant
@inverse:
    ldy #GG_REVERSE
    lda (se_gg_context),y
    beq @clip
    ldy #GG_CELL_HI
    lda (se_gg_context),y
    ldy #GG_WORD_HI
    eor (se_gg_context),y
    sta (se_gg_context),y
    ldy #GG_CELL_LO
    lda (se_gg_context),y
    ldy #GG_WORD_LO
    eor (se_gg_context),y
    sta (se_gg_context),y
@clip:
    ; R21 consumes only INK, not GG_COVERAGE. Validated width/styles ensure
    ; every transformed bit lies within advance; private GGclip is full.
@store:
    ; R21-private route publishes only the ink plane consumed by the row.
    ldy #GG_ROW
    lda (se_gg_context),y
    asl
    clc
    adc #GG_INK
    clc
    adc se_gg_context
    sta se_gg_pointer
    lda se_gg_context+1
    adc #0
    sta se_gg_pointer+1
    ldy #GG_WORD_HI
    lda (se_gg_context),y
    ldy #0
    sta (se_gg_pointer),y
    ldy #GG_WORD_LO
    lda (se_gg_context),y
    ldy #1
    sta (se_gg_pointer),y
    ldy #GG_KIND
    lda (se_gg_context),y
    bne @native_advance
    lda #60
    bne @advance
@native_advance:
    lda #1
@advance:
    ldy #GG_ROW_POINTER
    clc
    adc (se_gg_context),y
    sta (se_gg_context),y
    bcc :+
    iny
    lda (se_gg_context),y
    adc #0
    sta (se_gg_context),y
:   ldy #GG_ROW
    lda (se_gg_context),y
    clc
    adc #1
    sta (se_gg_context),y
    cmp #9
    jcc next_row
    lda #2
    ldy #GG_VALID
    sta (se_gg_context),y
    lda #0
    clc
    rts
.segment "RODATA"
prefix_hi:
.repeat 17,I
 .if I=0
    .byte 0
 .else
    .byte (($FFFF<<(16-I))>>8)&255
 .endif
.endrepeat
prefix_lo:
.repeat 17,I
 .if I=0
    .byte 0
 .else
    .byte ($FFFF<<(16-I))&255
 .endif
.endrepeat
