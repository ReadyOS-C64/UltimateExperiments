.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.import se_petscii_screen
.export se_geos_measure,gg_pointer,gg_save_pointer,gg_format
.segment "CODE"
se_geos_measure:
    stx se_gg_context
    sty se_gg_context+1
    lda #0
    ldy #GG_VALID
    sta (se_gg_context),y
    ldy #GG_ENCODING
    lda (se_gg_context),y
    cmp #2
    jcs argument
    iny
    lda (se_gg_context),y
    cmp #4
    jcs argument
    ldy #GG_CLIP_LEFT
    lda (se_gg_context),y
    cmp #17
    jcs argument
    iny
    lda (se_gg_context),y
    cmp #17
    jcs argument
    iny
    lda (se_gg_context),y
    cmp #10
    jcs argument
    iny
    lda (se_gg_context),y
    cmp #10
    jcs argument
    ldy #GG_FONT
    jsr gg_pointer
    ldy #0
@header:
    lda (se_gg_pointer),y
    cmp header,y
    jne gg_format
    iny
    cpy #8
    bcc @header
    ldy #GG_FLAGS
    lda (se_gg_context),y
    and #1
    ldy #GG_REVERSE
    sta (se_gg_context),y
    ldy #GG_ENCODING
    lda (se_gg_context),y
    beq @native
    ldy #GG_VALUE
    lda (se_gg_context),y
    bpl @normal
    lda #1
    ldy #GG_REVERSE
    sta (se_gg_context),y
    ldy #GG_VALUE
    lda (se_gg_context),y
@normal:
    and #$7F
    jmp @screen
@native:
    ldy #GG_VALUE
    lda (se_gg_context),y
    jsr se_petscii_screen
@screen:
    ldy #GG_SCREEN
    sta (se_gg_context),y
    ; Exact algorithmic mapping used by the existing verified extractor.
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
    ldy #GG_INDEX
    sta (se_gg_context),y
    lda #0
    beq @kind
@fallback:
    lda #1
@kind:
    ldy #GG_KIND
    sta (se_gg_context),y
    ldy #GG_WIDTHS
    jsr gg_pointer
    ldy #GG_SCREEN
    lda (se_gg_context),y
    tay
    lda (se_gg_pointer),y
    jeq gg_format
    cmp #9
    jcs gg_format
    ldy #GG_WIDTH
    sta (se_gg_context),y
    tax
    ldy #GG_KIND
    lda (se_gg_context),y
    beq :+
    cpx #8
    jne gg_format
:   txa
    ldy #GG_ADVANCE
    sta (se_gg_context),y
    ldy #GG_STYLE
    lda (se_gg_context),y
    and #GG_BOLD
    beq @italic
    ldy #GG_ADVANCE
    lda (se_gg_context),y
    clc
    adc #1
    sta (se_gg_context),y
@italic:
    ldy #GG_STYLE
    lda (se_gg_context),y
    and #GG_ITALIC
    beq @metrics
    ldy #GG_ADVANCE
    lda (se_gg_context),y
    clc
    adc #2
    sta (se_gg_context),y
@metrics:
    lda #6
    ldy #GG_BASELINE
    sta (se_gg_context),y
    lda #9
    iny
    sta (se_gg_context),y
    lda #1
    ldy #GG_VALID
    sta (se_gg_context),y
    lda #0
    clc
    rts
argument:
    lda #GG_ARGUMENT
    sec
    rts
gg_format:
    lda #0
    ldy #GG_VALID
    sta (se_gg_context),y
    lda #GG_FORMAT
    sec
    rts
gg_pointer:
    lda (se_gg_context),y
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    sta se_gg_pointer+1
    rts
gg_save_pointer:
    lda se_gg_pointer
    sta (se_gg_context),y
    iny
    lda se_gg_pointer+1
    sta (se_gg_context),y
    rts
.segment "RODATA"
header: .byte 6,60,0,9,8,0,204,0
