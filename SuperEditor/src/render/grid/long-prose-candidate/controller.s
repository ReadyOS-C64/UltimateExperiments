; Private C33 long-row coordinator. All pixel work is after complete validation.
.include "long.inc"
TLEN=C+59
NLEN=C+60
EDIT=C+61
SIGN=C+62
.import se_i_ready,se_i_count,se_n_cache_count
.import se_lp_shift_row
long_try:
 lda #16
 jsr helper
 bcs @bad1
 lda EDIT
 beq @bad1
 clc
 adc #1
 cmp W
 bcs @bad1
 lda #0
 sta se_i_ready
 sta se_i_count
 sta se_n_cache_count
 lda ROW
 sta LS_FIRST
 sta LS_ROW
 sta NEWROW
 lda OLDCOL
 clc
 adc SIGN
 sta NEWCOL
 cmp W
 bcs @bad1
 lda #0
 sta LS_NOEND
 lda POS
 sta se_v_pos
 lda POS+1
 sta se_v_pos+1
 lda POS+2
 sta se_v_pos+2
 jmp @validate
@bad1:jmp miss
@validate:
 jsr bounds
 bcs @bad1
 jsr row_bit
 tax
 lda B+111,x
 and BITMASK
 beq @bad1
 SUB24 END,POS,DELTA
 lda DELTA+1
 ora DELTA+2
 bne @bad1
 lda DELTA
 sta LS_COUNT
 cmp W
 bcc @terminal
 bne @bad1
 lda ROW
 cmp #21
 bcc @packet
 lda #1
 sta LS_NOEND
 bne @packet
@terminal:
 lda SIGN
 bmi @deleting
 lda LS_COUNT
 clc
 adc #1
 cmp W
 bcs @bad1 ;no newly introduced physical row
 jmp @packet
@deleting:
 lda LS_COUNT
 beq @bad1 ;no removal of an existing physical row
@packet:
 lda #80
 sta screen_ptr
 lda #$40
 sta screen_ptr+1
 ldx ROW
 beq @attrs
@attr_row:
 clc
 lda screen_ptr
 adc #40
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: dex
 bne @attr_row
@attrs:
 ldy #39
@attr:
 lda (screen_ptr),y
 cmp #$16
 jne miss
 dey
 bpl @attr
 lda #<P
 ldx #>P
 jsr fetch_row
 jcs miss
 jsr verify_row
 jcs miss
 ldx #0
@plain:
 lda P+80,x
 jne miss
 lda P+160,x
 and #$fb
 jne miss
 inx
 cpx W
 bcc @plain
 lda #0
 sta LS_COL
@compare:
 ldx LS_COL
 cpx LS_COUNT
 bcs @row_done
 lda ROW
 cmp LS_FIRST
 bne @same
 cpx EDIT
 bne @same
 lda SIGN
 bmi @skip
 jsr se_view_peek
 jcs miss
 sta LS_NEW
 sta LS_CHAIN
 jsr long_alnum
 jcs miss
 jsr long_advance
 jmp @same
@skip:
 lda P,x
 jsr long_alnum
 jcs miss
 jmp @next
@same:
 jsr se_view_peek
 jcs miss
 ldx LS_COL
 cmp P,x
 jne miss
 jsr long_advance
@next:
 inc LS_COL
 jmp @compare
@row_done:
 lda LS_COUNT
 cmp W
 bcc @end
 lda ROW
 cmp #21
 beq @end
 inc ROW
 jmp @validate
@end:
 lda ROW
 sta LS_LAST
 lda LS_NOEND
 bne @tail
 CMP24 se_v_pos,se_v_length
 beq @blank_tail
 jsr se_view_peek
 jcs miss
 cmp #13
 jne miss
@blank_tail:
 lda #32
 sta LS_TAIL
 jmp @staged
@tail:
 lda SIGN
 cmp #1
 beq @staged
 jsr se_view_peek
 jcs miss
 cmp #13
 jeq miss
 sta LS_TAIL
@staged:
 ; Borrowing8000 invalidates its previous merged-source cache authority.
 jsr se_doc_invalidate
 ldx #2
@invalid:
 lda se_gc_valid,x
 sta LS_GC,x
 lda #0
 sta se_gc_valid,x
 dex
 bpl @invalid
 lda OLDROW
 sta ROW
 lda OLDCOL
 jsr xor_cell
 lda LS_FIRST
 sta ROW
 sta LS_ROW
 lda W
 sta LPF
 lda #0
 ldx SIGN
 cpx #1
 beq :+
 lda #1
: sta LPF+3
@paint:
 lda ROW
 sta LPF+1
 lda #0
 ldx ROW
 cpx LS_FIRST
 bne :+
 lda EDIT
: sta LPF+2
 sta EDIT
 lda #<P
 ldx #>P
 jsr fetch_row
 jcs miss
 lda SIGN
 cmp #1
 beq @insert
 lda ROW
 cmp LS_LAST
 beq @last_ink
 inc ROW
 lda #<B
 ldx #>B
 jsr fetch_row
 jcs miss
 dec ROW
 lda B
 sta TLEN
 jmp @shift
@last_ink:
 lda LS_TAIL
 sta TLEN
 jmp @shift
@insert:
 lda LS_CHAIN
 sta TLEN
@shift:
 lda #18
 jsr helper
 jcs miss
 jsr se_lp_shift_row
 jcs miss
 lda #17
 jsr helper
 jcs miss
 lda NLEN
 sta LS_CHAIN
 lda ROW
 cmp LS_LAST
 beq @finish
 inc ROW
 lda #0
 sta EDIT
 jmp @paint
@finish:
 lda NEWROW
 sta ROW
 lda NEWCOL
 jsr xor_cell
 jsr status
 jcs miss
 ldx #2
@valid:
 lda LS_GC,x
 sta se_gc_valid,x
 dex
 bpl @valid
 lda LS_LAST
 sta ROW
 lda #15
 jsr helper
 jcs miss
 jmp success

.segment "TAIL"
long_alnum:
 cmp #'0'
 bcc @alpha
 cmp #'9'+1
 bcc @ok
@alpha:
 and #$7f
 cmp #'A'
 bcc @bad
 cmp #'Z'+1
 bcs @bad
@ok:
 clc
 rts
@bad:
 sec
 rts
long_advance:
 inc se_v_pos
 bne :+
 inc se_v_pos+1
 bne :+
 inc se_v_pos+2
: rts
