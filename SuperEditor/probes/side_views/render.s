; Reuse the actual verified M1 drawing implementation and existing generated
; narrow4/BSW9 assets. Its unused old test page is linked but never displayed.
.include "../../src/probe_display.s"
.import sv_help,sv_render_seq
.export sv_render,sv_source,sv_source_end,sv_header_codes
.segment "BSS"
sv_index: .res 1
sv_code: .res 1
sv_font_row: .res 1
.segment "CODE"
sv_render:
    php
    sei
    jsr se_display_init
    lda #$3B
    sta $D011
    lda #8
    sta $D018
    lda #0
    tax
@clear:
    .repeat 32,P
        sta VIC_BITMAP+P*$100,x
    .endrepeat
    .repeat 4,P
        sta $8000+P*$100,x
    .endrepeat
    inx
    bne @clear
    lda #$16
@attributes:
    .repeat 4,P
        sta VIC_SCREEN+P*$100,x
    .endrepeat
    inx
    bne @attributes
    plp
    lda #0
    sta se_ink_reverse
    sta p_font_flags
    jsr sv_header
    lda sv_help
    jeq @document
    P_TEXT sv_help_title,8,24,7,0
    P_TEXT sv_help_line1,8,48,0,0
    P_TEXT sv_help_line2,8,64,0,0
    P_TEXT sv_help_line3,8,80,3,0
    P_TEXT sv_help_line4,8,104,1,0
    jmp @footer
@document:
    lda #1
    sta p_font_flags
    P_TEXT sv_heading,8,16,7,0
    lda #0
    sta p_font_flags
    P_TEXT sv_case,8,30,0,0
    lda #2
    sta p_font_flags
    P_TEXT sv_italic,8,42,4,0
    lda #0
    sta p_font_flags
    P_TEXT sv_list1,8,54,0,0
    P_TEXT sv_list2,8,66,0,0
    P_TEXT sv_code_title,8,80,6,0
    lda se_mode
    cmp #3
    bne @narrow_code
    ; GEOS prose uses real BSW metrics; code stays aligned8-pixel PETSCII.
    jsr sv_code8
    jmp @after_code
@narrow_code:
    P_TEXT sv_basic1,8,92,3,0
    P_TEXT sv_basic2,8,100,0,0
    P_TEXT sv_basic3,8,108,3,0
    P_TEXT sv_asm1,8,124,3,0
    P_TEXT sv_asm2,8,132,1,0
    P_TEXT sv_asm3,8,140,3,0
@after_code:
    P_TEXT sv_region,8,152,6,0
    lda #$80
    sta se_ink_reverse
    P_TEXT sv_selected,220,152,3,0
    lda #0
    sta se_ink_reverse
    P_TEXT sv_symbols,8,164,0,0
    P_TEXT sv_ruler,0,180,1,1
@footer:
    lda #0
    sta p_x
    sta p_x+1
    lda #192
    sta p_y
    lda #1
    sta p_style
    lda se_mode
    cmp #3
    beq @geos_footer
    lda #<sv_status80
    ldx #>sv_status80
    bne @status
@geos_footer:
    lda #<sv_status_geos
    ldx #>sv_status_geos
@status:
    sta text_ptr
    stx text_ptr+1
    jsr sv_run8
    jsr p_present
    jsr p_present
    inc sv_render_seq
    bne :+
    inc sv_render_seq+1
:   rts

; Exactly the root's frozen physical40-tile chrome ABI; no title row.
sv_header:
    lda #0
    sta sv_index
@cell:
    lda sv_index
    asl
    asl
    asl
    sta p_x
    lda #0
    rol
    sta p_x+1
    lda #0
    sta p_y
    sta p_style
    ldx sv_index
    lda sv_header_codes,x
    cmp #$5D
    bne :+
    ldy #7
    sty p_style
:   jsr sv_char8
    lda #8
    sta p_y
    lda sv_index
    asl
    asl
    asl
    sta p_x
    lda #0
    rol
    sta p_x+1
    lda #7
    sta p_style
    ldx sv_index
    lda sv_rule_codes,x
    jsr sv_char8
    inc sv_index
    lda sv_index
    cmp #40
    bcc @cell
    rts

sv_code8:
    lda #<sv_basic1
    ldx #>sv_basic1
    ldy #92
    jsr sv_code_line
    lda #<sv_basic2
    ldx #>sv_basic2
    ldy #100
    jsr sv_code_line
    lda #<sv_basic3
    ldx #>sv_basic3
    ldy #108
    jsr sv_code_line
    lda #<sv_asm1
    ldx #>sv_asm1
    ldy #124
    jsr sv_code_line
    lda #<sv_asm2
    ldx #>sv_asm2
    ldy #132
    jsr sv_code_line
    lda #<sv_asm3
    ldx #>sv_asm3
    ldy #140
sv_code_line:
    sta text_ptr
    stx text_ptr+1
    sty p_y
    lda #8
    sta p_x
    lda #0
    sta p_x+1
    lda #3
    sta p_style
