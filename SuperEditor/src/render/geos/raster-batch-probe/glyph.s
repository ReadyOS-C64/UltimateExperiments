; Internal R21 glyph raster with its validated, fixed caller-owned GG frame.
.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.include "render/geos/row.inc"
G=GEOS_ROW_FRAME+GR_GLYPH
STRIP_ORIGIN=GEOS_ROW_FRAME+GR_PRIVATE+3
.import gg_pointer,gg_save_pointer,gg_format
.export se_geos_glyph
.segment "CODE"
se_geos_glyph:
    jsr se_geos_measure
    bcc :+
    rts
:   lda G+GG_KIND
    jeq packed
    lda #0
    sta se_gg_pointer+1
    lda G+GG_SCREEN
    asl
    rol se_gg_pointer+1
    asl
    rol se_gg_pointer+1
    asl
    rol se_gg_pointer+1
    sta se_gg_pointer
    lda G+GG_NATIVE
    clc
    adc se_gg_pointer
    sta se_gg_pointer
    lda G+GG_NATIVE+1
    adc se_gg_pointer+1
    sta se_gg_pointer+1
    ldy #GG_ROW_POINTER
    jsr gg_save_pointer
    jmp prepare_masks
packed:
    lda G+GG_INDEX
    asl
    clc
    adc #8
    sta se_gg_pointer
    lda #0
    sta se_gg_pointer+1
    lda G+GG_FONT
    clc
    adc se_gg_pointer
    sta se_gg_pointer
    lda G+GG_FONT+1
    adc se_gg_pointer+1
    sta se_gg_pointer+1
    lda se_gg_pointer
    sec
    sbc #GG_START
    sta se_gg_pointer
    bcs :+
    dec se_gg_pointer+1
:   ldy #GG_START
@index:
    lda (se_gg_pointer),y
    sta G,y
    iny
    cpy #GG_END+2
    bcc @index
    lda G+GG_END+1
    cmp #2
    jcs gg_format
    cmp #1
    bne @range_ok
    lda G+GG_END
    cmp #$E1
    jcs gg_format
@range_ok:
    ldy #GG_START
    jsr gg_pointer
    lda G+GG_END
    sec
    sbc se_gg_pointer
    sta G+GG_TEMP
    lda G+GG_END+1
    sbc se_gg_pointer+1
    jne gg_format
    lda G+GG_WIDTH
    cmp G+GG_TEMP
    jne gg_format
    lda se_gg_pointer
    and #7
    sta G+GG_PHASE
    .repeat 3
        lsr se_gg_pointer+1
        ror se_gg_pointer
    .endrepeat
    lda G+GG_FONT
    clc
    adc se_gg_pointer
    sta se_gg_pointer
    lda G+GG_FONT+1
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
    ldx G+GG_ADVANCE
    lda prefix_hi,x
    sta G+GG_CELL_HI
    lda prefix_lo,x
    sta G+GG_CELL_LO
    lda #0
    sta G+GG_ROW
next_row:
    lda STRIP_ORIGIN
    clc
    adc G+GG_ROW
    ldx STRIP_ORIGIN
    bpl @positive
    bcc @skip_invisible
@positive:
    cmp GEOS_ROW_FRAME+GR_TOP
    bcc @skip_invisible
    cmp GEOS_ROW_FRAME+GR_BOTTOM
    bcc @visible
@skip_invisible:
    jmp advance_row
@visible:
    lda #0
    sta G+GG_WORD_HI
    sta G+GG_WORD_LO
    lda G+GG_KIND
    beq @bsw
    lda G+GG_ROW
    cmp #8
    beq styles
    ldy #GG_ROW_POINTER
    jsr gg_pointer
    ldy #0
    lda (se_gg_pointer),y
    sta G+GG_WORD_HI
    jmp styles
@bsw:
    ldy #GG_ROW_POINTER
    jsr gg_pointer
    ldy #0
    lda (se_gg_pointer),y
    sta G+GG_WORD_HI
    lda G+GG_PHASE
    clc
    adc G+GG_WIDTH
    cmp #9
    bcc @one_byte
    ldy #1
    lda (se_gg_pointer),y
    sta G+GG_WORD_LO
@one_byte:
    ldx G+GG_PHASE
    beq phase_width_mask
    ; Select a fixed shift chain, as used by the GEOS font renderer.
    ; The source pointer is dead after the one/two-byte row fetch.
    lda phase_lo,x
    sta se_gg_pointer
    lda #>phase7
    sta se_gg_pointer+1
    lda G+GG_WORD_HI
    jmp (se_gg_pointer)
phase7: asl G+GG_WORD_LO
    rol
phase6: asl G+GG_WORD_LO
    rol
phase5: asl G+GG_WORD_LO
    rol
phase4: asl G+GG_WORD_LO
    rol
phase3: asl G+GG_WORD_LO
    rol
phase2: asl G+GG_WORD_LO
    rol
phase1: asl G+GG_WORD_LO
    rol
phase0:
    sta G+GG_WORD_HI
    .assert >phase7=>phase0,error,"phase dispatch crosses a page"
phase_width_mask:
    ldx G+GG_WIDTH
    lda prefix_hi,x
    and G+GG_WORD_HI
    sta G+GG_WORD_HI
    lda #0
    sta G+GG_WORD_LO
styles:
    lda G+GG_STYLE
    and #GG_BOLD
    beq @italic
    lda G+GG_WORD_HI
    lsr
    sta se_gg_pointer
    lda G+GG_WORD_LO
    ror
    ora G+GG_WORD_LO
    sta G+GG_WORD_LO
    lda se_gg_pointer
    ora G+GG_WORD_HI
    sta G+GG_WORD_HI
@italic:
    lda G+GG_STYLE
    and #GG_ITALIC
    beq @inverse
    lda G+GG_ROW
    cmp #6
    bcs @inverse
    ldx #1
    cmp #3
    bcs @slant
    inx
@slant:
    lsr G+GG_WORD_HI
    ror G+GG_WORD_LO
    dex
    bne @slant
@inverse:
    lda G+GG_REVERSE
    beq @store
    lda G+GG_CELL_HI
    eor G+GG_WORD_HI
    sta G+GG_WORD_HI
    lda G+GG_CELL_LO
    eor G+GG_WORD_LO
    sta G+GG_WORD_LO
@store:
    lda G+GG_ROW
    asl
    tax
    lda G+GG_WORD_HI
    sta G+GG_INK,x
    lda G+GG_WORD_LO
    sta G+GG_INK+1,x
advance_row:
    lda G+GG_KIND
    bne @native_advance
    lda #60
    bne @advance
@native_advance:
    lda #1
@advance:
    clc
    adc G+GG_ROW_POINTER
    sta G+GG_ROW_POINTER
    bcc :+
    inc G+GG_ROW_POINTER+1
:   inc G+GG_ROW
    lda G+GG_ROW
    cmp #9
    jcc next_row
    lda #2
    sta G+GG_VALID
    lda #0
    clc
    rts
.segment "RODATA"
phase_lo: .byte <phase0,<phase1,<phase2,<phase3,<phase4,<phase5,<phase6,<phase7
prefix_hi:
.repeat 12,I
 .if I=0
    .byte 0
 .else
    .byte (($FFFF<<(16-I))>>8)&255
 .endif
.endrepeat
prefix_lo:
.repeat 12,I
 .if I=0
    .byte 0
 .else
    .byte ($FFFF<<(16-I))&255
 .endif
.endrepeat
