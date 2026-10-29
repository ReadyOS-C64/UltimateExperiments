.setcpu "6502"
.macpack longbranch
.include "fold/api.inc"
.segment "FOLD_VALIDATE"
se_fold_validate_begin:
    lda se_fold_busy
    jne @busy
    lda #0
    sta se_fold_valid
    sta se_fold_index
    sta se_fold_index+1
    sta se_fold_error
    lda #$FF
    sta se_fold_depth
    SF_COPY se_fold_epoch,se_fold_stamp,4
    SF_COPY se_fold_token,se_fold_bound_token,5
    SF_COPY se_fold_count,se_fold_bound_count,2
    SF_COPY se_fold_length,se_fold_bound_length,3
    jsr se_fold_guard
    jcs se_fold_fail
    lda #1
    sta se_fold_busy
    sta se_fold_job
    clc
    rts
@busy:
    lda #SF_BUSY
    sec
    rts
se_fold_validate_step:
    lda se_fold_busy
    jeq @bad
    lda se_fold_job
    cmp #1
    jne @bad
    jsr se_fold_tick
    jcs @return
    lda se_fold_index
    cmp se_fold_count
    jne @read
    lda se_fold_index+1
    cmp se_fold_count+1
    jne @read
    lda #1
    sta se_fold_valid
    jmp se_fold_done
@read:
    jsr se_fold_read
    jcs se_fold_fail
    ; Canonical anchors are strict nonempty hidden intervals in the source.
    SF_GE se_fold_record+SF_SUMMARY,se_fold_record+SF_HIDDEN,@bad
    SF_GE se_fold_record+SF_HIDDEN,se_fold_record+SF_END,@bad
    SF_LT se_fold_length,se_fold_record+SF_END,@bad
    lda se_fold_record+SF_KIND
    cmp #SF_HEADING
    jcc @bad
    cmp #SF_REGION+1
    jcs @bad
    lda se_fold_record+SF_FLAGS
    and #$FC
    jne @bad
    lda se_fold_record+SF_FLAGS
    and #SF_SAVED
    jeq @level
    lda se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    jeq @bad
    SF_LT se_fold_record+SF_CARET,se_fold_record+SF_HIDDEN,@bad
    SF_GE se_fold_record+SF_CARET,se_fold_record+SF_END,@bad
@level:
    lda se_fold_record+SF_KIND
    cmp #SF_HEADING
    jne @other_level
    lda se_fold_record+SF_LEVEL
    jeq @bad
    cmp #7
    jcs @bad
    jcc @reserved
@other_level:
    lda se_fold_record+SF_LEVEL
    jne @bad
@reserved:
    ldx #31
@zero:
    lda se_fold_record,x
    jne @bad
    dex
    cpx #24
    jne @zero
    lda se_fold_record+SF_DEPTH
    cmp #SF_MAX_DEPTH
    jcs @bad
    tax
    lda se_fold_index
    ora se_fold_index+1
    jeq @first
    ; Preorder is strict by summary; a new level may be only one deeper.
    SF_GE se_fold_last,se_fold_record+SF_SUMMARY,@bad
    lda se_fold_depth
    clc
    adc #1
    cmp se_fold_record+SF_DEPTH
    jcc @bad
    lda se_fold_record+SF_DEPTH
    cmp se_fold_depth
    jcc @sibling
    jeq @sibling
    jne @parent
@first:
    txa
    jne @bad
    jeq @parent
@sibling:
    ; Previous record at this depth must finish before the new sibling begins.
    txa
    asl
    clc
    adc se_fold_record+SF_DEPTH
    tay
    lda se_fold_stack_end+2,y
    cmp se_fold_record+SF_SUMMARY+2
    jcc @parent
    jne @bad
    lda se_fold_stack_end+1,y
    cmp se_fold_record+SF_SUMMARY+1
    jcc @parent
    jne @bad
    lda se_fold_stack_end,y
    cmp se_fold_record+SF_SUMMARY
    jcc @parent
    jne @bad
@parent:
    ldx se_fold_record+SF_DEPTH
    jne @child
    lda se_fold_record+SF_PARENT
    and se_fold_record+SF_PARENT+1
    cmp #$FF
    jne @bad
    jeq @accept
@child:
    dex
    txa
    asl
    tay
    lda se_fold_stack_index,y
    cmp se_fold_record+SF_PARENT
    jne @bad
    lda se_fold_stack_index+1,y
    cmp se_fold_record+SF_PARENT+1
    jne @bad
    ; y=(depth-1)*3, parent hidden <= summary and child end <= parent end.
    txa
    asl
    clc
    adc #0
    sta se_fold_temp
    txa
    clc
    adc se_fold_temp
    tay
    lda se_fold_record+SF_SUMMARY+2
    cmp se_fold_stack_hidden+2,y
    jcc @bad
    jne @end
    lda se_fold_record+SF_SUMMARY+1
    cmp se_fold_stack_hidden+1,y
    jcc @bad
    jne @end
    lda se_fold_record+SF_SUMMARY
    cmp se_fold_stack_hidden,y
    jcc @bad
@end:
    lda se_fold_stack_end+2,y
    cmp se_fold_record+SF_END+2
    jcc @bad
    jne @accept
    lda se_fold_stack_end+1,y
    cmp se_fold_record+SF_END+1
    jcc @bad
    jne @accept
    lda se_fold_stack_end,y
    cmp se_fold_record+SF_END
    jcc @bad
@accept:
    lda se_fold_record+SF_DEPTH
    sta se_fold_depth
    asl
    tax
    lda se_fold_index
    sta se_fold_stack_index,x
    lda se_fold_index+1
    sta se_fold_stack_index+1,x
    txa
    clc
    adc se_fold_depth
    tax
    ldy #0
@save:
    lda se_fold_record+SF_END,y
    sta se_fold_stack_end,x
    lda se_fold_record+SF_HIDDEN,y
    sta se_fold_stack_hidden,x
    inx
    iny
    cpy #3
    jne @save
    SF_COPY se_fold_record+SF_SUMMARY,se_fold_last,3
    inc se_fold_index
    jne @more
    inc se_fold_index+1
@more:
    lda #0
    clc
@return:
    rts
@bad:
    lda #SF_BAD
    jmp se_fold_fail
