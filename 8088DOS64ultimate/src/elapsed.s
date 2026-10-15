.include "elapsed.inc"
.import dos64_host_clock_read, dos64_host_clock_ticks
.export dos64_elapsed_poll, dos64_elapsed_now

.segment "DEVICESTATE"
dos64_elapsed_now: .res 2

.segment "CODE"
.macro leave carry
    pla
    sta $01
    pla
    sta $00
    plp
    .if carry
        sec
    .else
        clc
    .endif
    rts
.endmacro
dos64_elapsed_poll:
    php
    sei
    cld
    lda $00
    pha
    ora #7
    sta $00
    lda $01
    pha
    and #$F8
    ora #5
    sta $01
    jsr dos64_host_clock_read
    bcs failed
    ; Compute the exact low 16 bits of the published 32-bit counter >> 12.
    ; Ownership excludes NMI/IRQ consumers during this two-byte publication.
    lda dos64_host_clock_ticks+1
    lsr
    lsr
    lsr
    lsr
    sta dos64_elapsed_now
    lda dos64_host_clock_ticks+2
    asl
    asl
    asl
    asl
    ora dos64_elapsed_now
    sta dos64_elapsed_now
    lda dos64_host_clock_ticks+2
    lsr
    lsr
    lsr
    lsr
    sta dos64_elapsed_now+1
    lda dos64_host_clock_ticks+3
    asl
    asl
    asl
    asl
    ora dos64_elapsed_now+1
    sta dos64_elapsed_now+1
    leave 0
failed:
    leave 1
