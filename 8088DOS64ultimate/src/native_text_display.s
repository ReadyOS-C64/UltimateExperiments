.include "native_text_display.inc"
.export dos64_native_text_setup, dos64_native_text_restore, dos64_native_text_state
.segment "DEVICESTATE"
dos64_native_text_state: .res ND_SIZE
nd_port: .res 1
nd_ddr: .res 1
.segment "DISPLAYCODE"
; Synchronous nonreentrant cold/overlay setup, no cursor or scheduler.
; Code must be writable/visible while KERNAL and I/O banking changes. Caller
; owns VIC raster IRQ compare (its high bit cannot be read back from D011),
; and IRQ/NMI handlers must not change these settings. No timer, ICR or TOD
; address is touched. Setup is idempotent; restore before setup is harmless.
; P except C restored; A/X/Y clobbered. Exact CPU DDR/output bits preserved.
; CIA PRA latent input latch bits and raster compare cannot be reconstructed.
.macro ND_ENTER
    php
    sei
    cld
    lda $00
    pha
    lda $01
    pha
    lda $00
    ora #7
    sta $00
    lda $01
    and #$F8
    ora #5
    sta $01
    pla
    sta nd_port
    pla
    sta nd_ddr
.endmacro
dos64_native_text_setup:
    ND_ENTER
    lda dos64_native_text_state+ND_READY
    bne nd_ok
    lda $D011
    and #$7F
    sta dos64_native_text_state+ND_D011
    lda $D016
    sta dos64_native_text_state+ND_D016
    lda $D018
    sta dos64_native_text_state+ND_D018
    lda $D015
    sta dos64_native_text_state+ND_D015
    lda $D020
    sta dos64_native_text_state+ND_D020
    lda $D021
    sta dos64_native_text_state+ND_D021
    lda $DD00
    sta dos64_native_text_state+ND_PRA
    and #$FC
    ora #2
    sta $DD00
    lda $DD02
    sta dos64_native_text_state+ND_DDRA
    ora #3
    sta $DD02
    lda #0
    sta $D015
    sta $D020
    sta $D021
    lda #$08
    sta $D018
    lda #$C8
    sta $D016
    lda #$3B
    sta $D011
    lda #1
    sta dos64_native_text_state+ND_READY
nd_ok:
    jmp nd_leave
dos64_native_text_restore:
    ND_ENTER
    lda dos64_native_text_state+ND_READY
    beq nd_ok
    lda dos64_native_text_state+ND_PRA
    sta $DD00
    lda dos64_native_text_state+ND_DDRA
    sta $DD02
    lda dos64_native_text_state+ND_D011
    sta $D011
    lda dos64_native_text_state+ND_D016
    sta $D016
    lda dos64_native_text_state+ND_D018
    sta $D018
    lda dos64_native_text_state+ND_D015
    sta $D015
    lda dos64_native_text_state+ND_D020
    sta $D020
    lda dos64_native_text_state+ND_D021
    sta $D021
    lda #0
    sta dos64_native_text_state+ND_READY
    jmp nd_leave
nd_leave:
    lda nd_ddr
    pha
    lda nd_port
    sta $01
    pla
    sta $00
    plp
    clc
    rts
