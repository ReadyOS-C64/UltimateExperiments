.setcpu "6502"
.export clock_start, clock_read, clock_delta, clock_elapsed
.export clock_now, clock_since, clock_rate, clock_is_pal
.export turbo_start, turbo_restore, turbo_readback, turbo_sample
.export turbo_detail, clock_detail, clock_controls

CIA_A_LO = $dd04
CIA_A_HI = $dd05
CIA_B_LO = $dd06
CIA_B_HI = $dd07
CIA_CRA = $dd0e
CIA_CRB = $dd0f
TURBO = $d031

.segment "PROBEBSS"
clock_now:      .res 4
clock_since:    .res 4
clock_elapsed:  .res 4
clock_latch:    .res 4
clock_rate:     .res 4
clock_is_pal:   .res 1
turbo_readback: .res 1
turbo_previous: .res 1
turbo_changed:  .res 1
turbo_sample:   .res 4
turbo_detail:   .res 1
clock_detail:   .res 1
clock_controls: .res 2

.segment "PROBE"
; $02a6 is the KERNAL's PAL detection result.
clock_start:
    lda $02a6
    and #1
    sta clock_is_pal
    tax
    lda clock_rate_lo,x
    sta clock_rate
    lda clock_rate_mid,x
    sta clock_rate+1
    lda clock_rate_hi,x
    sta clock_rate+2
    lda #0
    sta clock_rate+3
    sta CIA_CRA
    sta CIA_CRB
    lda #$ff
    sta CIA_A_LO
    sta CIA_A_HI
    sta CIA_B_LO
    sta CIA_B_HI
    lda #$51                    ; start B, count A underflow
    sta CIA_CRB
    lda #$11                    ; start A, count PHI2
    sta CIA_CRA
    rts

; Coherent cascaded read. Reject the A reload region and retry boundedly.
; Teardown or wrong mapping causes an invalid sample, not a bogus duration.
clock_read:
    lda #1
    sta clock_detail
    lda CIA_CRA
    sta clock_controls
    and #$61
    cmp #$01
    bne clock_fault
    inc clock_detail
    lda CIA_CRB
    sta clock_controls+1
    and #$61
    cmp #$41
    bne clock_fault
    inc clock_detail
    ; At 64 MHz a fast sequence of eight attempts can fit entirely in
    ; the A-high-byte FF guard region around underflow.
    ldx #128
retry:
    lda CIA_B_HI
    sta clock_latch+3
    lda CIA_B_LO
    sta clock_latch+2
    lda CIA_B_HI
    cmp clock_latch+3
    bne retry_next
    lda CIA_A_HI
    cmp #$ff
    beq retry_next
    sta clock_latch+1
    lda CIA_A_LO
    sta clock_latch
    lda CIA_A_HI
    cmp clock_latch+1
    bne retry_next
    lda CIA_B_LO
    cmp clock_latch+2
    bne retry_next
    lda CIA_B_HI
    cmp clock_latch+3
    bne retry_next
    lda #0
    sta clock_detail
    .repeat 4, I
        lda clock_latch+I
        eor #$ff
        sta clock_now+I
    .endrepeat
    clc
    rts
retry_next:
    dex
    bne retry
clock_fault:
    sec
    rts

clock_delta:
    sec
    .repeat 4, I
        lda clock_now+I
        sbc clock_since+I
        sta clock_elapsed+I
    .endrepeat
    rts

; Select max turbo with badline blocking disabled. Require both register
; readback and an independent elapsed-clock sanity check of effective rate.
turbo_start:
    lda #1
    sta turbo_detail
    lda TURBO
    cmp #$ff
    bne :+
    jmp turbo_fail
:
    sta turbo_previous
    and #$70
    ora #$8f
    sta TURBO
    inc turbo_changed
    lda TURBO
    sta turbo_readback
    inc turbo_detail
    and #$8f
    cmp #$8f
    beq :+
    jmp turbo_fail
:
    ; The initial A high byte is $ff for its first 256 PHI2 ticks.
    ; Wait for an observed tick-bounded start, not a CPU-time delay.
    ; 4096 I/O polls are far longer than 256 PHI2 ticks on this bus.
    inc turbo_detail
    ldy #16
    ldx #0
wait_clock:
    lda CIA_A_HI
    cmp #$ff
    bne clock_ready
    dex
    bne wait_clock
    dey
    bne wait_clock
    jmp turbo_fail
clock_ready:
    inc turbo_detail
    jsr clock_read
    bcs turbo_fail
    .repeat 4, I
        lda clock_now+I
        sta clock_since+I
    .endrepeat
    ; 329,217 instruction cycles, adjusted by the known page-crossing
    ; assertion below. At 64 MHz expect about 5050-5240 PHI2 ticks.
    ldy #0
turbo_outer:
    ldx #0
turbo_inner:
    dex
turbo_branch:
    bne turbo_inner
    dey
    bne turbo_outer
.assert >turbo_inner = >(turbo_branch+2), lderror, "turbo loop branch crosses a page"
    inc turbo_detail
    jsr clock_read
    bcs turbo_fail
    jsr clock_delta
    .repeat 4, I
        lda clock_elapsed+I
        sta turbo_sample+I
    .endrepeat
    inc turbo_detail
    lda clock_elapsed+3
    ora clock_elapsed+2
    bne turbo_fail
    ; Accept 4608..5887 ticks (upper bound excludes ~6700 at 48 MHz).
    lda clock_elapsed+1
    cmp #18
    bcc turbo_fail
    cmp #23
    bcs turbo_fail
    lda #0
    sta turbo_detail
    clc
    rts

turbo_fail:
    sec
    rts

turbo_restore:
    lda turbo_changed
    beq :+
    lda turbo_previous
    sta TURBO
:
    rts

; Nominal C64 PHI2 rates used for the display and exported to the host.
clock_rate_lo:  .byte <1022727, <985248
clock_rate_mid: .byte >1022727, >985248
clock_rate_hi:  .byte ^1022727, ^985248
