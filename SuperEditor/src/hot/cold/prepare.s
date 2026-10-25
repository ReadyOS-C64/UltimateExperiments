prepare:
    lda se_hot_pending
    jeq okay
    ; Minimal conservative delta excludes every guaranteed unchanged edge.
    lda se_hot_prefix
    sta se_hot_tmp
    lda se_hot_prefix+1
    sta se_hot_tmp+1
    lda #0
    sta se_hot_tmp+2
    ADD24 se_hot_base,se_hot_tmp,se_doc_edit_position
    sec
    lda se_hot_old_length
    sbc se_hot_prefix
    sta se_doc_edit_delete
    lda se_hot_old_length+1
    sbc se_hot_prefix+1
    sta se_doc_edit_delete+1
    sec
    lda se_doc_edit_delete
    sbc se_hot_suffix
    sta se_doc_edit_delete
    lda se_doc_edit_delete+1
    sbc se_hot_suffix+1
    sta se_doc_edit_delete+1
    sec
    lda se_hot_length
    sbc se_hot_prefix
    sta se_hot_feed_left
    lda se_hot_length+1
    sbc se_hot_prefix+1
    sta se_hot_feed_left+1
    sec
    lda se_hot_feed_left
    sbc se_hot_suffix
    sta se_hot_feed_left
    sta se_doc_edit_insert
    lda se_hot_feed_left+1
    sbc se_hot_suffix+1
    sta se_hot_feed_left+1
    sta se_doc_edit_insert+1
    lda #0
    sta se_doc_edit_insert+2
    sta se_doc_edit_delete+2
    lda se_hot_prefix
    sta se_hot_feed
    lda se_hot_prefix+1
    sta se_hot_feed+1
    COPY24 se_hot_before,se_h_before_caret
    COPY24 se_hot_caret,se_h_after_caret
    lda se_hot_group
    sta se_h_group
    lda #2
    sta se_hot_phase
.ifdef EDITOR_BINDINGS
    jsr bc_flush_prepare
.endif
    jmp pending
packet:
    lda se_hot_feed_left+1
    bne @cap
    lda se_hot_feed_left
    cmp #129
    bcc @count
@cap:
    lda #128
@count:
    sta se_hot_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    sta se_hot_packet
    lda #$80
    sta se_doc_c64+1
    sta se_hot_packet+1
@byte:
    lda se_hot_feed
    sta se_hot_target
    lda se_hot_feed+1
    sta se_hot_target+1
    jsr address
    ldy #0
    lda (se_hot_ptr),y
    sta (se_hot_packet),y
    inc se_hot_packet
    inc se_hot_feed
    bne :+
    inc se_hot_feed+1
:
    lda se_hot_feed_left
    bne :+
    dec se_hot_feed_left+1
:
    dec se_hot_feed_left
    dec se_hot_count
    bne @byte
    jmp okay
