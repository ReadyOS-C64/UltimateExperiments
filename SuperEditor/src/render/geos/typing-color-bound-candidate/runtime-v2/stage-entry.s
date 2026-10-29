.setcpu "6502"
.include "editor-api.inc"
.export entry
.segment "STYLE_HEADER"
image:
 OVL_BINDING
entry:
 lda #0
 clc
 rts
 .res 32-(*-image),0
.segment "CODE"
.import se_gst_transaction
 jmp se_gst_transaction
