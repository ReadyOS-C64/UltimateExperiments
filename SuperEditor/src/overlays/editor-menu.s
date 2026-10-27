.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "platform.inc"
.include "editor/api.inc"
.include "search/api.inc"
.include "document/math24.inc"
.include "render/geos/settings.inc"
.include "render/presentation.inc"
.include "render/geos/edit-certificate.inc"
.include "render/geos/typing/certificate.inc"
.include "presentation-defaults.inc"
.ifndef U_SETTINGS
U_SETTINGS=8
.endif
.ifndef E_SETTINGS
E_SETTINGS=103
.endif
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #10
    jeq brg_schedule
    cmp #11
    jeq brg_source_proof
    cmp #9 ;internal optional cache admission; no new user-facing menu command
    jeq cache_admission
    cmp #U_DRAW
    jeq se_ui_draw
    lda #0
    sta se_e_command
    lda se_overlay_frame
    cmp #U_SETTINGS
    jeq settings_open
    cmp #U_HELP
    jeq help_toggle
    cmp #U_FINDPROMPT
    jeq prompt_initialize
    cmp #U_GOTOPROMPT
    jeq prompt_initialize
    cmp #U_MENU
    jeq menu
    cmp #U_COMMAND
    jeq command
    lda se_e_ui
    cmp #4
    jeq preview_key
    lda se_e_key
    cmp #3
    jeq close
    lda se_e_ui
    cmp #2
    jeq command_key
    lda se_e_menu
    cmp #8
    jeq settings_key
    cmp #6
    bne :+
    lda se_e_key
    cmp #$86
    jeq help_page
    cmp #$87
    jeq help_page
:   lda se_e_menu
    cmp #7
    jeq okay ;readonly diagnostic popup never indexes six-menu tables
    lda se_e_menu
    jeq heading
    lda se_e_key
    cmp #$1D
    jeq next_menu
    cmp #$9D
    jeq previous_menu
    cmp #$11
    jeq next_item
    cmp #$91
    jeq previous_item
    cmp #13
    jeq choose
    jsr fold_key
    sta se_v_cell
    ldx se_e_menu
    dex
    txa
    asl
    tax
    lda menu_keys,x
    sta text_ptr
    lda menu_keys+1,x
    sta text_ptr+1
    ldx se_e_menu
    dex
    lda menu_counts,x
    sta se_v_menu_count
    ldy #0
@find:
    lda (text_ptr),y
    cmp se_v_cell
    beq @item
    iny
    cpy se_v_menu_count
    bcc @find
    jmp heading
@item:
    sty se_e_item
    jmp choose
cache_admission:
    jsr se_bc_admit
    cmp #BC_MISS
    bne :+
    ; Optional storage failure resumes the ordinary C21/parser route.
    lda #0
    sta se_f_owner
    sta $9136
    lda #21
    sta $9135
    lda #1
:
    clc
    rts
menu:
    lda se_e_ui
    cmp #1
    jeq close
    lda #1
    sta se_e_ui
    lda #0
    sta se_e_menu
    sta se_e_item
    clc
    rts
command:
    lda se_e_ui
    cmp #2
    jeq close
    lda #2
    sta se_e_ui
    lda #0
    sta se_e_text_length
    sta se_e_text
    clc
    rts
prompt_initialize:
    tax
    lda #2
    sta se_e_ui
    ldy #4
@text:
    lda find_text,y
    cpx #U_FINDPROMPT
    beq :+
    lda goto_text,y
:
    sta se_e_text,y
    dey
    bpl @text
    lda #5
    sta se_e_text_length
    lda #0
    sta se_e_text+5
    clc
    rts
close:
    lda #0
    ldx se_mode
    cpx #3
    bne @publish
    ldx se_r_presentation
    beq @publish
    ; Preview's command line and menus cannot bypass its text-mutation gate.
    ldx #preview_mutations_end-preview_mutations-1
@guard:
    lda se_e_command
    cmp preview_mutations,x
    beq @blocked
    dex
    bpl @guard
    bmi @preview
@blocked:
    lda #0
    sta se_e_command
