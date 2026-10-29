; One authenticated real backend font copy per complete CR transaction.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "font-crc.inc"
.include "render/grid/caret/api.inc"
.import se_overlay_ids,image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi
.import se_overlay_asset,asset_epoch,se_reu_epoch,se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_gf_state,se_crc_init,se_crc_value,se_doc_invalidate
.importzp text_ptr
.export se_cr_font
C=NC_C
FCAP=C+28
H=NC_HEADER
.segment "CODE"
bad:lda #$18
 sec
 rts
se_cr_font:
 ldx #7
@same:
 lda FCAP,x
 cmp H+N_FONT,x
 jne bad
 dex
 bpl @same
 lda asset_epoch
 cmp se_reu_epoch
 jne bad
 lda asset_epoch+1
 cmp se_reu_epoch+1
 jne bad
 ldx FCAP+1
 lda se_overlay_ids,x
 cmp FCAP
 jne bad
 lda image_slot,x
 and #$81
 cmp #$80
 jne bad
 lda image_size_lo,x
 jne bad
 lda image_size_hi,x
 cmp #16
 jne bad
 lda image_crc_lo,x
 cmp FCAP+6
 jne bad
 lda image_crc_hi,x
 cmp FCAP+7
 jne bad
 txa
 and #15
 .repeat 4
 asl
 .endrepeat
 ora #8
 sta se_reu_offset+1
 txa
 .repeat 4
 lsr
 .endrepeat
 tax
 lda se_overlay_asset,x
 cmp FCAP+2
 jne bad
 sta se_reu_logical
 tax
 lda se_reu_logical_owner,x
 cmp #2
 jne bad
 lda se_reu_map,x
 cmp FCAP+3
 jne bad
 tax
 lda se_reu_physical_owner,x
 cmp #2
 jne bad
 jsr se_doc_invalidate
 lda #0
 sta se_gf_state+21 ;sticky stage/window invalidation before5000 writes
 sta se_reu_offset
 sta se_reu_c64
 sta se_reu_length
 lda #$50
 sta se_reu_c64+1
 lda #4
 sta se_reu_length+1
 lda #1
 jsr se_reu_copy
 bcs ret
 jsr se_crc_init
 lda #0
 sta text_ptr
 lda #$50
 sta text_ptr+1
 ldy #0
@byte:
 lda (text_ptr),y
 eor se_crc_value+1
 tax
 lda se_crc_value
 eor $8F00,x
 sta se_crc_value+1
 lda $8E00,x
 sta se_crc_value
 iny
 bne @byte
 inc text_ptr+1
 lda text_ptr+1
 cmp #$54
 bcc @byte
 ldx #0
 lda C+1
 cmp #80
 beq :+
 inx
: lda se_crc_value
 cmp crc_lo,x
 jne bad
 lda se_crc_value+1
 cmp crc_hi,x
 jne bad
 lda #0
 clc
ret:rts
.segment "RODATA"
crc_lo:.byte <FONT4_CRC,<FONT5_CRC
crc_hi:.byte >FONT4_CRC,>FONT5_CRC
