; Byte compositor for the preview aligned-band contract; no BSS/ZP.
; A27px advance atphase7 can intersect FIVE8px tiles.
PB_BITS=PP_STATE+37          ;five bytes, dead pixel scratch37..41
PB_ROW=PP_STATE+42
PB_PY=PP_STATE+43
PB_FLAG=PP_STATE+44
PB_COLOR=PP_STATE+45
PB_COUNT=PP_STATE+46
PB_MASK=PP_STATE+47
PB_COL=PP_STATE+52           ;dead PP_TEMP24 during paint
PB_SHIFT=PP_STATE+53
paint:
 lda PP_Y
 clc
 adc PP_BASELINE
 sec
 sbc F+CG_BASELINE
 sta PP_GLYPH_Y
 lda PP_PROFILE+SES_FOREGROUND
 ldx PP_ROLE
 cpx #7
 bcc @fg
 cpx #14
 bcs @fg
 lda palette,x
@fg:
 asl
 asl
 asl
 asl
 ora PP_BASE_PROFILE+SES_BACKGROUND
 sta PB_COLOR
 lda F+CG_ADVANCE
 jeq @done
 clc
 adc #7
 lsr
 lsr
 lsr
 sta PB_COUNT
 lda F+CG_ADVANCE
 and #7
 tax
 lda clip_masks,x
 sta PB_MASK
 lda PP_X
 and #7
 sta PB_SHIFT
 lda PP_X+1
 lsr
 lda PP_X
 ror
 lsr
 lsr
 sta PB_COL
 lda #0
 sta PB_ROW
@row:
 lda PB_ROW
 cmp F+CG_HEIGHT
 jcs @done
 pha
 lda #0
 ldx #4
@zero:
 sta PB_BITS,x
 dex
 bpl @zero
 pla
 asl
 asl
 tax
 ldy #0
@copy:
 lda F+CG_INK,x
 sta PB_BITS,y
 inx
 iny
 cpy PB_COUNT
 bne @copy
 ; Respect final advance, including inline-code fixed advance.
 dey
 lda PB_BITS,y
 and PB_MASK
 sta PB_BITS,y
@shift:
 ldx PB_SHIFT
 beq @pointers
@bit:
 lsr PB_BITS
 ror PB_BITS+1
 ror PB_BITS+2
 ror PB_BITS+3
 ror PB_BITS+4
 dex
 bne @bit
@pointers:
 lda PB_ROW
 clc
 adc PP_GLYPH_Y
 sta PB_PY
 lsr
 lsr
 lsr
 tax
 lda PP_X
 and #$F8
 clc
 adc row_lo,x
 sta screen_ptr
 lda PP_X+1
 adc row_hi,x
 sta screen_ptr+1
 lda PB_PY
 and #7
 clc
 adc screen_ptr
 sta screen_ptr ;8-aligned base plus0..7 cannot carry
 lda attr_lo,x
 clc
 adc PB_COL
 sta text_ptr
 lda attr_hi,x
 adc #0
 sta text_ptr+1
 ; Relative bandrow*40 +firsttile. All preview bands are8px aligned.
 lda PB_PY
 sec
 sbc PP_Y
 and #$F8
 sta PB_FLAG
 asl
 asl
 clc
 adc PB_FLAG
 clc
 adc PB_COL
 sta PB_FLAG
 ldx #0
@tile:
 lda PB_BITS,x
 beq @next
 ldy #0
 ora (screen_ptr),y
 sta (screen_ptr),y
 ldy PB_FLAG
 lda PP_TILE_FLAGS,y
 bne @next
 lda #1
 sta PP_TILE_FLAGS,y
 txa
 tay
 lda PB_COLOR
 sta (text_ptr),y
@next:
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
:
 inc PB_FLAG
 inx
 cpx #5
 bne @tile
 inc PB_ROW
 jmp @row
@done:
 rts
