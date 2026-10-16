.include "abi.inc"
.import __CODE_RUN__, __CODE_SIZE__
.import dos64_guest, dos64_cpu_reset, dos64_mem_read, dos64_mem_write, dos64_physical
.importzp dos64_segment, dos64_offset, dos64_mem_value, dos64_address, dos64_mem_pointer
.import dos64_mem_access_kind, dos64_mem_write_span_byte
.macpack longbranch
.export dos64_cpu_init, dos64_cpu_step, dos64_cpu_status, dos64_cpu_opcode
.export dos64_cpu_instructions, dos64_cpu_yield, dos64_cpu_pending, dos64_cpu_irq_shadow
.export dos64_cpu_value, dos64_cpu_word_read, dos64_cpu_word_write
.export cpu_fetch8, cpu_fetch8_slow, cpu_fetch16, cpu_override, cpu_byte_registers
.import dos64_fetch_init, dos64_fast_fetch, dos64_fetch_owned_next
.export cpu_error_return
.export cpu_complete, cpu_memory_error, cpu_unsupported, cpu_return, cpu_rep, cpu_relative
.import dos64_strings_execute, dos64_string_pending, dos64_shifts_execute, dos64_control_execute
.import dos64_stack_execute, dos64_math_execute, dos64_indirect_execute, dos64_adjust_execute
.import dos64_bios_port, dos64_bios_host_error, dos64_bios_waiting
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

.segment "ZEROPAGE"
; Synchronous CPU-private scratch, never a public guest register or retained
; frame capability. Moving these bytes leaves the guest-state ABI unchanged.
cpu_reg: .res 1
cpu_byte: .res 1
cpu_low: .res 1
cpu_jump: .res 2
cpu_direction: .res 1
cpu_no_store: .res 1

.segment "RODATA"
cpu_byte_registers: .byte 0,2,4,6,1,3,5,7

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
    ; Prefix markers share the existing high-byte dispatch table. All normal
    ; handlers occupy low RAM. No guest byte is prefetched or cached here.
    tax
    lda cpu_table_hi,x
    bmi cpu_prefix_special
    sta cpu_jump+1
    lda cpu_table_lo,x
    sta cpu_jump
    lda #0
    sta dos64_cpu_pending
    lda dos64_cpu_opcode
    jmp (cpu_jump)
cpu_prefix_special:
    ; Low table bytes encode the last segment selector or REP/LOCK kind.
    ; X is still the original opcode index; only the seven high-byte markers
    ; can enter here. Keep the original opcode itself in REP/LOCK state.
    lda cpu_table_lo,x
    bmi @repeat_lock
    sta cpu_override
    jmp @next
@repeat_lock:
    cmp #$80
    bne @lock
    lda dos64_cpu_opcode
    sta cpu_rep
    jmp @next
@lock:
    lda dos64_cpu_opcode
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

 ; Pending state is cleared only after a non-prefix byte succeeds, exactly as
; before. Fetch faults and 64-prefix continuation retain the original state.
cpu_table_unsupported:
    lda #2
    jmp cpu_fault
cpu_table_halt:
    lda #1
    sta dos64_cpu_status
    jmp cpu_complete
