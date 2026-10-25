; Rare checked selected-reference reader. No calls to any other R overlay.
.setcpu "6502"
.macpack longbranch
.include "engine-api.inc"
.include "engine/api.inc"
.include "document/api.inc"
.include "editor_fold/journal.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #7
    jeq se_gcl_publish
    cmp #RANGE_BEGIN
    jeq se_range_begin
    cmp #RANGE_STEP
    jeq se_range_step
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

.import se_gcl_publish
