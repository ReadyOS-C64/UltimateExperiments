; C26 output buffers survive C20/R14. No other worker runs while C20 ownsjob.
window_try:
    lda SW_VALID
    cmp #1
    bne @miss
    lda SW_COUNT
    cmp #161
    bcs @miss
    lda SC_VALID
    cmp #1
    bne @miss
    jsr style_check
    bcs @miss
    sec
    ldx #0
    ldy #3
@subtract:
    lda L+GL_SCAN,x
    sbc SW_START,x
    sta SC_TEMP,x
    inx
    dey ;preserveborrow between allthree bytes
    bne @subtract
    bcc @miss
    lda SC_TEMP+1
    ora SC_TEMP+2
    bne @miss
    lda SC_TEMP
    sta SW_OFFSET
    clc
    adc L+GL_PACKET_COUNT
    bcs @miss
    cmp SW_COUNT
    bcc window_copy
    beq window_copy
@miss:
 lda #4
 sta se_overlay_frame
 lda #33
 ldx #0
 jsr se_overlay_call
 bcs @failed
 lda #0
 sta SW_OFFSET
 jmp window_copy
@failed:rts
window_copy:
    ldy SW_OFFSET
    ldx #0
@cell:
    cpy SW_COUNT
    bcs @base
    lda GI_OUTPUT_STYLES,y
    sta GS_STYLES,x
    lda GI_OUTPUT_ROLES,y
    jmp @role
@base:
    lda #0
    sta GS_STYLES,x
    lda GSEM_FRAME+GSEM_ROLE
@role:
    sta SW_ROLES,x
    iny
    inx
    cpx L+GL_PACKET_COUNT
    bcc @cell
    clc
    rts
window_count:
    sec
    ldx #0
    ldy #3
@subtract:
    lda GSEM_FRAME+GSEM_END,x
    sbc L+GL_SCAN,x
    sta SC_TEMP,x
    inx
    dey ;preserveborrow between allthree bytes
    bne @subtract
    bcc @zero
    lda SC_TEMP+1
    ora SC_TEMP+2
    bne @max
    lda SC_TEMP
    cmp #160
    bcc @ready
@max:
    lda #160
    bne @ready
@zero:
    lda #0
@ready:
    sta SW_COUNT
    tax ;return Z from the actualclampedcount, not priorCMP flags
    rts
