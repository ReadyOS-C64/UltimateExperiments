.include "render/presentation.inc"
grid_source:
    jsr grid_preflight
    jcs grid_return
    lda se_l_need_wrap
    jne grid_zero
    ; Admission proves the correct R leaf is available before any pixels.
    lda #GRID_ADMIT
    jsr grid_call
    jcs grid_return
    jsr style_context
    lda se_e_ui
    bne @style_ready ;publish an already-requested UI frame before background work
    lda se_st_request
    cmp #1
    bne @style_ready
    lda #ST_PENDING
    clc
    rts ;plan first: no bitmap cell or cache publication has happened yet
@style_ready:
    ldx #0
    lda se_e_ui
    cmp #3
    beq @popup
    cmp #1
    bne @cache_begin
    lda se_e_menu
    beq @cache_begin
@popup:
    inx
@cache_begin:
    lda g_width
    jsr se_grid_cache_begin
    jsr se_selection_range
    lda #0
    sta se_v_seen
    sta g_row
    ldx #NR_SIZE-1
@clear:
    sta G_NR,x
    dex
    bpl @clear
    lda g_width
    sta G_NR+NR_MODE
    sta G_NR+NR_COUNT
    lda #6
    sta G_NR+NR_BACKGROUND
    lda #$60
    sta G_NR+NR_BITMAP+1
    lda #$40
    sta G_NR+NR_ATTRIBUTES+1
    lda #$A8
    sta G_NR+NR_FONT+1
    lda #<G_CHARS
    sta G_NR+NR_CHARACTERS
    lda #>G_CHARS
    sta G_NR+NR_CHARACTERS+1
    lda #<G_ROLES
    sta G_NR+NR_ROLES
    lda #>G_ROLES
    sta G_NR+NR_ROLES+1
    lda #<G_FLAGS
    sta G_NR+NR_FLAGS
    lda #>G_FLAGS
    sta G_NR+NR_FLAGS+1
    lda #<grid_palette
    sta G_NR+NR_PALETTE
    lda #>grid_palette
    sta G_NR+NR_PALETTE+1
@row:
    ldx g_row
    lda g_width
    cmp #60
    beq @style60
    txa
    clc
    adc #22
    tax
@style60:
    lda grid_style_low,x
    sta g_style_ptr
    lda grid_style_high,x
    sta g_style_ptr+1
    jsr grid_bounds
    COPY24 g_start,g_pos
    ldy g_index
    ldx #0
@end:
    lda g_ends,y
    sta g_end,x
    iny
    inx
    cpx #3
    bcc @end
    lda se_l_mode
    beq @positioned
    SUB24 g_end,g_start,g_delta
    CMP24 se_l_pan,g_delta
    bcc @pan
    beq @pan
    ; Manual pan beyond this line is entirely blank. Clamp its synthetic
    ; position instead of allowing24-bit addition/increment to wrap to zero.
    COPY24 g_end,g_pos
    inc g_pos
    bne @positioned
    inc g_pos+1
    bne @positioned
    inc g_pos+2
    jmp @positioned
@pan:
    ADD24 g_pos,se_l_pan,g_pos
@positioned:
    lda #0
    sta g_col
@cell:
    ldx g_col
    lda #0
    sta G_ROLES,x
    sta G_FLAGS,x
    lda #32
    sta G_CHARS,x
    CMP24 g_pos,g_end
    bcc @source
    beq @mark
    jmp @advance
@source:
    COPY24 g_pos,se_v_pos
    jsr se_view_peek
    jcs grid_return
    ldx g_col
    sta G_CHARS,x
    lda se_st_valid
    beq @mark
    lda g_style_ptr
    sta text_ptr
    lda g_style_ptr+1
    sta text_ptr+1
    ldy g_col
    lda (text_ptr),y
    pha
    and #$70
    lsr
    lsr
    lsr
    lsr
    tax
    lda grid_mask_roles,x
    bne @role
    pla
    pha
    bmi @heading
    and #15
    tax
    lda grid_color_roles,x
    jmp @role
@heading:
    ; An unmodified heading has the priority of strong text. Inline colors
    ; retain their own role, with heading reversal handled separately below.
    lda #2
@role:
    ldx g_col
    sta G_ROLES,x
    pla
    bpl @mark
    lda #NR_INVERSE
    sta G_FLAGS,x
@mark:
    jsr grid_fold_marker
    lda se_sel_mark
    beq @caret
    CMP24 g_pos,se_sel_start
    bcc @caret
    CMP24 g_pos,se_sel_end
    bcs @caret
    ldx g_col
    lda G_FLAGS,x
    ora #NR_SELECTED
    sta G_FLAGS,x
@caret:
    lda se_v_seen
    bne @advance
    CMP24 g_pos,se_hot_caret
    bne @advance
    lda #1
    sta se_v_seen
    lda g_row
    sta se_v_caret_row
    lda g_col
    sta se_v_caret_col
    tax
    lda G_FLAGS,x
    ora #NR_CARET
    sta G_FLAGS,x
@advance:
    inc g_pos
    bne :+
    inc g_pos+1
    bne :+
    inc g_pos+2
:
    inc g_col
    lda g_col
    cmp g_width
    jcc @cell
    lda g_row
    clc
    adc #2
    jsr se_grid_cache_row
    cmp #0
    beq @next_row
    lda g_row
    clc
    adc #2
    sta G_NR+NR_ROW
    lda #GRID_ROW
    jsr grid_call
    bcs grid_return
    lda g_row
    clc
    adc #2
    jsr se_grid_cache_commit
@next_row:
    inc g_row
    lda g_row
    cmp #22
    jcc @row
    jsr tui_editor_chrome40
    jsr se_grid_cache_finish
    jmp grid_zero
; Frame pointer belongs to8880 workspace, survives loading the R leaf.
grid_call:
    sta se_overlay_frame
    lda #<G_NR
    sta se_overlay_frame+1
    lda #>G_NR
    sta se_overlay_frame+2
    lda g_backend
    ldx #0
    jmp se_overlay_call
grid_zero:
    lda #0
    clc
grid_return:
    rts
; A folded opener keeps every source glyph. Its CR/EOF blank carries the
; inverse '+' summary marker; selection/caret flags are applied by the caller.
grid_fold_marker:
    jsr se_ef_visible
    beq @done
    CMP24 g_pos,g_end
    bne @done
    lda g_row
    jsr se_ef_summary
    beq @done
    lda #NR_INVERSE
    bcc :+
    ora #NR_SELECTED
:
    ldx g_col
    sta G_FLAGS,x
    ldx g_col
    lda #$2B
    sta G_CHARS,x
    lda #2
    sta G_ROLES,x
@done:
    rts
.segment "RODATA"
grid_palette:
    .byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
grid_mask_roles:
    .byte 0,1,2,3,4,4,4,4
grid_color_roles:
    .byte 0,0,0,12,0,9,0,7,0,0,3,0,0,8,4,10
grid_style_low:
.repeat 2,W
.repeat 22,R
    .byte <($4800+(60+20*W)*R)
.endrepeat
.endrepeat
grid_style_high:
.repeat 2,W
.repeat 22,R
    .byte >($4800+(60+20*W)*R)
.endrepeat
.endrepeat
.segment "CODE"
