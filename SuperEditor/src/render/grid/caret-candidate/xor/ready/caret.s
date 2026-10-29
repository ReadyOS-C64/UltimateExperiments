; Private C33 retained-input narrow caret transaction. No resident/ZP state.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "api.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_v_columns,se_e_ui,se_e_menu,se_e_job,se_e_redraw,se_e_draw_busy,se_e_error
.import se_hot_ready,se_hot_pending,se_hot_phase,se_hot_base,se_hot_length,se_hot_old_length,se_hot_caret
.import se_h_fault,se_h_trimmed,se_r_presentation,se_r_revision,se_e_draw_sequence
.import se_doc_meta,se_doc_original,se_doc_append,se_doc_generation,se_doc_epoch,se_doc_busy,se_doc_read_locks
.import se_object_id,se_object_validate,se_view_init,se_view_peek,se_v_pos,se_v_length
.import se_v_top,se_v_bottom,se_v_rows,se_v_seen,se_v_caret_row,se_v_caret_col,se_v_nav_busy
.import se_l_valid,se_l_need_wrap,se_l_original,se_l_generation,se_l_revision,se_l_top,se_l_mode,se_l_manual,se_l_pan,se_n_view_columns
.import se_st_descriptor,se_st_request,se_st_valid
.import se_gc_handle,se_gc_width,se_gc_epoch,se_gc_valid,se_gc_previous_ui,se_gc_current_ui
.import se_ef_valid,se_ef_generation,se_ef_token,se_ef_count,se_ef_fold_rows,se_ef_projection_generation,se_ef_paint_ends,se_ef_summary,se_ef_key_match
.import se_sel_mark,se_sel_anchor,se_sel_start,se_sel_end,se_selection_range
.import se_overlay_ids,image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi,se_overlay_asset,asset_epoch
.import se_reu_retired,se_reu_epoch,se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_crc_init,se_crc_byte,se_crc_value,tui_editor_status40,se_doc_invalidate
.importzp text_ptr,screen_ptr
.export entry
H=NC_HEADER
P=NC_PACKET
B=NC_SECOND
C=NC_C
OP=C
W=C+1
BACKEND=C+2
ROW=C+3
COL=C+4
INDEX=C+5
PTR=C+6 ;2
POS=C+8 ;3
END=C+11 ;3
NEXT=C+14 ;3
DELTA=C+17 ;3
NEWROW=C+20
NEWCOL=C+21
NEWSEEN=C+22
OLDROW=C+23
OLDCOL=C+24
OLDSEEN=C+25
SUMSEL=C+26
ROWID=C+27
FCAP=C+28 ;8
FECAP=C+36 ;4
FCRC=C+40 ;2
BCOL=C+42
BITMASK=C+43
.segment "CODE"
 OVL_BINDING
entry:
 lda se_overlay_frame
 cmp #2
 bne :+
 jmp se_grid_plan
:
 cmp #2
 jcs argument
 ldx se_f_owner
 jne opaque
 sta OP
 lda #4
 sta se_f_owner
 jsr admit
 jcs miss
 lda OP
 jeq capture
 jsr fetch_header
 jcs miss
 jsr header_crc
 ldx #1
@checksum:
 lda se_crc_value,x
 cmp H+N_CRC,x
 jne miss
 dex
 bpl @checksum
 lda H
 cmp #'N'
 jne miss
 lda H+1
 cmp #'C'
 jne miss
 lda H+2
 cmp #1
 jne miss
 lda H+3
 cmp #$A5
 jne miss
 jsr fields
 jcs miss
 ldx #1
@sequence:
 lda H+N_SEQUENCE,x
 cmp se_e_draw_sequence,x
 jne miss
 dex
 bpl @sequence
 lda H+N_SEEN
 cmp #2
 jcs miss
 sta OLDSEEN
 tax
 beq @old_hidden
 lda H+N_ROW
 cmp #22
 jcs miss
 lda H+N_COL
 cmp W
 jcs miss
