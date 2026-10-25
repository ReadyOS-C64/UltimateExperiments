.setcpu "6502"
.include "platform.inc"
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_print
.importzp text_ptr,screen_ptr
.endif
.export tui_header40
.segment "CODE"
; ReadyOS menu header without a top rule/title. Two rows; no document state.
tui_header40:
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
    rts
.segment "RODATA"
header_text: .byte $DD,"File ",$DD,"Edit ",$DD,"View ",$DD,"Navigate",$DD,"Block ",$DD,"Help",$DD,0
separators: .byte 0,6,12,18,27,34,39
