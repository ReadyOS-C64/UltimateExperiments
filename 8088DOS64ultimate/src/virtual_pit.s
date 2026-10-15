.include "abi.inc"
.include "host_clock.inc"
.macpack longbranch
.import dos64_elapsed_poll, dos64_host_clock_ticks, dos64_host_clock_status
.import dos64_irq_pulse, dos64_irq_line, dos64_irq_result, dos64_cpu_status
.export dos64_pit_init, dos64_pit_rebase, dos64_pit_advance, dos64_pit_poll
.export dos64_pit_now, dos64_pit_last, dos64_pit_fraction, dos64_pit_phase
.export dos64_pit_until
.export dos64_pit_edges, dos64_pit_total, dos64_pit_ready, dos64_pit_error
.export dos64_pit_poll_error, dos64_pit_poll_enabled, dos64_pit_state_start, dos64_pit_state_end
; Initial fixed BIOS profile only: channel0 binary mode3, divisor65536,
; gate tied high. No guest PIT port access is handled by this prototype.
; Nominal XT PIT 13,125,000/11Hz / PAL985248Hz =546875/451572.
; Rational remainder survives every advance. No turbo CPU-time conversion.
.segment "DEVICESTATE"
dos64_pit_state_start:
dos64_pit_now: .res 4
dos64_pit_last: .res 4
dos64_pit_fraction: .res 3
dos64_pit_phase: .res 2
dos64_pit_edges: .res 2
dos64_pit_total: .res 4
dos64_pit_ready: .res 1
dos64_pit_error: .res 1
dos64_pit_poll_error: .res 1
dos64_pit_poll_enabled: .res 1
; Exact remaining raw phi2 ticks until the first next PIT edge.
dos64_pit_until: .res 2
pit_delta: .res 4
pit_product: .res 7
pit_factor: .res 7
pit_rem: .res 3
pit_count: .res 1
pit_phase: .res 2
pit_edges: .res 2
dos64_pit_state_end:
.segment "PITCODE"
dos64_pit_init:
    php
    sei
    cld
    lda #0
    ldx #dos64_pit_state_end-dos64_pit_state_start-5
@clear:
    sta dos64_pit_state_start+4,x
    dex
    bpl @clear
    lda #1
    sta dos64_pit_ready
    jmp pit_rebase
; Explicit pause/resume rebase: retain PIT phase/fraction/total, discard the
; unobserved host interval by caller policy, never synthesize BIOS ticks.
dos64_pit_rebase:
    php
    sei
    cld
    cld
    lda dos64_pit_ready
    beq pit_unready
pit_rebase:
    ldx #3
@copy:
    lda dos64_pit_now,x
    sta dos64_pit_last,x
    dex
    bpl @copy
    lda #0
    sta dos64_pit_error
    sta dos64_pit_edges
    sta dos64_pit_edges+1
    jsr pit_set_threshold
pit_ok:
    plp
    clc
    rts
pit_unready:
    lda #2
    sta dos64_pit_error
pit_failed:
    plp
    sec
    rts
pit_gap:
    lda #1
    sta dos64_pit_error
    jmp pit_failed
; 32-bit raw snapshot in now. Accept gaps0..32767*4096, modulo32bit wrap.
; Larger/reversed gaps latch error1 and require explicit rebase. Full raw
; wraps cannot be detected from two snapshots: caller must poll within window.
dos64_pit_advance:
    php
    sei
    cld
    lda #0
    sta dos64_pit_edges
    sta dos64_pit_edges+1
    lda dos64_pit_ready
    beq pit_unready
    lda dos64_pit_error
    bne pit_failed
    sec
    .repeat 4, I
        lda dos64_pit_now+I
        sbc dos64_pit_last+I
        sta pit_delta+I
    .endrepeat
    lda pit_delta+3
    and #$F8
    bne pit_gap
    ; Bound even worst subunit alignment to <=32767 elapsed units.
    lda pit_delta+3
    cmp #7
    bne @gap_ok
    lda pit_delta+2
    cmp #$FF
    bne @gap_ok
    lda pit_delta+1
    cmp #$F0
    bcc @gap_ok
    bne pit_gap
    lda pit_delta
    bne pit_gap
@gap_ok:
    lda pit_delta
    ora pit_delta+1
    ora pit_delta+2
    ora pit_delta+3
    beq pit_ok
    ; Only a validated delta strictly below the exact physical edge threshold
    ; may use binary increments. Public phase/fraction/epoch still update now.
    lda pit_delta+3
    ora pit_delta+2
    bne @full
    lda pit_delta+1
    cmp dos64_pit_until+1
    bcc @fast
    bne @full
    lda pit_delta
    cmp dos64_pit_until
    bcs @full
