.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.include "object/api.inc"
.include "document/frames/range.inc"
.ifndef ENGINE_STATE_ONLY
.export se_range_r32_begin,se_range_r32_step
.segment "CODE"
; Packed source references for a selected half-open range in a canonical
; checked graph. No text copying, source resize, allocation or publication.
; se_snapshot_busy:0 idle,1 full capture,2 selected-range capture. Both share
; the private walker; ordinary byte reads do not, and may evict its leaf.
se_range_r32_begin:
    jsr se_doc_validate
    jcs @return
    lda se_snapshot_busy
    jne @busy
    ADD24 se_range_position,se_range_length,range_end
    jcs @range
    CMP24 range_end,se_doc_length
    bcc @object
    jne @range
@object:
    DOC_TOKEN se_range_token
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #6
    jne @corrupt
    lda se_range_offset+2
    cmp object_size_hi,x
    bcc @valid
    jne @range
    lda se_range_offset+1
    cmp object_size_mid,x
    bcc @valid
    jne @range
    lda se_range_offset
    cmp object_size_lo,x
    bcc @valid
    jne @range
@valid:
    lda se_range_length
    ora se_range_length+1
    ora se_range_length+2
    beq @empty
    jsr se_doc_read_acquire
    bcs @return
    ldy #4
@token:
    lda se_range_token,y
    sta range_token,y
    dey
    bpl @token
    COPY24 se_range_offset,range_out
    COPY24 se_range_position,range_start
    COPY24 se_range_length,range_goal
    lda se_doc_epoch
    sta range_epoch
    lda se_doc_epoch+1
    sta range_epoch+1
    lda se_doc_generation
    sta range_generation
    lda se_doc_generation+1
    sta range_generation+1
    jsr range_clear
    jsr se_doc_walk_reset
    lda #2
    sta se_snapshot_busy
    lda #1
    clc
    rts
@empty:
    jsr range_clear
    lda #0
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

se_range_r32_step:
    lda se_snapshot_busy
    cmp #2
    jne range_state
    jsr se_doc_validate
    jcs range_abort
    lda se_doc_generation
    cmp range_generation
    jne range_changed
    lda se_doc_generation+1
    cmp range_generation+1
    jne range_changed
    lda #0
    sta range_packet
    sta range_done
    lda #8
    sta range_budget
@next:
    ; Prefix roots are immutable and already checked by their producer. Skip
    ; whole roots, but count each skip as one scheduler unit.
    jsr range_skip
    jcs range_abort
    cmp #1
    jeq @advance_budget
    jsr se_doc_walk_next
    bcc @record
    cmp #0
    jeq range_corrupt
    jmp range_abort
@record:
    ADD24 range_pos,se_doc_walk_piece+6,range_piece_end
    jcs range_corrupt
    CMP24 range_piece_end,range_start
    jcc @advance
    jeq @advance
    lda #0
    sta range_delta
    sta range_delta+1
    sta range_delta+2
    CMP24 range_pos,range_start
    bcs @length
    SUB24 range_start,range_pos,range_delta
@length:
    COPY24 se_doc_walk_piece+6,range_fragment
    CMP24 range_piece_end,range_end
    bcc @split
    SUB24 range_end,range_pos,range_fragment
    lda #1
    sta range_done
@split:
    SUB24 range_fragment,range_delta,range_fragment
    ADD24 se_doc_walk_piece+3,range_delta,se_doc_walk_piece+3
    jcs range_corrupt
    COPY24 range_fragment,se_doc_walk_piece+6
    ADD24 range_written,range_fragment,range_written
    bcs range_corrupt
    ldy range_packet
    ldx #0
@pack:
    lda se_doc_walk_piece,x
    sta $8000,y
    iny
    inx
    cpx #9
    bcc @pack
    sty range_packet
    inc se_range_pieces
    bne @advance
    inc se_range_pieces+1
@advance:
    COPY24 range_piece_end,range_pos
    lda range_done
    bne @flush
@advance_budget:
    dec range_budget
    jne @next
@flush:
    jsr range_flush
    bcs range_abort
    lda range_done
    beq @pending
    CMP24 range_written,range_goal
    bne range_corrupt
    jsr se_range_cancel
    lda #0
    clc
    rts
@pending:
    lda #1
    clc
    rts
range_changed:
    lda #$52
    bne range_abort
range_corrupt:
    lda #$42
range_abort:
    sta range_error
    jsr se_range_cancel
    lda range_error
    sec
    rts
range_state:
    lda #$40
    sec
    rts

range_skip:
    lda walk_record
    jne @walk
    lda walk_root
    cmp se_doc_root_count
    jcs @walk
    asl
    asl
    asl
    tay
    lda se_doc_roots,y
    cmp #64
    jcs @corrupt
    lda se_doc_roots+1,y
    jeq @corrupt
    cmp #65
    jcs @corrupt
    .repeat 3,N
        lda se_doc_roots+2+N,y
        sta range_root_end+N
    .endrepeat
    lda range_root_end
    ora range_root_end+1
    ora range_root_end+2
    beq @corrupt
    ADD24 range_pos,range_root_end,range_root_end
    bcs @corrupt
    CMP24 range_root_end,range_start
    bcc @skip
    bne @walk
@skip:
    COPY24 range_root_end,range_pos
    COPY24 range_root_end,walk_total
    inc walk_root
    lda #1
    clc
    rts
@walk:
    lda #0
    clc
    rts
@corrupt:
    lda #$42
    sec
    rts

range_flush:
    lda range_packet
    jeq @ok
    DOC_TOKEN range_token
    jsr se_object_validate
    jcs @return
    clc
    lda range_out
    adc range_packet
    sta range_store_end
    lda range_out+1
    adc #0
    sta range_store_end+1
    lda range_out+2
    adc #0
    sta range_store_end+2
    bcs @range
    cmp object_size_hi,x
    bcc @copy
    bne @range
    lda range_store_end+1
    cmp object_size_mid,x
    bcc @copy
    bne @range
    lda range_store_end
    cmp object_size_lo,x
    bcc @copy
    bne @range
@copy:
    COPY24 range_out,se_object_offset
    lda range_packet
    sta se_object_length
    lda #0
    sta se_object_length+1
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda #0
    jsr se_object_copy
    bcs @return
    COPY24 range_store_end,range_out
    clc
    lda se_range_bytes
    adc range_packet
    sta se_range_bytes
    lda se_range_bytes+1
    adc #0
    sta se_range_bytes+1
@ok:
    clc
@return:
    rts
@range:
    lda #$32
    sec
    rts

.endif ; full default or relocated engine code
.ifndef ENGINE_CODE
.segment "CODE"
se_range_cancel:
    lda se_snapshot_busy
    beq @done
    cmp #2
    beq @owned
    lda #$41
    sec
    rts
@owned:
    lda range_epoch
    cmp se_doc_epoch
    bne @forget
    lda range_epoch+1
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
.endif ; resident cancellation survives engine admission failure
.ifndef ENGINE_STATE_ONLY
.segment "CODE"
range_clear:
    lda #0
    sta se_range_pieces
    sta se_range_pieces+1
    sta se_range_bytes
    sta se_range_bytes+1
    sta range_written
    sta range_written+1
    sta range_written+2
    sta range_pos
    sta range_pos+1
    sta range_pos+2
    rts

.endif