@preview:
    lda #4 ;return to read-only formatted preview, never edit source implicitly
@publish:
    sta se_e_ui
    clc
    rts
preview_key:
    lda se_e_key
    cmp #3
    beq @source
    cmp #13
    beq @source
    cmp #$13
    beq @top
    cmp #$93
    beq @top
    cmp #$91
    beq @up
    cmp #$11
    beq @down
    cmp #$86
    beq @up
    cmp #$87
    beq @down
    clc ;all typing/deletion/left/right ignored in read-only preview
    rts
@source:
    lda #67 ;E_SOURCE, shared API assigned by resident owner
    bne @command
@top:
    lda #E_TOP
    bne @command
@up:
    lda #104 ;E_PREVPAGE, read-only preview coordinator
    bne @command
@down:
    lda #105 ;E_NEXTPAGE
@command:
    sta se_e_command
    clc
    rts
; UI1/menu6 owns text_length as a0..2 page index. Command/prompt entry resets
; length, and every menu selection/Help open initializes it. se_e_item remains
; the existing Help H/D selection and is never used as page state.
help_toggle:
    lda se_e_ui
    cmp #1
    bne @open
    lda se_e_menu
    cmp #6
    beq close
@open:
    lda #0
    sta se_e_text_length
    sta se_e_item
    lda #1
    sta se_e_ui
    lda #6
    sta se_e_menu
    clc
    rts
help_page:
    lda se_e_key
    cmp #$86
    beq @previous
    inc se_e_text_length
    lda se_e_text_length
    cmp #3
    bcc @done
    lda #0
    beq @store
@previous:
    lda se_e_text_length
    bne :+
    lda #3
:   sec
    sbc #1
@store:
    sta se_e_text_length
@done:
    clc
    rts
next_menu:
    inc se_e_menu
    lda se_e_menu
    cmp #7
    bcc selected_menu
    lda #1
    bne selected_menu
previous_menu:
    lda se_e_menu
    cmp #2
    bcc @last_menu
    dec se_e_menu
    lda se_e_menu
    bne selected_menu
@last_menu:
    lda #6
selected_menu:
    sta se_e_menu
    lda #0
    sta se_e_item
    sta se_e_text_length ;UI1 menu selection starts keyboard page, never prompt data
    clc
    rts
heading:
    lda se_e_key
    cmp #13
    jeq next_menu
    cmp #$1D
    jeq next_menu
    cmp #$9D
    jeq previous_menu
    jsr fold_key
    ldx #5
@head:
    cmp heading_keys,x
    beq @found
    dex
    bpl @head
    clc
    rts
@found:
    inx
    txa
    jmp selected_menu
next_item:
    inc se_e_item
    ldx se_e_menu
    lda se_e_item
    cmp menu_counts-1,x
    bcc okay
    lda #0
    sta se_e_item
okay:
    clc
    rts
previous_item:
    lda se_e_item
    beq @last
    dec se_e_item
    clc
    rts
@last:
    ldx se_e_menu
    lda menu_counts-1,x
    sec
    sbc #1
    sta se_e_item
    clc
    rts
choose:
    lda se_e_menu
    sec
    sbc #1
    asl
    tax
    lda menu_commands,x
    sta text_ptr
    lda menu_commands+1,x
    sta text_ptr+1
    ldy se_e_item
    lda (text_ptr),y
    sta se_e_command
    jmp close
fold_key:
    lda se_e_key
    and #$7F
    rts
command_key:
    lda se_e_key
    cmp #13
    jeq parse
    cmp #$14
    beq erase
    cmp #32
    bcc okay
    cmp #$80
    bcc @text
    cmp #$A0
    bcc okay
@text:
    ldx se_e_text_length
    cpx #31
    bcs okay
    lda se_e_key
    sta se_e_text,x
    inx
    stx se_e_text_length
    lda #0
    sta se_e_text,x
    clc
    rts
erase:
    ldx se_e_text_length
    beq okay
    dex
    stx se_e_text_length
    lda #0
    sta se_e_text,x
    clc
    rts
