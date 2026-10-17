.include "abi.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_opcode, dos64_cpu_value
.import dos64_decode_rm_owned, dos64_operand_read, dos64_operand_write
.import dos64_operand_width, dos64_modrm_reg
.import cpu_complete, cpu_memory_error
.export dos64_shifts_execute

.segment "BSS"
shift_result: .res 2
shift_count: .res 1
shift_carry: .res 1
shift_overflow: .res 1
shift_sign: .res 1
shift_flags: .res 1

.segment "CODE"
; Original 8088 D0-D3: use all eight CL bits, including 32 and 255.
; /6 is SETMO/SETMOC on this CPU, not the later SHL alias. Hardware
; SingleStepTests/8088 v2 pin aea84484abc79d09639d855b7b0ab32bc9e4dbeb
; establishes that result; all its arithmetic flags are masked undefined.
; Internal CPU entry inherits PHP/SEI/CLD from dos64_cpu_step.
dos64_shifts_execute:
    lda dos64_cpu_opcode
    and #1
    sta dos64_operand_width
    jsr dos64_decode_rm_owned
    jcs cpu_memory_error
    lda dos64_cpu_opcode
    and #2
    beq @one
    lda dos64_guest+G_CX
    beq @zero
    bne @count
@one:
    lda #1
@count:
    sta shift_count
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta shift_result
    lda dos64_cpu_value+1
    sta shift_result+1
    lda dos64_guest+G_FLAGS
    and #1
    sta shift_carry
    lda dos64_modrm_reg
    cmp #6
    jne shift_loop
    lda #$FF
    sta shift_result
    ldx dos64_operand_width
    beq @setmo
    sta shift_result+1
@setmo:
    lda #0
    sta shift_carry
    sta shift_overflow
    jmp shift_finish
@zero:
    ; Decode consumes displacement bytes but does not read/write the operand.
    ; No cache dirtiness, guest flags or operand change for a zero CL count.
    jmp cpu_complete

shift_loop:
    ldx dos64_operand_width
    lda shift_result,x
    and #$80
    sta shift_sign
    lda dos64_modrm_reg
    beq shift_rol
    cmp #1
    jeq shift_ror
    cmp #2
    jeq shift_rcl
    cmp #3
    jeq shift_rcr
    cmp #4
    jeq shift_shl
    cmp #5
    jeq shift_shr
    jmp shift_sar

shift_rol:
    asl shift_result
    lda dos64_operand_width
    beq @capture
    rol shift_result+1
@capture:
    lda #0
    rol
    sta shift_carry
    ora shift_result
    sta shift_result
    jmp shift_left_overflow

shift_rcl:
    lsr shift_carry
    rol shift_result
    lda dos64_operand_width
    beq @capture
    rol shift_result+1
@capture:
    lda #0
    rol
    sta shift_carry
    jmp shift_left_overflow

shift_shl:
    asl shift_result
    lda dos64_operand_width
    beq @capture
    rol shift_result+1
@capture:
    lda #0
    rol
    sta shift_carry
shift_left_overflow:
    ldx dos64_operand_width
    lda shift_result,x
    asl
    lda #0
    rol
    eor shift_carry
    sta shift_overflow
    jmp shift_next

shift_ror:
    lda dos64_operand_width
    beq @byte
    lsr shift_result+1
    ror shift_result
    jmp @capture
@byte:
    lsr shift_result
@capture:
    lda #0
    rol
    sta shift_carry
    beq shift_right_overflow
    ldx dos64_operand_width
    lda shift_result,x
    ora #$80
    sta shift_result,x
    jmp shift_right_overflow

shift_rcr:
    lsr shift_carry
    lda dos64_operand_width
    beq @low
    ror shift_result+1
@low:
    ror shift_result
    lda #0
    rol
    sta shift_carry
shift_right_overflow:
    ldx dos64_operand_width
    lda shift_result,x
    asl
    eor shift_result,x
    asl
    lda #0
    rol
    sta shift_overflow
    jmp shift_next

shift_shr:
    lda dos64_operand_width
    beq @byte
    lsr shift_result+1
    ror shift_result
    jmp @capture
@byte:
    lsr shift_result
@capture:
    lda #0
    rol
    sta shift_carry
    lda shift_sign
    asl
    lda #0
    rol
    sta shift_overflow
    jmp shift_next

shift_sar:
    lda shift_sign
    asl
    lda dos64_operand_width
    beq @low
    ror shift_result+1
@low:
    ror shift_result
    lda #0
    rol
    sta shift_carry
    lda #0
    sta shift_overflow
shift_next:
    dec shift_count
    jne shift_loop

shift_finish:
    lda dos64_guest+G_FLAGS
    and #$FE
    ora shift_carry
    sta shift_flags
    lda dos64_modrm_reg
    cmp #4
    bcc @flags
    ; Shifts update SZP. AF is undefined and deterministically cleared.
    lda shift_flags
    and #$2B
    sta shift_flags
    lda shift_result
    ora shift_result+1
    bne @sign
    lda shift_flags
    ora #$40
    sta shift_flags
@sign:
    ldx dos64_operand_width
    lda shift_result,x
    and #$80
    ora shift_flags
    sta shift_flags
    lda shift_result
    sta shift_sign
    lda #4
    ldy #8
@parity:
    lsr shift_sign
    bcc @next_bit
    eor #4
@next_bit:
    dey
    bne @parity
    ora shift_flags
    sta shift_flags
@flags:
    lda shift_flags
    sta dos64_guest+G_FLAGS
    lda shift_overflow
    asl
    asl
    asl
    sta shift_overflow
    lda dos64_guest+G_FLAGS+1
    and #$F7
    ora shift_overflow
    sta dos64_guest+G_FLAGS+1
    lda shift_result
    sta dos64_cpu_value
    lda shift_result+1
    sta dos64_cpu_value+1
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete
