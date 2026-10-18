.include "abi.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_opcode, dos64_cpu_value, dos64_cpu_irq_shadow
.import cpu_fetch8_owned, cpu_relative, cpu_complete, cpu_memory_error
.import dos64_cpu_word_read, dos64_stack_push, dos64_stack_pop
.importzp dos64_segment, dos64_offset
.export dos64_control_execute, dos64_interrupt_enter

.segment "BSS"
control_truth: .res 1
control_vector: .res 2
control_ip: .res 2
control_cs: .res 2
control_flags: .res 2

.segment "CODE"
; Tail entered with cpu_step's host P on the stack. Original 60..6F aliases
; use the same sixteen conditions as 70..7F. No guest flags change on branches.
dos64_control_execute:
    lda dos64_cpu_opcode
    cmp #$80
    jcc control_condition
    cmp #$E0
    jcs control_loop
    cmp #$CF
    jeq control_iret
    cmp #$CE
    bne @vector
    lda dos64_guest+G_FLAGS+1
    and #8
    jeq cpu_complete
    lda #4
    bne dos64_interrupt_enter
@vector:
    cmp #$CC
    bne @immediate
    lda #3
    bne dos64_interrupt_enter
@immediate:
    jsr cpu_fetch8_owned
    jcs cpu_memory_error
dos64_interrupt_enter:
    sta control_vector
    lda #0
    sta control_vector+1
    asl control_vector
    rol control_vector+1
    asl control_vector
    rol control_vector+1
    ; Read IVT before pushes: stack and vector memory can alias on a real XT.
    lda #0
    sta dos64_segment
    sta dos64_segment+1
    lda control_vector
    sta dos64_offset
    lda control_vector+1
    sta dos64_offset+1
    jsr dos64_cpu_word_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta control_ip
    lda dos64_cpu_value+1
    sta control_ip+1
    clc
    lda dos64_offset
    adc #2
    sta dos64_offset
    bcc @segment
    inc dos64_offset+1
@segment:
    jsr dos64_cpu_word_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta control_cs
    lda dos64_cpu_value+1
    sta control_cs+1
    lda dos64_guest+G_FLAGS
    and #$D5
    ora #2
    sta dos64_cpu_value
    lda dos64_guest+G_FLAGS+1
    ora #$F0
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs cpu_memory_error
    lda dos64_guest+G_FLAGS+1
    and #$FC
    sta dos64_guest+G_FLAGS+1
    lda dos64_guest+G_CS
    sta dos64_cpu_value
    lda dos64_guest+G_CS+1
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs cpu_memory_error
    lda dos64_guest+G_IP
    sta dos64_cpu_value
    lda dos64_guest+G_IP+1
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs cpu_memory_error
    jmp control_commit

control_displacement:
    jsr cpu_fetch8_owned
    bcs @failed
    sta dos64_cpu_value
    ldx #0
    cmp #$80
    bcc @positive
    dex
@positive:
    stx dos64_cpu_value+1
    clc
@failed:
    rts
control_condition:
    jsr control_displacement
    jcs cpu_memory_error
    lda dos64_cpu_opcode
    lsr
    and #7
    tax
    beq @overflow
    dex
    beq @carry
    dex
    beq @zero
    dex
    beq @below_equal
    dex
    beq @sign
    dex
    beq @parity
    jsr control_less
    ldx dos64_cpu_opcode
    cpx #$6E
    beq @less_equal
    cpx #$6F
    beq @less_equal
    cpx #$7E
    beq @less_equal
    cpx #$7F
    bne @truth
@less_equal:
    sta control_truth
    lda dos64_guest+G_FLAGS
    and #$40
    ora control_truth
    jmp @truth
@overflow:
    lda dos64_guest+G_FLAGS+1
    and #8
    bne @truth
    beq @truth
@carry:
    lda dos64_guest+G_FLAGS
    and #1
    jmp @truth
@zero:
    lda dos64_guest+G_FLAGS
    and #$40
    jmp @truth
@below_equal:
    lda dos64_guest+G_FLAGS
    and #$41
    jmp @truth
@sign:
    lda dos64_guest+G_FLAGS
    and #$80
    jmp @truth
@parity:
    lda dos64_guest+G_FLAGS
    and #4
@truth:
    ldx #0
    cmp #0
    beq @normalized
    inx
@normalized:
    stx control_truth
    lda dos64_cpu_opcode
    and #1
    eor control_truth
    jeq cpu_complete
    jmp cpu_relative
control_less:
    lda dos64_guest+G_FLAGS+1
    and #8
    asl
    asl
    asl
    asl
    eor dos64_guest+G_FLAGS
    and #$80
    rts

control_loop:
    jsr control_displacement
    jcs cpu_memory_error
    lda dos64_cpu_opcode
    cmp #$E3
    beq @zero_cx
    lda dos64_guest+G_CX
    bne @decrement
    dec dos64_guest+G_CX+1
@decrement:
    dec dos64_guest+G_CX
    lda dos64_guest+G_CX
    ora dos64_guest+G_CX+1
    jeq cpu_complete
    lda dos64_cpu_opcode
    cmp #$E2
    jeq cpu_relative
    lda dos64_guest+G_FLAGS
    and #$40
    beq @not_zero
    lda dos64_cpu_opcode
    cmp #$E1
    jeq cpu_relative
    jmp cpu_complete
@not_zero:
    lda dos64_cpu_opcode
    cmp #$E0
    jeq cpu_relative
    jmp cpu_complete
@zero_cx:
    lda dos64_guest+G_CX
    ora dos64_guest+G_CX+1
    jne cpu_complete
    jmp cpu_relative

control_iret:
    jsr dos64_stack_pop
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta control_ip
    lda dos64_cpu_value+1
    sta control_ip+1
    jsr dos64_stack_pop
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta control_cs
    lda dos64_cpu_value+1
    sta control_cs+1
    jsr dos64_stack_pop
    jcs cpu_memory_error
    lda dos64_cpu_value
    and #$D5
    ora #2
    sta control_flags
    lda dos64_cpu_value+1
    and #$0F
    ora #$F0
    sta control_flags+1
    ; Same original flags-load IF transition policy as POPF. Trap scheduling
    ; is not implemented merely because TF can be restored.
    lda dos64_guest+G_FLAGS+1
    and #2
    bne @flags
    lda control_flags+1
    and #2
    beq @flags
    lda #2
    sta dos64_cpu_irq_shadow
@flags:
    lda control_flags
    sta dos64_guest+G_FLAGS
    lda control_flags+1
    sta dos64_guest+G_FLAGS+1
control_commit:
    lda control_ip
    sta dos64_guest+G_IP
    lda control_ip+1
    sta dos64_guest+G_IP+1
    lda control_cs
    sta dos64_guest+G_CS
    lda control_cs+1
    sta dos64_guest+G_CS+1
    jmp cpu_complete
