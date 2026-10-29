; Private R25 transaction preparation/commit. Never calls another R leaf.
.import se_st_cp_valid,se_l_caret,se_hot_delete
TLEN=C+59
NLEN=C+60
EDIT=C+61
SIGN=C+62
TYPING=C+63
type_prepare:
 lda #1
 sta TYPING
 jsr admit
 jcs invalid
 jsr fetch_header
 jcs invalid
 jsr header_crc
 ldx #1
@crc:
 lda se_crc_value,x
 cmp H+N_CRC,x
 jne invalid
 dex
 bpl @crc
 lda H
 cmp #'N'
 jne invalid
 lda H+1
 cmp #'C'
 jne invalid
 lda H+2
 cmp #1
 jne invalid
 lda H+3
 cmp #$A5
 jne invalid
 jsr fields
 jcs invalid
 lda se_sel_mark
 ora se_ef_valid
 ora se_l_mode
 ora se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 ora se_l_manual
 jne invalid
 lda se_st_valid
 cmp #1
 jne invalid
 lda se_st_request
 jne invalid
 lda H+N_SEEN
 cmp #1
 jne invalid
 sta OLDSEEN
 lda H+N_ROW
 cmp #22
 jcs invalid
 sta ROW
 sta NEWROW
 sta OLDROW
 lda H+N_COL
 cmp W
 jcs invalid
 sta OLDCOL
 sta EDIT
 ; Authenticate old published sequence and exactly one revision increment.
 ldx #1
@seq:
 lda H+N_SEQUENCE,x
 cmp se_e_draw_sequence,x
 jne invalid
 dex
 bpl @seq
 sec
 lda se_v_length
 sbc H+N_KEY+21
 sta SIGN
 lda se_v_length+1
 sbc H+N_KEY+22
 sta DELTA+1
 lda se_v_length+2
 sbc H+N_KEY+23
 sta DELTA+2
 lda SIGN
 cmp #1
 bne @delete
 lda DELTA+1
 ora DELTA+2
 jne invalid
 lda #1
 jmp @delta
@delete:
 cmp #$FF
 jne invalid
 lda DELTA+1
 and DELTA+2
 cmp #$FF
 jne invalid
 dec EDIT
@delta:
 lda SIGN
 cmp #1
 beq @insertion
 lda se_hot_delete
 cmp #1
 jne invalid
 jmp @length_delta
@insertion:
 lda se_hot_delete
 jne invalid
@length_delta:
 sec
 lda se_hot_length
 sbc H+N_HOTLEN
 sta NEXT
 lda se_hot_length+1
 sbc H+N_HOTLEN+1
 sta NEXT+1
 lda NEXT
 cmp SIGN
 jne invalid
 lda NEXT+1
 ldx SIGN
 cpx #1
 beq :+
 cmp #$FF
 jne invalid
 beq :++
: cmp #0
 jne invalid
:
 lda se_hot_pending
 cmp #1
 jne invalid
 COPY24 H+N_CARET,DELTA
 lda SIGN
 cmp #1
 beq @caretadd
 dec DELTA
 lda DELTA
 cmp #$FF
 bne @caretcheck
 dec DELTA+1
 lda DELTA+1
 cmp #$FF
 bne @caretcheck
 dec DELTA+2
 jmp @caretcheck
@caretadd:
 inc DELTA
 bne @caretcheck
 inc DELTA+1
 bne @caretcheck
 inc DELTA+2
@caretcheck:
 CMP24 DELTA,se_hot_caret
 jne invalid
 sec
 .repeat 4,I
 lda H+N_KEY+17+I
 adc #0
 sta NEXT+I
 .endrepeat
 jcs invalid
 ldx #3
@rev:
 lda NEXT,x
 cmp se_r_revision,x
 jne invalid
 dex
 bpl @rev
 jsr bounds
 jcs invalid
 ; Conservative semantic proof from BOF, not inferred from palette role0.
 ; The real block classifier can enter code/region only on colon-leading
 ; fences. Reject any prior colon and long prefixes; false misses are safe.
 lda POS+1
 ora POS+2
 jne invalid
 lda POS
 cmp #128
 jcs invalid
 lda #0
 sta se_v_pos
 sta se_v_pos+1
 sta se_v_pos+2
@prefix:
 lda se_v_pos
 cmp POS
 beq @outside_code
 jsr se_view_peek
 jcs invalid
 cmp #':'
 jeq invalid
 inc se_v_pos
 jmp @prefix
@outside_code:
 SUB24 END,POS,DELTA
 lda DELTA+1
 ora DELTA+2
 jne invalid
 lda DELTA
 sta TLEN
 clc
 adc #1
 cmp W
 jcs invalid
 lda EDIT
 jeq invalid
 cmp TLEN
 jcs invalid
 lda TLEN
 clc
 adc SIGN
 sta NLEN
 COPY24 POS,se_v_pos
 lda POS
 ora POS+1
 ora POS+2
 beq @start
 jsr retreat
 jsr se_view_peek
 jcs invalid
 cmp #13
 jne invalid
 COPY24 POS,se_v_pos
