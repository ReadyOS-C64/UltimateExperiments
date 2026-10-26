; Completed semantic workers can return directly to the actual preview parent.
; Ordinary/source/nav clients retain A0. Only live root job11/presentation1
; publishes REQUEST27/STEP and A1, exactly like C20's inline continuation.
.import se_r_presentation,se_e_job
se_gp_preview_complete:
 lda se_r_presentation
 cmp #1
 bne @ordinary
 lda se_e_job
 cmp #11
 bne @ordinary
 lda #27
 sta $9135
 lda #1
 sta $9136
 clc
 rts
@ordinary:
 lda #21
 sta $9135
 lda #1
 sta $9136
 clc
 rts
