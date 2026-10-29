.setcpu "6502"
.include "diagnostics/internal.inc"
.segment "CODE"
se_diag_begin:
    lda se_diag_active
    ora se_diag_owned
    jne busy
    jsr se_doc_validate
    jcs done
    lda se_doc_busy
    ora se_hot_phase
    ora se_h_phase
    ora se_b_phase
    ora se_clip_busy
    ora se_snapshot_busy
    jne busy
    ; Checked exclusive COW scratch only:8800..8B80 inclusive starts.
    lda se_diag_buffer+1
    cmp #$88
    jcc buffer
    cmp #$8C
    jcs buffer
    cmp #$8B
    bne pointer_ok
    lda se_diag_buffer
    cmp #$81
    jcs buffer
pointer_ok:
    jsr se_diag_shape
    jcs done
    CMP24 se_diag_cursor,se_diag_length
    jcc cursor_ok
    jne buffer
cursor_ok:
    jsr se_doc_read_acquire
    jcs done
    lda #1
    sta se_diag_owned
    sta se_diag_active
    lda se_doc_epoch
    sta se_diag_epoch
    lda se_doc_epoch+1
    sta se_diag_epoch+1
    lda se_diag_buffer
    sta se_diag_output
    lda se_diag_buffer+1
    sta se_diag_output+1
    jsr se_diag_pointer
    lda #0
    ldy #DIAG_BYTES-1
clear:
    sta (text_ptr),y
    dey
    bpl clear
    sta se_diag_pos
    sta se_diag_pos+1
    sta se_diag_pos+2
    sta se_diag_error
    lda #$FF
    sta se_diag_crc
    sta se_diag_crc+1
    D_CONTEXT D_CAPTURE
    D_CAPTURE se_diag_length,DS_LENGTH,3
    D_CAPTURE se_diag_cursor,DS_CURSOR,3
    D_CAPTURE se_diag_crc,DS_CRC,2
    D_CAPTURE se_overlay_loads,DS_LOADS,2
    D_CAPTURE se_overlay_hits,DS_HITS,2
    D_CAPTURE se_overlay_calls,DS_CALLS,2
    D_CAPTURE se_reu_banks,DS_BANKS,2
    D_CAPTURE se_reu_retired,DS_RETIRED,1
    D_CAPTURE se_doc_read_locks,DS_READ_LOCKS,1
    lda se_h_dirty
    ldy #DS_HISTORY_DIRTY
    sta (text_ptr),y
    ora se_hot_pending
    beq clean
    lda #1
clean:
    ldy #DS_DIRTY
    sta (text_ptr),y
    ldy #0
    lda #'D'
    sta (text_ptr),y
    iny
    lda #'G'
    sta (text_ptr),y
    iny
    lda #'S'
    sta (text_ptr),y
    iny
    lda #'1'
    sta (text_ptr),y
    iny
    lda #1
    sta (text_ptr),y ;ABI
    iny
    lda #DIAG_BYTES
    sta (text_ptr),y
    iny
    lda #1
    sta (text_ptr),y ;scanning
    iny
    sta (text_ptr),y ;CCITT-FALSE
    ldy #DS_MAP
    lda #<se_reu_map
    sta (text_ptr),y
    iny
    lda #>se_reu_map
    sta (text_ptr),y
    iny
    lda #<se_reu_logical_owner
    sta (text_ptr),y
    iny
    lda #>se_reu_logical_owner
    sta (text_ptr),y
    iny
    lda #<se_reu_physical_owner
    sta (text_ptr),y
    iny
    lda #>se_reu_physical_owner
    sta (text_ptr),y
    ldx #0
owners:
    lda se_reu_logical_owner,x
    beq physical
    cmp #$FF
    beq physical
    ldy #DS_ALLOCATED
    jsr increment
physical:
    lda se_reu_physical_owner,x
    bne next
    ldy #DS_FREE
    jsr increment
next:
    inx
    bne owners
    lda #1
    clc
done:
    rts
increment:
    clc
    lda (text_ptr),y
    adc #1
    sta (text_ptr),y
    bcc :+
    iny
    lda (text_ptr),y
    adc #0
    sta (text_ptr),y
:
    rts
busy:
    lda #D_STATE
    sec
    rts
buffer:
    lda #D_BUFFER
    sec
    rts