@old_hidden:
 lda H+N_ROW
 sta OLDROW
 lda H+N_COL
 sta OLDCOL
 jsr locate
 jcs miss
 lda se_sel_mark
 beq @unmarked
 lda OLDSEEN
 and NEWSEEN
 jeq miss
 lda NEWROW
 sec
 sbc OLDROW
 cmp #2
 bcc @unmarked
 cmp #$FF
 jne miss ;marked movement touches at most two adjacent rows
@unmarked:
 ; Admit the exact font leaf before any pixel/cache publication.
 lda #2
 jsr leaf
 jcs miss
 ; Fetch/check both packets before modifying any owned output.
 lda OLDSEEN
 beq @new_only
 lda OLDROW
 sta ROW
 lda #<P
 ldx #>P
 jsr fetch_row
 jcs miss
 jsr verify_row
 jcs miss
@new_only:
 lda NEWSEEN
 beq @prepared
 lda OLDSEEN
 beq @second
 lda NEWROW
 cmp OLDROW
 beq @prepared
@second:
 lda NEWROW
 sta ROW
 lda #<B
 ldx #>B
 jsr fetch_row
 jcs miss
 jsr verify_row
 jcs miss
@prepared:
 lda #0
 sta CHANGE
 sta CHANGE+1
 jsr se_selection_range
 lda OLDSEEN
 beq @new_paint
 lda OLDROW
 sta ROW
 lda #<P
 ldx #>P
 jsr prepare_row
 jcs miss
@new_paint:
 lda NEWSEEN
 beq @publish
 lda OLDSEEN
 beq @prepare_second
 lda NEWROW
 cmp OLDROW
 beq @publish
@prepare_second:
 lda NEWROW
 sta ROW
 lda #<B
 ldx #>B
 jsr prepare_row
 jcs miss
@publish:
 ; From here every input/frame/range/capability is already checked; no yield.
 lda OLDSEEN
 beq @paint_new
 lda OLDROW
 sta ROW
 lda #<P
 ldx #>P
 jsr paint_row
 jcs miss
@paint_new:
 lda NEWSEEN
 beq @status
 lda OLDSEEN
 beq @paint_second
 lda NEWROW
 cmp OLDROW
 beq @status
@paint_second:
 lda NEWROW
 sta ROW
 lda #<B
 ldx #>B
 jsr paint_row
 jcs miss
@status:
 jsr status
 jcs miss
 lda NEWSEEN
 sta se_v_seen
 sta H+N_SEEN
 lda NEWROW
 sta H+N_ROW
 lda NEWCOL
 sta H+N_COL
 lda NEWSEEN
 beq :+
 lda NEWROW
 sta se_v_caret_row
 lda NEWCOL
 sta se_v_caret_col
: ldx #2
@caret:
 lda se_hot_caret,x
 sta H+N_CARET,x
 dex
 bpl @caret
 clc
 lda se_e_draw_sequence
 adc #1
 sta H+N_SEQUENCE
 lda se_e_draw_sequence+1
 adc #0
 sta H+N_SEQUENCE+1
 jsr store_header
 jcs miss
 jmp success
capture:
 ; Trusted post-full-publication seam; never manufacture a revision witness
 ; from validbits alone before a successful root frame.
 lda se_e_redraw
 ora se_e_draw_busy
 jne miss
 lda #0
 tax
@clear:
 sta H,x
 inx
 bne @clear
 jsr fields
 jcs miss
 lda #'N'
 sta H
 lda #'C'
 sta H+1
 lda #1
 sta H+2
 lda #$A5
 sta H+3
 ldx #2
@caret:
 lda se_hot_caret,x
 sta H+N_CARET,x
 dex
 bpl @caret
 ldx #1
@seq:
 lda se_e_draw_sequence,x
 sta H+N_SEQUENCE,x
 dex
 bpl @seq
 lda #0
 sta ROW
@row:
 jsr bounds
 jcs miss
 CMP24 NEXT,POS
 beq @packet
 COPY24 NEXT,se_v_pos
 jsr retreat
 jsr se_view_peek
 jcs miss
 cmp #13
 bne @packet
 jsr row_bit
 lda H+N_CR,x
 ora BITMASK
 sta H+N_CR,x
