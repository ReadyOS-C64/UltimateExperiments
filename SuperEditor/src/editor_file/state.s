.setcpu "6502"
.include "editor_file/api.inc"
; Outside the union: C8 must refuse while owner !=0; resident init zeroes owner.
.segment "BSS"
se_f_owner: .res 1
se_f_current_name: .res 16
se_f_current_len: .res 1
se_f_current_device: .res 1
; This follows the 267-byte FileIO frame in the $8D00..$917F phase union.
; Link FILESTATE once; do not zero/reinitialize while an owned channel exists.
.segment "FILESTATE"
se_f_operation: .res 1
se_f_phase: .res 1
se_f_request: .res 1
se_f_result: .res 1
se_f_carry: .res 1
se_f_error: .res 1
.export se_f_raw_error,se_f_dos_error
se_f_raw_error: .res 1
se_f_dos_error: .res 1
se_f_name: .res 16
se_f_name_len: .res 1
se_f_device: .res 1
se_f_cancel: .res 1
se_f_committed: .res 1
se_f_length: .res 3
se_f_position: .res 3
se_f_old: .res 15 ; meta/original/append tokens, only released after publication
se_f_candidate: .res 15
se_f_allocated: .res 1
se_f_backup: .res 280 ; roots256 + canonical22 + epoch2
se_f_banks: .res 1
se_f_lease: .res 1
se_f_history: .res 4
se_f_generation: .res 2
se_f_work: .res 3
se_f_left: .res 2
se_f_packet: .res 2
se_f_compare: .res 1
se_f_verify_target: .res 1
se_f_target_exists: .res 1
se_f_temp: .res 16
se_f_backup_name: .res 16
se_f_nonce: .res 1
; Native dialog result uses caller's se_f_name/name_len/device. No ASCII folding.
.export se_f_ui_key,se_f_ui_index,se_f_ui_help
se_f_ui_help: .res 1
se_f_ui_key: .res 1
se_f_ui_index: .res 1

se_f_epoch: .res 2 ; provider/document epoch captured before owning resources
