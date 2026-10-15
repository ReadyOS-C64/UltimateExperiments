.include "abi.inc"
.include "reu.inc"
.import dos64_reu_request, dos64_reu_transfer, dos64_mailbox
.export dos64_range_backup, dos64_range_restore
.ifdef DOS64_RANGE_SNAPSHOT
.export dos64_reu_backup := dos64_range_backup
.export dos64_reu_restore := dos64_range_restore
.endif

.segment "CODE"
; Hardware recovery only. Concatenate the complete touched page envelopes:
; REU 07FC00..0803FF -> host 6000..67FF (guest, 2048 bytes)
; REU 34FF00..3504FF -> host 6800..6DFF (source, 1536 bytes)
; REU 35FF00..3604FF -> host 6E00..73FF (destination, 1536 bytes).
; Six descriptors explicitly split every 64 KiB REU bank seam. Never clear or
; initialize backing here: backup is read-only, restore writes exactly 5120 bytes.
; Return carry clear on success; carry set / MB_ERROR 1..6 identifies the first
; incomplete chunk. A failed restore can have written a prefix; retry all chunks.
; Clobbers A/X/Y and primitive ZP scratch; exclusive REU/host ownership required.
dos64_range_backup:
    lda #1
    bne range_snapshot_direction
dos64_range_restore:
    lda #0
range_snapshot_direction:
    sta dos64_reu_request+R_DIRECTION
    lda #0
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_READY
    sta dos64_mailbox+MB_STATUS
    ldy #0
@chunk:
    lda #0
    sta dos64_reu_request+R_HOST
    sta dos64_reu_request+R_REU
    sta dos64_reu_request+R_LENGTH
    lda range_snapshot_chunks,y
    sta dos64_reu_request+R_HOST+1
    lda range_snapshot_chunks+1,y
    sta dos64_reu_request+R_REU+1
    lda range_snapshot_chunks+2,y
    sta dos64_reu_request+R_REU+2
    lda range_snapshot_chunks+3,y
    sta dos64_reu_request+R_LENGTH+1
    jsr dos64_reu_transfer             ; primitive preserves Y
    bcs @failed
    iny
    iny
    iny
    iny
    cpy #24
    bne @chunk
    lda #STATUS_PASS
    sta dos64_mailbox+MB_STATUS
    clc
    rts
@failed:
    tya
    lsr
    lsr
    clc
    adc #1
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_FAIL
    sta dos64_mailbox+MB_STATUS
    sec
    rts

.segment "RODATA"
; host high, REU middle, REU bank, length high (all low bytes are zero).
range_snapshot_chunks:
    .byte $60, $FC, $07, $04
    .byte $64, $00, $08, $04
    .byte $68, $FF, $34, $01
    .byte $69, $00, $35, $05
    .byte $6E, $FF, $35, $01
    .byte $6F, $00, $36, $05
