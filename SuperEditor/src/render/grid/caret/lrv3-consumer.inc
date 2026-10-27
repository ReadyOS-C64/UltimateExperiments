; Plain fixed-grid direct-row transaction. Frame18 prepares one authenticated
; local row from the retained physical anchors; frames14/15/17 consume it and
; keep the old wide-grid header private until the painted row succeeds.
.include "render/grid/paragraph/lrv3.inc"
.include "render/geos/edit-certificate.inc"

LRVT=$8D00
LT_WIDTH=1
LT_SIGN=2
LT_FIRST=3
LT_ROWS=4
LT_FLAGS=7
LT_REL=8
LT_START=9                 ;3
LT_LENGTH=12               ;2
LT_ROW=14
LT_CARET_ROW=15
LT_CARET_COL=16
LT_CLIP=18                 ;2, visible logical-row offset
LT_GC_VALID=25             ;3
LT_COVER=34
LT_PREPARED=35
LT_HINT=36
LT_HOT_POS=37              ;3
LT_HOT_NEXT=40             ;3
LT_HOT_DELTA=43            ;2
LT_HOT_REV=45              ;4, separate from the length/row scratch

; Frame14 resumes the exact frame18 transaction. R25 remains resident across
; C6 -> resident -> C33; there is no persistent LRV object in this slice.
lrv_admit:
 lda se_st_tx+ST_TX_PHASE
 cmp #ST_TX_READY
 jeq lrv_style_admit
 lda GEC_VALID
 cmp #1
 jne lrv_bad
 lda se_render_caps
 jne lrv_bad
 lda se_mode
 cmp LRVT+LT_FLAGS
 jne lrv_bad
 ldx #1
@sequence:
 lda GEC_SEQUENCE,x
 cmp se_e_draw_sequence,x
 jne lrv_bad
 dex
 bpl @sequence
 ldx #2
@gc:
 lda se_gc_valid,x
 sta LRVT+LT_GC_VALID,x
 dex
 bpl @gc
 lda #0
 sta LRVT+LT_REL
 sta LRVT+LT_CARET_ROW
 sta LRVT+LT_CARET_COL
 jsr lrv_span_check
 rts

; READY is authenticated once here, then expanded into the existing local-row
; transaction. No later row call needs to reload R25.
lrv_style_admit:
 lda #ST_TX_CHECK_SEED
 ldx #ST_TX_BYTES-1
@check:
 eor se_st_tx,x
 dex
 bne @check
 cmp #ST_TX_READY
 jne lrv_bad
 lda se_st_valid
 jne lrv_bad
 lda se_st_request
 cmp #0
 jne lrv_bad
 lda se_st_cp_valid
 cmp #1
 jne lrv_bad
 lda se_render_caps
 jeq lrv_bad
 lda se_mode
 cmp #3
 jcs lrv_bad
 tax
 ora #$80
 sta LRVT+LT_FLAGS
 lda lrv_widths,x
 sta LRVT+LT_WIDTH
 lda se_mode
 asl
 ora se_l_mode
 asl
 asl
 asl
 asl
 asl
 eor se_st_tx+ST_TX_ROW_MODE
 and #ST_TX_MODE_MASK
 jne lrv_bad
 lda se_st_tx+ST_TX_ROW_MODE
 and #ST_TX_ROW_MASK
 cmp #22
 jcs lrv_bad
 sta LRVT+LT_FIRST
 lda se_st_tx+ST_TX_COUNT_KIND
 and #ST_TX_COUNT_MASK
 jeq lrv_bad
 sta LRVT+LT_ROWS
 clc
 adc LRVT+LT_FIRST
 cmp se_st_cp_count
 jcs lrv_bad
 cmp #23
 jcs lrv_bad
 lda #ST_TX_DELETE
 bit se_st_tx+ST_TX_COUNT_KIND
 beq :+
 lda #$FF
 bne :++
: lda #1
: sta LRVT+LT_SIGN
 ldx #1
@sequence:
 lda se_st_tx+ST_TX_SEQUENCE,x
 cmp se_e_draw_sequence,x
 jne lrv_bad
 dex
 bpl @sequence
 ldx #3
