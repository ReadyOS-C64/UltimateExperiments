.setcpu "6502"
.include "editor-api.inc"
.include "render/geos/font-store.inc"
.segment "CODE"
 OVL_BINDING
.export entry
entry:
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
 lda se_overlay_frame+1
 jmp se_gf_import_begin
step:
 jmp se_gf_import_step
cancel:
 jmp se_gf_import_cancel
