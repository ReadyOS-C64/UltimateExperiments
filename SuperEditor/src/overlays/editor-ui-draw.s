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
    ldx se_e_text_length
    cpx #3
    bcc :+
    ldx #0
:   lda guide_pages,x
    jsr ui_print_group
    lda #0
    clc
    rts
.segment "RODATA"
guide_pages: .byte guide_table0-ui_print_table,guide_table1-ui_print_table,guide_table2-ui_print_table
guide_0_0: .byte "SuperEditor keys 1/3",0
guide_0_1: .byte "Type / Return / DEL / cursors",0
guide_0_2: .byte "F1 menus; View P preview/source",0
guide_0_3: .byte "View S settings; Settings H syntax",0
guide_0_4: .byte "F4 wrap; F8/CTRL-F8 modes",0
guide_0_5: .byte "F2 mark; CTRL-C/K copy",0
guide_0_6: .byte "CTRL-X cut / CTRL-V paste",0
guide_0_7: .byte "CTRL-Z undo / CTRL-Y redo",0
guide_0_8: .byte "HOME/CTRL-E line; F7 commands",0
guide_0_9: .byte "F7 find/goto; Help D diag",0
guide_0_10: .byte "F3/F5 pages; F6/STOP close",0
guide_1_0: .byte "SuperMark inline 2/3",0
guide_1_1: .byte "# to ###### + space: headings",0
guide_1_2: .byte "**bold**  *italic*  ***both***",0
guide_1_3: .byte "@@code@@; no backticks",0
guide_1_4: .byte "- item / * item: bullets",0
guide_1_5: .byte "1. item preserves typed numbers",0
guide_1_6: .byte "Pound escape: ",$5C,"* ",$5C,"# ",$5C,"@ ",$5C,"",$5C,"",0
guide_1_7: .byte "Escape only syntax; not in code",0
guide_1_8: .byte "CR ends inline; unmatched literal",0
guide_1_9: .byte "No underscore/backslash markup",0
guide_2_0: .byte "SuperMark blocks 3/3",0
guide_2_1: .byte ":::basic / :::asm / :::text",0
guide_2_2: .byte "Close with same colon count",0
guide_2_3: .byte "3-15 colons; longer fence quotes",0
guide_2_4: .byte "a shorter closing line literally",0
guide_2_5: .byte ":::region title / :::end nest",0
guide_2_6: .byte "Blocks start in column zero",0
guide_2_7: .byte "Source keeps controls; View P",0
guide_2_8: .byte "shows formatted GEOS preview",0
guide_2_9: .byte "Other Markdown forms stay literal",0
MENU_TEXT=1
.include "editor/menu-data.inc"
