.setcpu "6502"
.export _ps_guard,_ps_scan,_ps_matrix,_mu_fixture_init,fixture_return
.import _mu_init,sp
.segment "BSS"
_ps_matrix:.res 8
scan_mask:.res 1
saved_ports:.res 4
.segment "CODE"
; This panel never calls standalone platform ps_init/guard or touches clocks.
_ps_guard:
 brk
_mu_fixture_init:
 lda #<$bfff
 sta sp
 lda #>$bfff
 sta sp+1
 jmp _mu_init
_ps_scan:
 php
 sei
 ldx #3
@save:
 lda $dc00,x
 sta saved_ports,x
 dex
 bpl @save
 lda #$ff
 sta $dc02
 lda #0
 sta $dc03
 ldx #0
 lda #$fe
 sta scan_mask
@row:
 lda scan_mask
 sta $dc00
 nop
 nop
 lda $dc01
 eor #$ff
 sta _ps_matrix,x
 sec
 rol scan_mask
 inx
 cpx #8
 bne @row
 ldx #3
@restore:
 lda saved_ports,x
 sta $dc00,x
 dex
 bpl @restore
 plp
 rts
fixture_return=$02e0
