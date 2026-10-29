; Actual pure-lexer adapter + alignednative8 row primitive. Not a cache publisher.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "render/geos/code-typing-candidate/api.inc"
.include "supermark/api.inc"
.import se_sl_init,se_sl_feed,se_sl_next,se_sl_finish,se_sl_count
.import se_sl_start,se_sl_end,se_sl_style
.import se_petscii_screen
.importzp text_ptr,screen_ptr
.export se_gct_lex,se_gct_paint
.segment "CODE"
bad:
 lda #$90
 sec
 rts
se_gct_lex:
 lda GCT_COUNT
 cmp #40
 jcs bad
 lda GCT_LANGUAGE
 jeq bad
 cmp #3
 jcs bad
 jsr se_sl_init
 lda #4
 ldx #39
: sta GP_ROLES,x
 dex
 bpl :-
 lda #0
 sta GCT_INDEX
@feed:
 ldx GCT_INDEX
 cpx GCT_COUNT
 beq @finish
 lda GP_SOURCE,x
 jsr se_sl_feed
 jcs bad
 jsr drain
 jcs bad
 inc GCT_INDEX
 bne @feed
@finish:
 jsr se_sl_finish
 jcs bad
 jmp drain
drain:
 lda se_sl_count
 beq @done
 jsr se_sl_next
 jcs bad
 lda se_sl_start+1
 ora se_sl_start+2
 ora se_sl_end+1
 ora se_sl_end+2
 jne bad
 lda se_sl_start
 cmp se_sl_end
 jcs bad
 tax
 lda se_sl_end
 cmp GCT_COUNT
 bcc :+
 jne bad
: sta GCT_END
 lda se_sl_style
 cmp #7
 jcc bad
 cmp #14
 jcs bad
@span:
 sta GP_ROLES,x
 inx
 cpx GCT_END
 bcc @span
 jmp drain
@done:
 lda #0
 clc
 rts
se_gct_paint:
 lda GCT_FLAGS
 cmp #2
 jcs bad
 lda GCT_COUNT
 cmp #40
 jcs bad
 lda GCT_CARET
 cmp GCT_COUNT
 bcc :+
 jne bad
: lda GCT_TOP
 cmp #16
 jcc bad
 cmp #185
 jcs bad
 and #7
 jne bad
 ldx #39
@roles:
 lda GP_ROLES,x
 cmp #14
 jcs bad
 dex
 bpl @roles
 lda GCT_TOP
 lsr
 lsr
 lsr
 tax
 and #3
 .repeat 6
 asl
 .endrepeat
 sta screen_ptr
 sta GCT_BITMAP
 txa
 lsr
 lsr
 clc
 adc #$60
 stx GCT_COLUMN
 adc GCT_COLUMN
 sta screen_ptr+1
 sta GCT_BITMAP+1
 sec
 sbc #$60
 sta GCT_ATTRIBUTES+1
 lda GCT_BITMAP
 sta GCT_ATTRIBUTES
 .repeat 3
 lsr GCT_ATTRIBUTES+1
 ror GCT_ATTRIBUTES
 .endrepeat
 lda GCT_ATTRIBUTES+1
 clc
 adc #$40
 sta GCT_ATTRIBUTES+1
 lda #0
 sta GCT_COLUMN
@cell:
 ldx GCT_COLUMN
 cpx GCT_COUNT
 bcs @blank
 lda GP_SOURCE,x
 jsr se_petscii_screen
 jmp @glyph
@blank:
 lda #32
@glyph:
 sta GCT_GLYPH
 asl
 asl
 asl
 sta text_ptr
 lda GCT_GLYPH
 lsr
 lsr
 lsr
 lsr
 lsr
 and #3
 ora #$48
 sta text_ptr+1
 ldy #7
@row:
 lda (text_ptr),y
 bit GCT_GLYPH
 bpl :+
 eor #$FF
:
 ldx GCT_COLUMN
 cpx GCT_CARET
 bne :+
 ldx GCT_FLAGS
 bne :+
 eor #$FF
: sta (screen_ptr),y
 dey
 bpl @row
 lda #1
 ldx GCT_COLUMN
 cpx GCT_COUNT
 bcs @attribute
@color:
 ldy GP_ROLES,x
 lda palette,y
@attribute:
 asl
 asl
 asl
 asl
 ora #6
 sta GCT_FOREGROUND
 clc
 lda GCT_ATTRIBUTES
 adc GCT_COLUMN
 sta text_ptr
 lda GCT_ATTRIBUTES+1
 adc #0
 sta text_ptr+1
 ldy #0
 lda GCT_FOREGROUND
 sta (text_ptr),y
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: inc GCT_COLUMN
 lda GCT_COLUMN
 cmp #40
 jcc @cell
 lda #0
 clc
 rts
.segment "RODATA"
palette:.byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
