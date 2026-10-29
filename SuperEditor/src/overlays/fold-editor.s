.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "editor_fold/controller.inc"
.export entry
.segment "FOLD_EDITOR"
    OVL_BINDING
entry:
    lda se_overlay_frame
    beq @begin
    cmp #EF_STEP
    beq @step
    cmp #EF_CANCEL
    beq @cancel
    lda #$B0
    sec
    rts
@begin:
    jmp se_ef_begin
@step:
    jmp se_ef_step
@cancel:
    jmp se_ef_cancel
