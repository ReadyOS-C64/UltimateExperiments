.setcpu "6502"
.include "platform.inc"
.export se_display_init
.segment "CODE"
; Configure RAM character set and ReadyOS base theme. Caller masks IRQ for
; character-ROM access. This small hardware module has no menu/document code.
se_display_init:
    lda $01
    pha
    and #$F8
    ora #2
    sta $01
    ldx #0
@font:
    .repeat 8, P
        lda $D800+P*$100,x
        sta VIC_CHARSET+P*$100,x
    .endrepeat
    inx
    bne @font
    pla
    sta $01
    lda $DD00
    and #$FC
    ora #2
    sta $DD00
    lda $DD02
    ora #3
    sta $DD02
    lda #$02
    sta $D018
    lda #$1B
    sta $D011
    lda #$08
    sta $D016
    lda #0
    sta $D015
    lda #TUI_BG
    sta $D021
    sta $D020
    ldx #0
    lda #32
@clear:
    .repeat 4, P
        sta VIC_SCREEN+P*$100,x
    .endrepeat
    inx
    bne @clear
    lda #TUI_FG
@color:
    .repeat 4, P
        sta $D800+P*$100,x
    .endrepeat
    inx
    bne @color
    rts
