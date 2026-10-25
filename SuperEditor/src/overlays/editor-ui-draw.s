.import tui_box40
.export se_ui_draw
.segment "CODE"
se_ui_draw:
popup:
    lda se_e_menu
    jeq @bar_only
    cmp #6
    jeq help_popup
    cmp #7
    jeq diag_popup
    tax
    lda menu_counts-1,x
    sta se_v_menu_count
    clc
    adc #2
    sta tui_box_h
    lda #1
    sta tui_box_x
    lda #3
    sta tui_box_y
    lda #35
    sta tui_box_w
    jsr tui_box40
    lda se_e_menu
    sec
    sbc #1
    asl
    tax
    lda menu_labels,x
    sta se_v_menu_ptr
    lda menu_labels+1,x
    sta se_v_menu_ptr+1
    lda #0
    sta se_v_menu_index
@item:
    lda se_v_menu_ptr
    sta text_ptr
    lda se_v_menu_ptr+1
    sta text_ptr+1
    lda se_v_menu_index
    clc
    adc #4
    sta se_v_menu_row
    ldx #3
    ldy #0
@label:
    lda (text_ptr),y
    beq @end
    sty se_v_col
    stx se_v_row
    jsr se_petscii_screen
    ldx se_v_menu_index
    cpx se_e_item
    bne @plain
    eor #$80
    ldx #TUI_HIGHLIGHT
    bne @ink
@plain:
    ldx #TUI_FG
@ink:
    stx tui_color
    ldx se_v_row
    ldy se_v_menu_row
    jsr tui_putc40
    ldx se_v_row
    inx
    ldy se_v_col
    iny
    bne @label
@end:
    tya
    sec
    adc se_v_menu_ptr ;include NUL with carry set
    sta se_v_menu_ptr
    bcc :+
    inc se_v_menu_ptr+1
:
    inc se_v_menu_index
    lda se_v_menu_index
    cmp se_v_menu_count
    bcc @item
@bar_only:
    lda #0
    clc
    rts
help_popup:
    lda #1
    sta tui_box_x
    lda #3
    sta tui_box_y
    lda #38
    sta tui_box_w
    lda #16
    sta tui_box_h
    jsr tui_box40
    PRINT_AT help_title,4,3
    PRINT_AT help1,6,3
    PRINT_AT help2,7,3
    PRINT_AT help3,8,3
    PRINT_AT help4,10,3
    PRINT_AT help5,11,3
    PRINT_AT help6,12,3
    PRINT_AT help7,14,3
    PRINT_AT help8,15,3
    PRINT_AT help9,17,3
    lda #0
    clc
    rts
.segment "RODATA"
help_title: .asciiz "SuperEditor keyboard"
help1: .asciiz "Type / Return / DEL / cursors"
help2: .asciiz "F1 menus / F6 keyboard help"
help3: .asciiz "F3/F5 pages; F4 wrap; arrows move"
help4: .asciiz "CTRL-Z undo / CTRL-Y redo"
help5: .asciiz "HOME/CTRL-E line; F2 mark/unmark"
help6: .asciiz "CTRL-C/K copy CTRL-X/V cut/paste"
help7: .asciiz "F7 top/bottom/diag; Help-D diag"
help8: .asciiz "F8/CTRL-F8 modes; F7 wrap/pan"
help9: .asciiz "F6 or RUN/STOP closes help"
MENU_TEXT=1
.include "editor/menu-data.inc"
