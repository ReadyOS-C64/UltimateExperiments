; C31 sealed data image. Its safe C entry does not execute the staged code.
.setcpu "6502"
.include "editor-api.inc"
.export entry
.segment "C31_HEADER"
image:
 OVL_BINDING
entry:
 lda #0
 clc
 rts
 .res 32-(*-image),0
.segment "CODE"
.export se_gct_stage_lex,se_gct_stage_paint
.import se_gct_lex,se_gct_paint
se_gct_stage_lex: jmp se_gct_lex
se_gct_stage_paint: jmp se_gct_paint
