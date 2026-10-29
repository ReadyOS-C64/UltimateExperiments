.setcpu "6502"
.include "overlay-api.inc"
.segment "CODE"
image_start:
    OVL_BINDING
    lda #1
    ldx #1
    jsr se_overlay_call
    bcc failed
    sta se_overlay_frame+4
    lda #$44
    clc
    rts
failed:
    lda #$EF
    sec
    rts