parse:
    lda #<prefix_goto
    sta text_ptr
    lda #>prefix_goto
    sta text_ptr+1
    jsr argument_prefix
    jcc goto_argument
    lda #<prefix_findi
    sta text_ptr
    lda #>prefix_findi
    sta text_ptr+1
    jsr argument_prefix
    bcs :+
    lda #1
    jmp find_argument
:
    lda #<prefix_find
    sta text_ptr
    lda #>prefix_find
    sta text_ptr+1
    jsr argument_prefix
    bcs :+
    lda #0
    jmp find_argument
:
    ldx #0
@keyword:
    stx se_v_menu_index
    lda word_low,x
    sta text_ptr
    lda word_high,x
    sta text_ptr+1
    ldy #0
@letter:
    lda se_e_text,y
    and #$7F
    cmp (text_ptr),y
    bne @next
    cmp #0
    beq @match
    iny
    bne @letter
@next:
    ldx se_v_menu_index
    inx
    cpx #word_count
    bcc @keyword
    lda #$76
    sta se_e_error
    clc
    rts
@match:
    ldx se_v_menu_index
    cpx #syntax_first
    bcc @ordinary
    lda syntax_caps-syntax_first,x
    jsr settings_presentation
    jmp close
@ordinary:
    lda word_command,x
    sta se_e_command
    jmp close
argument_prefix:
    ldy #0
@next:
    lda (text_ptr),y
    beq @match
    lda se_e_text,y
    and #$7F
    cmp (text_ptr),y
    bne @miss
    iny
    bne @next
@match:
    clc
    rts
@miss:
    sec
    rts
argument_error:
    lda #$7C
    sta se_e_error
    clc
    rts
find_argument:
    pha
    tya
    eor #$FF
    sec
    adc se_e_text_length ;text_length - prefix_length
    beq @empty
    cmp #27
    bcs @empty
    sta se_s_length
    pla
    sta se_s_insensitive
    ldx #0
@copy:
    lda se_e_text,y
    sta se_s_pattern,x
    iny
    inx
    cpx se_s_length
    bcc @copy
    lda #E_FIND
    sta se_e_command
    jmp close
@empty:
    pla
    jmp argument_error
goto_argument:
    cpy se_e_text_length
    jeq argument_error
    lda #0
    sta se_g_line
    sta se_g_line+1
    sta se_g_line+2
@digit:
    lda se_e_text,y
    cmp #$30
    jcc argument_error
    cmp #$3A
    jcs argument_error
    sec
    sbc #$30
    sta se_s_byte
    COPY24 se_g_line,se_s_temp
    .repeat 2
        asl se_g_line
        rol se_g_line+1
        rol se_g_line+2
        jcs argument_error
    .endrepeat
    ADD24 se_g_line,se_s_temp,se_g_line
    jcs argument_error
    asl se_g_line
    rol se_g_line+1
    rol se_g_line+2
    jcs argument_error
    clc
    lda se_g_line
    adc se_s_byte
    sta se_g_line
    lda se_g_line+1
    adc #0
    sta se_g_line+1
    lda se_g_line+2
    adc #0
    sta se_g_line+2
    jcs argument_error
    iny
    cpy se_e_text_length
    jcc @digit
    lda se_g_line
    ora se_g_line+1
    ora se_g_line+2
    jeq argument_error
    lda #E_GOTO
    sta se_e_command
    jmp close
