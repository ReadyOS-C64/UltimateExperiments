; Bounded glyph-plane transform: underlying ink before selection/caret union.
.setcpu "6502"
.include "render/geos/underline.inc"
.export se_geos_underline
.segment "CODE"
se_geos_underline:
    stx se_gg_context
    sty se_gg_context+1
    ldy #GG_STYLE
    lda (se_gg_context),y
    cmp #8
    bcs argument
    and #GG_UNDERLINE
    beq zero
    ldy #GG_VALID
    lda (se_gg_context),y
    cmp #2
    bne argument
    ldy #GG_HEIGHT
    lda (se_gg_context),y
    cmp #10
    bcs argument
    ldy #GG_BASELINE
    lda (se_gg_context),y
    clc
    adc #1
    bcs zero
    ldy #GG_HEIGHT
    cmp (se_gg_context),y
    bcs zero
    asl
    clc
    adc #GG_INK
    tax
    ldy #GG_REVERSE
    lda (se_gg_context),y
    bne inverse
    txa
    clc
    adc #GG_COVERAGE-GG_INK
    tay
    lda (se_gg_context),y
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    sta se_gg_pointer+1
    jmp paint
inverse:
    lda #0
    sta se_gg_pointer
    sta se_gg_pointer+1
paint:
    txa
    tay
    lda se_gg_pointer
    sta (se_gg_context),y
    iny
    lda se_gg_pointer+1
    sta (se_gg_context),y
zero:
    lda #0
    clc
    rts
argument:
    lda #GG_ARGUMENT
    sec
    rts
