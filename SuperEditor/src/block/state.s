.setcpu "6502"
.include "block/api.inc"
.segment "BSS"
se_sel_mark: .res 1
se_sel_anchor: .res 3
se_sel_start: .res 3
se_sel_end: .res 3
se_sel_length: .res 3
se_b_phase: .res 1
se_b_command: .res 1
se_b_mode: .res 1 ;0 delete,1 one byte,2 clipboard
se_b_byte: .res 1
se_b_changed: .res 1
se_b_error: .res 1 ;deferred applied-error display after source cache reload
se_b_history_owned: .res 1
se_b_clip_owned: .res 1
se_b_token: .res 5
se_b_generation: .res 2
se_b_epoch: .res 2
se_b_start: .res 3
se_b_delete: .res 3
se_b_left: .res 3
se_b_position: .res 3
se_b_count: .res 1
se_b_temp: .res 3
se_b_reveal: .res 1
se_b_doc_epoch: .res 2
