; Private C33 long-row coordinator. All pixel work is after complete validation.
.include "long.inc"
TLEN=C+59
NLEN=C+60
EDIT=C+61
SIGN=C+62
.import se_i_ready,se_i_count,se_n_cache_count
LS_EDIT=LS+20
RG_GEOM=$8DFF
long_try:
 lda se_render_caps
 bne @prepared_worker
 ldy #3
 jsr authenticate_dependencies
 jcs miss
@prepared_worker:
 lda #16
 jsr helper
 jcs @bad1
 lda se_render_caps
 beq @raw_edit
 lda EDIT
 jeq @bad1
 clc
 adc #1
 cmp W
 jcs @bad1
 jmp @edit_ready
@raw_edit:
 lda SIGN
 bpl @raw_index
 lda OLDCOL
 bne @raw_index
 lda ROW
 jeq miss
 dec ROW
 lda W
 sec
 sbc #1
 sta EDIT
 jsr bounds
 jcs miss
 SUB24 END,POS,DELTA
 lda DELTA+1
 ora DELTA+2
 jne miss
 lda DELTA
 cmp W
 jne miss
@raw_index:
 lda EDIT
 cmp W
 jcs miss
@edit_ready:
 lda #0
 sta se_i_ready
 sta se_i_count
 sta se_n_cache_count
 sta RG_GEOM
 lda ROW
 sta LS_FIRST
 sta LS_ROW
 sta NEWROW
 lda EDIT
 sta LS_EDIT
 lda se_render_caps
 beq @raw_caret
 lda OLDCOL
 clc
 adc SIGN
 sta NEWCOL
 cmp W
 jcs @bad1
 jmp @caret_ready
@raw_caret:
 lda EDIT
 ldx SIGN
 cpx #1
 bne :+
 clc
 adc #1
: sta NEWCOL
 cmp W
 bcc @caret_ready
 lda #0
 sta NEWCOL
 inc NEWROW
 lda NEWROW
 cmp #22
 jcs miss
@caret_ready:
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
 jcs @bad1
 lda se_render_caps
 beq @raw_row
 jsr row_bit
 tax
 lda B+111,x
 and BITMASK
 jeq @bad1
@raw_row:
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
 jcs @geometry_boundary ;new boundary is admitted only by new R24
 jmp @packet
@deleting:
 lda LS_COUNT
 jeq @geometry_boundary
 jmp @packet
@geometry_boundary:
 lda se_render_caps
 jne @bad1
 lda #5
 jsr geometry
 jcs @bad1
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
 ; Stage just one realnarrowglyph before swapping to the pixelworker.
 lda SIGN
 bmi @tail_glyph
 lda LS_NEW
 sta TLEN
 jmp @fetch_glyph
@tail_glyph:
 lda LS_TAIL
 sta TLEN
@fetch_glyph:
 lda #18
 jsr helper
 jcs miss
 lda SIGN
 bpl @staged_glyph
 ldx #7
@tail_copy:
 lda LPF+4,x
 sta LS_TAILINK,x
 dex
 bpl @tail_copy
@staged_glyph:
 lda se_render_caps
 bne @worker_ready
 lda #6
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 jcs miss
@worker_ready:
 lda RG_GEOM
 beq :+
 lda #3
 jsr geometry
 jcs miss
:
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
 lda LS_EDIT
: sta LPF+2
 lda SIGN
 bpl @shift
 lda ROW
 cmp LS_LAST
 beq @tail_ink
 jsr long_next_ink
 jmp @shift
@tail_ink:
 ldx #7
@copy_ink:
 lda LS_TAILINK,x
 sta LPF+4,x
 dex
 bpl @copy_ink
@shift:
 lda #7
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 jcs miss
 ldx #7
@carry:
 lda LPF+12,x
 sta LPF+4,x
 dex
 bpl @carry
 lda ROW
 cmp LS_LAST
 beq @paint_done
 inc ROW
 jmp @paint
@paint_done:
 lda RG_GEOM
 beq :+
 lda #4
 jsr geometry
 jcs miss
:
 lda NEWROW
 sta ROW
 lda NEWCOL
 jsr xor_cell
 jsr status
 jcs miss
 ; R25 packets remain untouched while pixels carry. Publishthemforward only
 ; after everyphysicalrow hascompleted; a failedcall leavescacheinvalid.
 lda LS_FIRST
 sta ROW
 lda LS_EDIT
 sta EDIT
 lda LS_NEW
 sta LS_CHAIN
@packets:
 lda #<P
 ldx #>P
 jsr fetch_row
 jcs miss
 lda SIGN
 bpl @insert_packet
 lda ROW
 cmp LS_LAST
 beq @tail_char
 inc ROW
 lda #<B
 ldx #>B
 jsr fetch_row
 jcs miss
 dec ROW
 lda B
 jmp @char
@tail_char:
 lda LS_TAIL
 jmp @char
@insert_packet:
 lda LS_CHAIN
@char:
 sta TLEN
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
 jmp @packets
@finish:
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

; Nextrow's untouchedfirstglyph after theoldcaret wasremoved. Native4/5px
; normalization exactlymatches the core's glyphplaneinput.
long_next_ink:
 lda #8
 sta screen_ptr
 lda #$60
 sta screen_ptr+1
 lda W
 cmp #60
 beq :+
 lda #0
 sta screen_ptr
: ldx ROW
 inx
 inx
 inx
@row:
 clc
 lda screen_ptr
 adc #$40
 sta screen_ptr
 lda screen_ptr+1
 adc #1
 sta screen_ptr+1
 dex
 bne @row
 ldy #7
@ink:
 lda (screen_ptr),y
 ldx W
 cpx #60
 bne :+
 asl
 asl
: sta LPF+4,y
 dey
 bpl @ink
 rts

.segment "TAIL"
long_alnum:
 ldx se_render_caps
 bne :+
 cmp #13
 beq @bad
 clc
 rts
:
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
