.include "abi.inc"
.macpack longbranch
.import dos64_native_timer_repeat, dos64_irq_result, cpu_error_return
.import dos64_cpu_irq_shadow
.import dos64_guest, dos64_cpu_value, dos64_cpu_opcode, dos64_cpu_yield
.import cpu_rep, cpu_override, cpu_return, cpu_complete, cpu_memory_error
.import dos64_cpu_word_read, dos64_cpu_word_write, dos64_physical, dos64_mem_read, dos64_mem_write
.import dos64_alu_apply, dos64_alu_lhs, dos64_alu_rhs, dos64_alu_op, dos64_alu_width
.importzp dos64_segment, dos64_offset, dos64_mem_value
.export dos64_strings_execute, dos64_string_pending

.segment "BSS"
dos64_string_pending: .res 1
string_width: .res 1
string_kind: .res 1
string_slice: .res 1
string_delta: .res 1

.segment "CODE"
; Tail-dispatched with cpu_step's saved host P. A call handles one non-REP
; instruction or at most16 REP iterations, sampling IRQ after every eligible element. Host scheduling yields preserve
; decoded prefixes/opcode and do not re-fetch possibly modified instruction
; bytes. They are not guest interrupts and do not emulate interrupt restart.
dos64_strings_execute:
    lda #16
    sta string_slice
    lda dos64_cpu_opcode
    and #1
    sta string_width
    clc
    adc #1
    sta string_delta
    lda dos64_cpu_opcode
    and #$FE
    sta string_kind
    lda cpu_rep
    beq string_iteration
    lda dos64_guest+G_CX
    ora dos64_guest+G_CX+1
    jeq string_complete
string_iteration:
    lda string_kind
    cmp #$AA
    beq @stos
    cmp #$AE
    beq @scas
    jsr string_source_address
    jsr string_read
    jcs string_error
    lda string_kind
    cmp #$AC
    beq @lods
    cmp #$A6
    beq @cmps
    ; MOVS: fetch complete source word before the destination write.
    jsr string_destination_address
    jsr string_write
    jcs string_error
    jmp string_advance_both
@cmps:
    jsr string_lhs
    jsr string_destination_address
    jsr string_read
    jcs string_error
    jsr string_compare
    jmp string_advance_both
@stos:
    jsr string_accumulator
    jsr string_destination_address
    jsr string_write
    jcs string_error
    jmp string_advance_destination
@scas:
    jsr string_accumulator
    jsr string_lhs
    jsr string_destination_address
    jsr string_read
    jcs string_error
    jsr string_compare
    jmp string_advance_destination
@lods:
    lda dos64_cpu_value
    sta dos64_guest+G_AX
    lda string_width
    beq @source
    lda dos64_cpu_value+1
    sta dos64_guest+G_AX+1
@source:
    ldx #G_SI
    jsr string_advance
    jmp string_iteration_complete
string_advance_both:
    ldx #G_SI
    jsr string_advance
string_advance_destination:
    ldx #G_DI
    jsr string_advance
string_iteration_complete:
    lda dos64_cpu_irq_shadow
    beq :+
    dec dos64_cpu_irq_shadow
:
    lda cpu_rep
    jeq string_complete
    lda dos64_guest+G_CX
    bne @low
    dec dos64_guest+G_CX+1
@low:
    dec dos64_guest+G_CX
    lda string_kind
    cmp #$A6
    beq @condition
    cmp #$AE
    bne @continue
@condition:
    lda cpu_rep
    cmp #$F3
    beq @repe
    ; REPNE continues while ZF is clear, after testing a real iteration.
    lda dos64_guest+G_FLAGS
    and #$40
    jne string_complete
    beq @continue
@repe:
    lda dos64_guest+G_FLAGS
    and #$40
    jeq string_complete
@continue:
    ; Microcode checks INTR here: after comparison's ZF exit, before CX-zero.
    ; pending marks a restartable completed element, including final CX=0.
    lda #1
    sta dos64_string_pending
    jsr dos64_native_timer_repeat
    jcs cpu_error_return
    lda dos64_irq_result
    cmp #1
    jeq cpu_return
    lda dos64_guest+G_CX
    ora dos64_guest+G_CX+1
    jeq string_complete
    dec string_slice
    jne string_iteration
    lda #1
    sta dos64_string_pending
    sta dos64_cpu_yield
    jmp cpu_return
string_complete:
    lda #0
    sta dos64_string_pending
    jmp cpu_complete
string_error:
    ; A host error is terminal. A partially committed word/iteration is not
    ; retried as a guest fault; previous complete iterations remain visible.
    lda #0
    sta dos64_string_pending
    jmp cpu_memory_error

string_source_address:
    ldx cpu_override
    cpx #$FF
    bne @segment
    ldx #G_DS
@segment:
    lda dos64_guest,x
    sta dos64_segment
    lda dos64_guest+1,x
    sta dos64_segment+1
    lda dos64_guest+G_SI
    sta dos64_offset
    lda dos64_guest+G_SI+1
    sta dos64_offset+1
    rts
string_destination_address:
    ; ES is fixed even when a source segment override was decoded.
    lda dos64_guest+G_ES
    sta dos64_segment
    lda dos64_guest+G_ES+1
    sta dos64_segment+1
    lda dos64_guest+G_DI
    sta dos64_offset
    lda dos64_guest+G_DI+1
    sta dos64_offset+1
    rts
string_read:
    lda string_width
    bne @word
    jsr dos64_physical
    jsr dos64_mem_read
    bcs @failed
    sta dos64_cpu_value
    lda #0
    sta dos64_cpu_value+1
@failed:
    rts
@word:
    jmp dos64_cpu_word_read
string_write:
    lda string_width
    bne @word
    lda dos64_cpu_value
    sta dos64_mem_value
    jsr dos64_physical
    jmp dos64_mem_write
@word:
    jmp dos64_cpu_word_write
string_accumulator:
    lda dos64_guest+G_AX
    sta dos64_cpu_value
    lda dos64_guest+G_AX+1
    sta dos64_cpu_value+1
    rts
string_lhs:
    lda dos64_cpu_value
    sta dos64_alu_lhs
    lda dos64_cpu_value+1
    sta dos64_alu_lhs+1
    rts
string_compare:
    lda dos64_cpu_value
    sta dos64_alu_rhs
    lda dos64_cpu_value+1
    sta dos64_alu_rhs+1
    lda string_width
    sta dos64_alu_width
    lda #7
    sta dos64_alu_op
    jmp dos64_alu_apply
string_advance:
    lda dos64_guest+G_FLAGS+1
    and #4
    bne @backward
    clc
    lda dos64_guest,x
    adc string_delta
    sta dos64_guest,x
    lda dos64_guest+1,x
    adc #0
    sta dos64_guest+1,x
    rts
@backward:
    sec
    lda dos64_guest,x
    sbc string_delta
    sta dos64_guest,x
    lda dos64_guest+1,x
    sbc #0
    sta dos64_guest+1,x
    rts
