.setcpu "6502"
.include "render/narrow/api8.inc"
.export se_bitmap_cell8
.segment "CODE"
se_bitmap_cell8:
    stx se_bc_context
    sty se_bc_context+1
    ldy #BC_ROW
    lda (se_bc_context),y
    cmp #25
    bcs argument
    iny
    lda (se_bc_context),y
    cmp #40
    bcs argument
    ldy #BC_FOREGROUND
    lda (se_bc_context),y
    iny
    ora (se_bc_context),y
    cmp #16
    bcs argument
    iny
    lda (se_bc_context),y
    bne argument
    iny
    lda (se_bc_context),y
    and #$E3 ;A0,A4,...BC: readable1KiB glyph table outside fixed output
    cmp #$A0
    bne argument
    iny
    lda (se_bc_context),y
    bne argument
    iny
    lda (se_bc_context),y
    cmp #$60
    bne argument
    iny
    lda (se_bc_context),y
    bne argument
    iny
    lda (se_bc_context),y
    cmp #$40
    beq draw
argument:
    lda #BC_ARGUMENT
    sec
    rts
draw:
    ; Keep the glyph address on CPU stack while the other pointer computes
    ; the tile. Once all inputs are consumed, the context loan becomes source.
    ldy #BC_SCREEN
    lda (se_bc_context),y
    asl
    asl
    asl
    pha
    lda (se_bc_context),y
    lsr
    lsr
    lsr
    lsr
    lsr
    and #3
    ldy #BC_FONT+1
    clc
    adc (se_bc_context),y
    pha
    lda #$40
    sta se_bc_pointer+1
    ldy #BC_ROW
    lda (se_bc_context),y
    tax
    beq column
    lda #0
row:
    clc
    adc #40
    bcc :+
    inc se_bc_pointer+1
:
    dex
    bne row
column:
    ldy #BC_COLUMN
    clc
    adc (se_bc_context),y
    sta se_bc_pointer
    bcc :+
    inc se_bc_pointer+1
:
    ldy #BC_FOREGROUND
    lda (se_bc_context),y
    asl
    asl
    asl
    asl
    iny
    ora (se_bc_context),y
    ldy #0
    sta (se_bc_pointer),y
    ; cell offset*8 gives its VIC bitmap tile; pixel rows are consecutive.
    lda se_bc_pointer+1
    and #3
    sta se_bc_pointer+1
    .repeat 3
        asl se_bc_pointer
        rol se_bc_pointer+1
    .endrepeat
    lda se_bc_pointer+1
    clc
    adc #$60
    sta se_bc_pointer+1
    ldy #BC_SCREEN
    lda (se_bc_context),y
    tax
    pla
    sta se_bc_context+1
    pla
    sta se_bc_context
    ldy #7
pixels:
    lda (se_bc_context),y
    cpx #128
    bcc :+
    eor #$FF
:
    sta (se_bc_pointer),y
    dey
    bpl pixels
    lda #0
    clc
    rts
