.include "abi.inc"
.import dos64_host_clock_probe
.export dos64_entry, dos64_idle, dos64_mailbox, dos64_mailbox_end
.segment "LOADADDR"
    .word $0801
.segment "BASIC"
    .word $080b,10
    .byte $9e
    .asciiz "2061"
    .word 0
.segment "BSS"
dos64_mailbox: .res MB_SIZE
dos64_mailbox_end:
.segment "CODE"
dos64_entry:
    sei
    cld
    ldx #$ff
    txs
    lda #$2f
    sta $00
    lda #$35
    sta $01
    ; Explicit exclusive NMI takeover. Prior CIA state cannot be reconstructed.
    lda #<owned_nmi
    sta $fffa
    lda #>owned_nmi
    sta $fffb
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
    jsr dos64_host_clock_probe
dos64_idle:
    jmp dos64_idle
owned_nmi:
    rti
