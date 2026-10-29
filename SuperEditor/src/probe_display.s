; M1 throwaway display/input probe. No editor or document semantics are claimed.
.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.import se_mode, se_ink_reverse, se_display_init, se_petscii_screen
.import tui_box40, tui_box_x, tui_box_y, tui_box_w, tui_box_h
.importzp text_ptr
.export p_screen, p_key
.export p_render_seq, p_atlas, p_menu, p_draw_char
.segment "ZEROPAGE"
p_font_ptr: .res 2
p_pixel_ptr: .res 2
p_attr_ptr: .res 2
p_rank_ptr: .res 2

.segment "BSS"
p_render_seq: .res 2
p_x: .res 2
p_y: .res 1
p_char: .res 1
p_advance: .res 1
p_height: .res 1
p_width: .res 1
p_row: .res 1
p_col: .res 1
p_bits: .res 2
p_start_x: .res 2
p_start_y: .res 1
p_font_kind: .res 1 ; 1 = chrome mono font in hires
p_style: .res 1
p_atlas: .res 1
p_menu: .res 1
p_font_flags: .res 1 ; hires only: bit 0 bold, bit 1 italic
p_index: .res 1
p_tmp: .res 2

.macro P_TEXT label, xx, yy, style, chrome
    lda #<label
    sta text_ptr
    lda #>label
    sta text_ptr+1
    lda #<(xx)
    sta p_x
    lda #>(xx)
    sta p_x+1
    lda #yy
    sta p_y
    lda #style
    sta p_style
    lda #chrome
    sta p_font_kind
    jsr p_draw_run
.endmacro

.segment "CODE"
p_key:
    cmp #$8C ; F8
    beq @next_mode
    cmp #$85 ; F1
    beq @menu
    cmp #$41 ; native lowercase a: atlas
    beq @atlas
    cmp #$31
    bcc @done
    cmp #$35
    bcs @done
    sec
    sbc #$31
    sta se_mode
    jmp p_screen
@next_mode:
    inc se_mode
    lda se_mode
    and #3
    sta se_mode
    jmp p_screen
@menu:
    lda p_menu
    eor #1
    sta p_menu
    jmp p_screen
@atlas:
    lda p_atlas
    eor #1
    sta p_atlas
    jmp p_screen
@done:
    rts

p_screen:
    php
    sei
    jsr se_display_init
    lda se_mode
    jeq @text
    lda #$3B
    sta $D011
    lda #$08
    sta $D018
    lda #0
    ldx #0
@bitmap:
    .repeat 32, P
        sta VIC_BITMAP+P*$100,x
    .endrepeat
    .repeat 4, P
        sta $8000+P*$100,x ; priority scratch, probe only
    .endrepeat
    inx
    bne @bitmap
    lda #((TUI_FG<<4)|TUI_BG)
@attributes:
    .repeat 4, P
        sta VIC_SCREEN+P*$100,x
    .endrepeat
    inx
    bne @attributes
@text:
    plp ; keep IRQs available during slow prototype rendering
    lda #$80
    sta se_ink_reverse
    P_TEXT p_bar,0,0,7,1
    lda #0
    sta se_ink_reverse
    lda p_atlas
    jne @atlas
    P_TEXT p_title,8,16,3,0
    P_TEXT p_case,8,40,0,0
    P_TEXT p_symbols,8,56,4,0
    lda #1
    sta p_font_flags
    P_TEXT p_strong,8,80,5,0
    lda #2
    sta p_font_flags
    P_TEXT p_emphasis,8,96,4,0
    lda #0
    sta p_font_flags
    P_TEXT p_basic,8,120,3,0
    P_TEXT p_asm,8,136,2,0
    P_TEXT p_region,8,160,6,0
    jmp @footer
@atlas:
    lda #0
    sta p_index
    sta p_font_kind
@glyph:
    lda p_index
    and #15
    sta p_tmp
    asl
    asl
    asl
    asl
    sta p_x
    lda #0
    rol
    sta p_x+1
    lda p_tmp
    asl
    clc
    adc #8
    clc
    adc p_x
    sta p_x
    bcc :+
    inc p_x+1
:
    lda p_index
    and #$70
    clc
    adc #32
    sta p_y
    lda p_index
    lsr
    lsr
    lsr
    lsr
    and #7
    sta p_style
    lda p_index
    jsr p_draw_char
    inc p_index
    bpl @glyph
@footer:
    lda #$80
    sta se_ink_reverse
    P_TEXT p_help,0,192,7,1
    lda #0
    sta se_ink_reverse
    jsr p_edge
    lda p_menu
    jeq @done
    jsr p_panel
    ; Probe menu tests common geometry; full commands are M3.
    P_TEXT p_menu_title,32,40,7,1
    P_TEXT p_menu40,32,56,7,1
    P_TEXT p_menu60,32,72,7,1
    P_TEXT p_menu80,32,88,7,1
    P_TEXT p_menuhi,32,104,7,1
