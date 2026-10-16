.setcpu "6502"
.export _ps_guard,_ps_scan,ps_rti,_ps_matrix
.segment "BSS"
_ps_matrix: .res 8
scan_mask: .res 1
.segment "CODE"
_ps_guard:
 sei
 cld
 lda #$2f
 sta $00
 lda #$37
 sta $01 ; retain ROM handler until CIA masks/ack and our RAM vector ready
 lda #$7f
 sta $dc0d
 sta $dd0d
 lda $dc0d
 lda $dd0d
 lda #<ps_rti
 sta $fffa
 lda #>ps_rti
 sta $fffb
 lda #$35
 sta $01
 rts
ps_rti: rti
_ps_scan:
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
 lda #$ff
 sta $dc00
 rts