@packet:
 lda #<P
 ldx #>P
 jsr fetch_row
 jcs miss
 jsr packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 sta H+N_ROWCRC,x
 lda se_crc_value+1
 sta H+N_ROWCRC+1,x
 inc ROW
 lda ROW
 cmp #22
 jcc @row
 jsr locate
 jcs miss
 lda NEWSEEN
 cmp se_v_seen
 jne miss
 sta H+N_SEEN
 lda NEWROW
 sta H+N_ROW
 lda NEWCOL
 sta H+N_COL
 lda NEWSEEN
 beq @save
 lda NEWROW
 cmp se_v_caret_row
 jne miss
 lda NEWCOL
 cmp se_v_caret_col
 jne miss
@save:
 jsr store_header
 jcs miss
success:
 lda #0
 sta se_f_owner
 clc
 rts
miss:
 lda #0
 sta se_f_owner
opaque:
 lda #2
 clc
 rts
argument:
 lda #$90
 sec
 rts
.import se_overlay_capacity,se_ef_key,object_owner
admit:
 lda se_mode
 cmp #1
 beq @sixty
 cmp #2
 jne invalid
 lda #80
 ldx #16
 bne @width
@sixty:
 lda #60
 ldx #17
@width:
 sta W
 stx BACKEND
 cmp se_v_columns
 jne invalid
 cmp se_n_view_columns
 jne invalid
 cmp se_gc_width
 jne invalid
 lda se_e_ui
 ora se_e_job
 ora se_e_draw_busy
 ora se_e_error
 ora se_r_presentation
 ora se_hot_phase
 ora se_v_nav_busy
 ora se_doc_busy
 ora se_doc_read_locks
 ora se_gc_previous_ui
 ora se_gc_current_ui
 ora se_l_need_wrap
 ora se_h_fault
 ora se_h_trimmed
 ora se_h_trimmed+1
 jne invalid
 lda se_st_request
 cmp #1
 jeq invalid
 lda se_hot_ready
 and se_l_valid
 cmp #1
 jne invalid
 lda se_gc_valid
 and se_gc_valid+1
 cmp #$FF
 jne invalid
 lda se_gc_valid+2
 cmp #$3F
 jne invalid
 jsr owned
 jcs invalid
 jsr se_view_init
 jcs invalid
 ldx #9
@layout_source:
 lda se_doc_original,x
 cmp se_l_original,x
 jne invalid
 dex
 bpl @layout_source
 ldx #3
@revision:
 lda se_r_revision,x
 cmp se_l_revision,x
 jne invalid
 dex
 bpl @revision
 ldx #1
@generation:
 lda se_doc_generation,x
 cmp se_l_generation,x
 jne invalid
 dex
 bpl @generation
 CMP24 se_v_top,se_l_top
 jne invalid
 CMP24 se_v_top,se_v_rows
 jne invalid
 .repeat 3,I
 ldx #4
: lda se_doc_meta+I*5,x
 sta se_object_id,x
 dex
 bpl :-
 jsr se_object_validate
 jcs invalid
 .endrepeat
 lda se_ef_valid
 beq @font
 ldx #4
@fold_token:
 lda se_ef_token,x
 sta se_object_id,x
 dex
 bpl @fold_token
 jsr se_object_validate
 jcs invalid
 ldx se_ef_token
 lda object_owner,x
 cmp #$46
 jne invalid
@font:
 jsr font_cap
 rts
invalid:
 sec
 rts
owned:
 lda se_reu_retired
 jne invalid
 lda se_reu_epoch
 ora se_reu_epoch+1
 jeq invalid
 ldx #1
@epoch:
 lda se_gc_epoch,x
 cmp se_reu_epoch,x
 jne invalid
 lda asset_epoch,x
 cmp se_reu_epoch,x
 jne invalid
 sta FECAP+2,x
 dex
 bpl @epoch
 ldx se_gc_handle
 jeq invalid
 stx FECAP
 lda se_reu_logical_owner,x
 cmp #$FE
 jne invalid
 ldy se_reu_map,x
 jeq invalid
 sty FECAP+1
 lda se_reu_physical_owner,y
 cmp #$FE
 jne invalid
 clc
 rts
font_cap:
 lda BACKEND
 sta FCAP
 ldx #0
@find:
 lda se_overlay_ids,x
 cmp BACKEND
 jne @next
 lda image_slot,x
 and #$7F
 beq @found
