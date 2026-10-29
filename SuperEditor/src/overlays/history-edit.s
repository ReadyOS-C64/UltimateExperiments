.setcpu "6502"
.macpack longbranch
.ifdef EDITOR_BINDINGS
    .include "editor-api.inc"
.elseif .defined(HOT_BINDINGS)
    .include "hot-api.inc"
.else
    .include "history-api.inc"
.endif
.include "history/api.inc"
.ifdef EDITOR_BINDINGS
.include "hot/api.inc"
.endif
.include "document/api.inc"
.include "document/math24.inc"
.include "object/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
.ifdef EDITOR_BINDINGS
    cmp #W_PACKET
    jeq hot_packet
.endif
    cmp #H_INIT
    jeq initialize
    cmp #H_SAVED
    jeq saved
    cmp #H_CLEAR
    jeq clear
    cmp #H_BREAK
    jeq break_group
    jsr se_h_validate
    jcs return
    lda se_overlay_frame
    cmp #H_BEGIN
    jeq begin
    cmp #H_STEP
    jne state
    lda se_h_phase
    cmp #H_CAPTURE
    jeq capture
    cmp #H_SEAL
    jeq seal
    cmp #H_SPACE
    jeq space
    cmp #H_FEEDING
    jeq apply
    cmp #H_APPLY
    jeq apply
    cmp #H_MOVE
    jeq move
    cmp #H_APPEND
    jeq append
state:
    lda #$60
    sec
return:
    rts
abort:
    jmp se_h_abort
corrupt:
    lda #$62
    jmp abort
pending:
    lda #1
    clc
    rts

initialize:
    jsr se_doc_validate
    jcs return
    lda se_h_ready
    beq allocate
    DOC_TOKEN se_h_token
    jsr se_object_validate
    bcs allocate
    lda object_owner,x
    cmp #6
    bne corrupt
    lda object_size_lo,x
    ora object_size_mid,x
    bne corrupt
    lda object_size_hi,x
    cmp #1
    bne corrupt
    ldx #4
@same:
    lda se_h_original,x
    cmp se_doc_original,x
    bne new_context
    lda se_h_append,x
    cmp se_doc_append,x
    bne new_context
    dex
    bpl @same
    jmp se_h_validate ; same context is idempotent, including fault state
allocate:
    lda #6
    ldx #1
    jsr se_object_create
    jcs return
    ldy #4
@token:
    lda se_object_id,y
    sta se_h_token,y
    dey
    bpl @token
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    jsr se_object_resize
    jcs return
new_context:
.ifdef EDITOR_BINDINGS
    lda #0
    sta se_bc_ring ;VP_VALID: old BODY cannot survive H_INIT
.endif
    ldx #4
@context:
    lda se_doc_original,x
    sta se_h_original,x
    lda se_doc_append,x
    sta se_h_append,x
    dex
    bpl @context
    lda #0
    sta se_h_end
    sta se_h_end+1
    sta se_h_cursor
    sta se_h_cursor+1
    sta se_h_fault
    sta se_h_phase
    sta se_h_applied
    sta se_h_open_group
    sta se_h_trimmed
    sta se_h_trimmed+1
    ldx #3
@ids:
    sta se_h_current,x
    sta se_h_saved,x
    sta se_h_counter,x
    dex
    bpl @ids
    lda #1
    sta se_h_current
    sta se_h_saved
    sta se_h_counter
    sta se_h_ready
    jsr generation
    jsr se_h_dirty_update
    lda #0
    clc
    rts
saved:
    jsr se_h_validate
    jcs return
    ldx #3
@copy:
    lda se_h_current,x
    sta se_h_saved,x
    dex
    bpl @copy
    jsr se_h_dirty_update
    jmp break_group
clear:
    jsr se_h_context
    jcs return
    lda #0
    sta se_h_end
    sta se_h_end+1
    sta se_h_cursor
    sta se_h_cursor+1
    sta se_h_fault
break_group:
    lda #0
    sta se_h_open_group
    clc
    rts

begin:
    lda #0
    sta se_h_applied
    jsr se_doc_splice_local_begin ; dry-run range/quota/old-slot admission
    jcs return
    cmp #0
    bne :+
    clc
    rts
:
    jsr se_doc_splice_cancel
    CMP24 se_h_before_caret,se_doc_length
    bcc @after
    jne range_error
@after:
    SUB24 se_doc_length,se_doc_edit_delete,se_h_tmp
    ADD24 se_h_tmp,se_doc_edit_insert,se_h_tmp
    CMP24 se_h_after_caret,se_h_tmp
    bcc @carets_valid
    jne range_error
