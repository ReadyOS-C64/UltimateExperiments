; Probe-only bitmap backend for a fixed test window. Production reusable 40-col
; frame/cell micromodules are linked only into clients that actually need them.
.segment "CODE"
p_panel:
    lda se_mode
    bne @bitmap
    lda #3
    sta tui_box_x
    lda #4
    sta tui_box_y
    lda #29
    sta tui_box_w
    lda #12
    sta tui_box_h
    jmp tui_box40
@bitmap:
    lda #0
    sta p_x+1
    lda #24
    sta p_x
    lda #32
    sta p_y
@clear_row:
    ldy p_y
    lda p_bitmap_low,y
    clc
    adc #24
    sta p_pixel_ptr
    lda p_bitmap_high,y
    adc #0
    sta p_pixel_ptr+1
    ldy #0
    lda #0
@clear_bits:
    sta (p_pixel_ptr),y
    iny
    cpy #232
    bcc @clear_bits
    jsr p_attribute_address
    lda p_attr_ptr
    sta p_rank_ptr
    lda p_attr_ptr+1
    clc
    adc #$40
    sta p_rank_ptr+1
    ldy #0
@clear_attr:
    lda #0
    sta (p_rank_ptr),y
    lda #$16
    sta (p_attr_ptr),y
    iny
    cpy #29
    bcc @clear_attr
    lda p_y
    clc
    adc #8
    sta p_y
    cmp #128
    bcc @clear_row
    lda #6
    sta p_style
    lda #32
    sta p_y
@horizontal:
    lda #24
    sta p_x
@across:
    jsr p_plot
    inc p_x
    bne @across
    lda p_y
    cmp #127
    beq @vertical
    lda #127
    sta p_y
    bne @horizontal
@vertical:
    lda #33
    sta p_y
@side:
    lda #24
    sta p_x
    jsr p_plot
    lda #255
    sta p_x
    jsr p_plot
    inc p_y
    lda p_y
    cmp #127
    bcc @side
    rts
