.setcpu "6502"
.include "editor-api.inc"
.include "render/geos/fold-query.inc"
.import se_f_owner
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 beq step
 cmp #2
 beq cancel
 lda #$90
 sec
 rts
begin:
 jmp se_gfq_begin
step:
 jmp se_gfq_step
cancel:
 jmp se_gfq_cancel
busy:
 lda #$B2
 sec
 rts