@next:
 inx
 cpx #<se_overlay_capacity
 bcc @find
 sec
 rts
@found:
 stx FCAP+1
 lda image_size_lo,x
 jne invalid
 sta FCAP+4
 lda image_size_hi,x
 cmp #16
 jne invalid
 sta FCAP+5
 lda image_crc_lo,x
 sta FCAP+6
 lda image_crc_hi,x
 sta FCAP+7
 txa
 lsr
 lsr
 lsr
 lsr
 tax
 ldy se_overlay_asset,x
 jeq invalid
 sty FCAP+2
 lda se_reu_logical_owner,y
 cmp #2
 jne invalid
 ldx se_reu_map,y
 jeq invalid
 stx FCAP+3
 lda se_reu_physical_owner,x
 cmp #2
 jne invalid
 clc
 rts

.macro FIELD source,offset,size
 lda #<(source-(offset))
 sta text_ptr
 lda #>(source-(offset))
 sta text_ptr+1
 ldy #offset
 ldx #size
 jsr field
 jcs invalid
.endmacro
fields:
 FIELD se_doc_meta,N_KEY,15
 FIELD se_doc_generation,N_KEY+15,2
 FIELD se_r_revision,N_KEY+17,4
 FIELD se_v_length,N_KEY+21,3
 FIELD se_reu_epoch,N_KEY+24,2
 FIELD se_doc_epoch,N_KEY+26,2
 FIELD W,N_WIDTH,1
 FIELD se_mode,N_MODE,1
 FIELD se_l_mode,N_LAYOUT,1
 FIELD se_l_manual,N_MANUAL,1
 FIELD se_l_pan,N_PAN,3
 FIELD se_v_top,N_TOP,3
 FIELD se_v_bottom,N_BOTTOM,3
 FIELD se_st_descriptor,N_STYLE,37
 FIELD se_sel_mark,N_MARK,1
 FIELD se_sel_anchor,N_ANCHOR,3
 FIELD se_hot_ready,N_READY,1
 FIELD se_hot_pending,N_PENDING,1
 FIELD se_hot_base,N_HOTBASE,3
 FIELD se_hot_length,N_HOTLEN,2
 FIELD se_hot_old_length,N_OLDLEN,2
 FIELD se_ef_valid,N_FOLD,1
 FIELD se_ef_generation,N_FOLDGEN,2
 FIELD se_ef_token,N_TOKEN,5
 FIELD se_ef_count,N_COUNT,2
 FIELD se_ef_fold_rows,N_BITS,3
 FIELD se_ef_projection_generation,N_PROJECTION,2
 jsr fold_crc
 FIELD FCRC,N_FOLDCRC,2
 FIELD FECAP,N_FE,4
 FIELD FCAP,N_FONT,8
 FIELD se_v_rows,N_ROWS,66
 FIELD se_v_bottom,N_ROWS+66,3
 FIELD se_gc_valid,N_VALID,3
 FIELD se_gc_previous_ui,N_PREVUI,1
 FIELD se_gc_current_ui,N_CURUI,1
 lda se_ef_valid
 beq @done
 ldx #27
@fold_source:
 lda se_ef_key,x
 cmp H+N_KEY,x
 jne invalid
 dex
 bpl @fold_source
@done:
 clc
 rts
field:
 lda OP
 bne @compare
@copy:
 lda (text_ptr),y
 sta H,y
 iny
 dex
 bne @copy
 clc
 rts
@compare:
 lda (text_ptr),y
 cmp H,y
 jne invalid
 iny
 dex
 bne @compare
 clc
 rts
fold_crc:
 jsr se_crc_init
 ldy #0
@byte:
 lda se_ef_paint_ends,y
 jsr se_crc_byte
 iny
 cpy #66
 bcc @byte
 lda se_crc_value
 sta FCRC
 lda se_crc_value+1
 sta FCRC+1
 rts
header_crc:
 jsr se_crc_init
 ldy #0
@byte:
 lda H,y
 jsr se_crc_byte
 iny
 cpy #N_CRC
 bcc @byte
 rts
