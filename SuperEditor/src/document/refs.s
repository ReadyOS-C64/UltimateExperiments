.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.include "document/frames/refs.inc"
.ifndef ENGINE_STATE_ONLY
.segment "CODE"
; Same position/delete/insert-byte-length request as byte splice, plus packed
; type6 source references. Appended data is neither allocated nor resized.
se_doc_splice_refs_begin:
    jsr doc_splice_admit
    jcs refs_return
    lda #0
    sta tx_local_mode
    jmp refs_begin_checked
se_doc_splice_local_refs_begin:
    jsr doc_splice_admit
    jcs refs_return
    lda #1
    sta tx_local_mode
refs_begin_checked:
    lda se_doc_refs_pieces+1
    cmp #8
    bcc @count
    jne @full
    lda se_doc_refs_pieces
    jne @full
@count:
    lda se_doc_refs_pieces
    ora se_doc_refs_pieces+1
    bne @object
    lda se_doc_edit_insert
    ora se_doc_edit_insert+1
    ora se_doc_edit_insert+2
    jne @corrupt
@object:
    DOC_TOKEN se_doc_refs_token
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #6
    jne @corrupt
    lda se_doc_refs_pieces
    sta refs_bytes
    lda se_doc_refs_pieces+1
    sta refs_bytes+1
    .repeat 3
        asl refs_bytes
        rol refs_bytes+1
    .endrepeat
    clc
    lda refs_bytes
    adc se_doc_refs_pieces
    sta refs_bytes
    lda refs_bytes+1
    adc se_doc_refs_pieces+1
    sta refs_bytes+1
    clc
    lda se_doc_refs_offset
    adc refs_bytes
    sta refs_end
    lda se_doc_refs_offset+1
    adc refs_bytes+1
    sta refs_end+1
    lda se_doc_refs_offset+2
    adc #0
    sta refs_end+2
    jcs @range
    cmp object_size_hi,x
    bcc @prepare
    jne @range
    lda refs_end+1
    cmp object_size_mid,x
    bcc @prepare
    jne @range
    lda refs_end
    cmp object_size_lo,x
    bcc @prepare
    jne @range
@prepare:
    ldy #4
@token:
    lda se_doc_refs_token,y
    sta refs_token,y
    dey
    bpl @token
    COPY24 se_doc_refs_offset,refs_origin
    COPY24 se_doc_refs_offset,refs_pos
    lda se_doc_refs_pieces
    sta refs_left
    sta refs_count
    lda se_doc_refs_pieces+1
    sta refs_left+1
    sta refs_count+1
    lda #0
    sta doc_refs_active
    sta refs_sum
    sta refs_sum+1
    sta refs_sum+2
    lda #1
    sta tx_ref_mode
    jmp doc_splice_begin_checked
@return:
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

refs_return:
    rts
; Rewind the private request after local-root capacity triggers full repack.
doc_refs_rewind:
    COPY24 refs_origin,refs_pos
    lda refs_count
    sta refs_left
    lda refs_count+1
    sta refs_left+1
    lda #0
    sta doc_refs_active
    sta refs_sum
    sta refs_sum+1
    sta refs_sum+2
    rts

; Return1 to yield before processing reference packets, or0 for empty insert.
doc_refs_start:
    lda refs_left
    ora refs_left+1
    bne @start
    lda #1
    sta tx_inserted
    lda #0
    clc
    rts
@start:
    ldx #15
@old:
    lda se_doc_walk_piece,x
    sta refs_old_piece,x
    dex
    bpl @old
    lda #1
    sta doc_refs_active
    clc
    rts
; At most8 inserted refs per call. The old boundary piece survives in resident
; scratch while both rendering and this decoder may reuse other work buffers.
doc_refs_step:
    lda #8
    ldx refs_left+1
    bne @packet
    cmp refs_left
    bcc @packet
    lda refs_left
@packet:
    sta refs_packet_pieces
    sta refs_budget
    asl
    asl
    asl
    clc
    adc refs_packet_pieces
    sta refs_bytes
    lda #0
    sta refs_bytes+1
    DOC_TOKEN refs_token
    COPY24 refs_pos,se_object_offset
    lda refs_bytes
    sta se_object_length
    lda #0
    sta se_object_length+1
    sta se_object_c64
    sta refs_packet_offset
    lda #$80
    sta se_object_c64+1
    lda #1
    jsr se_object_copy
    jcs @return
@piece:
    ldx #15
    lda #0
@clear:
    sta se_doc_walk_piece,x
    dex
    bpl @clear
    ldy refs_packet_offset
    ldx #0
@unpack:
    lda $8000,y
    sta se_doc_walk_piece,x
    iny
    inx
    cpx #9
    bcc @unpack
    sty refs_packet_offset
    lda #$FF
    sta se_doc_walk_piece+9
    sta se_doc_walk_piece+10
    sta se_doc_walk_piece+11
    jsr se_doc_piece_validate
    jcs @return
    ADD24 refs_sum,se_doc_walk_piece+6,refs_sum
    jcs @corrupt
    CMP24 refs_sum,tx_insert
    bcc @emit
    jne @corrupt
@emit:
    ldx #15
@copy:
    lda se_doc_walk_piece,x
    sta se_doc_emit,x
    dex
    bpl @copy
    jsr doc_emit_piece
    jcs @return
    dec refs_budget
    jne @piece
    clc
    lda refs_pos
    adc refs_bytes
    sta refs_pos
    lda refs_pos+1
    adc #0
    sta refs_pos+1
    bcc :+
    inc refs_pos+2
:
    sec
    lda refs_left
    sbc refs_packet_pieces
    sta refs_left
    lda refs_left+1
    sbc #0
    sta refs_left+1
    lda refs_left
    ora refs_left+1
    beq @done
    lda #1
    clc
    rts
@done:
    CMP24 refs_sum,tx_insert
    jne @corrupt
    ldx #15
@restore:
    lda refs_old_piece,x
    sta se_doc_walk_piece,x
    dex
    bpl @restore
    lda #0
    sta doc_refs_active
    lda #1
    sta tx_inserted
    lda #0
    clc
@return:
    rts
@corrupt:
    lda #$42
    sec
    rts

.endif
