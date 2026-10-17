.include "abi.inc"
.ifndef DOS64_TRAP1
DOS64_TRAP1=0
.endif
.if DOS64_TRAP1
.import dos64_trap_irq
.endif
.macpack longbranch
.import dos64_pit_poll, dos64_pit_poll_enabled
.import dos64_guest, dos64_cpu_status, dos64_cpu_pending, dos64_cpu_irq_shadow
.import dos64_string_pending, dos64_cpu_value, dos64_cpu_word_read, dos64_stack_push
.import dos64_pic_imr, dos64_pic_irr, dos64_pic_isr, dos64_pic_base
.import dos64_pic_icw1, dos64_pic_icw4, dos64_pic_phase, dos64_pic_priority
.import dos64_pic_special_mask, dos64_pic_rotate_auto
.importzp dos64_segment, dos64_offset
.export dos64_irq_repeat, dos64_irq_callback_enabled
.export dos64_irq_pulse, dos64_irq_select, dos64_irq_try
.export dos64_irq_line, dos64_irq_selected, dos64_irq_result, dos64_irq_state_start, dos64_irq_state_end
.segment "DEVICESTATE"
dos64_irq_state_start:
dos64_irq_callback_enabled: .res 1
dos64_irq_line: .res 1
dos64_irq_selected: .res 1
dos64_irq_result: .res 1
irq_candidates: .res 1
irq_blockers: .res 1
irq_mask: .res 1
irq_target: .res 4
dos64_irq_state_end:
.segment "IRQDEVICE"
; Non-reentrant scheduler API; host P except C preserved, A/X/Y clobbered.
; Pulse is one low-high edge, not a level. Masked requests latch/coalesce.
dos64_irq_pulse:
    php
    sei
    cld
    ldx dos64_irq_line
    cpx #8
    jcs irq_invalid
    lda irq_bits,x
    ora dos64_pic_irr
    sta dos64_pic_irr
    plp
    clc
    rts
irq_invalid:
    plp
    sec
    rts
; Select leaves IRR/ISR/priority untouched. selected=FF means no eligible IRQ.
; Carry set means unsupported PIC configuration, never spurious IRQ7.
.segment "IRQMAIN"
dos64_irq_select:
    php
    sei
    cld
    jsr irq_select
    jcs irq_invalid
    plp
    clc
    rts
irq_select:
    lda #$FF
    sta dos64_irq_selected
    lda dos64_pic_phase
    bne @unsupported
    lda dos64_pic_icw1
    and #$1B
    cmp #$13
    bne @unsupported
    lda dos64_pic_icw4
    and #$11
    cmp #1
    bne @unsupported
    lda dos64_pic_icw4
    and #2
    beq @configured
    lda dos64_pic_icw4
    and #$0C
    cmp #8                    ; original pre1985 buffered slave lacks AEOI
    beq @unsupported
@configured:
    lda dos64_pic_imr
    eor #$FF
    and dos64_pic_irr
    sta irq_candidates
    ; No request can win priority arbitration; validated PIC state above still
    ; reports unsupported programming even with an empty/masked IRR.
    beq @none
    lda dos64_pic_isr
    sta irq_blockers
    lda dos64_pic_special_mask
    beq @scan
    lda dos64_pic_imr
    eor #$FF
    and irq_blockers
    sta irq_blockers
@scan:
    ldx dos64_pic_priority
    ldy #8
@next:
    inx
    txa
    and #7
    tax
    lda irq_bits,x
    sta irq_mask
    and irq_blockers
    bne @none                 ; equal priority ISR also blocks its own IRR
    lda irq_mask
    and irq_candidates
    bne @found
    dey
    bne @next
@none:
    clc
    rts
@found:
    stx dos64_irq_selected
    clc
    rts
@unsupported:
    sec
    rts
