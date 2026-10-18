.include "abi.inc"
.ifndef DOS64_TRAP1
DOS64_TRAP1=0
.endif
.if DOS64_TRAP1
.import dos64_guest,dos64_cpu_status,dos64_cpu_pending,dos64_cpu_irq_shadow
.import dos64_cpu_instructions,dos64_string_pending,dos64_irq_result
.import cpu_running,cpu_return,cpu_error_return,cpu_complete,cpu_wait,cpu_start_ip
.import dos64_interrupt_enter,dos64_native_timer_repeat
.export dos64_cpu_boundary,dos64_cpu_finish,dos64_segment_complete
.export dos64_trap_repeat,dos64_trap_wait,dos64_trap_state,dos64_trap_irq
.segment "BSS"
; 0 disabled,1 TF sampled for decoded instruction,2 due at boundary,3 entry.
dos64_trap_state:.res 1
.segment "CPUTRAP"
; Entered by tail jump with cpu_step's saved host P. Native timer/IRQ polling
; has already had its ordinary chance; a pending type1 precedes handler code.
dos64_cpu_boundary:
 lda dos64_cpu_status
 cmp #2
 bcc :+
 jmp cpu_error_return
: lda dos64_trap_state
 cmp #2
 beq trap_enter
 lda dos64_cpu_status
 beq :+
 jmp cpu_return
: lda dos64_cpu_pending
 ora dos64_string_pending
 bne :+
 lda dos64_guest+G_FLAGS+1
 and #1
 sta dos64_trap_state
: jmp cpu_running
trap_enter:
 ; Original REP restart retains only the last prefix, just like existing IRQ.
 lda dos64_string_pending
 beq :+
 sec
 lda dos64_guest+G_IP
 sbc #2
 sta dos64_guest+G_IP
 lda dos64_guest+G_IP+1
 sbc #0
 sta dos64_guest+G_IP+1
: lda dos64_guest+G_IP
 sta cpu_start_ip
 lda dos64_guest+G_IP+1
 sta cpu_start_ip+1
 lda #0
 sta dos64_string_pending
 sta dos64_cpu_status
 lda #3
 sta dos64_trap_state
 lda #1
 jmp dos64_interrupt_enter
; cpu_complete is also reached by the common software-IVT entry routine.
; Event entry is not a second completed instruction and does not eat a shadow.
dos64_cpu_finish:
 lda dos64_trap_state
 cmp #3
 bne :+
 lda #0
 sta dos64_trap_state
 jmp cpu_return
: asl dos64_trap_state
 lda dos64_cpu_irq_shadow
 beq :+
 dec dos64_cpu_irq_shadow
: inc dos64_cpu_instructions
 bne :+
 inc dos64_cpu_instructions+1
 bne :+
 inc dos64_cpu_instructions+2
 bne :+
 inc dos64_cpu_instructions+3
: jmp cpu_return
; All repaired-NMOS segment loads suppress their own boundary. This preserves
; the established general segment/IF shadow policy without reusing STI for TF.
dos64_segment_complete:
 lda #0
 sta dos64_trap_state
 lda #2
 sta dos64_cpu_irq_shadow
 jmp cpu_complete
; Same REP timer/IRQ poll, then arrange a type1 boundary before any further
; iteration. Existing delivered INTR still wins and supplies its own restart.
dos64_trap_repeat:
 jsr dos64_native_timer_repeat
 bcs :+
 lda dos64_trap_state
 cmp #1
 bne @ok
 lda #2
 sta dos64_trap_state
 lda #1
 sta dos64_irq_result
@ok:
 clc
: rts
; A pending WAIT test cycle can be observed without retiring WAIT itself.
dos64_trap_wait:
 asl dos64_trap_state
 jmp cpu_wait
.endif

.if DOS64_TRAP1
.segment "CPUTRAP"
; An INTR accepted immediately after POPF/IRET may precede the first traced
; instruction. Capture TF before INTR clears it, even without sampled state1.
dos64_trap_irq:
 lda dos64_guest+G_FLAGS+1
 and #1
 beq :+
 lda #2
 sta dos64_trap_state
: rts
.endif
