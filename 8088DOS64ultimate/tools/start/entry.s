.setcpu "6502"
.importzp sp
.import zerobss,_sf_main
.export sf_entry,runtime_init,_codec_init,fixture_return,sf_entry_idle
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word $080b,10
.byte $9e,"2061",0
.word 0
.segment "DATA"
sf_entered: .byte 0
.segment "CODE"
sf_entry:
 sei
 cld
 lda sf_entered
 bne sf_entry_idle
 inc sf_entered
 ldx #$ff
 txs
 lda #$2f
 sta $00
 lda #$37
 sta $01
 jsr runtime_init
 jsr _sf_main
sf_entry_idle: jmp sf_entry_idle
fixture_return: brk
runtime_init:
_codec_init:
 lda #$ff
 sta sp
 lda #$cf
 sta sp+1
 jsr zerobss
 rts
.assert sf_entry=$080d,lderror,"BASIC SYS2061 must enter actual startup"
