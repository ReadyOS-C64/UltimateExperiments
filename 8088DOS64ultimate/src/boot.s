.include "abi.inc"
.ifndef DOS64_PROBE
.ifndef DOS64_SNAPSHOT
.ifndef DOS64_CACHE_PROBE
DOS64_CORE_BOOT = 1
.import dos64_cpu_init
.endif
.endif
.endif
.import dos64_guest, dos64_mailbox, dos64_cpu_reset
.ifdef DOS64_PROBE
.import dos64_reu_probe
.endif
.if .defined(DOS64_SNAPSHOT)
.import dos64_reu_backup, dos64_reu_restore
.endif
.ifndef DOS64_PROBE
.ifndef DOS64_SNAPSHOT
.import dos64_cache_init, dos64_cache_limit
.endif
.endif
.ifdef DOS64_CACHE_PROBE
.import dos64_cache_probe
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
.ifdef DOS64_CORE_BOOT
    jsr dos64_cpu_init
.else
    jsr dos64_cpu_reset
.endif
.ifndef DOS64_PROBE
.ifndef DOS64_SNAPSHOT
    lda #32
    sta dos64_cache_limit
    jsr dos64_cache_init
.endif
.endif
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
.ifdef DOS64_CACHE_PROBE
    jsr dos64_cache_probe
.endif
.ifdef DOS64_SNAPSHOT
.ifdef DOS64_RESTORE
    jsr dos64_reu_restore
.else
    jsr dos64_reu_backup
.endif
.endif
dos64_idle:
    jmp dos64_idle
