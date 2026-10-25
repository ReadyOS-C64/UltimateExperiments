.setcpu "6502"
.include "nav/api.inc"
.segment "LINEINDEX"
se_index_table: .res INDEX_RECORDS*INDEX_BYTES
.segment "NAVSTATE"
se_n_start:
se_n_phase: .res 1
se_n_lookup_action: .res 1
se_n_target: .res 3
se_n_query: .res 3
se_n_scan: .res 3
se_n_line: .res 3
se_n_number: .res 3
se_n_extend: .res 1
se_n_rows: .res 1
se_n_remaining: .res 1
se_n_direction: .res 1
se_n_budget: .res 1
se_n_temp: .res 3
se_n_delta: .res 3
se_n_remainder: .res 1
se_n_index: .res 1
se_n_ptr: .res 2
se_n_looked: .res 1
se_n_result: .res 3
se_n_saved_preferred: .res 1
se_n_saved_valid: .res 1
se_n_reveal: .res 1
se_n_cache_hit: .res 1
se_n_end:
; Persistent contiguous logical-line cache. Unlike the per-command frame,
; this survives begin/step calls and is invalidated with the source context.
se_n_cache_count: .res 1
se_n_cache_head: .res 1
se_n_cache_end: .res 3
se_n_cache_base: .res 3
se_n_cache_starts: .res 75 ;25 consecutive24-bit line starts, circular order
.assert *-se_n_start <=128,error,"navigation frame/cache exceeds private area"
