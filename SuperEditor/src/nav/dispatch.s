.setcpu "6502"
.macpack longbranch
.include "nav/api.inc"
.include "document/api.inc"
.include "editor/api.inc"
.include "layout/api.inc"
.import se_overlay_call,se_overlay_frame
.import se_f_owner
.import se_ef_invalidate,se_ef_projection_invalidate
.segment "CODE"
; Root caller only, never enter from an active command overlay.
se_navigation_call:
    cmp #N_BEGIN
    bne :+
    ldx se_v_nav_busy
    beq :+
    lda #$7A
    sec
    rts
:
    cmp #N_CANCEL
    beq se_navigation_cancel
    sta se_overlay_frame
    lda #NAV_ID
    ldx se_overlay_frame
    cpx #L_BEGIN
    bcc :+
    lda #LAYOUT_ID
:
    ldx #1
    jsr se_overlay_call
    bcc @return
    pha
    bit se_l_active
    bpl :+
    jsr se_ef_invalidate
    jsr se_ef_projection_invalidate
:
    jsr se_navigation_cancel
    lda #0
    sta se_i_ready ;failed/corrupt continuation cannot leave partial indexes live
    sta se_l_valid
    pla
    sec
@return:
    rts
; Cancellation never requires a successful C reload. Release only owned epoch.
se_navigation_cancel:
    lda se_n_owned
    beq @clear
    lda se_l_active
    beq @index_epoch
    lda se_l_original+3
    cmp se_doc_epoch
    bne @clear
    lda se_l_original+4
    cmp se_doc_epoch+1
    bne @clear
    beq @owned
@index_epoch:
    lda se_i_original+3
    cmp se_doc_epoch
    bne @clear
    lda se_i_original+4
    cmp se_doc_epoch+1
    bne @clear
@owned:
    lda se_n_reveal
    beq @release
    lda se_n_saved_preferred
    sta se_n_preferred
    lda se_n_saved_valid
    sta se_n_preferred_valid
@release:
    jsr se_doc_read_release
@clear:
    bit se_l_active
    bpl :+
    lda se_f_owner
    cmp #3
    bne :+
    lda #0
    sta se_f_owner ;only the owned fold-layout phase; its FS lease fields are zero
:
    lda #0
    sta se_n_owned
    sta se_v_nav_busy
    sta se_n_reveal
    sta se_l_active
    clc
    rts
