; Narrow4/5px carry across a single actual VIC body row, no font decode/VIC setup.
.setcpu "6502"
.macpack longbranch
.include "shift-row.inc"
.importzp screen_ptr
.export se_lp_shift_row
PITCH=LPF+20
OTHER=LPF+21
FIRST=LPF+22
LAST=LPF+23
SHIFT=LPF+24
XLOW=LPF+25
XHI=LPF+26
BASE=LPF+27 ;2
GY=LPF+29
KEEP=LPF+30
OLD_FIRST=LPF+31
OLD_LAST=LPF+32
VALUE=LPF+33
COUNT=LPF+34
CELL=LPF+35
CELLSHIFT=LPF+36
MASK=LPF+37
LEFT=LPF+38
PART=LPF+39
HIGHMASK=LPF+40
.segment "CODE"
se_lp_shift_row:
 .ifndef LP_TRUSTED
 lda LPF+LP_WIDTH
 cmp #60
 beq @mode
 cmp #80
 jne argument
@mode:
 lda LPF+LP_ROW
 cmp #22
 jcs argument
 lda LPF+LP_COL
 cmp LPF+LP_WIDTH
 jcs argument
 lda LPF+LP_DIR
 cmp #2
 jcs argument
 .endif
 lda #4
 ldx LPF+LP_WIDTH
 cpx #60
 bne :+
 lda #5
: sta PITCH
 lda #8
 sec
 sbc PITCH
 sta OTHER
 lda #39
 ldx PITCH
 cpx #4
 beq :+
 lda #38
: sta LAST
 lda #$f0
 ldx PITCH
 cpx #4
 beq :+
 lda #$f8
: sta HIGHMASK
 ; Byte/bit location of the edited character.
 lda LPF+LP_COL
 asl
 sta XLOW
 lda #0
 rol
 sta XHI
 asl XLOW
 rol XHI
 lda PITCH
 cmp #5
 bne @x
 clc
 lda XLOW
 adc LPF+LP_COL
 sta XLOW
 bcc :+
 inc XHI
: clc
 lda XLOW
 adc #10
 sta XLOW
 bcc @x
 inc XHI
@x:
 lda XLOW
 and #7
 sta SHIFT
 ldx #3
@divide:
 lsr XHI
 ror XLOW
 dex
 bne @divide
 lda XLOW
 sta FIRST
 ; Preserve pixels before edited x, including the centered60 left margin.
 lda #$ff
 ldx SHIFT
@keep:
 cpx #0
 beq @kept
 lsr
 dex
 bne @keep
@kept:
 eor #$ff
 sta KEEP
 ; Row address: $6000 + (row+2)*320. Eight scanlines stay in this tile row.
 lda #0
 sta BASE
 lda #$60
 sta BASE+1
 ldx LPF+LP_ROW
 inx
 inx
@row:
 clc
 lda BASE
 adc #$40
 sta BASE
 lda BASE+1
 adc #1
 sta BASE+1
 dex
 bne @row
 lda #0
 sta GY
@scanline:
 clc
 lda BASE
 adc GY
 sta screen_ptr
 lda BASE+1
 adc #0
 sta screen_ptr+1
 ldx #0
@gather:
 ldy #0
 lda (screen_ptr),y
 sta LP_TEMP,x
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: inx
 cpx #40
 bcc @gather
 ldx FIRST
 lda LP_TEMP,x
 sta OLD_FIRST
 ldx LAST
 lda LP_TEMP,x
 sta OLD_LAST
 .ifndef LP_NO_CARRY
 ; Last-cell old ink normalized to high4/5bits for nextwrappedrow.
 ldy #4
 lda PITCH
 cmp #5
 bne :+
 ldy #1
: lda OLD_LAST
@last_ink:
 asl
 dey
 bne @last_ink
 and HIGHMASK
 ldx GY
 sta LPF+LP_CARRY,x
 .endif
 lda LPF+LP_DIR
 bne @delete
 ldx LAST
@insert:
 lda LP_TEMP,x
 ldy PITCH
@right_a:
 lsr
 dey
 bne @right_a
 sta VALUE
 lda LP_TEMP-1,x
 ldy OTHER
@right_b:
 asl
 dey
 bne @right_b
 ora VALUE
 sta LP_TEMP,x
 cpx FIRST
 beq @shifted
 dex
 jmp @insert
@delete:
 ldx FIRST
@left:
 lda LP_TEMP,x
 ldy PITCH
@left_a:
 asl
 dey
 bne @left_a
 sta VALUE
 lda LP_TEMP+1,x
 ldy OTHER
@left_b:
 lsr
 dey
 bne @left_b
 ora VALUE
 sta LP_TEMP,x
 cpx LAST
 beq @shifted
 inx
 jmp @left
@shifted:
 ; Keep source pixels before the edit and both centered60 margins exact.
 lda KEEP
 eor #$ff
 ldx FIRST
 and LP_TEMP,x
 sta VALUE
 lda OLD_FIRST
 and KEEP
 ora VALUE
 sta LP_TEMP,x
 lda PITCH
 cmp #5
 bne @cell
 ldx LAST
 lda LP_TEMP,x
 and #$fc
 sta VALUE
 lda OLD_LAST
 and #3
 ora VALUE
 sta LP_TEMP,x
@cell:
 lda FIRST
 sta CELL
 lda SHIFT
 sta CELLSHIFT
 lda LPF+LP_DIR
 beq @mask
 lda LAST
 sta CELL
 lda #4
 ldx PITCH
 cpx #4
 beq :+
 lda #1
: sta CELLSHIFT
@mask:
 lda HIGHMASK
 sta MASK
 lda #0
 sta LEFT
 ldy CELLSHIFT
 beq @glyph
@mask_right:
 lsr MASK
 ror LEFT
 dey
 bne @mask_right
@glyph:
 ldx GY
 lda LPF+LP_INK,x
 and HIGHMASK
 ldy CELLSHIFT
 beq @part
@glyph_right:
 lsr
 dey
 bne @glyph_right
@part:
 sta PART
 lda MASK
 eor #$ff
 ldx CELL
 and LP_TEMP,x
 ora PART
 sta LP_TEMP,x
 lda LEFT
 beq @scatter
 eor #$ff
 and LP_TEMP+1,x
 sta PART
 ldx GY
 lda LPF+LP_INK,x
 ldy #8
 sec
 tya
 sbc CELLSHIFT
 tay
 lda LPF+LP_INK,x
 and HIGHMASK
@glyph_left:
 asl
 dey
 bne @glyph_left
 ora PART
 ldx CELL
 sta LP_TEMP+1,x
@scatter:
 clc
 lda BASE
 adc GY
 sta screen_ptr
 lda BASE+1
 adc #0
 sta screen_ptr+1
 ldx #0
@write:
 lda LP_TEMP,x
 ldy #0
 sta (screen_ptr),y
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: inx
 cpx #40
 bcc @write
 inc GY
 lda GY
 cmp #8
 jcc @scanline
 lda #0
 clc
 rts
argument:
 lda #$7b
 sec
 rts
