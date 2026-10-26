; Checked writer and transport operations, never a C-slot supervisor.
.setcpu "6502"
.include "editor-api.inc"
.include "cache/arena/writer.inc"
.import se_overlay_frame,se_f_owner
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq open
 cmp #1
 beq step
 cmp #2
 beq cancel
 cmp #3
 beq trim
 cmp #4
 beq begin
 cmp #5
 beq append
 cmp #6
 beq final
 cmp #7
 beq abort
 lda #$C0
 sec
 rts
busy:lda #$B2
 sec
 rts
open:jmp se_bc_arena_open
step:jmp se_bc_arena_step
cancel:jmp se_bc_arena_cancel
trim:jmp se_bc_arena_trim
begin:jmp se_bc_write_begin
append:jmp se_bc_write_append
final:jmp se_bc_write_final
abort:jmp se_bc_write_cancel
