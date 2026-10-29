.ifndef SE_FOLD_API
SE_FOLD_API=1
SF_VERSION=1
SF_OBJECT_TYPE=$46
SF_RECORD_SIZE=32
SF_MAX_DEPTH=16
SF_HEADING=1
SF_CODE=2
SF_REGION=3
SF_COLLAPSED=1
SF_SAVED=2
SF_SUMMARY=0
SF_HIDDEN=3
SF_END=6
SF_PARENT=9
SF_DEPTH=11
SF_KIND=12
SF_FLAGS=13
SF_CARET=14
SF_LINES=17
SF_LEVEL=20
SF_MOTION=21
SF_BAD=$B0
SF_STALE=$B1
SF_BUSY=$B2
SF_CANCEL=$B3
SF_QUERY=2
SF_ACTION=3
.global se_fold_state,se_fold_state_size,se_fold_record
.global se_fold_token,se_fold_count,se_fold_length,se_fold_epoch,se_fold_stamp
.global se_fold_valid,se_fold_busy,se_fold_error,se_fold_index,se_fold_job
.global se_fold_caret,se_fold_motion,se_fold_select_a,se_fold_select_b
.global se_fold_query,se_fold_mode,se_fold_result,se_fold_hidden,se_fold_selected
.global se_fold_target,se_fold_action,se_fold_next,se_fold_last,se_fold_depth
.global se_fold_stack_end,se_fold_stack_hidden,se_fold_stack_index,se_fold_temp
.global se_fold_validate_begin,se_fold_validate_step,se_fold_query_begin,se_fold_query_step
.global se_fold_action_begin,se_fold_action_step,se_fold_cancel,se_fold_invalidate
.global se_fold_bound_token,se_fold_bound_count,se_fold_bound_length
.global se_fold_guard,se_fold_read,se_fold_write,se_fold_fail,se_fold_done,se_fold_tick
.macro SF_COPY source,target,n
    ldx #n-1
:
    lda source,x
    sta target,x
    dex
    bpl :-
.endmacro
; unsigned24 branch, source<target / source>=target.
.macro SF_LT source,target,dest
    lda source+2
    cmp target+2
    jcc dest
    bne :+
    lda source+1
    cmp target+1
    jcc dest
    bne :+
    lda source
    cmp target
    jcc dest
:
.endmacro
.macro SF_GE source,target,dest
    lda source+2
    cmp target+2
    bcc :+
    jne dest
    lda source+1
    cmp target+1
    bcc :+
    jne dest
    lda source
    cmp target
    jcs dest
:
.endmacro
.endif
