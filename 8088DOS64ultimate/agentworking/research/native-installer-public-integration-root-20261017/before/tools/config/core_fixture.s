.setcpu "6502"
.importzp sp
.import zerobss
.import _cg_default_start,_co_poll,_ps_guard
.import cp_bootstrap,_cp_high_ready

.import __RIBSS_RUN__,__RIBSS_SIZE__,__RMBSS_RUN__,__RMBSS_SIZE__
.assert __RIBSS_RUN__+__RIBSS_SIZE__=__RMBSS_RUN__,lderror,"CONFIG phase BSS zero extent must be contiguous"
.importzp ptr1,ptr2
.export runtime_init,fixture_return,config_poll_loop,config_poll_return
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word $080b,10
.byte $9e,"2061",0
.word 0
.segment "CODE"
; Standalone BASIC SYS consumer. Establish owned NMI/banking before any C state read.
 jmp config_entry
config_entry:
 sei
 cld
 jsr _ps_guard
 jsr runtime_init
 bcs fixture_return
 jsr _cg_default_start
config_poll_loop:
 jsr _co_poll
config_poll_return:
 jmp config_poll_loop
fixture_return: jmp fixture_return
runtime_init:
 jsr _ps_guard
 jsr cp_bootstrap
 php
 lda #$ff
 sta sp
 lda #$cf
 sta sp+1
 jsr zerobss
 lda #<__RIBSS_RUN__
 sta ptr1
 lda #>__RIBSS_RUN__
 sta ptr1+1
 lda #<(__RIBSS_SIZE__+__RMBSS_SIZE__)
 sta ptr2
 lda #>(__RIBSS_SIZE__+__RMBSS_SIZE__)
 sta ptr2+1
 ldy #0
@zero:
 lda ptr2
 ora ptr2+1
 beq @done
 lda #0
 sta (ptr1),y
 inc ptr1
 bne :+
 inc ptr1+1
: lda ptr2
 bne :+
 dec ptr2+1
: dec ptr2
 jmp @zero
@done:
@ready:
 plp
 bcs @bad
 lda #$a5
 sta _cp_high_ready
 clc
@bad:
 rts