store_header:
 jsr header_crc
 lda se_crc_value
 sta H+N_CRC
 lda se_crc_value+1
 sta H+N_CRC+1
 jsr header_request
 lda #0
 jmp se_reu_copy
fetch_header:
 jsr header_request
 lda #1
 jmp se_reu_copy
header_request:
 lda #<NC_REU
 sta se_reu_offset
 lda #>NC_REU
 sta se_reu_offset+1
 lda #0
 sta se_reu_length
 lda #1
 sta se_reu_length+1
 lda #<H
 sta se_reu_c64
 lda #>H
 sta se_reu_c64+1
 lda se_gc_handle
 sta se_reu_logical
 rts
; A/X packetpointer; ROW must0..21. No allocation or hardcodedphysical bank.
fetch_row:
 sta PTR
 stx PTR+1
 jsr row_request
 lda #1
 jmp se_reu_copy
row_request:
 lda PTR
 sta se_reu_c64
 lda PTR+1
 sta se_reu_c64+1
 lda #240
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 sta se_reu_offset
 sta se_reu_offset+1
 ldx ROW
 beq @done
@add:
 clc
 lda se_reu_offset
 adc #240
 sta se_reu_offset
 bcc :+
 inc se_reu_offset+1
: dex
 bne @add
@done:
 lda se_gc_handle
 sta se_reu_logical
 rts
packet_crc:
 lda PTR
 sta text_ptr
 lda PTR+1
 sta text_ptr+1
 jsr se_crc_init
 ldy #0
@byte:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 cpy #240
 bcc @byte
 rts
verify_row:
 jsr packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 cmp H+N_ROWCRC,x
 jne invalid
 lda se_crc_value+1
 cmp H+N_ROWCRC+1,x
 jne invalid
 ; Roles/flags are actual producer inputs; reject malformed cached packets.
 lda PTR
 clc
 adc #80
 sta text_ptr
 lda PTR+1
 adc #0
 sta text_ptr+1
 ldy #0
@roles:
 lda (text_ptr),y
 cmp #14
 jcs invalid
 iny
 cpy W
 bcc @roles
 clc
 lda text_ptr
 adc #80
 sta text_ptr
 bcc :+
 inc text_ptr+1
: ldy #0
@flags:
 lda (text_ptr),y
 cmp #8
 jcs invalid
 and #4
 beq @no_caret
 lda OLDSEEN
 jeq invalid
 lda ROW
 cmp OLDROW
 jne invalid
 cpy OLDCOL
 jne invalid
 bcs @next
@no_caret:
 lda OLDSEEN
 beq @next
 lda ROW
 cmp OLDROW
 jne @next
 cpy OLDCOL
 jeq invalid
@next:
 iny
 cpy W
 bcc @flags
 clc
 rts
; Canonical row ownership from the certified map and CAPTURE's true-CR bits.
bounds:
 lda ROW
 asl
 clc
 adc ROW
 sta INDEX
 tax
 ldy #0
@copy:
 lda H+N_ROWS,x
 sta POS,y
 lda se_ef_valid
 beq @plain
 lda se_ef_paint_ends,x
 jmp @next
@plain:
 lda H+N_ROWS+3,x
@next:
 sta NEXT,y
 sta END,y
 inx
 iny
 cpy #3
 bcc @copy
 CMP24 NEXT,POS
 jcc invalid
 jsr row_bit
 lda H+N_CR,x
 and BITMASK
 beq @ready
 lda END
 bne :+
 lda END+1
 bne @mid
 dec END+2
@mid:
 dec END+1
: dec END
@ready:
 clc
 rts
retreat:
 lda se_v_pos
 bne :+
 lda se_v_pos+1
 bne @mid
 dec se_v_pos+2
@mid:
 dec se_v_pos+1
: dec se_v_pos
 rts
row_bit:
 lda ROW
 and #7
 tax
 lda bits,x
 sta BITMASK
 lda ROW
 lsr
 lsr
 lsr
 tax
 rts
locate:
 lda #0
 sta NEWSEEN
 sta ROW
 lda #$FF
 sta NEWROW
 sta NEWCOL
