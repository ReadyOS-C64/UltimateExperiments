.setcpu "6502"
.include "prefix.inc"
.import _sc_ready,_br_ui_acquire,_br_ui_release
.import __RECOVER_BSS_RUN__,__RECOVER_BSS_SIZE__
.importzp ptr1
.export _jg_initialized,_jg_init,_jg_dispatch
.import _jg_begin,_jg_poll,_jg_state,_jg_error,_jg_cleanup,_jg_class,_jg_boot_ready,_jg_cancel,_jg_clock_fail
.segment "LOADADDR"
.word $6000
.segment "SHARED"
.incbin "shared-prefix.bin"
.segment "RECOVER_DATA"
_jg_initialized: .byte 0
.segment "RECOVER_CODE"
_jg_dispatch:
 cmp #0
 beq _jg_init
 cmp #1
 bne :+
 jmp _jg_begin
: cmp #2
 bne :+
 jsr _jg_poll
 jmp _jg_state
: cmp #3
 bne :+
 jmp _jg_state
: cmp #4
 bne :+
 jmp _jg_error
: cmp #5
 bne :+
 jmp _jg_cleanup
: cmp #6
 bne :+
 jmp _jg_class
: cmp #7
 bne :+
 jmp _jg_boot_ready
: cmp #8
 bne :+
 jsr _jg_cancel
 jmp _jg_state
: cmp #9
 bne dispatch_refuse
 jsr _jg_clock_fail
 jmp _jg_state
dispatch_refuse:
 lda #0
 tax
 rts
.assert _jg_dispatch=JG_ENTRY,lderror,"matched prefix entry"
_jg_init:
 lda _jg_initialized
 bne reject
 jsr _sc_ready
 cmp #0
 beq reject
 jsr _br_ui_acquire
 cmp #0
 beq reject
 jsr _br_ui_release
 cmp #0
 beq reject
 lda #<__RECOVER_BSS_RUN__
 sta ptr1
 lda #>__RECOVER_BSS_RUN__
 sta ptr1+1
 ldx #>__RECOVER_BSS_SIZE__
 lda #0
 ldy #0
 cpx #0
 beq tail
page:
 sta (ptr1),y
 iny
 bne page
 inc ptr1+1
 dex
 bne page
tail:
 ldy #0
loop:
 cpy #<__RECOVER_BSS_SIZE__
 beq done
 sta (ptr1),y
 iny
 bne loop
done:
 inc _jg_initialized
 lda #1
 ldx #0
 rts
reject:
 lda #0
 tax
 rts
.assert __RECOVER_BSS_RUN__=$9000,lderror,"private cold state"
.assert __RECOVER_BSS_SIZE__<=$800,lderror,"cold state bound"
