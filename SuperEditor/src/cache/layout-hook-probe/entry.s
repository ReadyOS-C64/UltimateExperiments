; PRIVATE R34 component selector, no registration in the canonical startup.
.setcpu "6502"
.include "editor-api.inc"
.include "cache/layout-hook-probe/api.inc"
.import se_f_owner,se_lm_capture,se_lm_restore,se_lm_step,se_lm_cancel,se_lm_revoke
.import se_lmh_init,se_lmh_begin,se_lmh_step
.export entry
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 bne @busy
 lda se_overlay_frame
 cmp #LM_BEGIN_CAPTURE
 beq @capture
 cmp #LM_BEGIN_RESTORE
 beq @restore
 cmp #LM_STEP
 beq @step
 cmp #LM_CANCEL
 beq @cancel
 cmp #LM_REVOKE
 beq @revoke
 cmp #21
 beq @init
 cmp #22
 beq @page_begin
 cmp #23
 beq @page_step
 lda #$90
 sec
 rts
@capture:jmp se_lm_capture
@restore:jmp se_lm_restore
@step:jmp se_lm_step
@cancel:jmp se_lm_cancel
@revoke:jmp se_lm_revoke
@busy:
 lda #$B2
 sec
 rts

@init:jmp se_lmh_init
@page_begin:jmp se_lmh_begin
@page_step:jmp se_lmh_step
