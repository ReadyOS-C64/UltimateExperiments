.setcpu "6502"
.include "editor-api.inc"
.include "render/geos/typing-candidate/api.inc"
.import se_f_owner
.importzp text_ptr,screen_ptr
.export entry
.exportzp gt_base,gt_bitmap
gt_base=text_ptr
gt_bitmap=screen_ptr
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 beq :+
 lda #$B2
 sec
 rts
: lda se_overlay_frame
 beq :+
 lda #$90
 sec
 rts
: jmp se_typing_patch
.assert entry=$A010,lderror,"probe entry binding"
