; Internal R21 glyph raster with its validated, fixed caller-owned GG frame.
.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.include "render/geos/row.inc"
G=GEOS_ROW_FRAME+GR_GLYPH
.import gg_format,se_geos_packed
.importzp se_gg_context
.export se_geos_glyph
.segment "CODE"
se_geos_glyph:
    jsr se_geos_measure
    bcc :+
    rts
:   lda G+GG_KIND
    beq packed
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
    lda #1
    sta G+GG_SHIFT
    jmp prepare_masks
packed:
    ; The admitted in-slot BSW9 index is immutable.  Fetch only the live
    ; two-byte bit offset; GG_START/GG_END are private dead outputs.
    lda G+GG_INDEX
    asl
    tax
    lda se_geos_packed+8,x
    sta se_gg_pointer
    lda se_geos_packed+9,x
    sta se_gg_pointer+1
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
:   lda #60
    sta G+GG_SHIFT
prepare_masks:
    ; Keep the row source in the other existing R21 zero-page pair.  The
    ; compositor does not consume its histogram pointer until glyph returns.
    lda se_gg_pointer
    sta se_gg_context
    lda se_gg_pointer+1
    sta se_gg_context+1
    ldx G+GG_ADVANCE
    lda prefix_hi,x
    sta G+GG_CELL_HI
    lda prefix_lo,x
    sta G+GG_CELL_LO
    lda #0
    sta G+GG_ROW
next_row:
    ; R21 fixes strip origin=0, top=0 and bottom=9 for this internal decoder.
    lda #0
    sta G+GG_WORD_HI
    sta G+GG_WORD_LO
    lda G+GG_KIND
    beq @bsw
    lda G+GG_ROW
    cmp #8
    beq styles
    ldy #0
    lda (se_gg_context),y
    sta G+GG_WORD_HI
    jmp styles
@bsw:
    ldy #0
    lda (se_gg_context),y
    sta G+GG_WORD_HI
    lda G+GG_PHASE
    clc
    adc G+GG_WIDTH
    cmp #9
    bcc @one_byte
    ldy #1
    lda (se_gg_context),y
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
    lsr
    bcc @plain_or_italic
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
    lda G+GG_STYLE
    lsr
@plain_or_italic:
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
    lda G+GG_SHIFT
    clc
    adc se_gg_context
    sta se_gg_context
    bcc :+
    inc se_gg_context+1
:   inc G+GG_ROW
    lda G+GG_ROW
    cmp #9
    jcc next_row
    ; Preserve the former completed frame value exactly.
    lda se_gg_context
    sta G+GG_ROW_POINTER
    lda se_gg_context+1
    sta G+GG_ROW_POINTER+1
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