@revision:
 lda se_st_tx+ST_TX_REVISION,x
 cmp se_r_revision,x
 jne lrv_bad
 dex
 bpl @revision
 ldx #1
@identity:
 lda se_st_tx+ST_TX_DOC_GENERATION,x
 cmp se_doc_generation,x
 jne lrv_bad
 lda se_st_tx+ST_TX_DOC_EPOCH,x
 cmp se_doc_epoch,x
 jne lrv_bad
 dex
 bpl @identity
 jsr se_view_init
 jcs lrv_bad
 ldx #2
@start:
 lda se_st_tx+ST_TX_START,x
 sta LRVT+LT_START,x
 dex
 bpl @start
 sec
 lda se_st_tx+ST_TX_END
 sbc se_st_tx+ST_TX_START
 sta LRVT+LT_LENGTH
 lda se_st_tx+ST_TX_END+1
 sbc se_st_tx+ST_TX_START+1
 sta LRVT+LT_LENGTH+1
 lda se_st_tx+ST_TX_END+2
 sbc se_st_tx+ST_TX_START+2
 jne lrv_bad
 lda LRVT+LT_FIRST
 asl
 clc
 adc LRVT+LT_FIRST
 tax
 ldy #0
@anchor:
 lda se_v_rows,x
 cmp LRVT+LT_START,y
 jne lrv_bad
 inx
 iny
 cpy #3
 bcc @anchor
 CMP24 se_v_length,se_st_tx+ST_TX_END
 jcc lrv_bad
 lda se_mode
 beq @expanded
 jsr lrv_save_header
 jcs lrv_bad
@expanded:
 lda LRVT+LT_LENGTH
 ora LRVT+LT_LENGTH+1
 bne @nonempty
 CMP24 se_st_tx+ST_TX_END,se_v_length
 jne lrv_bad
 jmp @record_ready
@nonempty:
 COPY24 se_st_tx+ST_TX_END,se_v_pos
 jsr retreat
 jsr se_view_peek
 jcs lrv_bad
 cmp #13
 beq @cr
 CMP24 se_st_tx+ST_TX_END,se_v_length
 jne lrv_bad
 jmp @record_ready
@cr:
 lda LRVT+LT_LENGTH
 bne :+
 dec LRVT+LT_LENGTH+1
: dec LRVT+LT_LENGTH
@record_ready:
 lda #0
 sta LRVT+LT_REL
 sta LRVT+LT_CARET_ROW
 sta LRVT+LT_CARET_COL
 ldx #2
@gc:
 lda se_gc_valid,x
 sta LRVT+LT_GC_VALID,x
 dex
 bpl @gc
 jsr lrv_span_check
 rts

; Frame17.  Rekey the grid authority only after all row leaves succeeded.
lrv_finish:
 lda LRVT+LT_REL
 cmp LRVT+LT_ROWS
 jne lrv_bad
 lda se_mode
 jeq @success
 lda LRVT+LT_CARET_ROW
 sta H+N_ROW
 lda LRVT+LT_CARET_COL
 sta H+N_COL
 lda #1
 sta H+N_SEEN
 ldx #2
@header_valid:
 lda LRVT+LT_GC_VALID,x
 sta H+N_VALID,x
 dex
 bpl @header_valid
 ldx #3
@header_revision:
 lda se_r_revision,x
 sta H+N_KEY+17,x
 bit LRVT+LT_FLAGS
 bpl :+
 sta H+N_STYLE+17,x
 sta se_st_descriptor+17,x
: dex
 bpl @header_revision
 ldx #2
@header_caret:
 lda se_hot_caret,x
 sta H+N_CARET,x
 dex
 bpl @header_caret
 lda se_hot_pending
 sta H+N_PENDING
 ldx #1
@hotlen:
 lda se_hot_length,x
 sta H+N_HOTLEN,x
 dex
 bpl @hotlen
 ldx #2
@length:
 lda se_v_length,x
 sta H+N_KEY+21,x
 bit LRVT+LT_FLAGS
 bpl :+
 sta H+N_STYLE+21,x
 sta se_st_descriptor+21,x
