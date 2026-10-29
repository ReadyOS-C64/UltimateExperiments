.setcpu "6502"
.include "hot/api.inc"
.segment "ZEROPAGE"
se_hot_ptr: .res 2
se_hot_packet: .res 2
.segment "DOCSTATE"
.export se_hot_state_start,se_hot_state_end
se_hot_state_start:
se_hot_ready: .res 1
se_hot_phase: .res 1 ;0idle,1loading,2history flush
se_hot_pending: .res 1
se_hot_fault: .res 1 ;last failed flush; applied data becomes authoritative
se_hot_owned: .res 1
se_hot_original: .res 5
se_hot_append: .res 5
se_hot_generation: .res 2
se_hot_position: .res 3 ;LOAD requested global caret
se_hot_base: .res 3
se_hot_caret: .res 3
se_hot_before: .res 3
se_hot_group: .res 1
se_hot_byte: .res 1
se_hot_old_length: .res 2
se_hot_length: .res 2
se_hot_left: .res 2
se_hot_right: .res 2
se_hot_prefix: .res 2
se_hot_suffix: .res 2
se_hot_loaded: .res 2
se_hot_target: .res 2
se_hot_feed: .res 2
se_hot_feed_left: .res 2
se_hot_tmp: .res 3
se_hot_count: .res 2
se_hot_delete: .res 1
se_hot_command: .res 1
se_hot_state_end:
.assert se_hot_state_end-se_hot_state_start <256,error,"hot clear bound"
.segment "BSS"
se_hot_epoch: .res 2
