.setcpu "6502"
.include "history/api.inc"
.segment "BSS"
se_h_service_epoch: .res 2
.segment "OBJECTS"
.export se_h_state_start, se_h_state_end
se_h_state_start:
se_h_token: .res 5
se_h_ready: .res 1
se_h_phase: .res 1
se_h_applied: .res 1
se_h_fault: .res 1
se_h_trimmed: .res 2
se_h_end: .res 2
se_h_cursor: .res 2
se_h_current: .res 4
se_h_saved: .res 4
se_h_counter: .res 4
se_h_group: .res 1
se_h_open_group: .res 1
se_h_before_caret: .res 3
se_h_after_caret: .res 3
se_h_caret: .res 3
se_h_dirty: .res 1
se_h_original: .res 5
se_h_append: .res 5
se_h_generation: .res 2
se_h_owned_lease: .res 1
se_h_owned_capture: .res 1
se_h_owned_splice: .res 1
se_h_target_node: .res 4
se_h_record: .res 64
se_h_record_start: .res 2
se_h_record_len: .res 2
se_h_keep_start: .res 2
se_h_keep_end: .res 2
se_h_keep_len: .res 2
se_h_trim_count: .res 2
se_h_io_pos: .res 3
se_h_io_dest: .res 3
se_h_io_left: .res 2
se_h_io_count: .res 2
se_h_crc: .res 2
se_h_crc_pos: .res 3
se_h_crc_left: .res 2
se_h_request: .res 9
se_h_base_append: .res 3
se_h_insert_offset: .res 3
se_h_action: .res 1
se_h_tmp: .res 3
se_h_error: .res 1
se_h_state_end:
.assert se_h_state_end-se_h_state_start <256, error, "history frame exceeds clear loop"
.segment "RODATA"
; Changes to this ABI version deliberately alter the resident binding seal.
.export se_history_abi
se_history_abi: .byte H_RECORD_ABI
