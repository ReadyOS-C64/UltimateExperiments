.setcpu "6502"
.importzp sp,ptr1
.import __HIGHBSS_RUN__,__HIGHBSS_SIZE__
.import zerobss
.export runtime_init,fixture_return
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word $080b,10
.byte $9e,"2061",0
.word 0
.segment "CODE"
 jmp fixture_return
fixture_return: jmp fixture_return
runtime_init:
 sei
 cld
 lda #$ff
 sta sp
 lda #$cf
 sta sp+1
 jsr zerobss
 lda #<__HIGHBSS_RUN__
 sta ptr1
 lda #>__HIGHBSS_RUN__
 sta ptr1+1
 ldx #>__HIGHBSS_SIZE__
 lda #0
 tay
@page:
 cpx #0
 beq @tail
@byte:
 sta (ptr1),y
 iny
 bne @byte
 inc ptr1+1
 dex
 bne @page
@tail:
 ldy #0
@last:
 cpy #<__HIGHBSS_SIZE__
 beq @done
 sta (ptr1),y
 iny
 bne @last
@done:
 rts
