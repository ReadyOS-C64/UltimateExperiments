.ifndef SE_FOLD_BUILDER_API
SE_FOLD_BUILDER_API=1
.include "fold/api.inc"
.include "supermark/api.inc"
FB_SPACE=$B4
FB_INCOMPLETE=$B5
FB_DEPTH=$B6
FB_PARSE=1
FB_EVENT=2
FB_EOF=3
FB_FILTER=4
FB_MARK=5
FB_COMPACT=6
FB_VALIDATE=7
FB_RETAIN_LOAD=8
FB_RETAIN_MATCH=9
.global se_fb_begin,se_fb_step,se_fb_cancel,se_fb_fail,se_fb_guard
.global se_fb_state,se_fb_state_size,se_fb_buffer,se_fb_source,se_fb_source_bound
.global se_fb_token_bound,se_fb_length_bound,se_fb_stamp,se_fb_capacity
.global se_fb_busy,se_fb_error,se_fb_phase,se_fb_raw_count,se_fb_count
.global se_fb_omitted,se_fb_empty,se_fb_line,se_fb_chunk,se_fb_used,se_fb_eof
.global se_fb_heads,se_fb_regions,se_fb_code,se_fb_code_index,se_fb_close
.global se_fb_scan,se_fb_slot,se_fb_depth,se_fb_start,se_fb_end,se_fb_kind
.global se_fb_old_token,se_fb_old_count,se_fb_old_source,se_fb_old_epoch,se_fb_old_length,se_fb_old_valid
.global se_fb_old_bound,se_fb_old_count_bound,se_fb_keep,se_fb_retained,se_fb_old_record
.global se_fb_retention_begin,se_fb_old_guard,se_fb_finish_build,se_fb_validate_candidate
.global se_fb_retain_load,se_fb_retain_match
.global se_fb_parse_step,se_fb_filter_step,se_fb_mark_step,se_fb_compact_step
.global se_sm_init,se_sm_feed,se_sm_finish,se_sm_pos,se_sm_ready,se_sm_kind
.global se_sm_start,se_sm_end,se_sm_level,se_sm_fence,se_sm_regions
; Phase union with foundation's validation stack, never resident allocation.
FB_H_INDEX=se_fold_stack_end
FB_H_LEVEL=se_fold_stack_end+12
FB_R_INDEX=se_fold_stack_end+18
FB_H_END=se_fold_stack_end+12
FB_H_OMIT=se_fold_stack_end+30
FB_E_END=se_fold_stack_end+36
.endif
