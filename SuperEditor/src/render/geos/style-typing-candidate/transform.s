; Genuine GG-equivalent bold/italic transform from an authenticated FE normalglyph.
.setcpu "6502"
.macpack longbranch
.include "render/geos/style-typing-candidate/transform.inc"
.export se_gst_transform
F=GST_FRAME
HI=F+GST_TEMP
LO=HI+1
ROW=HI+2
OUT=HI+3
ADV=HI+4
.segment "CODE"
se_gst_transform:
 lda F+GST_WIDTH
 jeq bad
 cmp #9
 jcs bad
 tax
 lda F+GST_STYLE
 cmp #4
 jcs bad
 lda F+GST_INVERSE
 cmp #2
 jcs bad
 ldy #8
@check:
 lda F+GST_NORMAL,y
 and forbidden,x
 jne bad
 dey
 bpl @check
 lda #0
 sta F+GST_VALID
 sta ROW
 sta OUT
 lda F+GST_STYLE
 and #1
 clc
 adc F+GST_WIDTH
 sta ADV
 lda F+GST_STYLE
 and #2
 clc
 adc ADV
 sta ADV
 sta F+GST_ADVANCE
@row:
 ldy ROW
 lda F+GST_NORMAL,y
 sta HI
 lda #0
 sta LO
 lda F+GST_STYLE
 and #1
 beq @italic
 lda HI
 lsr
 sta LO
 lda HI
 ora LO
 sta HI
 lda #0
 ror
 sta LO
@italic:
 lda F+GST_STYLE
 and #2
 beq @inverse
 lda ROW
 cmp #6
 bcs @inverse
 ldx #1
 cmp #3
 bcs @shift
 inx
@shift:
 lsr HI
 ror LO
 dex
 bne @shift
@inverse:
 lda F+GST_INVERSE
 beq @store
 ldx ADV
 lda HI
 eor prefix_hi,x
 sta HI
 lda LO
 eor prefix_lo,x
 sta LO
@store:
 ldy OUT
 lda HI
 sta F+GST_INK,y
 lda LO
 sta F+GST_INK+1,y
 inc OUT
 inc OUT
 inc ROW
 lda ROW
 cmp #9
 jcc @row
 lda #1
 sta F+GST_VALID
 lda #0
 clc
 rts
bad:
 lda #$90
 sec
 rts
.segment "RODATA"
forbidden:.byte 255,127,63,31,15,7,3,1,0
prefix_hi:.byte 0,$80,$C0,$E0,$F0,$F8,$FC,$FE,$FF,$FF,$FF,$FF
prefix_lo:.byte 0,0,0,0,0,0,0,0,0,$80,$C0,$E0
