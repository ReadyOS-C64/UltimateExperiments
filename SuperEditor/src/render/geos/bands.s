.setcpu "6502"
.macpack longbranch
SE_GEOS_BANDS_IMPLEMENTATION=1
.include "render/geos/bands.inc"
.export se_geos_bands_begin,se_geos_bands_step,se_geos_bands_hit_y
F=se_gb_frame
.macro ORDER left,right
 .local loop,done
 ldx F+GB_OFFSET
 inx
 inx
 ldy #2
loop:
 lda F+GB_LINES+left,x
 cmp F+GB_LINES+right,x
 bcc done
 jne bad_argument
 dex
 dey
 bpl loop
done:
.endmacro
.segment "GEOS_BANDS"
se_geos_bands_begin:
 lda F+GB_BUSY
 beq @new
 lda #GB_STATE
 sec
 rts
@new:
 lda #0
 sta F+GB_VALID
 sta F+GB_OUT_VALID
 sta F+GB_ERROR
 jsr header
 jcs failed
 lda #0
 sta F+GB_INDEX
 sta F+GB_RUNS
 lda #16
 sta F+GB_Y
 lda #$FF
 sta F+GB_LAST_VISIBLE
 lda #2
 sta F+GB_CURSOR
 lda #1
 sta F+GB_BUSY
 sta F+GB_STAGE
 lda F+GB_COUNT
 jne pending
 lda #1
 sta F+GB_VALID
 lda #2
 sta F+GB_STAGE
 jmp pending
header:
 lda F+GB_COUNT
 cmp #GB_LIMIT+1
 bcs @bad
 lda F+GB_ALIGN_NATIVE
 cmp #2
 bcs @bad
 clc
 rts
@bad:
 lda #GB_ARGUMENT
 sec
 rts
se_geos_bands_step:
 lda F+GB_BUSY
 jeq okay
 jsr header
 jcs failed
 lda F+GB_STAGE
 cmp #1
 beq validate
 cmp #2
 jeq strip
 lda #GB_STATE
 jmp failed
; Ten-byte stride calculation. Inputs constrained to logicalindex0..21.
offset:
 sta F+GB_OFFSET
 asl
 asl
 clc
 adc F+GB_OFFSET
 asl
 sta F+GB_OFFSET
 tax
 rts
validate:
 lda F+GB_INDEX
 cmp F+GB_COUNT
 jcs bad_argument
 jsr offset
 lda F+GB_LINES+GBL_HEIGHT,x
 cmp #8
 beq @height
 cmp #9
 jne bad_argument
@height:
 sta F+GB_LINE_BOTTOM ;temporary height
 ORDER GBL_START,GBL_END
 ORDER GBL_END,GBL_NEXT
 lda F+GB_INDEX
 beq @progress
 ; Canonical next/current adjacency, preserving skipped hidden source.
 ldx F+GB_OFFSET
 ldy #3
@chain:
 lda F+GB_LINES,x
 cmp F+GB_LINES-4,x
 jne bad_argument
 inx
 dey
 bne @chain
@progress:
 ldx F+GB_OFFSET
 ldy #3
@same:
 lda F+GB_LINES,x
 cmp F+GB_LINES+6,x
 bne @place
 inx
 dey
 bne @same
 lda F+GB_INDEX
 clc
 adc #1
 cmp F+GB_COUNT
 jne bad_argument
@place:
 lda F+GB_Y
 cmp #192
 bcs @outside
 lda F+GB_LINE_BOTTOM
 cmp #8
 bne @top
 lda F+GB_ALIGN_NATIVE
 beq @top
 lda F+GB_Y
 clc
 adc #7
 and #$F8
 sta F+GB_Y
 cmp #192
 bcs @outside
@top:
 lda F+GB_Y
 ldx F+GB_INDEX
 sta F+GB_TOPS,x
 stx F+GB_LAST_VISIBLE
 clc
 adc F+GB_LINE_BOTTOM
 cmp #192
 bcc @advance
 lda #192
@advance:
 sta F+GB_Y
 jmp @next
@outside:
 ldx F+GB_INDEX
 lda #$FF
 sta F+GB_TOPS,x
@next:
 inc F+GB_INDEX
 lda F+GB_INDEX
 cmp F+GB_COUNT
 jne pending
 lda #1
 sta F+GB_VALID
 lda #2
 sta F+GB_STAGE
 jmp pending
strip:
 lda F+GB_VALID
 cmp #1
 jne bad_state
 lda F+GB_CURSOR
 cmp #2
 jcc bad_state
 cmp #24
 jcs bad_state
 sta F+GB_ROW
 asl
 asl
 asl
 sta F+GB_STRIP_TOP
 lda #0
 sta F+GB_OUT_VALID
 sta F+GB_RUNS
 sta F+GB_SCAN
