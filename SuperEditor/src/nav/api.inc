NAV_ID=8
N_BEGIN=1
N_STEP=2
N_CANCEL=3
; C8-private synchronous planner: set overlay_frame,call NAV_ID directly.
; Do not send through se_navigation_call's asynchronous C8/C11 classifier.
N_EDGE=6
N_EDGE_REDRAW=0
N_EDGE_RELOAD=1
N_EDGE_FLUSH=2
N_LOOKUP=1
N_END=2
N_DOWN_END=3
N_DOWN_PREF=4
N_LOOK_INITIAL=0
N_LOOK_UP=1
N_LOOK_GOTO=2
INDEX_FIRST=$8D00
INDEX_RECORDS=128
INDEX_BYTES=9
.global se_navigation_call,se_navigation_cancel,se_index_changed
.global se_i_ready,se_i_count,se_i_generation,se_i_original,se_i_append,se_i_scan,se_i_line,se_i_number
.global se_n_owned,se_n_preferred,se_n_preferred_valid,se_n_columns
.global se_n_start,se_n_end,se_n_phase,se_n_lookup_action,se_n_target,se_n_query,se_n_scan
.global se_n_line,se_n_number,se_n_extend,se_n_rows,se_n_remaining,se_n_direction
.global se_n_budget,se_n_temp,se_n_delta,se_n_remainder,se_n_index,se_n_ptr,se_n_looked
.global se_index_table
.global se_n_result,se_n_saved_preferred,se_n_saved_valid,se_n_reveal
.global se_n_cache_hit,se_n_cache_count,se_n_cache_head,se_n_cache_end,se_n_cache_base,se_n_cache_starts
