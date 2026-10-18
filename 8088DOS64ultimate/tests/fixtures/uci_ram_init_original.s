.setcpu "6502"
.include "uci_ram_init_state.inc"
.segment "CODE"
.macro ENTER
 php
 sei
 pha
 txa
 pha
 tya
 pha
 cld
 lda $00
 pha
 ora #7
 sta $00
 lda $01
 pha
 and #$f8
 ora #$05
 sta $01
.endmacro
.macro LEAVE carry
 pla
 sta $01
 pla
 sta $00
 pla
 tay
 pla
 tax
 pla
 plp
 .if carry
 sec
 .else
 clc
 .endif
 rts
.endmacro
reference_init:
 ENTER
 lda #0
 ldx #dos64_uci_state_end-dos64_uci_state_start-1
@zero: sta dos64_uci_state_start,x
 dex
 bpl @zero
 lda #$1c
 sta dos64_uci_base
 lda #$df
 sta dos64_uci_base+1
 lda #$80
 sta dos64_uci_data_capacity
 lda #3
 sta dos64_uci_data_capacity+1
 lda #1
 sta dos64_uci_status_capacity+1
 lda #$2c
 sta dos64_uci_timeout
 lda #1
 sta dos64_uci_timeout+1
 lda #60
 sta dos64_uci_recovery_timeout
 LEAVE 0
