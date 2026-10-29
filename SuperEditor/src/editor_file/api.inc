.ifndef SE_EDITOR_FILE_API
SE_EDITOR_FILE_API=1
; C12 operations; resident dispatcher writes result/carry after requested action.
F_BEGIN=1
F_STEP=2
F_CANCEL=3
F_KEY=4
F_DRAW=5
F_DIALOG=6
F_DIALOG_FINISH=7
F_OPEN=1
F_SAVE=2
F_SAVEAS=3
; C10 transport opcodes. All requests return to resident before loading C slot.
FT_INIT=$C0
FT_PREFLIGHT_BEGIN=$C1
FT_PREFLIGHT_STEP=$C2
FT_OPEN=$C3
FT_READ=$C4
FT_CREATE=$C5
FT_WRITE=$C6
FT_CLOSE=$C7
FT_RENAME=$C8
FT_BACKUP=$C9
FT_SCRATCH_TEMP=$CA
FT_SCRATCH_BACKUP=$CB
FT_ABORT=$CC
FT_EMPTY_CLOSE=$CD
FT_DIRECTORY=$CE
FT_NEXT=$CF
FT_VALIDATE=$D0
FT_PREFLIGHT_CANCEL=$D1
FT_EXISTS_BEGIN=$D2 ;all non-DEL directory entries; no payload-chain read
; Resident-only history actions; never enter another C slot from C12.
FA_HISTORY_INIT=$E1
FA_HISTORY_SAVED=$E8
F_CAPACITY=$99
F_CHANGED=$9A
F_RECOVERY=$9B
F_CANCELLED=$9C
.global se_f_owner,se_f_current_name,se_f_current_len,se_f_current_device,se_f_epoch
.global se_f_operation,se_f_phase,se_f_request,se_f_result,se_f_carry,se_f_error
.global se_f_raw_error,se_f_dos_error
.global se_f_name,se_f_name_len,se_f_device,se_f_cancel,se_f_committed
.global se_f_length,se_f_position,se_f_old,se_f_candidate,se_f_allocated
.global se_f_backup,se_f_banks,se_f_lease,se_f_history,se_f_generation
.global se_f_work,se_f_left,se_f_packet,se_f_compare,se_f_verify_target
.global se_f_target_exists,se_f_temp,se_f_backup_name,se_f_nonce
.global se_f_preflight_phase,se_f_preflight_result,se_f_preflight_length
.global se_file_entry,se_file_transport,se_file_begin,se_file_step,se_file_cancel
.global se_file_ui_key,se_file_ui_draw,se_f_ui_help
.endif

.global se_file_dialog,se_file_dialog_key,se_file_dialog_step,se_file_dialog_finish,se_file_dialog_cancel