.segment "RODATA"
find_text: .byte $46,$49,$4E,$44,$20
goto_text: .byte $47,$4F,$54,$4F,$20
heading_keys: .byte 'f','e','v','n','b','h'
.include "editor/menu-data.inc"
word_low: .byte <w0,<w1,<w2,<w3,<w4,<w5,<w6,<w7,<w8,<w9,<w10,<w11,<w12,<w13,<w14,<w15,<w16,<w17,<w18,<w19,<w20,<w21,<w22,<w23,<w24,<w25,<w26,<w27,<w28,<w29,<w30,<w31,<w32,<w33,<w34,<w35,<w36,<w37,<w38,<w39,<w40,<w41,<w42,<w43,<w44,<w45,<w46,<w47
word_high: .byte >w0,>w1,>w2,>w3,>w4,>w5,>w6,>w7,>w8,>w9,>w10,>w11,>w12,>w13,>w14,>w15,>w16,>w17,>w18,>w19,>w20,>w21,>w22,>w23,>w24,>w25,>w26,>w27,>w28,>w29,>w30,>w31,>w32,>w33,>w34,>w35,>w36,>w37,>w38,>w39,>w40,>w41,>w42,>w43,>w44,>w45,>w46,>w47
syntax_first=43
word_count=48
syntax_caps: .byte 0,0,1,3,3
word_command: .byte E_UNDO,E_REDO,E_HOME,E_END,E_TOP,E_BOTTOM,E_JBACK,E_JFORWARD,E_DELETE,E_HELP,E_MODE40,E_MODE60,E_MODE80,E_HIRES,E_OPEN,E_SAVE,E_SAVEAS,E_COPY,E_PASTE,E_UP,E_DOWN,E_PAGEUP,E_PAGEDOWN,E_WORDLEFT,E_WORDRIGHT,E_FINDNEXT,E_FINDPROMPT,E_GOTOPROMPT,E_MARK,E_CUT,E_CLEARUNDO,E_WRAP,E_WRAP_ON,E_WRAP_OFF,E_PANLEFT,E_PANRIGHT,E_DIAG,E_FOLD,E_COLLAPSEALL,E_EXPANDALL,E_SETTINGS,102,67
w0: .asciiz "undo"
w1: .asciiz "redo"
w2: .asciiz "home"
w3: .asciiz "end"
w4: .asciiz "top"
w5: .asciiz "bottom"
w6: .asciiz "jump -40"
w7: .asciiz "jump +40"
w8: .asciiz "delete"
w9: .asciiz "help"
w10: .asciiz "mode 40"
w11: .asciiz "mode 60"
w12: .asciiz "mode 80"
w13: .asciiz "mode hires"
w14: .asciiz "open"
w15: .asciiz "save"
w16: .asciiz "save as"
w17: .asciiz "copy"
w18: .asciiz "paste"

w19: .asciiz "up"
w20: .asciiz "down"
w21: .asciiz "page up"
w22: .asciiz "page down"

prefix_goto: .asciiz "goto "
prefix_find: .asciiz "find "
prefix_findi: .asciiz "findi "
w23: .asciiz "word left"
w24: .asciiz "word right"
w25: .asciiz "next match"
w26: .asciiz "find"
w27: .asciiz "goto"

w28: .asciiz "mark"
w29: .asciiz "cut"
w30: .asciiz "clear undo"

w31: .asciiz "wrap"
w32: .asciiz "wrap on"
w33: .asciiz "wrap off"
w34: .asciiz "pan left"
w35: .asciiz "pan right"
w36: .asciiz "diag"
w37: .asciiz "fold"
w38: .asciiz "fold all"
w39: .asciiz "unfold all"
w40: .asciiz "settings"
w41: .asciiz "preview"
w42: .asciiz "source"
w43: .asciiz "syntax plain"
w44: .asciiz "syntax off"
w45: .asciiz "syntax markdown"
w46: .asciiz "syntax full"
w47: .asciiz "syntax on"

.include "overlays/editor-settings-control.s"

; UI drawing is an operation-sized R22 module. Pass no C7 pointers: all menu
; strings, diagnostics descriptors and box implementation live in that image.
; This label is local C7 dispatch/export only, never a resident/R1 call target.
.export se_ui_draw
.segment "CODE"
se_ui_draw:
    lda #0
    sta se_overlay_frame
    lda #22
    ldx #0
    jmp se_overlay_call

.segment "RODATA"
preview_mutations:
 .byte E_INSERT,E_BACK,E_DELETE,E_UNDO,E_REDO,E_CUT,E_PASTE,E_CLEARUNDO
preview_mutations_end:

.include "cache/editor/admit.inc"

.include "cache/edit-rebase-integration/menu.inc"
