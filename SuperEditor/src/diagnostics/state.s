.setcpu "6502"
.include "diagnostics/api.inc"
.segment "BSS"
se_diag_frame_start:
se_diag_buffer: .res 2 ;BEGIN request only;not used after admission
se_diag_cursor: .res 3 ;BEGIN request only
se_diag_active: .res 1
se_diag_owned: .res 1
se_diag_epoch: .res 2
se_diag_output: .res 2 ;admitted pointer survives request changes
se_diag_crc: .res 2 ;shared residentCRC may be clobbered between slices
se_diag_pos: .res 3
se_diag_length: .res 3
se_diag_hot_end: .res 3
se_diag_temp: .res 3
se_diag_count: .res 2
se_diag_error: .res 1
se_diag_frame_end:
.assert se_diag_frame_end-se_diag_frame_start <=48,error,"diagnostics frame budget"
