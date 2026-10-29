.setcpu "6502"
.macpack longbranch
.include "fold/builder.inc"
.include "object/api.inc"
.segment "FOLD_BUILD_RETAIN"
; Retain only collapsed bits from a caller-certified old map of the exact same
; immutable source token/length/revision and an exact freshly parsed identity.
; Saved inner caret/motion do not transfer. Changed snapshots reset expanded.
se_fb_retention_begin:
    lda #0
    sta se_fb_keep
    lda se_fb_old_valid
    jeq @done
    ldx #4
@source:
    lda se_fb_old_source,x
    cmp se_fb_source,x
    jne @done
    dex
    jpl @source
    ldx #3
@epoch:
    lda se_fb_old_epoch,x
    cmp se_fold_epoch,x
    jne @done
    dex
    jpl @epoch
    ldx #2
@length:
    lda se_fb_old_length,x
    cmp se_fold_length,x
    jne @done
    dex
    jpl @length
    ; Old/candidate objects must be distinct before any staging write.
    ldx #4
@distinct:
    lda se_fb_old_token,x
    cmp se_fold_token,x
    jne @admit
    dex
    jpl @distinct
    lda #SF_BAD
    sec
    rts
@admit:
.ifdef SE_FOLD_EDITOR_SOURCE
    lda se_fb_old_valid ;freeze the caller's certified mode for all later slices
.else
    lda #1
.endif
    sta se_fb_keep
    jmp se_fb_old_guard
@done:
    clc
    rts
se_fb_old_guard:
    ldx #4
@token:
    lda se_fb_old_token,x
    cmp se_fb_old_bound,x
    jne @stale
    dex
    jpl @token
    ldx #1
@count:
    lda se_fb_old_count,x
    cmp se_fb_old_count_bound,x
    jne @stale
    dex
    jpl @count
    SF_COPY se_fb_old_token,se_object_id,5
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    jne @bad
    lda se_fb_old_count+1
    cmp #$80
    jcc @size
    jne @bad
    lda se_fb_old_count
    jne @bad
@size:
    lda se_fb_old_count
    sta se_fold_temp
    lda se_fb_old_count+1
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
@stale:
    lda #SF_STALE
    sec
    rts
se_fb_finish_build:
    lda se_fb_keep
    jeq se_fb_validate_candidate
    lda #0
    sta se_fb_scan
    sta se_fb_scan+1
    sta se_fb_close
    sta se_fb_close+1
    lda #FB_RETAIN_LOAD
    sta se_fb_phase
    clc
    rts
se_fb_validate_candidate:
    SF_COPY se_fb_count,se_fold_count,2
    lda #0
    sta se_fold_busy
    jsr se_fold_validate_begin
    jcs se_fb_fail
    lda #FB_VALIDATE
    sta se_fb_phase
    clc
    rts
se_fb_retain_load:
    lda se_fb_scan
    cmp se_fb_count
    jne @old
    lda se_fb_scan+1
    cmp se_fb_count+1
    jeq se_fb_validate_candidate
@old:
    lda se_fb_close
    cmp se_fb_old_count
    jne @read
    lda se_fb_close+1
    cmp se_fb_old_count+1
    jeq se_fb_validate_candidate
@read:
    SF_COPY se_fb_scan,se_fold_index,2
    jsr se_fold_read
    jcs se_fb_fail
    lda #FB_RETAIN_MATCH
    sta se_fb_phase
    clc
    rts
se_fb_retain_match:
    lda se_fb_close
    cmp se_fb_old_count
    bne :+
    lda se_fb_close+1
    cmp se_fb_old_count+1
    jeq se_fb_validate_candidate
:
    ; One old-record READ, optional one candidate WRITE. Fresh record survives
    ; in the common buffer between calls; no cursor, stack or code checkpoint.
    SF_COPY se_fb_old_token,se_object_id,5
    lda se_fb_close
    sta se_object_offset
    lda se_fb_close+1
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
    lda #<se_fb_old_record
    sta se_object_c64
    lda #>se_fb_old_record
    sta se_object_c64+1
    lda #32
    sta se_object_length
    lda #0
    sta se_object_length+1
    lda #1
    jsr se_object_copy
    jcs se_fb_fail
    SF_LT se_fb_old_record,se_fold_record,@old_next
    SF_LT se_fold_record,se_fb_old_record,@new_next
.ifdef SE_FOLD_EDITOR_SOURCE
    lda se_fb_keep
    cmp #2
    bne @exact
    ; Hints have transformed canonical ranges, but obsolete row counts and
    ; numeric ancestry. Fresh parsing alone owns PARENT/DEPTH/LINES.
    ldx #8
@range:
    lda se_fb_old_record,x
    cmp se_fold_record,x
    jne @both_next
    dex
    jpl @range
    lda se_fb_old_record+SF_KIND
    cmp se_fold_record+SF_KIND
    jne @both_next
    lda se_fb_old_record+SF_LEVEL
    cmp se_fold_record+SF_LEVEL
    jne @both_next
    jmp @flags
@exact:
.endif
    ldx #12
@identity:
    lda se_fb_old_record,x
    cmp se_fold_record,x
    jne @both_next
    dex
    jpl @identity
    ldx #3
@linelevel:
    lda se_fb_old_record+SF_LINES,x
    cmp se_fold_record+SF_LINES,x
    jne @both_next
    dex
    jpl @linelevel
.ifdef SE_FOLD_EDITOR_SOURCE
@flags:
.endif
    lda se_fb_old_record+SF_FLAGS
    and #$FC
    jne @both_next
    lda se_fb_old_record+SF_FLAGS
    and #SF_COLLAPSED
    jeq @both_next
    sta se_fold_record+SF_FLAGS
    SF_COPY se_fb_scan,se_fold_index,2
    jsr se_fold_write
    jcs se_fb_fail
    inc se_fb_retained
    jne @both_next
    inc se_fb_retained+1
@both_next:
    inc se_fb_close
    jne @new_next
    inc se_fb_close+1
@new_next:
    inc se_fb_scan
    bne :+
    inc se_fb_scan+1
:   lda #FB_RETAIN_LOAD
    sta se_fb_phase
    clc
    rts
@old_next:
    inc se_fb_close
    bne :+
    inc se_fb_close+1
:   clc
    rts
