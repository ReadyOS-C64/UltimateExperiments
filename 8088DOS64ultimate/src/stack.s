.include "abi.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_value, dos64_cpu_opcode, dos64_cpu_irq_shadow
.import dos64_cpu_word_read, dos64_cpu_word_write
.import cpu_fetch16, cpu_complete, cpu_memory_error, cpu_unsupported
.importzp dos64_segment, dos64_offset
.export dos64_stack_push, dos64_stack_pop, dos64_stack_execute

.segment "BSS"
stack_reg: .res 1
stack_target: .res 2
stack_far: .res 2
stack_adjust: .res 2

.segment "CODE"
; Public synchronous stack words: input/output dos64_cpu_value, SS:SP. The
; 8088 word helpers wrap each byte's offset before 20-bit translation. Host P
; except returned C is preserved; A/X/Y and segment/offset scratch clobbered.
; Push commits SP before memory; a failed write can leave one byte committed.
; Pop advances SP only after the complete word read succeeds.
dos64_stack_push:
    php
    sei
    cld
    sec
    lda dos64_guest+G_SP
    sbc #2
    sta dos64_guest+G_SP
    lda dos64_guest+G_SP+1
    sbc #0
    sta dos64_guest+G_SP+1
    jsr stack_address
    jsr dos64_cpu_word_write
    bcs stack_failed
    plp
    clc
    rts

dos64_stack_pop:
    php
    sei
    cld
    jsr stack_address
    jsr dos64_cpu_word_read
    bcs stack_failed
    clc
    lda dos64_guest+G_SP
    adc #2
    sta dos64_guest+G_SP
    lda dos64_guest+G_SP+1
    adc #0
    sta dos64_guest+G_SP+1
    plp
    clc
    rts
stack_failed:
    plp
    sec
    rts
stack_address:
    lda dos64_guest+G_SS
    sta dos64_segment
    lda dos64_guest+G_SS+1
    sta dos64_segment+1
    lda dos64_guest+G_SP
    sta dos64_offset
    lda dos64_guest+G_SP+1
    sta dos64_offset+1
    rts

; Tail-dispatched from cpu_step, whose saved P is consumed by cpu_complete or
; the shared fault exit. Explicit matching also makes accidental dispatch fail.
dos64_stack_execute:
    lda dos64_cpu_opcode
    cmp #$50
    bcc @segment
    cmp #$60
    bcs @flags
    and #7
    asl
    sta stack_reg
    lda dos64_cpu_opcode
    and #8
    jne stack_pop_register
    ldx stack_reg
    jsr stack_load_register
    cpx #G_SP
    bne @push
    ; Original 8088 PUSH SP reads SP after its decrement, unlike 80186+.
    sec
    lda dos64_cpu_value
    sbc #2
    sta dos64_cpu_value
    lda dos64_cpu_value+1
    sbc #0
    sta dos64_cpu_value+1
@push:
    jmp stack_push_value
@segment:
    cmp #$06
    beq @es
    cmp #$07
    beq @es
    cmp #$0E
    beq @cs
    cmp #$16
    beq @ss
    cmp #$17
    beq @ss
    cmp #$1E
    beq @ds
    cmp #$1F
    jne cpu_unsupported
@ds:
    ldx #G_DS
    bne @register
@ss:
    ldx #G_SS
    bne @register
@cs:
    ldx #G_CS
    bne @register
@es:
    ldx #G_ES
@register:
    stx stack_reg
    and #1
    jne stack_pop_register
    jsr stack_load_register
    jmp stack_push_value
@flags:
    cmp #$9C
    jeq stack_push_flags
    cmp #$9D
    jeq stack_pop_flags
    cmp #$9E
    jeq stack_sahf
    cmp #$9F
    jeq stack_lahf
    cmp #$E8
    jeq stack_call_near
    cmp #$9A
    jeq stack_call_far
    cmp #$C2
    beq @return_immediate
    cmp #$CA
    beq @return_immediate
    cmp #$C3
    beq @return
    cmp #$CB
    jne cpu_unsupported
