; Appended leaf helper; no new ZP/BSS and no immutable asset relocation.
; Called only after scalar/span/font validation and the existing histogram
; reset. Full clipping admits byte clear; partial clipping retains every bit.
.segment "GEOS_ROW_FAST"
row_clear:
    lda F+GR_LEFT
    ora F+GR_LEFT+1
    ora F+GR_TOP
    bne generic_clear
    lda F+GR_RIGHT
    cmp #<320
    bne generic_clear
    lda F+GR_RIGHT+1
    cmp #>320
    bne generic_clear
    lda F+GR_BOTTOM
    cmp #8
    bne generic_clear
    ; One complete VIC character row is320 contiguous bitmap bytes, despite
    ; the8x8 arrangement of its scan lines. Clear256+64, never the next row.
    lda rowbase
    sta se_gg_pointer
    lda rowbase+1
    sta se_gg_pointer+1
    lda #0
    tay
@page:
    sta (se_gg_pointer),y
    iny
    bne @page
    inc se_gg_pointer+1
    ldy #63
@tail:
    sta (se_gg_pointer),y
    dey
    bpl @tail
    rts
generic_clear:
    lda F+GR_TOP
    sta sy
@clear_y:
    lda sy
    cmp F+GR_BOTTOM
    bcs @done
    lda F+GR_LEFT
    sta pixel
    lda F+GR_LEFT+1
    sta pixel+1
@clear_x:
    jsr clipped_right
    bcs @next_y
    jsr pixel_address
    lda masks,x
    eor #$FF
    and (se_gg_pointer),y
    sta (se_gg_pointer),y
    jsr next_pixel
    jmp @clear_x
@next_y:
    inc sy
    jmp @clear_y
@done:
    rts
.assert *-row_clear<=165,error,"GEOS clear helper exceeds immutable-font tail"
