; Strictstage borrower and stable helperjump ABI. No newresident state.
.setcpu "6502"
.include "editor-api.inc"
.include "render/geos/edit-certificate.inc"
.include "render/geos/typing/certificate.inc"
.import se_f_owner,se_gct_stage
.import se_gtt_admit,se_gtt_current,se_gp_cache_slot,se_gp_cache_read,se_gp_cache_write,se_gcc_status
.importzp text_ptr,screen_ptr
.export entry
.exportzp gt_base,gt_bitmap
gt_base=text_ptr
gt_bitmap=screen_ptr
.segment "CODE"
image:
 OVL_BINDING
entry: jmp root
 .res $20-(*-image),0
 jmp se_gtt_admit
 jmp se_gtt_current
 jmp se_gp_cache_slot
 jmp se_gp_cache_read
 jmp se_gp_cache_write
 jmp se_gcc_status
root:
 lda se_overlay_frame
 cmp #3
 bne bad
 lda se_f_owner
 bne miss
 lda GEC_VALID
 cmp #1
 bne miss
 lda GTC_VALID
 cmp #1
 bne miss
 lda #4
 sta se_f_owner
 jsr se_gct_stage
 bcs done
 jsr $5000
done:
 php
 pha
 lda #0
 sta se_f_owner
 pla
 plp
 rts
miss:
 lda #2
 clc
 rts
bad:
 lda #$90
 sec
 rts
