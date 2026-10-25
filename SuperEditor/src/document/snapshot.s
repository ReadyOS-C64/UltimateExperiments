.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/math24.inc"
.segment "DOCSTATE"
se_snapshot_token: .res 5 ; caller-owned type6 journal, committed working region
se_snapshot_offset: .res 3
se_snapshot_pieces: .res 2
se_snapshot_length: .res 3
se_snapshot_bytes: .res 2
snap_token: .res 5
snap_pos: .res 3
snap_expected: .res 2
snap_end: .res 3
snap_epoch: .res 2
snap_generation: .res 2
snap_packet: .res 1
snap_budget: .res 1
snap_eof: .res 1
snap_error: .res 1
.segment "CODE"
; Packed records are ID/gen16/offset24/length24 =9 bytes; no raw code pointers.
; Caller owns destination staging region, never an active journal record.
se_snapshot_begin:
    jsr se_doc_validate
    jcs @return
    lda se_snapshot_busy
    jne @busy
    DOC_TOKEN se_snapshot_token
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #6
    jne @corrupt
    lda #0
    sta snap_expected
    sta snap_expected+1
    ldy #0
@count:
    tya
    lsr
    lsr
    lsr
    cmp se_doc_root_count
    bcs @counted
    lda se_doc_roots+1,y
    jeq @corrupt
    cmp #65
    jcs @corrupt
    clc
    adc snap_expected
    sta snap_expected
    bcc :+
    inc snap_expected+1
:
    tya
    clc
    adc #8
    tay
    bne @count
@counted:
    ; root count already bounded32 => at most2048 records =>18432 packed bytes.
    lda snap_expected
    sta se_snapshot_bytes
    lda snap_expected+1
    sta se_snapshot_bytes+1
    .repeat 3
        asl se_snapshot_bytes
        rol se_snapshot_bytes+1
    .endrepeat
    clc
    lda se_snapshot_bytes
    adc snap_expected
    sta se_snapshot_bytes
    lda se_snapshot_bytes+1
    adc snap_expected+1
    sta se_snapshot_bytes+1
    clc
    lda se_snapshot_offset
    adc se_snapshot_bytes
    sta snap_end
    lda se_snapshot_offset+1
    adc se_snapshot_bytes+1
    sta snap_end+1
    lda se_snapshot_offset+2
    adc #0
    sta snap_end+2
    jcs @range
    cmp object_size_hi,x
    bcc @ready
    jne @range
    lda snap_end+1
    cmp object_size_mid,x
    bcc @ready
    jne @range
    lda snap_end
    cmp object_size_lo,x
    bcc @ready
    jne @range
@ready:
    jsr se_doc_read_acquire
    jcs @return
    ldy #4
@token:
    lda se_snapshot_token,y
    sta snap_token,y
    dey
    bpl @token
    COPY24 se_snapshot_offset,snap_pos
    COPY24 se_doc_length,se_snapshot_length
    lda se_doc_epoch
    sta snap_epoch
    lda se_doc_epoch+1
    sta snap_epoch+1
    lda se_doc_generation
    sta snap_generation
    lda se_doc_generation+1
    sta snap_generation+1
    lda #0
    sta se_snapshot_pieces
    sta se_snapshot_pieces+1
    jsr se_doc_walk_reset
    lda #1
    sta se_snapshot_busy
    clc
@return:
    rts
@busy:
    lda #$41
    sec
    rts
@corrupt:
    lda #$42
    sec
    rts
@range:
    lda #$32
    sec
    rts

; At most8 validated pieces per call; source read lease remains until EOF.
se_snapshot_step:
    lda se_snapshot_busy
    cmp #1
    jne @state
    jsr se_doc_validate
    jcs snap_abort
    lda se_doc_generation
    cmp snap_generation
    jne @changed
    lda se_doc_generation+1
    cmp snap_generation+1
    jne @changed
    lda #0
    sta snap_packet
    sta snap_eof
    lda #8
    sta snap_budget
@piece:
    jsr se_doc_walk_next
    bcc @pack
    cmp #0
    jne snap_abort
    lda #1
    sta snap_eof
    bne @flush
@pack:
    ldy snap_packet
    ldx #0
@byte:
    lda se_doc_walk_piece,x
    sta $8000,y
    iny
    inx
    cpx #9
    bcc @byte
    sty snap_packet
    inc se_snapshot_pieces
    bne :+
    inc se_snapshot_pieces+1
:
    dec snap_budget
    bne @piece
@flush:
    lda snap_packet
    beq @status
    DOC_TOKEN snap_token
    COPY24 snap_pos,se_object_offset
    lda #0
    sta se_object_length+1
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda snap_packet
    sta se_object_length
    lda #0
    jsr se_object_copy
    bcs snap_abort
    clc
    lda snap_pos
    adc snap_packet
    sta snap_pos
    bcc @status
    inc snap_pos+1
    bne @status
    inc snap_pos+2
@status:
    lda snap_eof
    beq @pending
    lda se_snapshot_pieces
    cmp snap_expected
    bne @corrupt
    lda se_snapshot_pieces+1
    cmp snap_expected+1
    bne @corrupt
    jsr se_snapshot_cancel
    lda #0
    clc
    rts
@pending:
    lda #1
    clc
    rts
@changed:
    lda #$52
    bne snap_abort
@corrupt:
    lda #$42
    bne snap_abort
@state:
    lda #$40
    sec
    rts
se_snapshot_cancel:
    lda se_snapshot_busy
    beq @done
    cmp #1
    beq :+
    lda #$41
    sec
    rts
:
    lda snap_epoch
    cmp se_doc_epoch
    bne @forget
    lda snap_epoch+1
    cmp se_doc_epoch+1
    bne @forget
    jsr se_doc_read_release
@forget:
    lda #0
    sta se_snapshot_busy
@done:
    lda #0
    clc
    rts
snap_abort:
    sta snap_error
    jsr se_snapshot_cancel
    lda snap_error
    sec
    rts
