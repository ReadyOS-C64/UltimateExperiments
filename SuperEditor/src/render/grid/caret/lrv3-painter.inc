; C33 frame1/4: consume the prepared Plain direct-row transaction. There are
; no calls to the cold parser/layout producer on this path.
.include "render/grid/paragraph/lrv3.inc"
.include "render/geos/edit-certificate.inc"
LRVT=$8D00
LT_WIDTH=1
LT_FIRST=3
LT_ROWS=4
LT_REL=8
LT_START=9
LT_LENGTH=12
LT_ROW=14
LT_CARET_ROW=15
LT_CARET_COL=16
LT_FLAGS=7
LT_CLIP=18
LT_SOURCE=20
LT_REMAIN=23              ;2, live content bytes at/after this row source
LT_GC_VALID=25
LT_END_PENDING=28         ;the one real CR/EOF caret cell has not been emitted
LT_ROW_CARET=29           ;row-relative caret column, or $FF
LT_LIVE=30                ;contiguous content/end cells emitted in this packet
LT_COVER=34
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
 lda se_st_tx+ST_TX_PHASE
 cmp #ST_TX_READY
 bne @plain
 jmp @claimed
@plain:
 lda LRVT+35                ;LT_PREPARED
 cmp #LRV_PUBLISHED
 jne miss
 lda #0
 sta LRVT+35                ;retire before any queued-state refusal
@claimed:
 lda #1
 sta OP
 sta C+63
 jsr authenticate_helper
 jcs miss
 lda se_st_tx+ST_TX_PHASE
 cmp #ST_TX_READY
 beq @queued_state
 ; The prepared transaction is consumable only while its exact R25 image and
 ; editor state remain current.  A queued command forces the ordinary redraw.
 inx
 cpx se_overlay_active
 jne miss
@queued_state:
 lda se_e_ui
 ora se_e_job
 ora se_e_draw_busy
 ora se_r_presentation
 ora se_sel_mark
 jne miss
 lda se_st_tx+ST_TX_PHASE
 cmp #ST_TX_READY
 beq @admit
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
@admit:
 lda #14
 jsr helper
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
 lda LRVT+LT_REL
 cmp LRVT+LT_ROWS
 bcs @finish
 clc
 adc LRVT+LT_FIRST
 sta LRVT+LT_ROW
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
 lda se_mode
 beq @header_done
 clc
 lda LRVT+LT_FIRST
 adc LRVT+LT_ROWS
 sta COL
 asl
 adc COL
 tax
@header_rows:
 lda se_v_rows,x
 sta H+N_ROWS,x
 inx
 cpx #66
 bcc @header_rows
 ldx #2
@header_bottom:
 lda se_v_bottom,x
 sta H+N_BOTTOM,x
 sta H+N_ROWS+66,x
 dex
 bpl @header_bottom
@header_done:
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
 ; Patch one private absolute,Y load before source callbacks borrow ZP. Padding
 ; never consults the plan, so stale cells beyond a shorter line stay plain.
 lda LRVT+LT_FLAGS
 bpl @plan_ready
 lda #0
 sta text_ptr
 lda se_mode
 beq :+
 lda #$48
 bne @plan_page
: lda #>STYLE_PLAN
@plan_page:
 sta text_ptr+1
 ldx LRVT+LT_ROW
 beq @plan_patch
@plan_seek:
 clc
 lda text_ptr
 adc LRVT+LT_WIDTH
 sta text_ptr
 bcc :+
 inc text_ptr+1
: dex
 bne @plan_seek
@plan_patch:
 lda text_ptr
 sta @style_cell+1
 lda text_ptr+1
 sta @style_cell+2
@plan_ready:
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
 ; Convert the authenticated 24-bit row source to one bounded 16-bit content
 ; countdown. LT_LENGTH is the content extent excluding CR; END_PENDING names
 ; its one real CR/EOF caret cell. A source beyond the extent is padding only.
 lda #0
 sta LRVT+LT_END_PENDING
 sec
 lda LRVT+LT_SOURCE
 sbc LRVT+LT_START
 sta NEXT
 lda LRVT+LT_SOURCE+1
 sbc LRVT+LT_START+1
 sta NEXT+1
 lda LRVT+LT_SOURCE+2
 sbc LRVT+LT_START+2
 sta NEXT+2
 sec
 lda LRVT+LT_LENGTH
 sbc NEXT
 sta LRVT+LT_REMAIN
 lda LRVT+LT_LENGTH+1
 sbc NEXT+1
 sta LRVT+LT_REMAIN+1
 lda #0
 sbc NEXT+2
 bcc @range_after
 inc LRVT+LT_END_PENDING
 bcs @range_ready
@range_after:
 lda #0
 sta LRVT+LT_REMAIN
 sta LRVT+LT_REMAIN+1
@range_ready:
 ; Resolve the only possible caret once for this row. The live-cell count below
 ; rejects a candidate in padding while retaining the exact end position.
 lda #$FF
 sta LRVT+LT_ROW_CARET
 sec
 lda se_hot_caret
 sbc LRVT+LT_SOURCE
 sta NEXT
 lda se_hot_caret+1
 sbc LRVT+LT_SOURCE+1
 sta NEXT+1
 lda se_hot_caret+2
 sbc LRVT+LT_SOURCE+2
 bcc @caret_ready
 bne @caret_ready
 lda NEXT+1
 bne @caret_ready
 lda NEXT
 cmp LRVT+LT_WIDTH
 bcs @caret_ready
 sta LRVT+LT_ROW_CARET
@caret_ready:
 lda #0
 sta COL
 sta LRVT+LT_LIVE
@cell:
 ldx COL
 lda #32
 sta P,x
 lda #0
 sta P+80,x
 sta P+160,x
 lda LRVT+LT_REMAIN
 ora LRVT+LT_REMAIN+1
 bne @read
 lsr LRVT+LT_END_PENDING
 bcc @next_cell
 inc LRVT+LT_LIVE
 bne @next_cell
@read:
 jsr se_view_peek
 jcs @bad
 ldx COL
 sta P,x
 lda LRVT+LT_FLAGS
 bpl @valid
 ldy COL
@style_cell:
 lda $FFFF,y
 pha
 and #15
 cmp #14
 jcs @style_bad
 ldx COL
 sta P+80,x
 pla
 bpl @valid
 lda P+160,x
 ora #1
 sta P+160,x
@valid:
 inc LRVT+LT_LIVE
 lda LRVT+LT_REMAIN
 bne :+
 dec LRVT+LT_REMAIN+1
: dec LRVT+LT_REMAIN
 inc se_v_pos
 bne :+
 inc se_v_pos+1
 bne :+
 inc se_v_pos+2
:
@next_cell:
 inc COL
 lda COL
 cmp LRVT+LT_WIDTH
 jcc @cell
 lda LRVT+LT_ROW_CARET
 cmp LRVT+LT_LIVE
 bcs @packet_ready
 tax
 lda LRVT+LT_ROW
 sta LRVT+LT_CARET_ROW
 lda LRVT+LT_ROW_CARET
 sta LRVT+LT_CARET_COL
 lda P+160,x
 ora #4
 sta P+160,x
@packet_ready:
 lda #0
 clc
 rts
@bad:
 lda #LRV_ERROR
 sec
 rts
@style_bad:
 pla
 jmp @bad

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
 sta H+N_ROWCRC,x
 lda se_crc_value+1
 sta H+N_ROWCRC+1,x
@done:
 inc LRVT+LT_REL
 clc
 rts
@commit_bad:
 lda #LRV_ERROR
 sec
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
 lda LRVT+LT_LIVE
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
