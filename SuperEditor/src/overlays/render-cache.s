; R1-private cache operations. Every hit validates full source ownership,
; generation and viewport. Uncertain contexts fall back to a complete paint.
cache_plan:
    lda #0
    sta se_r_path
    sta se_r_rows
    sta se_r_cells
    sta se_r_cells+1
    lda se_ef_valid
    jne @full ;folded maps are painted from their published canonical anchors
    lda se_st_valid
    cmp se_st_cache_valid
    jne @full
    ldx #1
@style_generation:
    lda se_st_generation,x
    cmp se_st_cache_generation,x
    jne @full
    dex
    bpl @style_generation
    lda se_r_valid
    jeq @full
    lda se_e_ui
    ora se_r_ui
    jne @full
    ldx #9
@source:
    lda se_doc_original,x
    cmp se_r_original,x
    jne @full
    dex
    bpl @source
    ldx #1
@generation:
    lda se_doc_generation,x
    cmp se_r_generation,x
    jne @full
    dex
    bpl @generation
    CMP24 se_v_top,se_r_top
    jne @full
    ldx #3
@revision:
    lda se_r_revision,x
    cmp se_r_saved_revision,x
    jne @mutated
    dex
    bpl @revision
    CMP24 se_v_length,se_r_length
    jne @full
    ; Find the caret before disturbing old coordinates or pixels.
    COPY24 se_hot_caret,se_r_first
    jsr locate
    jcs @full
    lda se_sel_mark
    ora se_r_mark
    bne @selection
    lda #1
    sta se_r_path
    rts
@selection:
    lda se_sel_mark
    cmp se_r_mark
    bne @union
    CMP24 se_sel_anchor,se_r_anchor
    bne @union
    CMP24 se_hot_caret,se_r_caret
    bne @symmetric
    lda #1
    sta se_r_path
    rts
@symmetric:
    ; With an unchanged anchor, only the interval traversed by the caret
    ; changes selected styling. Do not repaint a whole growing selection.
    COPY24 se_hot_caret,se_r_first
    COPY24 se_hot_caret,se_r_last
    COPY24 se_r_caret,se_v_temp
    jsr include_range
    jmp @style
@union:
    ; Repaint the union of the old and new marked intervals. This is bounded
    ; to visible rows, including the CR marker and blank EOF caret cell.
    COPY24 se_hot_caret,se_r_first
    COPY24 se_hot_caret,se_r_last
    lda se_sel_mark
    beq :+
    COPY24 se_sel_anchor,se_v_temp
    jsr include_range
:
    COPY24 se_r_caret,se_v_temp
    jsr include_range
    lda se_r_mark
    beq :+
    COPY24 se_r_anchor,se_v_temp
    jsr include_range
:
@style:
    lda #1
    sta se_r_mode ;style-only, no source offset delta
    lda #0
    sta se_r_delta
    sta se_r_delta+1
    sta se_r_delta+2
    jmp @dirty
@mutated:
    lda se_r_damage_valid
    beq @full
    lda se_sel_mark
    ora se_r_mark
    bne @full
    COPY24 se_r_damage_from,se_r_first
    COPY24 se_r_damage_to,se_r_last
    SUB24 se_v_length,se_r_length,se_r_delta
    lda #0
    sta se_r_mode
@dirty:
    ; Starting before the top may have changed its logical row alignment.
    CMP24 se_r_first,se_v_top
    bcc @full
    jsr locate
    bcs @full
    lda #2
    sta se_r_path
    rts
@full:
    lda #0
    sta se_r_path
    rts
include_range:
    CMP24 se_v_temp,se_r_first
    bcs :+
    COPY24 se_v_temp,se_r_first
:
    CMP24 se_v_temp,se_r_last
    bcc :+
    COPY24 se_v_temp,se_r_last
:
    rts