: dex
 bpl @length
 clc
 lda se_e_draw_sequence
 adc #1
 sta H+N_SEQUENCE
 lda se_e_draw_sequence+1
 adc #0
 sta H+N_SEQUENCE+1
 lda LRVT+LT_FLAGS
 bpl @store
 clc
 lda se_st_generation
 adc #1
 sta H+N_STYLE+STYLE_KEY_BYTES
 lda se_st_generation+1
 adc #0
 sta H+N_STYLE+STYLE_KEY_BYTES+1
 lda #1
 sta H+N_STYLE+STYLE_KEY_BYTES+2
 lda #0
 sta H+N_STYLE+STYLE_KEY_BYTES+3
@store:
 jsr store_header
 jcs lrv_bad
@success:
 lda LRVT+LT_FLAGS
 bpl @plain
 lda se_mode
 bne @descriptor_done
 ldx #3
@descriptor_revision:
 lda se_r_revision,x
 sta se_st_descriptor+17,x
 dex
 bpl @descriptor_revision
 ldx #2
@descriptor_length:
 lda se_v_length,x
 sta se_st_descriptor+21,x
 dex
 bpl @descriptor_length
@descriptor_done:
 inc se_st_generation
 bne :+
 inc se_st_generation+1
: lda #1
 sta se_st_valid
 lda #ST_TX_INVALID
 sta se_st_tx+ST_TX_PHASE
@plain:
 clc
 rts

lrv_plain_update:
 lda se_f_owner
 cmp #4
 jne lrv_bad
 lda se_render_caps
 ora se_ef_count
 ora se_ef_count+1
 jne lrv_bad
 lda GEC_VALID
 cmp #1
 jne lrv_bad
 lda GEC_OLD
 cmp #13
 jeq lrv_bad
 lda GEC_NEW
 cmp #13
 jeq lrv_bad
 lda se_mode
 cmp #3
 jcs lrv_bad
 sta LRVT+LT_FLAGS
 tax
 lda lrv_widths,x
 sta LRVT+LT_WIDTH
 cpx #0
 beq :+
 cmp se_v_columns
 jne lrv_bad
:
 lda se_overlay_frame+1
 cmp #22
 jcs lrv_bad
 sta LRVT+LT_HINT
 lda GEC_OP
 cmp #1
 bcc @insert
 jne lrv_bad
 lda GEC_NEW
 jne lrv_bad
 lda GEC_OLD
 jeq lrv_bad
 lda #$ff
 bne @sign
@insert:
 lda GEC_OLD
 jne lrv_bad
 lda GEC_NEW
 jeq lrv_bad
 lda #1
@sign:
 sta LRVT+LT_SIGN
 ; Materialize the expected post-edit length before comparing; no compare may
 ; disturb the multi-byte carry chain.
 ldx #2
@copy_length:
 lda GEC_LENGTH,x
 sta LRVT+LT_HOT_NEXT,x
 dex
 bpl @copy_length
 lda LRVT+LT_SIGN
 bmi @length_dec
 inc LRVT+LT_HOT_NEXT
 bne @length_ready
 inc LRVT+LT_HOT_NEXT+1
 bne @length_ready
 inc LRVT+LT_HOT_NEXT+2
 bne @length_ready
 jeq lrv_bad
@length_dec:
 lda LRVT+LT_HOT_NEXT
 bne @length_dec_low
 lda LRVT+LT_HOT_NEXT+1
 bne @length_dec_mid
 dec LRVT+LT_HOT_NEXT+2
@length_dec_mid:
 dec LRVT+LT_HOT_NEXT+1
@length_dec_low:
 dec LRVT+LT_HOT_NEXT
@length_ready:
 ; The retained row map is pre-edit authority, but se_v_length must describe
 ; the already-committed document before we compare the expected new length.
 jsr se_view_init
 jcs lrv_bad
 ldx #2
@length_cmp:
 lda LRVT+LT_HOT_NEXT,x
 cmp se_v_length,x
 jne lrv_bad
 dex
 bpl @length_cmp
 ; Exactly one revision increment, materialized before comparison.
 ldx #3
