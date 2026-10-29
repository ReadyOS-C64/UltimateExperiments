.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "editor/api.inc"
.include "editor_file/api.inc"
.include "fileio/api.inc"
.global se_fd_confirm,se_fd_list_count,se_fd_list_index
.global se_fd_list_names,se_fd_list_lengths,se_fd_page,se_fd_list_error
.import tui_box40
.importzp text_ptr,screen_ptr
.import se_print,se_hex_byte,se_petscii_screen,tui_putc40,tui_color
.import tui_box_x,tui_box_y,tui_box_w,tui_box_h
.export se_file_dialog_draw
.segment "CODE"
; Stateless AUX painter, invoked from resident after the source renderer returns.
; The FILESTATE owner keeps filenames/list data valid. No disk/overlay calls.
se_file_dialog_draw:
    lda #1
    sta tui_box_x
    lda #4
    sta tui_box_y
    lda #38
    sta tui_box_w
    lda #19
    sta tui_box_h
    jsr tui_box40
    PRINT_AT fd_open,5,3
    lda se_f_operation
    cmp #F_OPEN
    beq @title
    PRINT_AT fd_save,5,3
@title:
    ldx #34
    lda #TUI_TITLE
@title_color:
    sta $D800+5*40+3,x
    dex
    bpl @title_color
    PRINT_AT fd_device,6,3
    lda se_f_device
    clc
    adc #$30
    sta VIC_SCREEN+6*40+10
    PRINT_AT fd_name,7,3
    ldy #0
@name:
    cpy se_f_name_len
    bcs @caret
    lda se_f_name,y
    jsr se_petscii_screen
    sta VIC_SCREEN+7*40+10,y
    lda #TUI_HIGHLIGHT
    sta $D800+7*40+10,y
    iny
    bne @name
@caret:
    lda #$A0
    sta VIC_SCREEN+7*40+10,y
    lda #TUI_HIGHLIGHT
    sta $D800+7*40+10,y
    lda se_f_ui_help
    jne help
    lda se_fd_confirm
    jne confirm
    lda se_f_error
    cmp #F_RECOVERY
    jeq recovery
    lda #0
    sta se_v_menu_index
@list:
    lda se_v_menu_index
    cmp se_fd_list_count
    bcs @listed
    asl
    asl
    asl
    asl
    sta se_v_menu_row ;16-byte native filename stride
    ldy #0
@cell:
    ldx se_v_menu_index
    tya
    cmp se_fd_list_lengths,x
    bcs @next
    tya
    clc
    adc se_v_menu_row
    tax
    lda se_fd_list_names,x
    jsr se_petscii_screen
    pha
    lda #TUI_FG
    sta tui_color
    ldx se_v_menu_index
    cpx se_fd_list_index
    bne @plain
    lda #TUI_HIGHLIGHT
    sta tui_color
    pla
    eor #$80
    pha
@plain:
    sty se_v_col
    tya
    clc
    adc #4
    tax
    lda se_v_menu_index
    clc
    adc #9
    tay
    pla
    jsr tui_putc40
    ldy se_v_col
    iny
    bne @cell
@next:
    inc se_v_menu_index
    jmp @list
@listed:
    PRINT_AT fd_choose,18,3
    PRINT_AT fd_keys,19,3
    lda se_f_error
    ora se_fd_list_error
    jeq status
    PRINT_AT fd_error,21,3
    lda se_f_error
    bne @error_code
    lda se_fd_list_error
@error_code:
    jsr se_hex_byte
    stx VIC_SCREEN+21*40+10
    sta VIC_SCREEN+21*40+11
    lda se_f_dos_error
    jsr se_hex_byte
    stx VIC_SCREEN+21*40+19
    sta VIC_SCREEN+21*40+20
    jmp status
confirm:
    PRINT_AT fd_dirty,10,3
    PRINT_AT fd_choices,12,3
    PRINT_AT fd_cancel,14,3
    jmp status
help:
    PRINT_AT fd_help1,10,3
    PRINT_AT fd_help2,12,3
    PRINT_AT fd_help3,14,3
    PRINT_AT fd_choices,18,3
    PRINT_AT fd_cancel,16,3
    jmp status
recovery:
    PRINT_AT fd_recovery,10,3
    PRINT_AT fd_kept,12,3
    ldy #15
@owned:
    lda se_io_owned_temp
    beq @backup
    lda se_io_temp_name,y
    jsr se_petscii_screen
    sta VIC_SCREEN+14*40+4,y
@backup:
    lda se_io_owned_backup
    beq @next
    lda se_io_backup_name,y
    jsr se_petscii_screen
    sta VIC_SCREEN+16*40+4,y
@next:
    dey
    bpl @owned
status:
    PRINT_AT fd_status,24,0
    lda #0
    clc
    rts
.segment "RODATA"
fd_open: .asciiz "Open a PETSCII document"
fd_save: .asciiz "Save a PETSCII document"
fd_device: .asciiz "Device:"
fd_name: .asciiz "Name:"
fd_choose: .asciiz "UP/DOWN choose; RETURN accepts"
fd_keys: .asciiz "F3 drive 8/9  F5 page"
fd_error: .asciiz "Error $    DOS $"
fd_dirty: .asciiz "Save changes before opening?"
fd_choices: .asciiz "S Save   D Discard   C Cancel"
fd_cancel: .asciiz "STOP cancels; F6 help."
fd_help1: .asciiz "Type up to 16 PETSCII characters."
fd_help2: .asciiz "RETURN accepts the name."
fd_help3: .asciiz "F3 drive F5 page DEL erase"
fd_recovery: .asciiz "Recovery: files retained."
fd_kept: .asciiz "K keeps files and closes"
fd_status: .asciiz " File dialog       F6 Help   STOP Back   "