@return:
    lda #0
    sta stack_adjust
    sta stack_adjust+1
    jmp stack_return
@return_immediate:
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta stack_adjust
    lda dos64_cpu_value+1
    sta stack_adjust+1
    jmp stack_return

stack_load_register:
    lda dos64_guest,x
    sta dos64_cpu_value
    lda dos64_guest+1,x
    sta dos64_cpu_value+1
    rts
stack_push_value:
    jsr dos64_stack_push
    jcs cpu_memory_error
    jmp cpu_complete
stack_pop_register:
    jsr dos64_stack_pop
    jcs cpu_memory_error
    ldx stack_reg
    lda dos64_cpu_value
    sta dos64_guest,x
    lda dos64_cpu_value+1
    sta dos64_guest+1,x
    ; All segment POPs inhibit on repaired NMOS8088; general POPs do not.
    cpx #G_ES
    bcc @done
    lda #2
    sta dos64_cpu_irq_shadow
@done:
    jmp cpu_complete

stack_push_flags:
    lda dos64_guest+G_FLAGS
    and #$D5
    ora #2
    sta dos64_cpu_value
    lda dos64_guest+G_FLAGS+1
    ora #$F0
    sta dos64_cpu_value+1
    jmp stack_push_value
stack_pop_flags:
    lda dos64_guest+G_FLAGS+1
    and #2
    sta stack_reg
    jsr dos64_stack_pop
    jcs cpu_memory_error
    lda dos64_cpu_value
    and #$D5
    ora #2
    sta dos64_guest+G_FLAGS
    lda dos64_cpu_value+1
    and #$0F
    ora #$F0
    sta dos64_guest+G_FLAGS+1
    and #2
    beq @done
    lda stack_reg
    bne @done
    lda #2
    sta dos64_cpu_irq_shadow
@done:
    jmp cpu_complete
stack_sahf:
    lda dos64_guest+G_AX+1
    and #$D5
    ora #2
    sta dos64_guest+G_FLAGS
    jmp cpu_complete
stack_lahf:
    lda dos64_guest+G_FLAGS
    and #$D5
    ora #2
    sta dos64_guest+G_AX+1
    jmp cpu_complete

stack_call_near:
    jsr cpu_fetch16
    jcs cpu_memory_error
    clc
    lda dos64_cpu_value
    adc dos64_guest+G_IP
    sta stack_target
    lda dos64_cpu_value+1
    adc dos64_guest+G_IP+1
    sta stack_target+1
    ldx #G_IP
    jsr stack_load_register
    jsr dos64_stack_push
    jcs cpu_memory_error
    jmp stack_commit_ip
stack_call_far:
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta stack_target
    lda dos64_cpu_value+1
    sta stack_target+1
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta stack_far
    lda dos64_cpu_value+1
    sta stack_far+1
    ldx #G_CS
    jsr stack_load_register
    jsr dos64_stack_push
    jcs cpu_memory_error
    ldx #G_IP
    jsr stack_load_register
    jsr dos64_stack_push
    jcs cpu_memory_error
    jmp stack_commit_far
stack_return:
    jsr dos64_stack_pop
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta stack_target
    lda dos64_cpu_value+1
    sta stack_target+1
    lda dos64_cpu_opcode
    and #8
    beq @adjust
    jsr dos64_stack_pop
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta stack_far
    lda dos64_cpu_value+1
    sta stack_far+1
@adjust:
    clc
    lda dos64_guest+G_SP
    adc stack_adjust
    sta dos64_guest+G_SP
    lda dos64_guest+G_SP+1
    adc stack_adjust+1
    sta dos64_guest+G_SP+1
    lda dos64_cpu_opcode
    and #8
    beq stack_commit_ip
stack_commit_far:
    lda stack_far
    sta dos64_guest+G_CS
    lda stack_far+1
    sta dos64_guest+G_CS+1
stack_commit_ip:
    lda stack_target
    sta dos64_guest+G_IP
    lda stack_target+1
    sta dos64_guest+G_IP+1
    jmp cpu_complete
