; Static actual-line/actual-strip composition probe, never an editor loop.
.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "render/geos/line.inc"
.include "render/geos/row.inc"
.include "render/geos/api.inc"
.include "render/narrow/api8.inc"
.exportzp text_ptr,screen_ptr
text_ptr=$F0
screen_ptr=$F2
.import se_petscii_screen,se_geos_packed,se_geos_widths,se_bitmap_cell8,tui_header40,se_print
.export probe_ready,probe_error,probe_sequence,probe_help,probe_lines,probe_meta
.export se_ink_reverse
L=GEOS_LINE_FRAME
R=GEOS_ROW_FRAME
B=$8B40
probe_meta=$8000 ;private9-byte emitted logical-line records,max24
.segment "LOADADDR"
.word $0801
.segment "BOOT"
.word boot_end
.word 10
.byte $9E,$34,$30,$39,$36,0
boot_end:.word 0
.segment "BSS"
probe_ready:.res 1
probe_error:.res 1
probe_sequence:.res 1
probe_help:.res 1
probe_lines:.res 1
se_ink_reverse:.res 1
source_at:.res 2
end_at:.res 2
next_at:.res 2
line_y:.res 1
line_kind:.res 1
meta_at:.res 1
strip:.res 1
scanline:.res 1
run_count:.res 1
phase_ptr:.res 2
run_offset:.res 2
run_chars:.res 1
run_y:.res 1
array_kind:.res 1
array_at:.res 1
copy_value:.res 1
ui_row:.res 1
ui_col:.res 1
ui_start:.res 1
ui_bottom:.res 1
ui_left:.res 1
ui_right:.res 1
.segment "ENTRY"
entry:
    sei
    lda $01
    and #$F8
    ora #6
    sta $01
    lda #0
    sta probe_ready
    sta probe_error
    sta probe_sequence
    sta probe_help
    sta se_ink_reverse
    lda #1
    sta $CC
    lda #$80
    sta $0291
    ldx #0
@font:
.repeat 4,P
    lda native_font+P*$100,x
    sta $4800+P*$100,x ;explicit valid fallback, never assumed retained
    sta $A000+P*$100,x ;checked native8 cell service's caller font
.endrepeat
    inx
    bne @font
    lda $DD00
    and #$FC
    ora #2
    sta $DD00
    lda $DD02
    ora #3
    sta $DD02
    lda #8
    sta $D018
    sta $D016
    lda #$3B
    sta $D011
    lda #0
    sta $D015
    lda #6
    sta $D020
    sta $D021
    jsr layout
    bcs failed
    jsr paint
    bcs failed
    lda #1
    sta probe_ready
    cli
idle:
    jsr K_GETIN
    cmp #$8B
    bne idle
    lda probe_help
    eor #1
    sta probe_help
    sei
    jsr paint
    bcs failed
    cli
    jmp idle
failed:
    sta probe_error
    lda #2
    sta $D020
    cli
    jmp idle
.segment "CODE"
; Native source and styles are immutable; canonical sourcebase is010000.
layout:
    lda #0
    sta source_at
    sta source_at+1
    sta probe_lines
    sta meta_at
    lda #16
    sta line_y
@line:
    lda source_at
    sta screen_ptr
    lda source_at+1
    sta screen_ptr+1
    jsr kind_at
    sta line_kind
    beq :+
    lda line_y
    clc
    adc #7
    and #$F8
    sta line_y
:
    lda #0
    sta L+GL_MODE
    sta L+GL_PAN
    sta L+GL_PAN+1
    sta L+GL_PAN+2
    sta L+GL_CARET
    sta L+GL_CARET+1
    sta L+GL_CARET+2
    lda line_kind
    sta L+GL_ENCODING
    lda #60
    ldx line_kind
    beq :+
    lda #64
:
    sta L+GL_WIDTH
    lda #1
    sta L+GL_WIDTH+1
    lda source_at
    sta L+GL_START
    lda source_at+1
    sta L+GL_START+1
    lda #1
    sta L+GL_START+2
    lda #<se_geos_packed
    sta L+GL_FONT
    lda #>se_geos_packed
    sta L+GL_FONT+1
    lda #<se_geos_widths
    sta L+GL_WIDTHS
    lda #>se_geos_widths
    sta L+GL_WIDTHS+1
    lda #0
    sta L+GL_NATIVE
    lda #$48
    sta L+GL_NATIVE+1
    ldx #<L
    ldy #>L
    jsr se_geos_line_begin
    jcs done
