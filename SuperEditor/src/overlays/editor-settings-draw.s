; R22 operation0/menu8. Reads checked session tableCB80, no candidate orsource
; pointers crossC7->R22. All drawing uses unchanged ReadyOS TUI primitives.
.segment "CODE"
settings_popup:
    lda #1
    sta tui_box_x
    lda #3
    sta tui_box_y
    lda #38
    sta tui_box_w
    lda #20
    sta tui_box_h
    jsr tui_box40
    lda #settings_table-ui_print_table
    jsr ui_print_group
    lda #settings_right-ui_print_table
    jsr ui_print_group
    lda se_render_caps
    beq @plain
    cmp #1
    beq @markdown
    cmp #3
    bne @bad_preset
    PRINT_AT sp_full,20,17
    jmp @preset_done
@plain:
    PRINT_AT sp_plain,20,17
    jmp @preset_done
@markdown:
    PRINT_AT sp_markdown,20,17
    jmp @preset_done
@bad_preset:
    PRINT_AT sp_bad_preset,20,17
@preset_done:
    lda se_e_item
    and #7
    tax
    lda sp_offsets,x
    sta se_v_menu_count ;selected profile offset, not a pointer outsideR22
    txa
    clc
    adc #6
    sta se_v_menu_row
    ; Highlight the8-character profile label, including trailingblank.
    lda #0
    sta se_v_menu_index
@profile:
    ; Direct native screen conversion is unnecessary: labels already painted.
    lda se_v_menu_row
    asl
    tax
    lda sp_row_ptr,x
    sta text_ptr
    lda sp_row_ptr+1,x
    sta text_ptr+1
    ldy se_v_menu_index
    lda (text_ptr),y
    eor #$80
    pha
    lda #TUI_HIGHLIGHT
    sta tui_color
    lda se_v_menu_index
    clc
    adc #3
    tax
    ldy se_v_menu_row
    pla
    jsr tui_putc40
    inc se_v_menu_index
    lda se_v_menu_index
    cmp #8
    bcc @profile
    ldx se_v_menu_count
    lda se_editor_settings+SES_ORIGIN,x
    cmp #1
    beq @geos
    cmp #0
    bne @invalid
    lda se_editor_settings+SES_FAMILY+1,x
    bne @invalid
    lda se_editor_settings+SES_FAMILY,x
    beq @bsw
    cmp #1
    bne @invalid
    PRINT_AT sp_native,7,16
    jmp @numbers
@bsw:
    PRINT_AT sp_bsw,7,16
    jmp @numbers
@geos:
    ldx se_v_menu_count
    lda se_editor_settings+SES_FAMILY+1,x
    bne @invalid
    lda se_editor_settings+SES_FAMILY,x
    ldy #9
@find_family:
    cmp sp_family_ids,y
    beq @family_found
    dey
    bpl @find_family
    bmi @invalid
@family_found:
    tya
    asl
    tax
    lda sp_family_names,x
    sta text_ptr
    lda sp_family_names+1,x
    sta text_ptr+1
    lda #<(VIC_SCREEN+40*7+16)
    sta screen_ptr
    lda #>(VIC_SCREEN+40*7+16)
    sta screen_ptr+1
    jsr se_print
    jmp @numbers
@invalid:
    PRINT_AT sp_invalid,7,16
@numbers:
    ldx se_v_menu_count
    lda se_editor_settings+SES_POINT_SIZE,x
    ldx #22
    ldy #8
    jsr sp_hex
    ldx se_v_menu_count
    lda se_editor_settings+SES_FOREGROUND,x
    ldx #22
    ldy #9
    jsr sp_hex
    ldx se_v_menu_count
    lda se_editor_settings+SES_BACKGROUND,x
    ldx #22
    ldy #10
    jsr sp_hex
    lda #0
    sta se_v_menu_index
@style:
    ldx se_v_menu_count
    lda se_editor_settings+SES_STYLES,x
    ldx se_v_menu_index
    and sp_masks,x
    beq @off
    lda #TUI_HIGHLIGHT
    sta tui_color
    lda sp_letters,x
    eor #$80
    bne @letter
@off:
    lda #TUI_FG
    sta tui_color
    lda sp_letters,x
@letter:
    ldx se_v_menu_index
    pha
    lda sp_cols,x
    tax
    ldy #13
    pla
    jsr tui_putc40
    inc se_v_menu_index
    lda se_v_menu_index
    cmp #3
    bcc @style
    lda #0
    clc
    rts
; A byte / Xcolumn / Yrow; two hex screen codes, no source changes.
sp_hex:
    stx se_v_col
    sty se_v_menu_row
    jsr se_hex_byte
    pha
    txa
    pha
    lda #TUI_TITLE
    sta tui_color
    pla
    ldx se_v_col
    ldy se_v_menu_row
    jsr tui_putc40
    pla
    ldx se_v_col
    inx
    ldy se_v_menu_row
    jmp tui_putc40
.segment "RODATA"
sp_title: .asciiz "Session text settings"
sp_body: .asciiz "1 Body"
sp_h1: .asciiz "2 H1"
sp_h2: .asciiz "3 H2"
sp_h3: .asciiz "4 H3"
sp_h4: .asciiz "5 H4"
sp_h5: .asciiz "6 H5"
sp_h6: .asciiz "7 H6"
sp_code: .asciiz "8 Code"
sp_font: .asciiz "Font"
sp_bsw: .asciiz "BSW / 9"
sp_native: .asciiz "Native / 8"
; Genuine GEOS family IDs are lookup keys only, never user-facing labels.
sp_family_ids: .byte 1,2,3,4,5,26,27,28,29,30
sp_family_names:
    .word sp_university,sp_california,sp_roma,sp_dwinelle,sp_cory
    .word sp_commodore,sp_lw_roma,sp_lw_cal,sp_lw_greek,sp_lw_barrows
sp_university: .asciiz "University"
sp_california: .asciiz "California"
sp_roma: .asciiz "Roma"
sp_dwinelle: .asciiz "Dwinelle"
sp_cory: .asciiz "Cory"
sp_commodore: .asciiz "Commodore"
sp_lw_roma: .asciiz "LW Roma"
sp_lw_cal: .asciiz "LW Cal"
sp_lw_greek: .asciiz "LW Greek"
sp_lw_barrows: .asciiz "LW Barrows"
sp_invalid: .asciiz "Invalid / R reset"
sp_size: .asciiz "Size $"
sp_ink: .asciiz "Ink  $"
sp_paper: .asciiz "Paper$"
sp_style: .asciiz "B / I / U"
sp_keys1: .asciiz "F font  S size  C ink  G paper"
sp_keys2: .asciiz "B/I/U toggle; arrows/1-8 profile"
sp_keys3: .asciiz "R reset defaults; Return closes"
sp_session: .asciiz "Session only / no disk writes"
sp_syntax: .asciiz "H source mode:"
sp_plain: .asciiz "Plain"
sp_markdown: .asciiz "Markdown"
sp_full: .asciiz "Full"
sp_bad_preset: .asciiz "Invalid"
sp_offsets: .byte SES_BODY,SES_HEADING1,SES_HEADING2,SES_HEADING3,SES_HEADING4,SES_HEADING5,SES_HEADING6,SES_CODE
sp_masks: .byte SES_BOLD,SES_ITALIC,SES_UNDERLINE
sp_letters: .byte 'b'-64,'i'-64,'u'-64
sp_cols: .byte 16,20,24
sp_row_ptr:
.repeat 25,R
 .word VIC_SCREEN+40*R+3
.endrepeat
