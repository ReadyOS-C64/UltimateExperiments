; Read-only R24 leaf callable from GEOS C coordinators, no same-slot nesting.
.setcpu "6502"
.macpack longbranch
GFQ_IMPLEMENTATION=1
.include "render/geos/fold-query.inc"
.include "fold/api.inc"
.include "object/api.inc"
.import se_f_owner,se_ef_valid,se_ef_token,se_ef_count,se_ef_generation,se_ef_key
.import se_ef_key_match,se_hot_caret,se_sel_mark,se_sel_anchor,se_view_init,se_v_length
.export se_gfq_begin,se_gfq_step,se_gfq_cancel
.segment "CODE"
se_gfq_begin:
    jsr owner
    jcs return
    lda GFQ_ACTIVE
    jne busy
    lda GFQ_MODE
    cmp #2
    jcs bad
    lda se_ef_valid
    bne @published
    jsr se_view_init
    jcs fail
    SF_LT se_v_length,GFQ_QUERY,bad
    jmp visible
@published:
    jsr current
    jcs fail
    SF_COPY se_ef_token,GFQ_TOKEN,5
    SF_COPY se_ef_count,GFQ_COUNT,2
    SF_COPY se_ef_generation,GFQ_GENERATION,2
    SF_COPY se_ef_key+21,GFQ_LENGTH,3
    SF_LT GFQ_LENGTH,GFQ_QUERY,bad
    SF_COPY GFQ_QUERY,GFQ_BOUND_QUERY,3
    lda GFQ_MODE
    sta GFQ_BOUND_MODE
    SF_COPY se_hot_caret,GFQ_SELECT_A,3
    SF_COPY se_hot_caret,GFQ_SELECT_B,3
    lda se_sel_mark
    sta GFQ_MARK
    beq @no_anchor
    SF_COPY se_sel_anchor,GFQ_SELECT_B,3
@no_anchor:
    jsr typed
    jcs fail
    lda #0
    sta GFQ_INDEX
    sta GFQ_INDEX+1
    sta GFQ_ERROR
    lda #1
    sta GFQ_ACTIVE
pending:
    lda #1
    clc
return:
    rts
se_gfq_step:
    jsr owner
    jcs return
    lda GFQ_ACTIVE
    cmp #1
    jne bad
    jsr current
    jcs fail
    ldx #4
@token:
    lda se_ef_token,x
    cmp GFQ_TOKEN,x
    jne stale
    dex
    bpl @token
    ldx #1
@publication:
    lda se_ef_count,x
    cmp GFQ_COUNT,x
    jne stale
    lda se_ef_generation,x
    cmp GFQ_GENERATION,x
    jne stale
    dex
    bpl @publication
    ldx #2
@inputs:
    lda GFQ_QUERY,x
    cmp GFQ_BOUND_QUERY,x
    jne stale
    lda se_hot_caret,x
    cmp GFQ_SELECT_A,x
    jne stale
    lda se_ef_key+21,x
    cmp GFQ_LENGTH,x
    jne stale
    dex
    bpl @inputs
    lda GFQ_MODE
    cmp GFQ_BOUND_MODE
    jne stale
    lda se_sel_mark
    cmp GFQ_MARK
    jne stale
    lda GFQ_MARK
    beq @guard
    ldx #2
@anchor:
    lda se_sel_anchor,x
    cmp GFQ_SELECT_B,x
    jne stale
    dex
    bpl @anchor
@guard:
    jsr typed
    jcs fail
    lda GFQ_INDEX+1
    cmp GFQ_COUNT+1
    jcc @read
    jne bad
    lda GFQ_INDEX
    cmp GFQ_COUNT
    jcc @read
    jne bad
    jmp visible
@read:
    ; Exactly one record32, index*32, through checked typed object service.
    SF_COPY GFQ_TOKEN,se_object_id,5
    lda GFQ_INDEX
    sta se_object_offset
    lda GFQ_INDEX+1
    sta se_object_offset+1
    lda #0
    sta se_object_offset+2
    ldx #5
@offset:
    asl se_object_offset
    rol se_object_offset+1
    rol se_object_offset+2
    dex
    bne @offset
    lda #<GFQ_RECORD
    sta se_object_c64
    lda #>GFQ_RECORD
    sta se_object_c64+1
    lda #32
    sta se_object_length
    lda #0
    sta se_object_length+1
    lda #1
    jsr se_object_copy
    jcs fail
    ; Structural publication is trusted, but fail closed on corrupt scanned
    ; endpoints/flags/kind/reserved bytes rather than publishing invalid jumps.
    SF_GE GFQ_RECORD+SF_SUMMARY,GFQ_RECORD+SF_HIDDEN,bad
    SF_GE GFQ_RECORD+SF_HIDDEN,GFQ_RECORD+SF_END,bad
    SF_LT GFQ_LENGTH,GFQ_RECORD+SF_END,bad
    lda GFQ_RECORD+SF_KIND
    cmp #1
    jcc bad
    cmp #4
    jcs bad
    lda GFQ_RECORD+SF_FLAGS
    and #$FC
    jne bad
    lda GFQ_RECORD+SF_FLAGS
    and #SF_SAVED
    beq @depth
    lda GFQ_RECORD+SF_FLAGS
    and #SF_COLLAPSED
    jeq bad
    SF_LT GFQ_RECORD+SF_CARET,GFQ_RECORD+SF_HIDDEN,bad
    SF_GE GFQ_RECORD+SF_CARET,GFQ_RECORD+SF_END,bad
