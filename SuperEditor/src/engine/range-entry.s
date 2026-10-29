; Rare checked selected-reference reader. No calls to any other R overlay.
.setcpu "6502"
.macpack longbranch
.include "engine-api.inc"
.include "engine/api.inc"
.include "document/api.inc"
.include "editor_fold/journal.inc"
.import se_f_owner
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #8
    jeq se_gcl_rekey
    cmp #7
    jeq se_gcl_publish
    cmp #EJ_LOCAL
    jeq se_ej_local
    cmp #EJ_COMMIT
    jeq se_ej_commit
    cmp #EJ_FLUSH
    jeq se_ej_flush
    cmp #EJ_BASELINE
    jeq se_ej_baseline
    cmp #EJ_READLOG
    jeq se_ej_readlog
    lda #$79
    sec
    rts

.import se_gcl_publish,se_gsr_refresh

; Actual final writer. R19 is entered from resident after publication, owns the
; complete optional transaction, and calls no overlay.
se_gcl_rekey:
    lda se_f_owner
    bne @done
    lda #4
    sta se_f_owner
    jsr se_gsr_refresh
    lda #0
    sta se_f_owner
@done:
    lda #0
    clc
    rts
