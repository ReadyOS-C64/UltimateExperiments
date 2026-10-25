.import tui_color,tui_box40,tui_box_x,tui_box_y,tui_box_w,tui_box_h
mono:
    lda #0
    sta scanline
@line:
    lda scanline
    cmp probe_lines
    jcs success
    asl
    asl
    asl
    clc
    adc scanline
    tax
    lda probe_meta+8,x
    jeq @next
    lda probe_meta,x
    sta run_offset
    lda probe_meta+1,x
    sta run_offset+1
    lda probe_meta+6,x
    sta run_chars
    lda probe_meta+7,x
    lsr
    lsr
    lsr
    sta B+BC_ROW
    lda #0
    sta ui_col
@cell:
    lda ui_col
    cmp run_chars
    bcs @next
    sta B+BC_COLUMN
    clc
    adc run_offset
    sta screen_ptr
    lda run_offset+1
    adc #0
    sta screen_ptr+1
    ldx #0
    jsr source_byte
    jsr se_petscii_screen
    sta B+BC_SCREEN
    ldx #6
    jsr source_byte
    sta copy_value
    and #1
    beq :+
    lda B+BC_SCREEN
    eor #$80
    sta B+BC_SCREEN
:
    lda copy_value
    and #6
    beq :+
    lda B+BC_SCREEN
    eor #$80
    sta B+BC_SCREEN
:
    ldx #4
    jsr source_byte
    tax
    lda palette,x
    sta B+BC_FOREGROUND
    jsr cell
    jcs done
    inc ui_col
    jmp @cell
@next:
    inc scanline
    jmp @line
source_byte:
    clc
    lda run_offset
    adc ui_col
    sta text_ptr
    lda run_offset+1
    adc #0
    sta text_ptr+1
    clc
    lda text_ptr
    adc array_lo,x
    sta text_ptr
    lda text_ptr+1
    adc array_hi,x
    sta text_ptr+1
    ldy #0
    lda (text_ptr),y
    rts
cell:
    lda #6
    sta B+BC_BACKGROUND
    lda #0
    sta B+BC_FONT
    sta B+BC_BITMAP
    sta B+BC_ATTRIBUTES
    lda #$A0
    sta B+BC_FONT+1
    lda #$60
    sta B+BC_BITMAP+1
    lda #$40
    sta B+BC_ATTRIBUTES+1
    ldx #<B
    ldy #>B
    jmp se_bitmap_cell8
chrome:
    jsr tui_header40
    ldx #39
@footer:
    lda #32
    sta $4000+960,x
    lda #15
    sta $D800+960,x
    dex
    bpl @footer
    PRINT_AT footer,24,1
    lda #0
    sta ui_start
    sta ui_left
    lda #2
    sta ui_bottom
    lda #40
    sta ui_right
    jsr convert_rect
    lda #24
    sta ui_start
    lda #25
    sta ui_bottom
    jmp convert_rect
help:
    lda #3
    sta tui_box_x
    sta ui_left
    lda #5
    sta tui_box_y
    sta ui_start
    lda #34
    sta tui_box_w
    lda #14
    sta tui_box_h
    jsr tui_box40
    lda #7
    sta tui_color
    PRINT_AT help_title,6,5
    lda #1
    sta tui_color
    PRINT_AT help_1,8,5
    PRINT_AT help_2,9,5
    PRINT_AT help_3,11,5
    PRINT_AT help_4,12,5
    lda #3
    sta tui_color
    PRINT_AT help_5,15,5
    ldx #21
@title_color:
    lda #7
    sta $D800+6*40+5,x
    dex
    bpl @title_color
    ldx #26
@hint_color:
    lda #3
    sta $D800+15*40+5,x
    dex
    bpl @hint_color
    lda #37
    sta ui_right
    lda #19
    sta ui_bottom
    jmp convert_rect
convert_rect:
    lda ui_start
    sta ui_row
@row:
    lda ui_left
    sta ui_col
@cell:
    lda #0
    ldx ui_row
    lda #$40
    sta screen_ptr+1
    lda #0
@offset:
    cpx #0
    beq @column
    clc
    adc #40
    bcc :+
    inc screen_ptr+1
:
    dex
    bne @offset
@column:
    clc
    adc ui_col
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:
    ldy #0
    lda (screen_ptr),y
    sta B+BC_SCREEN
    lda screen_ptr+1
    clc
    adc #$98
    sta screen_ptr+1
    lda (screen_ptr),y
    and #15
    sta B+BC_FOREGROUND
    lda ui_row
    sta B+BC_ROW
    lda ui_col
    sta B+BC_COLUMN
    jsr cell
    jcs done
    inc ui_col
    lda ui_col
    cmp ui_right
    jcc @cell
    inc ui_row
    lda ui_row
    cmp ui_bottom
    jcc @row
    jmp success
.segment "RODATA"
footer:.asciiz "GEOS display/layout PROBE - F6 Help"
help_title:.asciiz "GEOS composition probe"
help_1:.asciiz "Real line and strip services."
help_2:.asciiz "Packed font + native mono code."
help_3:.asciiz "Static display validation."
help_4:.asciiz "This is not an editable mode."
help_5:.asciiz "F6 closes this help window."
.segment "CODE"
