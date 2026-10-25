; Component proof entry only: no cache authority/publication claim.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.import se_f_owner,se_gct_lex,se_gct_paint,se_gct_current
.export entry
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 bne owner
 lda se_overlay_frame
 jeq se_gct_lex
 cmp #1
 jeq se_gct_paint
 cmp #2
 jeq se_gct_current
 cmp #3
 bne bad
 jsr se_gct_lex
 bcs done
 jmp se_gct_paint
bad:
 lda #$90
 sec
done:
 rts
owner:
 lda #$B2
 sec
 rts
