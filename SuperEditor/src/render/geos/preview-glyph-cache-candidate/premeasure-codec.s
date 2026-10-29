; Pure private compact32B BSW9 ink record. NOT a cache/capability authority.
; Caller must first perform actual FD/face guard and FE lifetime admission.
; Fixed actual internal frame8800, record8A00; owner4, no BSS/ZP.
.setcpu "6502"
.macpack longbranch
.include "render/geos/catalog-glyph.inc"
.include "render/geos/preview.inc"
.import se_f_owner,se_crc_init,se_crc_byte,se_crc_value
.export glyph_pack,glyph_unpack
F=$8800
D=$8A00
.segment "CODE"
bad:
 lda #$90
 sec
 rts
fixed_kind:
 lda PP_CODE
 bne @yes
 lda PP_ROLE
 cmp #4
 beq @yes
 lda #0
 rts
@yes:
 lda #1
 rts
crc:
 jsr se_crc_init
 ldy #1
@byte:
 lda D,y
 jsr se_crc_byte
 iny
 cpy #28
 bne @byte
 rts
glyph_pack:
 ; Internal PUT follows genuine full measure+raster only. Its metrics are
 ; already authoritative; retain lossless compacting and independent GET checks.
 ; Refuse any lossy compacting, even if a caller forged metrics.
 ldx #0
@low:
 lda F+CG_INK+2,x
 ora F+CG_INK+3,x
 jne bad
 inx
 inx
 inx
 inx
 cpx #36
 bne @low
 lda #0
 sta D ;unpublished until complete payload+CRC
 sta D+30
 sta D+31
 lda F+CG_VALUE
 sta D+1
 lda F+CG_STYLE
 sta D+2
 lda F+CG_FLAGS
 sta D+3
 jsr fixed_kind
 sta D+9
 ldx #4
@metrics:
 lda F+CG_SCREEN,x
 sta D+4,x
 dex
 bpl @metrics
 ldx #0
 ldy #10
@ink:
 lda F+CG_INK,x
 sta D,y
 lda F+CG_INK+1,x
 sta D+1,y
 inx
 inx
 inx
 inx
 iny
 iny
 cpx #36
 bne @ink
 jsr crc
 lda se_crc_value
 sta D+28
 lda se_crc_value+1
 sta D+29
 lda #$A1
 sta D
 clc
done:
 rts
corrupt:
 lda #$94
 sec
 rts
glyph_unpack:
 lda #0
 sta F+CG_VALID
 lda D
 cmp #$A1
 jne corrupt
 lda D+1
 cmp F+CG_VALUE
 jne corrupt
 lda D+2
 cmp F+CG_STYLE
 jne corrupt
 lda D+3
 cmp F+CG_FLAGS
 jne corrupt
 lda D+30
 ora D+31
 jne corrupt
 jsr fixed_kind
 cmp D+9
 jne corrupt
 lda D+4
 cmp F+CG_SCREEN
 jne corrupt
 lda D+5
 cmp #12
 jcs corrupt
 lda F+CG_STYLE
 and #3
 clc
 adc D+5
 cmp D+6
 jne corrupt
 lda D+7
 cmp #9
 jne corrupt
 lda D+8
 cmp #6
 jne corrupt
 jsr crc
 lda se_crc_value
 cmp D+28
 jne corrupt
 lda se_crc_value+1
 cmp D+29
 jne corrupt
 ldx #4
@metrics:
 lda D+4,x
 sta F+CG_SCREEN,x
 dex
 bpl @metrics
 ldx #0
 ldy #10
@ink:
 lda D,y
 sta F+CG_INK,x
 lda D+1,y
 sta F+CG_INK+1,x
 lda #0
 sta F+CG_INK+2,x
 sta F+CG_INK+3,x
 inx
 inx
 inx
 inx
 iny
 iny
 cpx #36
 bne @ink
 lda #2
 sta F+CG_VALID
 clc
 rts
