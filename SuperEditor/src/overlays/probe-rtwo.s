.setcpu "6502"
.include "overlay-api.inc"
.segment "CODE"
image_start:
    OVL_BINDING
    inc se_overlay_frame+1
    lda #$42
    clc
    rts
