; Always-resident lease cleanup, also callable after overlay admission failure.
; Same END contract as fold/source-lease.s; no current graph's foreign lease
; is released after a provider epoch or complete token-graph replacement.
.setcpu "6502"
.export se_fs_end
.import se_fs_owned,se_fs_active,se_fs_identity
.import se_reu_epoch,se_doc_epoch,se_doc_meta,se_doc_original,se_doc_append
.import se_doc_read_locks,se_doc_read_release
.assert se_doc_original = se_doc_meta+5, lderror, "document token graph must be contiguous"
.assert se_doc_append = se_doc_meta+10, lderror, "document token graph must be contiguous"
.segment "CORE"
se_fs_end:
    lda se_fs_owned
    beq @forget
    ldx #1
@epochs:
    lda se_reu_epoch,x
    cmp se_fs_identity,x
    bne @forget
    cmp se_doc_epoch,x
    bne @forget
    dex
    bpl @epochs
    ldx #14
@tokens:
    lda se_doc_meta,x
    cmp se_fs_identity+6,x
    bne @forget
    dex
    bpl @tokens
    lda se_doc_read_locks
    beq @forget
    jsr se_doc_read_release
@forget:
    lda #0
    sta se_fs_owned
    sta se_fs_active
    clc
    rts
