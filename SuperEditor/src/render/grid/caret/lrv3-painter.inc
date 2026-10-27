; C33 frame1/4: consume the prepared Plain direct-row transaction. There are
; no calls to the cold parser/layout producer on this path.
.include "render/grid/paragraph/lrv3.inc"
.include "render/geos/edit-certificate.inc"
LRVT=$8D00
LRV_OLD_NC=$8500
LT_WIDTH=1
LT_FIRST=3
LT_ROWS=4
LT_REL=8
LT_START=9
LT_LENGTH=12
LT_ROW=14
LT_CARET_ROW=15
LT_CARET_COL=16
LT_RECORD_FLAGS=17
LT_CLIP=18
LT_SOURCE=20
LT_GC_VALID=25
LT_COVER=34
LT_CELL_VALID=7
LS_ROW=LRVT+40
LS_POS=LRVT+41
LS_NEXT=LRVT+44
LS_DELTA=LRVT+47
LS_AFTER=LRVT+50

lrv_paint_entry:
 ldx se_f_owner
 jne opaque
 lda #4
 sta se_f_owner
 lda LRVT+35                ;LT_PREPARED
 cmp #LRV_PUBLISHED
 jne miss
 lda #0
 sta LRVT+35                ;retire before any queued-state refusal
 lda #1
 sta OP
 sta C+63
 jsr authenticate_helper
 jcs miss
 ; The prepared transaction is consumable only while its exact R25 image and
 ; editor state remain current.  A queued command forces the ordinary redraw.
 inx
 cpx se_overlay_active
 jne miss
 lda se_e_ui
 ora se_e_job
 ora se_e_draw_busy
 ora se_r_presentation
 ora se_sel_mark
 jne miss
 lda LRVT+LT_COVER
 cmp se_l_mode
 jne miss
 lda LRVT+LT_FIRST
 asl
 clc
 adc LRVT+LT_FIRST
 tax
 ldy #0
@top:
 lda se_v_rows,x
 cmp LRVT+LT_START,y
 jne miss
 inx
 iny
 cpy #3
 bcc @top
 ldx #2
@position:
 lda GEC_POSITION,x
 sta NEXT,x
 dex
 bpl @position
 lda GEC_OP
 bne @caret_ready
 inc NEXT
 bne @caret_ready
 inc NEXT+1
 bne @caret_ready
 inc NEXT+2
@caret_ready:
 ldx #2
@caret:
 lda NEXT,x
 cmp se_hot_caret,x
 jne miss
 dex
 bpl @caret
 lda #14
 jsr helper
 jcs miss
 jsr lrv_span_check
 jcs miss
 lda se_mode
 beq @validated
 lda LRVT+LT_WIDTH
 sta W
 lda #18
 sec
 sbc se_mode
 sta BACKEND
 lda #2
 jsr leaf
 jcs miss
@validated:
 jsr se_doc_invalidate
 lda #0
 sta se_gc_valid
 sta se_gc_valid+1
 sta se_gc_valid+2
@row:
 lda #15
 jsr helper
 jcs miss
 cmp #1
 beq @finish
 jsr lrv_build_packet
 jcs miss
 lda se_mode
 beq @text40
 jsr lrv_native_row
 jcs miss
 jmp @commit
@text40:
 jsr lrv_text_row
 jcs miss
@commit:
 jsr lrv_commit_row
 jcs miss
@finish:
 lda se_mode
 beq @status40
 jsr status
 jcs miss
 jmp @status_done
@status40:
 jsr tui_editor_status40
@status_done:
 jsr lrv_finish_state
 jcs miss
 lda #17
 jsr helper
 jcs miss
 jmp success

; Pure resident-layout commit. R25 still owns the CRC-covered NC header write.
lrv_finish_state:
 clc
 lda LRVT+LT_FIRST
 adc LRVT+LT_ROWS
 sta COL
@row:
 lda COL
 cmp #22
 bcs @bottom
 asl
 clc
 adc COL
 tax
 jsr @rows
 inc COL
 bne @row
@bottom:
 lda #<se_v_bottom
 sta text_ptr
 lda #>se_v_bottom
 sta text_ptr+1
 jsr @add
 lda LRVT+LT_CARET_ROW
 sta se_v_caret_row
 lda LRVT+LT_CARET_COL
 sta se_v_caret_col
 lda #1
 sta se_v_seen
 ldx #2
