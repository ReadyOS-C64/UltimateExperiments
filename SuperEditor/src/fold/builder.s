.setcpu "6502"
.macpack longbranch
.include "fold/builder.inc"
.include "object/api.inc"
.ifdef SE_FOLD_EDITOR_SOURCE
.include "fold/source.inc"
.endif
.segment "FOLD_BUILD_PARSE"
; Candidate object is distinct from the immutable flat source logical object.
; Changed source snapshots reset expanded; exact unchanged snapshots may retain.
se_fb_begin:
    lda se_fb_busy
    ora se_fold_busy
    jne @busy
.ifdef SE_FOLD_EDITOR_SOURCE
    ; Only the editor coordinator may certify transformed hints (mode2).
    ; Flat-source same-token proof (mode1) cannot describe a merged gap view.
    lda se_fb_old_valid
    beq :+
    cmp #2
    beq :+
    lda #SF_BAD
    sec
    rts
:   jsr se_fs_begin
    bcc :+
    rts ; failed BEGIN owns no lease; never END another active client
:   SF_COPY se_fs_length,se_fold_length,3
    SF_COPY se_fs_revision,se_fold_epoch,4
.endif
    SF_COPY se_fb_source,se_fb_source_bound,5
    SF_COPY se_fold_token,se_fb_token_bound,5
    SF_COPY se_fold_length,se_fb_length_bound,3
    SF_COPY se_fold_epoch,se_fb_stamp,4
    SF_COPY se_fb_old_token,se_fb_old_bound,5
    SF_COPY se_fb_old_count,se_fb_old_count_bound,2
    SF_COPY se_fb_capacity,se_fold_count,2
    lda #0
    sta se_fb_keep
    sta se_fb_retained
    sta se_fb_retained+1
    sta se_fold_valid
    ; Clear every internal control, preserving caller inputs/bindings above.
    ldx #<(se_fb_state_size-(se_fb_busy-se_fb_state)-1)
@clear:
    sta se_fb_busy,x
    dex
    jpl @clear
    jsr se_fb_guard
    jcs se_fb_fail
    jsr se_fb_retention_begin
    jcs se_fb_fail
    jsr se_sm_init
    lda #1
    sta se_fb_busy
    sta se_fold_busy
    sta se_fb_phase
    lda #8
    sta se_fold_job
    clc
    rts
@busy:
    lda #SF_BUSY
    sec
    rts
se_fb_guard:
    ; Source revision/length/token and destination binding are immutable in-job.
    ldx #3
@epoch:
    lda se_fold_epoch,x
    cmp se_fb_stamp,x
    jne @stale
    dex
    jpl @epoch
    ldx #4
@tokens:
    lda se_fb_source,x
    cmp se_fb_source_bound,x
    jne @stale
    lda se_fold_token,x
    cmp se_fb_token_bound,x
    jne @stale
    dex
    jpl @tokens
    ldx #2
@length:
    lda se_fold_length,x
    cmp se_fb_length_bound,x
    jne @stale
    dex
    jpl @length
    lda se_fb_phase
    cmp #FB_VALIDATE
    beq @final_count
    lda se_fold_count
    cmp se_fb_capacity
    jne @stale
    lda se_fold_count+1
    cmp se_fb_capacity+1
    jne @stale
    jmp @guard
@final_count:
    lda se_fold_count
    cmp se_fb_count
    jne @stale
    lda se_fold_count+1
    cmp se_fb_count+1
    jne @stale
@guard:
    jsr se_fold_guard
    jcs @return
.ifdef SE_FOLD_EDITOR_SOURCE
    jsr se_fs_guard
    jcs @return
.else
    SF_COPY se_fb_source,se_object_id,5
    jsr se_object_validate
    jcs @return
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    jeq @bad
    lda object_size_lo,x
    cmp se_fold_length
    jne @stale
    lda object_size_mid,x
    cmp se_fold_length+1
    jne @stale
    lda object_size_hi,x
    cmp se_fold_length+2
    jne @stale
.endif
    lda se_fb_keep
    beq @ok
    jmp se_fb_old_guard
@ok:
    clc
@return:
    rts
@stale:
    lda #SF_STALE
    sec
    rts
@bad:
    lda #SF_BAD
    sec
    rts
se_fb_fail:
    sta se_fb_error
.ifdef SE_FOLD_EDITOR_SOURCE
    pha
    jsr se_fs_end
    pla
.endif
    pha
    lda #0
    sta se_fb_busy
    pla
    jmp se_fold_fail
se_fb_cancel:
    lda se_fb_busy
    jeq @done
    lda #SF_CANCEL
    jsr se_fb_fail
@done:
    clc
    rts
