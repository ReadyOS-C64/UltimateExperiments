; Editor-only C4 RAM packet producer. Stay in HEDIT between BEGIN/FEED/STEP;
; never invoke another command overlay from inside this image.
hot_packet:
    jsr se_h_validate
    jcs return
    jsr se_doc_validate
    jcs return
    lda se_hot_phase
    cmp #2
    jne @state
    lda se_h_phase
    cmp #H_FEEDING
    jne @state
    ldx #4
@identity:
    lda se_hot_original,x
    cmp se_doc_original,x
    jne @changed
    lda se_hot_append,x
    cmp se_doc_append,x
    jne @changed
    dex
    bpl @identity
    ldx #1
@generation:
    lda se_hot_generation,x
    cmp se_doc_generation,x
    jne @changed
    dex
    bpl @generation
    ; Bound every RAM read even if a private continuation frame is malformed.
    lda se_hot_length+1
    cmp #8
    bcc @length
    jne @state
    lda se_hot_length
    jne @state
@length:
    lda se_hot_feed_left
    ora se_hot_feed_left+1
    jeq @state
    clc
    lda se_hot_feed
    adc se_hot_feed_left
    sta se_hot_tmp
    lda se_hot_feed+1
    adc se_hot_feed_left+1
    jcs @state
    cmp se_hot_length+1
    bcc @gap
    jne @state
    lda se_hot_tmp
    cmp se_hot_length
    jcc @gap
    jne @state
@gap:
    lda se_hot_right+1
    cmp #8
    bcc @left_bound
    jne @state
    lda se_hot_right
    jne @state
@left_bound:
    lda se_hot_left+1
    cmp se_hot_right+1
    bcc @shape
    jne @state
    lda se_hot_left
    cmp se_hot_right
    jcc @shape
    jne @state
@shape:
    ; Logical length must equal prefix plus suffix. Individual field bounds
    ; alone allow a malformed suffix to read beyond HOT_END into DOCSTATE.
    sec
    lda #<HOT_BYTES
    sbc se_hot_right
    sta se_hot_tmp
    lda #>HOT_BYTES
    sbc se_hot_right+1
    sta se_hot_tmp+1
    clc
    lda se_hot_tmp
    adc se_hot_left
    sta se_hot_tmp
    lda se_hot_tmp+1
    adc se_hot_left+1
    cmp se_hot_length+1
    jne @state
    lda se_hot_tmp
    cmp se_hot_length
    jne @state
@count:
    lda #128
    ldx se_hot_feed_left+1
    bne :+
    cmp se_hot_feed_left
    bcc :+
    lda se_hot_feed_left
:
    sta se_hot_count
    lda se_hot_feed+1
    cmp se_hot_left+1
    bcc @prefix
    bne @suffix
    lda se_hot_feed
    cmp se_hot_left
    bcc @prefix
@suffix:
    sec
    lda se_hot_feed
    sbc se_hot_left
    sta se_hot_ptr
    lda se_hot_feed+1
    sbc se_hot_left+1
    sta se_hot_ptr+1
    clc
    lda se_hot_ptr
    adc se_hot_right
    sta se_hot_ptr
    lda se_hot_ptr+1
    adc se_hot_right+1
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    jmp @copy
@prefix:
    ; A packet stops at the gap. The next FEED consumes the suffix normally.
    sec
    lda se_hot_left
    sbc se_hot_feed
    sta se_hot_tmp
    lda se_hot_left+1
    sbc se_hot_feed+1
    bne :+
    lda se_hot_tmp
    cmp se_hot_count
    bcs :+
    sta se_hot_count
:
    lda se_hot_feed
    sta se_hot_ptr
    lda se_hot_feed+1
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
@copy:
    ldy #0
@byte:
    lda (se_hot_ptr),y
    sta $8000,y
    iny
    cpy se_hot_count
    bcc @byte
    lda se_hot_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    clc
    lda se_hot_feed
    adc se_hot_count
    sta se_hot_feed
    bcc :+
    inc se_hot_feed+1
:
    sec
    lda se_hot_feed_left
    sbc se_hot_count
    sta se_hot_feed_left
    bcs :+
    dec se_hot_feed_left+1
:
    lda #0
    clc
    rts
@state:
    lda #$70
    sec
    rts
@changed:
    lda #$74
    sec
    rts