; Every normal byte has an explicit target. The seven prefix high bytes are
; $80 markers; their low bytes are ignored. Unsupported forms keep the same
; diagnostic exit; instruction families still validate ModR/M and sub-opcodes.
.segment "RODATA"
cpu_table_lo:
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<dos64_stack_execute,<dos64_stack_execute
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<dos64_stack_execute,<cpu_table_unsupported
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<dos64_stack_execute,<dos64_stack_execute
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<dos64_stack_execute,<dos64_stack_execute
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,G_ES,<dos64_adjust_execute
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,G_CS,<dos64_adjust_execute
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,G_SS,<dos64_adjust_execute
    .byte <cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,<cpu_arithmetic,G_DS,<dos64_adjust_execute
    .byte <cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec
    .byte <cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec,<cpu_inc_dec
    .byte <dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute
    .byte <dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute
    .byte <dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute
    .byte <dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute
    .byte <dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute
    .byte <dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute
    .byte <cpu_group_immediate,<cpu_group_immediate,<cpu_group_immediate,<cpu_group_immediate,<cpu_test_rm,<cpu_test_rm,<dos64_indirect_execute,<dos64_indirect_execute
    .byte <cpu_move_rm,<cpu_move_rm,<cpu_move_rm,<cpu_move_rm,<cpu_move_segment,<cpu_lea,<cpu_move_segment,<dos64_indirect_execute
    .byte <cpu_exchange,<cpu_exchange,<cpu_exchange,<cpu_exchange,<cpu_exchange,<cpu_exchange,<cpu_exchange,<cpu_exchange
    .byte <dos64_indirect_execute,<dos64_indirect_execute,<dos64_stack_execute,<cpu_wait_test,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute,<dos64_stack_execute
    .byte <cpu_moffs,<cpu_moffs,<cpu_moffs,<cpu_moffs,<dos64_strings_execute,<dos64_strings_execute,<dos64_strings_execute,<dos64_strings_execute
    .byte <dos64_indirect_execute,<dos64_indirect_execute,<dos64_strings_execute,<dos64_strings_execute,<dos64_strings_execute,<dos64_strings_execute,<dos64_strings_execute,<dos64_strings_execute
    .byte <cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate
    .byte <cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate,<cpu_mov_immediate
    .byte <cpu_table_unsupported,<cpu_table_unsupported,<dos64_stack_execute,<dos64_stack_execute,<cpu_load_far,<cpu_load_far,<cpu_move_rm_immediate,<cpu_move_rm_immediate
    .byte <cpu_table_unsupported,<cpu_table_unsupported,<dos64_stack_execute,<dos64_stack_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute
    .byte <dos64_shifts_execute,<dos64_shifts_execute,<dos64_shifts_execute,<dos64_shifts_execute,<dos64_adjust_execute,<dos64_adjust_execute,<dos64_adjust_execute,<dos64_adjust_execute
    .byte <cpu_escape,<cpu_escape,<cpu_escape,<cpu_escape,<cpu_escape,<cpu_escape,<cpu_escape,<cpu_escape
    .byte <dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<dos64_control_execute,<cpu_io,<cpu_io,<cpu_io,<cpu_io
    .byte <dos64_stack_execute,<cpu_near_jump,<cpu_far_jump,<cpu_short_jump,<cpu_io,<cpu_io,<cpu_io,<cpu_io
    .byte $81,<cpu_table_unsupported,$80,$80,<cpu_table_halt,<cpu_cmc,<dos64_math_execute,<dos64_math_execute
    .byte <cpu_clc,<cpu_stc,<cpu_cli,<cpu_sti,<cpu_cld,<cpu_std,<dos64_indirect_execute,<dos64_indirect_execute
