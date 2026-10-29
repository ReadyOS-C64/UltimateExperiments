; Private fixed-source narrow tile compositor, included in C33.
; Uses only its existing64B COW scratch +NR68. Font must already be admitted.
.import se_petscii_screen
TPOS=C+44 ;2, pixel->column division / absolute output tile index
TILE=C+46
LASTTILE=C+47
TCOL=C+48
SHIFT=C+49
INV=C+50
SELECT=C+51
INK=C+52
COUNT=C+53
MASK=C+54
BEST=C+55
WEIGHT=C+56
RANK=C+57
TEMP=C+58
BUF=NC_NR+58
HIST=NC_NR+44
paint_cells:
 lda OLDSEEN
 beq @new
 lda ROW
 cmp OLDROW
 bne @new
 lda OLDCOL
 jsr paint_cell
@new:
 lda NEWSEEN
 beq @done
 lda ROW
 cmp NEWROW
 bne @done
 lda NEWCOL
 jsr paint_cell
@done:
 clc
 rts
paint_cell:
 ; Exact 4/5-pixel caret mask may straddle2tiles; old/new union up to4.
 sta TEMP
 lda #0
 sta TPOS+1
 lda TEMP
 asl
 rol TPOS+1
 asl
 rol TPOS+1
 ldx W
 cpx #60
 bne @pixel
 clc
 adc TEMP
 bcc :+
 inc TPOS+1
: clc
 adc #10
 bcc @pixel
 inc TPOS+1
@pixel:
 sta TPOS
 ldx #3
@divide:
 lsr TPOS+1
 ror TPOS
 dex
 bne @divide
 lda TPOS
 sta TILE
 ; Recompute end from column rather than retaining a second16-bit pixel.
 lda TEMP
 ldx W
 cpx #60
 bne @four
 asl
 asl
 clc
 adc TEMP
 bcc :+
 inc TPOS+1
: ; highbit of col*5 is recomputed below by comparison for the last columns.
 clc
 adc #14
 jmp @end
@four:
 asl
 asl
 clc
 adc #3
@end:
 ; Pixel highbit is1 exactly for logical x>=256 (col>=50 for60,64 for80).
 ldx #0
 ldy W
 cpy #60
 bne @eighty
 ldy TEMP
 cpy #49
 bcc @endhigh
 bne @high
 cmp #3 ;col49 end259, so high; comparison not needed, alwayshigh.
 bcs @high
@eighty:
 ldy TEMP
 cpy #64
 bcc @endhigh
@high:
 inx
@endhigh:
 stx TPOS+1
 sta TPOS
 ldx #3
@enddiv:
 lsr TPOS+1
 ror TPOS
 dex
 bne @enddiv
 lda TPOS
 sta LASTTILE
@tile:
 jsr tile
 lda TILE
 cmp LASTTILE
 beq @done
 inc TILE
 bne @tile
@done:
 rts

tile:
 lda #0
 ldx #21
@clear:
 sta HIST,x
 dex
 bpl @clear
 sta TCOL
 sta SHIFT
 ; Physical tile origin8*x; identify its first contributing logical glyph.
 lda TILE
 asl
 asl
 asl
 sta TPOS
 lda #0
 rol
 sta TPOS+1
 lda W
 cmp #80
 bne @sixty
 lda TILE
 asl
 sta TCOL
 lda #$F0
 bne @mask
@sixty:
 sec
 lda TPOS
 sbc #10
 sta TPOS
 lda TPOS+1
 sbc #0
 sta TPOS+1
 bpl @quotient
 lda #2 ;tile1 begins2pixels before source origin10
 sta SHIFT
 bne @five
@quotient:
 lda TPOS+1
 bne @subtract
 lda TPOS
 cmp #5
 bcc @remainder
@subtract:
 sec
 lda TPOS
 sbc #5
 sta TPOS
 lda TPOS+1
 sbc #0
 sta TPOS+1
 inc TCOL
 bne @quotient
@remainder:
 lda #0
 sec
 sbc TPOS
 sta SHIFT
@five:
 lda #$F8
@mask:
 sta MASK
@glyph:
 lda PTR
 sta text_ptr
 lda PTR+1
 sta text_ptr+1
 ldy TCOL
 lda (text_ptr),y
 jsr se_petscii_screen
 ldx #0
 stx screen_ptr+1
 asl
 rol screen_ptr+1
 asl
 rol screen_ptr+1
 asl
 rol screen_ptr+1
 sta screen_ptr
 lda screen_ptr+1
 clc
 adc #$A8
 sta screen_ptr+1
 tya
 clc
 adc #80
 tay
 lda (text_ptr),y
 sta NC_NR+32
 tya
 clc
 adc #80
 tay
 lda (text_ptr),y
 pha
 and #1
 beq :+
 lda MASK
: sta INV
 pla
 and #6
 beq :+
 lda MASK
: jsr shift
 sta SELECT
 ldy #0
@scanline:
 lda (screen_ptr),y
 and MASK
 eor INV
 jsr shift
 sta INK
 pha
 and #15
 tax
 lda nibble,x
 sta COUNT
 pla
 lsr
 lsr
 lsr
 lsr
 tax
 lda nibble,x
 clc
 adc COUNT
 ldx NC_NR+32
 clc
 adc HIST,x
 sta HIST,x
 lda INK
 eor SELECT
 ora BUF,y
 sta BUF,y
 iny
 cpy #8
 bcc @scanline
 ldx #4
 lda W
 cmp #60
 bne :+
 inx
: txa
 clc
 adc SHIFT
 sta SHIFT
 cmp #8
 bcs @resolve
 inc TCOL
 lda TCOL
 cmp W
 jcc @glyph
@resolve:
 lda #0
 sta BEST
 sta WEIGHT
 sta RANK
 tax
@role:
 lda HIST,x
 beq @next
 cmp WEIGHT
 bcc @next
 bne @choose
 lda priority,x
 cmp RANK
 bcc @next
 beq @next
@choose:
 lda HIST,x
 sta WEIGHT
 lda priority,x
 sta RANK
 stx BEST
@next:
 inx
 cpx #14
 bcc @role
 ; One canonical physical tile index produces both exact output addresses.
 lda TILE
 sta TPOS
 lda #0
 sta TPOS+1
 ldx ROW
 inx
 inx
@row:
 clc
 lda TPOS
 adc #40
 sta TPOS
 bcc :+
 inc TPOS+1
: dex
 bne @row
 lda TPOS
 sta text_ptr
 lda TPOS+1
 clc
 adc #$40
 sta text_ptr+1
 ldx BEST
 lda palette,x
 asl
 asl
 asl
 asl
 ora #6
 ldy #0
 sta (text_ptr),y
 lda TPOS
 ldx #3
@bitmap:
 asl
 rol TPOS+1
 dex
 bne @bitmap
 sta text_ptr
 lda TPOS+1
 clc
 adc #$60
 sta text_ptr+1
 ldy #7
@store:
 lda BUF,y
 sta (text_ptr),y
 dey
 bpl @store
 rts
shift:
 ldx SHIFT
 beq @done
 bmi @left
@right:
 lsr
 dex
 bne @right
 rts
@left:
 asl
 inx
 bne @left
@done:
 rts
.segment "RODATA"
nibble:.byte 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
priority:.byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
