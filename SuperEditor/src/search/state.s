.setcpu "6502"
.include "search/api.inc"
.segment "BSS"
; Linked after protected old BSS: no old service state moves.
se_s_active: .res 1
se_s_owned: .res 1
se_s_epoch: .res 2
se_s_position: .res 3
se_s_limit: .res 3
se_s_origin: .res 3
se_s_pattern: .res 26
se_s_prefix: .res 26
se_s_length: .res 1
se_s_insensitive: .res 1
se_s_match: .res 1
se_s_byte: .res 1
se_s_stage: .res 1
se_s_budget: .res 1
se_s_index: .res 1
se_s_temp: .res 3
se_s_wrapped: .res 1
se_s_found: .res 1
se_g_line: .res 3 ;one-based logical source line request