.assert *-cpu_table_lo = 256, error, "opcode low table must contain 256 entries"
cpu_table_hi:
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>dos64_stack_execute,>dos64_stack_execute
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>dos64_stack_execute,>cpu_table_unsupported
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>dos64_stack_execute,>dos64_stack_execute
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>dos64_stack_execute,>dos64_stack_execute
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,$80,>dos64_adjust_execute
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,$80,>dos64_adjust_execute
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,$80,>dos64_adjust_execute
    .byte >cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,>cpu_arithmetic,$80,>dos64_adjust_execute
    .byte >cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec
    .byte >cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec,>cpu_inc_dec
    .byte >dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute
    .byte >dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute
    .byte >dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute
    .byte >dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute
    .byte >dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute
    .byte >dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute
    .byte >cpu_group_immediate,>cpu_group_immediate,>cpu_group_immediate,>cpu_group_immediate,>cpu_test_rm,>cpu_test_rm,>dos64_indirect_execute,>dos64_indirect_execute
    .byte >cpu_move_rm,>cpu_move_rm,>cpu_move_rm,>cpu_move_rm,>cpu_move_segment,>cpu_lea,>cpu_move_segment,>dos64_indirect_execute
    .byte >cpu_exchange,>cpu_exchange,>cpu_exchange,>cpu_exchange,>cpu_exchange,>cpu_exchange,>cpu_exchange,>cpu_exchange
    .byte >dos64_indirect_execute,>dos64_indirect_execute,>dos64_stack_execute,>cpu_wait_test,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute,>dos64_stack_execute
    .byte >cpu_moffs,>cpu_moffs,>cpu_moffs,>cpu_moffs,>dos64_strings_execute,>dos64_strings_execute,>dos64_strings_execute,>dos64_strings_execute
    .byte >dos64_indirect_execute,>dos64_indirect_execute,>dos64_strings_execute,>dos64_strings_execute,>dos64_strings_execute,>dos64_strings_execute,>dos64_strings_execute,>dos64_strings_execute
    .byte >cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate
    .byte >cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate,>cpu_mov_immediate
    .byte >cpu_table_unsupported,>cpu_table_unsupported,>dos64_stack_execute,>dos64_stack_execute,>cpu_load_far,>cpu_load_far,>cpu_move_rm_immediate,>cpu_move_rm_immediate
    .byte >cpu_table_unsupported,>cpu_table_unsupported,>dos64_stack_execute,>dos64_stack_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute
    .byte >dos64_shifts_execute,>dos64_shifts_execute,>dos64_shifts_execute,>dos64_shifts_execute,>dos64_adjust_execute,>dos64_adjust_execute,>dos64_adjust_execute,>dos64_adjust_execute
    .byte >cpu_escape,>cpu_escape,>cpu_escape,>cpu_escape,>cpu_escape,>cpu_escape,>cpu_escape,>cpu_escape
    .byte >dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>dos64_control_execute,>cpu_io,>cpu_io,>cpu_io,>cpu_io
    .byte >dos64_stack_execute,>cpu_near_jump,>cpu_far_jump,>cpu_short_jump,>cpu_io,>cpu_io,>cpu_io,>cpu_io
    .byte $80,>cpu_table_unsupported,$80,$80,>cpu_table_halt,>cpu_cmc,>dos64_math_execute,>dos64_math_execute
    .byte >cpu_clc,>cpu_stc,>cpu_cli,>cpu_sti,>cpu_cld,>cpu_std,>dos64_indirect_execute,>dos64_indirect_execute

.assert *-cpu_table_hi = 256, error, "opcode high table must contain 256 entries"
.assert __CODE_RUN__ + __CODE_SIZE__ <= $8000, lderror, "dispatch prefix marker requires low-RAM CODE"

.segment "CODE"

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
    bne cpu_io_dx
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_io_port
    lda #0
    sta dos64_io_port+1
    lda dos64_cpu_opcode
    cmp #$E6
    bne cpu_io_cycle
    ; Private byte OUT callbacks require their exact owned synthetic ROM gate.
    lda dos64_io_port
    jsr dos64_bios_port
    bcc cpu_io_bios_result
    lda dos64_bios_host_error
    jne cpu_memory_error
    jmp cpu_io_cycle
cpu_io_bios_result:
    lda dos64_bios_waiting
    jeq cpu_complete
    jmp cpu_wait
cpu_wait_test:
    ; A completed WAIT TEST cycle ends the one-instruction IRQ inhibition,
    ; just as a completed REP primitive does, without retiring WAIT itself.
    lda #0
    sta dos64_cpu_irq_shadow
cpu_wait:
    ; Fixed absent8087 TEST inactive: WAIT yields at its original IP forever,
    ; permitting native scheduler/IRQ work without retiring a guest instruction.
    lda cpu_start_ip
    sta dos64_guest+G_IP
    lda cpu_start_ip+1
    sta dos64_guest+G_IP+1
    lda #1
    sta dos64_cpu_yield
    jmp cpu_return