@step:
    lda L+GL_SCAN
    sta source_at
    sta L+GL_PACKET_AT
    lda L+GL_SCAN+1
    sta source_at+1
    sta L+GL_PACKET_AT+1
    lda #1
    sta L+GL_PACKET_AT+2
    sec
    lda #<source_size
    sbc source_at
    sta end_at
    lda #>source_size
    sbc source_at+1
    sta end_at+1
    ora end_at
    beq @finish
    lda end_at+1
    bne @packet32
    lda end_at
    cmp #33
    bcc @count
@packet32:
    lda #32
@count:
    sta L+GL_PACKET_COUNT
    ldx #0
@pointers:
    clc
    lda source_at
    adc input_lo,x
    sta L+GL_PACKET,x
    lda source_at+1
    adc input_hi,x
    sta L+GL_PACKET+1,x
    inx
    inx
    cpx #6
    bcc @pointers
    lda #<source_advances
    sta L+GL_ADVANCES
    lda #>source_advances
    sta L+GL_ADVANCES+1
    ldx #<L
    ldy #>L
    jsr se_geos_line_step
    jcs done
    lda L+GL_STATE
    cmp #2
    bne @step
    beq @record
@finish:
    ldx #<L
    ldy #>L
    jsr se_geos_line_finish
    jcs done
@record:
    ldx meta_at
    lda L+GL_START
    sta probe_meta,x
    lda L+GL_START+1
    sta probe_meta+1,x
    lda L+GL_END
    sta probe_meta+2,x
    lda L+GL_END+1
    sta probe_meta+3,x
    lda L+GL_NEXT
    sta probe_meta+4,x
    lda L+GL_NEXT+1
    sta probe_meta+5,x
    sec
    lda L+GL_END
    sbc L+GL_START
    sta probe_meta+6,x
    lda L+GL_END+1
    sbc L+GL_START+1
    jne bad
    lda probe_meta+6,x
    cmp #129
    jcs bad
    lda line_y
    sta probe_meta+7,x
    lda line_kind
    sta probe_meta+8,x
    lda line_y
    clc
    adc #9
    ldy line_kind
    beq :+
    sec
    sbc #1
:
    sta line_y
    cmp #193
    jcs bad
    inc probe_lines
    lda meta_at
    clc
    adc #9
    sta meta_at
    lda L+GL_REASON
    cmp #GL_EOF
    beq success
    lda L+GL_NEXT
    sta source_at
    lda L+GL_NEXT+1
    sta source_at+1
    jmp @line
kind_at:
    clc
    lda screen_ptr
    adc #<source_kinds
    sta screen_ptr
    lda screen_ptr+1
    adc #>source_kinds
    sta screen_ptr+1
    ldy #0
    lda (screen_ptr),y
    rts
bad:
    lda #$7B
    sec
done:
    rts
success:
    lda #0
    clc
    rts
; Every physical strip calls the actual compositor with both intersecting runs.
paint:
    lda #2
    sta strip
@strip:
    lda #0
    ldx #19
@frame:
    sta R,x
    dex
    bpl @frame
    lda strip
    sta R+GR_ROW
    lda #1
    sta R+GR_RESET
    lda #6
    sta R+GR_BACKGROUND
    lda #0
    sta R+GR_NATIVE
    lda #$48
    sta R+GR_NATIVE+1
    lda #<se_geos_packed
    sta R+GR_FONT
    lda #>se_geos_packed
    sta R+GR_FONT+1
    lda #<se_geos_widths
    sta R+GR_WIDTHS
    lda #>se_geos_widths
    sta R+GR_WIDTHS+1
    lda #<palette
    sta R+GR_PALETTE
    lda #>palette
    sta R+GR_PALETTE+1
    lda #$40
    sta R+GR_RIGHT
    lda #1
    sta R+GR_RIGHT+1
    lda #8
    sta R+GR_BOTTOM
    lda #0
    sta R+GR_RUN_POINTER
    sta run_count
    sta scanline
    lda #$8D
    sta R+GR_RUN_POINTER+1
    lda #$30
    sta phase_ptr
    lda #$8D
    sta phase_ptr+1
