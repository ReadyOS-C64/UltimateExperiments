.include "abi.inc"
.include "reu.inc"
.include "range.inc"
.macpack longbranch
.import dos64_cache_init, dos64_cache_limit, dos64_mem_read, dos64_mem_write
.import dos64_range_copy, dos64_range_request, dos64_range_buffer
.import dos64_reu_transfer, dos64_reu_request, dos64_mailbox
.importzp dos64_address, dos64_mem_value
.export dos64_range_probe

.segment "ZEROPAGE"
range_probe_index: .res 2
range_probe_pointer: .res 2
range_probe_value: .res 1

.ifdef DOS64_UNIT_COLD
.segment "UNITCOLD"
.else
.segment "CODE"
.endif
; Standalone integrity transaction; external arenas and output are probe-owned.
; SOURCE 34FF00..3504FF -> guest 07FD00..0802FF -> DEST 35FF00..3604FF.
; Host 6000..65FF is evidence output only; C000..C0FF is the range bounce.
; Two frames force eviction. Dirty edits before export test cache authority.
dos64_range_probe:
    lda #2
    sta dos64_cache_limit
    jsr dos64_cache_init
    lda #0
    sta range_probe_index
    sta range_probe_index+1
@source_page:
    ldx #0
@fill:
    txa
    eor range_probe_index+1
    eor #$A7
    sta dos64_range_buffer,x
    inx
    bne @fill
    lda #$C0
    sta dos64_reu_request+R_HOST+1
    lda #$34
    jsr range_probe_dma_address
    lda #0
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    bcc @source_next
    lda #1
    jmp range_probe_fail
@source_next:
    inc range_probe_index+1
    lda range_probe_index+1
    cmp #6
    bne @source_page
    lda #$34
    ldx #GR_FROM_REU
    jsr range_probe_request
    jsr dos64_range_copy
    bcc @verify_init
    lda #2
    jmp range_probe_fail
@verify_init:
    lda #0
    sta range_probe_index
    sta range_probe_index+1
@verify_guest:
    jsr range_probe_guest_address
    jsr dos64_mem_read
    bcc @compare_guest
    lda #3
    jmp range_probe_fail
@compare_guest:
    sta range_probe_value
    jsr range_probe_pattern
    cmp range_probe_value
    beq @edit
    lda #4
    jmp range_probe_fail
@edit:
    lda range_probe_index
    bne @guest_next
    lda range_probe_value
    eor #$5A
    sta dos64_mem_value
    jsr dos64_mem_write
    bcc @guest_next
    lda #5
    jmp range_probe_fail
@guest_next:
    jsr range_probe_next
    bne @verify_guest
    lda #$35
    ldx #GR_TO_REU
    jsr range_probe_request
    jsr dos64_range_copy
    bcc @clear_output
    lda #6
    jmp range_probe_fail
@clear_output:
    ; Poison all evidence bytes before independent DEST -> host DMA.
    ldx #0
    lda #$CC
@poison:
    sta $6000,x
    sta $6100,x
    sta $6200,x
    sta $6300,x
    sta $6400,x
    sta $6500,x
    inx
    bne @poison
    lda #0
    sta range_probe_index
    sta range_probe_index+1
@reload_page:
    clc
    lda range_probe_index+1
    adc #$60
    sta dos64_reu_request+R_HOST+1
    lda #$35
    jsr range_probe_dma_address
    lda #1
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    bcc @reload_next
    lda #7
    jmp range_probe_fail
@reload_next:
    inc range_probe_index+1
    lda range_probe_index+1
    cmp #6
    bne @reload_page
    lda #0
    sta range_probe_index
    sta range_probe_index+1
    sta range_probe_pointer
    lda #$60
    sta range_probe_pointer+1
@verify_output:
    jsr range_probe_pattern
    ldx range_probe_index
    bne @compare_output
    eor #$5A
@compare_output:
    ldy #0
    cmp (range_probe_pointer),y
    beq @output_next
    lda #8
    jmp range_probe_fail
@output_next:
    inc range_probe_pointer
    bne @output_index
    inc range_probe_pointer+1
@output_index:
    jsr range_probe_next
    bne @verify_output
    lda #0
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_PASS
    sta dos64_mailbox+MB_STATUS
    lda #5
    sta $D020
    rts
range_probe_fail:
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_FAIL
    sta dos64_mailbox+MB_STATUS
    lda #2
    sta $D020
    rts

; A=external starting bank34/35; page index selects six individually bounded DMAs.
range_probe_dma_address:
    tax
    lda #0
    sta dos64_reu_request+R_HOST
    sta dos64_reu_request+R_REU
    sta dos64_reu_request+R_LENGTH
    lda #1
    sta dos64_reu_request+R_LENGTH+1
    clc
    lda range_probe_index+1
    adc #$FF
    sta dos64_reu_request+R_REU+1
    txa
    adc #0
    sta dos64_reu_request+R_REU+2
    rts
range_probe_request:
    sta dos64_range_request+GR_REU+2
    stx dos64_range_request+GR_DIRECTION
    lda #0
    sta dos64_range_request+GR_GUEST
    sta dos64_range_request+GR_REU
    sta dos64_range_request+GR_LENGTH
    lda #$FD
    sta dos64_range_request+GR_GUEST+1
    lda #7
    sta dos64_range_request+GR_GUEST+2
    lda #$FF
    sta dos64_range_request+GR_REU+1
    lda #6
    sta dos64_range_request+GR_LENGTH+1
    rts
range_probe_guest_address:
    lda range_probe_index
    sta dos64_address
    clc
    lda range_probe_index+1
    adc #$FD
    sta dos64_address+1
    lda #7
    adc #0
    sta dos64_address+2
    rts
range_probe_pattern:
    lda range_probe_index
    eor range_probe_index+1
    eor #$A7
    rts
range_probe_next:
    inc range_probe_index
    bne @not_done
    inc range_probe_index+1
    lda range_probe_index+1
    cmp #6
    rts
@not_done:
    lda #1
    rts
