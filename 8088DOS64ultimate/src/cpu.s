.include "abi.inc"
.import dos64_guest, dos64_cpu_reset, dos64_mem_read, dos64_mem_write, dos64_physical
.importzp dos64_segment, dos64_offset, dos64_mem_value
.macpack longbranch
.export dos64_cpu_init, dos64_cpu_step, dos64_cpu_status, dos64_cpu_opcode
.export dos64_cpu_instructions, dos64_cpu_yield, dos64_cpu_pending, dos64_cpu_irq_shadow
.export dos64_cpu_value, dos64_cpu_word_read, dos64_cpu_word_write
.export cpu_fetch8, cpu_fetch8_slow, cpu_fetch16, cpu_override, cpu_byte_registers
.import dos64_fetch_init, dos64_fast_fetch
.export cpu_complete, cpu_memory_error, cpu_unsupported, cpu_return, cpu_rep, cpu_relative
.import dos64_strings_execute, dos64_string_pending, dos64_shifts_execute, dos64_control_execute
.import dos64_stack_execute, dos64_math_execute, dos64_indirect_execute, dos64_adjust_execute
.import dos64_bios_port, dos64_bios_host_error
.import dos64_io_read, dos64_io_write, dos64_io_port, dos64_io_value, dos64_io_width
.import dos64_decode_rm, dos64_operand_read, dos64_operand_write, dos64_map_register
.import dos64_operand_width, dos64_modrm_reg, dos64_modrm_mod, dos64_operand_offset
.import dos64_operand_kind, dos64_operand_segment
.import dos64_alu_apply, dos64_alu_lhs, dos64_alu_rhs, dos64_alu_result, dos64_alu_op, dos64_alu_width

.segment "BSS"
dos64_cpu_status: .res 1       ; 0 running, 1 halted, 2 unsupported, 3 host memory error
dos64_cpu_opcode: .res 1
dos64_cpu_instructions: .res 4
dos64_cpu_yield: .res 1
dos64_cpu_pending: .res 1
dos64_cpu_irq_shadow: .res 1
dos64_cpu_value: .res 2
cpu_start_ip: .res 2
cpu_override: .res 1
cpu_rep: .res 1
cpu_lock: .res 1
cpu_slice: .res 1
cpu_reg: .res 1
cpu_byte: .res 1
cpu_low: .res 1
cpu_jump: .res 2
cpu_direction: .res 1
cpu_no_store: .res 1

.segment "RODATA"
cpu_byte_registers: .byte 0,2,4,6,1,3,5,7
cpu_stack_opcodes: .byte $06,$07,$0E,$16,$17,$1E,$1F,$9A,$9C,$9D,$9E,$9F,$C2,$C3,$CA,$CB,$E8

.segment "CODE"
dos64_cpu_init:
    jsr dos64_cpu_reset
    jsr dos64_fetch_init
    lda #0
    ldx #8
@clear:
    sta dos64_cpu_status,x
    dex
    bpl @clear
    sta dos64_string_pending
    rts

; One instruction or bounded prefix slice. P except C preserved, A/X/Y clobbered.
; Running/halted/yield return C clear. Unsupported/host error latch and return C
; set; init is required to resume. Host errors can leave partial memory writes.
dos64_cpu_step:
    php
    sei
    cld
    lda dos64_cpu_status
    beq @running
    cmp #1
    jeq cpu_return
    jmp cpu_error_return
@running:
    lda #0
    sta dos64_cpu_yield
    lda dos64_string_pending
    jne dos64_strings_execute
    lda #0
    sta cpu_slice
    lda dos64_cpu_pending
    bne cpu_prefix
    lda dos64_guest+G_IP
    sta cpu_start_ip
    lda dos64_guest+G_IP+1
    sta cpu_start_ip+1
    lda #$FF
    sta cpu_override
    lda #0
    sta cpu_rep
    sta cpu_lock
cpu_prefix:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_opcode
    cmp #$26
    beq @es
    cmp #$2E
    beq @cs
    cmp #$36
    beq @ss
    cmp #$3E
    beq @ds
    cmp #$F2
    beq @rep
    cmp #$F3
    beq @rep
    cmp #$F0
    beq @lock
    jmp cpu_dispatch
@es:
    lda #G_ES
    bne @segment