@row:
 jsr bounds
 jcs invalid
 CMP24 se_hot_caret,POS
 jcc @next
 CMP24 se_hot_caret,END
 bcc @found
 jne @next
 lda se_l_mode
 bne @found
 SUB24 END,POS,DELTA
 lda DELTA+1
 ora DELTA+2
 jne @next
 lda DELTA
 cmp W
 bcs @next
@found:
 lda ROW
 sta NEWROW
 SUB24 se_hot_caret,POS,DELTA
 CMP24 DELTA,se_l_pan
 bcc @hidden
 SUB24 DELTA,se_l_pan,DELTA
 lda DELTA+1
 ora DELTA+2
 bne @hidden
 lda DELTA
 cmp W
 bcs @hidden
 sta NEWCOL
 lda #1
 sta NEWSEEN
 clc
 rts
@hidden:
 lda se_l_manual
 jeq invalid
 clc
 rts
@next:
 inc ROW
 lda ROW
 cmp #22
 jcc @row
 sec
 rts
prepare_row:
 sta PTR
 stx PTR+1
 jsr bounds
 jcs invalid
 SUB24 END,POS,DELTA
 CMP24 se_l_pan,DELTA
 bcc @pan
 beq @pan
 COPY24 END,POS
 inc POS
 bne @pointer
 inc POS+1
 bne @pointer
 inc POS+2
 jmp @pointer
@pan:
 ADD24 POS,se_l_pan,POS
@pointer:
 clc
 lda PTR
 adc #160
 sta text_ptr
 lda PTR+1
 adc #0
 sta text_ptr+1
 ; Summary query clobbers only X/Y/se_r_color, never text_ptr.
 lda ROW
 jsr se_ef_summary
 lda #0
 bcc :+
 lda #2
: sta SUMSEL
 lda #0
 sta COL
@cell:
 ldy COL
 lda (text_ptr),y
 pha
 and #6
 beq :+
 lda #1
: sta WAS
 pla
 and #1
 sta BCOL ;current flag scratch, not statuscolumn yet
 CMP24 POS,END
 bcc @selection
 bne @caret
 lda BCOL
 ora SUMSEL
 sta BCOL
@selection:
 lda se_sel_mark
 beq @caret
 CMP24 POS,se_sel_start
 bcc @caret
 CMP24 POS,se_sel_end
 bcs @caret
 lda BCOL
 ora #2
 sta BCOL
@caret:
 lda NEWSEEN
 beq @store
 lda ROW
 cmp NEWROW
 bne @store
 lda COL
 cmp NEWCOL
 bne @store
 lda BCOL
 ora #4
 sta BCOL
@store:
 lda BCOL
 and #6
 beq :+
 lda #1
: cmp WAS
 beq @unchanged
 ldx #0
 lda PTR
 cmp #<P
 beq :+
 inx
: ldy CHANGE,x
 cpy #2
 jcs invalid ;optional fast path, never paint a wider marked delta
 lda COL
 cpx #0
 bne @second
 sta CELLA,y
 jmp @changed
@second:
 sta CELLB,y
@changed:
 inc CHANGE,x
@unchanged:
 ldy COL
 lda BCOL
 sta (text_ptr),y
 inc POS
 bne :+
 inc POS+1
 bne :+
 inc POS+2
: inc COL
 lda COL
 cmp W
 jcc @cell
 clc
 rts
paint_row:
 sta PTR
 stx PTR+1
 jsr xor_changes
 bcs @return
 jsr row_request
 lda #0
 jsr se_reu_copy
 bcs @return
 jsr packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 sta H+N_ROWCRC,x
 lda se_crc_value+1
 sta H+N_ROWCRC+1,x
 clc
@return:
 rts
leaf:
 sta se_overlay_frame
 lda BACKEND
 ldx #0
 jmp se_overlay_call
status:
 jsr tui_editor_status40
 lda #6
 sta BCOL