@scan:
 lda F+GB_SCAN
 cmp F+GB_COUNT
 jeq @packet
 tax
 lda F+GB_TOPS,x
 cmp #$FF
 beq @next
 sta F+GB_LINE_TOP
 lda F+GB_STRIP_TOP
 clc
 adc #8
 cmp F+GB_LINE_TOP
 bcc @next
 beq @next
 lda F+GB_SCAN
 jsr offset
 lda F+GB_LINES+GBL_HEIGHT,x
 clc
 adc F+GB_LINE_TOP
 sta F+GB_LINE_BOTTOM
 cmp F+GB_STRIP_TOP
 bcc @next
 beq @next
 lda F+GB_RUNS
 cmp #2
 jcs bad_state
 asl
 asl
 tay
 lda F+GB_SCAN
 sta F+GB_RUN0,y
 sec
 lda F+GB_LINE_TOP
 sbc F+GB_STRIP_TOP
 sta F+GB_RUN0+1,y
 bpl @cliptop
 lda #0
@cliptop:
 sta F+GB_RUN0+2,y
 sec
 lda F+GB_LINE_BOTTOM
 sbc F+GB_STRIP_TOP
 cmp #9
 bcc @clipbottom
 lda #8
@clipbottom:
 sta F+GB_RUN0+3,y
 inc F+GB_RUNS
@next:
 inc F+GB_SCAN
 jmp @scan
@packet:
 lda #1
 sta F+GB_OUT_VALID
 lda F+GB_CURSOR
 cmp #23
 beq @done
 inc F+GB_CURSOR
 jmp pending
@done:
 lda #0
 sta F+GB_BUSY
 sta F+GB_STAGE
okay:
 lda #0
 clc
return:
 rts
pending:
 lda #1
 clc
 rts
bad_state:
 lda #GB_STATE
 bne failed
bad_argument:
 lda #GB_ARGUMENT
failed:
 sta F+GB_ERROR
 pha
 lda #0
 sta F+GB_BUSY
 sta F+GB_VALID
 sta F+GB_OUT_VALID
 pla
 sec
 rts
; Query has no vertical state outside this caller frame; X mapping is separate.
se_geos_bands_hit_y:
 lda F+GB_VALID
 cmp #1
 jne query_state
 jsr header
 jcs return
 lda F+GB_HIT_Y
 cmp #200
 jcs query_argument
 cmp #16
 bcs @bottom
 lda #16
@bottom:
 cmp #192
 bcc @clamped
 lda #191
@clamped:
 sta F+GB_HIT_CLAMP
 lda F+GB_LAST_VISIBLE
 cmp #$FF
 beq @none
 cmp F+GB_COUNT
 jcs query_state
 jmp @lines
@none:
 lda F+GB_COUNT
 jne query_state
 jmp empty
@lines:
 lda #0
 sta F+GB_SCAN
@scan:
 lda F+GB_SCAN
 jsr offset
 ldx F+GB_SCAN
 lda F+GB_TOPS,x
 cmp #192
 jcs query_state
 sta F+GB_LINE_TOP
 ldx F+GB_OFFSET
 clc
 adc F+GB_LINES+GBL_HEIGHT,x
 sta F+GB_LINE_BOTTOM
 lda F+GB_HIT_CLAMP
 cmp F+GB_LINE_BOTTOM
 bcc @following
 lda F+GB_SCAN
 cmp F+GB_LAST_VISIBLE
 beq @last
 inc F+GB_SCAN
 jmp @scan
@following:
 sec
 lda F+GB_HIT_CLAMP
 sbc F+GB_LINE_TOP
 bcs @chosen
 lda #0 ;alignment gap maps to following line's first pixel
 beq @chosen
@last:
 lda F+GB_LINES+GBL_HEIGHT,x
 sec
 sbc #1
@chosen:
 sta F+GB_HIT_LOCAL
 lda F+GB_SCAN
 sta F+GB_HIT_INDEX
 lda F+GB_LINE_TOP
 sta F+GB_HIT_TOP
 lda #1
 sta F+GB_HIT_VALID
 ldx F+GB_OFFSET
 ldy #0
@anchors:
 lda F+GB_LINES,x
 sta F+GB_HIT_START,y
 inx
 iny
 cpy #9
 bne @anchors
 jmp okay
empty:
 lda #0
 sta F+GB_HIT_VALID
 sta F+GB_HIT_LOCAL
 lda #$FF
 sta F+GB_HIT_INDEX
 lda #16
 sta F+GB_HIT_TOP
 ldx #2
@source:
 lda F+GB_EMPTY_SOURCE,x
 sta F+GB_HIT_START,x
 sta F+GB_HIT_END,x
 sta F+GB_HIT_NEXT,x
 dex
 bpl @source
 jmp okay
query_state:
 lda #GB_STATE
 sec
 rts
query_argument:
 lda #GB_ARGUMENT
 sec
 rts
