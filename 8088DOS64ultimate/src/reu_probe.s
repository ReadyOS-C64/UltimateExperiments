.include "abi.inc"
.include "reu.inc"
.import dos64_reu_transfer, dos64_reu_request, dos64_mailbox
.export dos64_reu_probe
.exportzp probe_ptr

.segment "ZEROPAGE"
probe_ptr: .res 2
.ifdef DOS64_UNIT_COLD
.segment "UNITCOLD"
.else
.segment "CODE"
.endif
; Integrity vector shared by Peddle, VICE and later physical hardware.
; Requires normal RAM+IO mapping; uses $6000-$6FFF and REU $180003-$181002.
; Preserves P; clobbers A/X/Y and probe_ptr. No physical timing claim.
dos64_reu_probe:
    php
    sei
    cld
    lda #0
    sta dos64_mailbox+MB_ERROR
    sta probe_ptr
    lda #$60
    sta probe_ptr+1
    ldx #16
    ldy #0
@fill:
    tya
    eor #$A7
    sta (probe_ptr),y
    iny
    bne @fill
    inc probe_ptr+1
    dex
    bne @fill
    lda #0
    sta dos64_reu_request+R_HOST
    sta dos64_reu_request+R_REU+1
    sta dos64_reu_request+R_LENGTH
    sta dos64_reu_request+R_DIRECTION
    lda #$60
    sta dos64_reu_request+R_HOST+1
    lda #3
    sta dos64_reu_request+R_REU
    lda #$18
    sta dos64_reu_request+R_REU+2
    lda #$10
    sta dos64_reu_request+R_LENGTH+1
    jsr dos64_reu_transfer
    bcc @clear_start
    lda #1
    jmp @fail
@clear_start:
    lda #$60
    sta probe_ptr+1
    lda #0
    ldx #16
@clear:
    sta (probe_ptr),y
    iny
    bne @clear
    inc probe_ptr+1
    dex
    bne @clear
    lda #1
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    bcc @check_start
    lda #2
    jmp @fail
@check_start:
    lda #$60
    sta probe_ptr+1
    ldx #16
@check:
    tya
    eor #$A7
    cmp (probe_ptr),y
    bne @mismatch
    iny
    bne @check
    inc probe_ptr+1
    dex
    bne @check
    lda #STATUS_PASS
    sta dos64_mailbox+MB_STATUS
    lda #5
    sta $D020
    plp
    rts
@mismatch:
    lda #3
@fail:
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_FAIL
    sta dos64_mailbox+MB_STATUS
    lda #2
    sta $D020
    plp
    rts
