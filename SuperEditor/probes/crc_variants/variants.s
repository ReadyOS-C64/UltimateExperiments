.setcpu "6502"
.export crc_init,crc_value,crc_baseline_byte,crc256_byte,crc64_byte
.export crc256_bad_byte,crc_clock_calibration
.export crc_baseline_end,crc256_end,crc64_end,crc256_bad_end
.export crc256_lo,crc256_hi,crc64_low_lo,crc64_low_hi,crc64_high_lo,crc64_high_hi
.export crc256_bad_lo,crc256_bad_hi
.export crc256_tables_start,crc256_tables_end,crc64_tables_start,crc64_tables_end
.segment "STATE"
crc_value: .res 2
.segment "CODE"
; Same API as the production CRC: inputA, value16 state, clobberA/X/P, preserveY.
crc_init:
    lda #$FF
    sta crc_value
    sta crc_value+1
    rts
; Exact instruction sequence from src/overlay/crc.s; no table/scratch.
crc_baseline_byte:
    eor crc_value+1
    sta crc_value+1
    lsr
    lsr
    lsr
    lsr
    eor crc_value+1
    tax
    txa
    asl
    asl
    asl
    asl
    sta crc_value+1
    txa
    lsr
    lsr
    lsr
    eor crc_value+1
    sta crc_value+1
    lda crc_value
    eor crc_value+1
    sta crc_value+1
    txa
    asl
    asl
    asl
    asl
    asl
    sta crc_value
    txa
    eor crc_value
    sta crc_value
    rts
crc_baseline_end:
.macro CRC256 name,low,high,endlabel
name:
    eor crc_value+1
    tax
    lda crc_value
    eor high,x
    sta crc_value+1
    lda low,x
    sta crc_value
    rts
endlabel:
.endmacro
; Both indexed arrays are page-aligned. Every possible input has fixed cost.
CRC256 crc256_byte,crc256_lo,crc256_hi,crc256_end
; Diagnostic only: same algorithm with tables offset1 to exercise page penalties.
CRC256 crc256_bad_byte,crc256_bad_lo,crc256_bad_hi,crc256_bad_end
; CCITT byte table is linear: T[x]=T[x&15] XOR T[(x>>4)<<4].
; Four16-byte arrays occupy64 bytes. Existing CRC state is reused as scratch;
; one transient PHA byte holds partial output. No extra permanent RAM or ZP.
crc64_byte:
    eor crc_value+1
    sta crc_value+1
    and #$0F
    tax
    lda crc_value
    eor crc64_low_hi,x
    sta crc_value
    lda crc64_low_lo,x
    pha
    lda crc_value+1
    lsr
    lsr
    lsr
    lsr
    tax
    lda crc_value
    eor crc64_high_hi,x
    sta crc_value+1
    pla
    eor crc64_high_lo,x
    sta crc_value
    rts
crc64_end:
crc_clock_calibration:
    nop
    nop
    rts

; Generated constant tables. CCITT-FALSE poly1021; no reflection/finalxor.
.include "tables.inc"

; Link-time guards: no input-dependent indexed read penalty in chosen variants.
.assert (crc256_lo & $FF)=0, lderror, "CRC256 low table must start on a page"
.assert (crc256_hi & $FF)=0, lderror, "CRC256 high table must start on a page"
.assert (crc64_low_lo & $0F)=0, lderror, "CRC64 table alignment16 required"
.assert (crc64_low_hi & $0F)=0, lderror, "CRC64 table alignment16 required"
.assert (crc64_high_lo & $0F)=0, lderror, "CRC64 table alignment16 required"
.assert (crc64_high_hi & $0F)=0, lderror, "CRC64 table alignment16 required"