@cs:
    lda #G_CS
    bne @segment
@ss:
    lda #G_SS
    bne @segment
@ds:
    lda #G_DS
@segment:
    sta cpu_override
    jmp @next
@rep:
    sta cpu_rep
    jmp @next
@lock:
    sta cpu_lock
@next:
    inc cpu_slice
    lda cpu_slice
    cmp #64
    bcc cpu_prefix
    ; No invented 15-byte limit: yield and continue the same guest instruction.
    lda #1
    sta dos64_cpu_pending
    sta dos64_cpu_yield
    jmp cpu_return

cpu_dispatch:
    lda #0
    sta dos64_cpu_pending
    lda dos64_cpu_opcode
    cmp #$27
    jeq dos64_adjust_execute
    cmp #$2F
    jeq dos64_adjust_execute
    cmp #$37
    jeq dos64_adjust_execute
    cmp #$3F
    jeq dos64_adjust_execute
    cmp #$D4
    bcc @math
    cmp #$D8
    jcc dos64_adjust_execute
@math:
    cmp #$F6
    bcc @indirect
    cmp #$F8
    jcc dos64_math_execute
@indirect:
    cmp #$FE
    jcs dos64_indirect_execute
    cmp #$86
    bcc @short_branches
    cmp #$88
    jcc dos64_indirect_execute
    cmp #$8F
    jeq dos64_indirect_execute
    cmp #$98
    bcc @test_accumulator
    cmp #$9A
    jcc dos64_indirect_execute
@test_accumulator:
    cmp #$A8
    bcc @short_branches
    cmp #$AA
    jcc dos64_indirect_execute
@short_branches:
    cmp #$60
    bcc @strings
    cmp #$80
    jcc dos64_control_execute
@strings:
    cmp #$A4
    bcc @shift
    cmp #$A8
    jcc dos64_strings_execute
    cmp #$AA
    bcc @shift
    cmp #$B0
    jcc dos64_strings_execute
@shift:
    cmp #$D0
    bcc @interrupt
    cmp #$D4
    jcc dos64_shifts_execute
@interrupt:
    cmp #$CC
    bcc @loop
    cmp #$D0
    jcc dos64_control_execute
@loop:
    cmp #$E0
    bcc @stack
    cmp #$E4
    jcc dos64_control_execute
@stack:
    cmp #$50
    bcc @stack_table
    cmp #$60
    jcc dos64_stack_execute
@stack_table:
    ldx #16
@stack_scan:
    cmp cpu_stack_opcodes,x
    jeq dos64_stack_execute
    dex
    bpl @stack_scan
    cmp #$40
    bcs @inc_dec
    and #7
    cmp #6
    jcc cpu_arithmetic
    lda dos64_cpu_opcode
@inc_dec:
    cmp #$40
    bcc @binary
    cmp #$50
    jcc cpu_inc_dec
@binary:
    cmp #$80
    bcc @move
    cmp #$84
    jcc cpu_group_immediate
    cmp #$86
    jcc cpu_test_rm
@move:
    lda dos64_cpu_opcode
    cmp #$88
    bcc @immediate
    cmp #$8C
    jcc cpu_move_rm
    cmp #$8C
    jeq cpu_move_segment
    cmp #$8D
    jeq cpu_lea
    cmp #$8E
    jeq cpu_move_segment
@immediate:
    lda dos64_cpu_opcode
    cmp #$C4
    jeq cpu_load_far
    cmp #$C5
    jeq cpu_load_far
    cmp #$C6
    jeq cpu_move_rm_immediate
    cmp #$C7
    jeq cpu_move_rm_immediate
    cmp #$B0
    bcc @exchange
    cmp #$C0
    jcc cpu_mov_immediate
@exchange:
    cmp #$90
    bcc @moffs
    cmp #$98
    jcc cpu_exchange
@moffs:
    cmp #$A0
    bcc @control
    cmp #$A4
    jcc cpu_moffs
@control:
    cmp #$E4
    bcc @jump
    cmp #$E8
    jcc cpu_io
    cmp #$EC
    bcc @jump
    cmp #$F0
    jcc cpu_io
