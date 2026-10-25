; Optional exact-font cache. Called only after real inkentry measure/FD guards.
.setcpu "6502"
.macpack longbranch
.include "render/geos/catalog-glyph.inc"
.include "render/geos/font-store.inc"
.include "cache-font.inc"
.import se_gc_handle,se_gc_epoch,se_reu_epoch,se_reu_map
.import se_reu_logical_owner,se_reu_physical_owner,se_reu_logical,se_reu_offset
.import se_reu_length,se_reu_c64,se_reu_copy
.import glyph_pack,glyph_unpack
.export preview_cache_get,preview_cache_put
F=$8800
D=$8A00
H=$8A20
G=$8A60
ARMED=$8AA0
REMAIN=$8AA1
BASE=$EB69
RECORDS=BASE+64
.segment "CODE"
miss:
 lda #0
 clc
 rts
preview_cache_get:
 lda #0
 sta ARMED
 ; Scalar/font/window authority has just been checked by measure. Restrict
 ; this optional representation to exactBSW9/native4800/fullclip/PETSCII.
 lda F+CG_ENCODING
 ora F+CG_LEFT
 ora F+CG_TOP
 ora F+CG_NATIVE
 jne miss
 lda F+CG_NATIVE+1
 cmp #$48
 jne miss
 lda F+CG_RIGHT
 cmp #32
 jne miss
 lda F+CG_BOTTOM
 cmp #24
 jne miss
 lda F+CG_LENGTH
 cmp #$E8
 jne miss
 lda F+CG_LENGTH+1
 cmp #2
 jne miss
 lda se_gf_state+GF_ORIGIN
 cmp #2
 jne miss
 lda se_gf_state+GF_FAMILY
 and se_gf_state+GF_FAMILY+1
 cmp #$FF
 jne miss
 lda se_gf_state+GF_POINT
 cmp #9
 jne miss
 ; FD guard already authenticated currentprovider, but FE is independent.
 ldx #1
@epoch:
 lda se_gc_epoch,x
 cmp se_reu_epoch,x
 jne miss
 dex
 bpl @epoch
 ldx se_gc_handle
 jeq miss
 lda se_reu_logical_owner,x
 cmp #$FE
 jne miss
 ldy se_reu_map,x
 jeq miss
 lda se_reu_physical_owner,y
 cmp #$FE
 jne miss
 stx H+16
 sty H+17
 lda #0
 sta H+31
 sta H+32
 lda #3
 sta H+33
 ldx #15
@binding:
 lda $A000,x
 sta H,x
 dex
 bpl @binding
 ldx #1
@header_epoch:
 lda se_gc_epoch,x
 sta H+18,x
 dex
 bpl @header_epoch
 ldx #8
@fontcap:
 lda se_gf_state+GF_FAST_HANDLES,x
 sta H+20,x
 dex
 bpl @fontcap
 lda #<CACHE_FONT_CRC
 sta H+29
 lda #>CACHE_FONT_CRC
 sta H+30
 lda #<BASE
 sta se_reu_offset
 lda #>BASE
 sta se_reu_offset+1
 lda #<G
 ldx #>G
 ldy #64
 jsr request
 lda #1
 jsr se_reu_copy
 jcs cache_miss
 ; Every byte remains validated; reservedzero bytes need no expectedcopy.
 ldx #63
@reserved:
 lda G,x
 bne initialize
 dex
 cpx #34
 bcs @reserved
@compare:
 lda G,x
 cmp H,x
 bne initialize
 dex
 bpl @compare
 jmp ready
cache_miss:
 jmp miss
initialize:
 lda #0
 ldx #63
@expected_reserved:
 sta H,x
 dex
 cpx #34
 bcs @expected_reserved
 ; No oldrecord can acquire a newheader's authority. Clear all128 records
 ; before publishing the new64Bheader. Partialfailure remains cachemiss.
 lda #0
 ldx #31
@empty:
 sta D,x
 dex
 bpl @empty
 lda #128
 sta REMAIN
 lda #<RECORDS
 sta se_reu_offset
 lda #>RECORDS
 sta se_reu_offset+1
@clear:
 lda #<D
 ldx #>D
 ldy #32
 jsr request
 lda #0
 jsr se_reu_copy
 jcs cache_miss
 clc
 lda se_reu_offset
 adc #32
 sta se_reu_offset
 bcc :+
 inc se_reu_offset+1
: dec REMAIN
 bne @clear
 lda #<BASE
 sta se_reu_offset
 lda #>BASE
 sta se_reu_offset+1
 lda #<H
 ldx #>H
 ldy #64
 jsr request
 lda #0
 jsr se_reu_copy
 jcs cache_miss
ready:
 lda #1
 sta ARMED
 jsr record
 lda #1
 jsr se_reu_copy
 jcs cache_miss
 jsr glyph_unpack
 jcs cache_miss
 lda #1
 clc
 rts
preview_cache_put:
 lda ARMED
 jeq cache_miss
 jsr glyph_pack
 jcs cache_miss
 jsr record
 lda #0
 jsr se_reu_copy
 jmp cache_miss
record:
 lda F+CG_STYLE
 asl
 asl
 asl
 asl
 eor F+CG_SCREEN
 and #127
 pha
 lsr
 lsr
 lsr
 sta se_reu_offset+1
 pla
 .repeat 5
 asl
 .endrepeat
 clc
 adc #<RECORDS
 sta se_reu_offset
 lda se_reu_offset+1
 adc #>RECORDS
 sta se_reu_offset+1
 lda #<D
 ldx #>D
 ldy #32
request:
 sta se_reu_c64
 stx se_reu_c64+1
 sty se_reu_length
 lda #0
 sta se_reu_length+1
 lda se_gc_handle
 sta se_reu_logical
 rts