@cell:
 ldx BCOL
 stx NC_BC+1
 lda #24
 sta NC_BC
 lda $43C0,x
 sta NC_BC+2
 lda $DBC0,x
 and #15
 sta NC_BC+3
 lda #6
 sta NC_BC+4
 lda #0
 sta NC_BC+5
 sta NC_BC+7
 sta NC_BC+9
 lda #$AC
 sta NC_BC+6
 lda #$60
 sta NC_BC+8
 lda #$40
 sta NC_BC+10
 lda #<NC_BC
 sta se_overlay_frame+1
 lda #>NC_BC
 sta se_overlay_frame+2
 lda #1
 jsr leaf
 bcs @return
 ldx BCOL
 lda $DBC0,x
 and #15
 asl
 asl
 asl
 asl
 ora #6
 sta $43C0,x
 inc BCOL
 lda BCOL
 cmp #12
 bne :+
 lda #14
 sta BCOL
: cmp #22
 bcc @cell
 lda #0
 clc
@return:
 rts
.segment "RODATA"
palette: .byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
bits:.byte 1,2,4,8,16,32,64,128

.segment "CODE"
.import se_l_caret

; Pure source-grid layout admission, moved verbatim from resident preflight.
; Called only after resident se_ef_prepare; no buffer/phase/C nesting.
se_grid_plan:
 lda se_ef_valid
 beq @ordinary
 lda se_l_valid
 beq @start
 ldx #1
@fold_generation:
 lda se_ef_generation,x
 cmp se_ef_projection_generation,x
 bne @start
 dex
 bpl @fold_generation
 CMP24 se_hot_caret,se_l_caret
 bne @start
 CMP24 se_v_top,se_l_top
 bne @start
@ordinary:
 lda se_l_mode
 bne @context
 lda se_l_need_wrap
 beq @ready
@start:
 lda #1
 clc
 rts
@context:
 lda #2
 clc
 rts
@ready:
 lda #0
 clc
 rts

.segment "CODE"
; Exact selector-union delta over a certified unchanged narrow row.
; NR inverse/char/role are unchanged. Arbitration uses base ink, so attributes
; cannot change. XOR only cells whose (SELECTED|CARET) boolean changed.
CHANGE=C+44 ;A/B counts
CELLA=C+46 ;two column ordinals
CELLB=C+48 ;two column ordinals
WAS=C+50
PX=C+51 ;2
RIGHTMASK=C+53
LEFTMASK=C+54
CELLPTR=C+55 ;2
LEFT=C+57
DELTAFLAG=C+58
xor_changes:
 ldx #0
 lda PTR
 cmp #<P
 beq @first
 inx
@first:
 lda CHANGE,x
 beq @done
 sta LEFT
 txa
 asl
 clc
 adc #<CELLA
 sta CELLPTR
 lda #>CELLA
 adc #0
 sta CELLPTR+1
@cell:
 lda CELLPTR
 sta text_ptr
 lda CELLPTR+1
 sta text_ptr+1
 ldy #0
 lda (text_ptr),y
 jsr xor_cell
 inc CELLPTR
 bne :+
 inc CELLPTR+1
: dec LEFT
 bne @cell
@done:
 clc
 rts
xor_cell:
 sta DELTAFLAG
 lda #0
 sta PX+1
 lda DELTAFLAG
 asl
 rol PX+1
 asl
 rol PX+1
 ldx W
 cpx #60
 bne @four
 clc
 adc DELTAFLAG
 bcc :+
 inc PX+1
: clc
 adc #10
 bcc :+
 inc PX+1
: ldx #$F8
 bne @pixel
@four:
 ldx #$F0
@pixel:
 pha
 and #7
 tay
 stx RIGHTMASK
 lda #0
 sta LEFTMASK
 cpy #0
 beq @mask
@shift:
 lsr RIGHTMASK
 ror LEFTMASK
 dey
 bne @shift
@mask:
 pla
 and #$F8
 sta PX
 ldx ROW
 inx
 inx
@row:
 clc
 lda PX
 adc #$40
 sta PX
 lda PX+1
 adc #1
 sta PX+1
 dex
 bne @row
 lda PX
 sta text_ptr
 lda PX+1
 clc
 adc #$60
 sta text_ptr+1
 ldy #7
@right:
 lda (text_ptr),y
 eor RIGHTMASK
 sta (text_ptr),y
 dey
 bpl @right
 lda LEFTMASK
 beq @done
 ldy #15
@left:
 lda (text_ptr),y
 eor LEFTMASK
 sta (text_ptr),y
 dey
 cpy #7
 bne @left
@done:
 rts