@jump:
    cmp #$EA
    jeq cpu_far_jump
    cmp #$E9
    jeq cpu_near_jump
    cmp #$EB
    jeq cpu_short_jump
    cmp #$F4
    beq @halt
    cmp #$F5
    jeq cpu_cmc
    cmp #$F8
    jeq cpu_clc
    cmp #$F9
    jeq cpu_stc
    cmp #$FA
    jeq cpu_cli
    cmp #$FB
    jeq cpu_sti
    cmp #$FC
    jeq cpu_cld
    cmp #$FD
    jeq cpu_std
    lda #2
    jmp cpu_fault
@halt:
    lda #1
    sta dos64_cpu_status
    jmp cpu_complete

cpu_io:
    lda dos64_cpu_opcode
    and #1
    sta dos64_io_width
    lda dos64_guest+G_AX
    sta dos64_io_value
    lda dos64_guest+G_AX+1
    sta dos64_io_value+1
    lda dos64_cpu_opcode
    and #8
    bne @dx
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_io_port
    lda #0
    sta dos64_io_port+1
    lda dos64_cpu_opcode
    cmp #$E6
    bne @cycle
    ; Private byte OUT callbacks require their exact owned synthetic ROM gate.
    lda dos64_io_port
    jsr dos64_bios_port
    jcc cpu_complete
    lda dos64_bios_host_error
    jne cpu_memory_error
    jmp @cycle
@dx:
    lda dos64_guest+G_DX
    sta dos64_io_port
    lda dos64_guest+G_DX+1
    sta dos64_io_port+1
@cycle:
    lda dos64_cpu_opcode
    and #2
    beq @read
    jsr dos64_io_write
    jcs cpu_unsupported
    jmp cpu_complete
@read:
    jsr dos64_io_read
    jcs cpu_unsupported
    lda dos64_io_value
    sta dos64_guest+G_AX
    lda dos64_io_width
    beq @done
    lda dos64_io_value+1
    sta dos64_guest+G_AX+1
@done:
    jmp cpu_complete

cpu_unsupported:
    lda #2
    jmp cpu_fault

cpu_set_width:
    lda dos64_cpu_opcode
    and #1
    sta dos64_operand_width
    sta dos64_alu_width
    rts
cpu_decode:
    jsr cpu_set_width
    jsr dos64_decode_rm
    rts
cpu_select_reg:
    lda dos64_modrm_reg
    jsr dos64_map_register
    sta cpu_reg
    rts
cpu_get_reg:
    ldx cpu_reg
    lda dos64_guest,x
    sta dos64_cpu_value
    lda #0
    ldy dos64_operand_width
    beq @high
    lda dos64_guest+1,x
@high:
    sta dos64_cpu_value+1
    rts
cpu_put_reg:
    ldx cpu_reg
    lda dos64_cpu_value
    sta dos64_guest,x
    lda dos64_operand_width
    beq @done
    lda dos64_cpu_value+1
    sta dos64_guest+1,x
@done:
    rts
cpu_lhs:
    lda dos64_cpu_value
    sta dos64_alu_lhs
    lda dos64_cpu_value+1
    sta dos64_alu_lhs+1
    rts
cpu_rhs:
    lda dos64_cpu_value
    sta dos64_alu_rhs
    lda dos64_cpu_value+1
    sta dos64_alu_rhs+1
    rts
cpu_result:
    lda dos64_alu_result
    sta dos64_cpu_value
    lda dos64_alu_result+1
    sta dos64_cpu_value+1
    rts
cpu_immediate_value:
    lda dos64_operand_width
    bne @word
    jsr cpu_fetch8
    bcs @failed
    sta dos64_cpu_value
    lda #0
    sta dos64_cpu_value+1
    clc
@failed:
    rts
@word:
    jmp cpu_fetch16

cpu_arithmetic:
    lda dos64_cpu_opcode
    lsr
    lsr
    lsr
    and #7
    sta dos64_alu_op
    lda #0
    sta cpu_no_store
    lda dos64_alu_op
    cmp #7
    bne @form
    inc cpu_no_store
@form:
    lda dos64_cpu_opcode
    and #7
    cmp #4
    bcs @accumulator
    jsr cpu_decode
    jcs cpu_memory_error
    jsr cpu_select_reg
    jsr dos64_operand_read
    jcs cpu_memory_error
    jsr cpu_lhs
    jsr cpu_get_reg
    jsr cpu_rhs
    lda dos64_cpu_opcode
    and #2
    sta cpu_direction
    beq cpu_alu_store
    ; Direction one reverses lhs/rhs; subtraction and compare depend on order.
    ldx #1
