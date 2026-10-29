resolve:
    lda F+GR_TOP
    cmp F+GR_BOTTOM
    jeq complete
    lda #0
    sta tile
@tile:
    lda tile
    asl
    asl
    asl
    sta pixel
    lda tile
    lsr
    lsr
    lsr
    lsr
    lsr
    sta pixel+1
    jsr clipped_right
    jcs @next
    clc
    lda pixel
    adc #8
    sta pixel
    bcc :+
    inc pixel+1
:
    jsr clipped_left
    bcc @next
    beq @next
    lda #0
    sta role
    sta best
    sta weight
    sta rank
    jsr histogram_address
    ldy #0
@role:
    lda (se_gg_context),y
    cmp weight
    bcc @skip
    bne @choose
    cmp #0
    beq @skip
    lda priorities,y
    cmp rank
    bcc @skip
    beq @skip
@choose:
    lda (se_gg_context),y
    sta weight
    lda priorities,y
    sta rank
    sty best
@skip:
    iny
    cpy #14
    bcc @role
    lda F+GR_PALETTE
    sta se_gg_pointer
    lda F+GR_PALETTE+1
    sta se_gg_pointer+1
    ldy best
    lda (se_gg_pointer),y
    asl
    asl
    asl
    asl
    ora F+GR_BACKGROUND
    pha
    ldx F+GR_ROW
    lda attrslo,x
    clc
    adc tile
    sta se_gg_pointer
    lda attrshi,x
    adc #0
    sta se_gg_pointer+1
    pla
    ldy #0
    sta (se_gg_pointer),y
@next:
    inc tile
    lda tile
    cmp #40
    jcc @tile
complete:
    lda #1
    sta F+GR_VALID
    lda #0
    clc
    rts
.segment "RODATA"
priorities: .byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
attrslo:
.repeat 25,I
.byte <($4000+I*40)
.endrepeat
attrshi:
.repeat 25,I
.byte >($4000+I*40)
.endrepeat
.segment "CODE"
