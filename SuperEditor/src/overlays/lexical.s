; C15 is entered only from resident. It never calls another command overlay.
.setcpu "6502"
.include "editor-api.inc"
.import se_style_lexical
.segment "STYLE_CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #3
    bne @argument
    jmp se_style_lexical
@argument:
    lda #$BA
    sec
    rts
