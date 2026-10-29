; Production wrapper. Root generates style-api.inc from the linked resident.
.setcpu "6502"
.include "style-api.inc"
.include "style/api.inc"
.import se_style_auto
.segment "STYLE_CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    beq @begin
    cmp #ST_STEP
    beq @step
    cmp #ST_CANCEL
    beq @cancel
    cmp #3
    beq @auto
    lda #ST_ARGUMENT
    sec
    rts
@begin:jmp se_style_begin
@step:jmp se_style_step
@cancel:jmp se_style_cancel
@auto:jmp se_style_auto