@done:
    ; DisplayGet returns the completed VIC frame, not instantaneous RAM. Ensure
    ; two raster boundaries after drawing before publishing the ready sequence.
    jsr p_present
    jsr p_present
    inc p_render_seq
    bne :+
    inc p_render_seq+1
:
    rts

p_present:
@leave_top:
    lda $D012
    beq @leave_top
@next_top:
    lda $D011
    bmi @next_top
    lda $D012
    bne @next_top
    rts

p_edge:
    lda #1
    sta p_x+1
    sta p_font_kind
    lda #176
    sta p_y
    lda #7
    sta p_style
    lda se_mode
    beq @forty
    cmp #1
    beq @sixty
    lda #60 ; x = 316, final four-pixel cell
    bne @draw
@forty:
    lda #56 ; x = 312, final eight-pixel cell
    bne @draw
@sixty:
    lda #47 ; x = 303, column 59 in x=8, 5-pixel-pitch text area
@draw:
    sta p_x
    lda #88 ; screen-code uppercase X
    jmp p_draw_char

p_draw_run:
    ldy #0
    lda (text_ptr),y
    beq @done
    jsr se_petscii_screen
    jsr p_draw_char
    inc text_ptr
    bne p_draw_run
    inc text_ptr+1
    jmp p_draw_run
@done:
    rts

; A normal screen code. p_x/p_y is the cell origin; advances p_x.
p_draw_char:
    and #$7F
    sta p_char
    lda p_x
    sta p_start_x
    lda p_x+1
    sta p_start_x+1
    lda p_y
    sta p_start_y
    lda se_mode
    bne @bitmap
    jsr p_attribute_address
    ldy #0
    lda p_char
    eor se_ink_reverse
    sta (p_attr_ptr),y
    ; Color RAM address = screen offset + D800.
    lda p_attr_ptr
    sta p_pixel_ptr
    lda p_attr_ptr+1
    clc
    adc #$98
    sta p_pixel_ptr+1
    ldx p_style
    lda p_palette,x
    lsr
    lsr
    lsr
    lsr
    sta (p_pixel_ptr),y
    lda #8
    sta p_advance
    jmp p_advance_x
@bitmap:
    lda #8
    sta p_height
    lda se_mode
    cmp #3
    bne @narrow
    lda p_font_kind
    beq @geos
    lda #2
@narrow:
    cmp #1
    bne @font4
    lda #5
    sta p_advance
    lda #<p_font5
    sta p_font_ptr
    lda #>p_font5
    bne @font_base
@font4:
    lda #4
    sta p_advance
    lda #<p_font4
    sta p_font_ptr
    lda #>p_font4
@font_base:
    sta p_font_ptr+1
    lda p_char
    sta p_tmp
    lda #0
    sta p_tmp+1
    asl p_tmp
    rol p_tmp+1
    asl p_tmp
    rol p_tmp+1
    asl p_tmp
    rol p_tmp+1
    jmp @pointer
@geos:
    lda #9
    sta p_height
    ldx p_char
    lda p_bsw_width,x
    sta p_advance
    lda p_font_flags
    and #1
    beq :+
    inc p_advance
:
    lda p_font_flags
    and #2
    beq :+
    inc p_advance
    inc p_advance
:
    lda #<p_bsw
    sta p_font_ptr
    lda #>p_bsw
    sta p_font_ptr+1
    ; Screen-code index * 18 = *16 + *2.
    lda p_char
    asl
    sta p_tmp
    lda #0
    rol
    sta p_tmp+1
    lda p_char
    sta p_bits
    lda #0
    sta p_bits+1
    .repeat 4
        asl p_bits
        rol p_bits+1
    .endrepeat
    lda p_bits
    clc
    adc p_tmp
    sta p_tmp
    lda p_bits+1
    adc p_tmp+1
    sta p_tmp+1
@pointer:
    lda p_tmp
    clc
    adc p_font_ptr
    sta p_font_ptr
    lda p_tmp+1
    adc p_font_ptr+1
    sta p_font_ptr+1
    lda p_advance
    sta p_width
    lda #0
    sta p_row
@row:
    ldy #0
    lda (p_font_ptr),y
    sta p_bits
    lda #0
    sta p_bits+1
    lda p_height
    cmp #9
    bne @one_byte
    iny
    lda (p_font_ptr),y
    sta p_bits+1
    inc p_font_ptr
    bne @one_byte
    inc p_font_ptr+1
@one_byte:
    inc p_font_ptr
    bne :+
    inc p_font_ptr+1
