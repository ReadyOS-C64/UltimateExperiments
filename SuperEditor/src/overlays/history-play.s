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
.include "document/api.inc"
.include "document/math24.inc"
.include "object/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    jsr se_h_validate
    jcs return
    lda se_overlay_frame
    cmp #H_UNDO
    jeq undo
    cmp #H_REDO
    jeq redo
    cmp #H_STEP
    jne state
    lda se_h_phase
    cmp #H_COPY
    jeq copy
    cmp #H_VERIFY
    jeq verify
    cmp #H_REPLAY
    jeq replay
state:
    lda #$60
    sec
return:
    rts
abort:
    jmp se_h_abort
bad:
    lda #$62
    jmp abort
pending:
    lda #1
    clc
    rts
noop:
    lda #0
    sta se_h_applied
    sta se_h_open_group
    clc
    rts
undo:
    lda se_h_cursor
    ora se_h_cursor+1
    beq noop
    lda #2
    bne begin
redo:
    lda se_h_cursor+1
    cmp se_h_end+1
    bne @start
    lda se_h_cursor
    cmp se_h_end
    beq noop
@start:
    lda #3
begin:
    sta se_h_action
    lda #0
    sta se_h_applied
    jsr se_doc_read_acquire
    jcs return
    lda #1
    sta se_h_owned_lease
    lda #H_COPY
    sta se_h_phase
    lda se_h_action
    cmp #3
    beq @redo
    sec
    lda se_h_cursor
    sbc #2
    sta se_h_io_pos
    lda se_h_cursor+1
    sbc #0
    sta se_h_io_pos+1
    jcc bad
    lda #0
    sta se_h_io_pos+2
    sta se_h_io_count+1
    lda #2
    sta se_h_io_count
    lda #1
    jsr se_h_io
    jcs abort
    lda $8000
    sta se_h_record_len
    lda $8001
    sta se_h_record_len+1
    sec
    lda se_h_cursor
    sbc se_h_record_len
    sta se_h_record_start
    lda se_h_cursor+1
    sbc se_h_record_len+1
    sta se_h_record_start+1
    jcc bad
    jmp @header
@redo:
    lda se_h_cursor
    sta se_h_record_start
    lda se_h_cursor+1
    sta se_h_record_start+1
@header:
    clc
    lda se_h_record_start
    adc #64
    sta se_h_tmp
    lda se_h_record_start+1
    adc #0
    jcs bad
    cmp se_h_end+1
    bcc @read
    jne bad
    lda se_h_tmp
    cmp se_h_end
    bcc @read
    jne bad
@read:
    lda se_h_record_start
    sta se_h_io_pos
    lda se_h_record_start+1
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
    lda se_h_action
    cmp #3
    beq @length
    lda $8006
    cmp se_h_record_len
    jne bad
    lda $8007
    cmp se_h_record_len+1
    jne bad
@length:
    lda $8006
    sta se_h_record_len
    lda $8007
    sta se_h_record_len+1
    clc
    lda se_h_record_start
    adc se_h_record_len
    sta se_h_tmp
    lda se_h_record_start+1
    adc se_h_record_len+1
    jcs bad
    cmp se_h_end+1
    bcc @node
    jne bad
    lda se_h_tmp
    cmp se_h_end
    bcc @node
    jne bad
@node:
    ldy #12
    lda se_h_action
    cmp #2
    beq :+
    ldy #8
:
    ldx #0
@compare:
    lda $8000,y
    cmp se_h_current,x
    jne bad
    iny
    inx
    cpx #4
    bcc @compare
    ldx #63
@save:
    lda $8000,x
    sta se_h_record,x
    dex
    bpl @save
    lda se_h_record_len
    sta se_h_io_left
    lda se_h_record_len+1
    sta se_h_io_left+1
    lda #0
    sta se_h_io_dest
    sta se_h_io_dest+2
    lda #$B0
    sta se_h_io_dest+1
    ; io_pos is still the record's active source start.
    jmp pending
copy:
    jsr h_copy_packet
    jcs abort
    cmp #1
    jeq pending
    ; Validate the copied header independently before using staged references.
    lda #0
    sta se_h_io_pos
    sta se_h_io_pos+2
    sta se_h_io_count+1
    lda #$B0
    sta se_h_io_pos+1
    lda #64
    sta se_h_io_count
    lda #1
    jsr se_h_io
    jcs abort
    jsr h_header_check
    jcs abort
    ldx #63
@same:
    lda $8000,x
    cmp se_h_record,x
    jne bad
    dex
    bpl @same
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
    lda #H_VERIFY
    sta se_h_phase
    jmp pending
