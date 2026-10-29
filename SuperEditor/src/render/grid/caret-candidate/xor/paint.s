; Exact selector-union delta over a certified unchanged narrow row.
; NR inverse/char/role are unchanged. Arbitration uses base ink, so attributes
; cannot change. XOR only cells whose (SELECTED|CARET) boolean changed.
CHANGE=C+44 ;A/B counts
CELLA=C+46 ;two column ordinals
CELLB=C+48 ;two column ordinals
WAS=C+50
PX=C+51 ;2
RIGHTMASK=C+53
LEFTMASK=C+54
CELLPTR=C+55 ;2
LEFT=C+57
DELTAFLAG=C+58
xor_changes:
 ldx #0
 lda PTR
 cmp #<P
 beq @first
 inx
@first:
 lda CHANGE,x
 beq @done
 sta LEFT
 txa
 asl
 clc
 adc #<CELLA
 sta CELLPTR
 lda #>CELLA
 adc #0
 sta CELLPTR+1
@cell:
 lda CELLPTR
 sta text_ptr
 lda CELLPTR+1
 sta text_ptr+1
 ldy #0
 lda (text_ptr),y
 jsr xor_cell
 inc CELLPTR
 bne :+
 inc CELLPTR+1
: dec LEFT
 bne @cell
@done:
 clc
 rts
xor_cell:
 sta DELTAFLAG
 lda #0
 sta PX+1
 lda DELTAFLAG
 asl
 rol PX+1
 asl
 rol PX+1
 ldx W
 cpx #60
 bne @four
 clc
 adc DELTAFLAG
 bcc :+
 inc PX+1
: clc
 adc #10
 bcc :+
 inc PX+1
: ldx #$F8
 bne @pixel
@four:
 ldx #$F0
@pixel:
 pha
 and #7
 tay
 stx RIGHTMASK
 lda #0
 sta LEFTMASK
 cpy #0
 beq @mask
@shift:
 lsr RIGHTMASK
 ror LEFTMASK
 dey
 bne @shift
@mask:
 pla
 and #$F8
 sta PX
 ldx ROW
 inx
 inx
@row:
 clc
 lda PX
 adc #$40
 sta PX
 lda PX+1
 adc #1
 sta PX+1
 dex
 bne @row
 lda PX
 sta text_ptr
 lda PX+1
 clc
 adc #$60
 sta text_ptr+1
 ldy #7
@right:
 lda (text_ptr),y
 eor RIGHTMASK
 sta (text_ptr),y
 dey
 bpl @right
 lda LEFTMASK
 beq @done
 ldy #15
@left:
 lda (text_ptr),y
 eor LEFTMASK
 sta (text_ptr),y
 dey
 cpy #7
 bne @left
@done:
 rts
