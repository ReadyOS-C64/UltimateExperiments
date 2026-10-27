.include "render/presentation.inc"
.import se_e_target,se_e_command
; C33 retained-input narrow caret transaction. No resident/ZP state.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "api.inc"
.include "style/api.inc"
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
.import se_overlay_active
.import se_overlay_ids,image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi,se_overlay_asset,asset_epoch
.import se_reu_retired,se_reu_epoch,se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_crc_table_low,se_crc_table_high
.import se_i_ready,se_i_count,se_n_cache_count
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
 cmp #4
 jeq lrv_paint_entry
 cmp #1
 bne @not_frame1
 lda se_st_tx+ST_TX_PHASE
 cmp #ST_TX_ADMITTED
 bne @ready
 lda #ST_TX_WAIT
 clc
 rts
@ready:
 cmp #ST_TX_READY
 jeq lrv_paint_entry
 lda se_render_caps
 bne @ordinary_frame1
 lda $8D23                  ;LRVT+LT_PREPARED, private R25 transaction marker
 cmp #$A5
 jeq lrv_paint_entry
@ordinary_frame1:
 lda #1                    ;retain ordinary warm-caret frame semantics
@not_frame1:
 cmp #3
 bne ordinary_entry
 ldx se_f_owner
 beq @idle
 lda #$B2
 sec
 rts
@idle:
 ldx #2
@copy:
 lda se_hot_caret,x
 sta se_e_target,x
 dex
 bpl @copy
 lda #47
 sta se_e_command
 lda se_mode
 cmp #3
 bne @committed
 lda #1
 bne @done
@committed:
 lda #0
@done:
 clc
 rts
ordinary_entry:
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
 lda #0
 sta C+63
 sta C+62 ;capture-only retained R-slot catalogue index, zero before first admission
 lda OP
 beq :+
 ldx #3
@typed_revision:
 lda se_r_revision,x
 cmp se_l_revision,x
 jne type_try
 dex
 bpl @typed_revision
:
 jsr authenticate_helper
 jcs miss
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
 ; Guarded verified backing + C33-owned native font; no R16 execution.
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
 lda se_overlay_active
 sta C+62 ;checked R25; guard every refusal before borrowing the phase
 jsr capture_tables
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
 tax ;overlay dispatcher preserves A but clobbers X
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
 bcc @row ;range proven by assembler
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
 lda se_st_tx+ST_TX_PHASE
 cmp #ST_TX_READY
 bne :+
 lda #ST_TX_INVALID
 sta se_st_tx+ST_TX_PHASE
 sta se_st_cp_valid
:
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
.include "helper-witness.inc"
.include "paragraph-witness.inc"
invalid:
 sec
 rts
admit:
 lda #2
 jmp helper
fields:
 lda #3
 jmp helper
header_crc:
 lda #4
 jmp helper
store_header:
 lda #5
 jmp helper
fetch_header:
 lda #6
 jmp helper
fetch_row:
 sta PTR
 stx PTR+1
 lda #7
 jmp helper
row_request:
 lda #8
 jmp helper
packet_crc:
 lda OP
 bne @ordinary
 jsr se_crc_init
 ldy #0
@byte:
 lda P,y
 eor se_crc_value+1
 tax
 lda se_crc_value
 eor $8E00,x
 sta se_crc_value+1
 lda $8D00,x
 sta se_crc_value
 iny
 cpy #240
 bcc @byte
 rts
@ordinary:
 lda #9
 jmp helper
verify_row:
 lda #10
 jmp helper
bounds:
 lda #11
 jmp helper
retreat:
 lda #12
 jmp helper
row_bit:
 lda #13
 jmp helper
helper:
 sta se_overlay_frame
 ldx OP
 bne @ordinary
 ldx C+62
 beq @ordinary
 cpx se_overlay_active
 bne @ordinary
 ; Exclusive capture calls only resident source/CRC/DMA between helpers.
 ; The actual real-loader-admitted R25 remains at its public fixed entry.
 jmp $A010
@ordinary:
 lda #25
 ldx #0
 jmp se_overlay_call
; CAPTURE borrows the sparse line-index area. Revoke its retained authority
; before the first table write, just as the GEOS page coordinator does.
; Neither source peek nor R25 capture helpers use the inactive FS frame here.
capture_tables:
 .assert (se_crc_table_low & $FF)=0,lderror,"resident half-table alignment"
 .assert se_crc_table_high=se_crc_table_low+128,lderror,"resident half-table layout"
 lda #0
 sta se_i_ready
 sta se_i_count
 sta se_n_cache_count
 ldx #0
