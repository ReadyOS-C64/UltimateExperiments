.setcpu "6502"
.import set_lhs, multiply
.importzp mul_result
.export wide_a, wide_b, wide_product, wide_multiply, wide_divide, wide_mul_byte
.export wide_remainder, wide_round_divide, wide_sqrt, wide_root
.export wide_round_divide_score, wide_mul_byte_limited

; Unsigned little-endian arithmetic. 96 bits cover the RMS energy with
; guard bits even for all 96 channels at the signed 32-bit limit.
WIDTH = 12
NARROW_WIDTH = 7

.segment "ZEROPAGE"
divide_target:  .res 2

.segment "BSS"
wide_a:         .res WIDTH
wide_b:         .res WIDTH
wide_product:   .res WIDTH
wide_remainder: .res WIDTH
wide_root:      .res WIDTH
trial:          .res WIDTH
outer:          .res 1
inner:          .res 1
count_a:        .res 1
count_b:        .res 1
digits:         .res 1
bits:           .res 1
product_carry:  .res 1
divisor_index:  .res 1

.segment "CODE"
; A * B modulo 2^96 into product. Input words preserved.
.proc wide_multiply
    lda #0
    ldx #WIDTH-1
clear:
    sta wide_product,x
    dex
    bpl clear
    ldx #WIDTH-1
size_a:
    lda wide_a,x
    bne found_a
    dex
    bpl size_a
    rts
found_a:
    inx
    stx count_a
    ldx #WIDTH-1
size_b:
    lda wide_b,x
    bne found_b
    dex
    bpl size_b
    rts
found_b:
    inx
    stx count_b
    lda #0
    sta outer
row:
    ldx outer
    lda wide_a,x
    beq next_row
    jsr set_lhs
    lda #0
    sta inner
column:
    lda outer
    clc
    adc inner
    cmp #WIDTH
    bcs next_row
    tax
    ldy inner
    lda wide_b,y
    beq next_column
    tay
    jsr multiply
    clc
    adc wide_product,x
    sta wide_product,x
    ; INX and JMP preserve the carry from the low-byte addition.
    inx
    bcc high_without_carry
    cpx #WIDTH
    beq next_row
    sec
    bcs high
high_without_carry:
    cpx #WIDTH
    beq next_row
    clc
high:
    lda wide_product,x
    adc mul_result+1
    sta wide_product,x
    bcc next_column
carry:
    inx
    cpx #WIDTH
    beq next_column
    inc wide_product,x
    beq carry
next_column:
    inc inner
    lda inner
    cmp count_b
    bcc column
next_row:
    inc outer
    lda outer
    cmp count_a
    bcc row
    rts
.endproc

; A * low byte of B, modulo 2^96.
.proc wide_mul_byte
    ldx #WIDTH
    jmp wide_mul_byte_limited
.endproc

; X is the significant input width (1..12 bytes). Write up to X+1 low
; product bytes, capped at 12. Neither operand is modified.
.proc wide_mul_byte_limited
    stx count_b
    cpx #WIDTH
    bcc :+
    dex
:
    lda #0
    sta product_carry
clear:
    sta wide_product,x
    dex
    bpl clear
    lda wide_b
    bne size
    rts
size:
    ldx count_b
    dex
scan:
    lda wide_a,x
    bne found
    dex
    bpl scan
    rts
found:
    inx
    stx count_a
    lda wide_b
    jsr set_lhs
    ldx #0
byte:
    ldy wide_a,x
    jsr multiply
    clc
    adc product_carry
    sta wide_product,x
    lda mul_result+1
    adc #0
    sta product_carry
    inx
    cpx count_a
    bcc byte
    cpx #WIDTH
    bcs done
    sta wide_product,x
done:
    rts
.endproc

; Stream the dividend one byte at a time, from high to low. The input
; bit shifted out of the byte feeds the remainder, and the resulting
; quotient bit is shifted into the same byte. X starts at the top
; dividend byte. Only the active divisor bytes participate in the bit
; loop. A carry from the top of the remainder is an implicit extra bit.
.macro STREAM_DIVISOR name, width
.proc name
byte:
    ldy #8
    asl wide_a,x
digit_loop:
    .repeat width, I
        rol wide_remainder+I
    .endrepeat
    bcs subtract
    .repeat width, I
        lda wide_remainder+width-1-I
        cmp wide_b+width-1-I
        bcc digit
        bne subtract
    .endrepeat
subtract:
    sec
    .repeat width, I
        lda wide_remainder+I
        sbc wide_b+I
        sta wide_remainder+I
    .endrepeat
    ; The implied extra high bit may have supplied the borrow.
    sec
digit:
    rol wide_a,x
    dey
    .if width <= 5
        bne digit_loop
        dex
        bpl byte
    .else
        beq next_byte
        jmp digit_loop
next_byte:
        dex
        bmi done
        jmp byte
done:
    .endif
    clc
    rts
.endproc
.endmacro

STREAM_DIVISOR divide_1, 1
STREAM_DIVISOR divide_2, 2
STREAM_DIVISOR divide_3, 3
STREAM_DIVISOR divide_4, 4
STREAM_DIVISOR divide_5, 5
STREAM_DIVISOR divide_6, 6
STREAM_DIVISOR divide_7, 7

narrow_divide_lo: .lobytes divide_1, divide_2, divide_3, divide_4, divide_5, divide_6, divide_7
narrow_divide_hi: .hibytes divide_1, divide_2, divide_3, divide_4, divide_5, divide_6, divide_7

