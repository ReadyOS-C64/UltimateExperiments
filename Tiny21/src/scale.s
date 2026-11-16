.setcpu "6502"
.import mul8_unsigned
.importzp mul_rhs, mul_result, dot_result
.export scale_dot, scale_factor, scale_shift, scale_value

.segment "ZEROPAGE"
scale_factor: .res 3           ; unsigned Q0.24
scale_shift:  .res 1           ; activation exponent, 0..24
scale_value:  .res 4           ; signed output in input's working units
scale_sign:   .res 1
multiplicand: .res 4
wide:         .res 7
scale_i:      .res 1
scale_j:      .res 1
round_bits:   .res 1

.segment "CODE"
; scale_value = round_away(dot_result * scale_factor / 2^(24-scale_shift)).
; Preserve dot_result. Carry set on invalid exponent or signed overflow.
.proc scale_dot
    lda #24
    sec
    sbc scale_shift
    bcs :+
    rts_error:
    sec
    rts
:
    sta round_bits
    lda dot_result+3
    sta scale_sign
    bmi negative
    .repeat 4, I
        lda dot_result+I
        sta multiplicand+I
    .endrepeat
    jmp clear
negative:
    sec
    .repeat 4, I
        lda #0
        sbc dot_result+I
        sta multiplicand+I
    .endrepeat
clear:
    lda #0
    ldx #6
:
    sta wide,x
    dex
    bpl :-
    sta scale_i
outer:
    lda #0
    sta scale_j
inner:
    ldx scale_j
    lda scale_factor,x
    beq next
    sta mul_rhs
    ldx scale_i
    lda multiplicand,x
    beq next
    jsr mul8_unsigned
    lda scale_i
    clc
    adc scale_j
    tax
    clc
    lda wide,x
    adc mul_result
    sta wide,x
    inx
    lda wide,x
    adc mul_result+1
    sta wide,x
    bcc next
propagate:
    inx
    inc wide,x
    beq propagate
next:
    inc scale_j
    lda scale_j
    cmp #3
    bne inner
    inc scale_i
    lda scale_i
    cmp #4
    bne outer

    ; Drop full bytes first. If there are no residual bit shifts, the
    ; top bit of the last discarded byte decides nearest rounding.
    lda round_bits
    lsr
    lsr
    lsr
    tax
    clc
    beq remainder_bits
    lda wide-1,x
    asl
    php
    ldy #0
copy_bytes:
    lda wide,x
    sta wide,y
    iny
    inx
    cpx #7
    bcc copy_bytes
    lda #0
clear_bytes:
    sta wide,y
    iny
    cpy #7
    bcc clear_bytes
    plp
remainder_bits:
    lda round_bits
    and #7
    tax
    beq rounding
shift:
    lsr wide+6
    .repeat 6, I
        ror wide+5-I
    .endrepeat
    dex
    bne shift
rounding:
    bcc range
    ldx #0
round_up:
    inc wide,x
    bne range
    inx
    bne round_up
range:
    lda wide+6
    ora wide+5
    ora wide+4
    bne rts_error_far
    lda scale_sign
    bmi signed_negative
    lda wide+3
    bmi rts_error_far
    .repeat 4, I
        lda wide+I
        sta scale_value+I
    .endrepeat
    clc
    rts
signed_negative:
    lda wide+3
    cmp #$80
    bcc negate
    bne rts_error_far
    lda wide+2
    ora wide+1
    ora wide
    bne rts_error_far
negate:
    sec
    .repeat 4, I
        lda #0
        sbc wide+I
        sta scale_value+I
    .endrepeat
    clc
    rts
rts_error_far:
    sec
    rts
.endproc
