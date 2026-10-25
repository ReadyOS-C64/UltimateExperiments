; Logical UI uses the physical40-column matrix. Read each char/color before
; replacing its attribute byte. Row-major conversion never reads past a cell.
grid_finalize:
    jsr grid_width
    jcs grid_return
    lda #0
    sta g_x
    sta g_y
    sta g_skip
    lda #40
    sta g_w
    lda #2
    sta g_h
    jsr grid_rect
    jcs grid_return
    lda #24
    sta g_y
    lda #1
    sta g_h
    jsr grid_rect
    jcs grid_return
    lda se_e_ui
    cmp #3
    beq @popup
    cmp #1
    jne grid_zero
    lda se_e_menu
    jeq grid_zero
@popup:
    lda #1
    sta g_skip
    lda tui_box_x
    sta g_x
    lda tui_box_y
    sta g_y
    lda tui_box_w
    sta g_w
    lda tui_box_h
    sta g_h
    ; Existing box calls validate dimensions. Still refuse malformed inputs
    ; before the rectangle can touch bitmap-tail catalog or neighboring RAM.
    lda g_x
    cmp #40
    jcs grid_bad
    lda g_y
    cmp #25
    jcs grid_bad
    lda g_w
    beq @done
    cmp #41
    jcs grid_bad
    clc
    adc g_x
    cmp #41
    jcs grid_bad
    lda g_h
    beq @done
    cmp #26
    jcs grid_bad
    clc
    adc g_y
    cmp #26
    jcs grid_bad
    jsr grid_rect
    jcs grid_return
@done:
    jmp grid_zero
grid_rect:
    lda #0
    sta g_row
@row:
    lda #0
    sta g_col
@cell:
    lda g_x
    clc
    adc g_col
    sta G_BC+BC_COLUMN
    lda g_y
    clc
    adc g_row
    sta G_BC+BC_ROW
    tax
    ; Geometry above remains shared with old cell path. Only GEOS fullchrome
    ; rows batch; popup skip1 retains its exact original rectangle semantics.
    lda g_backend
    cmp #27
    bne @cell_path
    lda g_skip
    bne @cell_path
    txa
    sta se_overlay_frame+1
    lda #4
    sta se_overlay_frame
    lda #27
    ldx #0
    jsr se_overlay_call
    bcc :+
    rts
:   jmp @next_row
@cell_path:
    lda g_skip
    beq :+
    cpx #2
    bcc @advance
    cpx #24
    beq @advance
:
    lda #$40
    sta screen_ptr+1
    lda #0
@offset:
    cpx #0
    beq @column
    clc
    adc #40
    bcc :+
    inc screen_ptr+1
:
    dex
    bne @offset
@column:
    clc
    adc G_BC+BC_COLUMN
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:
    ldy #0
    lda (screen_ptr),y
    sta G_BC+BC_SCREEN
    lda screen_ptr+1
    clc
    adc #$98
    sta screen_ptr+1
    lda (screen_ptr),y
    and #15
    sta G_BC+BC_FOREGROUND
    lda #6
    sta G_BC+BC_BACKGROUND
    lda #0
    sta G_BC+BC_FONT
    sta G_BC+BC_BITMAP
    sta G_BC+BC_ATTRIBUTES
    lda #$AC
    sta G_BC+BC_FONT+1
    lda #$60
    sta G_BC+BC_BITMAP+1
    lda #$40
    sta G_BC+BC_ATTRIBUTES+1
    lda #GRID_CELL8
    sta se_overlay_frame
    lda #<G_BC
    sta se_overlay_frame+1
    lda #>G_BC
    sta se_overlay_frame+2
    lda g_backend
    ldx #0
    jsr se_overlay_call
    bcs @return
@advance:
    inc g_col
    lda g_col
    cmp g_w
    jcc @cell
@next_row:
    inc g_row
    lda g_row
    cmp g_h
    jcc @row
    lda #0
    clc
@return:
    rts
