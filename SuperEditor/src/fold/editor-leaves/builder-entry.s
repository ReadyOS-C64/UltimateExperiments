; Root selects this C leaf between complete calls; never C-to-C nesting.
.setcpu "6502"
.include "editor-api.inc"
.include "fold/editor-leaves/api.inc"
.export entry
.segment "FOLD_EDITOR"
    OVL_BINDING
entry:
    lda se_f_owner
    cmp #FE_OWNER
    bne busy ; no phase byte read before caller ownership
    lda se_overlay_frame
    cmp #FE_CANCEL
    beq cancel
    cmp #FE_STEP
    beq step
.ifndef FOLD_FINISH
    cmp #FE_BEGIN
    bne bad
    jsr se_fb_begin
    jmp result
.else
    bne bad
.endif
step:
    lda se_fb_phase
.ifdef FOLD_FINISH
    cmp #FB_FILTER
    bcc bad
    cmp #FB_RETAIN_MATCH+1
    bcs bad
.else
    cmp #FB_PARSE
    bcc bad
    cmp #FB_FILTER
    bcs bad
.endif
    jsr se_fb_step
result:
    bcs return
    lda se_fb_busy
    beq return
    lda #FE_PENDING
return:
    rts
cancel:
    jsr se_fb_cancel
    bcs return
    lda #0
    rts
busy:
    lda #SF_BUSY
    sec
    rts
bad:
    lda #SF_BAD
    sec
    rts
