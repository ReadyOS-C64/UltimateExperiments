.setcpu "6502"
.include "overlay-api.inc"
.segment "CODE"
image_start:
    OVL_BINDING
    inc se_overlay_frame+2
    lda #1
    ldx #1
    jsr se_overlay_call
    bcc failed
    sta se_overlay_frame+3
    lda #2
    ldx #0
    jsr se_overlay_call
    bcs failed
    cmp #$42
    bne failed
    lda #$43
    sec ; module error/continuation carry survives resident trampoline
    rts
failed:
    lda #$EF
    clc
    rts