@carets_valid:
    lda se_h_counter
    and se_h_counter+1
    and se_h_counter+2
    and se_h_counter+3
    cmp #$FF
    jeq exhausted
    jsr se_doc_read_acquire
    jcs return
    lda #1
    sta se_h_owned_lease
    sta se_h_action
    ldx #8
@request:
    lda se_doc_edit_position,x
    sta se_h_request,x
    dex
    bpl @request
    DOC_TOKEN se_doc_append
    jsr se_object_validate
    jcs abort
    lda object_size_lo,x
    sta se_h_base_append
    lda object_size_mid,x
    sta se_h_base_append+1
    lda object_size_hi,x
    sta se_h_base_append+2
    ldx #3
@node:
    lda se_h_counter,x
    sta se_h_target_node,x
    dex
    bpl @node
    inc se_h_target_node
    bne @node_done
    inc se_h_target_node+1
    bne @node_done
    inc se_h_target_node+2
    bne @node_done
    inc se_h_target_node+3
@node_done:
    ; Stage a new record; an adjacent pure-typing group may replace the last.
    ldx #63
    lda #0
@zero:
    sta se_h_record,x
    dex
    bpl @zero
    ldx #3
@magic:
    lda h_magic,x
    sta se_h_record,x
    lda se_h_current,x
    sta se_h_record+8,x
    lda se_h_target_node,x
    sta se_h_record+12,x
    dex
    bpl @magic
    lda #H_RECORD_ABI
    sta se_h_record+4
    ldx #4
@context:
    lda se_h_original,x
    sta se_h_record+16,x
    sta se_range_token,x ; overwritten with journal below
    lda se_h_append,x
    sta se_h_record+21,x
    lda se_h_token,x
    sta se_range_token,x
    dex
    bpl @context
    ldx #8
@edit:
    lda se_h_request,x
    sta se_h_record+26,x
    dex
    bpl @edit
    ldx #2
@carets:
    lda se_h_before_caret,x
    sta se_h_record+39,x
    lda se_h_after_caret,x
    sta se_h_record+42,x
    dex
    bpl @carets
    lda se_h_cursor
    sta se_h_keep_end
    lda se_h_cursor+1
    sta se_h_keep_end+1
    lda se_h_request+3
    ora se_h_request+4
    ora se_h_request+5
    bne @separate
    lda se_h_group
    beq @separate
    sta se_h_record+45
    lda #1
    sta se_h_record+5
    jsr try_group
    jcs abort
@separate:
    lda #0
    sta se_h_keep_start
    sta se_h_keep_start+1
    sta se_h_trim_count
    sta se_h_trim_count+1
    COPY24 se_h_request,se_range_position
    COPY24 se_h_request+3,se_range_length
    lda #$40
    sta se_range_offset
    lda #$B0
    sta se_range_offset+1
    lda #0
    sta se_range_offset+2
    jsr se_range_begin
    jcs abort
    sta se_h_owned_capture
    lda #H_CAPTURE
    sta se_h_phase
    jmp pending
range_error:
    lda #$32
    sec
    rts
exhausted:
    lda #$63
    sec
    rts

capture:
    lda se_h_owned_capture
    beq tail
    jsr se_range_step
    jcs abort
    cmp #1
    jeq pending
    lda #0
    sta se_h_owned_capture
tail:
    lda se_range_pieces
    sta se_h_record+35
    lda se_range_pieces+1
    sta se_h_record+36
    clc
    lda se_range_bytes
    adc #64
    sta se_h_insert_offset
    lda se_range_bytes+1
    adc #$B0
    sta se_h_insert_offset+1
    lda #0
    sta se_h_insert_offset+2
    lda #0
    sta se_h_io_count+1
    lda se_h_record+32
    ora se_h_record+33
    ora se_h_record+34
    beq no_insert
    ldx #2
@token:
    lda se_h_append,x
    sta $8000,x
    lda se_h_base_append,x
    sta $8003,x
    lda se_h_record+32,x
    sta $8006,x
    dex
    bpl @token
    lda #1
    sta se_h_record+37
    lda #9
