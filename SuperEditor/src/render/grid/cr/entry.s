.setcpu "6502"
.include "editor-api.inc"
.import se_f_owner,cr_begin,cr_next
.segment "CODE"
OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 cmp #6
 beq begin
 cmp #7
 beq next
 lda #$90
 sec
 rts
busy:lda #$B2
 sec
 rts
begin:jmp cr_begin
next:jmp cr_next