@gc:
 lda LRVT+LT_GC_VALID,x
 sta se_gc_valid,x
 dex
 bpl @gc
 ldx #3
@revision:
 lda se_r_revision,x
 sta se_l_revision,x
 dex
 bpl @revision
 ldx #2
@caret:
 lda se_hot_caret,x
 sta se_l_caret,x
 dex
 bpl @caret
 clc
 rts
@rows:
 lda #<se_v_rows
 sta text_ptr
 lda #>se_v_rows
 sta text_ptr+1
 txa
 clc
 adc text_ptr
 sta text_ptr
 bcc @add
 inc text_ptr+1
@add:
 ldy #0
 clc
 lda (text_ptr),y
 adc LRVT+2
 sta (text_ptr),y
 iny
 lda LRVT+2
 bmi :+
 lda #0
 beq :++
:
 lda #$FF
:
 adc (text_ptr),y
 sta (text_ptr),y
 iny
 lda LRVT+2
 bmi :+
 lda #0
 beq :++
:
 lda #$FF
:
 adc (text_ptr),y
 sta (text_ptr),y
 rts

; Pure owner4 source gather. R25 has already authenticated the LRV header,
; selected record, plan slice and row DMA before this code reads any byte.
lrv_build_packet:
 COPY24 LRVT+LT_START,LRVT+LT_SOURCE
 lda se_l_mode
 beq @wrapped
 ADD24 LRVT+LT_SOURCE,se_l_pan,LRVT+LT_SOURCE
 jmp @source_ready
@wrapped:
 clc
 lda LRVT+LT_CLIP
 adc LRVT+LT_REL
 sta NEXT
 lda LRVT+LT_CLIP+1
 adc #0
 sta NEXT+1
@offset_check:
 lda NEXT
 ora NEXT+1
 beq @source_ready
 clc
 lda LRVT+LT_SOURCE
 adc LRVT+LT_WIDTH
 sta LRVT+LT_SOURCE
 bcc :+
 inc LRVT+LT_SOURCE+1
 bne :+
 inc LRVT+LT_SOURCE+2
:
 lda NEXT
 bne :+
 dec NEXT+1
:
 dec NEXT
 jmp @offset_check
@source_ready:
 COPY24 LRVT+LT_SOURCE,se_v_pos
 lda #0
 sta COL
@cell:
 ldx COL
 lda #32
 sta P,x
 lda #0
 sta LRVT+LT_CELL_VALID
 ; Only offsets below the authenticated 16-bit content length read source.
 sec
 lda se_v_pos
 sbc LRVT+LT_START
 sta NEXT
 lda se_v_pos+1
 sbc LRVT+LT_START+1
 sta NEXT+1
 lda se_v_pos+2
 sbc LRVT+LT_START+2
 bne @flags
 lda NEXT+1
 cmp LRVT+LT_LENGTH+1
 bcc @read
 bne @flags
 lda NEXT
 cmp LRVT+LT_LENGTH
 bcc @read
 beq @end_cell
 jmp @advance
@read:
 lda #1
 sta LRVT+LT_CELL_VALID
 jsr se_view_peek
 jcs @bad
 ldx COL
 sta P,x
 jmp @flags
@end_cell:
 lda #2
 sta LRVT+LT_CELL_VALID
@flags:
 ldx COL
 lda LRVT+LT_RECORD_FLAGS
 and #LRRF_REVERSE
 beq :+
 lda #1
:
 sta P+160,x
 lda LRVT+LT_CELL_VALID
 cmp #1
 bne @caret
 CMP24 se_v_pos,se_sel_start
 bcc @caret
 CMP24 se_v_pos,se_sel_end
 bcs @caret
 lda P+160,x
 ora #2
 sta P+160,x
@caret:
 ; The end position is a real caret cell (including the exact-width EOF
 ; terminal row), but no later padding cell may alias another logical line.
 lda LRVT+LT_CELL_VALID
 beq @advance
 CMP24 se_v_pos,se_hot_caret
 bne @advance
 lda LRVT+LT_ROW
 sta LRVT+LT_CARET_ROW
 lda COL
 sta LRVT+LT_CARET_COL
 lda P+160,x
 ora #4
 sta P+160,x
