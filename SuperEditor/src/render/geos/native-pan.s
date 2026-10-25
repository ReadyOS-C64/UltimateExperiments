; Operation-sized native8 tile compositor for unaligned horizontal origins.
.setcpu "6502"
.macpack longbranch
.include "render/geos/native-pan.inc"
.import se_f_owner,se_petscii_screen,se_gnp_palette
.importzp text_ptr,screen_ptr
F=GNP_FRAME
.export se_gnp_begin,se_gnp_step
.segment "CODE"
se_gnp_begin:
 jsr owner
 bcc :+
 rts
:
 lda F+GNP_ROW
 cmp #2
 bcc @bad
 cmp #24
 bcs @bad
 lda F+GNP_COUNT
 beq @bad
 cmp #65
 bcs @bad
 lda F+GNP_ORIGIN+1
 beq @positive
 cmp #1
 beq @upper
 cmp #$FF
 jne argument
 lda F+GNP_ORIGIN
 cmp #$F9
 bcc @bad
 bcs @pointers
@upper:
 lda F+GNP_ORIGIN
 cmp #64
 bcs @bad
@positive:
 jmp @pointers
@bad:
 lda #$90
 sec
 rts
@pointers:
 ldx #GNP_CHARS
@pointer:
 jsr pointer
 bcc :+
 rts
:
 inx
 inx
 cpx #GNP_FLAGS+2
 bne @pointer
 lda #0
 sta F+GNP_CANDIDATE
@values:
 ldx #GNP_ROLES
 jsr input
 cmp #14
 bcs @bad
 ldx #GNP_FLAGS
 jsr input
 cmp #8
 bcs @bad
 inc F+GNP_CANDIDATE
 lda F+GNP_CANDIDATE
 cmp F+GNP_COUNT
 bcc @values
 lda #0
 sta F+GNP_INDEX
 sta F+GNP_ROWBASE
 lda #$40
 sta F+GNP_ROWBASE+1
 ldx F+GNP_ROW
@row:
 clc
 lda F+GNP_ROWBASE
 adc #40
 sta F+GNP_ROWBASE
 bcc :+
 inc F+GNP_ROWBASE+1
:
 dex
 bne @row
 lda F+GNP_ORIGIN+1
 bmi @negative
 lsr
 lda F+GNP_ORIGIN
 ror
 lsr
 lsr
 sta F+GNP_TILE
 lda F+GNP_ORIGIN
 and #7
 bpl @relative
@negative:
 lda #0
 sta F+GNP_TILE
 lda F+GNP_ORIGIN
@relative:
 sta F+GNP_RELATIVE
 lda #1
 sta F+GNP_ACTIVE
 jmp pending
se_gnp_step:
 jsr owner
 bcc :+
 rts
:
 lda F+GNP_ACTIVE
 cmp #1
 jne state
 lda #0
 ldx #24
@clear:
 sta F+GNP_PIXELS,x
 dex
 bpl @clear
 lda F+GNP_INDEX
 sta F+GNP_CANDIDATE
 lda F+GNP_RELATIVE
 sta F+GNP_X
 jsr glyph
 lda F+GNP_RELATIVE
 bpl @resolve
 clc
 adc #8
 sta F+GNP_X
 inc F+GNP_CANDIDATE
 jsr glyph
@resolve:
 ldx #13
@role:
 lda F+GNP_HISTOGRAM,x
 cmp F+GNP_WEIGHT
 bcc @skip
 bne @choose
 cmp #0
 beq @skip
 lda priority,x
 cmp F+GNP_RANK
 bcc @skip
@choose:
 lda F+GNP_HISTOGRAM,x
 sta F+GNP_WEIGHT
 lda priority,x
 sta F+GNP_RANK
 stx F+GNP_BEST
