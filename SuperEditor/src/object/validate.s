.setcpu "6502"
.macpack longbranch
.include "object/api.inc"
.import se_reu_epoch, se_reu_logical_owner, se_reu_physical_owner, se_reu_map
.segment "OBJECTS"
validate_index: .res 1
validate_extent: .res 1
validate_type: .res 1
.segment "CODE"
object_service_valid:
    lda se_object_epoch
    ora se_object_epoch+1
    beq stale
    lda se_object_epoch
    cmp se_reu_epoch
    bne stale
    lda se_object_epoch+1
    cmp se_reu_epoch+1
    bne stale
    clc
    rts
stale:
    lda #$30
    sec
    rts
; Entire bank ownership checked before a copy/free can start. Returns X=index.
se_object_validate:
    jsr object_service_valid
    bcs @return
    lda se_object_token_epoch
    cmp se_object_epoch
    bne token
    lda se_object_token_epoch+1
    cmp se_object_epoch+1
    bne token
    ldx se_object_id
    cpx #OBJECT_LIMIT
    bcs token
    lda object_owner,x
    cmp #3
    bcc token
    cmp #$FF
    beq token
    sta validate_type
    lda object_gen_lo,x
    cmp se_object_generation
    bne token
    lda object_gen_hi,x
    cmp se_object_generation+1
    bne token
    lda object_banks,x
    beq corrupt
    cmp #OBJECT_EXTENTS+1
    bcs corrupt
    stx validate_index
    lda #0
    sta validate_extent
@extent:
    lda validate_index
    asl
    asl
    asl
    asl
    ora validate_extent
    tax
    lda object_extents,x
    beq corrupt
    tax
    lda se_reu_logical_owner,x
    cmp validate_type
    bne corrupt
    ldy se_reu_map,x
    cmp se_reu_physical_owner,y
    bne corrupt
    inc validate_extent
    ldx validate_index
    lda validate_extent
    cmp object_banks,x
    bcc @extent
    lda #0
    clc
@return:
    rts
token:
    lda #$31
    sec
    rts
corrupt:
    lda #$34
    sec
    rts
