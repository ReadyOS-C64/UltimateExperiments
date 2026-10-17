.setcpu "6502"
.segment "CODE"
.import dos64_uci_state
.export _uci_state := dos64_uci_state
.import dos64_uci_error
.export _uci_error := dos64_uci_error
.import dos64_uci_recovery_failed
.export _uci_recovery_failed := dos64_uci_recovery_failed
.import dos64_uci_flags
.export _uci_flags := dos64_uci_flags
.import dos64_uci_last_status
.export _uci_last_status := dos64_uci_last_status
.import dos64_uci_command
.export _uci_command := dos64_uci_command
.import dos64_uci_data
.export _uci_data := dos64_uci_data
.import dos64_uci_status
.export _uci_status := dos64_uci_status
.import dos64_uci_command_len
.export _uci_command_len := dos64_uci_command_len
.import dos64_uci_data_len
.export _uci_data_len := dos64_uci_data_len
.import dos64_uci_status_len
.export _uci_status_len := dos64_uci_status_len
.import dos64_uci_now
.export _uci_now := dos64_uci_now
.import dos64_uci_data_capacity
.export _uci_data_capacity := dos64_uci_data_capacity
.import dos64_uci_status_capacity
.export _uci_status_capacity := dos64_uci_status_capacity
.import dos64_uci_timeout
.export _uci_timeout := dos64_uci_timeout
.import dos64_uci_recovery_timeout
.export _uci_recovery_timeout := dos64_uci_recovery_timeout
.import dos64_files_state
.export _files_state := dos64_files_state
.import dos64_files_error
.export _files_error := dos64_files_error
.import dos64_files_transport_error
.export _files_transport_error := dos64_files_transport_error
.import dos64_files_handle
.export _files_handle := dos64_files_handle
.import dos64_files_target
.export _files_target := dos64_files_target
.import dos64_files_op
.export _files_op := dos64_files_op
.import dos64_files_mode
.export _files_mode := dos64_files_mode
.import dos64_files_path_len
.export _files_path_len := dos64_files_path_len
.import dos64_files_count_known
.export _files_count_known := dos64_files_count_known
.import dos64_files_uncertain
.export _files_uncertain := dos64_files_uncertain
.import dos64_files_now
.export _files_now := dos64_files_now
.import dos64_files_actual
.export _files_actual := dos64_files_actual
.import dos64_files_offset
.export _files_offset := dos64_files_offset
.import dos64_uci_init
.export _uci_init := dos64_uci_init
.import dos64_uci_poll
.export _uci_poll := dos64_uci_poll
.import dos64_uci_accept
.export _uci_accept := dos64_uci_accept
.import dos64_uci_abort
.export _uci_abort := dos64_uci_abort
.import dos64_files_init
.export _files_init := dos64_files_init
.import dos64_files_poll
.export _files_poll := dos64_files_poll
.import dos64_uci_start
.export _uci_start
_uci_start:
 jsr dos64_uci_start
 lda #0
 rol a
 ldx #0
 rts
.import dos64_files_start
.export _files_start
_files_start:
 jsr dos64_files_start
 lda #0
 rol a
 ldx #0
 rts
