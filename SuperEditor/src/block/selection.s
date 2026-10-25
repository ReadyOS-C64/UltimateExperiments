.setcpu "6502"
.macpack longbranch
.include "block/api.inc"
.include "hot/api.inc"
.include "document/math24.inc"
.segment "CODE"
se_selection_toggle:
    lda se_sel_mark
    bne se_selection_clear
    COPY24 se_hot_caret,se_sel_anchor
    lda #1
    sta se_sel_mark
    rts
se_selection_clear:
    lda #0
    sta se_sel_mark
    rts
; Source range [min(anchor,caret),max). Return A/Z indicate nonempty.
se_selection_range:
    COPY24 se_hot_caret,se_sel_start
    COPY24 se_hot_caret,se_sel_end
    lda se_sel_mark
    beq @length
    CMP24 se_sel_anchor,se_hot_caret
    bcs @after
    COPY24 se_sel_anchor,se_sel_start
    jmp @length
@after:
    COPY24 se_sel_anchor,se_sel_end
@length:
    SUB24 se_sel_end,se_sel_start,se_sel_length
    lda se_sel_length
    ora se_sel_length+1
    ora se_sel_length+2
    rts
