.setcpu "6502"
.include "document/api.inc"
.segment "CODE"
; Foreground read leases prevent mutations across asynchronous copy work.
; Display reads need no lease within a single synchronous call.
se_doc_read_acquire:
    jsr se_doc_validate
    bcs @return
    lda se_doc_busy
    bne @busy
    lda se_doc_read_locks
    cmp #$FF
    beq @busy
    inc se_doc_read_locks
    lda #0
    clc
@return:
    rts
@busy:
    lda #$41
    sec
    rts
se_doc_read_release:
    lda se_doc_read_locks
    beq @state
    dec se_doc_read_locks
    lda #0
    clc
    rts
@state:
    lda #$40
    sec
    rts
