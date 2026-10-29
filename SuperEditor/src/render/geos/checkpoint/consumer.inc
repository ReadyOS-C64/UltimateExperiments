; Private first-classify optional source checkpoint consumption.
.include "consumer-witness.inc"
.import se_overlay_ids,se_overlay_capacity
.import image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi
.segment "GEOS_PAGE"
gsc_cap:
 ldx #0
@next:
 lda se_overlay_ids,x
 cmp #24
 bne @advance
 lda image_slot,x
 and #$7F
 cmp #1
 bne @advance
 lda image_size_lo,x
 cmp #<GSC_SEED_SIZE
 bne @bad
 lda image_size_hi,x
 cmp #>GSC_SEED_SIZE
 bne @bad
 lda image_crc_lo,x
 cmp #<GSC_SEED_CRC
 bne @bad
 lda image_crc_hi,x
 cmp #>GSC_SEED_CRC
 bne @bad
 clc
 rts
@advance:
 inx
 cpx #<se_overlay_capacity
 bcc @next
@bad:
 sec
 rts
