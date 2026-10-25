.include "render/presentation.inc"
; C11-only fold projection. Persistent ends/bits publish with se_l_valid;
; foundation remains in owner3 phase until normal scoped navigation cleanup.
; se_l_index:0plain,1claim,2topquery,3CRquery,4scan,5CRready.
layout_fold_init:
    lda #0
    sta se_l_index
    sta se_ef_fold_rows
    sta se_ef_fold_rows+1
    sta se_ef_fold_rows+2
    ldx #1
@bind:
    lda se_ef_generation,x
    sta se_ef_projection_generation,x
    dex
    bpl @bind
    jsr se_ef_visible
    jeq layout_fold_ready
    inc se_l_index
layout_fold_claim:
    lda se_f_owner
    jne layout_fold_pending ;never inspect or overwrite a foreign phase
    jsr se_ef_visible
    jeq changed
    jsr se_ef_key_match
    jcs return
    lda #3
    sta se_f_owner
    lda #$81
    sta se_l_active
    lda #0
    sta se_fs_owned
    sta se_fs_active
    sta se_fold_busy
    sta se_i_ready ;phase8D00 no longercontains the persistent navigation index
    sta se_i_count
    sta se_n_cache_count
    ; Published map is trusted; reconstruct disposable foundation bindings.
    ldx #4
@token:
    lda se_ef_token,x
    sta se_fold_token,x
    sta se_fold_bound_token,x
    dex
    bpl @token
    ldx #1
@count:
    lda se_ef_count,x
    sta se_fold_count,x
    sta se_fold_bound_count,x
    dex
    bpl @count
    ldx #2
@length:
    lda se_ef_key+21,x
    sta se_fold_length,x
    sta se_fold_bound_length,x
    dex
    bpl @length
    ldx #3
@revision:
    lda se_ef_key+17,x
    sta se_fold_epoch,x
    sta se_fold_stamp,x
    dex
    bpl @revision
    lda #1
    sta se_fold_valid
    COPY24 se_hot_caret,se_fold_select_a
    COPY24 se_hot_caret,se_fold_select_b
    lda se_sel_mark
    beq :+
    COPY24 se_sel_anchor,se_fold_select_b
:   COPY24 se_l_scan,se_fold_query
    lda #0
    sta se_fold_mode ;normalize a top inside collapsed hidden source
    lda #2
    sta se_l_index
    lda #8
    jsr layout_fold_call
    jcs return
    jmp layout_fold_pending

layout_fold_resume:
    lda se_l_index
    jeq layout_fold_ready
    cmp #1
    jeq layout_fold_claim
    lda se_f_owner
    cmp #3
    jne changed
    jsr se_ef_visible
    jeq changed
    ldx #1
@generation:
    lda se_ef_generation,x
    cmp se_ef_projection_generation,x
    jne changed
    dex
    bpl @generation
    jsr se_ef_key_match
    jcs return
    lda se_l_index
    cmp #4
    jcs @source_guard
    lda #9
    jsr layout_fold_call ;one query record maximum; never sourcewalk this slice
    jcs return
    lda se_fold_busy
    jne layout_fold_pending
    lda se_l_index
    cmp #2
    bne @skip
    COPY24 se_fold_result,se_l_scan
    COPY24 se_fold_result,se_l_top
    COPY24 se_fold_result,se_v_top
    COPY24 se_fold_result,se_v_rows
    lda #4
    sta se_l_index
    bne layout_fold_pending
@skip:
    lda se_fold_hidden
    beq @cr_done
    CMP24 se_fold_result,se_l_scan
    jcc corrupt
    jeq corrupt
    COPY24 se_fold_result,se_l_scan
    jsr layout_fold_mark
@cr_done:
    lda #5
    sta se_l_index
    bne layout_fold_pending
@source_guard:
    lda #5
    jsr layout_fold_call ;authenticatefoldtoken/mappings evenonasource-onlyslice
    jcs return
    lda se_l_index
    cmp #4
    jeq layout_fold_ready
    cmp #5
    jne state
@boundary_ready:
    lda #4
    sta se_l_index
    lda #2
    clc
    rts
layout_fold_ready:
    lda #0
    clc
    rts
layout_fold_pending:
    lda #1
    clc
    rts
layout_fold_call:
    sta se_overlay_frame
    lda #18
    ldx #0
    jmp se_overlay_call

; A=13 forCR ornormalizedwidth forsoftwrap. CaptureendBEFORE anyskip.
layout_fold_boundary:
    pha
    jsr layout_fold_store
    pla
    cmp #13
    bne layout_fold_ready
    lda se_l_index
    cmp #4
    bne layout_fold_ready
    COPY24 se_v_pos,se_l_scan
    COPY24 se_v_pos,se_fold_query
    lda #1
    sta se_fold_mode ;forward skip onlywhen CR landed in collapsedhiddenrange
    lda #3
    sta se_l_index
    lda #8
    jsr layout_fold_call
    jcs return
    jmp layout_fold_pending
layout_fold_store:
    lda se_l_rows
    sec
    sbc #1
    sta se_l_end ;private byte temp, not painterstate while layout is active
    asl
    clc
    adc se_l_end
    tax
    ldy #0
@copy:
    lda se_v_pos,y
    sta se_ef_paint_ends,x
    inx
    iny
    cpy #3
    bcc @copy
    rts
layout_fold_mark:
    lda se_l_rows
    sec
    sbc #1
    pha
    and #7
    tay
    lda layout_fold_masks,y
    tay
    pla
    lsr
    lsr
    lsr
    tax
    tya
    ora se_ef_fold_rows,x
    sta se_ef_fold_rows,x
    rts
layout_fold_shift:
    ldx #0
@copy:
    lda se_ef_paint_ends+3,x
    sta se_ef_paint_ends,x
    inx
    cpx #63
    bcc @copy
    lsr se_ef_fold_rows+2
    ror se_ef_fold_rows+1
    ror se_ef_fold_rows
    rts
layout_fold_eof:
    jsr layout_fold_store
    ; Continue afterthecurrentrow throughallpaddingrows, eachEOF endidentical.
    cpx #66
    bcs @done
@row:
    ldy #0
@copy:
    lda se_v_pos,y
    sta se_ef_paint_ends,x
    inx
    iny
    cpy #3
    bcc @copy
    cpx #66
    bcc @row
@done:
    rts
.segment "RODATA"
layout_fold_masks: .byte 1,2,4,8,16,32,64,128
.segment "CODE"
