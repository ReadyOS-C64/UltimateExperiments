.setcpu "6502"
.macpack longbranch
.include "fold/api.inc"
.segment "FOLD_ACTION"
; action0 toggle target,1 collapse target,2 expand target,3 collapse all,
;4 expand all,5 reveal query (opens every collapsed ancestor containing query).
; Outputs a new caret only on complete success; source/selection are immutable.
se_fold_action_begin:
    lda se_fold_busy
    jne @busy
    lda se_fold_valid
    jeq @stale
    lda se_fold_action
    cmp #6
    jcs @bad
    SF_LT se_fold_length,se_fold_caret,@bad
    SF_LT se_fold_length,se_fold_query,@bad
    jsr se_fold_tick
    jcs @return
    lda #0
    sta se_fold_index
    sta se_fold_index+1
    lda se_fold_action
    cmp #3
    jcs @all
    lda se_fold_target+1
    cmp se_fold_count+1
    jcc @target
    jne @bad
    lda se_fold_target
    cmp se_fold_count
    jcs @bad
@target:
    SF_COPY se_fold_target,se_fold_index,2
@all:
    SF_COPY se_fold_caret,se_fold_next,3
    lda #0
    sta se_fold_valid
    sta se_fold_error
    lda #SF_ACTION
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
se_fold_action_step:
    lda se_fold_busy
    jeq @bad
    lda se_fold_job
    cmp #SF_ACTION
    jne @bad
    jsr se_fold_tick
    jcs @return
    lda se_fold_index
    cmp se_fold_count
    jne @read
    lda se_fold_index+1
    cmp se_fold_count+1
    jeq @done
@read:
    jsr se_fold_read
    jcs se_fold_fail
    lda se_fold_action
    cmp #5
    jne @decide
    SF_LT se_fold_query,se_fold_record+SF_HIDDEN,@advance
    SF_GE se_fold_query,se_fold_record+SF_END,@advance
    jmp @expand
@decide:
    cmp #0
    jne @explicit
    lda se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    jeq @collapse
    jmp @expand
@explicit:
    cmp #1
    jeq @collapse
    cmp #3
    jeq @collapse
@expand:
    lda se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    jeq @advance
    lda se_fold_action
    cmp #5
    jeq @clear
    lda se_fold_record+SF_FLAGS
    and #SF_SAVED
    jeq @clear
    ldx #2
@summary:
    lda se_fold_next,x
    cmp se_fold_record+SF_SUMMARY,x
    jne @clear
    dex
    jpl @summary
    ldx #3
@motion:
    lda se_fold_motion,x
    cmp se_fold_record+SF_MOTION,x
    jne @clear
    dex
    jpl @motion
    SF_COPY se_fold_record+SF_CARET,se_fold_next,3
@clear:
    lda se_fold_record+SF_FLAGS
    and #$FC
    sta se_fold_record+SF_FLAGS
    jmp @write
@collapse:
    lda se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    jne @advance
    lda se_fold_record+SF_FLAGS
    and #$FC
    ora #SF_COLLAPSED
    sta se_fold_record+SF_FLAGS
    SF_LT se_fold_next,se_fold_record+SF_HIDDEN,@write
    SF_GE se_fold_next,se_fold_record+SF_END,@write
    SF_COPY se_fold_next,se_fold_record+SF_CARET,3
    SF_COPY se_fold_motion,se_fold_record+SF_MOTION,4
    lda se_fold_record+SF_FLAGS
    ora #SF_SAVED
    sta se_fold_record+SF_FLAGS
    SF_COPY se_fold_record+SF_SUMMARY,se_fold_next,3
@write:
    jsr se_fold_write
    jcs se_fold_fail
@advance:
    lda se_fold_action
    cmp #3
    jcc @done
    inc se_fold_index
    jne @more
    inc se_fold_index+1
@more:
    clc
    rts
@done:
    SF_COPY se_fold_next,se_fold_result,3
    lda #1
    sta se_fold_valid
    jmp se_fold_done
@bad:
    lda #SF_BAD
    jmp se_fold_fail
@return:
    rts