@start:
 lda #<B
 ldx #>B
 jsr fetch_row
 jcs invalid
 jsr verify_row
 jcs invalid
 lda B
 jsr alpha
 jcs invalid
 ldx #0
@old:
 lda B+80,x
 jne invalid
 lda B+160,x
 and #3
 jne invalid
 cpx TLEN
 bcs @oldnext
 lda B,x
 cmp #'*'
 jeq invalid
 cmp #'@'
 jeq invalid
 cmp #$5C
 jeq invalid
@oldnext:
 inx
 cpx W
 bcc @old
 ldx EDIT
 lda SIGN
 cmp #1
 beq @source
 lda B,x
 jsr alnum
 jcs invalid
@source:
 ldx #0
@copy_packet:
 lda B,x
 sta P,x
 inx
 cpx #240
 bcc @copy_packet
 lda #0
 sta COL
@byte:
 ldx COL
 cpx NLEN
 bcs @terminator
 jsr se_view_peek
 jcs invalid
 ldx COL
 sta P,x
 cpx EDIT
 bcc @same
 bne @after
 lda SIGN
 cmp #1
 bne @after
 lda P,x
 jsr alnum
 jcs invalid
 jmp @next
@after:
 lda SIGN
 cmp #1
 bne @deleted
 dex
 jmp @same
@deleted:
 inx
@same:
 lda B,x
 ldx COL
 cmp P,x
 jne invalid
@next:
 inc se_v_pos
 bne :+
 inc se_v_pos+1
 bne :+
 inc se_v_pos+2
: inc COL
 jmp @byte
@terminator:
 CMP24 se_v_pos,se_v_length
 beq @fill
 jsr se_view_peek
 jcs invalid
 cmp #13
 jne invalid
@fill:
 ldx COL
 lda #32
@space:
 sta P,x
 inx
 cpx W
 bcc @space
 lda #0
 ldx W
 dex
@flags:
 sta P+80,x
 sta P+160,x
 dex
 bpl @flags
 lda OLDCOL
 clc
 adc SIGN
 sta NEWCOL
 tax
 lda #4
 sta P+160,x
 lda #1
 sta NEWSEEN
 lda #<P
 sta PTR
 lda #>P
 sta PTR+1
 clc
 rts
alpha:
 and #$7F
 and #$DF
 cmp #'A'
 bcc type_bad
 cmp #'Z'+1
 bcs type_bad
 clc
 rts
alnum:
 cmp #'0'
 bcc alpha
 cmp #'9'+1
 bcs alpha
 clc
 rts
type_bad:
 sec
 rts

type_commit:
 ; The leaf has painted successfully. Publish only owned exact packet+metadata.
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
 ; Rebase all later canonical anchors, including viewport bottom.
 lda ROW
 clc
 adc #1
 sta COL
@row:
 lda COL
 asl
 clc
 adc COL
 tax
 clc
 lda se_v_rows,x
 adc SIGN
 sta se_v_rows,x
 lda SIGN
 bmi @minus
 lda #0
 jmp @mid
@minus:
 lda #$FF
@mid:
 adc se_v_rows+1,x
 sta se_v_rows+1,x
 lda SIGN
 bmi @minushi
 lda #0
 jmp @hi
@minushi:
 lda #$FF
@hi:
 adc se_v_rows+2,x
 sta se_v_rows+2,x
 inc COL
 lda COL
 cmp #22
 bcc @row
 ; Bottom is a separate VIEW field.
 clc
 lda se_v_bottom
 adc SIGN
 sta se_v_bottom
 lda SIGN
 bmi :+
 lda #0
 beq :++
: lda #$FF
: adc se_v_bottom+1
 sta se_v_bottom+1
 lda SIGN
 bmi :+
 lda #0
 beq :++
: lda #$FF
: adc se_v_bottom+2
 sta se_v_bottom+2
 ldx #3
@rev:
 lda se_r_revision,x
 sta se_l_revision,x
 sta se_st_descriptor+17,x
 dex
 bpl @rev
 ldx #2
@length:
 lda se_v_length,x
 sta se_st_descriptor+21,x
 lda se_hot_caret,x
 sta se_l_caret,x
 sta H+N_CARET,x
 dex
 bpl @length
 lda #0
 sta se_st_cp_valid
 sta OP
 jsr fields
 jcs invalid
 lda #1
 sta OP
 sta se_v_seen
 sta H+N_SEEN
 lda NEWROW
 sta se_v_caret_row
 sta H+N_ROW
 lda NEWCOL
 sta se_v_caret_col
 sta H+N_COL
 clc
 lda se_e_draw_sequence
 adc #1
 sta H+N_SEQUENCE
 lda se_e_draw_sequence+1
 adc #0
 sta H+N_SEQUENCE+1
 jmp store_header
