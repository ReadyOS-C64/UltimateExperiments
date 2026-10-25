; Appended into guarded R25. Calls only after whole-row validation has succeeded.
; long.inc is already included by the containing R25 service.
long_packet:
 ldx W
 dex
 lda P,x
 sta NLEN
 lda SIGN
 bmi @delete
@right:
 cpx EDIT
 beq @put
 lda P-1,x
 sta P,x
 dex
 bne @right
@put:
 lda TLEN
 sta P,x
 jmp @flags
@delete:
 ldx EDIT
@left:
 inx
 cpx W
 beq @last
 lda P,x
 sta P-1,x
 bne @left
@last:
 lda TLEN
 sta P-1,x
@flags:
 ldx W
 dex
 lda #0
@clear:
 sta P+80,x
 sta P+160,x
 dex
 bpl @clear
 lda ROW
 cmp NEWROW
 bne @write
 ldx NEWCOL
 lda #4
 sta P+160,x
@write:
 lda #<P
 sta PTR
 lda #>P
 sta PTR+1
 jsr row_request
 lda #0
 jsr se_reu_copy
 jcs invalid
 jsr packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 sta H+N_ROWCRC,x
 lda se_crc_value+1
 sta H+N_ROWCRC+1,x
 clc
 rts

; Native narrow glyph from exact managed verified backend backing, not Rslot.
.import se_petscii_screen
long_glyph:
 lda TLEN
 jsr se_petscii_screen
 and #127
 ldx #0
 stx se_reu_offset+1
 asl
 rol se_reu_offset+1
 asl
 rol se_reu_offset+1
 asl
 rol se_reu_offset+1
 sta se_reu_offset
 lda FCAP+1
 and #15
 asl
 asl
 asl
 asl
 ora #8
 ora se_reu_offset+1
 sta se_reu_offset+1
 lda FCAP+2
 sta se_reu_logical
 lda #<(LPF+4)
 sta se_reu_c64
 lda #>(LPF+4)
 sta se_reu_c64+1
 lda #8
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 lda #1
 jmp se_reu_copy
