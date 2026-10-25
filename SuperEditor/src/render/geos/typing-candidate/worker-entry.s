; Budget capsule: genuine admission +raster/status components; notfullcontroller.
.setcpu "6502"
.include "editor-api.inc"
.import se_gtt_admit,se_f_owner
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
: jmp se_gtt_admit
.segment "RODATA"
GTF_INCLUDE_GLYPH_CRC=1
.include "render/geos/typing-candidate/font-witness.inc"