@fast:
    jmp pit_fast_noedge
@full:
    lda #0
    ldx #6
@zero:
    sta pit_product,x
    sta pit_factor,x
    dex
    bpl @zero
    lda #$3B
    sta pit_factor
    lda #$58
    sta pit_factor+1
    lda #$08
    sta pit_factor+2
    lda #32
    sta pit_count
@multiply:
    lsr pit_delta+3
    ror pit_delta+2
    ror pit_delta+1
    ror pit_delta
    bcc @shift
    clc
    .repeat 7, I
        lda pit_product+I
        adc pit_factor+I
        sta pit_product+I
    .endrepeat
@shift:
    asl pit_factor
    .repeat 6, I
        rol pit_factor+I+1
    .endrepeat
    dec pit_count
    bne @multiply
    ; Add the previous fractional remainder before division.
    clc
    .repeat 3, I
        lda pit_product+I
        adc dos64_pit_fraction+I
        sta pit_product+I
    .endrepeat
    .repeat 4, I
        lda pit_product+I+3
        adc #0
        sta pit_product+I+3
    .endrepeat
    lda #0
    sta pit_rem
    sta pit_rem+1
    sta pit_rem+2
    lda #56
    sta pit_count
@divide:
    asl pit_product
    .repeat 6, I
        rol pit_product+I+1
    .endrepeat
    rol pit_rem
    rol pit_rem+1
    rol pit_rem+2
    lda pit_rem+2
    cmp #$06
    bcc @next
    bne @subtract
    lda pit_rem+1
    cmp #$E3
    bcc @next
    bne @subtract
    lda pit_rem
    cmp #$F4
    bcc @next
@subtract:
    sec
    lda pit_rem
    sbc #$F4
    sta pit_rem
    lda pit_rem+1
    sbc #$E3
    sta pit_rem+1
    lda pit_rem+2
    sbc #$06
    sta pit_rem+2
    inc pit_product
@next:
    dec pit_count
    bne @divide
    ; Quotient=whole PIT input clocks. Divisor65536 allows direct quotient/
    ; remainder extraction; edges include an existing phase carry.
    clc
    lda dos64_pit_phase
    adc pit_product
    sta pit_phase
    lda dos64_pit_phase+1
    adc pit_product+1
    sta pit_phase+1
    lda pit_product+2
    adc #0
    sta pit_edges
    lda pit_product+3
    adc #0
    sta pit_edges+1
    ; Publish only after complete bounded arithmetic.
    ldx #3
@last:
    lda dos64_pit_now,x
    sta dos64_pit_last,x
    dex
    bpl @last
    ldx #2
@fraction:
    lda pit_rem,x
    sta dos64_pit_fraction,x
    dex
    bpl @fraction
    ldx #1
@phase:
    lda pit_phase,x
    sta dos64_pit_phase,x
    lda pit_edges,x
    sta dos64_pit_edges,x
    dex
    bpl @phase
    clc
    lda dos64_pit_total
    adc pit_edges
    sta dos64_pit_total
    lda dos64_pit_total+1
    adc pit_edges+1
    sta dos64_pit_total+1
    lda dos64_pit_total+2
    adc #0
    sta dos64_pit_total+2
    lda dos64_pit_total+3
    adc #0
    sta dos64_pit_total+3
    jsr pit_set_threshold
    lda dos64_pit_edges
    ora dos64_pit_edges+1
    jeq pit_ok
    ; No guest ran during this interval: all observed rising edges fold into
    ; the same PIC IRR0 latch. Guest INT08, never this routine, owns BDA ticks.
    lda #0
    sta dos64_irq_line
    jsr dos64_irq_pulse
    jmp pit_ok
; Production integration entry: use the same elapsed publication as UCI,
; but all32rawbits for conversion. SAMPLE4 is transient: retain last epoch,
; still allow existing PIC requests. Other host errors/gap are terminalCPU.
dos64_pit_poll:
    php
    sei
    cld
    lda #0
    sta dos64_pit_poll_error
    jsr dos64_elapsed_poll
    bcs @clock
    ldx #3
@copy:
    lda dos64_host_clock_ticks,x
    sta dos64_pit_now,x
    dex
    bpl @copy
    jsr dos64_pit_advance
    jcc pit_ok
    lda dos64_pit_error
    ora #$80                   ; distinguish PIT state/gap from CIA status
    sta dos64_pit_poll_error
    jmp @fatal
@clock:
    lda dos64_host_clock_status
    sta dos64_pit_poll_error
    cmp #HC_ERR_SAMPLE
    jeq pit_ok
