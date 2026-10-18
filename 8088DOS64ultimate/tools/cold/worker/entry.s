.setcpu "6502"
.export _rf_init,_rf_dispatch
.import _rf_begin,_rf_poll,_rf_state,_rf_error,_rf_cleanup,_rf_cancel,_rf_clock_fail
.import __RF_BSS_RUN__,__RF_BSS_SIZE__
.importzp ptr1
.segment "LOADADDR"
.word $A000
.segment "RF_CODE"
; caller only after new phase installation, no live worker frames.
_rf_dispatch:
 cmp #0
 beq _rf_init
 cmp #1
 bne :+
 lda #1
 jmp _rf_begin
: cmp #2
 bne :+
 jsr _rf_poll
 jmp _rf_state
: cmp #3
 bne :+
 jmp _rf_error
: cmp #4
 bne :+
 jmp _rf_cleanup
: cmp #5
 bne :+
 jsr _rf_cancel
 jmp _rf_state
: cmp #6
 bne @refuse
 jsr _rf_clock_fail
 jmp _rf_state
@refuse:
 lda #0
 tax
 rts
_rf_init:
 lda #<__RF_BSS_RUN__
 sta ptr1
 lda #>__RF_BSS_RUN__
 sta ptr1+1
 ldx #>__RF_BSS_SIZE__
 ldy #0
 lda #0
@pages:
 cpx #0
 beq @tail
@page:
 sta (ptr1),y
 iny
 bne @page
 inc ptr1+1
 dex
 bne @page
@tail:
 cpy #<__RF_BSS_SIZE__
 beq @done
 sta (ptr1),y
 iny
 bne @tail
@done:
 lda #1
 tax
 rts