@skip:
 dex
 bpl @role
 clc
 lda F+GNP_ROWBASE
 adc F+GNP_TILE
 sta screen_ptr
 lda F+GNP_ROWBASE+1
 adc #0
 sta screen_ptr+1
 ldx F+GNP_BEST
 lda se_gnp_palette,x
 asl
 asl
 asl
 asl
 ora #6
 ldy #0
 sta (screen_ptr),y
 lda screen_ptr+1
 and #3
 sta screen_ptr+1
 .repeat 3
 asl screen_ptr
 rol screen_ptr+1
 .endrepeat
 lda screen_ptr+1
 clc
 adc #$60
 sta screen_ptr+1
 ldy #7
@copy:
 lda F+GNP_PIXELS,y
 sta (screen_ptr),y
 dey
 bpl @copy
 inc F+GNP_TILE
 lda F+GNP_TILE
 cmp #40
 bcs done
 lda F+GNP_RELATIVE
 beq @advance
 bmi @advance
 sec
 sbc #8
 sta F+GNP_RELATIVE
 jmp pending
@advance:
 inc F+GNP_INDEX
 lda F+GNP_INDEX
 cmp F+GNP_COUNT
 bcc pending
done:
 lda #0
 sta F+GNP_ACTIVE
 clc
return:
 rts
pending:
 lda #1
 clc
 rts
state:
 lda #$70
 sec
 rts
argument:
 lda #$90
 sec
 rts
owner:
 lda se_f_owner
 cmp #4
 beq @ok
 lda #$B2
 sec
 rts
@ok:
 clc
 rts
; X is one checked input-pointer field. PreserveX for the BEGIN pointer loop.
pointer:
 lda F+1,x
 cmp #$8D
 bcc argument
 cmp #$8F
 bcs argument
 clc
 lda F,x
 adc F+GNP_COUNT
 tay
 lda F+1,x
 adc #0
 cmp #$8F
 bcc @ok
 bne argument
 tya
 bne argument
@ok:
 clc
 rts
input:
 lda F,x
 sta text_ptr
 lda F+1,x
 sta text_ptr+1
 ldy F+GNP_CANDIDATE
 lda (text_ptr),y
 rts
glyph:
 lda F+GNP_CANDIDATE
 cmp F+GNP_COUNT
 bcc :+
 rts
:
 ldx #GNP_ROLES
 jsr input
 sta F+GNP_ROLE
 ldx #GNP_FLAGS
 jsr input
 sta F+GNP_FLAG
 ldx #GNP_CHARS
 jsr input
 jsr se_petscii_screen
 tax
 asl
 asl
 asl
 sta text_ptr
 txa
 lsr
 lsr
 lsr
 lsr
 lsr
 ora #$48
 sta text_ptr+1
 lda F+GNP_X
 bpl :+
 eor #$FF
 clc
 adc #1
:
 sta F+GNP_SHIFT
 lda #$FF
 jsr shift
 sta F+GNP_MASK
 ldy #7
@row:
 lda F+GNP_FLAG
 and #1
 beq @normal
 lda (text_ptr),y
 eor #$FF
 jmp @shift
@normal:
 lda (text_ptr),y
@shift:
 jsr shift
 sta F+GNP_INK
 ldx #0
@bits:
 asl
 bcc :+
 inx
:
 cmp #0
 bne @bits
 txa
 ldx F+GNP_ROLE
 clc
 adc F+GNP_HISTOGRAM,x
 sta F+GNP_HISTOGRAM,x
 lda F+GNP_INK
 pha
 lda F+GNP_FLAG
 and #6
 beq :+
 pla
 eor F+GNP_MASK
 pha
:
 pla
 ora F+GNP_PIXELS,y
 sta F+GNP_PIXELS,y
 dey
 bpl @row
 rts
shift:
 ldx F+GNP_SHIFT
 beq @done
@bit:
 bit F+GNP_X
 bmi @left
 lsr
 jmp @next
@left:
 asl
@next:
 dex
 bne @bit
@done:
 rts
.segment "RODATA"
priority:.byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
