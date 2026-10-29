.setcpu "6502"
.include "diagnostics/internal.inc"
.import se_crc_byte,se_crc_value
.segment "CODE"
; One call hashes<=128 native bytes. Committed reads visit<=8 source spans;
; gap runs stop at either side's boundary. No pointers into caches survive.
se_diag_step:
    lda se_diag_active
    jne active
    lda #D_STATE
    sec
    rts
active:
    jsr se_diag_context
    jcs se_diag_abort
    SUB24 se_diag_length,se_diag_pos,se_diag_temp
    lda se_diag_temp
    ora se_diag_temp+1
    ora se_diag_temp+2
    jeq complete
    lda #128
    sta se_diag_count
    lda #0
    sta se_diag_count+1
    jsr clamp
    lda se_hot_ready
    jeq direct
    CMP24 se_diag_pos,se_hot_base
    jcc prefix_source
    CMP24 se_diag_pos,se_diag_hot_end
    jcs suffix_source
    ; In RAM gap's visible span. Compute prefix or suffix host pointer.
    SUB24 se_diag_pos,se_hot_base,se_diag_temp
    lda se_diag_temp+1
    cmp se_hot_left+1
    bcc gap_prefix
    bne gap_suffix
    lda se_diag_temp
    cmp se_hot_left
    bcc gap_prefix
gap_suffix:
    sec
    lda se_diag_temp
    sbc se_hot_left
    sta text_ptr
    lda se_diag_temp+1
    sbc se_hot_left+1
    sta text_ptr+1
    clc
    lda text_ptr
    adc se_hot_right
    sta text_ptr
    lda text_ptr+1
    adc se_hot_right+1
    clc
    adc #>HOT_FIRST
    sta text_ptr+1
    SUB24 se_diag_hot_end,se_diag_pos,se_diag_temp
    jsr clamp
    jmp hash
gap_prefix:
    lda se_diag_temp
    sta text_ptr
    lda se_diag_temp+1
    clc
    adc #>HOT_FIRST
    sta text_ptr+1
    sec
    lda se_hot_left
    sbc se_diag_temp
    sta se_diag_temp
    lda se_hot_left+1
    sbc se_diag_temp+1
    sta se_diag_temp+1
    lda #0
    sta se_diag_temp+2
    jsr clamp
    jmp hash
prefix_source:
    SUB24 se_hot_base,se_diag_pos,se_diag_temp
    jsr clamp
direct:
    COPY24 se_diag_pos,se_doc_offset
    jmp read
suffix_source:
    ; physical = visible -new hot length +old committed span.
    sec
    lda se_diag_pos
    sbc se_hot_length
    sta se_doc_offset
    lda se_diag_pos+1
    sbc se_hot_length+1
    sta se_doc_offset+1
    lda se_diag_pos+2
    sbc #0
    sta se_doc_offset+2
    clc
    lda se_doc_offset
    adc se_hot_old_length
    sta se_doc_offset
    lda se_doc_offset+1
    adc se_hot_old_length+1
    sta se_doc_offset+1
    lda se_doc_offset+2
    adc #0
    sta se_doc_offset+2
read:
    lda se_diag_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    jcs se_diag_abort
    lda se_doc_read_done
    sta se_diag_count
    lda se_doc_read_done+1
    sta se_diag_count+1
    lda #0
    sta text_ptr
    lda #$80
    sta text_ptr+1
hash:
    lda se_diag_crc
    sta se_crc_value
    lda se_diag_crc+1
    sta se_crc_value+1
    ldy #0
byte:
    lda (text_ptr),y
    jsr se_crc_byte ;resident ABI preservesY,may destroyA/X/P
    iny
    cpy se_diag_count
    bne byte
    lda se_crc_value
    sta se_diag_crc
    lda se_crc_value+1
    sta se_diag_crc+1
    clc
    lda se_diag_pos
    adc se_diag_count
    sta se_diag_pos
    lda se_diag_pos+1
    adc se_diag_count+1
    sta se_diag_pos+1
    lda se_diag_pos+2
    adc #0
    sta se_diag_pos+2
    jsr se_diag_pointer
    D_CAPTURE se_diag_pos,DS_SCANNED,3
    D_CAPTURE se_diag_crc,DS_CRC,2
    CMP24 se_diag_pos,se_diag_length
    beq complete
    lda #1
    clc
    rts
complete:
    jsr se_diag_cancel
    jsr se_diag_pointer
    lda #2
    ldy #DS_STATUS
    sta (text_ptr),y
    lda #0
    clc
    rts
; Clamp count to remaining contiguous span(temp24),never larger than128.
clamp:
    lda se_diag_temp+2
    ora se_diag_temp+1
    bne :+
    lda se_diag_temp
    cmp se_diag_count
    bcs :+
    sta se_diag_count
:
    rts
