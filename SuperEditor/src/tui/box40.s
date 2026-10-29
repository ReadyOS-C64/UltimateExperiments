.setcpu "6502"
.macpack longbranch
.include "tui/theme.inc"
.ifndef EDITOR_OVERLAY
.import tui_putc40, tui_color
.endif
.export tui_box40, tui_box40_color, tui_box_x, tui_box_y, tui_box_w, tui_box_h
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.segment "BSS"
tui_box_x: .res 1
tui_box_y: .res 1
tui_box_w: .res 1
tui_box_h: .res 1
box_rx: .res 1
box_ry: .res 1
.endif
.segment "CODE"
; ReadyOS PETSCII window: light-blue frame, blue interior, white default text.
; Static parameter frame; nonreentrant. Dimensions validated; cells clipped.
tui_box40:
    lda #TUI_BORDER
tui_box40_color:
    sta @border_color+1
    lda tui_box_x
    cmp #40
    jcs @invalid
    lda tui_box_y
    cmp #25
    jcs @invalid
    lda tui_box_w
    cmp #2
    jcc @invalid
    cmp #41
    jcs @invalid
    lda tui_box_h
    cmp #2
    jcc @invalid
    cmp #26
    jcs @invalid
    lda #0
    sta box_ry
@row:
    lda #0
    sta box_rx
@cell:
    lda #TUI_FG
    sta tui_color
    lda box_ry
    beq @top
    clc
    adc #1
    cmp tui_box_h
    beq @bottom
    lda box_rx
    beq @vertical
    clc
    adc #1
    cmp tui_box_w
    beq @vertical
    lda #32
    bne @write
@vertical:
    lda #TUI_VLINE
    bne @border
@top:
    lda box_rx
    beq @tl
    clc
    adc #1
    cmp tui_box_w
    beq @tr
    lda #TUI_HLINE
    bne @border
@tl:
    lda #TUI_CORNER_TL
    bne @border
@tr:
    lda #TUI_CORNER_TR
    bne @border
@bottom:
    lda box_rx
    beq @bl
    clc
    adc #1
    cmp tui_box_w
    beq @br
    lda #TUI_HLINE
    bne @border
@bl:
    lda #TUI_CORNER_BL
    bne @border
@br:
    lda #TUI_CORNER_BR
@border:
@border_color:
    ldx #TUI_BORDER
    stx tui_color
@write:
    pha
    lda box_rx
    clc
    adc tui_box_x
    tax
    lda box_ry
    clc
    adc tui_box_y
    tay
    pla
    jsr tui_putc40
    inc box_rx
    lda box_rx
    cmp tui_box_w
    bcc @cell
    inc box_ry
    lda box_ry
    cmp tui_box_h
    jcc @row
    clc
    rts
@invalid:
    sec
    rts
