.setcpu "6502"
.import wide_a, wide_b, wide_product, wide_multiply
.export attention_exp, exp_delta_q16, exp_value_q24

.segment "ZEROPAGE"
lut: .res 2

.segment "BSS"
exp_delta_q16: .res 4
exp_value_q24: .res 4
offset:        .res 2
fraction:      .res 2

.segment "RODATA"
exp_table:
.include "exp_table.inc"
.assert *-exp_table = 1025*3, error, "unexpected softmax table size"

.segment "CODE"
; delta = max_score - score, unsigned Q16.16.
; Return linear interpolation in Q0.24 (including exact one).
.proc attention_exp
    lda #0
    ldx #3
clear_result:
    sta exp_value_q24,x
    dex
    bpl clear_result
    lda exp_delta_q16+3
    bne done
    lda exp_delta_q16+2
    cmp #16
    bcs done
    ; index = delta >> 10, each table entry is three bytes.
    sta offset+1
    lda exp_delta_q16+1
    lsr offset+1
    ror
    lsr offset+1
    ror
    sta offset
    ; Shift a copy of the index, then add the original index.
    asl
    ldx offset+1
    stx lut+1
    rol lut+1
    clc
    adc offset
    tay
    lda lut+1
    adc offset+1
    sta lut+1
    tya
    clc
    adc #<exp_table
    sta lut
    lda lut+1
    adc #>exp_table
    sta lut+1
    ldy #0
    .repeat 3, I
        lda (lut),y
        sta exp_value_q24+I
        iny
    .endrepeat
    lda exp_delta_q16+1
    and #3
    sta fraction+1
    lda exp_delta_q16
    sta fraction
    lda exp_delta_q16+2
    bne fraction_check
    lda exp_delta_q16+1
    cmp #4
    bcs fraction_check
    inc exp_value_q24+3
fraction_check:
    lda fraction
    ora fraction+1
    bne interpolate
done:
    rts
interpolate:
    ; Difference is left - right. The Q0.24 interpolated result is
    ; left - round(difference * fraction / 1024).
    sec
    .repeat 3, I
        lda exp_value_q24+I
        sbc (lut),y
        sta wide_a+I
        iny
    .endrepeat
    lda exp_value_q24+3
    sbc #0
    sta wide_a+3
    lda #0
    ldx #11
clear:
    sta wide_a,x
    sta wide_b,x
    dex
    cpx #3
    bne clear
    sta wide_b+3
    sta wide_b+2
    lda fraction
    sta wide_b
    lda fraction+1
    sta wide_b+1
    jsr wide_multiply
    ; Add half a quantum before dropping the low ten bits.
    clc
    lda wide_product+1
    adc #2
    sta wide_product+1
    bcc :+
    inc wide_product+2
    bne :+
    inc wide_product+3
:
    .repeat 2
        lsr wide_product+4
        ror wide_product+3
        ror wide_product+2
        ror wide_product+1
    .endrepeat
    sec
    .repeat 4, I
        lda exp_value_q24+I
        sbc wide_product+1+I
        sta exp_value_q24+I
    .endrepeat
    rts
.endproc