sv_run8:
    ldy #0
    lda (text_ptr),y
    beq @done
    jsr se_petscii_screen
    jsr sv_char8
    inc text_ptr
    bne sv_run8
    inc text_ptr+1
    jmp sv_run8
@done:
    rts

; Small probe adapter: M1's pixel/attribute backend with full8x8 native chrome
; and aligned GEOS code, without changing that prototype's font4 fallback.
sv_char8:
    and #$7F
    sta sv_code
    lda p_x
    sta p_start_x
    lda p_x+1
    sta p_start_x+1
    lda p_y
    sta p_start_y
    lda #0
    sta p_font_ptr+1
    lda sv_code
    asl
    rol p_font_ptr+1
    asl
    rol p_font_ptr+1
    asl
    rol p_font_ptr+1
    sta p_font_ptr
    lda p_font_ptr+1
    clc
    adc #>VIC_CHARSET
    sta p_font_ptr+1
    lda #0
    sta sv_font_row
@row:
    ldy sv_font_row
    lda (p_font_ptr),y
    eor se_ink_reverse
    sta p_bits
    lda #8
    sta p_col
@pixel:
    asl p_bits
    bcc :+
    jsr p_plot
:   inc p_x
    bne :+
    inc p_x+1
:   dec p_col
    bne @pixel
    lda p_start_x
    sta p_x
    lda p_start_x+1
    sta p_x+1
    inc p_y
    inc sv_font_row
    lda sv_font_row
    cmp #8
    bcc @row
    lda p_start_y
    sta p_y
    lda p_start_x
    clc
    adc #8
    sta p_x
    lda p_start_x+1
    adc #0
    sta p_x+1
    rts
.segment "RODATA"
sv_header_codes:
.byte $5D,70,9,12,5,32,$5D,69,4,9,20,32,$5D,86,9,5,23,32,$5D
.byte 78,1,22,9,7,1,20,5,$5D,66,12,15,3,11,32,$5D,72,5,12,16,$5D
sv_rule_codes:
.repeat 40,I
 .if I=0
  .byte $6D
 .elseif I=39
  .byte $7D
 .elseif I=6 .or I=12 .or I=18 .or I=27 .or I=34
  .byte $71
 .else
  .byte $40
 .endif
.endrepeat
sv_heading: .asciiz "A PETSCII notebook"
sv_case: .asciiz "Mixed CASE: Commodore 64 / il1 I / 0Oo."
sv_italic: .asciiz "Italic: gjpqy / Abc XYZ / native PETSCII."
sv_list1: .asciiz "1. One document: prose, code and native symbols."
sv_list2: .asciiz "- Lists align; source bytes stay intact."
sv_code_title: .asciiz "C64 BASIC and assembler"
sv_basic1: .byte "10 PRINT ",$22,"Hello, C64!",$22,0
sv_basic2: .asciiz "20 FOR I=1 TO 4: PRINT I: NEXT"
sv_basic3: .asciiz "30 GOTO 10"
sv_asm1: .asciiz "loop: LDA #$01"
sv_asm2: .asciiz "      STA $D020 ; border"
sv_asm3: .asciiz "      RTS"
sv_region: .asciiz "[-] Region: visible notes"
sv_selected: .asciiz "Selected"
sv_symbols: .byte "Native keys: # * : @ ",$5C,$20,$5E,$20,$5F,0
sv_ruler: .asciiz "12345678901234567890123456789012345678901234567890123456789012345678901234567890"
sv_status80: .asciiz "80-column PROBE  F6 Help   1/2 Views"
sv_status_geos: .asciiz "GEOS BSW/9 PROBE  F6 Help  1/2 Views"
sv_help_title: .asciiz "Side preview help"
sv_help_line1: .asciiz "1: 80-column narrow PETSCII"
sv_help_line2: .asciiz "2: GEOS BSW/9 proportional prose"
sv_help_line3: .asciiz "F6: show document / help"
sv_help_line4: .asciiz "Display probe; editing is not integrated."
; Identical native source fixture for both explicit display plans. Styles and
; fold/selection samples are scripted visual examples, not a parser/editor.
sv_source:
.byte "# A PETSCII notebook",13
.byte "Mixed CASE: Commodore 64 / il1 I / 0Oo.",13
.byte "*Italic: gjpqy / Abc XYZ / native PETSCII.*",13
.byte "1. One document: prose, code and native symbols.",13
.byte "- Lists align; source bytes stay intact.",13
.byte "```BASIC",13,"10 PRINT ",$22,"Hello, C64!",$22,13
.byte "20 FOR I=1 TO 4: PRINT I: NEXT",13,"30 GOTO 10",13,"```",13
.byte "```ASM",13,"loop: LDA #$01",13,"      STA $D020 ; border",13
.byte "      RTS",13,"```",13,"::: Region: visible notes",13
.byte "Selected",13,"Native keys: # * : @ ",$5C,32,$5E,32,$5F,13
.byte ":::",13
sv_source_end:
