.setcpu "6502"
.export _ps_guard,_ps_scan,ps_rti,_ps_matrix
.export _ps_shifted,_ps_buffer_poll
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

; Same physical shift mapping as platform.c, kept compact to leave room for
; standard buffer input in the resident installer. cc65 fastcall byte in A.
_ps_shifted:
 cmp #'a'
 bcc @digits
 cmp #'z'+1
 bcs @digits
 sec
 sbc #32
 bne @return
@digits:
 cmp #'1'
 bcc @functions
 cmp #'9'+1
 bcs @functions
 sec
 sbc #16
 bne @return
@functions:
 cmp #$90
 bcc @special
 cmp #$97
 bcs @special
 clc
 adc #1
 bne @return
@special:
 ldx #13
@find:
 cmp shift_from,x
 beq @found
 dex
 bpl @find
 bmi @return
@found:
 lda shift_to,x
@return:
 ldx #0
 rts
shift_from: .byte 8,9,'-','@','^',$83,$81,'.',',',':',';','/',$5c,0
shift_to:   .byte $85,0,'_','`','~',$82,$80,'>','<','[',']','?','|',0

; The existing .NET Ultimate client publishes PETSCII at $0277, count LAST
; at $C6. IRQs are masked here, so consume the bounded queue without GETIN.
; The producer must wait for count zero; count is retired after shifting.
_ps_buffer_poll:
 ldx $c6
 beq @empty
 cpx #11
 bcc @take
 lda #0
 sta $c6
 beq @empty
@take:
 lda $0277
 pha
 ldy #1
@shift:
 cpy $c6
 bcs @retire
 lda $0277,y
 sta $0276,y
 iny
 bne @shift
@retire:
 dec $c6
 pla
 ldx #17
@decode:
 cmp petscii_from,x
 beq @mapped
 dex
 bpl @decode
 cmp #32
 bcc @empty
 cmp #127
 bcs @empty
 bcc @return
@mapped:
 lda petscii_to,x
@return:
 ldx #0
 rts
@empty:
 lda #0
 tax
 rts
petscii_from: .byte 13,3,27,9,20,19,17,145,29,157,133,137,134,138,135,139,136,140
petscii_to:   .byte 13,27,27,9,8,$84,$81,$80,$83,$82,$90,$91,$92,$93,$94,$95,$96,$97
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
