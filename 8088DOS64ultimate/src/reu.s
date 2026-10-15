.include "abi.inc"
.include "reu.inc"
.export dos64_reu_request, dos64_reu_transfer
.exportzp reu_host_end, reu_far_end

.segment "ZEROPAGE"
reu_host_end: .res 2
reu_far_end: .res 2
.segment "BSS"
dos64_reu_request: .res R_SIZE

.segment "CODE"
; One immediate DMA chunk, RAM->REU (0) or REU->RAM (1).
; Nonzero count, host [$0200,$D000), no crossing an REU 64 KiB bank.
; An exact end at the bank boundary is valid. A higher-level range copier must
; split larger ranges; this avoids the REC's 512 KiB wrap on expanded REUs.
; Input/output: exported request. Out: C clear success; C set + R_ERROR failure.
; Clobbers A/X and 4 ZP bytes. Preserves Y, all P except C, $00/$01 output bits.
; Exclusive REU ownership; disables REU IRQ/autoload/fixed address modes.
dos64_reu_transfer:
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
    lda #0
    sta dos64_reu_request+R_ERROR
    sta dos64_reu_request+R_STATUS
    lda dos64_reu_request+R_DIRECTION
    cmp #2
    bcs @mode
    lda dos64_reu_request+R_LENGTH
    ora dos64_reu_request+R_LENGTH+1
    beq @zero
    lda dos64_reu_request+R_HOST+1
    cmp #2
    bcc @range
    clc
    lda dos64_reu_request+R_HOST
    adc dos64_reu_request+R_LENGTH
    sta reu_host_end
    lda dos64_reu_request+R_HOST+1
    adc dos64_reu_request+R_LENGTH+1
    sta reu_host_end+1
    bcs @range
    cmp #$D0
    bcc @far
    bne @range
    lda reu_host_end
    bne @range
@far:
    clc
    lda dos64_reu_request+R_REU
    adc dos64_reu_request+R_LENGTH
    sta reu_far_end
    lda dos64_reu_request+R_REU+1
    adc dos64_reu_request+R_LENGTH+1
    sta reu_far_end+1
    bcc @valid
    ora reu_far_end
    beq @valid
@range:
    lda #REU_ERR_RANGE
    bne @error
@mode:
    lda #REU_ERR_MODE
    bne @error
@zero:
    lda #REU_ERR_ZERO
@error:
    sta dos64_reu_request+R_ERROR
    pla
    sta $01
    pla
    sta $00
    plp
    sec
    rts
@valid:
    lda $DF00                  ; clear stale completion flags
    lda #0
    sta $DF09                  ; no REU interrupts
    sta $DF0A                  ; increment both addresses
    ldx #6
@setup:
    lda dos64_reu_request,x
    sta $DF02,x
    dex
    bpl @setup
    lda dos64_reu_request+R_DIRECTION
    ora #$90
    sta $DF01
    lda $DF00
    sta dos64_reu_request+R_STATUS
    lda dos64_reu_request+R_STATUS
    and #$60
    cmp #$40
    bne @device
    pla
    sta $01
    pla
    sta $00
    plp
    clc
    rts
@device:
    lda #REU_ERR_DEVICE
    jmp @error
