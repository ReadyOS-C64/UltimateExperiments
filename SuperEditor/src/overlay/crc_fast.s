.setcpu "6502"
.export se_crc_init,se_crc_byte,se_crc_value,se_crc_table_low,se_crc_table_high
.segment "BSS"
se_crc_value: .res 2
.segment "CODE"
; Same CCITT-FALSE byte ABI as crc.s; preserveY, clobberA/X/P. No extra scratch.
se_crc_init:
    lda #$FF
    sta se_crc_value
    sta se_crc_value+1
    rts
se_crc_byte:
    eor se_crc_value+1
.ifdef EDITOR_HALF_CRC
    bmi @upper
.endif
    tax
    lda se_crc_value
    eor se_crc_table_high,x
    sta se_crc_value+1
    lda se_crc_table_low,x
    sta se_crc_value
    rts
.ifdef EDITOR_HALF_CRC
@upper:
    and #$7F
    tax
    lda se_crc_value
    eor se_crc_table_high,x
    eor #$91 ;CCITT table[i+128] = table[i] XOR $9188
    sta se_crc_value+1
    lda se_crc_table_low,x
    eor #$88
    sta se_crc_value
    rts
.endif
.segment "CRC_TABLE"
.ifdef EDITOR_HALF_CRC
; Linearity halves the immutable table. Both128-byte arrays remain within
; one page, so absolute-indexed lookups incur no page-crossing penalty.
se_crc_table_low:
.repeat 128,I
    CRC .set I<<8
    .repeat 8
        .if CRC & $8000
            CRC .set ((CRC<<1)^$1021)&$FFFF
        .else
            CRC .set (CRC<<1)&$FFFF
        .endif
    .endrepeat
    .byte <CRC
.endrepeat
se_crc_table_high:
.repeat 128,I
    CRC .set I<<8
    .repeat 8
        .if CRC & $8000
            CRC .set ((CRC<<1)^$1021)&$FFFF
        .else
            CRC .set (CRC<<1)&$FFFF
        .endif
    .endrepeat
    .byte >CRC
.endrepeat
.assert (se_crc_table_low & $FF)=0,lderror,"CRC half lookup must be page aligned"
.assert se_crc_table_high=se_crc_table_low+128,lderror,"CRC half tables must share page"
.else
.include "overlay/crc_tables.inc"
.assert (se_crc_table_low & $FF)=0,lderror,"CRC low lookup must be page aligned"
.assert (se_crc_table_high & $FF)=0,lderror,"CRC high lookup must be page aligned"
.endif
