.setcpu "6502"
.include "diagnostics/internal.inc"
.export se_diag_context_changed
.segment "CODE"
se_diag_context:
    jsr se_doc_validate
    jcs done
    jsr se_diag_pointer
    D_CONTEXT D_CHECK
    lda se_reu_epoch
    cmp se_diag_epoch
    jne se_diag_context_changed
    lda se_reu_epoch+1
    cmp se_diag_epoch+1
    jne se_diag_context_changed
    lda se_doc_busy
    ora se_h_phase
    ora se_b_phase
    ora se_clip_busy
    ora se_snapshot_busy
    jne se_diag_context_changed
    clc
done:
    rts
se_diag_context_changed:
    lda #D_CHANGED
    sec
    rts

; Validate every bound before gap reads. Does not require a loaded hot window.
; Output merged length and hot end; no IO,source or REU writes.
se_diag_shape:
    COPY24 se_doc_length,se_diag_length
    lda se_hot_ready
    bne hot
    lda se_hot_pending
    jne bad
    lda #0
    clc
    rts
hot:
    cmp #1
    jne bad
    ldx #4
tokens:
    lda se_hot_original,x
    cmp se_doc_original,x
    jne se_diag_context_changed
    lda se_hot_append,x
    cmp se_doc_append,x
    jne se_diag_context_changed
    dex
    bpl tokens
    lda se_hot_generation
    cmp se_doc_generation
    jne se_diag_context_changed
    lda se_hot_generation+1
    cmp se_doc_generation+1
    jne se_diag_context_changed
    ; 0<=left<=right<=2048 and length=left+2048-right.
    lda se_hot_right+1
    cmp #8
    jcc right_ok
    jne bad
    lda se_hot_right
    jne bad
right_ok:
    lda se_hot_left+1
    cmp se_hot_right+1
    jcc ordered
    jne bad
    lda se_hot_left
    cmp se_hot_right
    jcc ordered
    jne bad
ordered:
    sec
    lda #0
    sbc se_hot_right
    sta se_diag_temp
    lda #8
    sbc se_hot_right+1
    sta se_diag_temp+1
    clc
    lda se_diag_temp
    adc se_hot_left
    sta se_diag_temp
    lda se_diag_temp+1
    adc se_hot_left+1
    sta se_diag_temp+1
    cmp se_hot_length+1
    jne bad
    lda se_diag_temp
    cmp se_hot_length
    jne bad
    lda se_hot_old_length
    sta se_diag_temp
    lda se_hot_old_length+1
    sta se_diag_temp+1
    cmp #8
    jcc old_ok
    jne bad
    lda se_diag_temp
    jne bad
old_ok:
    lda #0
    sta se_diag_temp+2
    ADD24 se_hot_base,se_diag_temp,se_diag_hot_end
    jcs bad
    CMP24 se_diag_hot_end,se_doc_length
    jcc within
    jne bad
within:
    SUB24 se_doc_length,se_diag_temp,se_diag_length
    lda se_hot_length
    sta se_diag_temp
    lda se_hot_length+1
    sta se_diag_temp+1
    ADD24 se_diag_length,se_diag_temp,se_diag_length
    jcs bad
    ADD24 se_hot_base,se_diag_temp,se_diag_hot_end
    jcs bad
    lda #0
    clc
    rts
bad:
    lda #D_SHAPE
    sec
    rts
