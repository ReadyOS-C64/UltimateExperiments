.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.include "render/geos/line.inc"
.import se_petscii_screen
.export se_geos_line_begin,se_geos_line_step,se_geos_line_finish
L=GEOS_LINE_FRAME
G=L+GL_GLYPH
M=L+GL_MAP
value=L+GL_PRIVATE
advance=value+1
position=value+2
mapped=position+2
hitx=mapped+2
distance=hitx+2
previous=distance+2
overwide=previous+2
.segment "CODE"
; Foreground caller supplies fixed frame X/Y and its existing two pointer pairs.
se_geos_line_begin:
    jsr context
    jcs return
    lda L+GL_MODE
    cmp #2
    jcs argument
    lda L+GL_ENCODING
    cmp #2
    jcs argument
    lda L+GL_WIDTH+1
    beq @low
    cmp #1
    jne argument
    lda L+GL_WIDTH
    cmp #65
    jcs argument
    bcc @width
@low:
    lda L+GL_WIDTH
    jeq argument
@width:
    clc
    lda L+GL_PAN
    adc L+GL_WIDTH
    sta L+GL_RIGHT
    lda L+GL_PAN+1
    adc L+GL_WIDTH+1
    sta L+GL_RIGHT+1
    lda L+GL_PAN+2
    adc #0
    sta L+GL_RIGHT+2
    jcs argument
    lda L+GL_ENCODING
    bne @init
    ldx #5
@font:
    lda L+GL_FONT,x
    sta G+GG_FONT,x
    dex
    bpl @font
    lda #32
    sta G+GG_VALUE
    lda #0
    sta G+GG_ENCODING
    sta G+GG_STYLE
    sta G+GG_FLAGS
    sta G+GG_CLIP_LEFT
    sta G+GG_CLIP_TOP
    lda #16
    sta G+GG_CLIP_RIGHT
    lda #9
    sta G+GG_CLIP_BOTTOM
    jsr measure
    jcs return
@init:
    lda #0
    sta L+GL_RASTER_X
    sta L+GL_RASTER_X+1
    ldx #47 ;clear state32..78, preserving callerpacket/hit inputs
    lda #0
@clear:
    sta L+GL_STATE,x
    dex
    bpl @clear
    ; RIGHT was scratch in the cleared suffix; recompute checked sum.
    clc
    lda L+GL_PAN
    adc L+GL_WIDTH
    sta L+GL_RIGHT
    lda L+GL_PAN+1
    adc L+GL_WIDTH+1
    sta L+GL_RIGHT+1
    lda L+GL_PAN+2
    adc #0
    sta L+GL_RIGHT+2
    ldx #2
@start:
    lda L+GL_START,x
    sta L+GL_SCAN,x
    sta L+GL_MAP_FIRST,x
    dex
    bpl @start
    lda #1
    sta L+GL_STATE
    lda L+GL_MODE
    bne @ready
    inc L+GL_MAP_STARTED
    lda #0
    sta M
    sta M+1
@ready:
.ifdef SE_EDITOR_GEOS_RENDERED
    jsr rendered_begin
.endif
    jsr caret
    jmp zero
se_geos_line_step:
    jsr active
    jcs return
    lda L+GL_PACKET_COUNT
    cmp #33
    jcs argument
    ldx #2
@identity:
    lda L+GL_PACKET_AT,x
    cmp L+GL_SCAN,x
    jne changed
    dex
    bpl @identity
    lda #0
    sta L+GL_USED
next:
    lda L+GL_USED
    cmp L+GL_PACKET_COUNT
    jcs zero
    lda #0
    sta overwide
    jsr caret
    ldx #GL_PACKET
    jsr packet
    sta value
.ifdef SE_EDITOR_GEOS_RENDERED
    jsr rendered_hidden
    jcs return
    cmp #1
    jeq next
    lda L+GL_MODE
    bne :+
    lda L+GL_MAP_CLOSED
    beq :+
    lda L+GL_REASON
    jmp publish_scan
:
    lda value
.endif
    cmp #13
    jeq cr
    lda L+GL_ENCODING
    beq @native
    ldx #GL_ADVANCES
    jsr packet
    jeq argument
    sta advance
    bne @advance
@native:
    lda value
    sta G+GG_VALUE
    ldx #GL_STYLES
    jsr packet
    cmp #4
    jcs argument
    sta G+GG_STYLE
    jsr measure
    jcs return
    lda G+GG_ADVANCE
    sta advance
