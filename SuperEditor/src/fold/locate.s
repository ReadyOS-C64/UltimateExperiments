.setcpu "6502"
.macpack longbranch
.include "fold/locate.inc"
.segment "FOLD_LOCATE"
se_fold_locate_begin:
    lda se_fold_busy
    bne busy
    lda se_fold_valid
    beq stale
    lda se_fold_mode
    cmp #3
    bcs bad
    SF_LT se_fold_length,se_fold_query,bad
    jsr se_fold_tick
    bcs return
    SF_COPY se_fold_query,se_fold_next,3
    lda se_fold_mode
    sta se_fold_action
    lda #$FF
    sta se_fold_last
    sta se_fold_last+1
    lda #0
    sta se_fold_index
    sta se_fold_index+1
    sta se_fold_error
    lda #SF_LOCATE
    sta se_fold_job
    lda #1
    sta se_fold_busy
    clc
return:
    rts
busy:
    lda #SF_BUSY
    sec
    rts
stale:
    lda #SF_STALE
    jmp se_fold_fail
bad:
    lda #SF_BAD
    jmp se_fold_fail

se_fold_locate_step:
    lda se_fold_busy
    beq bad
    lda se_fold_job
    cmp #SF_LOCATE
    bne bad
    ; A suspended locator cannot silently change its query/filter midscan.
    lda se_fold_mode
    cmp se_fold_action
    bne stale
    ldx #2
@query:
    lda se_fold_query,x
    cmp se_fold_next,x
    bne stale
    dex
    bpl @query
    jsr se_fold_tick
    bcs return
    lda se_fold_index
    cmp se_fold_count
    bne @read
    lda se_fold_index+1
    cmp se_fold_count+1
    jeq found
@read:
    jsr se_fold_read
    jcs se_fold_fail
    ; Strict preorder permits early completion before the nextsection begins.
    SF_LT se_fold_query,se_fold_record+SF_SUMMARY,found
    SF_GE se_fold_query,se_fold_record+SF_END,advance
    lda se_fold_mode
    beq @eligible
    sec
    sbc #1
    eor se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    bne @hidden
@eligible:
    SF_COPY se_fold_index,se_fold_last,2
@hidden:
    lda se_fold_record+SF_FLAGS
    and #SF_COLLAPSED
    beq advance
    SF_LT se_fold_query,se_fold_record+SF_HIDDEN,advance
    ; Hidden descendants are unavailable evenif expanded. Expanded-only mode
    ; returnsnone here, overriding an earlier eligibleexpandedancestor.
    lda se_fold_mode
    cmp #1
    bne found
    lda #$FF
    sta se_fold_last
    sta se_fold_last+1
found:
    SF_COPY se_fold_last,se_fold_target,2
    jmp se_fold_done
advance:
    inc se_fold_index
    bne :+
    inc se_fold_index+1
:   lda #0
    clc
    rts

se_fold_locate_cancel:
    lda se_fold_busy
    beq @idle
    lda se_fold_job
    cmp #SF_LOCATE
    jeq @cancel
    jmp busy
@cancel:
    lda #SF_CANCEL
    sta se_fold_error
    lda #0
    sta se_fold_busy
@idle:
    lda #0
    clc
    rts