; Locate first in the OLD row map. Cset=outside. EOF belongs to its first row.
; Writes row/col. Offset within a row is at most39, except a CR source boundary
; after exactly40 glyphs, which is explicitly represented by the next row.
locate:
    ldx #0
    ldy #0
@row:
    jsr read_next
    CMP24 se_r_first,se_r_next
    jcc @found
    jne @next
    lda se_v_rows,x
    cmp se_r_next
    bne @boundary
    lda se_v_rows+1,x
    cmp se_r_next+1
    bne @boundary
    lda se_v_rows+2,x
    cmp se_r_next+2
    jeq @found
@boundary:
    ; EOF in a partial text row is its final blank cell, not a new row.
    ; A CR or a full40-cell wrap really does advance to the following row.
    lda se_r_valid
    beq @current
    CMP24 se_r_first,se_r_length
    bne @next
    jmp @partial
@current:
    CMP24 se_r_first,se_v_length
    bne @next
@partial:
    sec
    lda se_r_first
    sbc se_v_rows,x
    cmp #40
    bcs @next
    txa
    pha
    tya
    pha
    COPY24 se_r_first,se_v_pos
    jsr se_view_retreat
    jsr se_view_peek
    bcs @read_failed
    sta se_r_color
    pla
    tay
    pla
    tax
    lda se_r_color
    cmp #13
    bne @found
    beq @next
@read_failed:
    pla
    tay
    pla
    tax
    sec
    rts
@next:
    inx
    inx
    inx
    iny
    cpy #EDITOR_BODY_ROWS
    jcc @row
    sec
    rts
@found:
    sty se_v_row
    sec
    lda se_r_first
    sbc se_v_rows,x
    sta se_v_col
    clc
    rts
read_next:
    cpx #EDITOR_LAST_ROW_OFFSET
    beq @bottom
    lda se_v_rows+3,x
    sta se_r_next
    lda se_v_rows+4,x
    sta se_r_next+1
    lda se_v_rows+5,x
    sta se_r_next+2
    rts
@bottom:
    COPY24 se_v_bottom,se_r_next
    rts
restore_caret:
    ldx se_r_caret_col
    lda se_r_caret_row
    clc
    adc #2
    tay
    lda se_r_under_color
    sta tui_color
    lda se_r_under_glyph
    jsr body_put
    rts
paint_caret:
    COPY24 se_hot_caret,se_r_first
    jsr locate
    bcs @done
    COPY24 se_hot_caret,se_v_pos
    lda #32
    sta se_v_cell
    CMP24 se_v_pos,se_v_length
    bcs @plain
    jsr se_view_peek
    bcs @done
    cmp #13
    beq @plain
    jsr se_petscii_screen
    sta se_v_cell
    jsr put_source
    clc
    rts
@plain:
    jsr put_plain
    clc
@done:
    rts
body_put:
    inc se_r_cells
    bne :+
    inc se_r_cells+1
:
    jmp tui_putc40
cache_save:
    lda se_st_valid
    sta se_st_cache_valid
    ldx #1
@style_generation:
    lda se_st_generation,x
    sta se_st_cache_generation,x
    dex
    bpl @style_generation
    ldx #9
@source:
    lda se_doc_original,x
    sta se_r_original,x
    dex
    bpl @source
    ldx #1
@generation:
    lda se_doc_generation,x
    sta se_r_generation,x
    dex
    bpl @generation
    COPY24 se_v_length,se_r_length
    COPY24 se_v_top,se_r_top
    COPY24 se_hot_caret,se_r_caret
    COPY24 se_sel_anchor,se_r_anchor
    lda se_sel_mark
    sta se_r_mark
    lda se_e_ui
    sta se_r_ui
    ldx #3
@revision:
    lda se_r_revision,x
    sta se_r_saved_revision,x
    dex
    bpl @revision
    lda #0
    sta se_r_damage_valid
    lda #1
    sta se_r_valid
    clc
    rts
