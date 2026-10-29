.setcpu "6502"
.include "overlay-api.inc"
.segment "CODE"
image_start:
    OVL_BINDING
start:
    inc se_overlay_frame
    lda #$41
    clc
    rts
    .res $1000-(*-image_start),$A5 ; full-slot, multi-sector streaming fixture
