.include "abi.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_value, dos64_cpu_opcode, cpu_rep
.import dos64_decode_rm_owned, dos64_operand_read, dos64_operand_write
.import dos64_operand_width, dos64_modrm_reg
.import dos64_alu_apply, dos64_alu_lhs, dos64_alu_rhs, dos64_alu_result, dos64_alu_op, dos64_alu_width
.import cpu_fetch8, cpu_fetch16, cpu_complete, cpu_memory_error, dos64_interrupt_enter
.export dos64_math_execute

.segment "BSS"
math_op: .res 1
math_width: .res 1
math_sign: .res 1
math_rem_sign: .res 1
math_count: .res 1
math_temp: .res 1
math_operand: .res 2
math_multiplicand: .res 4
math_multiplier: .res 2
math_result: .res 4
math_remainder: .res 2

.segment "CODE"
; Tail entry from cpu_step. Fixed bounds: multiplication at most16 shifts,
; division at most16 restoring steps. No host integer substitute is used.
dos64_math_execute:
    lda dos64_cpu_opcode
    and #1
    sta math_width
    sta dos64_operand_width
    sta dos64_alu_width
    jsr dos64_decode_rm_owned
    jcs cpu_memory_error
    lda dos64_modrm_reg
    sta math_op
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta math_operand
    lda dos64_cpu_value+1
    sta math_operand+1
    lda math_op
    cmp #2
    jcc math_test
    jeq math_not
    cmp #3
    jeq math_neg
    cmp #6
    jcs math_divide
    jmp math_multiply
math_test:
    lda math_operand
    sta dos64_alu_lhs
    lda math_operand+1
    sta dos64_alu_lhs+1
    lda math_width
    bne @word
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_value
    lda #0
    sta dos64_cpu_value+1
    jmp @rhs
@word:
    jsr cpu_fetch16
    jcs cpu_memory_error
@rhs:
    lda dos64_cpu_value
    sta dos64_alu_rhs
    lda dos64_cpu_value+1
    sta dos64_alu_rhs+1
    lda #4
    sta dos64_alu_op
    jsr dos64_alu_apply
    jmp cpu_complete
math_not:
    lda math_operand
    eor #$FF
    sta dos64_cpu_value
    lda math_operand+1
    eor #$FF
    sta dos64_cpu_value+1
    jmp math_write
math_neg:
    lda #0
    sta dos64_alu_lhs
    sta dos64_alu_lhs+1
    lda math_operand
    sta dos64_alu_rhs
    lda math_operand+1
    sta dos64_alu_rhs+1
    lda #5
    sta dos64_alu_op
    jsr dos64_alu_apply
    lda dos64_alu_result
    sta dos64_cpu_value
    lda dos64_alu_result+1
    sta dos64_cpu_value+1
math_write:
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete

math_multiply:
    lda #0
    sta math_sign
    sta math_result
    sta math_result+1
    sta math_result+2
    sta math_result+3
    sta math_multiplicand+2
    sta math_multiplicand+3
    lda dos64_guest+G_AX
    sta math_multiplier
    lda #0
    ldx math_width
    beq @multiplier
    lda dos64_guest+G_AX+1
@multiplier:
    sta math_multiplier+1
    lda math_op
    cmp #5
    bne @prefix
    ; Signed operands are multiplied as magnitudes, then result sign applied.
    ldx math_width
    lda math_operand,x
    bpl @acc_sign
    jsr math_negate_operand
    inc math_sign
@acc_sign:
    ldx math_width
    lda math_multiplier,x
    bpl @prefix
    sec
    lda #0
    sbc math_multiplier
    sta math_multiplier
    lda math_width
    beq @toggle
    lda #0
    sbc math_multiplier+1
    sta math_multiplier+1
@toggle:
    lda math_sign
    eor #1
    sta math_sign
@prefix:
    lda cpu_rep
    beq @setup
    lda math_sign
    eor #1
    sta math_sign
@setup:
    lda math_operand
    sta math_multiplicand
    lda math_operand+1
    sta math_multiplicand+1
    lda #8
    ldx math_width
    beq @count
    asl
@count:
    sta math_count
@loop:
    lsr math_multiplier+1
    ror math_multiplier
    bcc @shift
    clc
    lda math_result
    adc math_multiplicand
    sta math_result
    lda math_result+1
    adc math_multiplicand+1
    sta math_result+1
    lda math_result+2
    adc math_multiplicand+2
    sta math_result+2
    lda math_result+3
    adc math_multiplicand+3
    sta math_result+3
@shift:
    asl math_multiplicand
    rol math_multiplicand+1
    rol math_multiplicand+2
    rol math_multiplicand+3
    dec math_count
    bne @loop
    lda math_sign
    beq @flags
    ldy #4
    jsr math_negate_result
@flags:
    lda math_op
    cmp #5
    beq @signed_flags
    lda math_width
    bne @unsigned_word
    lda math_result+1
    jmp @overflow
@unsigned_word:
    lda math_result+2
    ora math_result+3
    jmp @overflow
@signed_flags:
    ldx math_width
    lda math_result,x
    bpl @expected
    lda #$FF
    bne @upper
