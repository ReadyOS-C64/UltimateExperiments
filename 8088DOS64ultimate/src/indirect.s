.include "abi.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_opcode, dos64_cpu_value
.import cpu_fetch8, cpu_fetch16, cpu_complete, cpu_memory_error, cpu_unsupported
.import dos64_decode_rm, dos64_operand_read, dos64_operand_write, dos64_map_register
.import dos64_operand_width, dos64_operand_kind, dos64_operand_reg, dos64_modrm_reg
.import dos64_operand_offset
.import dos64_stack_push, dos64_stack_pop
.import dos64_alu_apply, dos64_alu_lhs, dos64_alu_rhs, dos64_alu_result, dos64_alu_op, dos64_alu_width
.export dos64_indirect_execute

.segment "BSS"
indirect_saved: .res 2
indirect_far: .res 2
indirect_reg: .res 1

.segment "CODE"
; Tail entry under cpu_step's PHP/SEI/CLD. No fabricated guest #UD exceptions:
; unimplemented/undefined forms use the core's explicit diagnostic exit.
dos64_indirect_execute:
    lda dos64_cpu_opcode
    cmp #$98
    jeq indirect_cbw
    cmp #$99
    jeq indirect_cwd
    cmp #$A8
    jeq indirect_test_accumulator
    cmp #$A9
    jeq indirect_test_accumulator
    cmp #$86
    jeq indirect_exchange
    cmp #$87
    jeq indirect_exchange
    cmp #$8F
    jeq indirect_pop
    cmp #$FE
    beq @group
    cmp #$FF
    jne cpu_unsupported
@group:
    jsr indirect_width
    jsr dos64_decode_rm
    jcs cpu_memory_error
    lda dos64_modrm_reg
    cmp #2
    bcc indirect_inc_dec
    lda dos64_cpu_opcode
    cmp #$FE
    jeq cpu_unsupported       ; unaudited undefined byte control/stack forms
    lda dos64_modrm_reg
    cmp #3
    jeq indirect_far_pointer
    cmp #5
    jeq indirect_far_pointer
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_modrm_reg
    cmp #6
    jcs indirect_push        ; original FF /7 aliases PUSH /6
    lda dos64_cpu_value
    sta indirect_saved
    lda dos64_cpu_value+1
    sta indirect_saved+1
    lda dos64_modrm_reg
    cmp #4
    jeq indirect_commit_ip
    jmp indirect_call_near

indirect_width:
    lda dos64_cpu_opcode
    and #1
    sta dos64_operand_width
    sta dos64_alu_width
    rts

indirect_inc_dec:
    lda dos64_modrm_reg
    clc
    adc #8
    sta dos64_alu_op
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_alu_lhs
    lda dos64_cpu_value+1
    sta dos64_alu_lhs+1
    jsr dos64_alu_apply
    lda dos64_alu_result
    sta dos64_cpu_value
    lda dos64_alu_result+1
    sta dos64_cpu_value+1
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete

indirect_push:
    lda dos64_operand_kind
    bne @push
    lda dos64_operand_reg
    cmp #G_SP
    bne @push
    ; PUSH SP uses the decremented value on the original 8088, also for FF.
    sec
    lda dos64_cpu_value
    sbc #2
    sta dos64_cpu_value
    lda dos64_cpu_value+1
    sbc #0
    sta dos64_cpu_value+1
@push:
    jsr dos64_stack_push
    jcs cpu_memory_error
    jmp cpu_complete

indirect_pop:
    lda #1
    sta dos64_operand_width
    jsr dos64_decode_rm
    jcs cpu_memory_error
    lda dos64_modrm_reg
    jne cpu_unsupported
    ; Retain the decoded address across the stack read. No 8088 ModR/M form
    ; uses SP as an EA base. For register SP, increment then overwrite with
    ; the popped value, just like the dedicated POP SP instruction.
    jsr dos64_stack_pop
    jcs cpu_memory_error
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete

indirect_far_pointer:
    lda dos64_operand_kind
    jeq cpu_unsupported       ; invalid register pointer depends on hidden EU state
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta indirect_saved
    lda dos64_cpu_value+1
    sta indirect_saved+1
    clc
    lda dos64_operand_offset
    adc #2
    sta dos64_operand_offset
    bcc @segment
    inc dos64_operand_offset+1
@segment:
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta indirect_far
    lda dos64_cpu_value+1
    sta indirect_far+1
    lda dos64_modrm_reg
    cmp #5
    beq indirect_commit_far
    ; Complete pointer loads before pushes: pointer and stack can alias.
    lda dos64_guest+G_CS
    sta dos64_cpu_value
    lda dos64_guest+G_CS+1
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs cpu_memory_error
    jsr indirect_push_ip
    jcs cpu_memory_error
indirect_commit_far:
    lda indirect_far
    sta dos64_guest+G_CS
    lda indirect_far+1
    sta dos64_guest+G_CS+1
indirect_commit_ip:
    lda indirect_saved
    sta dos64_guest+G_IP
    lda indirect_saved+1
    sta dos64_guest+G_IP+1
    jmp cpu_complete
indirect_call_near:
    jsr indirect_push_ip
    jcs cpu_memory_error
    jmp indirect_commit_ip
indirect_push_ip:
    lda dos64_guest+G_IP
    sta dos64_cpu_value
    lda dos64_guest+G_IP+1
    sta dos64_cpu_value+1
    jmp dos64_stack_push

indirect_exchange:
    jsr indirect_width
    jsr dos64_decode_rm
    jcs cpu_memory_error
    lda dos64_modrm_reg
    jsr dos64_map_register
    sta indirect_reg
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta indirect_saved
    lda dos64_cpu_value+1
    sta indirect_saved+1
    ldx indirect_reg
    lda dos64_guest,x
    sta dos64_cpu_value
    lda #0
    ldy dos64_operand_width
    beq @value
    lda dos64_guest+1,x
@value:
    sta dos64_cpu_value+1
    ; Write the memory/ModR/M destination before changing an EA base register.
    jsr dos64_operand_write
    jcs cpu_memory_error
    ldx indirect_reg
    lda indirect_saved
    sta dos64_guest,x
    lda dos64_operand_width
    beq @done
    lda indirect_saved+1
    sta dos64_guest+1,x
@done:
    jmp cpu_complete

indirect_test_accumulator:
    jsr indirect_width
    lda dos64_operand_width
    bne @word
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_value
    lda #0
    sta dos64_cpu_value+1
    beq @apply
@word:
    jsr cpu_fetch16
    jcs cpu_memory_error
@apply:
    lda dos64_cpu_value
    sta dos64_alu_rhs
    lda dos64_cpu_value+1
    sta dos64_alu_rhs+1
    lda dos64_guest+G_AX
    sta dos64_alu_lhs
    lda dos64_guest+G_AX+1
    sta dos64_alu_lhs+1
    lda #4
    sta dos64_alu_op
    jsr dos64_alu_apply
    jmp cpu_complete

indirect_cbw:
    ldx #0
    lda dos64_guest+G_AX
    bpl @positive
    dex
@positive:
    stx dos64_guest+G_AX+1
    jmp cpu_complete
indirect_cwd:
    ldx #0
    lda dos64_guest+G_AX+1
    bpl @positive
    dex
@positive:
    stx dos64_guest+G_DX
    stx dos64_guest+G_DX+1
    jmp cpu_complete