@depth:
    lda GFQ_RECORD+SF_DEPTH
    cmp #16
    jcs bad
    lda GFQ_RECORD+SF_KIND
    cmp #SF_HEADING
    bne @other_level
    lda GFQ_RECORD+SF_LEVEL
    jeq bad
    cmp #7
    jcs bad
    bcc @reserved
@other_level:
    lda GFQ_RECORD+SF_LEVEL
    jne bad
@reserved:
    ldx #31
@zero:
    lda GFQ_RECORD,x
    jne bad
    dex
    cpx #24
    bne @zero
    lda GFQ_INDEX
    ora GFQ_INDEX+1
    beq @ordered
    SF_GE GFQ_LAST,GFQ_RECORD+SF_SUMMARY,bad
@ordered:
    SF_COPY GFQ_RECORD+SF_SUMMARY,GFQ_LAST,3
    SF_LT GFQ_QUERY,GFQ_RECORD+SF_SUMMARY,visible
    lda GFQ_RECORD+SF_FLAGS
    and #SF_COLLAPSED
    jeq next
    SF_LT GFQ_QUERY,GFQ_RECORD+SF_HIDDEN,next
    SF_GE GFQ_QUERY,GFQ_RECORD+SF_END,next
    SF_COPY GFQ_RECORD+SF_SUMMARY,GFQ_SUMMARY,3
    SF_COPY GFQ_RECORD+SF_HIDDEN,GFQ_BODY,3
    SF_COPY GFQ_RECORD+SF_END,GFQ_END,3
    lda #1
    sta GFQ_HIDDEN
    lda #0
    sta GFQ_SELECTED
    SF_LT GFQ_SELECT_A,GFQ_SELECT_B,@forward_selection
    SF_LT GFQ_SELECT_B,GFQ_SELECT_A,@backward_selection
    jmp project
@forward_selection:
    SF_GE GFQ_SELECT_A,GFQ_END,project
    SF_GE GFQ_BODY,GFQ_SELECT_B,project
    jmp selected
@backward_selection:
    SF_GE GFQ_SELECT_B,GFQ_END,project
    SF_GE GFQ_BODY,GFQ_SELECT_A,project
selected:
    lda #1
    sta GFQ_SELECTED
project:
    lda GFQ_MODE
    beq @summary
    SF_COPY GFQ_END,GFQ_RESULT,3
    jmp done
@summary:
    SF_COPY GFQ_SUMMARY,GFQ_RESULT,3
    jmp done
next:
    inc GFQ_INDEX
    bne :+
    inc GFQ_INDEX+1
:
    jmp pending
visible:
    SF_COPY GFQ_QUERY,GFQ_RESULT,3
    lda #0
    sta GFQ_HIDDEN
    sta GFQ_SELECTED
    ldx #8
@clear:
    sta GFQ_SUMMARY,x
    dex
    bpl @clear
done:
    lda #0
    sta GFQ_ACTIVE
    sta GFQ_ERROR
    clc
    rts
se_gfq_cancel:
    jsr owner
    bcs return_far
    lda #0
    sta GFQ_ACTIVE
    sta GFQ_ERROR
    clc
return_far:
    rts
owner:
    lda se_f_owner
    cmp #4
    beq owner_ok
busy:
    lda #SF_BUSY
    sec
    rts
owner_ok:
    clc
    rts
current:
    lda se_ef_valid
    beq stale
    jmp se_ef_key_match
; Authenticates full typedtoken +allmappings +committed count*32 capacity.
typed:
    SF_COPY GFQ_TOKEN,se_object_id,5
    jsr se_object_validate
    bcs return_far
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    bne bad
    lda GFQ_COUNT+1
    cmp #$80
    bcc @length
    bne bad
    lda GFQ_COUNT
    bne bad
@length:
    lda GFQ_COUNT
    sta se_object_offset
    lda GFQ_COUNT+1
    sta se_object_offset+1
    lda #0
    sta se_object_offset+2
    ldy #5
@shift:
    asl se_object_offset
    rol se_object_offset+1
    rol se_object_offset+2
    dey
    bne @shift
    lda object_size_hi,x
    cmp se_object_offset+2
    bcc bad
    bne @ok
    lda object_size_mid,x
    cmp se_object_offset+1
    bcc bad
    bne @ok
    lda object_size_lo,x
    cmp se_object_offset
    bcc bad
@ok:
    clc
    rts
stale:
    lda #SF_STALE
    bne fail
bad:
    lda #SF_BAD
fail:
    sta GFQ_ERROR
    pha
    lda #0
    sta GFQ_ACTIVE
    pla
    sec
    rts
