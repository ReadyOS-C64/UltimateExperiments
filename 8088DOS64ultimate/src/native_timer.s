; Resident lease boundary for the combined IRQ/PIT image.
.include "abi.inc"
.include "host_clock.inc"
.import dos64_irq_callback_enabled, dos64_pit_poll_enabled, dos64_pit_now
.import dos64_irq_result, dos64_cpu_status, dos64_cpu_step
.import dos64_overlay_irq_repeat, dos64_overlay_pit_init, dos64_overlay_pit_rebase
.import dos64_overlay_error, dos64_elapsed_poll, dos64_host_clock_status, dos64_host_clock_ticks
.export dos64_native_timer_repeat, dos64_native_timer_step
.export dos64_native_timer_init, dos64_native_timer_resume
.segment "CODE"
; The disabled fast path never acquires an overlay. Preserve P except C.
; Enabled calls return entirely resident before the wrapped lease releases.
; A failed acquisition is terminal for the CPU; an acknowledged edge cannot
; safely be retried after arbitrary partial guest/cache effects.
dos64_native_timer_repeat:
 php
 lda #0
 sta dos64_irq_result
 lda dos64_irq_callback_enabled
 bne @enabled
 plp
 clc
 rts
@enabled:
 plp
 jsr dos64_overlay_irq_repeat
 bcc @return
 php
 lda #3
 sta dos64_cpu_status
 lda dos64_overlay_error
 beq @preserve_result
 lda #5
 sta dos64_irq_result
@preserve_result:
 plp
 sec
@return:
 rts
; Every ordinary instruction / HLT poll samples the physical clock first.
; REP samples additionally at the frozen original-8088 internal boundary.
dos64_native_timer_step:
 jsr dos64_native_timer_repeat
 bcs @return
 jmp dos64_cpu_step
@return:
 rts
; Called only after a successful physical elapsed sample, PIC/BIOS/IVT ready.
dos64_native_timer_init:
 jsr timer_epoch
 jsr dos64_overlay_pit_init
 bcs @return
 lda #1
 sta dos64_pit_poll_enabled
 sta dos64_irq_callback_enabled
 clc
@return:
 rts
; An explicit debugger pause discards unobserved wall time while preserving
; oscillator phase/remainder and PIC IRR/ISR. SAMPLE remains retryable.
dos64_native_timer_resume:
 jsr dos64_elapsed_poll
 bcs @return
 jsr timer_epoch
 jmp dos64_overlay_pit_rebase
@return:
 rts
timer_epoch:
 ldx #3
@copy:
 lda dos64_host_clock_ticks,x
 sta dos64_pit_now,x
 dex
 bpl @copy
 rts
