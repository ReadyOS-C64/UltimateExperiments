; Shared resident frame and command-overlay ABI1. Logical journal offsets.
H_INIT=1
H_BEGIN=2
H_FEED=3
H_STEP=4
H_CANCEL=5
H_UNDO=6
H_REDO=7
H_SAVED=8
H_CLEAR=9
H_BREAK=10
H_EDIT_ID=4
H_PLAY_ID=5
H_CAPTURE=1
H_SEAL=2
H_SPACE=3
H_FEEDING=4
H_APPLY=5
H_MOVE=6
H_APPEND=7
H_COPY=8
H_VERIFY=9
H_REPLAY=10
H_STAGE=$B000
H_HEADER=64
H_RECORD_ABI=1
H_CHUNK=128
.global se_history_cold, se_history_call, se_h_validate, se_h_context
.global se_h_io, se_h_abort, se_h_cancel, se_h_dirty_update
.global se_h_service_epoch
.global se_h_token
.global se_h_ready
.global se_h_phase
.global se_h_applied
.global se_h_fault
.global se_h_trimmed
.global se_h_end
.global se_h_cursor
.global se_h_current
.global se_h_saved
.global se_h_counter
.global se_h_group
.global se_h_open_group
.global se_h_before_caret
.global se_h_after_caret
.global se_h_caret
.global se_h_dirty
.global se_h_original
.global se_h_append
.global se_h_generation
.global se_h_owned_lease
.global se_h_owned_capture
.global se_h_owned_splice
.global se_h_target_node
.global se_h_record
.global se_h_record_start
.global se_h_record_len
.global se_h_keep_start
.global se_h_keep_end
.global se_h_keep_len
.global se_h_trim_count
.global se_h_io_pos
.global se_h_io_dest
.global se_h_io_left
.global se_h_io_count
.global se_h_crc
.global se_h_crc_pos
.global se_h_crc_left
.global se_h_request
.global se_h_base_append
.global se_h_insert_offset
.global se_h_action
.global se_h_tmp
.global se_h_error
