; A prepared flush is only an intent. R2 commits it at root publication;
; W_COMMIT handles the checked zero-delta case. Cancellation never emits it.
.include "cache/observer/ring.inc"
bc_flush_prepare:
 jsr bc_reserve
 beq @done
 lda #BC_EVENT_REKEY
 sta se_bc_ring+BC_E_KIND,y
 BC_STORE se_r_revision,BC_E_REV_BEFORE,4
 BC_STORE se_doc_generation,BC_E_GEN_BEFORE,2
 ; The prepared conservative tuple is contiguous in both frames.
 tya
 clc
 adc #BC_E_POSITION
 tay
 ldx #0
@copy:
 lda se_doc_edit_position,x
 sta se_bc_ring,y
 iny
 inx
 cpx #9
 bcc @copy
@done:
 rts
