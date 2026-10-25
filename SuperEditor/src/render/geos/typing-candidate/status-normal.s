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
.segment "RODATA"
modified: .asciiz "Modified"
clean: .asciiz "Clean   "