@fatal:
    lda #3
    sta dos64_cpu_status
    lda #4
    sta dos64_irq_result
    jmp pit_failed

; Threshold and exact fast conversion share the same rational binary terms.
; For each raw-bit i: 2^i*N = q[i]*D+r[i], 0<=r[i]<D.
; Accumulator phase/rem is exact; trial product[0..4] adds one term and
; normalizes the remainder once. product[5] records phase16 overflow.
pit_load_acc:
    ldx #2
@frac:
    lda dos64_pit_fraction,x
    sta pit_rem,x
    dex
    bpl @frac
    lda dos64_pit_phase
    sta pit_phase
    lda dos64_pit_phase+1
    sta pit_phase+1
    rts
pit_commit_trial:
    lda pit_product
    sta pit_phase
    lda pit_product+1
    sta pit_phase+1
    .repeat 3,I
        lda pit_product+2+I
        sta pit_rem+I
    .endrepeat
    rts
pit_add_bit:
    clc
    lda pit_phase
    adc pit_qlo,x
    sta pit_product
    lda pit_phase+1
    adc pit_qhi,x
    sta pit_product+1
    lda #0
    adc #0
    sta pit_product+5
    clc
    lda pit_rem
    adc pit_rlo,x
    sta pit_product+2
    lda pit_rem+1
    adc pit_rmid,x
    sta pit_product+3
    lda pit_rem+2
    adc pit_rhi,x
    sta pit_product+4
    cmp #$06
    bcc @done
    bne @subtract
    lda pit_product+3
    cmp #$e3
    bcc @done
    bne @subtract
    lda pit_product+2
    cmp #$f4
    bcc @done
@subtract:
    sec
    lda pit_product+2
    sbc #$f4
    sta pit_product+2
    lda pit_product+3
    sbc #$e3
    sta pit_product+3
    lda pit_product+4
    sbc #6
    sta pit_product+4
    inc pit_product
    bne @done
    inc pit_product+1
    bne @done
    inc pit_product+5
@done:
    lda pit_product+5
    cmp #1
    rts
; Greedy inverse finds largest raw delta with no edge, then adds1. The
; conversion is monotone, so each accepted binary bit preserves an exact
; (phase,rem) candidate. Bounded16 trials, no host/turbo timing assumptions.
pit_set_threshold:
    jsr pit_load_acc
    lda #0
    sta pit_edges
    sta pit_edges+1
    sta pit_factor
    lda #$80
    sta pit_factor+1
    ldx #15
@bit:
    jsr pit_add_bit
    bcs @skip
    jsr pit_commit_trial
    lda pit_edges
    ora pit_factor
    sta pit_edges
    lda pit_edges+1
    ora pit_factor+1
    sta pit_edges+1
@skip:
    lsr pit_factor+1
    ror pit_factor
    dex
    bpl @bit
    clc
    lda pit_edges
    adc #1
    sta dos64_pit_until
    lda pit_edges+1
    adc #0
    sta dos64_pit_until+1
    rts
pit_fast_noedge:
    sec
    lda dos64_pit_until
    sbc pit_delta
    sta dos64_pit_until
    lda dos64_pit_until+1
    sbc pit_delta+1
    sta dos64_pit_until+1
    jsr pit_load_acc
    ldx #0
@bit:
    lsr pit_delta+1
    ror pit_delta
    bcc @next
    jsr pit_add_bit
    jsr pit_commit_trial
@next:
    inx
    lda pit_delta
    ora pit_delta+1
    bne @bit
    ldx #2
@frac:
    lda pit_rem,x
    sta dos64_pit_fraction,x
    dex
    bpl @frac
    lda pit_phase
    sta dos64_pit_phase
    lda pit_phase+1
    sta dos64_pit_phase+1
    ldx #3
@last:
    lda dos64_pit_now,x
    sta dos64_pit_last,x
    dex
    bpl @last
    jmp pit_ok
pit_qlo: .byte $01,$02,$04,$09,$13,$26,$4D,$9B,$36,$6C,$D8,$B0,$60,$C0,$81,$03
pit_qhi: .byte $00,$00,$00,$00,$00,$00,$00,$00,$01,$02,$04,$09,$13,$26,$4D,$9B
pit_rlo: .byte $47,$8E,$1C,$44,$94,$28,$5C,$C4,$88,$10,$20,$40,$80,$00,$0C,$24
pit_rmid: .byte $74,$E8,$D1,$BE,$98,$31,$7E,$18,$31,$63,$C6,$8C,$18,$31,$7E,$18
pit_rhi: .byte $01,$02,$05,$04,$02,$05,$03,$00,$00,$00,$00,$01,$03,$06,$05,$04
