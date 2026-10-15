.include "abi.inc"
.import dos64_guest, dos64_mailbox, dos64_cpu_reset
.ifdef DOS64_PROBE
.import dos64_reu_probe
.endif
.export dos64_entry, dos64_idle

.segment "LOADADDR"
    .word $0801
.segment "BASIC"
    .word $080B, 10
    .byte $9E
    .asciiz "2061"
    .word 0

.segment "CODE"
dos64_entry:
    sei
    cld
    ldx #$FF
    txs
    lda #$2F
    sta $00
    lda #$35
    sta $01
    jsr dos64_cpu_reset
    lda #0
    ldx #MB_SIZE-1
@clear:
    sta dos64_mailbox,x
    dex
    bpl @clear
    lda #DOS64_ABI_VERSION
    sta dos64_mailbox+MB_VERSION
    lda #STATUS_READY
    sta dos64_mailbox+MB_STATUS
    lda #5
    sta $D020
.ifdef DOS64_PROBE
    jsr dos64_reu_probe
.endif
dos64_idle:
    jmp dos64_idle
