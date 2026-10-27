; Internal R21-only measurement: its row entry already certifies fixed GG frame.
.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.include "render/geos/row.inc"
G=GEOS_ROW_FRAME+GR_GLYPH
.import se_petscii_screen,se_geos_packed
HEADER_OK=GEOS_ROW_FRAME+GR_PRIVATE+38
.export se_geos_measure,gg_pointer,gg_save_pointer,gg_format
.segment "CODE"
se_geos_measure:
    lda G+GG_STYLE
    cmp #4
    jcs argument
    lda HEADER_OK
    bne @header_ready
    lda G+GG_FONT
    sta se_gg_pointer
    lda G+GG_FONT+1
    sta se_gg_pointer+1
    ldy #0
@header:
    lda (se_gg_pointer),y
    cmp header,y
    jne gg_format
    iny
    cpy #8
    bcc @header
    ; Only the in-slot asset is immutable under all certified row output spans.
    ; Other readable RAM fonts may alias caller maps and retain every check.
    lda se_gg_pointer
    cmp #<se_geos_packed
    bne @header_ready
    lda se_gg_pointer+1
    cmp #>se_geos_packed
    bne @header_ready
    inc HEADER_OK
@header_ready:
    lda G+GG_FLAGS
    and #1
    sta G+GG_REVERSE
    lda G+GG_VALUE
    jsr se_petscii_screen
    sta G+GG_SCREEN
    cmp #1
    bcc @at
    cmp #27
    bcc @lower
    beq @bracket
    cmp #29
    beq @bracket
    cmp #32
    bcc @fallback
    cmp #64
    bcc @ordinary
    cmp #65
    bcc @fallback
    cmp #91
    bcs @fallback
@ordinary:
    sec
    sbc #32
    jmp @mapped
@at:
    lda #32
    bne @mapped
@lower:
    clc
    adc #64
    bne @mapped
@bracket:
    clc
    adc #32
@mapped:
    sta G+GG_INDEX
    lda #0
    beq @kind
@fallback:
    lda #1
@kind:
    sta G+GG_KIND
    lda G+GG_WIDTHS
    sta se_gg_pointer
    lda G+GG_WIDTHS+1
    sta se_gg_pointer+1
    ldy G+GG_SCREEN
    lda (se_gg_pointer),y
    beq gg_format
    cmp #9
    bcs gg_format
    sta G+GG_WIDTH
    tax
    lda G+GG_KIND
    beq :+
    cpx #8
    bne gg_format
:   txa
    sta G+GG_ADVANCE
    lda G+GG_STYLE
    lsr
    bcc @italic
    inc G+GG_ADVANCE
@italic:
    lsr
    bcc @metrics
    inc G+GG_ADVANCE
    inc G+GG_ADVANCE
@metrics:
    lda #0
    clc
    rts
argument:
    lda #GG_ARGUMENT
    sec
    rts
gg_format:
    lda #GG_FORMAT
    sec
    rts
gg_pointer:
    lda G,y
    sta se_gg_pointer
    iny
    lda G,y
    sta se_gg_pointer+1
    rts
gg_save_pointer:
    lda se_gg_pointer
    sta G,y
    iny
    lda se_gg_pointer+1
    sta G,y
    rts
.segment "GEOS_ROW_FAST"
header: .byte 6,60,0,9,8,0,204,0
