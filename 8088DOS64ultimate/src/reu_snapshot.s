.include "abi.inc"
.include "reu.inc"
.import dos64_reu_request, dos64_reu_transfer, dos64_mailbox
.export dos64_reu_backup, dos64_reu_restore

.ifdef DOS64_UNIT_COLD
.segment "UNITEXTRA"
.else
.segment "CODE"
.endif
; Dedicated hardware-fixture helpers. Back up/restore exactly 07FC00..0803FF
; through host 6000..67FF; split at the REC bank boundary. No file operations.
dos64_reu_backup:
    lda #1
    bne snapshot_direction
dos64_reu_restore:
    lda #0
snapshot_direction:
    sta dos64_reu_request+R_DIRECTION
    lda #0
    sta dos64_reu_request+R_HOST
    sta dos64_reu_request+R_REU
    sta dos64_reu_request+R_LENGTH
    lda #$60
    sta dos64_reu_request+R_HOST+1
    lda #$FC
    sta dos64_reu_request+R_REU+1
    lda #7
    sta dos64_reu_request+R_REU+2
    lda #4
    sta dos64_reu_request+R_LENGTH+1
    jsr dos64_reu_transfer
    bcc @second
    lda #1
    bne snapshot_failed
@second:
    lda #$64
    sta dos64_reu_request+R_HOST+1
    lda #0
    sta dos64_reu_request+R_REU+1
    lda #8
    sta dos64_reu_request+R_REU+2
    jsr dos64_reu_transfer
    bcc @passed
    lda #2
    bne snapshot_failed
@passed:
    lda #0
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_PASS
    sta dos64_mailbox+MB_STATUS
    rts
snapshot_failed:
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_FAIL
    sta dos64_mailbox+MB_STATUS
    rts