verify:
    jsr h_crc_request
    jcs abort
    cmp #1
    jeq pending
    lda se_h_crc
    cmp se_h_record+56
    jne bad
    lda se_h_crc+1
    cmp se_h_record+57
    jne bad
    sec
    lda se_h_record_len
    sbc #2
    sta se_h_io_pos
    lda se_h_record_len+1
    sbc #0
    clc
    adc #$B0
    sta se_h_io_pos+1
    lda #0
    sta se_h_io_pos+2
    sta se_h_io_count+1
    lda #2
    sta se_h_io_count
    lda #1
    jsr se_h_io
    jcs abort
    lda $8000
    cmp se_h_record_len
    jne bad
    lda $8001
    cmp se_h_record_len+1
    jne bad
    lda #H_REPLAY
    sta se_h_phase
    jmp pending
replay:
    lda se_h_owned_splice
    jne apply
    lda se_doc_read_locks
    jeq bad
    cmp #1
    jne pending
    ; Configure the same selected source edit in either direction.
    COPY24 se_h_record+26,se_doc_edit_position
    lda se_h_action
    cmp #2
    bne @redo
    COPY24 se_h_record+32,se_doc_edit_delete
    COPY24 se_h_record+29,se_doc_edit_insert
    lda se_h_record+35
    sta se_doc_refs_pieces
    lda se_h_record+36
    sta se_doc_refs_pieces+1
    lda #64
    sta se_doc_refs_offset
    lda #$B0
    sta se_doc_refs_offset+1
    jmp @token
@redo:
    COPY24 se_h_record+29,se_doc_edit_delete
    COPY24 se_h_record+32,se_doc_edit_insert
    lda se_h_record+37
    sta se_doc_refs_pieces
    lda se_h_record+38
    sta se_doc_refs_pieces+1
    lda se_h_record+35
    sta se_h_tmp
    lda se_h_record+36
    sta se_h_tmp+1
    .repeat 3
        asl se_h_tmp
        rol se_h_tmp+1
    .endrepeat
    clc
    lda se_h_tmp
    adc se_h_record+35
    sta se_h_tmp
    lda se_h_tmp+1
    adc se_h_record+36
    sta se_h_tmp+1
    clc
    lda se_h_tmp
    adc #64
    sta se_doc_refs_offset
    lda se_h_tmp+1
    adc #$B0
    sta se_doc_refs_offset+1
@token:
    ; Both stored carets must be valid in their respective source versions.
    SUB24 se_doc_length,se_doc_edit_delete,se_h_tmp
    jcc bad
    ADD24 se_h_tmp,se_doc_edit_insert,se_h_tmp
    jcs bad
    lda se_h_action
    cmp #2
    bne @redo_carets
    CMP24 se_h_record+39,se_h_tmp
    bcc :+
    jne bad
:
    CMP24 se_h_record+42,se_doc_length
    bcc @carets_valid
    jne bad
    jmp @carets_valid
@redo_carets:
    CMP24 se_h_record+42,se_h_tmp
    bcc :+
    jne bad
:
    CMP24 se_h_record+39,se_doc_length
    bcc @carets_valid
    jne bad
@carets_valid:
    lda #0
    sta se_doc_refs_offset+2
    ldx #4
@copy_token:
    lda se_h_token,x
    sta se_doc_refs_token,x
    dex
    bpl @copy_token
    jsr se_doc_read_release
    jcs abort
    lda #0
    sta se_h_owned_lease
    jsr se_doc_splice_local_refs_begin
    jcs abort
    cmp #1
    jne bad
    sta se_h_owned_splice
    jmp pending
apply:
    jsr se_doc_splice_step
    jcs abort
    cmp #1
    jeq pending
.ifdef EDITOR_BINDINGS
    jsr se_ef_journal_commit
.endif
    lda #0
    sta se_h_owned_splice
    sta se_h_phase
    sta se_h_open_group
    lda #1
    sta se_h_applied
    lda se_doc_generation
    sta se_h_generation
    lda se_doc_generation+1
    sta se_h_generation+1
    lda se_h_action
    cmp #2
    bne forward
    ldx #3
@node:
    lda se_h_record+8,x
    sta se_h_current,x
    dex
    bpl @node
    ldx #2
@caret:
    lda se_h_record+39,x
    sta se_h_caret,x
    dex
    bpl @caret
    lda se_h_record_start
    sta se_h_cursor
    lda se_h_record_start+1
    sta se_h_cursor+1
    jmp complete
forward:
    ldx #3
@node:
    lda se_h_record+12,x
    sta se_h_current,x
    dex
    bpl @node
    ldx #2
@caret:
    lda se_h_record+42,x
    sta se_h_caret,x
    dex
    bpl @caret
    clc
    lda se_h_record_start
    adc se_h_record_len
    sta se_h_cursor
    lda se_h_record_start+1
    adc se_h_record_len+1
    sta se_h_cursor+1
complete:
    jsr se_h_dirty_update
    lda #0
    clc
    rts
.include "history/record.inc"
