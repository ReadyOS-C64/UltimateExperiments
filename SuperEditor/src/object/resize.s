.setcpu "6502"
.include "object/api.inc"
.segment "CODE"
; Publish committed length from request offset24 after staged writes succeed.
; Does not initialize newly exposed bytes; only the owning document service may
; grow after writing them. Shrink does not erase backing storage.
se_object_resize:
    jsr se_object_validate
    bcs @return
    lda se_object_offset+2
    cmp object_banks,x
    bcc @valid
    bne @range
    lda se_object_offset
    ora se_object_offset+1
    bne @range
@valid:
    lda se_object_offset
    sta object_size_lo,x
    lda se_object_offset+1
    sta object_size_mid,x
    lda se_object_offset+2
    sta object_size_hi,x
    lda #0
    clc
@return:
    rts
@range:
    lda #$32
    sec
    rts