@swap:
    lda dos64_alu_lhs,x
    pha
    lda dos64_alu_rhs,x
    sta dos64_alu_lhs,x
    pla
    sta dos64_alu_rhs,x
    dex
    bpl @swap
    jmp cpu_alu_store
@accumulator:
    jsr cpu_set_width
    lda #G_AX
    sta cpu_reg
    lda #1
    sta cpu_direction
    jsr cpu_get_reg
    jsr cpu_lhs
    jsr cpu_immediate_value
    jcs cpu_memory_error
    jsr cpu_rhs
cpu_alu_store:
    jsr dos64_alu_apply
    lda cpu_no_store
    jne cpu_complete
    jsr cpu_result
    lda cpu_direction
    beq @rm
    jsr cpu_put_reg
    jmp cpu_complete
@rm:
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete

cpu_group_immediate:
    jsr cpu_decode
    jcs cpu_memory_error
    lda dos64_modrm_reg
    sta dos64_alu_op
    lda #0
    sta cpu_direction
    sta cpu_no_store
    lda dos64_alu_op
    cmp #7
    bne @lhs
    inc cpu_no_store
@lhs:
    jsr dos64_operand_read
    jcs cpu_memory_error
    jsr cpu_lhs
    lda dos64_cpu_opcode
    cmp #$83
    beq @signed
    jsr cpu_immediate_value
    jcs cpu_memory_error
    jmp @rhs
@signed:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_value
    ldx #0
    cmp #$80
    bcc @positive
    dex
@positive:
    stx dos64_cpu_value+1
@rhs:
    jsr cpu_rhs
    jmp cpu_alu_store

cpu_test_rm:
    jsr cpu_decode
    jcs cpu_memory_error
    jsr cpu_select_reg
    jsr dos64_operand_read
    jcs cpu_memory_error
    jsr cpu_lhs
    jsr cpu_get_reg
    jsr cpu_rhs
    lda #4
    sta dos64_alu_op
    jsr dos64_alu_apply
    jmp cpu_complete

cpu_inc_dec:
    lda #1
    sta dos64_operand_width
    sta dos64_alu_width
    lda dos64_cpu_opcode
    and #7
    asl
    sta cpu_reg
    jsr cpu_get_reg
    jsr cpu_lhs
    lda dos64_cpu_opcode
    and #8
    lsr
    lsr
    lsr
    ora #8
    sta dos64_alu_op
    jsr dos64_alu_apply
    jsr cpu_result
    jsr cpu_put_reg
    jmp cpu_complete

cpu_move_rm:
    jsr cpu_decode
    jcs cpu_memory_error
    jsr cpu_select_reg
    lda dos64_cpu_opcode
    and #2
    beq @write_rm
    jsr dos64_operand_read
    jcs cpu_memory_error
    jsr cpu_put_reg
    jmp cpu_complete
@write_rm:
    jsr cpu_get_reg
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete

cpu_move_rm_immediate:
    jsr cpu_decode
    jcs cpu_memory_error
    ; Original 8088 ignores the reg extension on C6/C7 (hardware aliases).
    jsr cpu_immediate_value
    jcs cpu_memory_error
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete

cpu_decode_word:
    lda #1
    sta dos64_operand_width
    sta dos64_alu_width
    jmp dos64_decode_rm
cpu_move_segment:
    jsr cpu_decode_word
    jcs cpu_memory_error
    lda dos64_modrm_reg
    and #3
    asl
    clc
    adc #G_ES
    sta cpu_reg
    lda dos64_cpu_opcode
    cmp #$8E
    beq @read_rm
    jsr cpu_get_reg
    jsr dos64_operand_write
    jcs cpu_memory_error
    jmp cpu_complete
@read_rm:
    jsr dos64_operand_read
    jcs cpu_memory_error
    jsr cpu_put_reg
    lda cpu_reg
    cmp #G_SS
    jne cpu_complete
    lda #2
    sta dos64_cpu_irq_shadow
    jmp cpu_complete

