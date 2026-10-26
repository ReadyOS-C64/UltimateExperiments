; CR-only role0 row primitive. Actual shared PETSCII converter.
; Input W=$89C1 (60/80), ROW=$89C3 (logical0..21), P=real240B packet.
; Caller authenticates/copies genuine narrow font to5000, holds owner4, and
; invalidates cache before mutation. All flags0..7 retain native inverse/XOR.
.setcpu "6502"
.macpack longbranch
.import se_petscii_screen
.importzp text_ptr,screen_ptr
.export se_cr_raw_row
P=$88C4
W=$89C1
ROW=$89C3
F=$8880
COL=F
SHIFT=F+1
MASK=F+2
OUT=F+3
INK=F+5
PITCH=F+6
SPILL=F+7
LEFT=F+8
REVERSE=F+9
.segment "CODE"
bad:lda #$90
 sec
 rts
se_cr_raw_row:
 lda W
 cmp #60
 beq @mode
 cmp #80
 jne bad
@mode:
 lda ROW
 cmp #22
 jcs bad
 ldx W
 dex
@policy:
 lda P+80,x
 jne bad
 lda P+160,x
 and #$F8
 jne bad
 dex
 bpl @policy
 ; Every refusal above precedes any output write.
 lda #0
 sta screen_ptr
 lda #$60
 sta screen_ptr+1
 lda ROW
 clc
 adc #2
 tax
@row_address:
 clc
 lda screen_ptr
 adc #$40
 sta screen_ptr
 lda screen_ptr+1
 adc #1
 sta screen_ptr+1
 dex
 bne @row_address
 lda screen_ptr
 sta OUT
 lda screen_ptr+1
 sta OUT+1
 lda #0
 tay
@clear:
 sta (screen_ptr),y
 iny
 bne @clear
 inc screen_ptr+1
@tail:
 sta (screen_ptr),y
 iny
 cpy #64
 bcc @tail
 lda #0
 sta screen_ptr
 lda #$40
 sta screen_ptr+1
 lda ROW
 clc
 adc #2
 tax
@attribute_address:
 clc
 lda screen_ptr
 adc #40
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: dex
 bne @attribute_address
 lda #$16
 ldy #39
@attrs:
 sta (screen_ptr),y
 dey
 bpl @attrs
 lda #0
 sta COL
 lda W
 cmp #80
 jeq raw80
 lda #0
 sta SHIFT
 lda #4
 sta PITCH
 lda #5
 sta SPILL
 lda #$F0
 sta MASK
 lda W
 cmp #80
 beq @glyph
 lda #5
 sta PITCH
 lda #4
 sta SPILL
 lda #$F8
 sta MASK
 lda #2
 sta SHIFT
 lda OUT
 clc
 adc #8
 sta OUT
 bcc @glyph
 inc OUT+1
@glyph:
 lda OUT
 sta screen_ptr
 lda OUT+1
 sta screen_ptr+1
 ldx COL
 lda P,x
 jsr se_petscii_screen
 ldx #0
 stx text_ptr+1
 .repeat 3
 asl
 rol text_ptr+1
 .endrepeat
 sta text_ptr
 lda text_ptr+1
 clc
 adc #$50
 sta text_ptr+1
 ; Native bit0 inverse and bits1/2 selection/caret XOR independently.
 ldx COL
 lda P+160,x
 and #1
 sta REVERSE
 lda P+160,x
 and #6
 beq :+
 lda REVERSE
 eor #1
 sta REVERSE
: lda REVERSE
 beq :+
 lda MASK
: sta REVERSE
 lda #8
 sec
 sbc SHIFT
 sta LEFT
 ldy #7
@scanline:
 lda (text_ptr),y
 eor REVERSE
 and MASK
 sta INK
 ldx SHIFT
 beq @first
@right:
 lsr
 dex
 bne @right
@first:
 ora (screen_ptr),y
 sta (screen_ptr),y
 lda SHIFT
 cmp SPILL
 bcc @nextline
 ldx LEFT
 lda INK
@left:
 asl
 dex
 bne @left
 tax
 tya
 clc
 adc #8
 tay
 txa
 ora (screen_ptr),y
 sta (screen_ptr),y
 tya
 sec
 sbc #8
 tay
@nextline:
 dey
 bpl @scanline
 lda SHIFT
 clc
 adc PITCH
 cmp #8
 bcc @position
 and #7
 pha
 lda OUT
 clc
 adc #8
 sta OUT
 bcc :+
 inc OUT+1
: pla
@position:
 sta SHIFT
 inc COL
 lda COL
 cmp W
 jcc @glyph
 lda #0
 clc
 rts
; Two4px glyphs share one physical tile. Same converter/flags/font authority
; as above, with fixed shifts and no per-bit/tile histogram work for role0.
raw80:
 lda OUT
 sta screen_ptr
 lda OUT+1
 sta screen_ptr+1
@pair:
 jsr raw80_glyph
 .repeat 8,I
 ldy #I
 txa
 eor (text_ptr),y
 and #$F0
 sta (screen_ptr),y
 .endrepeat
 inc COL
 jsr raw80_glyph
 .repeat 8,I
 ldy #I
 txa
 eor (text_ptr),y
 and #$F0
 lsr
 lsr
 lsr
 lsr
 ora (screen_ptr),y
 sta (screen_ptr),y
 .endrepeat
 inc COL
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: lda COL
 cmp #80
 jcc @pair
 lda #0
 clc
 rts
raw80_glyph:
 ldx COL
 lda P,x
 jsr se_petscii_screen
 ldx #0
 stx text_ptr+1
 .repeat 3
 asl
 rol text_ptr+1
 .endrepeat
 sta text_ptr
 lda text_ptr+1
 clc
 adc #$50
 sta text_ptr+1
 ldx COL
 lda P+160,x
 and #1
 sta REVERSE
 lda P+160,x
 and #6
 beq :+
 lda REVERSE
 eor #1
 sta REVERSE
: lda REVERSE
 beq :+
 lda #$F0
: tax
 rts