; try is called BETWEEN cpu_step calls. result:0 deferred,1 delivered,
; 2 memory terminal,3 unsupported PIC. No guest instruction count increment.
; CPU unsupported/memory states never deliver. HLT(status1) may wake.
; Prefix-only host slices are not architectural interrupt boundaries.
.segment "IRQDEVICE"
dos64_irq_try:
    php
    sei
    cld
    lda #0
    sta dos64_irq_result
    lda dos64_cpu_status
    cmp #2
    jcs irq_done
    lda dos64_cpu_pending
    ora dos64_cpu_irq_shadow
    jne irq_done
    lda dos64_guest+G_FLAGS+1
    and #2
    jeq irq_done
    jsr irq_select
    jcs irq_config_error
    ldx dos64_irq_selected
    jmi irq_done
    ; Logical INTA precedes all guest memory. A later host memory failure is
    ; terminal, never retry: otherwise an acknowledged edge could run twice.
    lda irq_bits,x
    eor #$FF
    and dos64_pic_irr
    sta dos64_pic_irr
    lda dos64_pic_icw4
    and #2
    bne @auto
    lda irq_bits,x
    ora dos64_pic_isr
    sta dos64_pic_isr
    jmp @vector
@auto:
    lda dos64_pic_rotate_auto
    beq @vector
    stx dos64_pic_priority
@vector:
    txa
    ora dos64_pic_base
    sta dos64_offset
    lda #0
    sta dos64_offset+1
    asl dos64_offset
    rol dos64_offset+1
    asl dos64_offset
    rol dos64_offset+1
    sta dos64_segment
    sta dos64_segment+1
    jsr dos64_cpu_word_read
    jcs irq_memory_error
    lda dos64_cpu_value
    sta irq_target
    lda dos64_cpu_value+1
    sta irq_target+1
    clc
    lda dos64_offset
    adc #2
    sta dos64_offset
    bcc @cs
    inc dos64_offset+1
@cs:
    jsr dos64_cpu_word_read
    jcs irq_memory_error
    lda dos64_cpu_value
    sta irq_target+2
    lda dos64_cpu_value+1
    sta irq_target+3
    ; Original8088 REP interrupt restart is opcode IP minus2, hence only
    ; the last prefix survives. Host yield alone retains all decoded prefixes.
    lda dos64_string_pending
    beq @flags
    sec
    lda dos64_guest+G_IP
    sbc #2
    sta dos64_guest+G_IP
    lda dos64_guest+G_IP+1
    sbc #0
    sta dos64_guest+G_IP+1
    lda #0
    sta dos64_string_pending
@flags:
    lda dos64_guest+G_FLAGS
    and #$D5
    ora #2
    sta dos64_cpu_value
    lda dos64_guest+G_FLAGS+1
    ora #$F0
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs irq_memory_error
 .if DOS64_TRAP1
    jsr dos64_trap_irq
 .endif
    lda dos64_guest+G_FLAGS+1
    and #$FC
    sta dos64_guest+G_FLAGS+1
    lda dos64_guest+G_CS
    sta dos64_cpu_value
    lda dos64_guest+G_CS+1
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs irq_memory_error
    lda dos64_guest+G_IP
    sta dos64_cpu_value
    lda dos64_guest+G_IP+1
    sta dos64_cpu_value+1
    jsr dos64_stack_push
    jcs irq_memory_error
    lda irq_target
    sta dos64_guest+G_IP
    lda irq_target+1
    sta dos64_guest+G_IP+1
    lda irq_target+2
    sta dos64_guest+G_CS
    lda irq_target+3
    sta dos64_guest+G_CS+1
    lda #0
    sta dos64_cpu_status
    lda #1
    sta dos64_irq_result
irq_done:
    plp
    clc
    rts
irq_config_error:
    lda #3
    sta dos64_irq_result
    plp
    sec
    rts
irq_memory_error:
    lda #3
    sta dos64_cpu_status
    lda #0
    sta dos64_cpu_pending
    sta dos64_string_pending
    lda #2
    sta dos64_irq_result
    plp
    sec
    rts
irq_bits: .byte 1,2,4,8,16,32,64,128

; Called only at a completed REP element's interrupt-sampling point.
; Disabled by default until the scheduler's PIC ownership is initialized.
; Native P except C is preserved, result0 means no transfer,1 delivered.
dos64_irq_repeat:
    php
    sei
    cld
    lda #0
    sta dos64_irq_result
    lda dos64_irq_callback_enabled
    beq @none
    lda dos64_pit_poll_enabled
    beq @arbitrate
    jsr dos64_pit_poll
    bcs @failed
@arbitrate:
    jsr dos64_irq_try
    bcs @failed
@none:
    plp
    clc
    rts
@failed:
    plp
    sec
    rts