cpu_io_dx:
    lda dos64_guest+G_DX
    sta dos64_io_port
    lda dos64_guest+G_DX+1
    sta dos64_io_port+1
cpu_io_cycle:
    lda dos64_cpu_opcode
    and #2
    beq cpu_io_read
    jsr dos64_io_write
    jcs cpu_unsupported
    jmp cpu_complete
cpu_io_read:
    jsr dos64_io_read
    jcs cpu_unsupported
    lda dos64_io_value
    sta dos64_guest+G_AX
    lda dos64_io_width
    beq cpu_io_done
    lda dos64_io_value+1
    sta dos64_guest+G_AX+1
cpu_io_done:
    jmp cpu_complete

cpu_unsupported = cpu_table_unsupported

; Original8088 ESC D8..DF is decoded even without8087. Memory forms perform
; a dummy word READ through the ordinary coherent guest bus; no form writes
; guest memory, registers or FLAGS, and no coprocessor status is invented.
cpu_escape:
    jsr cpu_decode_word
    jcs cpu_memory_error
    jsr dos64_operand_read
    jcs cpu_memory_error
    jmp cpu_complete

cpu_set_width:
    lda dos64_cpu_opcode
    and #1
    sta dos64_operand_width
    sta dos64_alu_width
    rts
cpu_decode:
    jsr cpu_set_width
    jmp dos64_decode_rm
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
    ; Repaired NMOS8088 inhibits after MOV to ANY segment (Intel/manual+die).
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
    jmp cpu_low_flags
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
    lda dos64_guest+G_FLAGS+1
    and #2
    bne @already
    lda #2
    sta dos64_cpu_irq_shadow
@already:
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

cpu_fetch8 = dos64_fast_fetch
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
    ; The continuation requires this exact preceding ownership validation.
    jsr dos64_fast_fetch
    bcs @error
    sta cpu_low
    jsr dos64_fetch_owned_next
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
    ; A successful low byte owns this resolution until the following access.
    ; Stay within one physical256-byte subpage and one offset256-byte subpage.
    ; Thus no512-byte cache/PC-region/20-bit/segment-offset seam is crossed.
    jsr word_span_check
    bcs @slow
    jsr dos64_mem_read_next_byte
    inc dos64_address
    jmp word_read_complete
@slow:
    jsr word_next
    jsr dos64_physical
    jsr dos64_mem_read
    jsr word_previous
    bcs word_failed
word_read_complete:
    sta dos64_cpu_value+1
word_success:
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
    jsr word_span_check
    bcs @slow
    lda dos64_cpu_value+1
    sta dos64_mem_value
    jsr dos64_mem_write_next_byte
    inc dos64_address
    jmp word_success
@slow:
    jsr word_next
    lda dos64_cpu_value+1
    sta dos64_mem_value
    jsr dos64_physical
    jsr dos64_mem_write
    jsr word_previous
    bcc word_success
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

; C clear proves both low-byte increments cannot cross any transfer seam.
word_span_check:
    lda dos64_address
    cmp #$FF
    beq @done
    lda dos64_offset
    cmp #$FF
@done:
    rts

; Internal synchronous continuation after a successful mem_read/mem_write.
; word_span_check proves both physical and segmented offsets remain inside
; one256-byte subpage; no intervening bus/cache operation is permitted.
; Holes have no pointer. ROM/hole writes remain ignored. CPU owns SEI/CLD.
dos64_mem_read_next_byte:
    lda dos64_mem_access_kind
    cmp #2
    beq @hole
    inc dos64_mem_pointer
    ldy #0
    lda (dos64_mem_pointer),y
    rts
@hole:
    lda #$FF
    rts

dos64_mem_write_next_byte:
    lda dos64_mem_access_kind
    beq @write
    cmp #3
    bne @ignored
@write:
    inc dos64_mem_pointer
    ldy #0
    ; Existing per-byte publication preserves generation, epoch and CGA dirty.
    jmp dos64_mem_write_span_byte
@ignored:
    rts
