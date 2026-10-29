; C33 retained-input narrow caret transaction. No resident/ZP state.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "api.inc"
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
.include "render/geos/editor.inc"
.include "render/geos/page-paint.inc"
S=GPP_STATE
R=S+$20
source=S+$42
lo=S+$48
hi=S+$4B
want=S+$9E
flags=S+$9F
char=S+$5D
role=S+$5E
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 cmp #2
 bcc original
 jmp helpers
original:
 cmp #0
 jne selection_bounds
.include "render/geos/tail-policy.inc"
busy:
 lda #$B2
 sec
 rts

helpers:
 cmp #2
 bne :+
 jmp admit
:
 cmp #3
 bne :+
 jmp fields
:
 cmp #4
 bne :+
 jmp header_crc
:
 cmp #5
 bne :+
 jmp store_header
:
 cmp #6
 bne :+
 jmp fetch_header
:
 cmp #7
 bne :+
 lda PTR
 ldx PTR+1
 jmp fetch_row
:
 cmp #8
 bne :+
 jmp row_request
:
 cmp #9
 bne :+
 jmp packet_crc
:
 cmp #10
 bne :+
 jmp verify_row
:
 cmp #11
 bne :+
 jmp bounds
:
 cmp #12
 bne :+
 jmp retreat
:
 cmp #13
 bne :+
 jmp row_bit
:
 cmp #14
 jeq type_prepare
 cmp #15
 jeq type_commit
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
 lda C+63
 bne @revision_done
 ldx #3
@revision:
 lda se_r_revision,x
 cmp se_l_revision,x
 jne invalid
 dex
 bpl @revision
@revision_done:
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
 lda C+63
 beq @read
 cpy #N_KEY+17
 bcc @read
 cpy #N_KEY+24
 bcc @skip
 cpy #N_PENDING
 beq @skip
 cpy #N_HOTLEN
 beq @skip
 cpy #N_HOTLEN+1
 beq @skip
@read:
 lda (text_ptr),y
 cmp H,y
 jne invalid
@skip:
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

.segment "CODE"
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

.segment "RODATA"
bits:.byte 1,2,4,8,16,32,64,128
