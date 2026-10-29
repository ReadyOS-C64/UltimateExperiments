.setcpu "6502"
.include "editor-api.inc"
.import se_f_owner
.include "cache/semantic/api.inc"
.export entry
.segment "BSC_CODE"
    OVL_BINDING
entry:
    lda se_f_owner
    cmp #4
    bne @busy
    lda se_overlay_frame
    beq @begin
    cmp #1
    beq @step
    cmp #2
    beq @cancel
    cmp #3
    beq @ack
    lda #BSC_BAD
    sec
    rts
@busy:
    lda #BSC_BUSY
    sec
    rts
@begin:jmp se_bsc_begin
@step:jmp se_bsc_step
@cancel:jmp se_bsc_cancel
@ack:jmp se_bsc_ack
