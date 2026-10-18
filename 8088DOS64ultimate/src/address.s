.include "abi.inc"
.export dos64_segment, dos64_offset, dos64_address, dos64_physical, dos64_physical_owned

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
    jsr dos64_physical_owned
    plp
    rts

; CPU-private CLD entry. P/A clobbered, X/Y/inputs/banking preserved.
; No caller may depend on incoming carry after this translation.
dos64_physical_owned:
    ; Decompose segment*16 into its three bytes before adding the offset.
    ; Accumulator shifts avoid four full three-byte ZP rotations. The low
    ; nibble of segment+1 forms physical bits 12..15; its high nibble forms
    ; bits 16..19. No scratch, register, flag or bank lifetime is extended.
    lda dos64_segment+1
    lsr
    lsr
    lsr
    lsr
    sta dos64_address+2
    lda dos64_segment+1
    asl
    asl
    asl
    asl
    sta dos64_address+1
    lda dos64_segment
    lsr
    lsr
    lsr
    lsr
    ora dos64_address+1
    sta dos64_address+1
    lda dos64_segment
    asl
    asl
    asl
    asl
    clc
    adc dos64_offset
    sta dos64_address
    lda dos64_address+1
    adc dos64_offset+1
    sta dos64_address+1
    lda dos64_address+2
    adc #0
    and #$0F
    sta dos64_address+2
    rts
