; Executable5000 borrower. All legal writers already clear GF_VALID beforewrite.
.setcpu "6502"
.macpack longbranch
.include "stage-constants.inc"
.include "render/geos/font-store.inc"
.import se_f_owner,se_reu_retired,se_reu_epoch,se_reu_logical_owner
.import se_reu_map,se_reu_physical_owner,se_overlay_asset,asset_epoch
.import se_overlay_ids,image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_overlay_loads,se_crc_init,se_crc_byte,se_crc_value,se_doc_invalidate
.importzp text_ptr
.export se_gct_stage
S=se_gf_state
IDX=$8BF0
HANDLE=$8BF1
PHYSICAL=$8BF2
EPOCH=$8BF3
STAMP=$5C80
.assert $5000+GCT_STAGE_LENGTH<=STAMP,error,"executable lexer overlapswindow witness"
.segment "CODE"
se_gct_stage:
 lda se_f_owner
 cmp #4
 jne foreign
 lda se_reu_retired
 jne stale
 lda se_reu_epoch
 ora se_reu_epoch+1
 jeq stale
 ldx #1
@epoch:
 lda asset_epoch,x
 cmp se_reu_epoch,x
 jne stale
 sta EPOCH,x
 dex
 bpl @epoch
 lda se_overlay_asset
 jeq stale
 ldx #3
@handles:
 lda se_overlay_asset,x
 beq @next
 tay
 lda se_reu_logical_owner,y
 cmp #2
 jne stale
@next:
 dex
 bpl @handles
 ldx #0
@find:
 lda se_overlay_ids,x
 cmp #GCT_STAGE_ID
 bne @advance
 lda image_slot,x
 cmp #1
 beq @found
@advance:
 inx
 cpx #64
 bcc @find
 lda #$17
 jmp fail
@found:
 stx IDX
 lda image_size_lo,x
 cmp #<GCT_STAGE_IMAGE_LENGTH
 jne format
 lda image_size_hi,x
 cmp #>GCT_STAGE_IMAGE_LENGTH
 jne format
 lda image_crc_lo,x
 cmp #<GCT_STAGE_IMAGE_CRC
 jne format
 lda image_crc_hi,x
 cmp #>GCT_STAGE_IMAGE_CRC
 jne format
 txa
 lsr
 lsr
 lsr
 lsr
 tax
 lda se_overlay_asset,x
 jeq stale
 sta HANDLE
 tax
 lda se_reu_map,x
 jeq stale
 sta PHYSICAL
 tax
 lda se_reu_physical_owner,x
 cmp #2
 jne stale
 ; Exact sharednamespace41 plus immutablecapabilitygraph owns this lifetime.
 lda S+GF_VALID
 cmp #GCT_STAGE_VALID
 bne prime
 lda S+GF_FACE
 cmp #$FF
 bne prime
 ldx #4
@witness:
 lda IDX,x
 cmp STAMP,x
 bne prime
 dex
 bpl @witness
 lda #0
 clc
 rts
prime:
 lda #0
 sta S+GF_VALID
 lda #$FF
 sta S+GF_FACE
 ; Check actual resident-binding bytes fromthe authoritativeassetbacking.
 jsr request
 lda #0
 sta se_reu_c64
 lda #$80
 sta se_reu_c64+1
 lda #$80
 sta se_reu_c64
 lda #16
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 lda #1
 jsr se_reu_copy
 jcs fail
 ldx #15
@binding:
 lda $8080,x
 cmp $A000,x
 jne abi
 dex
 bpl @binding
 jsr request
 lda #GCT_STAGE_OFFSET
 sta se_reu_offset
 lda #0
 sta se_reu_c64
 lda #$50
 sta se_reu_c64+1
 lda #<GCT_STAGE_LENGTH
 sta se_reu_length
 lda #>GCT_STAGE_LENGTH
 sta se_reu_length+1
 lda #1
 jsr se_reu_copy
 jcs fail
 ; No execution from5000 until complete trustedCRC haspassed.
 jsr se_crc_init
 lda #0
 sta text_ptr
 lda #$50
 sta text_ptr+1
 lda #<GCT_STAGE_LENGTH
 sta se_reu_length
 lda #>GCT_STAGE_LENGTH
 sta se_reu_length+1
 ldy #0
@crc:
 lda (text_ptr),y
 jsr se_crc_byte
 inc text_ptr
 bne :+
 inc text_ptr+1
: lda se_reu_length
 bne :+
 dec se_reu_length+1
: dec se_reu_length
 lda se_reu_length
 ora se_reu_length+1
 bne @crc
 lda se_crc_value
 cmp #<GCT_STAGE_CRC
 jne format
 lda se_crc_value+1
 cmp #>GCT_STAGE_CRC
 jne format
 ldx #4
@stamp:
 lda IDX,x
 sta STAMP,x
 dex
 bpl @stamp
 lda se_overlay_loads
 sta S+GF_LOADS
 lda se_overlay_loads+1
 sta S+GF_LOADS+1
 lda #GCT_STAGE_VALID
 sta S+GF_VALID
 lda #0
 clc
 rts
request:
 lda HANDLE
 sta se_reu_logical
 lda #0
 sta se_reu_offset
 lda IDX
 and #15
 asl
 asl
 asl
 asl
 sta se_reu_offset+1
 rts
stale:
 lda #$18
 bne fail
format:
 lda #$94
 bne fail
abi:
 lda #$11
fail:
 pha
 lda #0
 sta S+GF_VALID
 pla
 sec
 rts
foreign:
 lda #$B2
 sec
 rts
