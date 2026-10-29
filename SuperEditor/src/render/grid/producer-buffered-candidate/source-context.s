; Private exact-condition branch shortening; ca65 range checks everybranch.
.setcpu "6502"
.include "fold/source.inc"
.segment "FOLD_SOURCE_CODE"
se_fs_begin:
    lda se_fs_active
    ora se_fs_owned
    jne fs_busy
    jsr se_doc_validate
    jcs fs_return
    jsr se_fs_tokens
    jcs fs_return
    lda se_doc_busy
    ora se_hot_phase
    ora se_hot_owned
    ora se_h_phase
    ora se_b_phase
    ora se_clip_busy
    ora se_snapshot_busy
    jne fs_busy
    jsr se_fs_shape
    jcs fs_return
    jsr se_doc_read_acquire
    jcs fs_return
    lda #1
    sta se_fs_active
    sta se_fs_owned
    lda #0
    sta se_fs_error
    FS_FIELDS FS_CAPTURE
    ldx #3
@revision:
    lda se_r_revision,x
    sta se_fs_revision,x
    dex
    bpl @revision
    clc
fs_return:
    rts
se_fs_guard:
    lda se_fs_active
    and se_fs_owned
    jeq fs_changed
    jsr se_doc_validate
    bcs fs_return
    FS_FIELDS FS_CHECK
    lda se_doc_busy
    ora se_hot_phase
    ora se_hot_owned
    ora se_h_phase
    ora se_b_phase
    ora se_clip_busy
    ora se_snapshot_busy
    bne fs_changed
    jsr se_fs_tokens
    jcs fs_return
    clc
    rts
fs_changed:
    lda #FS_CHANGED
    sec
    rts
fs_busy:
    lda #FS_BUSY
    sec
    rts
se_fs_tokens:
    DOC_TOKEN se_doc_meta
    jsr se_object_validate
    bcs @return
    DOC_TOKEN se_doc_original
    jsr se_object_validate
    bcs @return
    DOC_TOKEN se_doc_append
    jmp se_object_validate
@return:
    rts
; Check all gap geometry before any HOT_FIRST indexing. No IO or source writes.
se_fs_shape:
    COPY24 se_doc_length,se_fs_length
    lda #0
    sta se_fs_hot_end
    sta se_fs_hot_end+1
    sta se_fs_hot_end+2
    lda se_hot_pending
    cmp #2
    jcs fs_bad_shape
    lda se_hot_ready
    bne @hot
    lda se_hot_pending
    jne fs_bad_shape
    clc
    rts
@hot:
    cmp #1
    jne fs_bad_shape
    ldx #4
@tokens:
    lda se_hot_original,x
    cmp se_doc_original,x
    bne fs_changed
    lda se_hot_append,x
    cmp se_doc_append,x
    jne fs_changed
    dex
    bpl @tokens
    lda se_hot_epoch
    cmp se_doc_epoch
    jne fs_changed
    lda se_hot_epoch+1
    cmp se_doc_epoch+1
    jne fs_changed
    lda se_hot_generation
    cmp se_doc_generation
    jne fs_changed
    lda se_hot_generation+1
    cmp se_doc_generation+1
    jne fs_changed
    lda se_hot_right+1
    cmp #8
    bcc @ordered
    jne fs_bad_shape
    lda se_hot_right
    jne fs_bad_shape
@ordered:
    lda se_hot_left+1
    cmp se_hot_right+1
    bcc @length
    jne fs_bad_shape
    lda se_hot_left
    cmp se_hot_right
    bcc @length
    jne fs_bad_shape
@length:
    sec
    lda #0
    sbc se_hot_right
    sta se_fs_temp
    lda #8
    sbc se_hot_right+1
    sta se_fs_temp+1
    clc
    lda se_fs_temp
    adc se_hot_left
    sta se_fs_temp
    lda se_fs_temp+1
    adc se_hot_left+1
    cmp se_hot_length+1
    jne fs_bad_shape
    lda se_fs_temp
    cmp se_hot_length
    jne fs_bad_shape
    lda se_hot_old_length
    sta se_fs_temp
    lda se_hot_old_length+1
    sta se_fs_temp+1
    cmp #8
    bcc @old
    jne fs_bad_shape
    lda se_fs_temp
    jne fs_bad_shape
@old:
    lda #0
    sta se_fs_temp+2
    ADD24 se_hot_base,se_fs_temp,se_fs_hot_end
    jcs fs_bad_shape
    CMP24 se_fs_hot_end,se_doc_length
    bcc @merged
    bne fs_bad_shape
@merged:
    SUB24 se_doc_length,se_fs_temp,se_fs_length
    lda se_hot_length
    sta se_fs_temp
    lda se_hot_length+1
    sta se_fs_temp+1
    ADD24 se_fs_length,se_fs_temp,se_fs_length
    bcs fs_bad_shape
    ADD24 se_hot_base,se_fs_temp,se_fs_hot_end
    bcs fs_bad_shape
    clc
    rts
fs_bad_shape:
    lda #FS_BAD
    sec
    rts
