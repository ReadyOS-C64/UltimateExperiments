.setcpu "6502"
.include "platform.inc"
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_print
.importzp text_ptr,screen_ptr
.endif
.export tui_header40
.ifdef EDITOR_OVERLAY
.export tui_round_corners
.endif
.segment "CODE"
; ReadyOS menu header without a top rule/title. Two rows; no document state.
tui_header40:
.ifdef EDITOR_OVERLAY
    ; The lowercase ROM uses square line corners in these slots. Patch the
    ; private RAM charset once after each font reload, inside display-owned
    ; overlay code rather than growing the resident editor.
    lda $D011
    and #$20
    bne @font_ready
    jsr tui_round_corners
@font_ready:
.endif
    PRINT_AT header_text,0,0
    ldx #39
@rule:
    lda #TUI_HLINE
    sta VIC_SCREEN+40,x
    lda #TUI_TITLE
    sta $D800+40,x
    lda #TUI_FG
    sta $D800,x
    dex
    bpl @rule
    ldx #6
@separator:
    ldy separators,x
    lda #TUI_TITLE
    sta $D800,y
    lda #$71 ; ReadyOS T_UP, joins the vertical above to the bottom rule
    sta VIC_SCREEN+40,y
    dex
    bpl @separator
    lda #TUI_CORNER_BL
    sta VIC_SCREEN+40
    lda #TUI_CORNER_BR
    sta VIC_SCREEN+79
    lda #TUI_HIGHLIGHT
    ldx #5
@mnemonic:
    ldy mnemonics,x
    sta $D800,y
    dex
    bpl @mnemonic
    rts
.ifdef EDITOR_OVERLAY
tui_round_corners:
    lda VIC_CHARSET+TUI_CORNER_BL*8+2
    cmp #$1C
    beq @corners_done
    ldx #7
@corners:
    lda rounded_bl,x
    sta VIC_CHARSET+TUI_CORNER_BL*8,x
    lda rounded_br,x
    sta VIC_CHARSET+TUI_CORNER_BR*8,x
    dex
    bpl @corners
@corners_done:
    rts
.endif
.segment "RODATA"
header_text: .byte $DD,"File ",$DD,"Edit ",$DD,"View ",$DD,"Navigate",$DD,"Block ",$DD,"Help",$DD,0
separators: .byte 0,6,12,18,27,34,39
mnemonics: .byte 1,7,13,19,28,35
.ifdef EDITOR_OVERLAY
rounded_bl: .byte $18,$18,$1C,$0F,$07,$00,$00,$00
rounded_br: .byte $18,$18,$38,$F0,$E0,$00,$00,$00
.endif