cpu_lea:
    jsr cpu_decode_word
    jcs cpu_memory_error
    lda dos64_operand_kind
    jeq cpu_unsupported
    jsr cpu_select_reg
    lda dos64_operand_offset
    sta dos64_cpu_value
    lda dos64_operand_offset+1
    sta dos64_cpu_value+1
    jsr cpu_put_reg
    jmp cpu_complete

cpu_load_far:
    jsr cpu_decode_word
    jcs cpu_memory_error
    lda dos64_operand_kind
    jeq cpu_unsupported
    jsr cpu_select_reg
    jsr dos64_operand_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta cpu_jump
    lda dos64_cpu_value+1
    sta cpu_jump+1
    clc
    lda dos64_operand_offset
    adc #2
    sta dos64_operand_offset
    bcc @second
    inc dos64_operand_offset+1
@second:
    jsr dos64_operand_read
    jcs cpu_memory_error
    ldx #G_ES
    lda dos64_cpu_opcode
    cmp #$C4
    beq @segment
    ldx #G_DS
@segment:
    lda dos64_cpu_value
    sta dos64_guest,x
    lda dos64_cpu_value+1
    sta dos64_guest+1,x
    lda cpu_jump
    sta dos64_cpu_value
    lda cpu_jump+1
    sta dos64_cpu_value+1
    jsr cpu_put_reg
    jmp cpu_complete

cpu_mov_immediate:
    and #7
    tax
    lda dos64_cpu_opcode
    cmp #$B8
    bcs @word
    lda cpu_byte_registers,x
    sta cpu_reg
    jsr cpu_fetch8
    jcs cpu_memory_error
    ldx cpu_reg
    sta dos64_guest,x
    jmp cpu_complete
@word:
    txa
    asl
    sta cpu_reg
    jsr cpu_fetch16
    jcs cpu_memory_error
    ldx cpu_reg
    lda dos64_cpu_value
    sta dos64_guest,x
    lda dos64_cpu_value+1
    sta dos64_guest+1,x
    jmp cpu_complete

cpu_exchange:
    and #7
    asl
    tax
    lda dos64_guest+G_AX
    pha
    lda dos64_guest,x
    sta dos64_guest+G_AX
    pla
    sta dos64_guest,x
    lda dos64_guest+G_AX+1
    pha
    lda dos64_guest+1,x
    sta dos64_guest+G_AX+1
    pla
    sta dos64_guest+1,x
    jmp cpu_complete

cpu_moffs:
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_offset
    lda dos64_cpu_value+1
    sta dos64_offset+1
    ldx cpu_override
    cpx #$FF
    bne @segment
    ldx #G_DS
@segment:
    lda dos64_guest,x
    sta dos64_segment
    lda dos64_guest+1,x
    sta dos64_segment+1
    lda dos64_cpu_opcode
    and #2
    bne @write
    lda dos64_cpu_opcode
    and #1
    beq @read_byte
    jsr dos64_cpu_word_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_guest+G_AX
    lda dos64_cpu_value+1
    sta dos64_guest+G_AX+1
    jmp cpu_complete
@read_byte:
    jsr dos64_physical
    jsr dos64_mem_read
    jcs cpu_memory_error
    sta dos64_guest+G_AX
    jmp cpu_complete
@write:
    lda dos64_guest+G_AX
    sta dos64_cpu_value
    sta dos64_mem_value
    lda dos64_guest+G_AX+1
    sta dos64_cpu_value+1
    lda dos64_cpu_opcode
    and #1
    beq @write_byte
    jsr dos64_cpu_word_write
    jcs cpu_memory_error
    jmp cpu_complete
@write_byte:
    jsr dos64_physical
    jsr dos64_mem_write
    jcs cpu_memory_error
    jmp cpu_complete

cpu_short_jump:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_value
    ldx #0
    cmp #$80
    bcc @positive
    dex
@positive:
    stx dos64_cpu_value+1
    jmp cpu_relative
cpu_near_jump:
    jsr cpu_fetch16
    jcs cpu_memory_error
cpu_relative:
    clc
    lda dos64_guest+G_IP
    adc dos64_cpu_value
    sta dos64_guest+G_IP
    lda dos64_guest+G_IP+1
    adc dos64_cpu_value+1
    sta dos64_guest+G_IP+1
    jmp cpu_complete