no_insert:
    tax
    clc
    adc se_range_bytes
    sta se_h_record_len
    lda se_range_bytes+1
    adc #0
    sta se_h_record_len+1
    clc
    lda se_h_record_len
    adc #66
    sta se_h_record_len
    sta se_h_record+6
    lda se_h_record_len+1
    adc #0
    sta se_h_record_len+1
    sta se_h_record+7
    lda se_h_record_len
    sta $8000,x
    lda se_h_record_len+1
    sta $8001,x
    inx
    inx
    stx se_h_io_count
    COPY24 se_h_insert_offset,se_h_io_pos
    lda #0
    jsr se_h_io
    jcs abort
    lda #$FF
    sta se_h_crc
    sta se_h_crc+1
    lda #$40
    sta se_h_crc_pos
    lda #$B0
    sta se_h_crc_pos+1
    lda #0
    sta se_h_crc_pos+2
    sec
    lda se_h_record_len
    sbc #64
    sta se_h_crc_left
    lda se_h_record_len+1
    sbc #0
    sta se_h_crc_left+1
    lda #H_SEAL
    sta se_h_phase
    jmp pending
seal:
    jsr h_crc_request
    jcs abort
    cmp #1
    jeq pending
    lda se_h_crc
    sta se_h_record+56
    lda se_h_crc+1
    sta se_h_record+57
    jsr h_header_save
    jcs abort
    lda #H_SPACE
    sta se_h_phase
    jmp pending

space:
    sec
    lda se_h_keep_end
    sbc se_h_keep_start
    sta se_h_keep_len
    lda se_h_keep_end+1
    sbc se_h_keep_start+1
    sta se_h_keep_len+1
    jcc corrupt
    clc
    lda se_h_keep_len
    adc se_h_record_len
    sta se_h_tmp
    lda se_h_keep_len+1
    adc se_h_record_len+1
    jcs corrupt
    cmp #$B0
    bcc admitted
    bne evict
    lda se_h_tmp
    beq admitted
evict:
    lda se_h_keep_start
    sta se_h_io_pos
    lda se_h_keep_start+1
    sta se_h_io_pos+1
    lda #0
    sta se_h_io_pos+2
    sta se_h_io_count+1
    lda #64
    sta se_h_io_count
    lda #1
    jsr se_h_io
    jcs abort
    jsr h_header_check
    jcs abort
    clc
    lda se_h_keep_start
    adc $8006
    sta se_h_tmp
    lda se_h_keep_start+1
    adc $8007
    jcs corrupt
    cmp se_h_keep_end+1
    bcc @advance
    jne corrupt
    lda se_h_tmp
    cmp se_h_keep_end
    bcc @advance_low
    jne corrupt
@advance_low:
    lda se_h_keep_end+1
@advance:
    sta se_h_keep_start+1
    lda se_h_tmp
    sta se_h_keep_start
    inc se_h_trim_count
    bne :+
    inc se_h_trim_count+1
:
    jmp pending
admitted:
    lda se_doc_read_locks
    jeq corrupt
    cmp #1
    jne pending ; wait for foreign readers while retaining the outer lease
    jsr se_doc_read_release
    jcs abort
    lda #0
    sta se_h_owned_lease
    ldx #8
@restore:
    lda se_h_request,x
    sta se_doc_edit_position,x
    dex
    bpl @restore
    jsr se_doc_splice_local_begin
    jcs abort
    cmp #1
    jne corrupt
    sta se_h_owned_splice
    lda #H_FEEDING
    sta se_h_phase
    jmp pending
apply:
    jsr se_doc_splice_step
    bcc @result
    cmp #$45
    jeq return ; retryable missing insertion input, transaction stays active
    jmp abort
@result:
    cmp #1
    bne committed
    lda #H_APPLY
    sta se_h_phase
    jmp pending
committed:
.ifdef EDITOR_BINDINGS
    jsr se_ef_journal_publish
.endif
    lda #0
    sta se_h_owned_splice
    lda #1
    sta se_h_applied
    ldx #3
@node:
    lda se_h_target_node,x
    sta se_h_current,x
    sta se_h_counter,x
    dex
    bpl @node
    ldx #2
@caret:
    lda se_h_record+42,x
    sta se_h_caret,x
    dex
    bpl @caret
    jsr generation
    lda se_h_record+45
    sta se_h_open_group
    jsr se_h_dirty_update
    jsr se_doc_read_acquire
    jcs abort
    lda #1
    sta se_h_owned_lease
    lda se_h_keep_start
    ora se_h_keep_start+1
    beq start_append
    lda se_h_keep_start
    sta se_h_io_pos
    lda se_h_keep_start+1
    sta se_h_io_pos+1
    lda se_h_keep_len
    sta se_h_io_left
    lda se_h_keep_len+1
    sta se_h_io_left+1
    lda #0
    sta se_h_io_pos+2
    sta se_h_io_dest
    sta se_h_io_dest+1
    sta se_h_io_dest+2
    lda #H_MOVE
    sta se_h_phase
    jmp pending
move:
    lda se_h_io_left
    ora se_h_io_left+1
    beq start_append
    jsr h_copy_packet
    jcs abort
    cmp #1
    jeq pending