@line:
    lda scanline
    cmp probe_lines
    jcs @draw
    asl
    asl
    asl
    clc
    adc scanline
    tax
    lda probe_meta+8,x
    jne @next
    lda strip
    asl
    asl
    asl
    sta copy_value
    sec
    lda probe_meta+7,x
    sbc copy_value
    cmp #8
    bcc @intersect
    cmp #$F8
    jcc @next
@intersect:
    sta run_y
    lda probe_meta,x
    sta run_offset
    lda probe_meta+1,x
    sta run_offset+1
    lda probe_meta+6,x
    sta run_chars
    jsr copy_run
    jcs done
@next:
    inc scanline
    jmp @line
@draw:
    lda run_count
    sta R+GR_RUNS
    ldx #<R
    ldy #>R
    jsr se_geos_row
    jcs done
    inc strip
    lda strip
    cmp #24
    jcc @strip
    jsr mono
    jcs done
    jsr chrome
    lda probe_help
    beq @ready
    jsr help
@ready:
    inc probe_sequence
    jmp success
; Copy each caller-owned native/style/role/flag array and reserve map outputs.
copy_run:
    lda run_count
    cmp #2
    jcs bad
    lda run_count
    beq @zero
    lda #17
    bne @desc
@zero:
    lda #0
@desc:
    tax
    lda run_chars
    sta $8D00+GRR_COUNT,x
    lda run_y
    sta $8D00+GRR_Y,x
    lda #2
    sta $8D00+GRR_X,x
    lda #0
    sta $8D00+GRR_X+1,x
    lda #0
    sta array_kind
@array:
    lda run_count
    beq :+
    lda #17
:
    clc
    adc #GRR_CHARACTERS
    adc array_kind
    tax
    lda phase_ptr
    sta $8D00,x
    lda phase_ptr+1
    sta $8D01,x
    ldx array_kind
    clc
    lda run_offset
    adc array_lo,x
    sta text_ptr
    lda run_offset+1
    adc array_hi,x
    sta text_ptr+1
    lda phase_ptr
    sta screen_ptr
    lda phase_ptr+1
    sta screen_ptr+1
    ldy #0
@copy:
    cpy run_chars
    beq @advance
    lda (text_ptr),y
    sta (screen_ptr),y
    iny
    bne @copy
@advance:
    clc
    lda phase_ptr
    adc run_chars
    sta phase_ptr
    bcc :+
    inc phase_ptr+1
:
    inc array_kind
    inc array_kind
    lda array_kind
    cmp #8
    bcc @array
    lda run_count
    beq :+
    lda #17
:
    tax
    lda phase_ptr
    sta $8D00+GRR_BOUNDARIES,x
    lda phase_ptr+1
    sta $8D01+GRR_BOUNDARIES,x
    lda run_chars
    clc
    adc #1
    asl
    sta end_at
    lda #0
    rol
    sta end_at+1
    clc
    lda phase_ptr
    adc end_at
    sta phase_ptr
    lda phase_ptr+1
    adc end_at+1
    sta phase_ptr+1
    lda phase_ptr+1
    cmp #$91
    bcc :+
    jne bad
    lda phase_ptr
    cmp #$81
    jcs bad
:
    inc run_count
    jmp success
.include "geos-composed-ui.inc"
.segment "RODATA"
input_lo:.byte <source,0,<source_styles,0,<source_advances,0
input_hi:.byte >source,0,>source_styles,0,>source_advances,0
array_lo:.byte <source,0,<source_styles,0,<source_roles,0,<source_flags,0
array_hi:.byte >source,0,>source_styles,0,>source_roles,0,>source_flags,0
palette:.byte 1,3,7,10,12,12,12,7,13,5,15,7,3,1
native_font:.incbin "assets/fonts/generated/native8.bin"
.include "geos-composed-fixture.inc"
