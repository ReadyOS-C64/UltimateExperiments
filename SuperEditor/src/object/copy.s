.setcpu "6502"
.macpack longbranch
.include "object/api.inc"
.import se_reu_copy, se_reu_c64, se_reu_offset, se_reu_length, se_reu_logical
.segment "OBJECTS"
copy_direction: .res 1
copy_index: .res 1
copy_end: .res 3
copy_pos: .res 3
copy_host: .res 2
copy_left: .res 2
.segment "CODE"
; A=0 stash within capacity,1 fetch within committed size. Request unchanged.
; Protect objects/slots/fonts/state: host buffer must be wholly8000-99FF.
; All mappings/ranges validated before ANY DMA; bank crossings split explicitly.
; Nonreentrant foreground only; provider/object ownership cannot change mid-call.
se_object_copy:
    cmp #2
    jcs @argument
    sta copy_direction
    jsr se_object_validate
    jcs @return
    stx copy_index
    lda se_object_length
    ora se_object_length+1
    jeq @argument
    lda se_object_c64+1
    cmp #$80
    jcc @host
    lda se_object_c64
    clc
    adc se_object_length
    sta copy_end
    lda se_object_c64+1
    adc se_object_length+1
    jcs @host
    cmp #$9A
    bcc @offset
    jne @host
    lda copy_end
    jne @host
@offset:
    clc
    lda se_object_offset
    adc se_object_length
    sta copy_end
    lda se_object_offset+1
    adc se_object_length+1
    sta copy_end+1
    lda se_object_offset+2
    adc #0
    sta copy_end+2
    jcs @range
    cmp object_banks,x
    bcc @read_limit
    jne @range
    lda copy_end
    ora copy_end+1
    jne @range
@read_limit:
    lda copy_direction
    beq @validated
    lda copy_end+2
    cmp object_size_hi,x
    bcc @validated
    jne @range
    lda copy_end+1
    cmp object_size_mid,x
    bcc @validated
    jne @range
    lda copy_end
    cmp object_size_lo,x
    bcc @validated
    jne @range
@validated:
    ldx #2
@position:
    lda se_object_offset,x
    sta copy_pos,x
    dex
    bpl @position
    ldx #1
@buffers:
    lda se_object_c64,x
    sta copy_host,x
    lda se_object_length,x
    sta copy_left,x
    dex
    bpl @buffers
@chunk:
    lda copy_host
    sta se_reu_c64
    lda copy_host+1
    sta se_reu_c64+1
    lda copy_pos
    sta se_reu_offset
    lda copy_pos+1
    sta se_reu_offset+1
    lda copy_left
    sta se_reu_length
    lda copy_left+1
    sta se_reu_length+1
    clc
    lda copy_pos
    adc copy_left
    lda copy_pos+1
    adc copy_left+1
    bcc @length
    ; The pending copy reaches this bank's exclusive end. Never send zero.
    sec
    lda #0
    sbc copy_pos
    sta se_reu_length
    lda #0
    sbc copy_pos+1
    sta se_reu_length+1
@length:
    lda copy_index
    asl
    asl
    asl
    asl
    ora copy_pos+2
    tax
    lda object_extents,x
    sta se_reu_logical
    lda copy_direction
    jsr se_reu_copy
    bcs @return
    sec
    lda copy_left
    sbc se_reu_length
    sta copy_left
    lda copy_left+1
    sbc se_reu_length+1
    sta copy_left+1
    clc
    lda copy_host
    adc se_reu_length
    sta copy_host
    lda copy_host+1
    adc se_reu_length+1
    sta copy_host+1
    clc
    lda copy_pos
    adc se_reu_length
    sta copy_pos
    lda copy_pos+1
    adc se_reu_length+1
    sta copy_pos+1
    bcc :+
    inc copy_pos+2
:
    lda copy_left
    ora copy_left+1
    jne @chunk
    lda #0
    clc
@return:
    rts
@argument:
    lda #$36
    sec
    rts
@host:
    lda #$33
    sec
    rts
@range:
    lda #$32
    sec
    rts
