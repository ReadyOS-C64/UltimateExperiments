.setcpu "6502"
.macpack longbranch
.include "clipboard/api.inc"
.include "object/api.inc"
.include "document/api.inc"
.segment "BSS"
se_clip_epoch: .res 2
.segment "OBJECTS"
se_clip_token: .res 5
se_clip_length: .res 3
se_clip_active: .res 1
se_clip_busy: .res 1 ;0 idle,1 copy,2 paste
se_clip_generation: .res 2
se_clip_position: .res 3
se_clip_span: .res 3
.segment "CODE"
; Once per provider epoch; idempotent within the epoch, preserving clipboard
; across document changes. No REU allocation until a nonempty copy succeeds.
se_clip_init:
    jsr object_service_valid
    bcs @return
    lda se_clip_epoch
    cmp se_object_epoch
    bne @initialize
    lda se_clip_epoch+1
    cmp se_object_epoch+1
    beq @ok
@initialize:
    lda #0
    sta se_clip_active
    sta se_clip_busy
    sta se_clip_length
    sta se_clip_length+1
    sta se_clip_length+2
    sta se_clip_generation+1
    lda #1
    sta se_clip_generation
    lda se_object_epoch
    sta se_clip_epoch
    lda se_object_epoch+1
    sta se_clip_epoch+1
@ok:
    lda #0
    clc
@return:
    rts
se_clip_validate:
    jsr object_service_valid
    bcs @stale
    lda se_clip_epoch
    cmp se_object_epoch
    bne @stale
    lda se_clip_epoch+1
    cmp se_object_epoch+1
    bne @stale
    lda se_clip_active
    beq @ok
    cmp #1
    bne @corrupt
    DOC_TOKEN se_clip_token
    jsr se_object_validate
    bcs @return
    lda object_owner,x
    cmp #5
    bne @corrupt
    lda object_size_lo,x
    cmp se_clip_length
    bne @corrupt
    lda object_size_mid,x
    cmp se_clip_length+1
    bne @corrupt
    lda object_size_hi,x
    cmp se_clip_length+2
    bne @corrupt
    lda se_clip_length
    ora se_clip_length+1
    ora se_clip_length+2
    beq @corrupt
@ok:
    lda #0
    clc
@return:
    rts
@stale:
    lda #$50
    sec
    rts
@corrupt:
    lda #$54
    sec
    rts
