.setcpu "6502"
.export se_crc_init, se_crc_byte, se_crc_value
.segment "BSS"
se_crc_value: .res 2
.segment "CODE"
; CRC16/CCITT-FALSE: poly1021, initFFFF, no reflection/final xor.
se_crc_init:
    lda #$FF
    sta se_crc_value
    sta se_crc_value+1
    rts
; A next byte. Clobbers A/X/P. No ZP, table or input buffer dependency.
se_crc_byte:
    ; x = (oldHigh XOR byte); x ^= x>>4.
    ; newHigh = oldLow XOR (x<<4) XOR (x>>3), newLow = x XOR (x<<5).
    ; Linear CCITT polynomial reduction, no table, scratch byte or data branch.
    eor se_crc_value+1
    sta se_crc_value+1
    lsr
    lsr
    lsr
    lsr
    eor se_crc_value+1
    tax
    txa
    asl
    asl
    asl
    asl
    sta se_crc_value+1
    txa
    lsr
    lsr
    lsr
    eor se_crc_value+1
    sta se_crc_value+1
    lda se_crc_value
    eor se_crc_value+1
    sta se_crc_value+1
    txa
    asl
    asl
    asl
    asl
    asl
    sta se_crc_value
    txa
    eor se_crc_value
    sta se_crc_value
    rts
