.setcpu "6502"
.include "engine/api.inc"
.include "document/api.inc"
.include "document/splice.inc"
.import se_overlay_call,se_overlay_frame
.import se_ej_status,se_hot_phase
.export se_ef_journal_local,se_ef_journal_publish,se_ef_journal_commit
.export se_ef_journal_call,se_ef_transform_call
.segment "CODE"
se_doc_splice_begin:
    lda #ENGINE_BEGIN
    beq invoke
se_doc_splice_local_begin:
    lda #ENGINE_LOCAL_BEGIN
    bne invoke
se_doc_splice_feed:
    lda #ENGINE_FEED
    bne invoke
se_doc_splice_step:
    lda #ENGINE_STEP
    bne invoke
se_doc_splice_refs_begin:
    lda #ENGINE_REFS_BEGIN
    bne invoke
se_doc_splice_local_refs_begin:
    lda #ENGINE_LOCAL_REFS_BEGIN
invoke:
    ldy #ENGINE_ID
invoke_id:
    tax
    lda se_overlay_frame
    pha
    stx se_overlay_frame
    tya
    ldx #0
    jsr se_overlay_call
    ; These instructions preserve carry; Y is explicitly caller-clobbered.
    tay
    pla
    sta se_overlay_frame
    tya
    rts
se_range_begin:
    lda #RANGE_BEGIN
    beq range_invoke
se_range_step:
    lda #RANGE_STEP
range_invoke:
    ldy #RANGE_ID
    bne invoke_id
se_doc_splice_cancel:
    lda #0
    sta se_doc_busy
    sta doc_refs_active
    clc
    rts

; Optional fold provenance must never turn a successful source edit into failure.
se_ef_journal_local:
    lda #2
    bne journal_observe
se_ef_journal_publish:
    lda se_hot_phase
    cmp #2
    bne se_ef_journal_commit
    lda #4
    bne journal_observe
se_ef_journal_commit:
    lda #3
journal_observe:
    ldy se_ej_status
    cpy #1
    beq @call
    cpy #2
    bne @done
@call:
    jsr se_ef_journal_call
    bcc @done
    lda #$80
    sta se_ej_status
@done:
    lda #0
    clc
    rts
se_ef_journal_call:
    jmp range_invoke
se_ef_transform_call:
    ldy #20
    jmp invoke_id
