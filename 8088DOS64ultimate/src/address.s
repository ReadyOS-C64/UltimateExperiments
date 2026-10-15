.include "abi.inc"
.export dos64_segment, dos64_offset, dos64_address, dos64_physical

.segment "ZEROPAGE"
dos64_segment: .res 2
dos64_offset: .res 2
dos64_address: .res 3

.segment "CODE"
; In: segment/offset words. Out: 20-bit physical address, little endian.
; Clobbers A and address; preserves X/Y/P, input words and host banking.
dos64_physical:
    php
    cld
    lda dos64_segment
    sta dos64_address
    lda dos64_segment+1
    sta dos64_address+1
    lda #0
    sta dos64_address+2
.repeat 4
    asl dos64_address
    rol dos64_address+1
    rol dos64_address+2
.endrepeat
    clc
    lda dos64_address
    adc dos64_offset
    sta dos64_address
    lda dos64_address+1
    adc dos64_offset+1
    sta dos64_address+1
    lda dos64_address+2
    adc #0
    and #$0F
    sta dos64_address+2
    plp
    rts