@advance:
    clc
    lda L+GL_X
    adc advance
    sta L+GL_PENDING_X
    lda L+GL_X+1
    adc #0
    sta L+GL_PENDING_X+1
    lda L+GL_X+2
    adc #0
    sta L+GL_PENDING_X+2
    jcs range
    lda L+GL_MODE
    jne accept
    lda L+GL_PENDING_X+2
    jne overflow
    lda L+GL_PENDING_X+1
    cmp L+GL_WIDTH+1
    bcc accept
    jne overflow
    lda L+GL_PENDING_X
    cmp L+GL_WIDTH
    bcc accept
    beq accept
    jmp overflow
accept:
    ; A24-bit source anchor is checked before publication/packet consumption.
    lda L+GL_SCAN
    and L+GL_SCAN+1
    and L+GL_SCAN+2
    cmp #255
    jeq range
    jsr map_cell
    jcs return
    ldx #2
@x:
    lda L+GL_PENDING_X,x
    sta L+GL_X,x
    dex
    bpl @x
    jsr consumed
.ifdef SE_EDITOR_GEOS_RENDERED
    lda value
    cmp #32
    bne :+
    ldx #2
@render_break:
    lda GL_RENDER_EDGE,x
    sta GL_RENDER_BREAK_EDGE,x
    dex
    bpl @render_break
:
.endif
    lda overwide
    beq :+
 .ifdef SE_EDITOR_GEOS_RENDERED
    lda #GL_OVERWIDE
    sta L+GL_REASON
    lda #1
    sta L+GL_MAP_CLOSED
    jmp next
 .else
    lda #GL_OVERWIDE
    jmp publish_scan
 .endif
:
    lda L+GL_MODE
    jne next
    lda value
    cmp #32 ;literal nativeSPACE is the sole whitespace wrap opportunity
    bne @full
    lda #1
    sta L+GL_BREAK_VALID
    ldx #1
@count:
    lda L+GL_MAP_COUNT,x
    sta L+GL_BREAK_COUNT,x
    dex
    bpl @count
    ldx #2
@break:
    lda L+GL_SCAN,x
    sta L+GL_BREAK_SOURCE,x
    lda L+GL_X,x
    sta L+GL_BREAK_X,x
    dex
    bpl @break
@full:
    lda L+GL_X+1
    cmp L+GL_WIDTH+1
    jne next
    lda L+GL_X
    cmp L+GL_WIDTH
    jne next
 .ifdef SE_EDITOR_GEOS_RENDERED
    lda #GL_FULL
    sta L+GL_REASON
    lda #GL_FULL
    sta L+GL_REASON
    lda #GL_FULL
    sta L+GL_REASON
    lda #GL_FULL
    sta L+GL_REASON
    lda #1
    sta L+GL_MAP_CLOSED ;hold exact-width end through canonical hidden suffix
    jmp next
 .else
    lda #GL_FULL
    jmp publish_scan
 .endif
overflow:
    lda L+GL_MAP_COUNT
    ora L+GL_MAP_COUNT+1
    bne @existing
    ; One overwide glyph makes forward progress and keeps its clipped map.
    lda #1
    sta overwide
    jmp accept
@existing:
    lda L+GL_BREAK_VALID
    beq @hard
    ldx #1
@count:
    lda L+GL_BREAK_COUNT,x
    sta L+GL_MAP_COUNT,x
    dex
    bpl @count
    ldx #2
@rewind:
    lda L+GL_BREAK_SOURCE,x
    sta L+GL_END,x
    sta L+GL_NEXT,x
    lda L+GL_BREAK_X,x
    sta L+GL_X,x
    dex
    bpl @rewind
    lda #0
    sta L+GL_REWIND
    ldx #2
@distance:
    lda L+GL_NEXT,x
    cmp L+GL_SCAN,x
    bne @backtracked
    dex
    bpl @distance
    bmi @word
@backtracked:
    inc L+GL_REWIND
@word:
    lda #GL_WORD
    jmp ready
@hard:
    lda #GL_HARD
    jmp publish_scan
cr:
    lda L+GL_SCAN
    and L+GL_SCAN+1
    and L+GL_SCAN+2
    cmp #255
    jeq range
    jsr ensure_map
    ldx #2
@end:
    lda L+GL_SCAN,x
    sta L+GL_END,x
    dex
    bpl @end
    jsr consumed
    ldx #2
@next:
    lda L+GL_SCAN,x
    sta L+GL_NEXT,x
    dex
    bpl @next
    lda #GL_CR
    jmp ready
se_geos_line_finish:
    jsr active
    jcs return
.ifdef SE_EDITOR_GEOS_RENDERED
    lda L+GL_MODE
    bne :+
    lda L+GL_MAP_CLOSED
    beq :+
    lda L+GL_REASON
    jmp publish_scan
