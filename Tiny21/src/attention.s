.setcpu "6502"
.import cache_attention_first, cache_slot_address, token_pos, query, attention
.import reu_transfer, REU_TILE, REU_TILE_SIZE
.importzp reu_addr, reu_ram, reu_size, reu_direction
.import wide_a, wide_b, wide_product, wide_multiply, wide_round_divide, wide_mul_byte
.import wide_round_divide_score, wide_mul_byte_limited
.import attention_exp, exp_delta_q16, exp_value_q24
.export cache_attention

RECORD_BYTES = 200
BLOCK_RECORDS = 40
.assert BLOCK_RECORDS * RECORD_BYTES <= REU_TILE_SIZE, lderror, "attention block must fit tile"
HEAD_COUNT = 4
HEAD_WIDTH = 24
SCORE_BYTES = 8
ACCUM_BYTES = 9
QUERY_BYTES = 4
COEFFICIENT_BYTES = 7
; round(2^24 / sqrt(24)), and 127 * 2^16 * 2^24.
INVERSE_SQRT = 3424635

.segment "ZEROPAGE"
record:   .res 2
score:    .res 2
sample:   .res 2
channel:  .res 2
weight:   .res 2

.segment "BSS"
remaining:  .res 1
block_count:   .res 1
tail_count:    .res 1
tail_score:    .res 2
head:       .res 1
head_channel: .res 1
lanes:      .res 1
polarity:   .res 1
sample_sign: .res 1
; score accumulation is reused for the signed max-minus-score delta.
signed_sum: .res SCORE_BYTES
prepared_query: .res HEAD_COUNT*HEAD_WIDTH*(QUERY_BYTES+1)
factors:    .res HEAD_COUNT*4
maximum:    .res HEAD_COUNT*SCORE_BYTES
scores:     .res 128*HEAD_COUNT*SCORE_BYTES
weighted:   .res HEAD_COUNT*HEAD_WIDTH*ACCUM_BYTES

.segment "CODE"
.macro ADDRESS dst, addr
    lda #<(addr)
    sta dst
    lda #>(addr)
    sta dst+1
.endmacro

.macro ADVANCE ptr, size
    clc
    lda ptr
    adc #size
    sta ptr
    bcc :+
    inc ptr+1
:
.endmacro

.macro CLEAR_ARRAY address, size
    lda #0
    ldx #size-1
:
    sta address,x
    dex
    bpl :-
.endmacro

.proc begin_key_pass
    lda token_pos
    clc
    adc #1
    sta remaining
    ADDRESS score, scores
    lda #0
    jmp cache_slot_address
.endproc

; REU address advances through the live prefix. Each block fits the tile.
.proc read_block
    lda #BLOCK_RECORDS
    ; Fall through to the variable limit entry.
.endproc
.proc read_block_limit
    cmp remaining
    bcc use_limit
    lda remaining
use_limit:
    sta block_count
    lda remaining
    sec
    sbc block_count
    sta remaining
    ldx block_count
    ADDRESS reu_size, 0
size_loop:
    clc
    lda reu_size
    adc #RECORD_BYTES
    sta reu_size
    bcc :+
    inc reu_size+1
:
    dex
    bne size_loop
    ADDRESS reu_ram, REU_TILE
    ADDRESS record, REU_TILE
    lda #1
    sta reu_direction
    jmp reu_transfer
.endproc

; Signed packed 32-bit at sample -> unsigned magnitude in wide_a,
; and sign bit in sample_sign.
.proc load_sample
    ldy #3
    lda (sample),y
    sta sample_sign
    bmi negative
    .repeat 4, I
        lda (sample),y
        sta wide_a+3-I
        dey
    .endrepeat
    rts
negative:
    ldy #0
    sec
    .repeat 4, I
        lda #0
        sbc (sample),y
        sta wide_a+I
        iny
    .endrepeat
    rts
.endproc

; The query is invariant across the live prefix. Extract its signs
; and magnitudes once, storing the lanes in head order.
.proc prepare_query
    ADDRESS sample, query
    ADDRESS channel, prepared_query
    lda #HEAD_COUNT*HEAD_WIDTH
    sta lanes
