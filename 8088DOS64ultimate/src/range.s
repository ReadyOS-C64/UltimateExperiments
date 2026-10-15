.include "abi.inc"
.include "reu.inc"
.include "range.inc"
.macpack longbranch
.import dos64_reu_request, dos64_reu_transfer, dos64_mem_read, dos64_mem_write
.importzp dos64_address, dos64_mem_value
.export dos64_range_copy, dos64_range_request, dos64_range_buffer

.segment "BSS"
dos64_range_request: .res GR_SIZE
range_chunk: .res 2
range_index: .res 1
range_end: .res 3
.segment "RANGEBUFFER"
dos64_range_buffer: .res 256
.assert dos64_range_buffer = $C000, lderror, "range buffer must be C000-C0FF"

.segment "CODE"
; Coherent copy between a non-guest REU arena and linear 20-bit guest bus.
; P except returned C preserved; normal RAM/I/O mapping, non-reentrant. All
; guest accesses use cache API. Request mutates to remaining work; DONE counts
; current invocation only and resets on entry. Import commits one byte at a
; time; export commits one <=256-byte chunk only after successful DMA.
dos64_range_copy:
    php
    sei
    cld
    lda #0
    sta dos64_range_request+GR_STATUS
    sta dos64_range_request+GR_ERROR
    sta dos64_range_request+GR_DONE
    sta dos64_range_request+GR_DONE+1
    lda dos64_range_request+GR_GUEST+2
    cmp #$10
    jcs range_input_error
    lda dos64_range_request+GR_DIRECTION
    cmp #2
    jcs range_input_error
    lda dos64_range_request+GR_REU+2
    cmp #$10
    jcc range_reu_error
    cmp #$40
    jcs range_reu_error
    clc
    lda dos64_range_request+GR_REU
    adc dos64_range_request+GR_LENGTH
    sta range_end
    lda dos64_range_request+GR_REU+1
    adc dos64_range_request+GR_LENGTH+1
    sta range_end+1
    lda dos64_range_request+GR_REU+2
    adc #0
    sta range_end+2
    cmp #$40
    bcc range_next
    jne range_reu_error
    lda range_end
    ora range_end+1
    jne range_reu_error
range_next:
    lda dos64_range_request+GR_LENGTH
    ora dos64_range_request+GR_LENGTH+1
    jeq range_success
    lda #0
    sta range_index
    sta range_chunk
    lda #1
    sta range_chunk+1
    lda dos64_range_request+GR_LENGTH+1
    bne @seam
    sta range_chunk+1
    lda dos64_range_request+GR_LENGTH
    sta range_chunk
@seam:
    lda dos64_range_request+GR_REU+1
    cmp #$FF
    bne @direction
    lda dos64_range_request+GR_REU
    beq @direction
    ; Only the final partial256bytes of a64KiBbank can constrain this chunk.
    eor #$FF
    clc
    adc #1
    tax
    lda range_chunk+1
    bne @limit
    txa
    cmp range_chunk
    bcs @direction
@limit:
    stx range_chunk
    lda #0
    sta range_chunk+1
@direction:
    lda dos64_range_request+GR_DIRECTION
    bne range_export
    lda #1
    jsr range_dma
    jcs range_dma_error
range_import:
    lda #0
    jsr range_guest_address
    ldx range_index
    lda dos64_range_buffer,x
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs range_cache_error
    jsr range_advance_one
    inc range_index
    lda range_index
    cmp range_chunk
    bne range_import
    jmp range_next
range_export:
    lda range_index
    jsr range_guest_address
    jsr dos64_mem_read
    jcs range_cache_error
    ldx range_index
    sta dos64_range_buffer,x
    inc range_index
    lda range_index
    cmp range_chunk
    bne range_export
    lda #0
    jsr range_dma
    jcs range_dma_error
    lda #0
    sta range_index
@commit:
    jsr range_advance_one
    inc range_index
    lda range_index
    cmp range_chunk
    bne @commit
    jmp range_next
range_dma:
    sta dos64_reu_request+R_DIRECTION
    lda #<dos64_range_buffer
    sta dos64_reu_request+R_HOST
    lda #>dos64_range_buffer
    sta dos64_reu_request+R_HOST+1
    ldx #2
@address:
    lda dos64_range_request+GR_REU,x
    sta dos64_reu_request+R_REU,x
    dex
    bpl @address
    lda range_chunk
    sta dos64_reu_request+R_LENGTH
    lda range_chunk+1
    sta dos64_reu_request+R_LENGTH+1
    jmp dos64_reu_transfer
range_guest_address:
    clc
    adc dos64_range_request+GR_GUEST
    sta dos64_address
    lda dos64_range_request+GR_GUEST+1
    adc #0
    sta dos64_address+1
    lda dos64_range_request+GR_GUEST+2
    adc #0
    and #$0F
    sta dos64_address+2
    rts
range_advance_one:
    inc dos64_range_request+GR_GUEST
    bne @reu
    inc dos64_range_request+GR_GUEST+1
    bne @reu
    inc dos64_range_request+GR_GUEST+2
    lda dos64_range_request+GR_GUEST+2
    and #$0F
    sta dos64_range_request+GR_GUEST+2
@reu:
    inc dos64_range_request+GR_REU
    bne @remaining
    inc dos64_range_request+GR_REU+1
    bne @remaining
    inc dos64_range_request+GR_REU+2
@remaining:
    lda dos64_range_request+GR_LENGTH
    bne @low
    dec dos64_range_request+GR_LENGTH+1
@low:
    dec dos64_range_request+GR_LENGTH
    inc dos64_range_request+GR_DONE
    bne @done
    inc dos64_range_request+GR_DONE+1
@done:
    rts
range_input_error:
    lda #GR_ERR_INPUT
    bne range_error
range_reu_error:
    lda #GR_ERR_REU
    bne range_error
range_cache_error:
    lda #GR_ERR_CACHE
    bne range_error
range_dma_error:
    lda #GR_ERR_DMA
range_error:
    sta dos64_range_request+GR_ERROR
    lda #2
    sta dos64_range_request+GR_STATUS
    plp
    sec
    rts
range_success:
    lda #1
    sta dos64_range_request+GR_STATUS
    plp
    clc
    rts
