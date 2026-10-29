; Outer entry excludes phases4..9. Reject instead of replacing active C code.
.setcpu "6502"
.include "fold/editor-leaves/api.inc"
.segment "FOLD_EDITOR"
se_fb_filter_step:
se_fb_mark_step:
se_fb_compact_step:
    lda #SF_BAD
    jmp se_fb_fail