lane:
    jsr load_sample
    ldy #0
    .repeat ::QUERY_BYTES, I
        lda wide_a+I
        sta (channel),y
        iny
    .endrepeat
    lda sample_sign
    sta (channel),y
    ADVANCE sample, QUERY_BYTES
    ADVANCE channel, QUERY_BYTES+1
    dec lanes
    bne lane
    rts
.endproc

; Set wide_b to the absolute int8 in A. XOR its sign with sample_sign.
.proc byte_magnitude
    tax
    eor sample_sign
    sta polarity
    txa
    bpl :+
    eor #$ff
    clc
    adc #1
:
    sta wide_b
    rts
.endproc

; Use signed_sum and the current K record peak to evaluate one score.
.proc score_head
    lda #4
    clc
    adc head_channel
    adc record
    sta weight
    lda record+1
    adc #0
    sta weight+1
    CLEAR_ARRAY signed_sum, SCORE_BYTES
    lda #HEAD_WIDTH
    sta lanes
dot:
    ldy #0
    lda (weight),y
    bne :+
    jmp next
:
    pha
    .repeat ::QUERY_BYTES, I
        lda (sample),y
        sta wide_a+I
        iny
    .endrepeat
    lda (sample),y
    sta sample_sign
    pla
    jsr byte_magnitude
    ldx #QUERY_BYTES
    jsr wide_mul_byte_limited
    lda polarity
    bmi subtract
    clc
    .repeat ::SCORE_BYTES, I
        lda signed_sum+I
        .if I <= ::QUERY_BYTES
            adc wide_product+I
        .else
            adc #0
        .endif
        sta signed_sum+I
    .endrepeat
    jmp next
subtract:
    sec
    .repeat ::SCORE_BYTES, I
        lda signed_sum+I
        .if I <= ::QUERY_BYTES
            sbc wide_product+I
        .else
            sbc #0
        .endif
        sta signed_sum+I
    .endrepeat
next:
    ADVANCE sample, QUERY_BYTES+1
    ADVANCE weight, 1
    dec lanes
    beq scale
    jmp dot
scale:
    CLEAR_ARRAY wide_a, 12
    CLEAR_ARRAY wide_b, 12
    lda signed_sum+SCORE_BYTES-1
    sta polarity
    bmi negative
    .repeat ::SCORE_BYTES, I
        lda signed_sum+I
        sta wide_a+I
    .endrepeat
    jmp peak
negative:
    sec
    .repeat ::SCORE_BYTES, I
        lda #0
        sbc signed_sum+I
        sta wide_a+I
    .endrepeat
peak:
    ldy #0
    .repeat 4, I
        lda (record),y
        sta wide_b+I
        iny
    .endrepeat
    jsr wide_multiply
    jsr product_to_a
    CLEAR_ARRAY wide_b, 12
    lda #<INVERSE_SQRT
    sta wide_b
    lda #>INVERSE_SQRT
    sta wide_b+1
    lda #^INVERSE_SQRT
    sta wide_b+2
    jsr wide_multiply
    jsr product_to_a
    jsr wide_round_divide_score
    ldy #0
    lda polarity
    bmi store_negative
    .repeat ::SCORE_BYTES, I
        lda wide_a+I
        sta (score),y
        iny
    .endrepeat
    jmp update
store_negative:
    sec
    .repeat ::SCORE_BYTES, I
        lda #0
        sbc wide_a+I
        sta (score),y
        iny
    .endrepeat
update:
    ; Signed high byte first, then compare remaining bytes unsigned.
    lda head
    asl
    asl
    asl
    tax
    ldy #SCORE_BYTES-1
    lda (score),y
    eor #$80
    sta sample_sign
    lda maximum+SCORE_BYTES-1,x
    eor #$80
    cmp sample_sign
    bcc replace
    bne done
    txa
    clc
    adc #SCORE_BYTES-2
    tax
    dey
compare:
    lda (score),y
    cmp maximum,x
    bcc done
    bne reset_replace
    dex
    dey
    bpl compare
