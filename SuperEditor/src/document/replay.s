.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.segment "DOCSTATE"
se_replay_token: .res 5
se_replay_offset: .res 3
se_replay_pieces: .res 2
se_replay_length: .res 3
replay_token: .res 5
replay_pos: .res 3
replay_left: .res 2
replay_goal: .res 3
replay_end: .res 3
replay_bytes: .res 2
replay_generation: .res 2
replay_packet_pieces: .res 1
replay_packet_offset: .res 1
replay_budget: .res 1
replay_error: .res 1
.segment "CODE"
; Rebuild a whole document from packed immutable references, no append writes
; or append-size shrink. Permits undo/redo even at a full append quota.
se_replay_begin:
    jsr se_doc_validate
    jcs @return
    lda se_doc_busy
    ora se_doc_read_locks
    jne @busy
    lda se_replay_pieces+1
    cmp #8
    bcc @count
    jne @full
    lda se_replay_pieces
    jne @full
@count:
    lda se_replay_pieces
    ora se_replay_pieces+1
    bne @nonempty
    lda se_replay_length
    ora se_replay_length+1
    ora se_replay_length+2
    jne @corrupt
@nonempty:
    DOC_TOKEN se_doc_original
    jsr se_object_validate
    jcs @return
    lda se_replay_length+2
    cmp object_banks,x
    bcc @capacity
    jne @range
    lda se_replay_length
    ora se_replay_length+1
    jne @range
@capacity:
    DOC_TOKEN se_replay_token
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #6
    jne @corrupt
    lda se_replay_pieces
    sta replay_bytes
    lda se_replay_pieces+1
    sta replay_bytes+1
    .repeat 3
        asl replay_bytes
        rol replay_bytes+1
    .endrepeat
    clc
    lda replay_bytes
    adc se_replay_pieces
    sta replay_bytes
    lda replay_bytes+1
    adc se_replay_pieces+1
    sta replay_bytes+1
    clc
    lda se_replay_offset
    adc replay_bytes
    sta replay_end
    lda se_replay_offset+1
    adc replay_bytes+1
    sta replay_end+1
    lda se_replay_offset+2
    adc #0
    sta replay_end+2
    jcs @range
    cmp object_size_hi,x
    bcc @prepare
    jne @range
    lda replay_end+1
    cmp object_size_mid,x
    bcc @prepare
    jne @range
    lda replay_end
    cmp object_size_lo,x
    bcc @prepare
    jne @range
@prepare:
    jsr doc_emit_reset
    jcs @return
    ldy #4
@token:
    lda se_replay_token,y
    sta replay_token,y
    dey
    bpl @token
    COPY24 se_replay_offset,replay_pos
    COPY24 se_replay_length,replay_goal
    lda se_replay_pieces
    sta replay_left
    lda se_replay_pieces+1
    sta replay_left+1
    lda se_doc_generation
    sta replay_generation
    lda se_doc_generation+1
    sta replay_generation+1
    lda #3
    sta se_doc_busy
    lda #1
    clc
@return:
    rts
@busy:
    lda #$41
    sec
    rts
@range:
    lda #$32
    sec
    rts
@full:
    lda #$43
    sec
    rts
@corrupt:
    lda #$42
    sec
    rts
se_replay_step:
    lda se_doc_busy
    cmp #3
    jne @state
    jsr se_doc_validate
    jcs replay_abort
    lda se_doc_generation
    cmp replay_generation
    jne @state_abort
    lda se_doc_generation+1
    cmp replay_generation+1
    jne @state_abort
    lda replay_left
    ora replay_left+1
    jeq @finish
    lda #8
    ldx replay_left+1
    bne @packet
    cmp replay_left
    bcc @packet
    lda replay_left
@packet:
    sta replay_packet_pieces
    sta replay_budget
    asl
    asl
    asl
    clc
    adc replay_packet_pieces
    sta replay_bytes
    lda #0
    sta replay_bytes+1
    DOC_TOKEN replay_token
    COPY24 replay_pos,se_object_offset
    lda replay_bytes
    sta se_object_length
    lda #0
    sta se_object_length+1
    sta se_object_c64
    sta replay_packet_offset
    lda #$80
    sta se_object_c64+1
    lda #1
    jsr se_object_copy
    jcs replay_abort
@piece:
    ldx #15
    lda #0
@clear:
    sta se_doc_walk_piece,x
    dex
    bpl @clear
    ldy replay_packet_offset
    ldx #0
@unpack:
    lda $8000,y
    sta se_doc_walk_piece,x
    iny
    inx
    cpx #9
    bcc @unpack
    sty replay_packet_offset
    lda #$FF
    sta se_doc_walk_piece+9
    sta se_doc_walk_piece+10
    sta se_doc_walk_piece+11
    jsr se_doc_piece_validate
    jcs replay_abort
    ldx #15
@emit:
    lda se_doc_walk_piece,x
    sta se_doc_emit,x
    dex
    bpl @emit
    jsr doc_emit_piece
    jcs replay_abort
    dec replay_budget
    bne @piece
    clc
    lda replay_pos
    adc replay_bytes
    sta replay_pos
    lda replay_pos+1
    adc #0
    sta replay_pos+1
    bcc :+
    inc replay_pos+2
:
    sec
    lda replay_left
    sbc replay_packet_pieces
    sta replay_left
    lda replay_left+1
    sbc #0
    sta replay_left+1
    lda replay_left
    ora replay_left+1
    beq @finish
    lda #1
    clc
    rts
@finish:
    jsr doc_emit_finish
    jcs replay_abort
    CMP24 emit_total,replay_goal
    jne @corrupt
    ldx #0
@publish:
    lda se_doc_next_roots,x
    sta se_doc_roots,x
    inx
    bne @publish
    COPY24 replay_goal,se_doc_length
    lda emit_root_count
    sta se_doc_root_count
    inc se_doc_generation
    bne :+
    inc se_doc_generation+1
:
    jsr se_doc_invalidate
    lda #0
    sta se_doc_busy
    clc
    rts
@corrupt:
    lda #$42
    jmp replay_abort
@state_abort:
    lda #$40
    jmp replay_abort
@state:
    lda #$40
    sec
    rts
se_replay_cancel:
    lda se_doc_busy
    beq @idle
    cmp #3
    bne @other
    jsr se_doc_splice_cancel
@idle:
    lda #0
    clc
    rts
@other:
    lda #$41
    sec
    rts
replay_abort:
    sta replay_error
    jsr se_replay_cancel
    lda replay_error
    sec
    rts
