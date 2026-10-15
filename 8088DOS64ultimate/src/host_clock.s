.include "host_clock.inc"
.export dos64_host_clock_init, dos64_host_clock_read
.export dos64_host_clock_claim, dos64_host_clock_ready
.export dos64_host_clock_status, dos64_host_clock_ticks

CIA2_TALO = $dd04
CIA2_TAHI = $dd05
CIA2_TBLO = $dd06
CIA2_TBHI = $dd07
CIA2_CRA = $dd0e
CIA2_CRB = $dd0f

.segment "DEVICESTATE"
dos64_host_clock_claim: .res 1
dos64_host_clock_ready: .res 1
dos64_host_clock_status: .res 1
dos64_host_clock_ticks: .res 4
sample: .res 4
attempts: .res 1

.macro enter
    php
    sei
    cld
    pha
    txa
    pha
    tya
    pha
    lda $00
    pha
    lda $01
    pha
    lda $00
    ora #$07
    sta $00
    lda $01
    and #$f8
    ora #$05
    sta $01
.endmacro
.macro leave carry
    pla
    sta $01
    pla
    sta $00
    pla
    tay
    pla
    tax
    pla
    plp
    .if carry
        sec
    .else
        clc
    .endif
    rts
.endmacro

.segment "DEVICECODE"
.proc dos64_host_clock_init
    enter
    lda #0
    sta dos64_host_clock_ready
    lda dos64_host_clock_claim
    cmp #HC_OWNED
    beq owned
    lda #HC_ERR_OWNER
    sta dos64_host_clock_status
    leave 1
owned:
    ; Preserve TOD-related control bits, stop timers and remove serial/PB
    ; effects. Ownership includes these timer-related control fields.
    lda CIA2_CRA
    and #$80
    sta CIA2_CRA
    lda CIA2_CRB
    and #$80
    sta CIA2_CRB
    lda #$ff
    sta CIA2_TALO
    sta CIA2_TAHI
    sta CIA2_TBLO
    sta CIA2_TBHI
    lda CIA2_CRB
    ora #$41
    sta CIA2_CRB
    lda CIA2_CRA
    ora #$01
    sta CIA2_CRA
    lda #1
    sta dos64_host_clock_ready
    lda #HC_OK
    sta dos64_host_clock_status
    leave 0
.endproc

.proc dos64_host_clock_read
    enter
    lda dos64_host_clock_claim
    cmp #HC_OWNED
    beq owner_ok
    lda #HC_ERR_OWNER
    jmp failed
owner_ok:
    lda dos64_host_clock_ready
    cmp #1
    beq ready_ok
    lda #HC_ERR_UNREADY
    jmp failed
ready_ok:
    lda CIA2_CRA
    and #$7f
    cmp #$01
    bne control_error
    lda CIA2_CRB
    and #$7f
    cmp #$41
    beq control_ok
control_error:
    lda #HC_ERR_CONTROL
    jmp failed
control_ok:
    lda #HC_READ_ATTEMPTS
    sta attempts
retry:
    ; B high/low/high guards its byte seam, before the A sample.
    lda CIA2_TBHI
    sta sample+3
    lda CIA2_TBLO
    sta sample+2
    lda CIA2_TBHI
    cmp sample+3
    bne inconsistent
    ; A high/low/high guards its byte seam. FF excludes the reload
    ; window: cascaded B may lag A's underflow by a CIA pipeline tick.
    lda CIA2_TAHI
    cmp #$ff
    beq inconsistent
    sta sample+1
    lda CIA2_TALO
    sta sample
    lda CIA2_TAHI
    cmp sample+1
    bne inconsistent
    ; B is unchanged throughout A sampling, including a B-byte wrap.
    lda CIA2_TBHI
    cmp sample+3
    bne inconsistent
    lda CIA2_TBLO
    cmp sample+2
    bne inconsistent
    lda CIA2_TBHI
    cmp sample+3
    bne inconsistent
    ldx #3
publish:
    lda sample,x
    eor #$ff
    sta dos64_host_clock_ticks,x
    dex
    bpl publish
    lda #HC_OK
    sta dos64_host_clock_status
    leave 0
inconsistent:
    dec attempts
    bne retry
    lda #HC_ERR_SAMPLE
failed:
    sta dos64_host_clock_status
    leave 1
.endproc