done:
    rts
reset_replace:
    lda head
    asl
    asl
    asl
    tax
replace:
    ldy #0
copy_max:
    lda (score),y
    sta maximum,x
    inx
    iny
    cpy #SCORE_BYTES
    bne copy_max
    rts
.endproc

.proc product_to_a
    ldx #11
copy:
    lda wide_product,x
    sta wide_a,x
    dex
    bpl copy
    rts
.endproc

; Use the saved scores for the current record. Accumulate both the
; per-head denominator and its 24 signed weighted-value sums.
.proc value_head
    lda head
    asl
    asl
    asl
    tax
    ldy #0
    sec
    .repeat ::SCORE_BYTES, I
        lda maximum+I,x
        sbc (score),y
        sta signed_sum+I
        iny
    .endrepeat
    lda signed_sum+4
    ora signed_sum+5
    ora signed_sum+6
    ora signed_sum+7
    beq exp
    jmp skip_head
exp:
    .repeat 4, I
        lda signed_sum+I
        sta exp_delta_q16+I
    .endrepeat
    jsr attention_exp
    lda exp_value_q24
    ora exp_value_q24+1
    ora exp_value_q24+2
    ora exp_value_q24+3
    bne has_factor
    jmp skip_head
has_factor:
    lda head
    asl
    asl
    tax
    clc
    .repeat 4, I
        lda factors+I,x
        adc exp_value_q24+I
        sta factors+I,x
    .endrepeat
    CLEAR_ARRAY wide_a, 12
    CLEAR_ARRAY wide_b, 12
    ldy #100
    .repeat 4, I
        lda (record),y
        sta wide_a+I
        lda exp_value_q24+I
        sta wide_b+I
        iny
    .endrepeat
    jsr wide_multiply
    ; This seven-byte coefficient is invariant across all value lanes.
    .repeat ::COEFFICIENT_BYTES, I
        lda wide_product+I
        sta wide_a+I
    .endrepeat
    lda #0
    sta sample_sign
    lda #104
    clc
    adc head_channel
    adc record
    sta sample
    lda record+1
    adc #0
    sta sample+1
    lda #HEAD_WIDTH
    sta lanes
lane:
    ldy #0
    lda (sample),y
    bne :+
    jmp next
:
    jsr byte_magnitude
    ldx #COEFFICIENT_BYTES
    jsr wide_mul_byte_limited
    ldy #0
    lda polarity
    bmi subtract
    clc
    .repeat ::ACCUM_BYTES, I
        lda (channel),y
        .if I <= ::COEFFICIENT_BYTES
            adc wide_product+I
        .else
            adc #0
        .endif
        sta (channel),y
        iny
    .endrepeat
    jmp next
subtract:
    sec
    .repeat ::ACCUM_BYTES, I
        lda (channel),y
        .if I <= ::COEFFICIENT_BYTES
            sbc wide_product+I
        .else
            sbc #0
        .endif
        sta (channel),y
        iny
    .endrepeat
next:
    ADVANCE channel, ACCUM_BYTES
    ADVANCE sample, 1
    dec lanes
    beq done
    jmp lane
skip_head:
    ADVANCE channel, HEAD_WIDTH*ACCUM_BYTES
done:
    rts
.endproc

.proc finish_values
    ADDRESS channel, weighted
    ADDRESS sample, attention
    lda #0
    sta head
head_loop:
    CLEAR_ARRAY wide_a, 12
    CLEAR_ARRAY wide_b, 12
    lda head
    asl
    asl
    tax
    .repeat 4, I
        lda factors+I,x
        sta wide_a+I
    .endrepeat
    lda #127
    sta wide_b
    jsr wide_mul_byte
    ldx #11
denominator:
    lda wide_product,x
    sta wide_b,x
    dex
    bpl denominator
    lda #HEAD_WIDTH
    sta lanes
lane_loop:
    CLEAR_ARRAY wide_a, 12
    ldy #ACCUM_BYTES-1
    lda (channel),y
    sta polarity
    bmi negate
    .repeat ::ACCUM_BYTES, I
        lda (channel),y
        sta wide_a+ACCUM_BYTES-1-I
        dey
    .endrepeat
    jmp divide
