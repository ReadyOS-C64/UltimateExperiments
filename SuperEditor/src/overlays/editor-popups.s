; R22 stateless ReadyOS popup micro module. Operation0 draws current menu/help/
; diagnostics from resident UI state; it receives no pointers into caller C7.
; Box40 and renderer ABI remain unchanged. FILE owner1 has its own AUX popup.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "platform.inc"
.include "editor/api.inc"
.include "render/geos/settings.inc"
.segment "CODE"
    OVL_BINDING
.export entry
entry:
    lda se_e_menu
    cmp #8
    jeq settings_popup
    jmp se_ui_draw
.include "overlays/editor-ui-draw.s"
.include "diagnostics/ui.s"

.include "overlays/editor-settings-draw.s"

.segment "CODE"
; A is a byte offset into this sealed list of (text16,row*2|col16flag).
; Source and destination are the existing text_ptr/screen_ptr loans. se_print
; and se_petscii_screen preserve X (checked resident source/bytes); no new state.
; Every group terminates with word0; all rows are0..24 and byte offsets<256.
; ABI: A/X/Y/P clobbered, no caller pointers retained across overlay swaps.
ui_print_group:
    tax
@next:
    lda ui_print_table+1,x
    beq @done
    sta text_ptr+1
    lda ui_print_table,x
    sta text_ptr
    lda ui_print_table+2,x
    and #$7f
    tay
    lda sp_row_ptr,y
    sta screen_ptr
    lda sp_row_ptr+1,y
    sta screen_ptr+1
    lda ui_print_table+2,x
    bpl :+
    lda screen_ptr
    clc
    adc #13
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:   jsr se_print
    inx
    inx
    inx
    bne @next
@done:
    rts
.segment "RODATA"
ui_print_table:
guide_table0:
 .word guide_0_0
 .byte 8
 .word guide_0_1
 .byte 12
 .word guide_0_2
 .byte 14
 .word guide_0_3
 .byte 16
 .word guide_0_4
 .byte 18
 .word guide_0_5
 .byte 20
 .word guide_0_6
 .byte 22
 .word guide_0_7
 .byte 24
 .word guide_0_8
 .byte 26
 .word guide_0_9
 .byte 28
 .word guide_0_10
 .byte 34
 .word 0
guide_table1:
 .word guide_1_0
 .byte 8
 .word guide_1_1
 .byte 12
 .word guide_1_2
 .byte 14
 .word guide_1_3
 .byte 16
 .word guide_1_4
 .byte 18
 .word guide_1_5
 .byte 20
 .word guide_1_6
 .byte 22
 .word guide_1_7
 .byte 24
 .word guide_1_8
 .byte 26
 .word guide_1_9
 .byte 28
 .word guide_0_10
 .byte 34
 .word 0
guide_table2:
 .word guide_2_0
 .byte 8
 .word guide_2_1
 .byte 12
 .word guide_2_2
 .byte 14
 .word guide_2_3
 .byte 16
 .word guide_2_4
 .byte 18
 .word guide_2_5
 .byte 20
 .word guide_2_6
 .byte 22
 .word guide_2_7
 .byte 24
 .word guide_2_8
 .byte 26
 .word guide_2_9
 .byte 28
 .word guide_0_10
 .byte 34
 .word 0
diag_table:
 .word diag_title
 .byte 8
 .word diag_length
 .byte 12
 .word diag_cursor
 .byte 14
 .word diag_hash
 .byte 16
 .word diag_pending
 .byte 20
 .word diag_epoch
 .byte 22
 .word diag_owners
 .byte 24
 .word diag_overlay
 .byte 28
 .word diag_map
 .byte 34
 .word diag_physical
 .byte 36
 .word diag_types1
 .byte 38
 .word diag_types2
 .byte 40
 .word diag_close
 .byte 42
 .word 0
settings_table:
 .word sp_title
 .byte 8
 .word sp_body
 .byte 12
 .word sp_h1
 .byte 14
 .word sp_h2
 .byte 16
 .word sp_h3
 .byte 18
 .word sp_h4
 .byte 20
 .word sp_h5
 .byte 22
 .word sp_h6
 .byte 24
 .word sp_code
 .byte 26
 .word sp_keys1
 .byte 30
 .word sp_keys2
 .byte 34
 .word sp_keys3
 .byte 38
 .word sp_syntax
 .byte 40
 .word sp_session
 .byte 42
 .word 0
settings_right:
 .word sp_font
 .byte 140
 .word sp_size
 .byte 144
 .word sp_ink
 .byte 146
 .word sp_paper
 .byte 148
 .word sp_style
 .byte 152
 .word 0
ui_print_table_end:
.assert ui_print_table_end-ui_print_table<256,error,"static print index"