:
.endif
    jsr caret
    jsr ensure_map
    lda #GL_EOF
publish_scan:
    pha
    ldx #2
@end:
    lda L+GL_SCAN,x
    sta L+GL_END,x
    sta L+GL_NEXT,x
    dex
    bpl @end
    pla
ready:
    sta L+GL_REASON
.ifdef SE_EDITOR_GEOS_RENDERED
    jsr rendered_ready
.endif
    lda #2
    sta L+GL_STATE
    ; The exact end is retained only forCR/EOF. Other ends are next-line starts.
    lda L+GL_CARET_VALID
    beq zero
    ldx #2
@caret_end:
    lda L+GL_CARET,x
    cmp L+GL_END,x
    bcc zero
    bne @hide
    dex
    bpl @caret_end
    lda L+GL_REASON
    cmp #GL_EOF+1
    bcc zero
@hide:
    lda #0
    sta L+GL_CARET_VALID
zero:
    lda #0
    clc
return:
    rts
context:
    cpx #<L
    bne argument
    cpy #>L
    bne argument
    clc
    rts
active:
    jsr context
    bcs return
    lda L+GL_STATE
    cmp #1
    bne state
    clc
    rts
argument:
    lda #GL_ARGUMENT
    sec
    rts
changed:
    lda #GL_CHANGED
    sec
    rts
state:
    lda #GL_STATE_ERROR
    sec
    rts
range:
    lda #GL_RANGE
    sec
    rts
; C20 owns one fixed packed BSW9 face. Recheck its eight-byte header for
; every measured glyph so corruption introduced between BEGIN and STEP still
; fails exactly as before while deleting unrelated raster-frame validation.
measure:
    lda L+GL_FONT
    sta se_gg_pointer
    lda L+GL_FONT+1
    sta se_gg_pointer+1
    ldy #0
@header:
    lda (se_gg_pointer),y
    cmp fixed_font_header,y
    beq :+
    jmp fixed_format
:
    iny
    cpy #8
    bcc @header
    lda G+GG_VALUE
    jsr se_petscii_screen
    sta G+GG_SCREEN
    cmp #1
    bcc @at
    cmp #27
    bcc @lower
    beq @bracket
    cmp #29
    beq @bracket
    cmp #32
    bcc @fallback
    cmp #64
    bcc @ordinary
    cmp #65
    bcc @fallback
    cmp #91
    bcs @fallback
@ordinary:
    sec
    sbc #32
    bcs @mapped
@at:
    lda #32
    bne @mapped
@lower:
    clc
    adc #64
    bne @mapped
@bracket:
    clc
    adc #32
@mapped:
    lda #0
    beq @kind
@fallback:
    lda #1
@kind:
    sta G+GG_KIND
    lda L+GL_WIDTHS
    sta se_gg_pointer
    lda L+GL_WIDTHS+1
    sta se_gg_pointer+1
    ldy G+GG_SCREEN
    lda (se_gg_pointer),y
    beq fixed_format
    cmp #9
    bcs fixed_format
    tax
    lda G+GG_KIND
    beq :+
    cpx #8
    bne fixed_format
:   txa
    sta G+GG_ADVANCE
    lda G+GG_STYLE
    lsr
    bcc @italic
    inc G+GG_ADVANCE
@italic:
    lsr
    bcc @metrics
    inc G+GG_ADVANCE
    inc G+GG_ADVANCE
@metrics:
    lda #0
    clc
    rts
fixed_format:
    lda #GG_FORMAT
    sec
    rts
packet:
    lda L,x
    sta se_gg_pointer
    lda L+1,x
    sta se_gg_pointer+1
    ldy L+GL_USED
    lda (se_gg_pointer),y
    rts
consumed:
    inc L+GL_SCAN
    bne :+
    inc L+GL_SCAN+1
    bne :+
    inc L+GL_SCAN+2
:
    inc L+GL_USED
    jsr caret
    rts
caret:
    ldx #2
@match:
    lda L+GL_SCAN,x
    cmp L+GL_CARET,x
    bne @done
    dex
    bpl @match
    ldx #2
@x:
    lda L+GL_X,x
    sta L+GL_CARET_X,x
    dex
    bpl @x
    lda #1
    sta L+GL_CARET_VALID
@done:
    rts
.segment "RODATA"
fixed_font_header: .byte 6,60,0,9,8,0,204,0
.segment "CODE"
.include "render/geos/line-map.s"
.ifdef SE_EDITOR_GEOS_RENDERED
.include "render/geos/line-rendered.s"
.endif