; Replace A with floor(A/B), expose the remainder. B is preserved.
; A zero denominator returns carry set.
.proc wide_divide
    ldx #WIDTH-1
denominator:
    lda wide_b,x
    bne found
    dex
    bpl denominator
    sec
    rts
found:
    stx divisor_index
    lda #0
    ldx #WIDTH-1
clear:
    sta wide_remainder,x
    dex
    bpl clear
    ldx #WIDTH-1
numerator:
    lda wide_a,x
    bne start
    dex
    bpl numerator
    clc
    rts
start:
    ldy divisor_index
    cpx divisor_index
    bcc smaller_dividend
    cpy #NARROW_WIDTH
    bcs full_width
    ; The leading divisor-width-minus-one dividend bytes are strictly
    ; less than B. Seed the remainder with them and leave zero quotient
    ; bytes before starting the bit loop on the rest of the dividend.
    dey
    bmi stream
prefix:
    lda wide_a,x
    sta wide_remainder,y
    lda #0
    sta wide_a,x
    dex
    dey
    bpl prefix
stream:
    ldy divisor_index
    lda narrow_divide_lo,y
    sta divide_target
    lda narrow_divide_hi,y
    sta divide_target+1
    jmp (divide_target)
smaller_dividend:
    lda wide_a,x
    sta wide_remainder,x
    lda #0
    sta wide_a,x
    dex
    bpl smaller_dividend
    clc
    rts
full_width:
    inx
    stx digits
    lda #8
    sta bits
    stx outer
next_bit:
    ldx #0
    asl wide_a
    ldy digits
    dey
    beq into_remainder
rotate_byte:
    inx
    rol wide_a,x
    dey
    bne rotate_byte
into_remainder:
    .repeat ::WIDTH, I
        rol wide_remainder+I
    .endrepeat
    bcs subtract
    ldx #WIDTH-1
compare:
    lda wide_remainder,x
    cmp wide_b,x
    bcc advance
    bne subtract
    dex
    bpl compare
subtract:
    sec
    .repeat ::WIDTH, I
        lda wide_remainder+I
        sbc wide_b+I
        sta wide_remainder+I
    .endrepeat
    inc wide_a
advance:
    dec bits
    bne continue
    lda #8
    sta bits
    dec outer
    beq finished
continue:
    jmp next_bit
finished:
    clc
    rts
.endproc

; Round nonnegative A/B to nearest, ties up. Use B - remainder instead
; of doubling the remainder, so the comparison also works at the limit.
.proc wide_round_divide
    jsr wide_divide
    bcc :+
    rts
:
    sec
    .repeat ::WIDTH, I
        lda wide_b+I
        sbc wide_remainder+I
        sta trial+I
    .endrepeat
    ldx #WIDTH-1
compare:
    lda wide_remainder,x
    cmp trial,x
    bcc no_round
    bne round
    dex
    bpl compare
round:
    ldx #0
increment:
    inc wide_a,x
    bne no_round
    inx
    cpx #WIDTH
    bcc increment
    sec
    rts
no_round:
    clc
done:
    rts
.endproc

; Divide the attention numerator by 127 * 2^40, rounding ties up.
; The top 56 bits divide by 127 with a one-byte remainder. The removed
; fraction matters only for remainder 63, where bit 39 breaks the tie.
.proc wide_round_divide_score
    lda wide_a+4
    and #$80
    sta bits
    ldx #0
move:
    lda wide_a+5,x
    sta wide_a,x
    inx
    cpx #7
    bne move
    lda #0
clear:
    sta wide_a,x
    inx
    cpx #WIDTH
    bne clear
    ldx #6
digit:
    asl wide_a,x
    .repeat 8
        rol
        cmp #127
        bcc :+
        sbc #127
:
        rol wide_a,x
    .endrepeat
    dex
    bpl digit
    cmp #63
    bcc done
    bne round_up
    bit bits
    bpl done
round_up:
    ldx #0
increment:
    inc wide_a,x
    bne done
    inx
    bne increment
done:
    rts
.endproc

; Integer square root of A by consuming one pair of digits per step.
; A is destroyed. The previous remainder is shifted by two, compared
; against 4 * old_root + 1, then reduced when a root bit is set.
.proc wide_sqrt
    lda #0
    ldx #WIDTH-1
clear:
    sta wide_root,x
    sta wide_remainder,x
    dex
    bpl clear
    lda #48
    sta bits
pair:
    .repeat 2
        asl wide_a
        .repeat ::WIDTH-1, I
            rol wide_a+I+1
        .endrepeat
        .repeat 7, I
            rol wide_remainder+I
        .endrepeat
    .endrepeat
    clc
    .repeat 7, I
        lda wide_root+I
        rol
        sta trial+I
    .endrepeat
    clc
    .repeat 7, I
        rol trial+I
    .endrepeat
    inc trial
    asl wide_root
    .repeat 6, I
        rol wide_root+I+1
    .endrepeat
    ldx #6
compare:
    lda wide_remainder,x
    cmp trial,x
    bcc advance
    bne subtract
    dex
    bpl compare
subtract:
    sec
    .repeat 7, I
        lda wide_remainder+I
        sbc trial+I
        sta wide_remainder+I
    .endrepeat
    inc wide_root
advance:
    dec bits
    beq done
    jmp pair
done:
    rts
.endproc
