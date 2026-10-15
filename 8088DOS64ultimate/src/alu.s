.include "abi.inc"
.import dos64_guest
.macpack longbranch
.export dos64_alu_apply, dos64_alu_lhs, dos64_alu_rhs, dos64_alu_result
.export dos64_alu_op, dos64_alu_width

.segment "BSS"
dos64_alu_lhs: .res 2
dos64_alu_rhs: .res 2
dos64_alu_result: .res 2
dos64_alu_op: .res 1       ; ADD OR ADC SBB AND SUB XOR CMP INC DEC = 0..9
dos64_alu_width: .res 1    ; 0 byte, 1 word
alu_kind: .res 1
alu_host_flags: .res 1
alu_flags: .res 1
alu_carry: .res 1

.segment "RODATA"
alu_parity:
.include "parity.inc"

.segment "CODE"
; Actual binary 6502 ALU, with independent guest flags. Preserves host P except
; returned C, clobbers A/X/Y. Logic AF is deterministically cleared (undefined
; on original CPU); conformance uses the upstream defined-flag mask.
dos64_alu_apply:
    php
    sei
    cld
    lda dos64_alu_width
    cmp #2
    jcs @invalid
    lda dos64_alu_op
    cmp #10
    jcs @invalid
    sta alu_kind
    lda dos64_guest+G_FLAGS
    and #1
    sta alu_carry
    lda #0
    sta dos64_alu_result+1
    lda dos64_alu_op
    cmp #8
    bcc @normal
    lda #1
    sta dos64_alu_rhs
    lda #0
    sta dos64_alu_rhs+1
    lda dos64_alu_op
    cmp #8
    beq @inc
    lda #5
    bne @kind
@inc:
    lda #0
@kind:
    sta alu_kind
@normal:
    lda alu_kind
    cmp #7
    bne @classify
    lda #5
    sta alu_kind
@classify:
    cmp #1
    jeq @or
    cmp #4
    jeq @and
    cmp #6
    jeq @xor
    cmp #3
    beq @sbb
    cmp #5
    beq @sub
    ; ADD/ADC share native carry propagation; D is explicitly clear.
    cmp #2
    beq @adc_carry
    clc
    bcc @add
@adc_carry:
    lda alu_carry
    lsr
@add:
    lda dos64_alu_lhs
    adc dos64_alu_rhs
    sta dos64_alu_result
    lda dos64_alu_width
    beq @capture
    lda dos64_alu_lhs+1
    adc dos64_alu_rhs+1
    sta dos64_alu_result+1
    jmp @capture
@sbb:
    lda alu_carry
    eor #1
    lsr
    jmp @subtract
@sub:
    sec
@subtract:
    lda dos64_alu_lhs
    sbc dos64_alu_rhs
    sta dos64_alu_result
    lda dos64_alu_width
    beq @capture
    lda dos64_alu_lhs+1
    sbc dos64_alu_rhs+1
    sta dos64_alu_result+1
@capture:
    php
    pla
    sta alu_host_flags
    ; x86 borrow flag is the inverse of the 6502 SBC carry flag.
    lda alu_kind
    cmp #3
    beq @invert
    cmp #5
    bne @arith_flags
@invert:
    lda alu_host_flags
    eor #1
    sta alu_host_flags
@arith_flags:
    lda dos64_alu_lhs
    eor dos64_alu_rhs
    eor dos64_alu_result
    and #$10
    sta alu_flags
    jmp @flags
@or:
    lda dos64_alu_lhs
    ora dos64_alu_rhs
    sta dos64_alu_result
    lda dos64_alu_width
    beq @logic_flags
    lda dos64_alu_lhs+1
    ora dos64_alu_rhs+1
    sta dos64_alu_result+1
    jmp @logic_flags
@and:
    lda dos64_alu_lhs
    and dos64_alu_rhs
    sta dos64_alu_result
    lda dos64_alu_width
    beq @logic_flags
    lda dos64_alu_lhs+1
    and dos64_alu_rhs+1
    sta dos64_alu_result+1
    jmp @logic_flags
@xor:
    lda dos64_alu_lhs
    eor dos64_alu_rhs
    sta dos64_alu_result
    lda dos64_alu_width
    beq @logic_flags
    lda dos64_alu_lhs+1
    eor dos64_alu_rhs+1
    sta dos64_alu_result+1
@logic_flags:
    lda #0
    sta alu_host_flags
    sta alu_flags
@flags:
    lda dos64_guest+G_FLAGS
    and #$2A
    ora alu_flags
    sta alu_flags
    lda dos64_alu_op
    cmp #8
    bcs @keep_carry
    lda alu_host_flags
    and #1
    jmp @carry
@keep_carry:
    lda alu_carry
@carry:
    ora alu_flags
    sta alu_flags
    ldx dos64_alu_result
    lda alu_parity,x
    ora alu_flags
    sta alu_flags
    lda dos64_alu_result
    ora dos64_alu_result+1
    bne @sign
    lda alu_flags
    ora #$40
    sta alu_flags
@sign:
    ldx dos64_alu_width
    lda dos64_alu_result,x
    and #$80
    ora alu_flags
    sta dos64_guest+G_FLAGS
    lda alu_host_flags
    and #$40
    lsr
    lsr
    lsr
    sta alu_flags
    lda dos64_guest+G_FLAGS+1
    and #$F7
    ora alu_flags
    sta dos64_guest+G_FLAGS+1
    plp
    clc
    rts
@invalid:
    plp
    sec
    rts
