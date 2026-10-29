; Reusable40-column ReadyOS editor chrome: header plus one status/prompt row.
; Caller supplies resident editor fields and returns to its own cache/publisher.
; No body/cache/layout calls, added state or zero page. Existing text/screen
; pointers and se_v_col/se_v_cell are scratch, matching the original R1 code.
.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_print,se_hex_byte
.importzp text_ptr,screen_ptr
.import se_e_ui,se_e_error,se_e_text,se_e_text_length
.import se_hot_caret,se_hot_pending,se_h_dirty,se_h_fault,se_h_trimmed
.import se_sel_mark,se_v_col,se_v_cell
.endif
.include "editor/geometry.inc"

.export tui_editor_status40
.segment "CODE"
tui_editor_status40:
    ; Status, diagnostics and the command prompt share exactly one row.
    ldx #39
    lda #32
@clear_status:
    sta VIC_SCREEN+EDITOR_STATUS_ROW*40,x
    dex
    bpl @clear_status
    ldx #39
    lda #TUI_STATUS
@status_ink:
    sta $D800+EDITOR_STATUS_ROW*40,x
    dex
    bpl @status_ink
    lda se_e_ui
    cmp #2
    jeq command_line
    lda se_e_error
    cmp #$7C
    jeq @argument
    cmp #$7D
    jeq @line
    cmp #$7E
    jeq @missing
    lda se_h_fault
    jne @history_fault
    lda se_e_error
    jne @error
    lda se_h_trimmed
    ora se_h_trimmed+1
    jne @trimmed
    PRINT_AT position,EDITOR_STATUS_ROW,1
    lda se_hot_caret+2
    ldx #6
    jsr status_hex
    lda se_hot_caret+1
    ldx #8
    jsr status_hex
    lda se_hot_caret
    ldx #10
    jsr status_hex
    lda se_hot_pending
    ora se_h_dirty
    beq @clean
    PRINT_AT modified,EDITOR_STATUS_ROW,14
    jmp @mark
@clean:
    PRINT_AT clean,EDITOR_STATUS_ROW,14
@mark:
    lda se_sel_mark
    beq @help
    PRINT_AT mark_label,EDITOR_STATUS_ROW,23
@help:
    PRINT_AT help_hint,EDITOR_STATUS_ROW,32
    rts
@error:
    PRINT_AT error_label,EDITOR_STATUS_ROW,1
    lda se_e_error
    ldx #7
    jsr status_hex
    jmp @help
@argument:
    PRINT_AT argument_hint,EDITOR_STATUS_ROW,1
    rts
@line:
    PRINT_AT line_hint,EDITOR_STATUS_ROW,1
    rts
@missing:
    PRINT_AT missing_hint,EDITOR_STATUS_ROW,1
    rts
@history_fault:
    PRINT_AT fault_hint,EDITOR_STATUS_ROW,1
    rts
@trimmed:
    PRINT_AT trim_hint,EDITOR_STATUS_ROW,1
    rts
status_hex:
    stx se_v_col
    jsr se_hex_byte
    sta se_v_cell
    txa
    ldx se_v_col
    sta VIC_SCREEN+EDITOR_STATUS_ROW*40,x
    lda se_v_cell
    sta VIC_SCREEN+EDITOR_STATUS_ROW*40+1,x
    rts
command_line:
    PRINT_AT command_label,EDITOR_STATUS_ROW,0
    PRINT_AT se_e_text,EDITOR_STATUS_ROW,8
    ldx se_e_text_length
    lda #$A0
    sta VIC_SCREEN+EDITOR_STATUS_ROW*40+8,x
    rts
.segment "RODATA"
position: .asciiz "Pos:"
modified: .asciiz "Modified"
clean: .asciiz "Clean"
error_label: .asciiz "Error"
mark_label: .asciiz "Mark"
help_hint: .asciiz "F6 Help"
argument_hint: .asciiz "Invalid number/text / F6 Help"
line_hint: .asciiz "No such line / F6 Help"
missing_hint: .asciiz "No match / CTRL-N next / F6 Help"
trim_hint: .asciiz "Undo full: oldest dropped / F6 Help"
fault_hint: .asciiz "Undo fault: Edit/C clear / F6 Help"
command_label: .asciiz "Command:"
