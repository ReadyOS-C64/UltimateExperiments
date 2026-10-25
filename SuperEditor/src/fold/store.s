.setcpu "6502"
.macpack longbranch
.include "fold/api.inc"
.include "object/api.inc"
.segment "FOLD_STORE"
; Public state is a caller-owned disposable/checkpointable frame, not resident BSS.
; Every operation authenticates logical token, provider epoch and all extents.
se_fold_guard:
    SF_COPY se_fold_token,se_object_id,5
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    jne @bad
    lda se_fold_count+1
    cmp #$80
    jcc @size
    jne @bad
    lda se_fold_count
    jne @bad
@size:
    lda se_fold_count
    sta se_fold_temp
    lda se_fold_count+1
    sta se_fold_temp+1
    lda #0
    sta se_fold_temp+2
    ldy #5
@shift:
    asl se_fold_temp
    rol se_fold_temp+1
    rol se_fold_temp+2
    dey
    jne @shift
    lda object_size_hi,x
    cmp se_fold_temp+2
    jcc @bad
    jne @ok
    lda object_size_mid,x
    cmp se_fold_temp+1
    jcc @bad
    jne @ok
    lda object_size_lo,x
    cmp se_fold_temp
    jcc @bad
@ok:
    clc
@return:
    rts
@bad:
    lda #SF_BAD
    sec
    rts
; READ/WRITE one32-byte logical record. Index<count is checked before DMA.
se_fold_read:
    lda #1
    bne copy
se_fold_write:
    lda #0
copy:
    pha
    lda se_fold_index+1
    cmp se_fold_count+1
    jcc @offset
    jne @bad
    lda se_fold_index
    cmp se_fold_count
    jcs @bad
@offset:
    SF_COPY se_fold_token,se_object_id,5
    lda se_fold_index
    sta se_object_offset
    lda se_fold_index+1
    sta se_object_offset+1
    lda #0
    sta se_object_offset+2
    ldx #5
@shift:
    asl se_object_offset
    rol se_object_offset+1
    rol se_object_offset+2
    dex
    jne @shift
    lda #<se_fold_record
    sta se_object_c64
    lda #>se_fold_record
    sta se_object_c64+1
    lda #32
    sta se_object_length
    lda #0
    sta se_object_length+1
    pla
    jmp se_object_copy
@bad:
    pla
    lda #SF_BAD
    sec
    rts
se_fold_fail:
    sta se_fold_error
    lda #0
    sta se_fold_busy
    sta se_fold_valid
    lda se_fold_error
    sec
    rts
se_fold_done:
    lda #0
    sta se_fold_busy
    sta se_fold_error
    clc
    rts
; STEP gate: rejects changed source revision even halfway through a scan.
se_fold_tick:
    ldx #3
@epoch:
    lda se_fold_epoch,x
    cmp se_fold_stamp,x
    jne @stale
    dex
    jpl @epoch
    ldx #4
@token:
    lda se_fold_token,x
    cmp se_fold_bound_token,x
    jne @stale
    dex
    jpl @token
    ldx #1
@count:
    lda se_fold_count,x
    cmp se_fold_bound_count,x
    jne @stale
    dex
    jpl @count
    ldx #2
@length:
    lda se_fold_length,x
    cmp se_fold_bound_length,x
    jne @stale
    dex
    jpl @length
    jsr se_fold_guard
    jcs @fail
    clc
    rts
@stale:
    lda #SF_STALE
@fail:
    jmp se_fold_fail
se_fold_invalidate:
    lda #SF_STALE
    jmp se_fold_fail
se_fold_cancel:
    lda se_fold_busy
    jeq @done
    lda se_fold_job
    cmp #SF_QUERY
    jeq @keep
    lda #0
    sta se_fold_valid
@keep:
    lda #SF_CANCEL
    sta se_fold_error
@done:
    lda #0
    sta se_fold_busy
    clc
    rts
