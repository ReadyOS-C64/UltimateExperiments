.setcpu "6502"
.export mul8_unsigned, mul_rhs, mul_result
.export set_lhs, multiply
.export dot_w8a16, dot_prepare, dot_weights, dot_columns, dot_result
.export activation_lo, activation_hi

.segment "ZEROPAGE"
plus_lo:     .res 2
plus_hi:     .res 2
minus_lo:    .res 2
minus_hi:    .res 2
mul_rhs:     .res 1
mul_result:  .res 2
dot_weights: .res 2
dot_columns: .res 1       ; zero encodes 256 columns
dot_result:  .res 4
weight_sign: .res 1
product:     .res 3

.segment "BSS"
activation_lo: .res 256
activation_hi: .res 256
magnitude_lo:  .res 256
magnitude_hi:  .res 256
activation_sign: .res 256
active_columns:  .res 256
active_any:      .res 1
active_last:     .res 1

.segment "RODATA"
; floor(s^2/4) and floor((s-255)^2/4), split into byte planes.
.align 256
square_lo:
.repeat 512, I
    .byte <((I * I) / 4)
.endrepeat
square_hi:
.repeat 512, I
    .byte >((I * I) / 4)
.endrepeat
difference_lo:
.repeat 512, I
    .byte <(((I-255) * (I-255)) / 4)
.endrepeat
difference_hi:
.repeat 512, I
    .byte >(((I-255) * (I-255)) / 4)
.endrepeat
; Two's-complement byte magnitudes. Indexed by the original weight.
weight_magnitude:
.repeat 128, I
    .byte I
.endrepeat
.repeat 128, I
    .byte 128-I
.endrepeat

.segment "CODE"
; A and mul_rhs are unsigned bytes. X preserved. Returns exact 16-bit product.
.proc mul8_unsigned
    jsr set_lhs
    ldy mul_rhs
    jsr multiply
    sta mul_result
    rts
.endproc

.proc init_tables
    lda #>square_lo
    sta plus_lo+1
    lda #>square_hi
    sta plus_hi+1
    lda #>difference_lo
    sta minus_lo+1
    lda #>difference_hi
    sta minus_hi+1
    rts
.endproc

.proc set_lhs
    pha
    jsr init_tables
    pla
    ; Fall through to fast path using already initialized high bytes.
.endproc
.proc set_lhs_low
    sta plus_lo
    sta plus_hi
    eor #$ff
    sta minus_lo
    sta minus_hi
    rts
.endproc

; Y = unsigned RHS. A = product low byte, mul_result+1 = high byte.
.proc multiply
    sec
    lda (plus_lo),y
    sbc (minus_lo),y
    pha
    lda (plus_hi),y
    sbc (minus_hi),y
    sta mul_result+1
    pla
    rts
.endproc

; Compact the signed activation vector once, in original column order.
; The sparse list is reused for every row of the matrix (or Q/K/V trio).
.proc dot_prepare
    ldx #0
    ldy #0
    stx active_any
column:
    lda activation_lo,x
    ora activation_hi,x
    beq advance
    lda #1
    sta active_any
    sty active_last
    txa
    sta active_columns,y
    lda activation_hi,x
    sta activation_sign,y
    bmi negative
    sta magnitude_hi,y
    lda activation_lo,x
    sta magnitude_lo,y
    jmp stored
negative:
    sec
    lda #0
    sbc activation_lo,x
    sta magnitude_lo,y
    lda #0
    sbc activation_hi,x
    sta magnitude_hi,y
stored:
    iny
advance:
    inx
    cpx dot_columns
    bne column
    jmp init_tables
.endproc

; Signed byte weights at dot_weights times the prepared signed word vector.
; Exact signed 32-bit result. Does not change the input or its preparation.
.proc dot_w8a16
    lda #0
    sta dot_result
    sta dot_result+1
    sta dot_result+2
    sta dot_result+3
    lda active_any
    bne :+
    rts
:
    ldx #0
column:
    ldy active_columns,x
    lda (dot_weights),y
    sta weight_sign
    tay
    lda weight_magnitude,y
    sta plus_lo
    sta plus_hi
    eor #$ff
    sta minus_lo
    sta minus_hi

    ldy magnitude_lo,x
    sec
    lda (plus_lo),y
    sbc (minus_lo),y
    sta product
    lda (plus_hi),y
    sbc (minus_hi),y
    sta product+1

    ldy magnitude_hi,x
    bne high_input
    tya
    beq high_done
high_input:
    sec
    lda (plus_lo),y
    sbc (minus_lo),y
    sta product+2
    lda (plus_hi),y
    sbc (minus_hi),y
    tay
    clc
    lda product+2
    adc product+1
    sta product+1
    tya
    adc #0
high_done:
    sta product+2
    lda weight_sign
    eor activation_sign,x
    bmi subtract
    clc
    lda dot_result
    adc product
    sta dot_result
    lda dot_result+1
    adc product+1
    sta dot_result+1
    lda dot_result+2
    adc product+2
    sta dot_result+2
    ; The product is at most three bytes. Update the fourth only on carry.
    bcc advance
    inc dot_result+3
    jmp advance
subtract:
    sec
    lda dot_result
    sbc product
    sta dot_result
    lda dot_result+1
    sbc product+1
    sta dot_result+1
    lda dot_result+2
    sbc product+2
    sta dot_result+2
    bcs advance
    dec dot_result+3
advance:
    cpx active_last
    beq done
    inx
    jmp column
done:
    rts
.endproc