@byte:
 lda se_crc_table_low,x
 sta $8D00,x
 eor #$88
 sta $8D80,x
 lda se_crc_table_high,x
 sta $8E00,x
 eor #$91
 sta $8E80,x
 inx
 bpl @byte
 rts
authenticate_helper:
 ldy #0
 beq authenticate_dependencies
authenticate_paragraph:
 ldy #2
authenticate_dependencies:
@image:
 ldx #0
@find:
 lda se_overlay_ids,x
 cmp auth_id,y
 bne @next
 lda image_slot,x
 and auth_mask,y
 cmp auth_slot,y
 beq @found
@next:
 inx
 cpx #64
 bcc @find
 sec
 rts
@found:
 lda image_size_lo,x
 cmp auth_size_lo,y
 bne @miss
 lda image_size_hi,x
 cmp auth_size_hi,y
 bne @miss
 lda image_crc_lo,x
 cmp auth_crc_lo,y
 bne @miss
 lda image_crc_hi,x
 cmp auth_crc_hi,y
 bne @miss
 cpy #3
 beq @authenticated
 dey
 bpl @image
@authenticated:
 clc
 rts
@miss:
 sec
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
; C33's sealed native8 font is part of its own authenticated immutable payload.
; R25 guard requires the actual backend native font's exact bound/verified asset.
status_pixels:
 ldy #7
@row:
 lda (text_ptr),y
 cpx #128
 bcc :+
 eor #$FF
: sta (screen_ptr),y
 dey
 bpl @row
 rts
status:
 jsr tui_editor_status40
 lda #6
 sta BCOL
 lda #48
 sta screen_ptr
 lda #$7E
 sta screen_ptr+1
@cell:
 ldx BCOL
 lda $43C0,x
 pha
 and #127
 ldx #25
@lookup:
 cmp status_codes,x
 beq @mapped
 dex
 bpl @lookup
@mapped:
 txa
 asl
 asl
 asl
 sta text_ptr
 lda #>local_native8
 sta text_ptr+1
 ldx BCOL
 lda $DBC0,x
 and #15
 asl
 asl
 asl
 asl
 ora #6
 sta $43C0,x
 pla
 tax
 jsr status_pixels
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: inc BCOL
 lda BCOL
 cmp #12
 bne :+
 lda #14
 sta BCOL
 lda #112
 sta screen_ptr
: lda BCOL
 cmp #22
 bcc @cell
 rts
.segment "CODE"
.import se_l_caret

; Pure source-grid layout admission, moved verbatim from resident preflight.
; Called only after resident se_ef_prepare; no buffer/phase/C nesting.
se_grid_plan:
 jsr se_ef_visible
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

.segment "CODE"
type_try:
 jmp miss
.include "lrv3-painter.inc"

.segment "NATIVE"
local_native8:
.incbin "status-font.bin"
.assert local_native8=$BF00,lderror,"C33 native font ABI"
.assert *-local_native8=208,error,"C33 native font size"

.segment "RODATA"
auth_id:.byte 25,14,14,14
auth_slot:.byte 0,$81,$80,0
auth_mask:.byte 1,$FF,$FF,1
.segment "RODATA"
auth_size_lo:.byte <HELPER_SIZE,<PARAGRAPH_CODE_SIZE,<PARAGRAPH_SOURCE_SIZE,<PARAGRAPH_SOURCE_SIZE
auth_size_hi:.byte >HELPER_SIZE,>PARAGRAPH_CODE_SIZE,>PARAGRAPH_SOURCE_SIZE,>PARAGRAPH_SOURCE_SIZE
auth_crc_lo:.byte <HELPER_CRC,<PARAGRAPH_CODE_CRC,<PARAGRAPH_SOURCE_CRC,<PARAGRAPH_SOURCE_CRC
auth_crc_hi:.byte >HELPER_CRC,>PARAGRAPH_CODE_CRC,>PARAGRAPH_SOURCE_CRC,>PARAGRAPH_SOURCE_CRC


.segment "RODATA"
nr_defaults:
 .byte 0,0,0,0,6
 .word $6000,$4000,$A800,P,P+80,P+160,palette
.assert *-nr_defaults=19,error,"complete native-row public input template"

.segment "TAIL"
palette: .byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
bits:.byte 1,2,4,8,16,32,64,128
status_codes:.incbin "status-codes.bin"
