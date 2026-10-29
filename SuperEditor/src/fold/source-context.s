.setcpu "6502"
.include "fold/source.inc"
.macro FS_CHECK_NEAR source,offset,n,fail
    ldx #n-1
:
    lda source,x
    cmp se_fs_identity+offset,x
    bne fail
    dex
    bpl :-
.endmacro
.segment "FOLD_SOURCE_CODE"
.assert se_doc_original=se_doc_meta+5,lderror,"document identity fields are no longer contiguous"
.assert se_doc_append=se_doc_original+5,lderror,"document identity fields are no longer contiguous"
.assert se_doc_root_count=se_doc_length+3,lderror,"document length identity fields are no longer contiguous"
.assert se_hot_append=se_hot_original+5,lderror,"hot object identity fields are no longer contiguous"
.assert se_hot_length=se_hot_old_length+2,lderror,"hot length fields are no longer contiguous"
.assert se_hot_left=se_hot_old_length+4,lderror,"hot length fields are no longer contiguous"
.assert se_hot_right=se_hot_old_length+6,lderror,"hot length fields are no longer contiguous"
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
    ; Preserve the 59-byte identity ABI while joining physically contiguous
    ; fields.  This removes seven copies of the same indexed loop.
    FS_CAPTURE se_reu_epoch,0,2
    FS_CAPTURE se_doc_epoch,2,2
    FS_CAPTURE se_doc_generation,4,2
    FS_CAPTURE se_doc_meta,6,15
    FS_CAPTURE se_doc_length,21,4
    FS_CAPTURE se_r_revision,25,4
    FS_CAPTURE se_hot_ready,29,1
    FS_CAPTURE se_hot_pending,30,1
    FS_CAPTURE se_hot_phase,31,1
    FS_CAPTURE se_hot_owned,32,1
    FS_CAPTURE se_hot_fault,33,1
    FS_CAPTURE se_hot_epoch,34,2
    FS_CAPTURE se_hot_generation,36,2
    FS_CAPTURE se_hot_original,38,10
    FS_CAPTURE se_hot_base,48,3
    FS_CAPTURE se_hot_old_length,51,8
    ldx #3
@revision:
    lda se_r_revision,x
    sta se_fs_revision,x
    dex
    jpl @revision
    clc
fs_return:
    rts
se_fs_guard:
    lda se_fs_active
    and se_fs_owned
    jeq fs_changed
    jsr se_doc_validate
    jcs fs_return
    FS_CHECK_NEAR se_reu_epoch,0,2,@identity_changed_a
    FS_CHECK_NEAR se_doc_epoch,2,2,@identity_changed_a
    FS_CHECK_NEAR se_doc_generation,4,2,@identity_changed_a
    FS_CHECK_NEAR se_doc_meta,6,15,@identity_changed_a
    FS_CHECK_NEAR se_doc_length,21,4,@identity_changed_a
    FS_CHECK_NEAR se_r_revision,25,4,@identity_changed_a
    FS_CHECK_NEAR se_hot_ready,29,1,@identity_changed_a
    FS_CHECK_NEAR se_hot_pending,30,1,@identity_changed_a
    jmp @identity_checked_a
@identity_changed_a:
    jmp fs_changed
@identity_checked_a:
    FS_CHECK_NEAR se_hot_phase,31,1,@identity_changed_b
    FS_CHECK_NEAR se_hot_owned,32,1,@identity_changed_b
    FS_CHECK_NEAR se_hot_fault,33,1,@identity_changed_b
    FS_CHECK_NEAR se_hot_epoch,34,2,@identity_changed_b
    FS_CHECK_NEAR se_hot_generation,36,2,@identity_changed_b
    FS_CHECK_NEAR se_hot_original,38,10,@identity_changed_b
    FS_CHECK_NEAR se_hot_base,48,3,@identity_changed_b
    FS_CHECK_NEAR se_hot_old_length,51,8,@identity_changed_b
    jmp @identity_checked_b
@identity_changed_b:
    jmp fs_changed
@identity_checked_b:
    lda se_doc_busy
    ora se_hot_phase
    ora se_hot_owned
    ora se_h_phase
    ora se_b_phase
    ora se_clip_busy
    ora se_snapshot_busy
    jne fs_changed
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
    jcs @return
    DOC_TOKEN se_doc_original
    jsr se_object_validate
    jcs @return
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
    jne fs_changed
    lda se_hot_append,x
    cmp se_doc_append,x
    jne fs_changed
    dex
    jpl @tokens
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
    jcc @old
    jne fs_bad_shape
    lda se_fs_temp
    jne fs_bad_shape
@old:
    lda #0
    sta se_fs_temp+2
    ADD24 se_hot_base,se_fs_temp,se_fs_hot_end
    jcs fs_bad_shape
    CMP24 se_fs_hot_end,se_doc_length
    jcc @merged
    jne fs_bad_shape
@merged:
    SUB24 se_doc_length,se_fs_temp,se_fs_length
    lda se_hot_length
    sta se_fs_temp
    lda se_hot_length+1
    sta se_fs_temp+1
    ADD24 se_fs_length,se_fs_temp,se_fs_length
    jcs fs_bad_shape
    ADD24 se_hot_base,se_fs_temp,se_fs_hot_end
    jcs fs_bad_shape
    clc
    rts
fs_bad_shape:
    lda #FS_BAD
    sec
    rts
