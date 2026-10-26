; Complete block/inline query. Held results remain provisional until A0.
.setcpu "6502"
.include "editor-api.inc"
.include "cache/query/api.inc"
.import se_f_owner,se_overlay_frame
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
 cmp #3
 beq ack
 lda #$C0
 sec
 rts
busy:lda #$B2
 sec
 rts
begin:jmp se_bc_query_begin
step:jmp se_bc_query_step
cancel:jmp se_bc_query_cancel
ack:jmp se_bc_query_ack
