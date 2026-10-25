.setcpu "6502"
.include "search/api.inc"
.include "document/api.inc"
.import se_overlay_call,se_overlay_frame
.segment "CODE"
se_search_call:
    cmp #S_CANCEL
    beq se_search_cancel
    sta se_overlay_frame
    lda #SEARCH_ID
    ldx #1
    jsr se_overlay_call
    bcc @return
    pha
    jsr se_search_cancel
    pla
    sec
@return:
    rts
se_search_cancel:
    lda se_s_owned
    beq @clear
    lda se_s_epoch
    cmp se_doc_epoch
    bne @clear
    lda se_s_epoch+1
    cmp se_doc_epoch+1
    bne @clear
    jsr se_doc_read_release
@clear:
    lda #0
    sta se_s_owned
    sta se_s_active
    clc
    rts
