.setcpu "6502"
.importzp sp
.import zerobss
.export runtime_init,fixture_return
.segment "LOADADDR"
.word $0801
.segment "CODE"
runtime_init:
 lda #$ff
 sta sp
 lda #$cf
 sta sp+1
 jsr zerobss
 rts
fixture_return: brk
