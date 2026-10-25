.setcpu "6502"
.include "platform.inc"
.export tui_putc40, tui_color
.segment "ZEROPAGE"
tui_cell_ptr: .res 2
tui_color_ptr: .res 2
.segment "BSS"
tui_color: .res 1
.segment "CODE"
; A screen code, X column, Y row. Clips before stores. A/X/Y/P clobbered.
; This independent cell primitive has no menu, frame or input dependency.
tui_putc40:
    cpx #40
    bcs @done
    cpy #25
    bcs @done
    pha
    txa
    clc
    adc cell_row_low,y
    sta tui_cell_ptr
    sta tui_color_ptr
    lda cell_row_high,y
    adc #0
    sta tui_cell_ptr+1
    clc
    adc #$98
    sta tui_color_ptr+1
    ldy #0
    pla
    sta (tui_cell_ptr),y
    lda tui_color
    sta (tui_color_ptr),y
@done:
    rts
.segment "RODATA"
cell_row_low:
.repeat 25, R
    .byte <(VIC_SCREEN+40*R)
.endrepeat
cell_row_high:
.repeat 25, R
    .byte >(VIC_SCREEN+40*R)
.endrepeat
