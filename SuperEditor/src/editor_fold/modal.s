.setcpu "6502"
SE_EDITOR_FOLD_IMPLEMENTATION=1
.include "editor_fold/api.inc"
.import se_f_owner,se_ef_valid,se_ef_suspended
.import se_ef_invalidate,se_ef_key_match,se_ef_projection_invalidate
.export se_ef_modal
.segment "CODE"
; Resident, phase-independent safe point before layout/key preparation, even
; when VALID0. FILE owns the union: plain rows may scan source, but never query
; R18. Preserve the published map allocation, records, key and user fold flags.
; After FILE exits, only a still-matching canonical key may republish the map.
; A0/Cclear normal (including changed OPEN source); provider fault A/Cset.
se_ef_modal:
    lda se_f_owner
    cmp #1
    bne @resume
    lda se_ef_valid
    beq @ready
    lda #1
    sta se_ef_suspended
    jsr se_ef_invalidate
    jsr se_ef_projection_invalidate
    jmp @ready
@resume:
    lda se_ef_suspended
    beq @ready
    lda #0
    sta se_ef_suspended
    jsr se_ef_key_match
    bcs @changed
    lda #1
    sta se_ef_valid
    jsr se_ef_projection_invalidate
    jmp @ready
@changed:
    cmp #EF_CHANGED
    bne @error
    jsr se_ef_projection_invalidate
@ready:
    lda #0
    clc
    rts
@error:
    sec
    rts
