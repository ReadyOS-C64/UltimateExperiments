.setcpu "6502"
.macpack longbranch
.include "fold/api.inc"
.segment "FOLD_QUERY"
; mode0 visual projection,1 forward skip,2 backward skip. Canonical input stays.
se_fold_query_begin:
    lda se_fold_busy
    jne @busy
    lda se_fold_valid
    jeq @stale
    lda se_fold_mode
    cmp #3
    jcs @bad
    SF_LT se_fold_length,se_fold_query,@bad
    jsr se_fold_tick
    jcs @return
    lda #0
    sta se_fold_index
    sta se_fold_index+1
    sta se_fold_hidden
    sta se_fold_selected
    sta se_fold_error
    lda #SF_QUERY
    sta se_fold_job
    lda #1
    sta se_fold_busy
    clc
@return:
    rts
@busy:
    lda #SF_BUSY
    sec
    rts
@stale:
    lda #SF_STALE
    jmp se_fold_fail
@bad:
    lda #SF_BAD
    jmp se_fold_fail
se_fold_query_step:
    lda se_fold_busy
    jeq @bad
    lda se_fold_job
    cmp #SF_QUERY
    jne @bad
    jsr se_fold_tick
    jcs @return
    lda se_fold_index
    cmp se_fold_count
    jne @read
    lda se_fold_index+1
    cmp se_fold_count+1
    jeq @visible
@read:
    jsr se_fold_read
    jcs se_fold_fail
    ; Sorted summaries permit early completion before the next section.
    SF_LT se_fold_query,se_fold_record+SF_SUMMARY,@visible
    lda se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    jeq @next
    SF_LT se_fold_query,se_fold_record+SF_HIDDEN,@next
    SF_GE se_fold_query,se_fold_record+SF_END,@next
    lda #1
    sta se_fold_hidden
    ldx #2
@empty:
    lda se_fold_select_a,x
    cmp se_fold_select_b,x
    jne @range
    dex
    jpl @empty
    jmp @projection
@range:
    ; A spanning selection includes the hidden canonical source interval.
    SF_LT se_fold_select_a,se_fold_select_b,@ordered
    SF_GE se_fold_select_b,se_fold_record+SF_END,@projection
    SF_GE se_fold_record+SF_HIDDEN,se_fold_select_a,@projection
    jmp @selected
@ordered:
    SF_GE se_fold_select_a,se_fold_record+SF_END,@projection
    SF_GE se_fold_record+SF_HIDDEN,se_fold_select_b,@projection
@selected:
    lda #1
    sta se_fold_selected
@projection:
    lda se_fold_mode
    cmp #1
    jeq @forward
    SF_COPY se_fold_record+SF_SUMMARY,se_fold_result,3
    jmp se_fold_done
@forward:
    SF_COPY se_fold_record+SF_END,se_fold_result,3
    jmp se_fold_done
@next:
    inc se_fold_index
    jne @more
    inc se_fold_index+1
@more:
    clc
    rts
@visible:
    SF_COPY se_fold_query,se_fold_result,3
    jmp se_fold_done
@bad:
    lda #SF_BAD
    jmp se_fold_fail
@return:
    rts
