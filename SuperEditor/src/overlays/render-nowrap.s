; R1 logical-line renderer. C11 supplies all22 starts and the bottom anchor;
; hidden long-line bytes are never traversed inside this synchronous painter.
nowrap_draw:
    jsr nowrap_locate
    jcs return
    jsr clear_screen
    lda #0
    sta se_r_path
    sta se_v_row
@row:
    inc se_r_rows
    jsr nowrap_bounds
    jcs return
    ADD24 se_r_first,se_l_pan,se_v_pos
    lda #0
    sta se_v_col
@cell:
    CMP24 se_v_pos,se_l_end
    bcc @source
    beq @end
    jmp @pad
@source:
    jsr se_view_peek
    jcs return
    jsr se_petscii_screen
    sta se_v_cell
    jsr put_source
    jsr se_view_advance
    inc se_v_col
    lda se_v_col
    cmp #40
    bcc @cell
    jmp @next
@end:
    jsr put_end ;CR/EOF marker, including hidden selection summary
    inc se_v_col
@pad:
    lda se_v_col
    cmp #40
    bcs @next
    lda #TUI_FG
    sta tui_color
    ldx se_v_col
    lda se_v_row
    clc
    adc #2
    tay
    lda #32
    jsr body_put
    inc se_v_col
    jmp @pad
@next:
    inc se_v_row
    lda se_v_row
    cmp #EDITOR_BODY_ROWS
    jcc @row
    jmp chrome
; End excludesCR; theCR/EOF boundary itself can be a visible blank cell.
nowrap_bounds:
    lda se_v_row
    asl
    clc
    adc se_v_row
    tax
    lda se_v_rows,x
    sta se_r_first
    lda se_v_rows+1,x
    sta se_r_first+1
    lda se_v_rows+2,x
    sta se_r_first+2
    jsr read_next
    lda se_ef_valid
    beq :+
    ldy #0
@paint_end:
    lda se_ef_paint_ends,x
    sta se_r_next,y
    inx
    iny
    cpy #3
    bcc @paint_end
:
    COPY24 se_r_next,se_l_end
    CMP24 se_l_end,se_r_first
    bcc @bad
    beq @ready
    COPY24 se_l_end,se_v_pos
    jsr se_view_retreat
    jsr se_view_peek
    bcs @return
    cmp #13
    bne @ready
    COPY24 se_v_pos,se_l_end
@ready:
    clc
@return:
    rts
@bad:
    lda #$7B
    sec
    rts
nowrap_locate:
    lda #0
    sta se_v_row
@row:
    jsr nowrap_bounds
    jcs @return
    CMP24 se_hot_caret,se_r_first
    bcc @next
    CMP24 se_hot_caret,se_l_end
    bcc @found
    beq @found
@next:
    inc se_v_row
    lda se_v_row
    cmp #EDITOR_BODY_ROWS
    bcc @row
    lda #$7B
    sec
    rts
@found:
    SUB24 se_hot_caret,se_r_first,se_l_column
    lda se_l_manual
    bne @ready
    CMP24 se_l_column,se_l_pan
    bcc @left
    SUB24 se_l_column,se_l_pan,se_r_delta
    lda se_r_delta+2
    ora se_r_delta+1
    bne @right
    lda se_r_delta
    cmp #40
    bcc @ready
@right:
    sec
    lda se_l_column
    sbc #39
    sta se_l_pan
    lda se_l_column+1
    sbc #0
    sta se_l_pan+1
    lda se_l_column+2
    sbc #0
    sta se_l_pan+2
    jmp @ready
@left:
    COPY24 se_l_column,se_l_pan
@ready:
    clc
@return:
    rts
