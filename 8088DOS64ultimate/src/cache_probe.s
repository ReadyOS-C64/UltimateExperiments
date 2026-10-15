.include "abi.inc"
.import dos64_cache_init, dos64_cache_limit, dos64_cache_flush
.import dos64_mem_read, dos64_mem_write, dos64_mailbox
.importzp dos64_address, dos64_mem_value
.export dos64_cache_probe

.segment "ZEROPAGE"
cache_probe_index: .res 2
cache_probe_pointer: .res 2
cache_probe_value: .res 1

.ifdef DOS64_UNIT_COLD
.segment "UNITCOLD"
.else
.segment "CODE"
.endif
; Same native transaction on Peddle/VICE/physical C64U. Two frames force dirty
; eviction across the expanded REC seam; 1536 bytes at guest 07FD00..0802FF.
; Exports verified readback at host 6000..65FF. No physical timing claim.
dos64_cache_probe:
    lda #2
    sta dos64_cache_limit
    jsr dos64_cache_init
    lda #0
    sta cache_probe_index
    sta cache_probe_index+1
@write:
    jsr cache_probe_address
    lda cache_probe_index
    eor cache_probe_index+1
    eor #$A7
    sta dos64_mem_value
    jsr dos64_mem_write
    bcc @next_write
    lda #1
    jmp cache_probe_fail
@next_write:
    jsr cache_probe_next
    bne @write
    jsr dos64_cache_flush
    bcc @flushed
    lda #2
    jmp cache_probe_fail
@flushed:
    jsr dos64_cache_init
    lda #0
    sta cache_probe_index
    sta cache_probe_index+1
    sta cache_probe_pointer
    lda #$60
    sta cache_probe_pointer+1
@read:
    jsr cache_probe_address
    jsr dos64_mem_read
    bcc @compare
    lda #3
    jmp cache_probe_fail
@compare:
    sta cache_probe_value
    ldy #0
    sta (cache_probe_pointer),y
    lda cache_probe_index
    eor cache_probe_index+1
    eor #$A7
    cmp cache_probe_value
    beq @next_read
    lda #4
    jmp cache_probe_fail
@next_read:
    inc cache_probe_pointer
    bne @index
    inc cache_probe_pointer+1
@index:
    jsr cache_probe_next
    bne @read
    lda #0
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_PASS
    sta dos64_mailbox+MB_STATUS
    lda #5
    sta $D020
    rts
cache_probe_fail:
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_FAIL
    sta dos64_mailbox+MB_STATUS
    lda #2
    sta $D020
    rts

cache_probe_address:
    lda cache_probe_index
    sta dos64_address
    clc
    lda cache_probe_index+1
    adc #$FD
    sta dos64_address+1
    lda #7
    adc #0
    sta dos64_address+2
    rts
cache_probe_next:
    inc cache_probe_index
    bne @not_done
    inc cache_probe_index+1
    lda cache_probe_index+1
    cmp #6
    rts
@not_done:
    lda #1
    rts