se_fb_step:
    lda se_fb_busy
    jeq @bad
    jsr se_fb_guard
    jcs se_fb_fail
    lda se_fb_phase
    cmp #FB_FILTER
    jeq se_fb_filter_step
    cmp #FB_MARK
    jeq se_fb_mark_step
    cmp #FB_COMPACT
    jeq se_fb_compact_step
    cmp #FB_RETAIN_LOAD
    jeq se_fb_retain_load
    cmp #FB_RETAIN_MATCH
    jeq se_fb_retain_match
    cmp #FB_VALIDATE
    jeq @validate
    jmp se_fb_parse_step
@validate:
    jsr se_fold_validate_step
    jcs se_fb_fail
    lda se_fold_busy
    jne @return
.ifdef SE_FOLD_EDITOR_SOURCE
    jsr se_fs_end
.endif
    lda #0
    sta se_fb_busy
    sta se_fb_error
@return:
    clc
    rts
@bad:
    lda #SF_BAD
    jmp se_fb_fail

se_fb_parse_step:
    lda se_fb_phase
    cmp #FB_EVENT
    jeq event
    cmp #FB_EOF
    jeq finish
    ; Consume no more than32 bytes, stopping at the first complete block event.
    lda se_fb_used
    cmp se_fb_chunk
    jeq refill
    lda #32
    sta se_fb_slot
@feed:
    ldx se_fb_used
    lda se_fb_buffer,x
    jsr se_sm_feed
    inc se_fb_used
    lda se_sm_ready
    jne @event
    lda se_fb_used
    cmp se_fb_chunk
    jeq @return
    dec se_fb_slot
    jne @feed
@return:
    clc
    rts
@event:
    lda #FB_EVENT
    sta se_fb_phase
    clc
    rts
refill:
    lda se_sm_pos
    cmp se_fold_length
    jne @read
    lda se_sm_pos+1
    cmp se_fold_length+1
    jne @read
    lda se_sm_pos+2
    cmp se_fold_length+2
    jne @read
    jsr se_sm_finish
    lda #1
    sta se_fb_eof
    lda se_sm_ready
    jeq @eof
    lda #FB_EVENT
    sta se_fb_phase
    clc
    rts
@eof:
    lda #FB_EOF
    sta se_fb_phase
    clc
    rts
@read:
.ifdef SE_FOLD_EDITOR_SOURCE
    SF_COPY se_sm_pos,se_fs_offset,3
    lda #128
    sta se_fs_count
    lda #<se_fb_buffer
    sta se_fs_buffer
    lda #>se_fb_buffer
    sta se_fs_buffer+1
    jsr se_fs_read
    jcs se_fb_fail
    lda se_fs_done
    jeq incomplete ; offset<EOF requires actual forward progress
    sta se_fb_chunk
    lda #0
    sta se_fb_used
    clc
    rts
.else
    SF_COPY se_fb_source,se_object_id,5
    SF_COPY se_sm_pos,se_object_offset,3
    sec
    lda se_fold_length
    sbc se_sm_pos
    sta se_object_length
    lda se_fold_length+1
    sbc se_sm_pos+1
    sta se_object_length+1
    lda se_fold_length+2
    sbc se_sm_pos+2
    jne @full
    lda se_object_length+1
    jne @full
    lda se_object_length
    cmp #128
    jcc @size
@full:
    lda #128
@size:
    sta se_fb_chunk
    sta se_object_length
    lda #0
    sta se_object_length+1
    sta se_fb_used
    lda #<se_fb_buffer
    sta se_object_c64
    lda #>se_fb_buffer
    sta se_object_c64+1
    lda #1
    jsr se_object_copy
    jcs se_fb_fail
    clc
    rts
.endif

event:
    lda se_sm_kind
    cmp #SM_HEADING
    jeq heading
    cmp #SM_CODE_OPEN
    jeq code_open
    cmp #SM_CODE_CLOSE
    jeq code_close
    cmp #SM_REGION_OPEN
    jeq region_open
    cmp #SM_REGION_CLOSE
    jeq region_close
    jmp event_done
heading:
    ldx se_fb_heads
    jeq @open
    dex
    lda FB_H_LEVEL,x
    cmp se_sm_level
    jcc @open
    dec se_fb_heads
    txa
    asl
    tax
    lda FB_H_INDEX,x
    sta se_fb_close
    lda FB_H_INDEX+1,x
    sta se_fb_close+1
    SF_COPY se_sm_start,se_fb_end,3
    jsr close_heading
    jcs se_fb_fail
    clc
    rts
@open:
    lda #SF_HEADING
    jsr open_record
    jcs se_fb_fail
    ldx se_fb_heads
    lda se_sm_level
    sta FB_H_LEVEL,x
    txa
    asl
    tax
    lda se_fold_index
    sta FB_H_INDEX,x
    lda se_fold_index+1
    sta FB_H_INDEX+1,x
    inc se_fb_heads
    jmp event_done
code_open:
    lda #SF_CODE
    jsr open_record
    jcs se_fb_fail
    SF_COPY se_fold_index,se_fb_code_index,2
    lda #1
    sta se_fb_code
    jmp event_done
