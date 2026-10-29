.setcpu "6502"
.include "diagnostics/api.inc"
.include "document/api.inc"
.import se_reu_epoch
.importzp text_ptr
.export se_diag_pointer,se_diag_abort
.segment "CODE"
se_diag_pointer:
    lda se_diag_output
    sta text_ptr
    lda se_diag_output+1
    sta text_ptr+1
    rts
; Resident cleanup can be used even after a failed diagnostic overlay reload.
; Never decrement another epoch's lease, even if document state was not reset.
se_diag_cancel:
    ldx #0
    ldy #3
    bne cleanup
se_diag_abort:
    tax
    ldy #4
cleanup:
    stx se_diag_error
    lda se_diag_active
    beq lease
    jsr se_diag_pointer
    tya
    ldy #DS_STATUS
    sta (text_ptr),y
    lda se_diag_error
    ldy #DS_ERROR
    sta (text_ptr),y
lease:
    lda se_diag_owned
    beq forget
    lda se_diag_epoch
    cmp se_reu_epoch
    bne forget
    cmp se_doc_epoch
    bne forget
    lda se_diag_epoch+1
    cmp se_reu_epoch+1
    bne forget
    cmp se_doc_epoch+1
    bne forget
    jsr se_doc_read_release
forget:
    lda #0
    sta se_diag_active
    sta se_diag_owned
    lda se_diag_error
    beq success
    sec
    rts
success:
    clc
    rts