@advance:
 inc se_v_pos
 bne :+
 inc se_v_pos+1
 bne :+
 inc se_v_pos+2
:
 inc COL
 lda COL
 cmp LRVT+LT_WIDTH
 jcc @cell
 lda #0
 clc
 rts
@bad:
 lda #LRV_ERROR
 sec
 rts

; The native leaf evicts R25 from the R slot.  Commit the already-built
; packet here so a successful row does not reload R25 merely to prepare one
; DMA and calculate one CRC.  Frame18 authenticated the retained NC handle
; and saved its header before any leaf ran.
lrv_commit_row:
 lda se_mode
 beq @done
 lda #<P
 sta se_reu_c64
 lda #>P
 sta se_reu_c64+1
 lda #240
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 sta se_reu_offset
 sta se_reu_offset+1
 ldx LRVT+LT_ROW
 beq @request
@offset:
 clc
 lda se_reu_offset
 adc #240
 sta se_reu_offset
 bcc :+
 inc se_reu_offset+1
: dex
 bne @offset
@request:
 lda se_gc_handle
 sta se_reu_logical
 lda #0
 jsr se_reu_copy
 jcs @commit_bad
 jsr se_crc_init
 ldy #0
@crc:
 lda P,y
 jsr se_crc_byte
 iny
 cpy #240
 bcc @crc
 lda LRVT+LT_ROW
 asl
 tax
 lda se_crc_value
 sta LRV_OLD_NC+N_ROWCRC,x
 lda se_crc_value+1
 sta LRV_OLD_NC+N_ROWCRC+1,x
@done:
 inc LRVT+LT_REL
 clc
 rts
@commit_bad:
 lda #LRV_ERROR
 sec
 rts

; The selected visible slice must fit its logical line.  Multiplying
; (CLIP_ROW + PLAN_ROWS - 1) by width proves the final row's first source
; byte is at or before LENGTH.  This also admits exactly one terminal row at
; empty or exact-width EOF and works unchanged for nowrap's one visible row.
lrv_span_check:
 clc
 lda LRVT+LT_CLIP
 adc LRVT+LT_ROWS
 sta NEXT
 lda LRVT+LT_CLIP+1
 adc #0
 sta NEXT+1
 bcs @bad
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
 lda #LRV_ERROR
 sec
 rts
@ok:
 clc
 rts

lrv_native_row:
 ldx #18
@descriptor:
 lda nr_defaults,x
 sta NC_NR,x
 dex
 bpl @descriptor
 lda LRVT+LT_WIDTH
 sta NC_NR
 sta NC_NR+2
 lda LRVT+LT_ROW
 clc
 adc #2
 sta NC_NR+1
 lda #<NC_NR
 sta se_overlay_frame+1
 lda #>NC_NR
 sta se_overlay_frame+2
 lda #0
 jmp leaf

; The 40-column mode shares the same packet authority.  Roles become the
; ReadyOS palette color and live selector flags become PETSCII reverse video.
.import se_petscii_screen
lrv_text_row:
 lda #0
 sta screen_ptr
 lda #$40                  ;VIC screen base $4000
 sta screen_ptr+1
 ldx LRVT+LT_ROW
 inx
 inx
@screen_row:
 clc
 lda screen_ptr
 adc #40
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
:
 dex
 bne @screen_row
 lda screen_ptr
 sta text_ptr
 lda screen_ptr+1
 clc
 adc #$98                  ;matching color RAM base $D800
 sta text_ptr+1
 lda #0
 sta COL
@cell:
 ldx COL
 lda P,x
 jsr se_petscii_screen
 ldx COL
 ldy P+160,x
 beq :+
 eor #$80
:
 ldy COL
 sta (screen_ptr),y
 lda P+160,x
 and #6
 beq @role_color
 lda #3                    ;live selection/caret accent
 bne @color
@role_color:
 lda P+80,x
 cmp #14
 jcs @bad
 tax
 lda palette,x
@color:
 sta (text_ptr),y
 inc COL
 lda COL
 cmp #40
 bcc @cell
 lda #0
 clc
 rts
@bad:
 lda #LRV_ERROR
 sec
 rts