code_close:
    lda se_fb_code
    jeq incomplete
    SF_COPY se_fb_code_index,se_fb_close,2
    SF_COPY se_sm_pos,se_fb_end,3
    jsr close_explicit
    jcs se_fb_fail
    lda #0
    sta se_fb_code
    jmp event_done
region_open:
    lda se_fb_regions
    cmp #16
    jcs depth_error
    lda #SF_REGION
    jsr open_record
    jcs se_fb_fail
    lda se_fb_regions
    asl
    tax
    lda se_fold_index
    sta FB_R_INDEX,x
    lda se_fold_index+1
    sta FB_R_INDEX+1,x
    inc se_fb_regions
    jmp event_done
region_close:
    lda se_fb_regions
    jeq incomplete
    dec se_fb_regions
    lda se_fb_regions
    asl
    tax
    lda FB_R_INDEX,x
    sta se_fb_close
    lda FB_R_INDEX+1,x
    sta se_fb_close+1
    SF_COPY se_sm_pos,se_fb_end,3
    jsr close_explicit
    jcs se_fb_fail
    jmp event_done
event_done:
    SM_INC24 se_fb_line
    lda se_fb_eof
    jeq @parse
    lda #FB_EOF
    jne @set
@parse:
    lda #FB_PARSE
@set:
    sta se_fb_phase
    clc
    rts
finish:
    lda se_fb_code
    ora se_fb_regions
    jne incomplete
    lda se_fb_heads
    jeq @filter
    dec se_fb_heads
    lda se_fb_heads
    asl
    tax
    lda FB_H_INDEX,x
    sta se_fb_close
    lda FB_H_INDEX+1,x
    sta se_fb_close+1
    SF_COPY se_fold_length,se_fb_end,3
    jsr close_heading
    jcs se_fb_fail
    clc
    rts
@filter:
    lda #0
    sta se_fb_scan
    sta se_fb_scan+1
    sta se_fb_heads
    sta se_fb_regions
    lda #FB_FILTER
    sta se_fb_phase
    clc
    rts
incomplete:
    lda #FB_INCOMPLETE
    jmp se_fb_fail
depth_error:
    lda #FB_DEPTH
    jmp se_fb_fail
open_record:
    pha
    lda se_fb_raw_count+1
    cmp se_fold_count+1
    bcc @room
    bne @full
    lda se_fb_raw_count
    cmp se_fold_count
    bcc @room
@full:
    pla
    lda #FB_SPACE
    sec
    rts
@room:
    SF_COPY se_fb_raw_count,se_fold_index,2
    lda #0
    ldx #31
@clear:
    sta se_fold_record,x
    dex
    jpl @clear
    pla
    sta se_fold_record+SF_KIND
    cmp #SF_HEADING
    jne @anchors
    lda se_sm_level
    sta se_fold_record+SF_LEVEL
@anchors:
    SF_COPY se_sm_start,se_fold_record+SF_SUMMARY,3
    SF_COPY se_sm_pos,se_fold_record+SF_HIDDEN,3
    SF_COPY se_fb_line,se_fold_record+SF_LINES,3
    lda #$FF
    sta se_fold_record+SF_PARENT
    sta se_fold_record+SF_PARENT+1
    jsr se_fold_write
    jcs @return
    inc se_fb_raw_count
    jne @return
    inc se_fb_raw_count+1
@return:
    rts
close_heading:
    ; hidden-line count = current logical ordinal - opening ordinal -1.
    jsr load_close
    jcs @return
    sec
    lda se_fb_line
    sbc se_fold_record+SF_LINES
    sta se_fold_record+SF_LINES
    lda se_fb_line+1
    sbc se_fold_record+SF_LINES+1
    sta se_fold_record+SF_LINES+1
    lda se_fb_line+2
    sbc se_fold_record+SF_LINES+2
    sta se_fold_record+SF_LINES+2
    sec
    lda se_fold_record+SF_LINES
    sbc #1
    sta se_fold_record+SF_LINES
    lda se_fold_record+SF_LINES+1
    sbc #0
    sta se_fold_record+SF_LINES+1
    lda se_fold_record+SF_LINES+2
    sbc #0
    sta se_fold_record+SF_LINES+2
    jmp write_close
@return:
    rts
close_explicit:
    jsr load_close
    jcs close_return
    sec
    lda se_fb_line
    sbc se_fold_record+SF_LINES
    sta se_fold_record+SF_LINES
    lda se_fb_line+1
    sbc se_fold_record+SF_LINES+1
    sta se_fold_record+SF_LINES+1
    lda se_fb_line+2
    sbc se_fold_record+SF_LINES+2
    sta se_fold_record+SF_LINES+2
write_close:
    SF_COPY se_fb_end,se_fold_record+SF_END,3
    jmp se_fold_write
close_return:
    rts
load_close:
    SF_COPY se_fb_close,se_fold_index,2
    jmp se_fold_read
