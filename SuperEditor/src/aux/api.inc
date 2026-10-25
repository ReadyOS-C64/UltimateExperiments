; Rare control operations share one command image. Calls originate at resident
; safe points; no auxiliary operation enters another command overlay.
AUX_ID=13
A_LAYOUT_CONTEXT=1
A_FILE_ABORT=2
A_INDEX_CHANGED=3
A_FILE_RECOVERY=4
A_FILE_DRAW=5
.global se_aux_layout_context,se_aux_index_changed,se_file_emergency
.global se_file_recovery_key,se_file_dialog_draw