negate:
    ldy #0
    sec
    .repeat ::ACCUM_BYTES, I
        lda #0
        sbc (channel),y
        sta wide_a+I
        iny
    .endrepeat
divide:
    jsr wide_round_divide
    bcc store
    rts
store:
    ldy #0
    lda polarity
    bmi store_negative
    .repeat 4, I
        lda wide_a+I
        sta (sample),y
        iny
    .endrepeat
    jmp advance
store_negative:
    sec
    .repeat 4, I
        lda #0
        sbc wide_a+I
        sta (sample),y
        iny
    .endrepeat
advance:
    ADVANCE sample, 4
    ADVANCE channel, ACCUM_BYTES
    dec lanes
    beq end_head
    jmp lane_loop
end_head:
    inc head
    lda head
    cmp #HEAD_COUNT
    beq done
    jmp head_loop
done:
    clc
    rts
.endproc

.macro START_HEADS
    lda #0
    sta head
    sta head_channel
.endmacro

.macro ADVANCE_HEAD
    ADVANCE score, SCORE_BYTES
    lda head_channel
    clc
    adc #HEAD_WIDTH
    sta head_channel
    inc head
    lda head
    cmp #HEAD_COUNT
.endmacro

.proc cache_attention
    lda token_pos
    bne general
    jmp cache_attention_first
general:
    cmp #128
    bcc valid
    sec
    rts
valid:
    jsr prepare_query
    CLEAR_ARRAY maximum, HEAD_COUNT*SCORE_BYTES
    lda #$80
    .repeat ::HEAD_COUNT, I
        sta maximum+I*SCORE_BYTES+SCORE_BYTES-1
    .endrepeat
    jsr begin_key_pass
    bcc first_k_block
    rts
first_k_block:
    ; Start with any partial block so the retained final tile is full.
    lda remaining
trim_first:
    cmp #BLOCK_RECORDS+1
    bcc load_k_block
    sbc #BLOCK_RECORDS
    jmp trim_first
next_k_block:
    lda #BLOCK_RECORDS
load_k_block:
    jsr read_block_limit
    bcc remember_block
    rts
remember_block:
    lda score
    sta tail_score
    lda score+1
    sta tail_score+1
    lda block_count
    sta tail_count
k_record:
    ADDRESS sample, prepared_query
    START_HEADS
k_head:
    jsr score_head
    ADVANCE_HEAD
    bne k_head
    ADVANCE record, RECORD_BYTES
    dec block_count
    bne k_record
    lda remaining
    bne next_k_block

    CLEAR_ARRAY factors, HEAD_COUNT*4
    lda #0
    ldx #0
clear_values:
    sta weighted,x
    sta weighted+256,x
    sta weighted+512,x
    cpx #ACCUM_BYTES*HEAD_COUNT*HEAD_WIDTH-768
    bcs :+
    sta weighted+768,x
:
    inx
    bne clear_values
    ; The last K tile still holds its corresponding values. Consume it
    ; first, then stream only the earlier prefix. Integer sums are exact
    ; in either order, with one final divide per output lane.
    lda tail_score
    sta score
    lda tail_score+1
    sta score+1
    ADDRESS record, REU_TILE
    lda tail_count
    sta block_count
    lda token_pos
    clc
    adc #1
    sec
    sbc tail_count
    sta remaining
    jmp v_record
next_v_block:
    jsr read_block
    bcc v_record
    rts
v_record:
    ADDRESS channel, weighted
    START_HEADS
v_head:
    jsr value_head
    ADVANCE_HEAD
    bne v_head
    ADVANCE record, RECORD_BYTES
    dec block_count
    bne v_record
    lda remaining
    beq values_done
    lda tail_count
    beq next_v_block
    ; Rewind to position zero once, after consuming the resident tile.
    lda #0
    sta tail_count
    ADDRESS score, scores
    lda #0
    jsr cache_slot_address
    bcc next_v_block
    rts
values_done:
    jmp finish_values
.endproc
