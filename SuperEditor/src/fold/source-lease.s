.setcpu "6502"
.include "fold/source.inc"
.segment "FOLD_SOURCE_CLEANUP"
; Separate operation: eventual editor placement must remain callable after
; failed overlay admission. No newly current graph/epoch's lease is decremented.
se_fs_end:
    lda se_fs_owned
    jeq @forget
    lda se_reu_epoch
    cmp se_fs_identity
    jne @forget
    cmp se_doc_epoch
    jne @forget
    lda se_reu_epoch+1
    cmp se_fs_identity+1
    jne @forget
    cmp se_doc_epoch+1
    jne @forget
    ldx #4
@tokens:
    lda se_doc_meta,x
    cmp se_fs_identity+6,x
    jne @forget
    lda se_doc_original,x
    cmp se_fs_identity+11,x
    jne @forget
    lda se_doc_append,x
    cmp se_fs_identity+16,x
    jne @forget
    dex
    jpl @tokens
    lda se_doc_read_locks
    jeq @forget
    jsr se_doc_read_release
@forget:
    lda #0
    sta se_fs_owned
    sta se_fs_active
    clc
    rts