@expected:
    lda #0
@upper:
    sta math_temp
    lda math_width
    bne @signed_word
    lda math_result+1
    eor math_temp
    jmp @overflow
@signed_word:
    lda math_result+2
    eor math_temp
    sta math_temp
    lda math_result+1
    bpl @positive_high
    lda math_result+3
    eor #$FF
    ora math_temp
    jmp @overflow
@positive_high:
    lda math_result+3
    ora math_temp
@overflow:
    tax
    lda dos64_guest+G_FLAGS
    and #$FE
    sta dos64_guest+G_FLAGS
    lda dos64_guest+G_FLAGS+1
    and #$F7
    sta dos64_guest+G_FLAGS+1
    cpx #0
    beq @store
    inc dos64_guest+G_FLAGS
    lda dos64_guest+G_FLAGS+1
    ora #8
    sta dos64_guest+G_FLAGS+1
@store:
    lda math_result
    sta dos64_guest+G_AX
    lda math_result+1
    sta dos64_guest+G_AX+1
    lda math_width
    jeq cpu_complete
    lda math_result+2
    sta dos64_guest+G_DX
    lda math_result+3
    sta dos64_guest+G_DX+1
    jmp cpu_complete

math_divide:
    lda #0
    sta math_sign
    sta math_rem_sign
    sta math_result+2
    sta math_result+3
    lda math_operand
    ora math_operand+1
    jeq math_divide_error
    lda dos64_guest+G_AX
    sta math_result
    lda dos64_guest+G_AX+1
    sta math_result+1
    lda math_width
    beq @signed
    lda dos64_guest+G_DX
    sta math_result+2
    lda dos64_guest+G_DX+1
    sta math_result+3
@signed:
    lda math_op
    cmp #7
    bne @setup
    ldx math_width
    lda math_operand,x
    bpl @dividend_sign
    jsr math_negate_operand
    inc math_sign
@dividend_sign:
    ldx #1
    lda math_width
    beq @test_sign
    ldx #3
@test_sign:
    lda math_result,x
    bpl @rep
    inc math_rem_sign
    lda math_sign
    eor #1
    sta math_sign
    ldy #2
    lda math_width
    beq @absolute
    ldy #4
@absolute:
    jsr math_negate_result
@rep:
    lda cpu_rep
    beq @setup
    lda math_sign
    eor #1
    sta math_sign
@setup:
    lda #0
    sta math_remainder+1
    lda math_width
    bne @word
    lda math_result+1
    sta math_remainder
    lda #0
    sta math_result+1
    lda #8
    bne @count
@word:
    lda math_result+2
    sta math_remainder
    lda math_result+3
    sta math_remainder+1
    lda #16
@count:
    sta math_count
    ; If the dividend's upper half is already >=divisor the quotient cannot
    ; fit the destination. This also protects the restoring-loop invariant.
    jsr math_remainder_compare
    jcs math_divide_error
@loop:
    asl math_result
    lda math_width
    beq @remainder
    rol math_result+1
@remainder:
    rol math_remainder
    rol math_remainder+1
    bcs @subtract
    jsr math_remainder_compare
    bcc @next
@subtract:
    sec
    lda math_remainder
    sbc math_operand
    sta math_remainder
    lda math_remainder+1
    sbc math_operand+1
    sta math_remainder+1
    inc math_result ; low bit was zero after shift, so this cannot carry
@next:
    dec math_count
    bne @loop
    lda math_op
    cmp #7
    bne @store
    ; Original8088 rejects magnitude80/8000 even for negative quotient.
    ldx math_width
    lda math_result,x
    jmi math_divide_error
    lda math_sign
    beq @remainder_sign
    sec
    lda #0
    sbc math_result
    sta math_result
    lda math_width
    beq @remainder_sign
    lda #0
    sbc math_result+1
    sta math_result+1
@remainder_sign:
    lda math_rem_sign
    beq @store
    sec
    lda #0
    sbc math_remainder
    sta math_remainder
    lda #0
    sbc math_remainder+1
    sta math_remainder+1
@store:
    lda math_result
    sta dos64_guest+G_AX
    lda math_width
    bne @store_word
    lda math_remainder
    sta dos64_guest+G_AX+1
    jmp cpu_complete
@store_word:
    lda math_result+1
    sta dos64_guest+G_AX+1
    lda math_remainder
    sta dos64_guest+G_DX
    lda math_remainder+1
    sta dos64_guest+G_DX+1
    jmp cpu_complete
math_divide_error:
    lda #0
    jmp dos64_interrupt_enter
math_remainder_compare:
    lda math_remainder+1
    cmp math_operand+1
    bne @done
    lda math_remainder
    cmp math_operand
@done:
    rts
math_negate_operand:
    sec
    lda #0
    sbc math_operand
    sta math_operand
    lda math_width
    beq @done
    lda #0
    sbc math_operand+1
    sta math_operand+1
@done:
    rts
math_negate_result:
    sec
    ldx #0
@byte:
    lda #0
    sbc math_result,x
    sta math_result,x
    inx
    dey
    bne @byte
    rts
