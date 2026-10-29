.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "fold/transform.inc"
.import se_f_owner
.export entry
.segment "FOLD_EDITOR"
    OVL_BINDING
entry:
    lda se_f_owner
    cmp #3
    bne busy
    lda se_overlay_frame
    beq begin
    cmp #1
    beq step
    cmp #2
    beq cancel
    cmp #3
    beq beginlog
    lda #$B0
    sec
    rts
begin: jmp se_ft_begin
step: jmp se_ft_step
cancel: jmp se_ft_cancel
beginlog: jmp se_ft_begin_log
busy:
    lda #$B2
    sec
    rts