:
    lda p_height
    cmp #9
    bne @styles_done
    lda p_font_flags
    and #1
    beq @italic
    lda p_bits
    pha
    lda p_bits+1
    pha
    lsr p_bits
    ror p_bits+1
    pla
    ora p_bits+1
    sta p_bits+1
    pla
    ora p_bits
    sta p_bits
@italic:
    lda p_font_flags
    and #2
    beq @styles_done
    lda p_row
    cmp #6
    bcs @styles_done
    lsr p_bits
    ror p_bits+1
    cmp #3
    bcs @styles_done
    lsr p_bits
    ror p_bits+1
@styles_done:
    lda #0
    sta p_col
@pixel:
    lda p_bits
    eor se_ink_reverse
    bpl @skip
    jsr p_plot
@skip:
    asl p_bits+1
    rol p_bits
    inc p_x
    bne :+
    inc p_x+1
:
    inc p_col
    lda p_col
    cmp p_width
    bcc @pixel
    lda p_start_x
    sta p_x
    lda p_start_x+1
    sta p_x+1
    inc p_y
    inc p_row
    lda p_row
    cmp p_height
    jcc @row
    lda p_start_y
    sta p_y
p_advance_x:
    lda p_start_x
    clc
    adc p_advance
    sta p_x
    lda p_start_x+1
    adc #0
    sta p_x+1
    rts

p_attribute_address:
    lda p_y
    lsr
    lsr
    lsr
    tax
    lda p_x+1
    lsr
    lda p_x
    ror
    lsr
    lsr ; X pixel >> 3, 0..39
    clc
    adc p_attr_low,x
    sta p_attr_ptr
    lda p_attr_high,x
    adc #0
    sta p_attr_ptr+1
    rts

p_plot:
    lda p_y
    cmp #200
    bcs @done
    lda p_x+1
    beq @visible
    cmp #1
    bne @done
    lda p_x
    cmp #64
    bcs @done
@visible:
    ldy p_y
    lda p_x
    and #$F8
    clc
    adc p_bitmap_low,y
    sta p_pixel_ptr
    lda p_x+1
    adc p_bitmap_high,y
    sta p_pixel_ptr+1
    lda p_x
    and #7
    tax
    ldy #0
    lda (p_pixel_ptr),y
    ora p_masks,x
    sta (p_pixel_ptr),y
    jsr p_attribute_address
    lda p_attr_ptr
    sta p_rank_ptr
    lda p_attr_ptr+1
    clc
    adc #$40
    sta p_rank_ptr+1
    ldy #0
    lda (p_rank_ptr),y
    cmp p_style
    bcs @done
    lda p_style
    sta (p_rank_ptr),y
    tax
    lda p_palette,x
    sta (p_attr_ptr),y
@done:
    rts

.include "probe_panel.s"

.segment "RODATA"
p_masks: .byte $80,$40,$20,$10,$08,$04,$02,$01
p_palette: .byte $16,$F6,$A6,$36,$76,$16,$E6,$76
p_attr_low:
.repeat 25, R
    .byte <($4000+R*40)
.endrepeat
p_attr_high:
.repeat 25, R
    .byte >($4000+R*40)
.endrepeat
p_bitmap_low: .incbin "assets/fonts/generated/bitmap-row-low.bin"
p_bitmap_high: .incbin "assets/fonts/generated/bitmap-row-high.bin"
p_font4: .incbin "assets/fonts/generated/narrow4.bin"
p_font5: .incbin "assets/fonts/generated/narrow5.bin"
p_bsw_width: .incbin "assets/fonts/generated/bsw9-widths.bin"
p_bsw: .incbin "assets/fonts/generated/bsw9.bin"
p_bar: .asciiz "File Edit View Navigate Block Help"
p_title: .asciiz "SuperEditor display probe"
p_case: .asciiz "Mixed case: Abc XYZ / il1 / 0Oo"
p_symbols: .byte "Native keys: # * : @ ",$5C,$20,$5E,$20,$5F,0
p_strong: .asciiz "Bold glyphs: Abc XYZ 0123"
p_emphasis: .asciiz "Italic glyphs: gjpqy Abc"
p_basic: .byte "10 PRINT ",$22,"Hello, C64!",$22,0
p_asm: .asciiz "lda #$00 : sta $d020 : rts"
p_region: .asciiz "[-] Region: font and color tests"
p_help: .asciiz "F1 menu  F8 mode  1-4 direct  A atlas"
p_menu_title: .asciiz "View / display probe"
p_menu40: .asciiz "1  Text 40"
p_menu60: .asciiz "2  Text 60"
p_menu80: .asciiz "3  Text 80"
p_menuhi: .asciiz "4  GEOS hires"