@copy_revision:
 lda GEC_REVISION,x
 sta LRVT+LT_HOT_REV,x
 dex
 bpl @copy_revision
 inc LRVT+LT_HOT_REV
 bne @revision
 inc LRVT+LT_HOT_REV+1
 bne @revision
 inc LRVT+LT_HOT_REV+2
 bne @revision
 inc LRVT+LT_HOT_REV+3
 jeq lrv_bad
@revision:
 ldx #3
@revision_cmp:
 lda LRVT+LT_HOT_REV,x
 cmp se_r_revision,x
 jne lrv_bad
 dex
 bpl @revision_cmp
 ldx #1
@epochs:
 lda GEC_DOC_EPOCH,x
 cmp se_doc_epoch,x
 jne lrv_bad
 lda GEC_REU_EPOCH,x
 cmp se_reu_epoch,x
 jne lrv_bad
 dex
 bpl @epochs
 ; Preserve the old authenticated NC header for the later 60/80 row commits.
 jsr lrv_save_header
 jcs lrv_bad
@header:
 lda se_l_mode
 sta LRVT+LT_COVER
 lda LRVT+LT_HINT
 asl
 clc
 adc LRVT+LT_HINT
 tax
 ldy #0
@start:
 lda se_v_rows,x
 sta LRVT+LT_HOT_POS,y
 inx
 iny
 cpy #3
 bcc @start
 lda LRVT+LT_HINT
 cmp #21
 bne @next_row
 ldy #2
@bottom:
 lda se_v_bottom,y
 sta LRVT+LT_HOT_NEXT,y
 dey
 bpl @bottom
 jmp @adjust_next
@next_row:
 ldy #0
@next:
 lda se_v_rows,x
 sta LRVT+LT_HOT_NEXT,y
 inx
 iny
 cpy #3
 bcc @next
@adjust_next:
 jsr lrv_adjust_next
 sec
 lda LRVT+LT_HOT_NEXT
 sbc LRVT+LT_HOT_POS
 sta LRVT+LT_HOT_DELTA
 lda LRVT+LT_HOT_NEXT+1
 sbc LRVT+LT_HOT_POS+1
 sta LRVT+LT_HOT_DELTA+1
 lda LRVT+LT_HOT_NEXT+2
 sbc LRVT+LT_HOT_POS+2
 jne lrv_bad
 lda LRVT+LT_HOT_DELTA
 ora LRVT+LT_HOT_DELTA+1
 beq @empty
 COPY24 LRVT+LT_HOT_NEXT,se_v_pos
 jsr retreat
 jsr se_view_peek
 jcs lrv_bad
 cmp #13
 bne @eof
 sec
 lda LRVT+LT_HOT_DELTA
 sbc #1
 sta LRVT+LT_HOT_DELTA
 lda LRVT+LT_HOT_DELTA+1
 sbc #0
 sta LRVT+LT_HOT_DELTA+1
 jcc lrv_bad
 jmp @selected
@eof:
 CMP24 LRVT+LT_HOT_NEXT,se_v_length
 jne lrv_bad
 jmp @selected
@empty:
 CMP24 LRVT+LT_HOT_POS,se_v_length
 jne lrv_bad
@selected:
 ldx #2
@save_start:
 lda LRVT+LT_HOT_POS,x
 sta LRVT+LT_START,x
 dex
 bpl @save_start
 lda LRVT+LT_HOT_DELTA
 sta LRVT+LT_LENGTH
 lda LRVT+LT_HOT_DELTA+1
 sta LRVT+LT_LENGTH+1
 lda LRVT+LT_HINT
 sta LRVT+LT_FIRST
 lda #1
 sta LRVT+LT_ROWS
 jsr lrv_check_edit_row
 jcs lrv_bad
 lda #LRV_PUBLISHED
 sta LRVT+LT_PREPARED
 lda #0
 clc
 rts

