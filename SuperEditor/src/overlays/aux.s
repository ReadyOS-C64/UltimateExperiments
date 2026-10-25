.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "aux/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #6
    jeq se_gsr_refresh
    cmp #A_LAYOUT_CONTEXT
    jeq se_aux_layout_context
    cmp #A_FILE_ABORT
    jeq se_file_emergency
    cmp #A_INDEX_CHANGED
    jeq se_aux_index_changed
    cmp #A_FILE_RECOVERY
    jeq se_file_recovery_key
    cmp #A_FILE_DRAW
    jeq se_file_dialog_draw
    lda #$70
    sec
    rts

.import se_gsr_refresh