cpu_far_jump:
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta cpu_jump
    lda dos64_cpu_value+1
    sta cpu_jump+1
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_guest+G_CS
    lda dos64_cpu_value+1
    sta dos64_guest+G_CS+1
    lda cpu_jump
    sta dos64_guest+G_IP
    lda cpu_jump+1
    sta dos64_guest+G_IP+1
    jmp cpu_complete

cpu_cmc:
    lda dos64_guest+G_FLAGS
    eor #1
    bne cpu_low_flags
    beq cpu_low_flags
cpu_clc:
    lda dos64_guest+G_FLAGS
    and #$FE
    jmp cpu_low_flags
cpu_stc:
    lda dos64_guest+G_FLAGS
    ora #1
cpu_low_flags:
    sta dos64_guest+G_FLAGS
    jmp cpu_complete
cpu_cli:
    lda dos64_guest+G_FLAGS+1
    and #$FD
    jmp cpu_high_flags
cpu_sti:
    lda #2
    sta dos64_cpu_irq_shadow
    lda dos64_guest+G_FLAGS+1
    ora #2
    jmp cpu_high_flags
cpu_cld:
    lda dos64_guest+G_FLAGS+1
    and #$FB
    jmp cpu_high_flags
cpu_std:
    lda dos64_guest+G_FLAGS+1
    ora #4
cpu_high_flags:
    sta dos64_guest+G_FLAGS+1
cpu_complete:
    lda dos64_cpu_irq_shadow
    beq @count
    dec dos64_cpu_irq_shadow
@count:
    inc dos64_cpu_instructions
    bne cpu_return
    inc dos64_cpu_instructions+1
    bne cpu_return
    inc dos64_cpu_instructions+2
    bne cpu_return
    inc dos64_cpu_instructions+3
cpu_return:
    plp
    clc
    rts
cpu_memory_error:
    lda #3
cpu_fault:
    sta dos64_cpu_status
    lda cpu_start_ip
    sta dos64_guest+G_IP
    lda cpu_start_ip+1
    sta dos64_guest+G_IP+1
    lda #0
    sta dos64_cpu_pending
    sta dos64_string_pending
cpu_error_return:
    plp
    sec
    rts

cpu_fetch8:
    jmp dos64_fast_fetch
cpu_fetch8_slow:
    lda dos64_guest+G_CS
    sta dos64_segment
    lda dos64_guest+G_CS+1
    sta dos64_segment+1
    lda dos64_guest+G_IP
    sta dos64_offset
    lda dos64_guest+G_IP+1
    sta dos64_offset+1
    jsr dos64_physical
    jsr dos64_mem_read
    bcs @error
    sta cpu_byte
    inc dos64_guest+G_IP
    bne @read
    inc dos64_guest+G_IP+1
@read:
    lda cpu_byte
@error:
    rts
cpu_fetch16:
    jsr cpu_fetch8
    bcs @error
    sta cpu_low
    jsr cpu_fetch8
    bcs @error
    sta dos64_cpu_value+1
    lda cpu_low
    sta dos64_cpu_value
@error:
    rts

; Segmented word transfers wrap the offset before translating the second byte.
; Input segment/offset are preserved. Value is little endian; C reports memory
; failure. A failed high-byte store can leave a committed low byte.
dos64_cpu_word_read:
    php
    sei
    cld
    jsr dos64_physical
    jsr dos64_mem_read
    bcs word_failed
    sta dos64_cpu_value
    jsr word_next
    jsr dos64_physical
    jsr dos64_mem_read
    jsr word_previous
    bcs word_failed
    sta dos64_cpu_value+1
    plp
    clc
    rts
dos64_cpu_word_write:
    php
    sei
    cld
    lda dos64_cpu_value
    sta dos64_mem_value
    jsr dos64_physical
    jsr dos64_mem_write
    bcs word_failed
    jsr word_next
    lda dos64_cpu_value+1
    sta dos64_mem_value
    jsr dos64_physical
    jsr dos64_mem_write
    jsr word_previous
    bcs word_failed
    plp
    clc
    rts
word_failed:
    plp
    sec
    rts
word_next:
    inc dos64_offset
    bne @done
    inc dos64_offset+1
@done:
    rts
word_previous:
    ; Preserve A and carry from the transfer while restoring the input offset.
    pha
    lda dos64_offset
    bne @low
    dec dos64_offset+1
@low:
    dec dos64_offset
    pla
    rts
