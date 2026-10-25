; Included by C8 NAVIGATE. Synchronous arithmetic only; no leases, source reads,
; mutation services or overlay nesting. The resident dispatcher performs every
; reload/flush/retry after C8 returns. se_e_key/se_hot_byte stay untouched.
; N_EDGE request: se_e_command,validated hot frame -> target/after_load;
; Cclear/A0 redraw(noop),A1 reload,A2 flush pending then retry once.
editor_edge:
    lda se_e_command
    cmp #E_LEFT
    bne @right
    lda se_hot_caret
    ora se_hot_caret+1
    ora se_hot_caret+2
    jeq editor_edge_noop
    COPY24 se_hot_caret,se_e_target
    sec
    lda se_e_target
    sbc #1
    sta se_e_target
    lda se_e_target+1
    sbc #0
    sta se_e_target+1
    lda se_e_target+2
    sbc #0
    sta se_e_target+2
    jmp editor_edge_reload
@right:
    COPY24 se_hot_caret,se_e_target
    lda se_e_command
    cmp #E_RIGHT
    bne @edit
    CMP24 se_hot_caret,se_doc_length
    jeq editor_edge_noop
    inc se_e_target
    jne editor_edge_reload
    inc se_e_target+1
    jne editor_edge_reload
    inc se_e_target+2
    jmp editor_edge_reload
@edit:
    cmp #E_BACK
    bne @forward
    lda se_hot_caret
    ora se_hot_caret+1
    ora se_hot_caret+2
    jeq editor_edge_noop
    lda #W_BACK
    bne @retry
@forward:
    cmp #E_DELETE
    bne editor_edge_state
    ; Visible caret may equal committed EOF after pending edits while immutable
    ; source still follows this window. Only old cached end establishes EOF.
    lda se_hot_old_length
    sta se_v_temp
    lda se_hot_old_length+1
    sta se_v_temp+1
    lda #0
    sta se_v_temp+2
    ADD24 se_hot_base,se_v_temp,se_v_temp
    CMP24 se_v_temp,se_doc_length
    jeq editor_edge_noop
    lda #W_DELETE
@retry:
    sta se_e_after_load
    lda se_hot_pending
    bne editor_edge_flush
editor_edge_reload:
    lda #N_EDGE_RELOAD
    clc
    rts
editor_edge_noop:
    lda #N_EDGE_REDRAW
    clc
    rts
editor_edge_flush:
    lda #N_EDGE_FLUSH
    clc
    rts
editor_edge_state:
    lda #$70
    sec
    rts
