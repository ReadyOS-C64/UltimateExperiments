.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "editor_file/api.inc"
.import se_file_dialog,se_file_dialog_key,se_file_dialog_step,se_file_dialog_finish,se_file_dialog_cancel
.segment "CODE"
    OVL_BINDING
se_file_entry:
    lda se_overlay_frame
    cmp #F_BEGIN
    jeq se_file_begin
    cmp #F_STEP
    jeq se_file_dialog_step
    cmp #F_CANCEL
    jeq se_file_dialog_cancel
    cmp #F_KEY
    jeq se_file_dialog_key
    cmp #6
    jeq se_file_dialog
    cmp #7
    jeq se_file_dialog_finish
.ifndef SE_FILE_UI_KEY_ONLY
    cmp #F_DRAW
    jeq se_file_ui_draw
.endif
    lda #$90
    sec
    rts