start_append:
    lda #0
    sta se_h_io_pos
    sta se_h_io_pos+2
    sta se_h_io_dest+2
    lda #$B0
    sta se_h_io_pos+1
    lda se_h_keep_len
    sta se_h_io_dest
    lda se_h_keep_len+1
    sta se_h_io_dest+1
    lda se_h_record_len
    sta se_h_io_left
    lda se_h_record_len+1
    sta se_h_io_left+1
    lda #H_APPEND
    sta se_h_phase
    jmp pending
append:
    jsr h_copy_packet
    jcs abort
    cmp #1
    jeq pending
    clc
    lda se_h_keep_len
    adc se_h_record_len
    sta se_h_end
    sta se_h_cursor
    lda se_h_keep_len+1
    adc se_h_record_len+1
    sta se_h_end+1
    sta se_h_cursor+1
    clc
    lda se_h_trimmed
    adc se_h_trim_count
    sta se_h_trimmed
    lda se_h_trimmed+1
    adc se_h_trim_count+1
    sta se_h_trimmed+1
    jsr se_doc_read_release
    lda #0
    sta se_h_owned_lease
    sta se_h_phase
    clc
    rts
generation:
    lda se_doc_generation
    sta se_h_generation
    lda se_doc_generation+1
    sta se_h_generation+1
    rts
; Merge only an adjacent pure insertion in the same open group, never across
; a savepoint or redo branch. The old record stays intact until text commits.
try_group:
    lda se_h_group
    cmp se_h_open_group
    jne group_no
    lda se_h_cursor
    cmp se_h_end
    jne group_no
    lda se_h_cursor+1
    cmp se_h_end+1
    jne group_no
    ldx #3
@savepoint:
    lda se_h_current,x
    cmp se_h_saved,x
    bne @eligible
    dex
    bpl @savepoint
    jmp group_no
@eligible:
    sec
    lda se_h_cursor
    sbc #75
    sta se_h_io_pos
    lda se_h_cursor+1
    sbc #0
    sta se_h_io_pos+1
    jcc corrupt
    lda #0
    sta se_h_io_pos+2
    sta se_h_io_count+1
    lda #75
    sta se_h_io_count
    lda #1
    jsr se_h_io
    jcs group_return
    jsr h_header_check
    jcs group_return
    lda $8006
    cmp #75
    jne corrupt
    lda $8007
    jne corrupt
    lda $802D
    cmp se_h_group
    jne group_no
    lda $8005
    cmp #1
    jne group_no
    lda $8023
    ora $8024
    jne group_no
    lda $8025
    cmp #1
    jne group_no
    lda $8049
    cmp #75
    jne corrupt
    lda $804A
    jne corrupt
    ldx #3
@current:
    lda $800C,x
    cmp se_h_current,x
    jne corrupt
    dex
    bpl @current
    ldx #2
@source:
    lda $8040,x
    cmp se_h_append,x
    jne corrupt
    lda $8046,x
    cmp $8020,x
    jne corrupt
    dex
    bpl @source
    jsr se_crc_init
    ldy #64
@body_crc:
    lda $8000,y
    jsr se_crc_byte
    iny
    cpy #75
    bcc @body_crc
    lda se_crc_value
    cmp $8038
    jne corrupt
    lda se_crc_value+1
    cmp $8039
    jne corrupt
    ADD24 $801A,$8020,se_h_tmp
    jcs corrupt
    CMP24 se_h_tmp,se_h_request
    jne group_no
    ADD24 $8043,$8046,se_h_tmp
    jcs corrupt
    CMP24 se_h_tmp,se_h_base_append
    jne group_no
    lda se_h_io_pos
    sta se_h_keep_end
    lda se_h_io_pos+1
    sta se_h_keep_end+1
    ldx #3
@before:
    lda $8008,x
    sta se_h_record+8,x
    dex
    bpl @before
    ldx #2
@merge:
    lda $801A,x
    sta se_h_record+26,x
    lda $8027,x
    sta se_h_record+39,x
    lda $8043,x
    sta se_h_base_append,x
    dex
    bpl @merge
    ADD24 $8020,se_h_request+6,se_h_record+32
    jcs corrupt
group_no:
    clc
group_return:
    rts
H_HEADER_WRITER=1
.include "history/record.inc"

.ifdef EDITOR_BINDINGS
.include "history/hot_packet.inc"
.endif

.ifdef EDITOR_BINDINGS
.include "cache/api.inc"
; H_INIT has validated/adopted the new source. Retain the arena token solely
; for checked reclamation; no old root or queued event may certify this source.
.endif
