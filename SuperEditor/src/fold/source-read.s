.setcpu "6502"
.include "fold/source.inc"
.segment "FOLD_SOURCE_CODE"
se_fs_read:
    lda #0
    sta se_fs_done
.ifndef SE_FS_TRUSTED_CALLER
    jsr se_fs_guard
    jcs read_return
.endif
    lda se_fs_count
    jeq read_bad
    cmp #129
    jcs read_bad
    ; Whole requested output must fit owned8880..8BFF or8D00..917F.
    lda se_fs_buffer+1
    cmp #$88
    jcc read_bad
    jne @second
    lda se_fs_buffer
    cmp #$80
    jcc read_bad
@second:
    lda se_fs_buffer+1
    cmp #$8C
    jcc @end
    jeq read_bad
    cmp #$8D
    jcc read_bad
    cmp #$92
    jcs read_bad
@end:
    clc
    lda se_fs_buffer
    adc se_fs_count
    sta se_fs_temp
    lda se_fs_buffer+1
    adc #0
    sta se_fs_temp+1
    jcs read_bad
    lda se_fs_buffer+1
    cmp #$8C
    jcs @union_end
    lda se_fs_temp+1
    cmp #$8C
    jcc @overlap
    jne read_bad
    lda se_fs_temp
    jne read_bad
    jeq @overlap
@union_end:
    lda se_fs_temp+1
    cmp #$91
    jcc @overlap
    jne read_bad
    lda se_fs_temp
    cmp #$81
    jcs read_bad
@overlap:
    ; Reject overlap with this adapter frame if caller places it in scratch.
    lda se_fs_buffer+1
    cmp #>(se_fs_state+se_fs_state_size)
    jcc @possibly
    jne @position
    lda se_fs_buffer
    cmp #<(se_fs_state+se_fs_state_size)
    jcs @position
@possibly:
    lda se_fs_temp+1
    cmp #>se_fs_state
    jcc @position
    jne read_bad
    lda se_fs_temp
    cmp #<se_fs_state
    jcc @position
    jne read_bad
@position:
    CMP24 se_fs_offset,se_fs_length
    jcc @remaining
    jne read_bad
    lda #0
    clc
    rts
@remaining:
    lda se_fs_buffer
    sta se_fs_output
    lda se_fs_buffer+1
    sta se_fs_output+1
    lda se_fs_count
    sta se_fs_done
    SUB24 se_fs_length,se_fs_offset,se_fs_temp
    jsr clamp
    lda se_hot_ready
    jeq committed_direct
    CMP24 se_fs_offset,se_hot_base
    jcc prefix_source
    CMP24 se_fs_offset,se_fs_hot_end
    jcs suffix_source
    SUB24 se_fs_offset,se_hot_base,se_fs_temp
    lda se_fs_temp+1
    cmp se_hot_left+1
    jcc gap_prefix
    jne gap_suffix
    lda se_fs_temp
    cmp se_hot_left
    jcc gap_prefix
gap_suffix:
    sec
    lda se_fs_temp
    sbc se_hot_left
    sta se_fs_phys
    lda se_fs_temp+1
    sbc se_hot_left+1
    sta se_fs_phys+1
    clc
    lda se_fs_phys
    adc se_hot_right
    sta se_fs_phys
    lda se_fs_phys+1
    adc se_hot_right+1
    sta se_fs_phys+1
    SUB24 se_fs_hot_end,se_fs_offset,se_fs_temp
    jsr clamp
    jmp gap_copy
gap_prefix:
    lda se_fs_temp
    sta se_fs_phys
    lda se_fs_temp+1
    sta se_fs_phys+1
    sec
    lda se_hot_left
    sbc se_fs_temp
    sta se_fs_temp
    lda se_hot_left+1
    sbc se_fs_temp+1
    sta se_fs_temp+1
    lda #0
    sta se_fs_temp+2
    jsr clamp
    jmp gap_copy
prefix_source:
    SUB24 se_hot_base,se_fs_offset,se_fs_temp
    jsr clamp
committed_direct:
    COPY24 se_fs_offset,se_doc_offset
    jmp committed
suffix_source:
    sec
    lda se_fs_offset
    sbc se_hot_length
    sta se_doc_offset
    lda se_fs_offset+1
    sbc se_hot_length+1
    sta se_doc_offset+1
    lda se_fs_offset+2
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
committed:
    lda se_fs_done
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    jcs read_return
    lda se_doc_read_done+1
    jne read_bad
    lda se_doc_read_done
    jeq read_bad
    sta se_fs_done
    jsr output_pointer
    ldy #0
@copy:
    lda $8000,y
    sta (text_ptr),y
    iny
    cpy se_fs_done
    jne @copy
    lda #0
    clc
    rts
gap_copy:
    ; Clamp to the source page, then patch the high byte of one absolute,X
    ; loop.  R14 is a writable, non-reentrant overlay and every call rewrites
    ; the operand before executing it.
    lda se_fs_phys
    jeq @page
    sec
    lda #0
    sbc se_fs_phys
    cmp se_fs_done
    jcs @page
    sta se_fs_done
@page:
    jsr output_pointer
    lda se_fs_phys+1
    clc
    adc #>HOT_FIRST
    sta @load+2
    ldy #0
    ldx se_fs_phys
@load:
    lda HOT_FIRST,x
    sta (text_ptr),y
    inx
    iny
    cpy se_fs_done
    bne @load
    lda #0
    clc
    rts
output_pointer:
    lda se_fs_output
    sta text_ptr
    lda se_fs_output+1
    sta text_ptr+1
    rts
clamp:
    lda se_fs_temp+2
    ora se_fs_temp+1
    bne :+
    lda se_fs_temp
    cmp se_fs_done
    bcs :+
    sta se_fs_done
:   rts
read_bad:
    lda #FS_BAD
    sec
read_return:
    rts
