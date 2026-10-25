; Outer entry excludes BEGIN and parser phases1..3.
.setcpu "6502"
.include "fold/editor-leaves/api.inc"
.segment "FOLD_EDITOR"
se_sm_init:
se_sm_feed:
se_sm_finish:
    lda #SF_BAD
    sec
    rts