lrv_adjust_next:
 lda LRVT+LT_SIGN
 bmi @dec
 inc LRVT+LT_HOT_NEXT
 bne @done
 inc LRVT+LT_HOT_NEXT+1
 bne @done
 inc LRVT+LT_HOT_NEXT+2
 rts
@dec:
 lda LRVT+LT_HOT_NEXT
 bne @dec_low
 lda LRVT+LT_HOT_NEXT+1
 bne @dec_mid
 dec LRVT+LT_HOT_NEXT+2
@dec_mid:
 dec LRVT+LT_HOT_NEXT+1
@dec_low:
 dec LRVT+LT_HOT_NEXT
@done:
 rts

lrv_check_edit_row:
 lda LRVT+LT_HOT_DELTA+1
 jne @bad
 lda LRVT+LT_HOT_DELTA
 cmp LRVT+LT_WIDTH
 bcs @bad
 sta POS
 lda #0
 sta POS+1
 sta POS+2
 lda GEC_OP
 beq @insert
 inc POS
 lda POS
 cmp LRVT+LT_WIDTH
 bcs @bad
 jmp @bounds
@insert:
 lda POS
 jeq @bad
 dec POS
@bounds:
 clc
 lda LRVT+LT_HOT_POS
 adc POS
 sta POS
 lda LRVT+LT_HOT_POS+1
 adc #0
 sta POS+1
 lda LRVT+LT_HOT_POS+2
 adc #0
 sta POS+2
 CMP24 GEC_POSITION,LRVT+LT_HOT_POS
 bcc @bad
 CMP24 GEC_POSITION,POS
 bcc @ok
 bne @bad
 lda GEC_OP
 beq @ok
@bad:
 sec
 rts
@ok:
 clc
 rts

; Authenticate and retain the old narrow-cache header once per transaction.
lrv_save_header:
 lda se_mode
 beq @done
 lda #1
 sta C+63
 jsr admit
 jcs @return
 jsr fetch_header
 jcs @return
 jsr header_crc
 ldx #1
@crc:
 lda se_crc_value,x
 cmp H+N_CRC,x
 bne @bad
 dex
 bpl @crc
 lda H
 cmp #'N'
 bne @bad
 lda H+1
 cmp #'C'
 bne @bad
 lda H+2
 cmp #1
 bne @bad
 lda H+3
 cmp #LRV_PUBLISHED
 bne @bad
@done:
 clc
@return:
 rts
@bad:
 sec
 rts

; Prove the last selected row starts within the authenticated logical length.
lrv_span_check:
 lda LRVT+LT_ROWS
 sta NEXT
 lda #0
 sta NEXT+1
 lda NEXT
 bne :+
 dec NEXT+1
:
 dec NEXT
 lda #0
 sta NEXT+2
 sta POS
 sta POS+1
 sta POS+2
 lda LRVT+LT_WIDTH
 sta COL
@bit:
 lsr COL
 bcc @shift
 clc
 lda POS
 adc NEXT
 sta POS
 lda POS+1
 adc NEXT+1
 sta POS+1
 lda POS+2
 adc NEXT+2
 sta POS+2
@shift:
 asl NEXT
 rol NEXT+1
 rol NEXT+2
 lda COL
 bne @bit
 lda POS+2
 bne @bad
 lda POS+1
 cmp LRVT+LT_LENGTH+1
 bcc @ok
 bne @bad
 lda POS
 cmp LRVT+LT_LENGTH
 bcc @ok
 beq @ok
@bad:
 sec
 rts
@ok:
 ; Wrapped layout needs exactly this many rows. The lower bound above rejects
 ; shrinkage; this strict upper bound also rejects an added terminal caret row.
 lda se_l_mode
 bne @valid
 clc
 lda POS
 adc LRVT+LT_WIDTH
 sta POS
 bcc :+
 inc POS+1
:
 lda LRVT+LT_LENGTH+1
 cmp POS+1
 bcc @valid
 bne @bad
 lda LRVT+LT_LENGTH
 cmp POS
 bcs @bad
@valid:
 clc
 rts

lrv_bad:
 lda #LRV_ERROR
 sec
 rts

.segment "RODATA"
lrv_widths:.byte 40,60,80
