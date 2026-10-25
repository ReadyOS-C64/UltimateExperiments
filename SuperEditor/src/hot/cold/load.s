load:
    lda se_hot_phase
    ora se_hot_pending
    jne busy
    jsr se_doc_validate
    jcs return
    CMP24 se_hot_position,se_doc_length
    bcc @range
    jne boundary
@range:
    lda #0
    sta se_hot_ready
    sta se_hot_fault
    COPY24 se_hot_position,se_hot_caret
    COPY24 se_hot_position,se_hot_base
    ; Start up to512 bytes before caret. Fill at most1024 baseline bytes.
    lda se_hot_base+2
    bne @subtract
    lda se_hot_base+1
    cmp #2
    bcs @subtract
    lda #0
    sta se_hot_base
    sta se_hot_base+1
    sta se_hot_left+1
    lda se_hot_position
    sta se_hot_left
    lda se_hot_position+1
    sta se_hot_left+1
    jmp @size
@subtract:
    sec
    lda se_hot_base+1
    sbc #2
    sta se_hot_base+1
    lda se_hot_base+2
    sbc #0
    sta se_hot_base+2
    lda #0
    sta se_hot_left
    lda #2
    sta se_hot_left+1
@size:
    SUB24 se_doc_length,se_hot_base,se_hot_tmp
    lda se_hot_tmp+2
    bne @cap
    lda se_hot_tmp+1
    cmp #4
    bcc @amount
@cap:
    lda #0
    sta se_hot_tmp
    lda #4
    sta se_hot_tmp+1
@amount:
    lda se_hot_tmp
    sta se_hot_length
    sta se_hot_old_length
    lda se_hot_tmp+1
    sta se_hot_length+1
    sta se_hot_old_length+1
    ; Gap right=2048-(length-left).
    sec
    lda se_hot_left
    sbc se_hot_length
    sta se_hot_right
    lda se_hot_left+1
    sbc se_hot_length+1
    clc
    adc #8
    sta se_hot_right+1
    ldx #4
@identity:
    lda se_doc_original,x
    sta se_hot_original,x
    lda se_doc_append,x
    sta se_hot_append,x
    dex
    bpl @identity
    lda se_doc_generation
    sta se_hot_generation
    lda se_doc_generation+1
    sta se_hot_generation+1
    jsr se_doc_read_acquire
    jcs return
    lda #1
    sta se_hot_owned
    sta se_hot_phase
    lda #0
    sta se_hot_loaded
    sta se_hot_loaded+1
    jmp pending
load_step:
    lda se_hot_phase
    cmp #1
    jne state
    ; Read at most128 bytes/eight spans, then copy directly to both gap sides.
    sec
    lda se_hot_length
    sbc se_hot_loaded
    sta se_hot_count
    lda se_hot_length+1
    sbc se_hot_loaded+1
    sta se_hot_count+1
    ora se_hot_count
    jeq loaded
    lda se_hot_count+1
    bne @cap
    lda se_hot_count
    cmp #129
    bcc @count
@cap:
    lda #128
    sta se_hot_count
@count:
    lda #0
    sta se_hot_count+1
    sta se_hot_tmp+2
    lda se_hot_loaded
    sta se_hot_tmp
    lda se_hot_loaded+1
    sta se_hot_tmp+1
    ADD24 se_hot_base,se_hot_tmp,se_doc_offset
    lda se_hot_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    jcs return
    lda se_doc_read_done
    sta se_hot_count
    lda #0
    sta se_hot_packet
    lda #$80
    sta se_hot_packet+1
@copy:
    lda se_hot_loaded
    sta se_hot_target
    lda se_hot_loaded+1
    sta se_hot_target+1
    jsr address
    ldy #0
    lda (se_hot_packet),y
    sta (se_hot_ptr),y
    inc se_hot_packet
    inc se_hot_loaded
    bne :+
    inc se_hot_loaded+1
:
    dec se_hot_count
    bne @copy
    lda se_hot_loaded
    cmp se_hot_length
    jne pending
    lda se_hot_loaded+1
    cmp se_hot_length+1
    jne pending
loaded:
    jsr se_doc_read_release
    lda #0
    sta se_hot_owned
    sta se_hot_phase
    lda #1
    sta se_hot_ready
    jmp okay
; Logical target -> HOT address; gap split maps suffix to right side.
address:
    lda se_hot_target+1
    cmp se_hot_left+1
    bcc @prefix
    bne @suffix
    lda se_hot_target
    cmp se_hot_left
    bcc @prefix
@suffix:
    sec
    lda se_hot_target
    sbc se_hot_left
    sta se_hot_ptr
    lda se_hot_target+1
    sbc se_hot_left+1
    sta se_hot_ptr+1
    clc
    lda se_hot_ptr
    adc se_hot_right
    sta se_hot_ptr
    lda se_hot_ptr+1
    adc se_hot_right+1
    jmp @high
@prefix:
    lda se_hot_target
    sta se_hot_ptr
    lda se_hot_target+1
@high:
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    rts
